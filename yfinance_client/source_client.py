'''
This script is the source client to standardize codes for the major instrument sources -- Exchanges and Indexes.
We will use the ISO 10383 standard to standardize the codes for the major instrument sources, targeting the United States Financial Market.

We will start by downloading the ISO 10383 standard file from a source URL and then standardize the codes for both exchanges and indexes. 
'''
import requests
import json
import os
from dotenv import load_dotenv
import pandas as pd
import re
import io
import numpy as np
load_dotenv()

ISO_SOURCE_URL = os.environ["ISO_SOURCE_URL"]
TARGETED_EXCHANGES = ["New York Stock Exchange", "NASDAQ Stock Market", "NYSE American", "NYSE Arca"]
TARGETED_INDEXES = ["S&P 500", "Dow Jones Industrial Average", "Nasdaq Composite", "Nasdaq-100", "Russell 2000"]
def get_exchanges_from_csv(file_path: str, exchanges: list[str]) -> list[str]:
    mic_mapping = {}
    # Get the Operating MIC code for the targeted exchanges from the CSV file
    # read the CSV file
    with open(file_path, "r") as file:
        reader = pd.read_csv(file)
        # set the header row
        reader.columns = reader.columns.str.lower()
        # Need only records with the same MIC code and operating MIC code, dont involve exchanges yet
        operating_exchanges = reader[reader["mic"] == reader["operating mic"]]
        market_name_col = "market name-institution description"
        # Direct mappings for known US exchanges
        # Format: "User Name": ("CSV Search Pattern", "MIC Code if known", is_segment)
        exchange_configs = {
            "New York Stock Exchange": ("NEW YORK STOCK EXCHANGE", "XNYS", False),
            "NASDAQ Stock Market": ("NASDAQ - ALL MARKETS", "XNAS", False),
            "NYSE American": ("NYSE AMERICAN", "XASE", True),  # Segment
            "NYSE Arca": ("NYSE ARCA", "ARCX", True)  # Segment
        }
        for exchange_name in exchanges:
            if exchange_name not in exchange_configs:
                print(f"⚠ Unknown exchange: {exchange_name}")
                continue
            
            pattern, expected_mic, is_segment = exchange_configs[exchange_name]
            
            # Search in appropriate dataset
            search_df = reader if is_segment else operating_exchanges
            
            matches = search_df[
                search_df[market_name_col].str.contains(pattern, case=False, na=False)
            ]
            
            if not matches.empty:
                mic_code = matches.iloc[0]["mic"]
                mic_mapping[exchange_name] = mic_code
                print(f"✓ {exchange_name} -> {mic_code}")
            else:
                print(f"✗ Not found: {exchange_name}")
        
        return mic_mapping


def get_iso_10383_standard_file() -> tuple[dict, dict]:
    response = requests.get(ISO_SOURCE_URL)
    response.raise_for_status()
    # Continue if response is a successful response, otherwise raise an error
    if response.status_code == 200:
        # Get all the links in the response (a href links), with filtering for a .csv file
        pattern = r'href=["\']?([^"\'>\s]*\.csv)["\']?'
        matches = re.findall(pattern, response.text)
        if matches:
            csv_link = matches[0]
            if not csv_link.startswith("http"):
                # get the domain from the ISO_SOURCE_URL
                domain = ISO_SOURCE_URL.split("/")[2]
                csv_link = "https://" + domain + csv_link
            # Download the CSV file
            response = requests.get(csv_link)
            response.raise_for_status()
            if response.status_code == 200:
                # Save the CSV file as a temporary file
                with open("iso_10383_standard_file.csv", "wb") as file:
                    file.write(response.content)
                    print(f"Saved the CSV file to {file.name}")
                    # Get the MIC codes for the targeted exchanges from the CSV file - NYSE,NASDAQ,NYSE_American,NYSE_Arca ONLY
                    exchanges = get_exchanges_from_csv(file.name, TARGETED_EXCHANGES)
                    return exchanges


def get_etfs_from_alphavantage_api() -> list[str]:
    print("Getting ETFs list from Alphavantage API...")
    etfs = requests.get("https://www.alphavantage.co/query?function=LISTING_STATUS&apikey=demo")
    etfs.raise_for_status()
    etfs = pd.read_csv(io.StringIO(etfs.text))
    etfs = etfs[etfs["assetType"] == "ETF"]["symbol"].unique().tolist()
    print(f"Found {len(etfs)} ETFs")
    print("Saving ETF tickers to file...")
    os.makedirs("data/yfinance", exist_ok=True)
    with open("data/yfinance/etf_tickers.json", "w") as file:
        json.dump(etfs, file)
    print("ETFs saved to data/yfinance/etf_tickers.json")
    return etfs

def get_stocks_from_alphavantage_api() -> list[str]:
    print("Getting stocks list from Alphavantage API...")
    stocks = requests.get("https://www.alphavantage.co/query?function=LISTING_STATUS&apikey=demo")
    stocks.raise_for_status()
    stocks = pd.read_csv(io.StringIO(stocks.text))
    # Filter for Stocks and sanitize the list for NaN values
    stocks = stocks[stocks["assetType"] == "Stock"]["symbol"].unique().tolist()
    stocks.remove(np.nan)
    # Sanitize the stocks list to remove NaN values
    stocks = [stock for stock in stocks if stock is not None or stock != np.nan]
    print(f"Found {len(stocks)} stocks")
    print("Saving stocks to file...")
    os.makedirs("data/yfinance", exist_ok=True)
    with open("data/yfinance/stock_tickers.json", "w") as file:
        json.dump(stocks, file)
    return stocks

def remove_iso_10383_standard_file() -> None:
    os.remove("iso_10383_standard_file.csv")
    print("ISO 10383 standard file removed")

if __name__ == "__main__":
    print("=" * 70)
    print("Starting source client...")
    print("-" * 70)
    print("Getting ISO 10383 standard file to extract exchange MIC codes ...")
    exchanges= get_iso_10383_standard_file()
    remove_iso_10383_standard_file()
    print(f"Found targeted exchanges: {exchanges}")
    print("Saving exchanges to file...")
    with open("exchanges.json", "w") as file:
        json.dump(exchanges, file)
    print("-" * 70)
    print("Index Identifiers are implemented manually for now...")
    print("Index identifiers are already saved to indexes.json file...")
    print("-" * 70)
    print("Getting ETF tickers and stock tickers using Alphavantage API...")
    etfs = get_etfs_from_alphavantage_api()
    stocks = get_stocks_from_alphavantage_api()
    print(f"Found {len(etfs)} ETFs and {len(stocks)} stocks")
    print("ETFs and stocks saved to data/yfinance/etf_tickers.json and data/yfinance/stocks.json")
    print("-" * 70)
    print("Completed source client...")
    print("=" * 70)