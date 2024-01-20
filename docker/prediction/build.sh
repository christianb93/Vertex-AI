#!/bin/bash

#
# Create Dockerfile
#
cp ../../models/torchserve.config .
cp ../../models/download_model.py .
cp ../../models/entrypoint.sh .
cat  > Dockerfile <<EOF
FROM $GOOGLE_REGION-docker.pkg.dev/$GOOGLE_PROJECT_ID/vertex-ai-docker-repo/base:latest


RUN apt-get update && apt-get --yes install openjdk-17-jre
RUN pip3 install nvgpu

COPY torchserve.config .
COPY download_model.py .
COPY entrypoint.sh .

ENTRYPOINT ["/bin/bash", "-c"]
CMD [/bin/bash", "entrypoint.sh"]

EOF
#
# Do the actual build
#
docker build -t $GOOGLE_REGION-docker.pkg.dev/$GOOGLE_PROJECT_ID/vertex-ai-docker-repo/prediction:latest .
