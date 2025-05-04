import time
import pickle
import requests
import pandas as pd
import boto3
import os
from io import BytesIO
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split

BUCKET_NAME = "data-model-bucket-abhishek"
PREFIX = "stock_data/"
MODEL_KEY = "models/models.pkl"
PUSHGATEWAY_URL = "http://34.228.29.38:9091/metrics/job/train_model"

s3 = boto3.client('s3',
                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

print("Fetching stock data from S3")

response = s3.list_objects_v2(Bucket=BUCKET_NAME, Prefix=PREFIX)
stock_files = [obj['Key'] for obj in response.get('Contents', []) if obj['Key'].endswith('_data.csv')]

if not stock_files:
    print("No stock data found in S3. Exiting.")
    exit(1)

start_time = time.time()
models = {}
num_models_trained = 0
total_loss = 0
r2_scores = {}  # Dictionary to store R² scores for each symbol

####################### Model training ##########################################################
for s3_key in stock_files:
    symbol = s3_key.split('/')[-1].split('_')[0]
    print(f"Processing {symbol} from {s3_key}...")

    response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
    data = pd.read_csv(response['Body'], parse_dates=["Datetime"])
    data.sort_values("Datetime", inplace=True)
    data.dropna(subset=["Open", "High", "Low", "Close", "Volume"], inplace=True)

    if len(data) < 10:
        print(f"Skipping {symbol}: insufficient data")
        continue

    data["Target"] = data["Close"].shift(-1)
    data.dropna(inplace=True)

    X = data[["Open", "High", "Low", "Close", "Volume"]]
    y = data["Target"]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    accuracy = r2_score(y_test, y_pred) * 100  # R² as percentage
    loss = mean_squared_error(y_test, y_pred)

    total_loss += loss
    num_models_trained += 1
    r2_scores[symbol] = accuracy  # Store R² score for this symbol

    models[symbol] = {'model': model, 'scaler': scaler}
    print(f"Model trained for {symbol} | R² Score: {accuracy:.2f}% | Loss: {loss:.4f}")

avg_loss = total_loss / num_models_trained if num_models_trained else 0
print(f"Average Loss: {avg_loss:.4f}")

print("Saving models to S3")
model_buffer = BytesIO()
pickle.dump(models, model_buffer)
model_buffer.seek(0)
s3.put_object(Bucket=BUCKET_NAME, Key=MODEL_KEY, Body=model_buffer.getvalue())
print(f"Models and scalers saved to s3://{BUCKET_NAME}/{MODEL_KEY}")

end_time = time.time()
training_duration = end_time - start_time

############ Pushing metrics to Prometheus gateway ####################
metrics = f"""
# HELP model_training_time_seconds Time taken to train models
# TYPE model_training_time_seconds gauge
model_training_time_seconds {training_duration}

# HELP models_trained_total Total number of models trained
# TYPE models_trained_total gauge
models_trained_total {num_models_trained}

# HELP model_r2_score_percentage R² score for each stock model (Percentage)
# TYPE model_r2_score_percentage gauge
"""
# Add individual R² scores with symbol labels
for symbol, r2_score in r2_scores.items():
    metrics += f'model_r2_score_percentage{{symbol="{symbol}"}} {r2_score:.2f}\n'

metrics += f"""
# HELP model_average_loss Average model loss (Mean Squared Error)
# TYPE model_average_loss gauge
model_average_loss {avg_loss:.4f}
"""

try:
    response = requests.post(PUSHGATEWAY_URL, data=metrics)
    if response.status_code == 200:
        print("📡 Training metrics pushed to Prometheus.")
    else:
        print(f"❌ Failed to push metrics. Status code: {response.status_code}")
        print(f"Response: {response.text}")  # Added for debugging
except Exception as e:
    print(f"❌ Error pushing metrics: {e}")
