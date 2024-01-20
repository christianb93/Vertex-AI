#!/bin/bash

#
# Create Dockerfile
#
cp ../../requirements.txt requirements.txt
cat  > Dockerfile <<EOF
FROM python:3.10

COPY ./requirements.txt .
RUN pip3 install -r requirements.txt

ENTRYPOINT ["/bin/sh", "-c"]
CMD ["/bin/bash"]

EOF
#
# Do the actual build
#
docker build -t $GOOGLE_REGION-docker.pkg.dev/$GOOGLE_PROJECT_ID/vertex-ai-docker-repo/base:latest .
#
# Clean up
#
rm -f requirements.txt
