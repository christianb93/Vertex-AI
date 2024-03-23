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
# Determine project number from project id
#
client = grm.ProjectsClient()
project = client.get_project(name = f"projects/{google_project_id}")
project_number = project.name.split("/")[-1]

#
# Get arguments
#
parser = argparse.ArgumentParser()
parser.add_argument("--split",
           default = 100,
           type = int,
           help = "The percentage of traffic that we route to this instance")
parser.add_argument("--vpc",
           type = str,
           help = "The name of the VPC to which we want to connect")
args = parser.parse_args()

#
# Check whether our endpoint exists and if not, 
# create it
#
endpoints = aip.PrivateEndpoint.list(
    filter = 'display_name="vertex-ai-private-endpoint"'
)

if len(endpoints) == 0:
    print("Endpoint does not seem to exist yet, creating it")
    endpoint = aip.PrivateEndpoint.create(
        display_name = "vertex-ai-private-endpoint",
        project = google_project_id, 
        location = google_region,
        network = f"projects/{project_number}/global/networks/{args.vpc}"
    )
else:
    if len(endpoints) > 1:
        print("WARNING: more than one endpoint with the name vertex-ai-endpoint, picking first one")
    endpoint = endpoints[0]

assert endpoint is not None, "Something went wrong, do not have a valid endpoint"


print(f"Using endpoint with ID {endpoint.name} ({endpoint.resource_name})")

model_prefix = f"{project.name}/locations/{google_region}/models/"
model_name = f"{model_prefix}vertexaimodel"
model = aip.Model(
    model_name = model_name
)
print(f"Deploying model {model.name} with version {model.version_id}")
#
# Deploy
#
service_account = f"vertex-ai-run@{google_project_id}.iam.gserviceaccount.com"
endpoint.deploy(
    model = model,
    machine_type = "n1-standard-2",
    min_replica_count = 1,
    max_replica_count = 1,
    service_account = service_account
)

    