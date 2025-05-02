from flask import Flask, render_template, request
import pickle
import numpy as np
import yfinance as yf
import traceback
import boto3
import os
from io import BytesIO

app = Flask(__name__)

S3_BUCKET = "data-model-bucket-abhishek"
MODEL_FILE = "models/models.pkl"  # Path to models.pkl in S3

# Initialize S3 client
s3 = boto3.client("s3",
                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

# Load models and scalers directly from S3
response = s3.get_object(Bucket=S3_BUCKET, Key=MODEL_FILE)
models = pickle.load(BytesIO(response['Body'].read()))

@app.route("/", methods=["GET", "POST"])
def index():
    prediction = None
    real_price = None
    tomorrow_prediction = None

    if request.method == "POST":
        try:
            ticker = request.form["ticker"].upper()
            if ticker in models:
                model_info = models[ticker]
                model = model_info['model']
                scaler = model_info['scaler']

                stock = yf.Ticker(ticker)
                latest_data = stock.history(period="2d")

                if len(latest_data) >= 2:
                    X_input = np.array([[
                        latest_data["Open"].iloc[-2],
                        latest_data["High"].iloc[-2],
                        latest_data["Low"].iloc[-2],
                        latest_data["Close"].iloc[-2],
                        latest_data["Volume"].iloc[-2]
                    ]])
                    # Scale input data
                    X_input_scaled = scaler.transform(X_input)
                    prediction = model.predict(X_input_scaled)[0]

                    real_price = latest_data["Close"].iloc[-1]

                    X_tomorrow = np.array([[
                        latest_data["Open"].iloc[-1],
                        latest_data["High"].iloc[-1],
                        latest_data["Low"].iloc[-1],
                        prediction,
                        latest_data["Volume"].iloc[-1]
                    ]])
                    # Scale tomorrow's input data
                    X_tomorrow_scaled = scaler.transform(X_tomorrow)
                    tomorrow_prediction = model.predict(X_tomorrow_scaled)[0]
                else:
                    prediction = "No recent stock data available."
            else:
                prediction = "No trained model for this stock."

        except Exception:
            error_msg = traceback.format_exc()
            print(f"ERROR: {error_msg}")
            prediction = "An error occurred. Check logs."

    return render_template("index.html", prediction=prediction, real_price=real_price, tomorrow_prediction=tomorrow_prediction)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
