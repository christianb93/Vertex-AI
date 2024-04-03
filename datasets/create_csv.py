def create_data():
    import torch
    import numpy as np 
    import pickle 
    X = []
    Y = []
    N = 2000
    with open("data.csv", "w") as csv:
        #
        # Print header line
        #
        csv.write("x,y,label\n")
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
            csv.write(f"{x[0]},{x[1]},{label}\n")


if __name__ == "__main__":
    create_data()