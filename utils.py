import os
import pandas as pd


def create_folders():
    """Create the folders required by the application."""
    os.makedirs("data", exist_ok=True)
    os.makedirs("charts", exist_ok=True)


def load_tickers_from_csv(file_path):
    """Load ticker symbols from a CSV file."""

    try:
        df = pd.read_csv(file_path)

        if "Ticker" not in df.columns:
            print(f"Error: '{file_path}' must contain a 'Ticker' column.")
            return []

        tickers = (
            df["Ticker"]
            .dropna()
            .astype(str)
            .str.strip()
            .str.upper()
            .tolist()
        )

        return tickers

    except FileNotFoundError:
        print(f"Error: Could not find '{file_path}'.")
        return []

    except pd.errors.EmptyDataError:
        print(f"Error: '{file_path}' is empty.")
        return []

    except Exception as error:
        print(f"Error loading ticker file: {error}")
        return []