"""
config.py

Stores settings used throughout the trading platform.
"""

# Web page containing the current S&P 500 company list
SP500_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

# Local backup ticker file
TICKER_FILE = "data/sp500.csv"

# Historical stock-data period
PERIOD = "6mo"

# Moving-average periods
SHORT_MA = 20
LONG_MA = 50

# Output file containing the scanner results
CSV_FILE = "data/stock_signals.csv"