from flask import Flask, render_template, request
import pickle
import numpy as np
import yfinance as yf
import traceback  # For debugging errors

app = Flask(__name__)


with open(r"models.pkl", "rb") as f:
    models = pickle.load(f)

@app.route("/", methods=["GET", "POST"])
def index():
    prediction = None
    real_price = None
    tomorrow_prediction = None

    if request.method == "POST":
        try:
            ticker = request.form["ticker"].upper()  
            
            if ticker in models:
                model = models[ticker]

              
                stock = yf.Ticker(ticker)
                latest_data = stock.history(period="2d")

                if len(latest_data) >= 2:
        
                    X_input = np.array([[
                        latest_data["Open"].iloc[-1], 
                        latest_data["High"].iloc[-1], 
                        latest_data["Low"].iloc[-1], 
                        latest_data["Close"].iloc[-1]
                    ]])

                  
                    prediction = model.predict(X_input)[0]

                    
                    real_price = latest_data["Close"].iloc[-1]

                  
                    X_tomorrow = np.array([[
                        latest_data["Open"].iloc[-1], 
                        latest_data["High"].iloc[-1], 
                        latest_data["Low"].iloc[-1], 
                        prediction  
                    ]])

                    tomorrow_prediction = model.predict(X_tomorrow)[0]
                else:
                    prediction = " No recent stock data available."
            else:
                prediction = "No trained model for this stock."

        except Exception as e:
            error_msg = traceback.format_exc()
            print(f" ERROR: {error_msg}")  
            prediction = " An error occurred. Check logs."

    return render_template("index.html", prediction=prediction, real_price=real_price, tomorrow_prediction=tomorrow_prediction)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
