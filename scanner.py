"""
scanner.py

Downloads stock data in one batch, calculates indicators,
generates trading signals, and ranks the results.
"""

import pandas as pd
import yfinance as yf

from config import PERIOD, SHORT_MA, LONG_MA
from indicators import calculate_indicators, generate_signal
from strategy import calculate_score


def scan_stocks(stocks):
    """
    Scan multiple stock tickers using one batch download.

    Parameters:
        stocks (list): Ticker symbols to analyse.

    Returns:
        tuple:
            - DataFrame containing ranked stock results
            - Dictionary containing data used for charts
    """

    # Store the summary results
    results = []

    # Store each stock's historical data for charting
    chart_data = {}

    print(f"Downloading market data for {len(stocks)} stocks...")

    try:
        # Download all stocks together instead of making
        # a separate request for every ticker
        batch_data = yf.download(
            tickers=stocks,
            period=PERIOD,
            group_by="ticker",
            auto_adjust=False,
            progress=True,
            threads=True
        )

    except Exception as error:
        print(f"Batch download failed: {error}")
        return pd.DataFrame(), {}

    # Stop if Yahoo Finance returned no data
    if batch_data.empty:
        print("No market data was downloaded.")
        return pd.DataFrame(), {}

    print("\nDownload completed. Analysing stocks...")

    # Analyse each ticker using the already-downloaded data
    for ticker in stocks:
        try:
            # Extract this ticker's data from the batch
            data = batch_data[ticker].copy()

            # Remove rows containing no price information
            data = data.dropna(how="all")

            # Skip stocks with no usable data
            if data.empty:
                print(f"Warning: No data for {ticker}. Skipping.")
                continue

            # We need enough rows to calculate the long moving average
            if len(data) < LONG_MA:
                print(
                    f"Warning: Not enough data for {ticker}. "
                    f"Only {len(data)} trading days found."
                )
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

            # Skip the stock if its latest values are missing
            if pd.isna(latest_close):
                print(f"Warning: Missing closing price for {ticker}.")
                continue

            if pd.isna(latest_ma_short) or pd.isna(latest_ma_long):
                print(f"Warning: Missing moving averages for {ticker}.")
                continue

            # Generate the BUY, SELL, or HOLD signal
            signal = generate_signal(
                latest_ma_short,
                latest_ma_long
            )
            
            score = calculate_score(signal, strength)

            # Add this stock to the results table
            results.append({
                "Ticker": ticker,
                "Close": round(float(latest_close), 2),

                f"{SHORT_MA}-Day MA": round(
                    float(latest_ma_short),
                    2
                ),
                f"{LONG_MA}-Day MA": round(
                    float(latest_ma_long),
                    2
                ),
                "Strength (%)": round(float(strength), 2),
                "Signal": signal,
                "Score": score
            })

            # Keep the historical data for charting
            chart_data[ticker] = {
                "close": close,
                "ma_short": ma_short,
                "ma_long": ma_long
            }

        except KeyError:
            # This happens when a ticker was not returned
            # in the batch download
            print(f"Warning: {ticker} was not downloaded. Skipping.")

        except Exception as error:
            # One failed ticker should not stop the full scanner
            print(f"Error analysing {ticker}: {error}")

    # Convert the collected results into a DataFrame
    df = pd.DataFrame(results)

    # Rank stocks from strongest to weakest
    if not df.empty:
        df = (
            df.sort_values(
                by=["Score", "Strength (%)"],
                ascending=[False, False]
            )
            .reset_index(drop=True)
        )

    print(f"\nSuccessfully analysed {len(df)} stocks.")

    return df, chart_data