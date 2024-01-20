import os
import google.cloud.aiplatform as aip

#
# Initialize client
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")
aip.init(project = google_project_id, location = google_region)

#
# Doing upload
#
registry = f"{google_region}-docker.pkg.dev"
repository = f"{google_project_id}/vertex-ai-docker-repo"
image = f"{registry}/{repository}/prediction:latest"
bucket = f"gs://vertex-ai-{google_project_id}"
model = aip.Model.upload(
    serving_container_image_uri = image,
    artifact_uri = f"{bucket}/models",
    model_id = "vertexaimodel",
    serving_container_predict_route = "/predictions/model",
    serving_container_health_route = "/ping",
    display_name = "my-model",
    project = google_project_id,
    location = google_region
)
print(model)