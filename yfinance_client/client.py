"""
This script gets the data from the yfinance API for the tickers in the cik_mapping.json file.

We need to primarily get data from three different financial instruments:

- Stocks
- ETFs
- Indices
"""

import json
import os
from dotenv import load_dotenv
import pandas as pd
import requests
import io
load_dotenv()
import yfinance as yf

def get_ticker_data(ticker: str) -> dict:
    print(f"Getting data for {ticker}...")
    data = yf.Ticker(ticker).info
    return data

if __name__ == "__main__":
    print("=" * 70)
    print("Starting yfinance client...")
    print("Getting data for a random ETF ticker...")
    BLKC = get_ticker_data("BLKC")
    json.dump(BLKC, open("data/yfinance/blkc.json", "w"))
    print("-" * 70)
    print("=" * 70)