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
        #
        # Log something
        #
        aip.log_params({
            "lr" : 0.01,
            "epochs" : 1000
        })
        aip.log_metrics({
            'accuracy': 0.95, 
            'validation_loss': 0.14
        })
        for i in range(20):
            aip.log_time_series_metrics({
                "loss" : 100 - i*i*0.001
            }, step = i)


#
# Get logged data from experiment run
#
experiment_run = aip.ExperimentRun(
    run_name = "my-experiment-run",
    experiment = "my-experiment")
parameters = experiment_run.get_params()
metrics = experiment_run.get_metrics()

print(f"Logged parameters: {parameters}")
print(f"Logged metrics:    {metrics}")