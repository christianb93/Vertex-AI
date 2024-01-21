import os
import google.cloud.aiplatform as aip  
import google.cloud.aiplatform.metadata.schema.system.artifact_schema as artifact_schema
import google.cloud.aiplatform.metadata.schema.system.context_schema as context_schema
import google.cloud.aiplatform.metadata.schema.system.execution_schema as execution_schema 

#
# Initialize client
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")
aip.init(project = google_project_id, location = google_region)


#
# Create an artifact
#
artifact = aip.Artifact.create(
    schema_title = artifact_schema.Artifact.schema_title,
    uri = f"gs://vertex-ai-{google_project_id}/artifacts/my-artifact",
    display_name = "my-artifact",
    project = google_project_id,
    location = google_region
)
print(artifact)

#
# Create an execution 
#
with aip.start_execution(display_name = "my-execution", 
                       schema_title = execution_schema.ContainerExecution.schema_title) as execution:
    print(execution)
    execution.assign_output_artifacts([artifact])    

#
# Create a context for an experiment
#
experiment = aip.Context.create(
    schema_title = context_schema.Experiment.schema_title,
    display_name = "my-experiment",
    project = google_project_id,
    location = google_region
)
print(experiment)
print(type(experiment))

