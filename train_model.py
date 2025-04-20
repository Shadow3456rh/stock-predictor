import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import pickle
import os
import time
import requests
import boto3

DATA_DIR = "./stock_data"
PUSHGATEWAY_URL = "http://34.228.29.38:9091/metrics/job/train_model"
S3_BUCKET = "data-model-bucket-abhishek"

# AWS Client
s3 = boto3.client("s3")

start_time = time.time()
models = {}

num_models_trained = 0
total_accuracy = 0
total_loss = 0

for filename in os.listdir(DATA_DIR):
    if filename.endswith("_data.csv"):
        symbol = filename.split("_")[0]
        file_path = os.path.join(DATA_DIR, filename)

        data = pd.read_csv(file_path, parse_dates=["Datetime"])
        data.sort_values("Datetime", inplace=True)
        data.dropna(subset=["Open", "High", "Low", "Close"], inplace=True)

        data["Target"] = data["Close"].shift(-1)
        data.dropna(inplace=True)

        X = data[["Open", "High", "Low", "Close"]]
        y = data["Target"]

        model = LinearRegression()
        model.fit(X, y)

        y_pred = model.predict(X)
        accuracy = r2_score(y, y_pred) * 100
        loss = mean_squared_error(y, y_pred)

        total_accuracy += accuracy
        total_loss += loss
        num_models_trained += 1

        models[symbol] = model
        print(f"✅ Model trained for {symbol} | Accuracy: {accuracy:.2f}% | Loss: {loss:.4f}")

avg_accuracy = total_accuracy / num_models_trained if num_models_trained else 0
avg_loss = total_loss / num_models_trained if num_models_trained else 0

# Save model
with open("models.pkl", "wb") as f:
    pickle.dump(models, f)

# Upload to S3
s3.upload_file("models.pkl", S3_BUCKET, "models.pkl")
print("📤 Uploaded models.pkl to S3.")

# Upload all CSV files in stock_data/
for file in os.listdir(DATA_DIR):
    if file.endswith(".csv"):
        s3.upload_file(os.path.join(DATA_DIR, file), S3_BUCKET, f"stock_data/{file}")
        print(f"📤 Uploaded {file} to S3.")

end_time = time.time()
training_duration = end_time - start_time

metrics = f"""
# HELP model_training_time_seconds Time taken to train models
# TYPE model_training_time_seconds gauge
model_training_time_seconds {training_duration}

# HELP models_trained_total Total number of models trained
# TYPE models_trained_total gauge
models_trained_total {num_models_trained}

# HELP model_average_accuracy_percentage Average model accuracy (Percentage)
# TYPE model_average_accuracy_percentage gauge
model_average_accuracy_percentage {avg_accuracy}

# HELP model_average_loss Average model loss (Mean Squared Error)
# TYPE model_average_loss gauge
model_average_loss {avg_loss}
"""

try:
    response = requests.post(PUSHGATEWAY_URL, data=metrics)
    if response.status_code == 200:
        print("📡 Metrics pushed to Prometheus.")
    else:
        print(f"❌ Failed to push metrics. Status code: {response.status_code}")
except Exception as e:
    print(f"❌ Error pushing metrics: {e}")
