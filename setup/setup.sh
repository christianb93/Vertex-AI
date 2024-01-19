#!/bin/bash

#
# Create a bucket
#
gcloud storage buckets create \
    gs://vertex-ai-$GOOGLE_PROJECT_ID \
    --location=$GOOGLE_REGION 

#
# Create service accounts
#
gcloud iam service-accounts create \
    vertex-ai-run \
    --display-name=vertex-ai-run \
    --description="A service account that we will use to run jobs and endpoints"

gcloud iam service-accounts create \
    vertex-ai-build \
    --display-name=vertex-ai-build \
    --description="A service account that we will use to assemble and submit jobs"

#
# Grant the service accounts the necessary rights 
#
accounts=(
    vertex-ai-run
    vertex-ai-build
)
project_roles=(
    aiplatform.user
)
bucket_roles=(
    storage.objectAdmin
    storage.legacyBucketOwner
)
for account in ${accounts[@]}
do 
    sa="$account@$GOOGLE_PROJECT_ID.iam.gserviceaccount.com"
    bucket="gs://vertex-ai-$GOOGLE_PROJECT_ID"
    for role in ${project_roles[@]}
    do
        gcloud projects add-iam-policy-binding \
            $GOOGLE_PROJECT_ID \
            --member="serviceAccount:$sa" \
            --role="roles/$role"
    done
    for role in ${bucket_roles[@]}
    do
        gcloud storage buckets add-iam-policy-binding \
            $bucket \
            --member="serviceAccount:$sa" \
            --role="roles/$role"
    done
done 
#
# The build account needs the permission to use the run account
#
sa="vertex-ai-build@$GOOGLE_PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts add-iam-policy-binding \
        vertex-ai-run@$GOOGLE_PROJECT_ID.iam.gserviceaccount.com  \
        --member="serviceAccount:$sa" \
        --role="roles/iam.serviceAccountUser"
