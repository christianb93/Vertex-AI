import os
from google.cloud import storage

#
# The model location that Google will give us is without the actual file name
#
base_uri = os.environ.get("AIP_STORAGE_URI")
uri = f"{base_uri}/model.mar"
print(f"Base URI as provided: {base_uri}")
print(f"Will use blob at:     {uri}")
gcs_client = storage.Client()
with open("model.mar", "wb") as file:
    blob = gcs_client.download_blob_to_file(uri, file)
  
