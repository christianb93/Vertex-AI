import google.cloud.aiplatform as aip 
import time
import os

#
# Get project ID and location from environment
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")

#
# Assemble experiment run name
#
EXPERIMENT = "my-experiment"
timestamp = time.strftime("%Y%m%d%H%M%S", time.localtime())
aip.init(project = google_project_id,
         location = google_region,
         experiment = EXPERIMENT)
#
# Assemble URI for staging bucket and container
#
staging_bucket = f"vertex-ai-{google_project_id}"
registry = f"{google_region}-docker.pkg.dev/{google_project_id}"
repository = f"{registry}/vertex-ai-docker-repo"
image = f"{repository}/base"

#
# Start the run. Naming is a bit tricky at this point:
# - the method start_run expects a run name which is supposed to be unique
#   within the experiment
# - from this, a run ID is built which is the concatentation of experiment 
#   name and run name
# - the resulting context will have this as resource ID and the run name as display name
#
run_name = f"run-{timestamp}"
print(f"Using run_name {run_name}")
with aip.start_run(run_name) as experiment_run:
    print(f"Experiment resource ID: {experiment_run.resource_id}")
    job = aip.CustomJob.from_local_script(
        display_name = "my-job",
        script_path = "train.py",
        container_uri = image,
        machine_type  = "n1-standard-4",
        base_output_dir = f"gs://{staging_bucket}/job_output/{timestamp}",
        project = google_project_id,
        location = google_region,
        staging_bucket = staging_bucket,
        environment_variables = {
            "GOOGLE_PROJECT_ID" : google_project_id,
            "GOOGLE_REGION" : google_region
        }
    )
    service_account = f"vertex-ai-run@{google_project_id}.iam.gserviceaccount.com"
    job.run(
        service_account = service_account,
        experiment = EXPERIMENT, 
        experiment_run = run_name
    )
