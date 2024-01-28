#!/bin/bash

#
# Create Dockerfile
#
cp ../../pipelines/model.py .
cp ../../pipelines/tb_utils.py .
cat  > Dockerfile <<EOF
FROM $GOOGLE_REGION-docker.pkg.dev/$GOOGLE_PROJECT_ID/vertex-ai-docker-repo/base:latest

COPY model.py .
COPY tb_utils.py .

ENTRYPOINT ["/bin/bash", "-c"]

EOF
#
# Do the actual build
#
docker build -t $GOOGLE_REGION-docker.pkg.dev/$GOOGLE_PROJECT_ID/vertex-ai-docker-repo/pipeline:latest .
