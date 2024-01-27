from kfp import dsl
from kfp.dsl import Output, Model, Input, Dataset, Metrics
from kfp import compiler
import os

google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")


@dsl.component(
    base_image = f"{google_region}-docker.pkg.dev/{google_project_id}/vertex-ai-docker-repo/pipeline:latest",
)
def create_data(google_project_id : str, google_region: str, data : Output[Dataset], items : int ):
    import numpy as np
    import torch
    import pickle
    X = []
    Y = []
    for i in range(items):
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
    assert X.shape == torch.Size([items, 2])
    assert Y.shape == torch.Size([items])
    dataset = (X, Y)
    print(f"Writing training data to {data.path}")
    with open(data.path, "wb") as out:
        pickle.dump(dataset, out)

@dsl.component(
    base_image = f"{google_region}-docker.pkg.dev/{google_project_id}/vertex-ai-docker-repo/pipeline:latest",
)
def train(google_project_id : str, google_region: str, 
                            epochs : int, 
                            lr : float,
                            data : Input[Dataset],  
                            trained_model : Output[Model],
                            metrics: Output[Metrics]):
    #
    # Unpickle data again
    #
    import pickle
    with open(data.path, "rb") as file:
        X, Y = pickle.load(file)
    print(f"Got {len(X)} rows of training data")#
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
    base_image = f"{google_region}-docker.pkg.dev/{google_project_id}/vertex-ai-docker-repo/pipeline:latest",
)
def evaluate(trained_model : Input[Model], trials : int):
    import model 
    import torch
    import pickle
    import numpy as np
    #
    # Load model
    #        
    _model = model.Model()
    with open(trained_model.path, "rb") as file:
        _model.load_state_dict(torch.load(file))
    hits = 0 
    for t in range(trials):
        label = np.random.randint(0, 2)
        if label == 0:
            x = np.array([ 0.5, 0.25 ])
        else:
            x = np.array([ 0.5, 0.75 ])
        x = x + 0.05 * np.random.random(2)
        prediction = _model.predict(torch.tensor(x, dtype = torch.float32))
        if prediction == label:
            hits = hits + 1
        accuracy = 100.0 * hits / trials
    print(f"Accuracy: {accuracy}")


@dsl.pipeline(
    name = "my-pipeline"
)
def my_pipeline(epochs : int, lr : float, items : int, trials : int):
    _create_data = create_data(google_project_id = google_project_id, 
                               google_region = google_region, 
                               items = items)
    _train = train(google_project_id = google_project_id,
                  google_region = google_region,
                  epochs = epochs,
                  lr = lr,
                  data = _create_data.outputs['data'])
    _train.set_cpu_limit("2")
    _eval = evaluate(trained_model = _train.outputs['trained_model'],
                     trials = trials)


if __name__ == "__main__":
    #
    # Compile
    #
    compiler.Compiler().compile(pipeline_func = my_pipeline, 
                            package_path = "my-pipeline.yaml")
