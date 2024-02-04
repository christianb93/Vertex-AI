#
# Run a component locally
#
import kfp
from kfp.dsl import executor
import pipeline_definition
import argparse
import os
import docker
import json
import pathlib
from dataclasses import dataclass
import time
import shutil


#
# This class holds step output artifacts
#
@dataclass
class StepOutput:
    outputs : dict()

#
# A simple component for testing this test driver
#
@kfp.dsl.component(
        base_image = "python:3.9"
)
def say_hello():
    print("Hello")
    

class ComponentRunner:
    """
    A simple test driver to run an invidual pipeline component. This class works by building an executor input
    structure that points to local data for a given component function and then uses the KFP executor to actually
    run it or runs a container. 

    """
    def __init__(self, pipeline_root = "pipeline_root", local_dir = "./gcs", no_container = False):
        """
        Initialize a component runner

        Args:
            local_dir :  the local directory under which inputs and outputs are placed, not including a trailing slash
            pipeline_root : the name of the subdirectory under this local dir where artifacts are created
            no_container : set this to True to run outside of a container
        """
        self.local_dir = local_dir
        self.pipeline_root = pipeline_root
        self._no_container = no_container

    def __enter__(self):
        #
        # Patch GCS prefix. When initializing the executor, an URI starting with
        # gs:// is turned into a path by replacing gs:// by this prefix. Usually this 
        # is /gcs, we overwrite this by our local directory
        #
        self._old_prefix = kfp.dsl.types.artifact_types._GCS_LOCAL_MOUNT_PREFIX
        kfp.dsl.types.artifact_types._GCS_LOCAL_MOUNT_PREFIX = f"{self.local_dir}/"
        return self
    
    def __exit__(self, exc_type, exc_value, exc_traceback):
        kfp.dsl.types.artifact_types._GCS_LOCAL_MOUNT_PREFIX = self._old_prefix
        return False

    def create_runtime_artifact(self, artifact_name, step_name, schema_title):
        """
        Create the part of an execution input JSON which specifies an individual artifact. Uusally the URI used for this is 
        gs://{pipeline_root}/{step_name}/{artifact_name}
    
        Args:
            artifact_name : the name of the artifact
            step_name : the name of the step, this will be used as part of the URI
            schema_title : schema title to use for this artifact
        """
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
            # types.artifact_types._GCS_LOCAL_MOUNT_PREFIX - this is what we patch in the __enter__ method
            #
            "uri" : f"gs://{self.pipeline_root}/{step_name}/{artifact_name}"
        }

    def get_param_type(self, param_spec):
        """
        Check whether an input or output is an artifact, a parameter and input or output. 
        At the time of writing at least this can be detected by checking whether the type is a schema definition 
        of the form <schema_title>@<schema_version>
        
        Args:
            param_spec : the parameter specifaction to inspect

        """
        is_input = isinstance (param_spec, kfp.dsl.structures.InputSpec)
        is_artifact = "@" in param_spec.type
        return is_input, is_artifact

    def build_executor_input_from_function(self, comp, step_name, **kwargs):
        """
        Assemble an executor input structure for a component, using the provided input mappings
        (see the comment for create_runtime_artifact). Input parameters will be taken from the kwargs

        Args:
            comp : the component for which we want to create the executor input, needs to be an instance of PythonComponent
            step_name : the step name
            kwargs : additional key word arguments used as inputs

        """
        inputs_and_outputs = { **(comp.component_spec.inputs or {}), **(comp.component_spec.outputs or {})}
        output_artifacts = {}
        input_artifacts = {}
        parameter_values = {}
        #
        # Go through inputs and outputs and add items to input_artifacts and parameter_values
        #
        for param_name, param_spec in inputs_and_outputs.items():
            is_input, is_artifact = self.get_param_type(param_spec)
            if not is_artifact:
                #
                # This is a parameter - we only handle input parameters
                # 
                if is_input:
                    #
                    # Check that input is contained in kwargs
                    #
                    assert param_name in kwargs, f"Parameter {param_name} not in parameter values"
                    #
                    # and take it from there
                    #
                    parameter_values[param_name] = kwargs[param_name]
            else:
                #
                # If the input is contained in the kwargs, take it from there
                #
                if param_name in kwargs and is_input:
                    input_artifacts[param_name] = kwargs[param_name]
                else:
                    #
                    # Need to build the structure ourselves. We can get the schema
                    # title and the schema version from the type
                    #
                    schema_title = param_spec.type.split("@")[0]
                    #
                    # Add an entry to the input artifacts dictionary. Each entry
                    # is a dictionary with the key artifacts. The value is a list
                    # (we only use one entry) and each item in the list is an actual
                    # artifact with name, metadata, schema and URI
                    #
                    run_artifact = {
                        "artifacts" : [
                            self.create_runtime_artifact(
                                artifact_name = param_name, 
                                step_name = step_name,
                                schema_title = schema_title)
                        ]
                    }
                    if is_input:
                        input_artifacts[param_name] = run_artifact
                    else:
                        output_artifacts[param_name] = run_artifact
            
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

    def run_step(self, comp, step_name, verbose = False,  key_json = None, **kwargs):
        """
        Run a step, using the provided kwargs and the provided input mappings. 
    
        We return a dataclass containing the output artifacts so that they can be used as input for the next
        step in a syntax similar to a pipeline definition, i.e.

        _first = run_step(...)
        _second = run_step(..., <argument name> = _first.outputs['<argument_name>'])

        Args:
            comp : the PythonComponent to run
            step_name : a step name (needs to be unique)
            verbose : set this to True to collect extra output
            kwargs : key word arguments that will be used as input parameters for the step      
            key_json : optional - full path of a service account key JSON file that we will use 
        
        """
        executor_input = self.build_executor_input_from_function(comp, step_name, **kwargs)
        if verbose: 
            print(f"Preparing step {step_name} - using executor input: \n{json.dumps(executor_input, indent = 4)}")
        #
        # Make sure that output directory exists
        # 
        if "artifacts" in executor_input['outputs']:
            output_dir = f"{self.local_dir}/{self.pipeline_root}/{step_name}"
            os.makedirs(output_dir, exist_ok = True)
        if self._no_container:
            #
            # Create executor 
            #    
            _executor = executor.Executor(
                    executor_input = executor_input, 
                    function_to_execute = comp)

            # 
            # Run it. The executor will use the executor input to 
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
            #
            # Figure out whether we have credentials
            #
            env = {}
            if key_json is not None:
                shutil.copy(key_json, f"{self.local_dir}/key.json")
                env["GOOGLE_APPLICATION_CREDENTIALS"] = f"/gcs/key.json"
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
                environment = env
            )
            for l in container.logs(stream = True):
                print(l.decode('utf-8'), end = "")
            container.remove()
        if "artifacts" in executor_input['outputs']:
            # TODO: also consider the data in the output file here to 
            # learn about parameter outputs and updated metadata
            return StepOutput(outputs = executor_input['outputs']['artifacts'] )
        else:
            return StepOutput(outputs = {})
        
            

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
    parser.add_argument("--experiment", 
                        type = str,
                        default = None,
                        help = "Experiment to use")
    parser.add_argument("--key_json", 
                        type = str,
                        default = None,
                        help = "JSON service account key")
    return parser.parse_args()

