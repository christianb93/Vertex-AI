import google.cloud.aiplatform as aip 
import os

google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")

aip.init(project = google_project_id,
         location = google_region)

#
# Create a pipeline job from the 
# pipeline definition
#
pipeline_job = aip.PipelineJob(
    display_name = "my-pipeline",
    template_path = "my-pipeline.yaml",
    pipeline_root = f"gs://vertex-ai-{google_project_id}/pipeline_root",
    parameter_values = {
        "epochs" : 5000,
        "lr" : 0.05,
        "size" : 1000,
    },
    project = google_project_id,
    location = google_region
)

#
# Submit the job
#
service_account = f"vertex-ai-run@{google_project_id}.iam.gserviceaccount.com"
pipeline_job.submit(
    service_account = service_account
)