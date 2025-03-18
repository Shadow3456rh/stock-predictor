import requests
import pandas as pd

STOCKS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]

def get_stock_data(symbol, range="1y", interval="1d"):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={range}"
    headers = {"User-Agent": "Mozilla/5.0"}
    
    response = requests.get(url, headers=headers)
    data = response.json()
    
    if "chart" in data and "result" in data["chart"] and data["chart"]["result"]:
        result = data["chart"]["result"][0]
        timestamps = result.get("timestamp", [])
        quotes = result.get("indicators", {}).get("quote", [{}])[0]
        
        if timestamps and "close" in quotes:
            df = pd.DataFrame({
                "Date": pd.to_datetime(timestamps, unit="s"),
                "Open": quotes.get("open", []),
                "High": quotes.get("high", []),
                "Low": quotes.get("low", []),
                "Close": quotes.get("close", []),
                "Volume": quotes.get("volume", []),
            })
            return df.dropna()
    
    print(f"⚠️ No data found for {symbol}")
    return pd.DataFrame()

# Function to fetch all stock data
def fetch_all_stock_data():
    stock_data = {}
    for stock in STOCKS:
        df = get_stock_data(stock)
        if not df.empty:
            stock_data[stock] = df
    return stock_data

# Example usage
if __name__ == "__main__":
    stock_data = fetch_all_stock_data()
    for symbol, df in stock_data.items():
        print(f"\n📊 {symbol} Data:\n", df.head())

