from kfp import dsl, compiler
from kfp.dsl import Output, Model, Input, Dataset, Metrics
import os

#
# Get Google project ID and region from enironment
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")


@dsl.component(
    base_image = f"{google_region}-docker.pkg.dev/{google_project_id}/vertex-ai-docker-repo/pipeline:latest",
)
def create_data(training_data : Output[Dataset], 
                validation_data : Output[Dataset],
                size : int ):
    """
    Create training- and validation data with a 80/20 split

    Args:
        size : the number of items in the dataset overall 
        training_data : the training data set
        validation_data : the validation data set 

    """
    import numpy as np
    import torch
    import pickle
    X = []
    Y = []
    for i in range(size):
        #
        # First do the label, then choose a point in a corresponding cluster
        #
        label = np.random.randint(0, 2)
        if label == 0:
            #
            # below diagonal
            #
            x = np.array([ 0.5, 0.25 ])
        else:
            x = np.array([ 0.5, 0.75 ])
        #
        # Add some noise
        #
        x = x + 0.05 * np.random.random(2)
        X.append(x)
        Y.append(label)
    #
    # X is now a list of arrays - converting this to a single array 
    # before turning this into a tensor is more efficient
    #
    X = np.array(X)
    X = torch.tensor(X, dtype = torch.float32)
    Y = torch.tensor(Y, dtype = torch.float32)
    assert X.shape == torch.Size([size, 2])
    assert Y.shape == torch.Size([size])
    split = int(size*0.8)
    training_dataset = (X[:split], Y[:split])
    validation_dataset = (X[split:], Y[split:])
    print(f"Writing training data to {training_data.path}")
    with open(training_data.path, "wb") as out:
        pickle.dump(training_dataset, out)
    print(f"Writing validation data to {validation_data.path}")
    with open(validation_data.path, "wb") as out:
        pickle.dump(validation_dataset, out)


@dsl.component(
    base_image = f"{google_region}-docker.pkg.dev/{google_project_id}/vertex-ai-docker-repo/pipeline:latest",
)
def train(epochs : int, 
            lr : float,
            data : Input[Dataset],  
            trained_model : Output[Model],
            metrics: Output[Metrics],
            job_name : str ):
    """
    Do the actual training. This is a simple binary classification model

    Args:
        epochs : epochs
        lr : learning rate
        trained_model : model output 
        metrics : training metrics
        job_name : the name of the pipeline job in which this executes

    """
    print(f"Job name : {job_name}")
    #
    # Unpickle data again
    #
    import pickle
    with open(data.path, "rb") as file:
        X, Y = pickle.load(file)
    print(f"Got {len(X)} rows of training data")
    import model    
    import torch
    _model = model.Model()
    #
    # Run actual training loop
    #
    _model.train()
    optimizer = torch.optim.SGD(_model.parameters(), lr = lr)
    loss_fn = torch.nn.functional.binary_cross_entropy_with_logits
    for e in range(epochs):
        logits = _model(X).squeeze(dim = 1)
        #
        # Yes, the targets are expected to be floats
        #
        loss = loss_fn(input = logits, target = Y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print(f"Final loss: {loss.item()}")
    metrics.log_metric("final_loss", loss.item())
    #
    # Store trained model as state dir
    #
    torch.save(_model.state_dict(), trained_model.path)

@dsl.component(
    base_image = f"{google_region}-docker.pkg.dev/{google_project_id}/vertex-ai-docker-repo/pipeline:latest"
)
def evaluate(trained_model : Input[Model], 
             validation_data : Input[Dataset], 
             metrics: Output[Metrics]):
    """
    Evaluate the model

    Args:
        trained_model : the model to be evaluated
        validation_data : the validation data
        metrics : metric artifact to which we log the result of the validation

    """
    import model 
    import torch
    import numpy as np
    #
    # Load model
    #        
    _model = model.Model()
    with open(trained_model.path, "rb") as file:
        _model.load_state_dict(torch.load(file))
    hits = 0 
    #
    # Unpickle validation data
    #
    import pickle
    with open(validation_data.path, "rb") as file:
        X, Y = pickle.load(file)
    print(f"Got {len(X)} rows of validation data")
    for t, x in enumerate(X):
        label = Y[t]
        prediction = _model.predict(x)
        if prediction == label:
            hits = hits + 1
        accuracy = 100.0 * hits / len(X)
    print(f"Accuracy: {accuracy}")
    metrics.log_metric("accuracy", accuracy)


@dsl.pipeline(
    name = "my-pipeline"
)
def my_pipeline(epochs : int, lr : float, size : int):
    _create_data = create_data(size = size)
    _train = train(epochs = epochs,
                  lr = lr,
                  data = _create_data.outputs['training_data'],
                  #
                  # This actually gets what is called the job ID in the
                  # PipelineJob create method, i.e. unless overwritten there,
                  # this is <display_name>-<timestamp>
                  # It will be resolved at runtime, i.e. in the executor input
                  # provided by VertexAI to our job
                  #
                  job_name = dsl.PIPELINE_JOB_NAME_PLACEHOLDER)
    _train.set_cpu_limit("2")
    _eval = evaluate(trained_model = _train.outputs['trained_model'],
                     validation_data = _create_data.outputs['validation_data'])


if __name__ == "__main__":
    #
    # Compile
    #
    compiler.Compiler().compile(pipeline_func = my_pipeline, 
                            package_path = "my-pipeline.json")
