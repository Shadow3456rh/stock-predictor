import pickle

with open("models.pkl", "rb") as f:
    models = pickle.load(f)

print(models.keys())  # Check what stock symbols are available

