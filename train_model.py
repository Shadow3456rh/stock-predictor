import os
import time
import pickle
import requests
import pandas as pd
import boto3
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.preprocessing import StandardScaler

DATA_DIR = "./stock_data"
PUSHGATEWAY_URL = "http://34.228.29.38:9091/metrics/job/train_model"
BUCKET_NAME = "data-model-bucket-abhishek"
PREFIX = "stock_data/"

# Download data from S3 if not present
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
total_r2 = 0
total_mse = 0
total_mae = 0
total_directional_accuracy = 0

for filename in os.listdir(DATA_DIR):
    if filename.endswith("_data.csv"):
        symbol = filename.split("_")[0]
        file_path = os.path.join(DATA_DIR, filename)

        # Load and preprocess data
        data = pd.read_csv(file_path, parse_dates=["Datetime"])
        data.sort_values("Datetime", inplace=True)
        data.dropna(subset=["Open", "High", "Low", "Close", "Volume"], inplace=True)

        if len(data) < 10:
            print(f"Skipping {symbol}: insufficient data")
            continue

        # Check for mixed intraday and daily data
        time_diffs = data["Datetime"].diff().dropna()
        if time_diffs.dt.total_seconds().min() < 24 * 3600:  # Less than a day
            print(f"⚠️ Warning: {symbol} data may contain intraday intervals. Aggregating to daily...")
            data = data.resample('D', on='Datetime').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna().reset_index()

        # Create lagged features to avoid data leakage
        data["Lag_Open"] = data["Open"].shift(1)
        data["Lag_High"] = data["High"].shift(1)
        data["Lag_Low"] = data["Low"].shift(1)
        data["Lag_Close"] = data["Close"].shift(1)
        data["Lag_Volume"] = data["Volume"].shift(1)

        # Define target (next day's Close)
        data["Target"] = data["Close"].shift(-1)
        data.dropna(inplace=True)

        # Features: Use lagged values only
        X = data[["Lag_Open", "Lag_High", "Lag_Low", "Lag_Close", "Lag_Volume"]]
        y = data["Target"]

        # Check for leakage via correlation
        correlations = X.corrwith(data["Target"])
        print(f"📊 {symbol} Feature-Target Correlations:\n{correlations}")
        if correlations.abs().max() > 0.99:
            print(f"⚠️ Warning: High correlation (>0.99) detected for {symbol}. Possible leakage!")

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Time-based train-test split
        train_size = int(len(X_scaled) * 0.8)
        X_train, X_test = X_scaled[:train_size], X_scaled[train_size:]
        y_train, y_test = y[:train_size], y[train_size:]

        # Train model
        model = LinearRegression()
        model.fit(X_train, y_train)

        # Predict and evaluate
        y_pred = model.predict(X_test)
        r2 = r2_score(y_test, y_pred)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)

        # Calculate directional accuracy
        y_test_shifted = y_test.shift(1).iloc[1:]  # Previous day's actual Close
        y_pred_shifted = pd.Series(y_pred, index=y_test.index)[1:]  # Predicted Close
        y_test_diff = y_test.iloc[1:] - y_test_shifted  # Actual price movement
        y_pred_diff = y_pred_shifted - y_test_shifted  # Predicted price movement
        directional_accuracy = ((y_test_diff * y_pred_diff) > 0).mean() * 100

        total_r2 += r2
        total_mse += mse
        total_mae += mae
        total_directional_accuracy += directional_accuracy
        num_models_trained += 1

        models[symbol] = {'model': model, 'scaler': scaler}
        print(f"✅ Model trained for {symbol} | R²: {r2:.4f} | MSE: {mse:.4f} | MAE: {mae:.4f} | Directional Accuracy: {directional_accuracy:.2f}%")

        # Warn if R² is suspiciously high
        if r2 > 0.99:
            print(f"⚠️ Warning: R² = {r2:.4f} for {symbol} is suspiciously high. Inspect data for leakage!")

avg_r2 = total_r2 / num_models_trained if num_models_trained else 0
avg_mse = total_mse / num_models_trained if num_models_trained else 0
avg_mae = total_mae / num_models_trained if num_models_trained else 0
avg_directional_accuracy = total_directional_accuracy / num_models_trained if num_models_trained else 0

# Save models and scalers
with open("models.pkl", "wb") as f:
    pickle.dump(models, f)

print("✅ All models and scalers saved successfully!")
print(f"Average R²: {avg_r2:.4f} | Average MSE: {avg_mse:.4f} | Average MAE: {avg_mae:.4f} | Average Directional Accuracy: {avg_directional_accuracy:.2f}%")

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

# HELP model_average_r2 Average model R² score
# TYPE model_average_r2 gauge
model_average_r2 {avg_r2}

# HELP model_average_mse Average model Mean Squared Error
# TYPE model_average_mse gauge
model_average_mse {avg_mse}

# HELP model_average_mae Average model Mean Absolute Error
# TYPE model_average_mae gauge
model_average_mae {avg_mae}

# HELP model_average_directional_accuracy_percentage Average directional accuracy (Percentage)
# TYPE model_average_directional_accuracy_percentage gauge
model_average_directional_accuracy_percentage {avg_directional_accuracy}
"""

try:
    response = requests.post(PUSHGATEWAY_URL, data=metrics)
    if response.status_code == 200:
        print("📡 Training metrics pushed to Prometheus.")
    else:
        print(f"❌ Failed to push metrics. Status code: {response.status_code}")
except Exception as e:
    print(f"❌ Error pushing metrics: {e}")
