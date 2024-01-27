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
import os
import docker
import json
import pathlib

#
# A simple test driver to run an invidual pipeline component. This class works by building an executor input
# structure that points to local data for a given component function and then uses the KFP executor to actually
# run it or runs a container. 
# Currently, this only supports a subset of possible signatures - specifically we support only simple 
# annotations like Output[Model] or int, but no lists as outputs and no function outputs (i.e. output parameters)
#
class ComponentRunner:

    #
    # local_dir = the local directory under which inputs and outputs are placed, not including
    #             a trailing slash
    # pipeline_root = the name of the subdirectory under this local dir where artifacts
    # are created
    #
    def __init__(self, pipeline_root = "pipeline_root", local_dir = "./gcs"):
        self.local_dir = local_dir
        self.pipeline_root = pipeline_root
        #
        # Patch GCS prefix. When initializing the executor, an URI starting with
        # gs:// is turned into a path by replacing gs:// by this prefix. Usually this 
        # is /gcs, we overwrite this by our local directory
        #
        types.artifact_types._GCS_LOCAL_MOUNT_PREFIX = f"{self.local_dir}/"

    #
    # Define the local path for an input or output artifact of a given step
    # 
    def get_local_artifact_path(self, artifact_name, step_name):
        output_dir = f"{self.local_dir}/{self.pipeline_root}/{step_name}"
        if artifact_name is None:
            return output_dir
        return f"{output_dir}/{artifact_name}"

    #
    # Create the part of an execution input JSON which specifies an individual artifact. Uusally
    # the URI used for this is 
    # gs://{pipeline_root}/{step_name}/{artifact_name}
    # The input_mappings parameter can be used to let the URI point to an output from a 
    # different step, and is a mapping whose keys are the names of the artifacts. If, for instance, 
    # there is an entry
    # "artifact_name" : {
    #                      "from_step" : "train",
    #                      "from_artifact" : "model"
    #                   }
    # then the URI used for the artifact (usually an input artifact) "artifact_name" will be
    # gs://{pipeline_root}/train/model
    # so that we read from the output artifact model of the step train 
    # 
    def create_runtime_artifact(self, artifact_name, step_name, schema_title, input_mappings = None):
        #
        # See whether the artifact name shows up in input_mapping and if yes,
        # use that step and artifact name for the URI so that we use the output
        # of that step as input artifact
        #
        uri_step_name = step_name
        uri_artifact_name = artifact_name    
        if input_mappings is not None:
            if artifact_name in input_mappings:
                uri_step_name = input_mappings[artifact_name]['from_step']
                uri_artifact_name = input_mappings[artifact_name]['from_artifact']
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
            # the KFP executor will replace gs:// prefix  by /gcs or more precisely by the value of
            # types.artifact_types._GCS_LOCAL_MOUNT_PREFIX - as we have patched this in the constructor
            # this should point into our local directory tree
            #
            "uri" : f"gs://{self.pipeline_root}/{uri_step_name}/{uri_artifact_name}"
        }

    #
    # Get a schema title for a class
    #
    def get_schema_title_for_type(self, cls):
        return cls.schema_title     

    #
    # Assemble an executor input structure for a component, using the provided input mappings
    # (see the comment for create_runtime_artifact)
    # Input parameters will be taken from the kwargs
    #
    def build_executor_input_from_function(self, comp, step_name, input_mappings = None, **kwargs):
        #
        # Strip off Python function and get its signature
        #
        python_func = comp.python_func 
        signature = inspect.signature(python_func)
        output_artifacts = {}
        input_artifacts = {}
        parameter_values = {}
        #
        # Go through parameters and add data to input_artifacts and output_artifacts
        # or to parameter_values
        #
        for _, param in signature.parameters.items():
            param_type = param.annotation
            param_name = param.name 
            if param_type == str or param_type == int or param_type == float:
                #
                # Check that input is contained in kwargs
                #
                assert param_name in kwargs, f"Parameter {param_name} not in parameter values"
                #
                # and take it from there
                #
                parameter_values[param_name] = kwargs[param_name]
            if typing.get_origin(param_type) == typing.Annotated:
                #
                # This is an annotation like Output[Model]. Check whether it is input
                # or output. We ignore more complex patterns like lists and so forth
                # and only suppor what the KFP documentation calls the traditional style
                #
                args = typing.get_args(param_type)
                if  args[1] == types.type_annotations.OutputAnnotation:
                    #
                    # Get output type, for instance Model
                    # 
                    output_type = args[0]
                    schema_title = self.get_schema_title_for_type(output_type)
                    #
                    # Add an entry to the output artifacts dictionary. Each entry
                    # is a dictionary with the key artifacts. The value is a list
                    # (we only use one entry) and each item in the list is an actual
                    # artifact with name, metadata, schema and URI
                    #
                    output_artifacts[param_name] = {
                        "artifacts" : [
                            self.create_runtime_artifact(
                                artifact_name = param_name, 
                                step_name = step_name,
                                schema_title = schema_title)
                        ]
                    }
                if  args[1] == types.type_annotations.InputAnnotation:
                    #
                    # Same for input
                    #
                    input_type = args[0]
                    schema_title = self.get_schema_title_for_type(input_type)
                    input_artifacts[param_name] = {
                        "artifacts" : [
                            self.create_runtime_artifact(
                                artifact_name = param_name, 
                                step_name = step_name,
                                schema_title = schema_title,
                                input_mappings = input_mappings)
                        ]
                    }
        
        #
        # Assemble the executor input structure. There are two sections that will later
        # be used by the executor:
        # 
        # inputs: contains all inputs. This can be parameter values but also input artifacts
        # outputs: contains all outputs. In addition, there is a key outputFile which is the
        #          local path to which the executor output is written
        #
        executor_input = {
            "inputs" : {
                "parameterValues" : parameter_values,
            }, 
            "outputs":  {
                "outputFile" : f"{self.local_dir}/{step_name}/execution_output.json"
            }
        }
        if len(input_artifacts.keys()) > 0:
            executor_input['inputs']['artifacts'] = input_artifacts
        if len(output_artifacts.keys()) > 0:
            executor_input['outputs']['artifacts'] = output_artifacts
        return executor_input

    #
    # Run a step, using the provided kwargs and the provided input mappings. If no_container
    # is True, no docker container will be launched but the code is executed locally in a separate
    # executor
    #
    def run_step(self, comp, step_name, verbose = False, input_mappings = None, no_container = False, **kwargs):
        #
        # Assemble executor input
        #
        executor_input = self.build_executor_input_from_function(comp, step_name, input_mappings = input_mappings, **kwargs)
        if verbose: 
            print(f"Preparing step {step_name} - using executor input: \n{json.dumps(executor_input, indent = 4)}")
        #
        # Make sure that output directory exists
        # 
        if "artifacts" in executor_input['outputs']:
            output_dir = self.get_local_artifact_path(step_name = step_name, artifact_name = None)
            os.makedirs(output_dir, exist_ok = True)
        if no_container:
            #
            # Create executor 
            #    
            _executor = executor.Executor(
                    executor_input = executor_input, 
                    function_to_execute = comp)


            #
            # Actually run it. The executor will use the executor input to 
            # instantiate input and output artifacts, model etc. and then
            # invoke the actual function with these inputs
            #
            output_file = _executor.execute()
            if verbose: 
                print(f"Execution of step {step_name} complete, output file has been written to {output_file}")
        else:
            #
            # Run our component in a docker container
            #
            image = comp.component_spec.implementation.container.image
            command = comp.component_spec.implementation.container.command
            if verbose:
                print(f"Command: {command}")
            args = [
                "--executor_input",
                json.dumps(executor_input),
                "--function_to_execute",
                step_name
            ]
            docker_client = docker.from_env()
            container = docker_client.containers.run(
                image = image,
                entrypoint = command,
                command = args,
                volumes = [
                    f"{pathlib.Path(self.local_dir).resolve()}:/gcs",
                ],
                stderr = True,
                stdout = True,
                detach = True,
            )
            for l in container.logs(stream = True):
                print(l.decode('utf-8'), end = "")
            container.remove()
            

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", 
                        action = "store_true",
                        default = False,
                        help = "Generate a bit more output")
    parser.add_argument("--no_container", 
                        action = "store_true",
                        default = False,
                        help = "Do not run in container")
    return parser.parse_args()

#
# Get arguments
#
args = get_args()
#
# Create runner
#
runner = ComponentRunner()
#
# Run the first step of our pipeline
#
runner.run_step(comp = pipeline_definition.create_data, 
         step_name = "create_data", 
         verbose = args.verbose,
         training_items = 1000,
         no_container = args.no_container)
#
# Run step "train", using the artifact "data"
# from step "create_data" as input for the parameter "data"
#
runner.run_step(comp = pipeline_definition.train, 
         step_name = "train",
         input_mappings = {
             "data" : {
                 "from_step" : "create_data",
                 "from_artifact" : "data"
             }
         }, 
         verbose = args.verbose,
         google_project_id = os.environ.get("GOOGLE_PROJECT_ID"),
         google_region = os.environ.get("GOOGLE_REGION"),
         epochs = 1000,
         lr = 0.05,
         no_container = args.no_container
         )
#
# Similarly run step evaluate
#
runner.run_step(comp = pipeline_definition.evaluate, 
         step_name = "evaluate",
         input_mappings = {
             "trained_model" : {
                 "from_step" : "train",
                 "from_artifact" : "trained_model"
             }
         }, 
         verbose = args.verbose,
         trials = 100, 
         no_container = args.no_container)
