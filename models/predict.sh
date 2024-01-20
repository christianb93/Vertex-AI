#!/bin/bash
ENDPOINT_ID=$(gcloud ai endpoints list \
  --filter="display_name=vertex-ai-endpoint" \
  --format="value(name)")
TOKEN=$(gcloud auth print-access-token)
BASE_URL="https://$GOOGLE_REGION-aiplatform.googleapis.com/v1"
ENDPOINT=$(gcloud ai endpoints describe \
  $ENDPOINT_ID \
  --format="value(name)")
URL=$BASE_URL/$ENDPOINT
echo "Using prediction endpoint $URL"
curl  \
    --header 'Content-Type: application/json'  \
    --header "Authorization: Bearer $TOKEN"  \
    --data '{ "instances" : [[0.5, 0.35]]}' \
   $URL:predict

