#
# A simple binary regression on an artificial dataset
# with two features, data consists of two blobs below and above the diagonal
#

import torch
import numpy as np
from model import Model


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
# Train
#
N = 1000
epochs = 5000
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
# Export model
#
torch.save(model.state_dict(), "model.pt")