"""
utils.py

Contains helper functions for creating folders and loading
the S&P 500 ticker symbols.
"""

import os
from io import StringIO

import pandas as pd
import requests


def create_folders():
    """Create the folders required by the application."""

    os.makedirs("data", exist_ok=True)
    os.makedirs("charts", exist_ok=True)


def load_tickers_from_csv(file_path):
    """
    Load ticker symbols from a local CSV file.

    The CSV must contain a column named 'Ticker'.
    """

    try:
        df = pd.read_csv(file_path)

        if "Ticker" not in df.columns:
            print(f"Error: '{file_path}' requires a Ticker column.")
            return []

        tickers = df["Ticker"].dropna().astype(str).str.strip().str.upper().tolist()

        return tickers

    except FileNotFoundError:
        print(f"Backup ticker file not found: {file_path}")
        return []

    except Exception as error:
        print(f"Error reading backup ticker file: {error}")
        return []


def download_sp500_tickers(url, backup_file):
    """
    Download the current S&P 500 ticker list.

    If the download fails, load the saved local CSV backup.
    """

    try:
        print("Downloading the current S&P 500 ticker list...")

        # Identify the application making the request
        headers = {
            "User-Agent": (
                "DavidTradingPlatform/1.0 (personal Python learning project)"
            )
        }

        # Download the webpage manually
        response = requests.get(url, headers=headers, timeout=20)

        # Raise an error for HTTP responses such as 403 or 404
        response.raise_for_status()

        # Read the HTML tables from the downloaded webpage
        tables = pd.read_html(StringIO(response.text))

        # The first table contains the S&P 500 companies
        sp500_table = tables[0]

        # Extract and clean the ticker symbols
        tickers = (
            sp500_table["Symbol"].dropna().astype(str).str.strip().str.upper().tolist()
        )

        # Yahoo Finance uses hyphens instead of periods
        # Example: BRK.B becomes BRK-B
        tickers = [ticker.replace(".", "-") for ticker in tickers]

        # Save the latest ticker list as a backup
        pd.DataFrame({"Ticker": tickers}).to_csv(backup_file, index=False)

        print(f"Loaded {len(tickers)} S&P 500 ticker symbols.")
        print(f"Ticker backup saved to {backup_file}")

        return tickers

    except requests.RequestException as error:
        print(f"Could not download the S&P 500 list: {error}")
        print("Attempting to load the local backup file...")

        return load_tickers_from_csv(backup_file)

    except Exception as error:
        print(f"Could not process the S&P 500 list: {error}")
        print("Attempting to load the local backup file...")

        return load_tickers_from_csv(backup_file)
