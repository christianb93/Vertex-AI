import os
import argparse
import google.cloud.aiplatform as aip
import google.cloud.resourcemanager_v3 as grm

#
# Initialize client
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")
aip.init(project = google_project_id, location = google_region)

#
# Get arguments
#
parser = argparse.ArgumentParser()
parser.add_argument("--split",
           default = 100,
           type = int,
           help = "The percentage of traffic that we route to this instance")
args = parser.parse_args()

#
# Check whether our endpoint exists and if not, 
# create it
#
endpoints = aip.Endpoint.list(
    filter='display_name="vertex-ai-endpoint"'
)

if len(endpoints) == 0:
    print("Endpoint does not seem to exist yet, creating it")
    endpoint = aip.Endpoint.create(
        display_name = "vertex-ai-endpoint",
        project = google_project_id, 
        location = google_region
    )
else:
    if len(endpoints) > 1:
        print("WARNING: more than one endpoint with the name vertex-ai-endpoint, picking first one")
    endpoint = endpoints[0]

assert endpoint is not None, "Something went wrong, do not have a valid endpoint"


print(f"Using endpoint with ID {endpoint.name} ({endpoint.resource_name})")

#
# Get our model. We need the project number for that purpose
#
projects_client = grm.ProjectsClient()
projects = projects_client.search_projects(
    query=f"id={google_project_id}"
)
projects = [p for p in projects]
if 0 == len(projects):
    print(f"Could not find a project with ID  {google_project_id}")
    exit(1)
project = projects[0]
if len(projects) > 1:
    print(f"WARNING: found more than one project with project ID {google_project_id}, using first one")
model_prefix = f"{project.name}/locations/{google_region}/models/"
model_name = f"{model_prefix}vertexaimodel"
model = aip.Model(
    model_name = model_name
)
print(f"Deploying model {model.name} with version {model.version_id}, using traffic split {args.split}")
#
# Deploy
#
service_account = f"vertex-ai-run@{google_project_id}.iam.gserviceaccount.com"
endpoint.deploy(
    model = model,
    traffic_percentage = args.split,
    machine_type = "n1-standard-2",
    min_replica_count = 1,
    max_replica_count = 1,
    service_account = service_account
)

