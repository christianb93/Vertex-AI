#!/bin/bash
TOKEN=$(gcloud auth print-access-token)
ENDPOINT="https://$GOOGLE_REGION-aiplatform.googleapis.com"
PARENT="projects/$GOOGLE_PROJECT_ID/locations/$GOOGLE_REGION"
curl \
  -H "Authorization: Bearer $TOKEN" \
   $ENDPOINT/v1/$PARENT/metadataStores/default/metadataSchemas