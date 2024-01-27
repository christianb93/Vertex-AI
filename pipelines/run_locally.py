#
# Run a component locally
#
import inspect
import typing
from kfp.dsl import executor
from kfp.dsl import types
import pipeline_definition
import shutil
import argparse


LOCAL_DIR = "./gcs"
PIPELINE_ROOT = "/vertex-ai/pipeline_root"

#
# Patch GCS prefix. When initializing the executor, an URI starting with
# gs:// is turned into a path by replacing gs:// by this prefix. Usually this 
# is /gcs, we overwrite this by our local directory
#
types.artifact_types._GCS_LOCAL_MOUNT_PREFIX = LOCAL_DIR

#
# Parameter values for all steps
#
common_parameter_values = {
            "epochs" : 500,
            "google_project_id" : "my-project",
            "google_region" : "us-east1"
        }

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", 
                        action = "store_true",
                        default = False,
                        help = "Generate a bit more output")
    return parser.parse_args()
#
# Define the local path for an input or output artifact of a given step
# 
def get_local_artifact_path(artifact_name, step_name):
    return f"{LOCAL_DIR}{PIPELINE_ROOT}/{step_name}/{artifact_name}"


def create_runtime_artifact(artifact_name, step_name, schema_title):
        #
        # This dictionary represents a runtime artifact,
        # i.e. an instance of one of the classes in dsl.types.artifact_types
        # At runtime, the schema title is used to identify the correct class
        #
        return {
            "name" : f"{artifact_name}",    
            "metadata" : {},
            "type": {
                "schemaTitle" : schema_title
            },  
            #
            # The URI will be used to determine the local path at runtime. For a GCS bucket,
            # the gs:// prefix will be replaced by /gcs or more precisely by the value of
            # types.artifact_types._GCS_LOCAL_MOUNT_PREFIX
            #
            "uri" : f"gs://{PIPELINE_ROOT}/{step_name}/{artifact_name}"
        }


def get_schema_title_for_type(cls):
    return cls.schema_title     


def build_executor_input_from_function(func, step_name):
    #
    # Strip of Python function
    #
    python_func = func.python_func 
    signature = inspect.signature(python_func)
    output_artifacts = {}
    input_artifacts = {}
    parameter_values = {}
    for _, param in signature.parameters.items():
        param_type = param.annotation
        param_name = param.name 
        if param_type == str or param_type == int:
            #
            # Check that input is contained in common executor input
            #
            assert param_name in common_parameter_values
            #
            # and take it from there
            #
            parameter_values[param_name] = common_parameter_values[param_name]
        if typing.get_origin(param_type) == typing.Annotated:
            args = typing.get_args(param_type)
            if  args[1] == types.type_annotations.OutputAnnotation:
                output_type = args[0]
                schema_title = get_schema_title_for_type(output_type)
                output_artifacts[param_name] = {
                    "artifacts" : [
                        create_runtime_artifact(
                            artifact_name = param_name, 
                            step_name = step_name,
                            schema_title = schema_title)
                    ]
                }
            if  args[1] == types.type_annotations.InputAnnotation:
                input_type = args[0]
                schema_title = get_schema_title_for_type(input_type)
                input_artifacts[param_name] = {
                    "artifacts" : [
                        create_runtime_artifact(
                            artifact_name = param_name, 
                            step_name = step_name,
                            schema_title = schema_title)
                    ]
                }
        
    executor_input = {
        "inputs" : {
            "parameterValues" : parameter_values,
        }, 
        "outputs":  {
            "outputFile" : f"{LOCAL_DIR}/{step_name}/execution_output.json"
        }
    }
    if len(input_artifacts.keys()) > 0:
        executor_input['inputs']['artifacts'] = input_artifacts
    if len(output_artifacts.keys()) > 0:
        executor_input['outputs']['artifacts'] = output_artifacts
    return executor_input


def run_step(func, step_name, verbose = False):
    #
    # Assemble executor input
    #
    executor_input = build_executor_input_from_function(func, step_name)
    if verbose: 
        print(f"Using executor input: \n{executor_input}")
    #
    # Create executor 
    #    
    _executor = executor.Executor(
            executor_input = executor_input, 
            function_to_execute = func)


    output_file = _executor.execute()
    if verbose: 
        print(f"Execution of step {step_name} complete, output file has been written to {output_file}")

#
# Get arguments
#
args = get_args()
#
# Run steps of pipeline. After each step, copy output
# to the location where the next step expects it
#
run_step(pipeline_definition.create_data, "create_data", verbose = args.verbose)
shutil.copy(get_local_artifact_path("data", "create_data"),
            get_local_artifact_path("data", "train"))
run_step(pipeline_definition.train, "train", verbose = args.verbose)
