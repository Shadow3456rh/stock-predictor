from fetch_data import fetch_all_stock_data
from sklearn.linear_model import LinearRegression
import pickle
import requests
import time

PUSHGATEWAY_URL = "http://192.168.174.124:9091/metrics/job/train_model"

# Fetch data for all stocks
start_time = time.time()
all_stock_data = fetch_all_stock_data()
models = {}
num_models_trained = 0

for symbol, data in all_stock_data.items():
    data["Target"] = data["Close"].shift(-1)  # Predict next day's close
    data.dropna(inplace=True)

    X = data[["Open", "High", "Low", "Close"]]
    y = data["Target"]

    model = LinearRegression()
    model.fit(X, y)

    models[symbol] = model
    num_models_trained += 1

    print(f"✅ Model trained for {symbol}")

# Save models as a dictionary
with open("models.pkl", "wb") as f:
    pickle.dump(models, f)

end_time = time.time()
training_duration = end_time - start_time

print("✅ All models saved successfully!")

# Send metrics to Prometheus Pushgateway
metrics = f"""
# HELP model_training_time_seconds Time taken to train models
# TYPE model_training_time_seconds gauge
model_training_time_seconds {training_duration}

# HELP models_trained_total Total number of models trained
# TYPE models_trained_total gauge
models_trained_total {num_models_trained}
"""

try:
    response = requests.post(PUSHGATEWAY_URL, data=metrics)
    if response.status_code == 200:
        print("✅ Training metrics pushed to Prometheus.")
    else:
        print(f"⚠️ Failed to push metrics. Status code: {response.status_code}")
except Exception as e:
    print(f"❌ Error pushing metrics: {e}")
