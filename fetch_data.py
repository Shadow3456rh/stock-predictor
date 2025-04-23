import yfinance as yf
import pandas as pd
import boto3
from io import StringIO

STOCKS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
BUCKET_NAME = "data-model-bucket-abhishek"
PREFIX = "stock_data/"

# Initialize S3 client
s3 = boto3.client('s3',
                  aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                  aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'))

# Long-term data
def get_stock_data(symbol):
    df = yf.download(symbol, period="max", interval="1d", auto_adjust=True, progress=False)
    df.reset_index(inplace=True)
    df = df.rename(columns={"Date": "Datetime"})
    return df.dropna()

# Short-term data
def get_intraday_data(symbol):
    df = yf.download(symbol, period="60d", interval="2m", auto_adjust=True, progress=False)
    df.reset_index(inplace=True)
    return df.dropna()

# Merging both
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

# Function to create or update the CSV in S3
def update_stock_data(symbol, long_term_data, short_term_data):
    s3_key = f"{PREFIX}{symbol}_data.csv"

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

    # Check if file exists in S3
    try:
        # Read existing data from S3
        response = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        existing_data = pd.read_csv(response['Body'], parse_dates=["Datetime"])
        existing_data["Datetime"] = existing_data["Datetime"].dt.tz_localize(None)

        final_data = pd.concat([existing_data, combined_data]).drop_duplicates(subset="Datetime", keep="last")
        final_data.sort_values("Datetime", inplace=True)
        final_data.reset_index(drop=True, inplace=True)

        if len(final_data) > len(existing_data):
            # Save updated data to S3
            csv_buffer = StringIO()
            final_data.to_csv(csv_buffer, index=False)
            s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=csv_buffer.getvalue())
            print(f"Updated {symbol}: Added new data, long-term trimmed to avoid overlap.")
        else:
            print(f"No new data for {symbol}. S3 object remains unchanged.")
    except s3.exceptions.NoSuchKey:
        # Save new data to S3
        csv_buffer = StringIO()
        combined_data.to_csv(csv_buffer, index=False)
        s3.put_object(Bucket=BUCKET_NAME, Key=s3_key, Body=csv_buffer.getvalue())
        print(f"Created new S3 object and saved initial data for {symbol}.")

if __name__ == "__main__":
    all_stock_data = fetch_all_stock_data()
    for symbol, df in all_stock_data.items():
        base_symbol = symbol.split('_')[0]
        if 'long_term' in symbol:
            long_term_data = df
        if 'intraday' in symbol:
            short_term_data = df
            update_stock_data(base_symbol, long_term_data, short_term_data)
