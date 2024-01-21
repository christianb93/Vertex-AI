#
# A simple binary regression on an artificial dataset
# with two features, data consists of two blobs below and above the diagonal
#

import os
import torch
import numpy as np
import google.cloud.storage as gcs

class Model(torch.nn.Module):

    def __init__(self):
        super().__init__()
        self.layers = torch.nn.Sequential(
            torch.nn.Linear(in_features = 2, out_features = 1)
        )
        self.activation = torch.nn.Sigmoid()

    def forward(self, X):
        return self.layers(X)

    #
    # Make a prediction for a single input
    # Input: a torch tensor of shape (2)
    # Output: an integer (0 or 1)
    #
    def predict(self, x):
        with torch.no_grad():
            logit = self.forward(x)
            out = self.activation(logit)
        return 0 if out < 0.5 else 1


#
# Create training data. Output is X, Y where
# X has dimension N x D (with D = 2 being the dimension of our feature space)
# and Y is the labels
#
def create_data(N = 100):
    X = []
    Y = []
    for i in range(N):
        #
        # First do the label, then choose a point in a corresponding cluster
        #
        label = np.random.randint(0, 2)
        if label == 0:
            #
            # below diagonal
            #
            x = np.array([ 0.5, 0.25 ])
        else:
            x = np.array([ 0.5, 0.75 ])
        #
        # Add some noise
        #
        x = x + 0.05 * np.random.random(2)
        X.append(x)
        Y.append(label)
    #
    # X is now a list of arrays - converting this to a single array 
    # before turning this into a tensor is more efficient
    #
    X = np.array(X)
    X = torch.tensor(X, dtype = torch.float32)
    Y = torch.tensor(Y, dtype = torch.float32)
    assert X.shape == torch.Size([N, 2])
    assert Y.shape == torch.Size([N])
    return X, Y




#
# Train. Our data is very small, so we do not use
# a dataset of shuffling but do everything in one batch
#
def train_model(model, X, Y, epochs = 5000):
    model.train()
    optimizer = torch.optim.SGD(model.parameters(), lr = 0.1)
    loss_fn = torch.nn.functional.binary_cross_entropy_with_logits
    for e in range(epochs):
        logits = model(X).squeeze(dim = 1)
        #
        # Yes, the targets are expected to be floats
        #
        loss = loss_fn(input = logits, target = Y)
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    print(f"Final loss: {loss.detach()}")

#
# Upload model to Google Cloud storage to the location pointed to by AIP_MODEL_DIR
#
def upload_model(model):
    #
    # Export model
    #
    torch.save(model.state_dict(), "model.bin")
    #
    # Initialize client
    #
    gcs_client = gcs.Client() 
    #
    # Determine bucket 
    #
    model_dir = os.environ.get("AIP_MODEL_DIR")
    print(f"Using model dir {model_dir}")
    uri = f"{model_dir}/model.bin"
    path_components = uri.replace("gs://", "").rsplit("/")
    bucket_name = path_components[0]
    blob_name = "/".join(path_components[1:])
    print(f"Doing upload to model directory {model_dir} (bucket {bucket_name}, blob {blob_name})")
    #
    # Do upload
    #
    bucket = gcs_client.get_bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename("model.bin")


#
# Train
#
N = 1000
epochs = 500
X, Y = create_data(N = N)
model = Model()
train_model(model, X, Y, epochs = epochs)
#
# Calculate accuracy
#
hits = 0
X, Y = create_data(N = N)
for _x, x in enumerate(X):
    prediction = model.predict(x)
    true_label = int(Y[_x])
    if true_label == prediction:
        hits = hits + 1
print(f"Accuracy on test data: {1.0 * hits / N}")

#
# Store model on GCS
#
print(f"AIP_MODEL_DIR={os.environ['AIP_MODEL_DIR']}")
upload_model(model)