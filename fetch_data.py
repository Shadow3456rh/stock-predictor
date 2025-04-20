import yfinance as yf
import pandas as pd
import os

STOCKS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
DATA_DIR = "./stock_data"

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

#lngterm data
def get_stock_data(symbol):
    df = yf.download(symbol, period="max", interval="1d", auto_adjust=True, progress=False)
    df.reset_index(inplace=True)
    df = df.rename(columns={"Date": "Datetime"})
    return df.dropna()

#Short term data
def get_intraday_data(symbol):
    df = yf.download(symbol, period="60d", interval="2m", auto_adjust=True, progress=False)
    df.reset_index(inplace=True)

    return df.dropna()

#merging both 
def fetch_all_stock_data():
    stock_data = {}
    for stock in STOCKS:
        df_long_term = get_stock_data(stock)
        if not df_long_term.empty:
            stock_data[f"{stock}_long_term"] = df_long_term

        df_intraday = get_intraday_data(stock)
        if not df_intraday.empty:
            stock_data[f"{stock}_intraday"] = df_intraday

    return stock_data

# Function to create or update the CSV
def update_stock_data(symbol, long_term_data, short_term_data):
    file_path = os.path.join(DATA_DIR, f"{symbol}_data.csv")

    def flatten_columns(df):
        if isinstance(df.columns[0], tuple):
            df.columns = [col[0] if col[0] else col[1] for col in df.columns]
        return df

    long_term_data = flatten_columns(long_term_data)
    short_term_data = flatten_columns(short_term_data)

    for df_name, df in [("Long Term", long_term_data), ("Short Term", short_term_data)]:
        if "Datetime" not in df.columns:
            raise ValueError(f"❌ 'Datetime' column missing in {symbol} {df_name} data!")
        df["Datetime"] = pd.to_datetime(df["Datetime"]).dt.tz_localize(None)

   
    cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=60)
    long_term_data = long_term_data[long_term_data["Datetime"] <= cutoff_date]

    
    combined_data = pd.concat([long_term_data, short_term_data]).drop_duplicates(subset="Datetime", keep="last")
    combined_data.sort_values("Datetime", inplace=True)
    combined_data.reset_index(drop=True, inplace=True)

    ################################################# Saving/updating csv files#############################################
    if os.path.exists(file_path):
        existing_data = pd.read_csv(file_path, parse_dates=["Datetime"])
        existing_data["Datetime"] = existing_data["Datetime"].dt.tz_localize(None)

        final_data = pd.concat([existing_data, combined_data]).drop_duplicates(subset="Datetime", keep="last")
        final_data.sort_values("Datetime", inplace=True)
        final_data.reset_index(drop=True, inplace=True)

        if len(final_data) > len(existing_data):
            final_data.to_csv(file_path, index=False)
            print(f"Updated {symbol}: Added new data, long-term trimmed to avoid overlap.")
        else:
            print(f"No new data for {symbol}. CSV remains unchanged.")
    else:
        combined_data.to_csv(file_path, index=False)
        print(f"Created new CSV and saved initial data for {symbol}.")



if __name__ == "__main__":
    all_stock_data = fetch_all_stock_data()
    for symbol, df in all_stock_data.items():
        base_symbol = symbol.split('_')[0]

        if 'long_term' in symbol:
            long_term_data = df
        if 'intraday' in symbol:
            short_term_data = df
            update_stock_data(base_symbol, long_term_data, short_term_data)
