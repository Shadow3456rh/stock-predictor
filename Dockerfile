FROM python:3.9

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir flask yfinance scikit-learn pandas matplotlib

CMD ["python", "app.py"]

