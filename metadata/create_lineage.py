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
aip.init(project = google_project_id, 
         location = google_region,
         experiment = "my-experiment")


#
# Start run
# 
with aip.start_run(run = "my-experiment-run") as experiment_run:
    with aip.start_execution(display_name = "my-execution",
                             schema_title = execution_schema.CustomJobExecution.schema_title) as execution:
        #
        # Create an artifact, maybe a model
        #
        model  = aip.metadata.artifact.Artifact.create(
            schema_title = artifact_schema.Model.schema_title,
            uri = f"gs://vertex-ai-{google_project_id}/models/my-models",
            display_name = "my-model",
            project = google_project_id,
            location = google_region
        )
        execution.assign_output_artifacts([model])


