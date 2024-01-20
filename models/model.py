#
# Our model - one layer only, activation function left out
#

import torch

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
