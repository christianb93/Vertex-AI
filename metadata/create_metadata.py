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
artifact = aip.metadata.artifact.Artifact.create(
    schema_title = artifact_schema.Artifact.schema_title,
    uri = f"gs://vertex-ai-{google_project_id}/artifacts/my-artifact",
    display_name = "my-artifact",
    project = google_project_id,
    location = google_region
)
print(artifact)

#
# Create a context 
#
context = aip.Context.create(
    schema_title = context_schema.ExperimentRun.schema_title,
    display_name = "my-experiment-run",
    project = google_project_id,
    location = google_region
)
print(context)



#
# Create an execution. For some reason, I get a gRPC error if I do not
# explicitly set the credentials to None 
#
execution = aip.metadata.execution.Execution.create(
    display_name = "my-execution",
    schema_title = execution_schema.CustomJobExecution.schema_title,
    project = google_project_id, 
    location = google_region,
    credentials = None
)
print(execution)
#
# Assign artifact to execution
#
execution.assign_output_artifacts([artifact])    
#
# Assign execution to context
#
context.add_artifacts_and_executions(
    execution_resource_names = [execution.resource_name]
)
print(context)

#
# Finally create a parent context. To be displayed in the Experiment tab of the
# console, the metadata needs to contain the "experiment_deleted" property
#
parent_context = aip.metadata.context.Context.create(
    schema_title = context_schema.Experiment.schema_title,
    display_name = "my-experiment",
    project = google_project_id,
    location = google_region,
    metadata = {"experiment_deleted": False}
)
print(parent_context)
#
# And associate with child context
#
parent_context.add_context_children([context])

    
