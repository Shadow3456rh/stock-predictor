import os
import time
import pickle
import requests
import pandas as pd
import boto3
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


DATA_DIR = "./stock_data"
PUSHGATEWAY_URL = "http://34.228.29.38:9091/metrics/job/train_model"
BUCKET_NAME = "data-model-bucket-abhishek"  
PREFIX = "stock_data/"             


if not os.path.exists(DATA_DIR):
    print(f"{DATA_DIR} not found. Downloading from S3...")

    s3 = boto3.client('s3',
                      aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                      aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

    os.makedirs(DATA_DIR, exist_ok=True)

    response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)
    for obj in response.get('Contents', []):
        key = obj['Key']
        filename = os.path.basename(key)
        if filename:
            download_path = os.path.join(DATA_DIR, filename)
            print(f"⬇️  {filename}")
            s3.download_file(BUCKET_NAME, key, download_path)

print("Stock data ready. Starting training")

# ========== TRAIN MODELS ==========
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
        data.dropna(subset=["Open", "High", "Low", "Close", "Volume"], inplace=True)

        data["Target"] = data["Close"].shift(-1)
        data.dropna(inplace=True)

        X = data[["Open", "High", "Low", "Close", "Volume"]]
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

# Save models
with open("models.pkl", "wb") as f:
    pickle.dump(models, f)

print("✅ All models saved successfully!")

# ========== PUSH METRICS TO PROMETHEUS ==========
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
        print("📡 Training metrics pushed to Prometheus.")
    else:
        print(f"❌ Failed to push metrics. Status code: {response.status_code}")
except Exception as e:
    print(f"❌ Error pushing metrics: {e}")
