"""
watchlist.py

Handles loading, saving and updating the Project Atlas watchlist.
"""

import json
import os

WATCHLIST_FILE = "watchlist.json"


def load_watchlist():
    """Load saved ticker symbols from disk."""

    if not os.path.exists(WATCHLIST_FILE):
        return []

    try:
        with open(WATCHLIST_FILE, "r", encoding="utf-8") as file:
            watchlist = json.load(file)

        return sorted(set(watchlist))

    except (json.JSONDecodeError, OSError):
        return []


def save_watchlist(watchlist):
    """Save ticker symbols to disk."""

    cleaned_watchlist = sorted(
        {
            str(ticker).strip().upper()
            for ticker in watchlist
            if str(ticker).strip()
        }
    )

    with open(WATCHLIST_FILE, "w", encoding="utf-8") as file:
        json.dump(
            cleaned_watchlist,
            file,
            indent=4
        )


def add_stock(watchlist, ticker):
    """Add one ticker to the watchlist."""

    updated_watchlist = set(watchlist)
    updated_watchlist.add(ticker.strip().upper())

    updated_watchlist = sorted(updated_watchlist)
    save_watchlist(updated_watchlist)

    return updated_watchlist


def remove_stock(watchlist, ticker):
    """Remove one ticker from the watchlist."""

    updated_watchlist = {
        stock
        for stock in watchlist
        if stock != ticker.strip().upper()
    }

    updated_watchlist = sorted(updated_watchlist)
    save_watchlist(updated_watchlist)

    return updated_watchlist


def replace_watchlist(tickers):
    """Replace the full saved watchlist."""

    save_watchlist(tickers)
    return load_watchlist()