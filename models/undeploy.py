import os 
import google.cloud.aiplatform as aip
import google.cloud.resourcemanager_v3 as grm

#
# Initialize client
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")
aip.init(project = google_project_id, location = google_region)


#
# Get endpoint
#
endpoints = aip.Endpoint.list(
    filter='display_name="vertex-ai-endpoint"'
)

if len(endpoints) == 0:
    print("Endpoint does not seem to exist")
    exit(1)
else:
    if len(endpoints) > 1:
        print("WARNING: more than one endpoint with the name vertex-ai-endpoint, picking first one")
    endpoint = endpoints[0]

assert endpoint is not None, "Something went wrong, do not have a valid endpoint"


print(f"Using endpoint with ID {endpoint.name} ({endpoint.resource_name})")

#
# Get all deployed models
#
for m in endpoint.list_models():
    print(f"Undeploying deployed model {m.id}")
    endpoint.undeploy(deployed_model_id = m.id)

#
# Finally delete endpoint
#
endpoint.delete()