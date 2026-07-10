"""
charts.py

Contains functions used to display stock-price charts.
"""

import matplotlib.pyplot as plt

from config import SHORT_MA, LONG_MA


def plot_chart(ticker, close, ma_short, ma_long):
    """
    Display the closing price and moving averages for a stock.

    Parameters:
        ticker (str): Stock ticker symbol.
        close (pandas.Series): Historical closing prices.
        ma_short (pandas.Series): Short-term moving average.
        ma_long (pandas.Series): Long-term moving average.
    """

    # Create the chart window
    plt.figure(figsize=(14, 6))

    # Plot the closing price and moving averages
    plt.plot(close, label="Closing Price")
    plt.plot(
        ma_short,
        label=f"{SHORT_MA}-Day Moving Average"
    )
    plt.plot(
        ma_long,
        label=f"{LONG_MA}-Day Moving Average"
    )

    # Add chart information
    plt.title(f"{ticker} Stock Analysis")
    plt.xlabel("Date")
    plt.ylabel("Price ($)")

    # Display the chart legend and grid
    plt.legend()
    plt.grid(True)

    # Adjust spacing and display the chart
    plt.tight_layout()
    plt.show()