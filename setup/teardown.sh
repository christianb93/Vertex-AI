#!/bin/bash

#
# Delete bucket again
#
gcloud storage buckets delete \
    gs://vertex-ai-$GOOGLE_PROJECT_ID


#
# Delete associated roles
#
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
        gcloud projects remove-iam-policy-binding \
            $GOOGLE_PROJECT_ID \
            --member="serviceAccount:$sa" \
            --role="roles/$role"
    done
    for role in ${bucket_roles[@]}
    do
        gcloud storage buckets remove-iam-policy-binding \
            $bucket \
            --member="serviceAccount:$sa" \
            --role="roles/$role"
    done
done 
sa="vertex-ai-build@$GOOGLE_PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts remove-iam-policy-binding \
        vertex-ai-run@$GOOGLE_PROJECT_ID.iam.gserviceaccount.com  \
        --member="serviceAccount:$sa" \
        --role="roles/iam.serviceAccountUser"


#
# Delete service accounts
#
accounts=(
    vertex-ai-run
    vertex-ai-build
)
for account in ${accounts[@]}
do
    sa="$account@$GOOGLE_PROJECT_ID.iam.gserviceaccount.com"
    gcloud iam service-accounts delete $sa
done
    

