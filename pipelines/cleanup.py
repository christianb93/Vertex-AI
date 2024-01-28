import google.cloud.aiplatform as aip
import argparse
import datetime
import os 
import time

#
# Initialize API
# 
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
location = os.environ.get("GOOGLE_REGION")

aip.init(project = google_project_id, location = location) 

# 
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--retention_days", 
                    type = int, 
                    default = 30,
                    help = "Number of days you want to retain")
    args=parser.parse_args()
    return args

args = get_args()
today = datetime.datetime.now(datetime.timezone.utc)
cut_off = today - datetime.timedelta(days = args.retention_days)


print(f"Cleaning up all pipeline jobs created before {cut_off}")
date_filter = f"create_time<\"{cut_off.isoformat()}\""
pipelines = aip.PipelineJob.list(filter = date_filter)
for p in pipelines:
    time.sleep(1.5) # to avoid rate limiting issues
    p.delete()

#
# Delete all artifacts which are older than retention_days
#
print(f"Cleaning up all artifacts created before {cut_off}")
artifacts = aip.Artifact.list(filter = date_filter)
for a in artifacts:
    time.sleep(1.5)
    a.delete()

print(f"Cleaning up all executions created before {cut_off}")
executions = aip.Execution.list(filter = date_filter)
for e in executions:
    time.sleep(1.5)
    e.delete()

print(f"Cleaning up all contexts created before {cut_off}")
contexts = aip.Context.list(filter = date_filter)
for c in contexts:
    time.sleep(1.5)
    c.delete()

print(f"Cleaning up all custom jobs created before {cut_off}")
jobs = aip.CustomJob.list(filter = date_filter)
for j in jobs:
    time.sleep(1.5)
    j.delete()

