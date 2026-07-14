"""
watchlist.py

Handles loading and saving the Project Atlas watchlist.
"""

import json
import os

WATCHLIST_FILE = "watchlist.json"


def load_watchlist():
    """
    Load the watchlist from disk.
    """

    if not os.path.exists(WATCHLIST_FILE):
        return []

    with open(WATCHLIST_FILE, "r") as file:
        return json.load(file)


def save_watchlist(watchlist):
    """
    Save the watchlist.
    """

    with open(WATCHLIST_FILE, "w") as file:
        json.dump(
            watchlist,
            file,
            indent=4
        )


def add_stock(watchlist, ticker):
    """
    Add a stock if it doesn't already exist.
    """

    ticker = ticker.upper()

    if ticker not in watchlist:
        watchlist.append(ticker)

    watchlist.sort()

    save_watchlist(watchlist)

    return watchlist


def remove_stock(watchlist, ticker):
    """
    Remove a stock.
    """

    ticker = ticker.upper()

    if ticker in watchlist:
        watchlist.remove(ticker)

    save_watchlist(watchlist)

    return watchlist