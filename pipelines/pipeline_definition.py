from kfp import dsl
from kfp.dsl import Output, Model
from kfp import compiler
import os

@dsl.component(
    base_image = "python:3.9",
)
def train(google_project_id : str, google_region: str, epochs : int, model : Output[Model]):
    #
    # We do not actually do anything here 
    # and only print the parameters
    #
    print(f"Google project ID: {google_project_id}")
    print(f"Google region:     {google_region}")
    print(f"Epochs:            {epochs}")



@dsl.pipeline(
    name = "my-pipeline"
)
def my_pipeline(epochs : int):
    google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
    google_region = os.environ.get("GOOGLE_REGION")
    component = train(google_project_id = google_project_id,
                  google_region = google_region,
                  epochs = epochs)
    component.set_cpu_limit("2")



if __name__ == "__main__":
    #
    # Compile
    #
    compiler.Compiler().compile(pipeline_func = my_pipeline, 
                            package_path = "my-pipeline.yaml")
