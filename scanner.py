"""
scanner.py

Downloads stock data, calculates indicators, generates signals,
and returns a ranked results table.
"""

import pandas as pd
import yfinance as yf

from config import PERIOD, SHORT_MA, LONG_MA
from indicators import calculate_indicators, generate_signal


def scan_stocks(stocks):
    """
    Scan a list of stock tickers.

    Parameters:
        stocks (list): Stock ticker symbols to analyse.

    Returns:
        tuple:
            - pandas DataFrame containing the ranked results
            - dictionary containing chart data for each stock
    """

    # Store the summary results for the final table
    results = []

    # Store full price history so it can be reused for charts
    chart_data = {}

    # Analyse each ticker one at a time
    for ticker in stocks:
        print(f"Analysing {ticker}...")

        try:
            # Download historical daily stock data
            data = yf.download(
                ticker,
                period=PERIOD,
                progress=False
            )

            # Skip the ticker if Yahoo Finance returned no data
            if data.empty:
                print(f"Warning: No data returned for {ticker}. Skipping.")
                continue

            # Calculate moving averages and trend strength
            (
                close,
                ma_short,
                ma_long,
                latest_close,
                latest_ma_short,
                latest_ma_long,
                strength
            ) = calculate_indicators(
                data,
                SHORT_MA,
                LONG_MA
            )

            # Create a BUY, SELL, or HOLD signal
            signal = generate_signal(
                latest_ma_short,
                latest_ma_long
            )

            # Add the stock summary to the results list
            results.append({
                "Ticker": ticker,
                "Close": round(float(latest_close), 2),
                f"{SHORT_MA}-Day MA": round(float(latest_ma_short), 2),
                f"{LONG_MA}-Day MA": round(float(latest_ma_long), 2),
                "Strength (%)": round(float(strength), 2),
                "Signal": signal
            })

            # Save the full data for charting later
            chart_data[ticker] = {
                "close": close,
                "ma_short": ma_short,
                "ma_long": ma_long
            }

        except Exception as error:
            # Keep scanning other stocks if one ticker fails
            print(f"Error analysing {ticker}: {error}")

    # Convert the results list into a pandas DataFrame
    df = pd.DataFrame(results)

    # Only sort if at least one stock was analysed successfully
    if not df.empty:
        df = df.sort_values(
            by="Strength (%)",
            ascending=False
        ).reset_index(drop=True)

    return df, chart_data