
import torch 
from ts.torch_handler.base_handler import BaseHandler


class Handler(BaseHandler):

    def __init__(self):
        super().__init__()
        self.model = None

    #
    # This will be called by the base handler. We assume that there is
    # only one input and will ignore all others. 
    #    
    def preprocess(self, data):
        print(f"Preprocess: {data}")
        data = data[0]
        input = torch.tensor(data, dtype = torch.float32)
        print(f"Preprocess: returning {input}")
        return input
    
    #
    # This gets the input from the preprocess step. The standard in the base handler
    # simply calls forward on the model, but we need predict
    #
    def inference(self, data):
        return self.model.predict(data)

    #
    # Make sure that the output also matches the Google expectations
    # {
    #   "predictions" : [...]
    # }
    # 
    def postprocess(self, data):
        #
        # This is the result of the inference method
        #
        return [str(data)]