#
# Get arguments
#
args = get_args()
#
# Get Google project ID and region from enironment
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")
#
# Make sure that local ./gcs directory exists before we run a container
# otherwise this will be added with owner root and we have a permission issue
#
os.makedirs("./gcs", exist_ok = True)
#
# Create runner
#
with ComponentRunner(no_container = args.no_container) as runner:
    #
    # Be nice and say hello first
    # 
    runner.run_step(comp = say_hello,
                    step_name = "say_hello",
                    verbose = args.verbose)
    #
    # Run the first step of our pipeline
    #
    _create_data = runner.run_step(comp = pipeline_definition.create_data, 
            step_name = "create_data", 
            verbose = args.verbose,
            size = 1000)

    #
    # Run step "train", using the artifact "data"
    # from step "create_data" as input for the parameter "data"
    #
    timestamp = time.strftime("%Y%m%d%H%M%S",time.localtime())
    _train = runner.run_step(comp = pipeline_definition.train, 
            step_name = "train",
            key_json = args.key_json,
            data = _create_data.outputs['training_data'],
            verbose = args.verbose,
            epochs = 1000,
            lr = 0.05, 
            job_name = f"my-run-{timestamp}",
            google_project_id = google_project_id,
            google_region = google_region, 
            experiment_name = args.experiment,
)
    #
    # Similarly run step evaluate
    #
    runner.run_step(comp = pipeline_definition.evaluate, 
            step_name = "evaluate",
            trained_model = _train.outputs['trained_model'],
            validation_data = _create_data.outputs['validation_data'])
