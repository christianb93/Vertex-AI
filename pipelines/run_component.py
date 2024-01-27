#
# Run a component locally
#
from kfp.dsl import executor
from kfp.dsl import types
import pipeline_definition

LOCAL_DIR = "./gcs"

#
# Set up executor input structure
#

executor_input = {  
    "inputs" : {
        "parameterValues" : {
            "epochs" : 500,
            "google_project_id" : "my-project",
            "google_region" : "us-east1"
        },
    },
    "outputs" :  {
        "artifacts" : {
            "model" : {
                "artifacts" : [
                    #
                    # This dictionary represents a runtime artifact,
                    # i.e. an instance of one of the classes in dsl.types.artifact_types
                    # At runtime, the schema title is used to identify the correct class
                    #
                    {
                        "name" : "my-model",    
                        "metadata" : {},
                        "type": {
                            "schemaTitle" : "system.Model"
                        },  
                        #
                        # The URI will be used to determine the local path at runtime. For a GCS bucket,
                        # the gs:// prefix will be replaced by /gcs or more precisely by the value of
                        # types.artifact_types._GCS_LOCAL_MOUNT_PREFIX
                        #
                        "uri" : "gs://vertex-ai/pipeline_root/model.bin"
                    }
                ]
            }
        },
        "outputFile" : f"{LOCAL_DIR}/out.json"
        },
    }

#
# Patch GCS prefix. When initializing the executor, an URI starting with
# gs:// is turned into a path by replacing gs:// by this prefix. Usually this 
# is /gcs, we overwrite this by our local directory
#
types.artifact_types._GCS_LOCAL_MOUNT_PREFIX = LOCAL_DIR

#
# Create executor 
#    
_executor = executor.Executor(
        executor_input = executor_input, 
        function_to_execute = pipeline_definition.train)

#
# Inspect output artifacts
# 
for name, artifact in _executor.output_artifacts.items():
    print(f"Output artifact {name} at path {artifact.path}")

output_file = _executor.execute()
print(f"Execution complete, output file has been written to {output_file}")