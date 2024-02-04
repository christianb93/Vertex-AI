import google.cloud.aiplatform as aip
import google.cloud.aiplatform_v1 as aip_v1
import google.cloud.resourcemanager_v3 as grm

import argparse
import datetime
import os 
import time

#
# Get project number
#
def get_project_number(google_project_id):
    projects_client = grm.ProjectsClient()
    projects = projects_client.search_projects(
        query=f"id={google_project_id}"
    )
    projects = [p for p in projects]
    if 0 == len(projects):
        return None
    project = projects[0]
    if len(projects) > 1:
        print(f"WARNING: found more than one project with project ID {google_project_id}, using first one")
    return project.name.split("/")[-1]

# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retention_days", 
                    type = int, 
                    default = 30,
                    help = "Number of days you want to retain")
    parser.add_argument("--archive",
                    type = str,
                    default = None,
                    help = "A file name to which archived lineage graphs will be written")
    args=parser.parse_args()
    return args


#
# Initialize API
# 
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")

aip.init(project = google_project_id, location = google_region) 


args = get_args()
today = datetime.datetime.now(datetime.timezone.utc)
cut_off = today - datetime.timedelta(days = args.retention_days)
date_filter = f"create_time<\"{cut_off.isoformat()}\""

#
# If archiving is requested, go through all contexts older than the 
# cut-off and add their lineage graph to the archive
#
if args.archive is not None:
    with open(args.archive, "w+") as archive:
        contexts = aip.Context.list(filter = date_filter)
        for c in contexts:
            time.sleep(1)
            lineage = c.query_lineage_subgraph()
            archive.write(f"Context {c.resource_name}\n--------------\nMetadata: {c.metadata}\nLineage: \n{str(lineage)}\n")
            

#
# Create client
#
client = aip_v1.MetadataServiceClient(client_options = {
    "api_endpoint": f"{google_region}-aiplatform.googleapis.com"
})

#
# Determine Google project number
#
project_number = get_project_number(google_project_id)
if project_number is None:
    print(f"Could not get project number for project {google_project_id}")
    exit(1)
parent = f"projects/{project_number}/locations/{google_region}/metadataStores/default"

print(f"Cleaning up all pipeline jobs created before {cut_off}")
pipelines = aip.PipelineJob.list(filter = date_filter)
for p in pipelines:
    time.sleep(1.5) # to avoid rate limiting issues
    p.delete()

#
# Delete all artifacts which are older than retention_days
#
print(f"Cleaning up all artifacts created before {cut_off}")
op = client.purge_artifacts(request = aip_v1.PurgeArtifactsRequest(
    parent = parent,
    filter = date_filter,
    force = True
))
op.result()

print(f"Cleaning up all executions created before {cut_off}")
op = client.purge_executions(request = aip_v1.PurgeExecutionsRequest(
    parent = parent,
    filter = date_filter,
    force = True,
))
op.result()

print(f"Cleaning up all contexts created before {cut_off}")
op = client.purge_contexts(request = aip_v1.PurgeContextsRequest(
    parent = parent,
    filter = date_filter,
    force = True
))
op.result()

print(f"Cleaning up all custom jobs created before {cut_off}")
jobs = aip.CustomJob.list(filter = date_filter)
for j in jobs:
    time.sleep(1.5)
    j.delete()

