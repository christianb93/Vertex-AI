#!/bin/sh
# The startup script downloads model artifacts from GCS and start the TorchServe
# server.
echo "Using model location $AIP_STORAGE_URI"
python3 download_model.py
torchserve \
    --start \
    --ts-config=torchserve.config \
    --foreground \
    --model-store=$(pwd) \
    --models \
    model=model.mar

