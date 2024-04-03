from google.cloud.aiplatform_v1 import DatasetServiceClient, ListDatasetsRequest
import google.cloud.resourcemanager as grm
import os 

#
# Get a project number for a project ID, using a resource
# manager client
#
def get_project_number(project_id):
    grm_client = grm.ProjectsClient()
    project = grm_client.get_project(name = f"projects/{google_project_id}")
    return project.name.split("/")[-1]

#
# Get a dataset by display name. We return the first
# dataset with a matching name
#
def get_dataset(project_id, display_name):
    #
    # Get project number
    #
    project_number = get_project_number(google_project_id)

    #
    # Create low-level client. Note that the API endpoint needs to be 
    # specified, otherwise the request will fail
    # 
    client = DatasetServiceClient(client_options = {
        "api_endpoint": f"{google_region}-aiplatform.googleapis.com"
    })

    #
    # Create and submit request
    #
    request = ListDatasetsRequest(
        parent = f"projects/{project_number}/locations/{google_region}"
    )
    response = client.list_datasets(request = request)

    for ds in response:
        if ds.display_name == display_name:
            return ds
        
    return None

#
# Get project ID and location from environment 
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")

#
# Get dataset
#
ds = get_dataset(google_project_id, "my-dataset")
print(ds)