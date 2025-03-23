import requests
import pandas as pd
import time

STOCKS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]

def get_stock_data(symbol, data_range="1y", interval="1d", retries=3):
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={data_range}"

    headers = {"User-Agent": "Mozilla/5.0"}
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
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
            
            print(f"⚠️ Attempt {attempt + 1} failed for {symbol}. Retrying in 5 seconds...")
            time.sleep(5)
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Network error for {symbol}: {e}. Retrying in 5 seconds...")
            time.sleep(5)
    
    print(f"❌ Failed to fetch data for {symbol} after {retries} attempts.")
    return pd.DataFrame()

# Fetch all stock data
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
