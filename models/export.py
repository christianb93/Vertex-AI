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
print(f"Exporting model {model.name}")
print("This model supports the following export formats:")
print(model.supported_export_formats)
#
# Do the actual export
#
export = model.export_model(
            export_format_id = "custom-trained",
            artifact_destination = f"gs://vertex-ai-{google_project_id}/exports",
            image_destination = f"{google_region}-docker.pkg.dev/{google_project_id}/vertex-ai-docker-repo/export:latest"
)
print(export)
