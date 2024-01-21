import os
import google.cloud.aiplatform as aip  
import argparse

#
# Get arguments
#
def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--delete",
                        default = False,
                        action = "store_true",
                        help = "Delete metadata items instead of only listing them")

    parser.add_argument("--verbose",
                        default = False,
                        action = "store_true",
                        help = "Print metadata")
    return  parser.parse_args()

#
# Handle an item
#
def handle_item(item, category, delete =  False, verbose = False):
    print(f"Found {category} {item.display_name} / {item.name} / {item.schema_title}")
    if verbose:
        print(f"   Metadata: {item.metadata}")
        if isinstance(item, aip.Context):
            for execution in item.get_executions():
                print(f"   Execution {execution.display_name}")
            for parent in item.parent_contexts:
                print(f"   Parent {parent}")
        if isinstance(item, aip.Execution):
            for artifact in item.get_output_artifacts():
                print(f"   Artifact {artifact.display_name} is output of this execution")
            for artifact in item.get_input_artifacts():
                print(f"   Artifact {artifact.display_name} is input of this execution")
    if delete:
        print("Deleting")
        item.delete()

#
# Initialize client
#
google_project_id = os.environ.get("GOOGLE_PROJECT_ID")
google_region = os.environ.get("GOOGLE_REGION")
aip.init(project = google_project_id, location = google_region)

args = get_args()

#
# First list all artifacts
#
for artifact in aip.Artifact.list():
    handle_item(artifact, "artifact", args.delete, args.verbose)
#
# Next all executions
#
for execution in aip.Execution.list():
    handle_item(execution, "execution", args.delete, args.verbose)

#
# And all contexts
#
contexts = aip.Context.list()
for context in contexts:
    handle_item(context, "context", args.delete, args.verbose)

