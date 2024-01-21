import os
import time
import google.cloud.aiplatform as aip
from google.cloud import storage


import argparse 
import tempfile 
import shutil
import re

#
# Initialize client
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")
aip.init(project = google_project_id, location = google_region)

#
# Get parameters
#
parser = argparse.ArgumentParser()
parser.add_argument("--submit", 
                    default = False,
                    action = "store_true",
                    help = "Submit job after creation")
parser.add_argument("--local_run", 
                    default = False,
                    action = "store_true",
                    help = "Run job locally")
args = parser.parse_args()

#
# Assemble URI for staging bucket and container
#
staging_bucket = f"vertex-ai-{google_project_id}"
registry = f"{google_region}-docker.pkg.dev/{google_project_id}"
repository = f"{registry}/vertex-ai-docker-repo"
image = f"{repository}/base"
timestamp = time.strftime("%Y%m%d%H%M%S",time.localtime())

#
# Create the job
#
job = aip.CustomJob.from_local_script(
        display_name = "my-job",
        script_path = "train.py",
        container_uri = image,
        machine_type  = "n1-standard-4",
        base_output_dir = f"gs://{staging_bucket}/job_output/{timestamp}",
        project = google_project_id,
        location = google_region,
        staging_bucket = staging_bucket
)
print("Machine specification:\n-------------------------\n")
print(job.job_spec.worker_pool_specs[0].machine_spec)
print("Container specification:\n-------------------------\n")
print(job.job_spec.worker_pool_specs[0].container_spec)

#
# Submit if requested
#
if args.submit:
    service_account = f"vertex-ai-run@{google_project_id}.iam.gserviceaccount.com"
    job.submit(
        service_account = service_account
    )

elif args.local_run:
    #
    # Run container locally. This assumes that a suitable service
    # account key is present as key.json in the current working directory
    #
    with tempfile.TemporaryDirectory() as tmpdir:
        print(f"Using temporary directory {tmpdir}")
        print(f"Using base image {image}")
        env = {
            "AIP_MODEL_DIR" : f"gs://{staging_bucket}/job_output/{timestamp}/model"
        }
        try: 
            os.stat("./key.json")
        except FileNotFoundError:            
            print("Please make sure that the JSON secret key is located in a file key.json in the local directory")
            exit(1)
        #
        # Extract location of package from cmd
        #
        cmd = " ".join(job.job_spec.worker_pool_specs[0].container_spec.command)
        pattern = f"/gcs/{staging_bucket}/\S*"
        print(f"Pattern: {pattern}")
        print(f"cmd: {cmd}")
        local_package_path = re.search(pattern, cmd).group()
        package_uri = local_package_path.replace("/gcs/", "gs://")
        print(f"Using package at {package_uri}")
        #
        # Download package
        #
        gcs_client = storage.Client()
        with open(f"{tmpdir}/package.tgz", "wb") as file:
            blob = gcs_client.download_blob_to_file(package_uri, file)
        #
        # Replace GCS path in command by local path
        #
        cmd = cmd.replace(local_package_path, "/scriptdir/package.tgz")
        #
        # Split command into entrypoint and actual command. Note that
        # according to this page 
        # https://cloud.google.com/vertex-ai/docs/training/configure-container-settings#create_custom_job_custom_container-python_vertex_ai_sdk
        # what is called command in the job specs is really the entrypoint. However, the docker CLI does not allow us to combine
        # executable and args into the entrypoint argument, so we need to split this into
        # the actual entrypoint ("sh"), the first argument ("-c") and the remaining arguments which we escape
        #
        entrypoint = cmd.split(" ")[0]
        flag = cmd.split(" ")[1]
        command = " ".join(cmd.split(" ")[2:])
        #
        # Run container, mapping temporary directory
        #
        docker_args = [
            f"--name=job-test",
            f"-it",
            f"--rm",
            f"--entrypoint {entrypoint}",
            f"-v {tmpdir}:/scriptdir",
            " ".join([f"-e {e}={env[e]}" for e in env.keys()]),
            "-v ./:/keys",
            "-e GOOGLE_APPLICATION_CREDENTIALS=/keys/key.json"
        ]
        docker_cmd = f"docker run  {' '.join(docker_args)}  {image} {flag} '{command}'" 
        print(f"Using docker command: \n{docker_cmd}")
        print(os.system(docker_cmd))
