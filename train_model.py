from fetch_data import fetch_all_stock_data
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
import pickle
import requests
import time

PUSHGATEWAY_URL = "http://34.228.29.38:9091/metrics/job/train_model"

#data fetching also time pause
start_time = time.time()
all_stock_data = fetch_all_stock_data()
models = {}


num_models_trained = 0
total_accuracy = 0
total_loss = 0

for symbol, data in all_stock_data.items():
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


with open("models.pkl", "wb") as f:
    pickle.dump(models, f)

end_time = time.time()
training_duration = end_time - start_time

print("✅ All models saved successfully!")

#prometheus metrics format
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
        print("Training metrics pushed to Prometheus.")
    else:
        print(f"Failed to push metrics. Status code: {response.status_code}")
except Exception as e:
    print(f"Error pushing metrics: {e}")
