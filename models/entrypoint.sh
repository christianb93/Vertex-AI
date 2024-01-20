#!/bin/sh
# The startup script downloads model artifacts from GCS and start the TorchServe
# server.
echo "Using model location $AIP_STORAGE_URI"
python3 download_model.py
cp model.mar model-store/model.mar
torchserve \
    --start \
    --ts-config=/home/model-server/config.properties \
    --foreground \
    --models \
    model=model.mar

