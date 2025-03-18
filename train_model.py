from fetch_data import fetch_all_stock_data
from sklearn.linear_model import LinearRegression
import pickle

# Fetch data for all stocks
all_stock_data = fetch_all_stock_data()
models = {}

for symbol, data in all_stock_data.items():
    data["Target"] = data["Close"].shift(-1)  # Predict next day's close
    data.dropna(inplace=True)

    X = data[["Open", "High", "Low", "Close"]]
    y = data["Target"]

    model = LinearRegression()
    model.fit(X, y)

    models[symbol] = model
    print(f"✅ Model trained for {symbol}")

# Save models as a dictionary
with open("models.pkl", "wb") as f:
    pickle.dump(models, f)

print("✅ All models saved successfully!")

