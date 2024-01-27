from kfp import dsl
from kfp.dsl import Output, Model, Input, Dataset
from kfp import compiler
import os

@dsl.component(
    base_image = "python:3.9",
)
def create_data(google_project_id : str, google_region: str, data : Output[Dataset]):
    import numpy as np
    import torch
    import pickle
    N = 100
    X = []
    Y = []
    for i in range(N):
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
    assert X.shape == torch.Size([N, 2])
    assert Y.shape == torch.Size([N])
    dataset = (X, Y)
    print(f"Writing training data to {data.path}")
    with open(data.path, "wb") as out:
        pickle.dump(dataset, out)

@dsl.component(
    base_image = "python:3.9",
)
def train(google_project_id : str, google_region: str, epochs : int, data : Input[Dataset],  model : Output[Model]):
    #
    # Unpickle data again
    #
    import pickle
    with open(data.path, "rb") as file:
        X, Y = pickle.load(file)
    print(f"Got {len(X)} rows of training data")
    

@dsl.pipeline(
    name = "my-pipeline"
)
def my_pipeline(epochs : int):
    google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
    google_region = os.environ.get("GOOGLE_REGION")
    _create_data = create_data(google_project_id = google_project_id, 
                               google_region = google_region)
    _train = train(google_project_id = google_project_id,
                  google_region = google_region,
                  epochs = epochs,
                  data = _create_data.outputs['data'])
    _train.set_cpu_limit("2")



if __name__ == "__main__":
    #
    # Compile
    #
    compiler.Compiler().compile(pipeline_func = my_pipeline, 
                            package_path = "my-pipeline.yaml")
