import requests
import pandas as pd
import time
import os

STOCKS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
DATA_DIR = "./stock_data"  # Directory to store the CSV files

# Create directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# Function to fetch long-term (1d) data
def get_stock_data(symbol, data_range="5y", interval="1d", retries=3):
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

# Function to fetch short-term (15m) data
def get_intraday_data(symbol, data_range="30d", interval="15m", retries=3):
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

# Function to fetch all stock data (both long-term and short-term)
def fetch_all_stock_data():
    stock_data = {}
    for stock in STOCKS:
        # Fetch long-term (daily) data for each stock (5 years)
        df_long_term = get_stock_data(stock, data_range="5y", interval="1d")
        if not df_long_term.empty:
            stock_data[f"{stock}_long_term"] = df_long_term

        # Fetch short-term (15 minutes) data for each stock (30 days)
        df_intraday = get_intraday_data(stock, data_range="30d", interval="15m")
        if not df_intraday.empty:
            # Directly store the intraday (15m) data without resampling
            stock_data[f"{stock}_intraday"] = df_intraday

    return stock_data

# Function to create or update the CSV with new data
# Function to create or update the CSV with new data
def update_stock_data(symbol, long_term_data, short_term_data):
    file_path = os.path.join(DATA_DIR, f"{symbol}_data.csv")
    
    if os.path.exists(file_path):
        # Load existing data
        existing_data = pd.read_csv(file_path, parse_dates=["Date"])
        
        # Remove the last 30 days from the long-term data
        most_recent_date = existing_data["Date"].max()
        thirty_days_ago = most_recent_date - pd.Timedelta(days=30)
        long_term_data = long_term_data[long_term_data["Date"] <= thirty_days_ago]

        # Concatenate the remaining long-term data with the new short-term data
        combined_data = pd.concat([long_term_data, short_term_data]).drop_duplicates(subset='Date', keep='last')
        combined_data.sort_values("Date", inplace=True)

        # Check if any new data is added (based on length comparison)
        if len(combined_data) > len(existing_data):
            combined_data.to_csv(file_path, index=False)
            print(f"✅ Updated {symbol} with new short-term data and removed last 30 days from long-term data. New data added.")
        else:
            print(f"ℹ️ No new data for {symbol}. CSV remains unchanged.")
        
    else:
        # If the file doesn't exist, save the new data as a new CSV
        combined_data = pd.concat([long_term_data, short_term_data]).drop_duplicates(subset='Date', keep='last')
        combined_data.sort_values("Date", inplace=True)
        combined_data.to_csv(file_path, index=False)
        print(f"✅ Created new CSV and saved data for {symbol}.")

# Main execution
if __name__ == "__main__":
    all_stock_data = fetch_all_stock_data()

    # For each stock, create or update the CSV with the new data
    for symbol, df in all_stock_data.items():
        # Get the base stock symbol without the suffix (long_term or intraday)
        base_symbol = symbol.split('_')[0]

        # If it's long-term data, store it
        if 'long_term' in symbol:
            long_term_data = df
        # If it's short-term data, store it and update the CSV
        if 'intraday' in symbol:
            short_term_data = df
            # Update the data for the stock, removing the last 30 days from long-term data and adding short-term data
            update_stock_data(base_symbol, long_term_data, short_term_data)
