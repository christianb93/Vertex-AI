import os 
import argparse
import google.cloud.aiplatform as aip

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
parser.add_argument("--raw", 
                    action = "store_true",
                    default = False,
                    help = "Use raw predictions")
args = parser.parse_args()
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

prediction = endpoint.predict(
    instances = [[0.5, 0.35]]
)
if not args.raw:
    print("Making prediction:")
    print(f"Prediction: {prediction.predictions}")
    print(f"ModeL:      {prediction.model_resource_name}")
    print(f"Version:    {prediction.model_version_id}")
else:
    print("Making raw prediction:")
    raw_prediction = endpoint.raw_predict(
        body = b'{"instances" : [[0.5, 0.35]]}',
        headers = {"Content-Type": "application/json"},
    )
    print(f"Status:     {raw_prediction.status_code}")
    print(f"Prediction: {raw_prediction.json()['predictions']}")
    print(f"Model:      {raw_prediction.headers['X-Vertex-AI-Model']}")
    print(f"Version:    {raw_prediction.headers['X-Vertex-AI-Model-Version-Id']}")