"""
scanner.py

Downloads S&P 500 market data in a batch, calculates indicators,
generates trading signals, scores each stock, and ranks the results.
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
        stocks (list): Stock ticker symbols to analyse.

    Returns:
        tuple:
            - pandas.DataFrame containing ranked results
            - dictionary containing chart data for each stock
    """

    # Store the summary results for the final table
    results = []

    # Store historical data for charting
    chart_data = {}

    print(f"Downloading market data for {len(stocks)} stocks...")

    try:
        # Download all stocks together for better performance
        batch_data = yf.download(
            tickers=stocks,
            period=PERIOD,
            group_by="ticker",
            auto_adjust=False,
            progress=False,
            threads=True
        )

    except Exception as error:
        print(f"Batch download failed: {error}")
        return pd.DataFrame(), {}

    # Stop if no data was returned
    if batch_data.empty:
        print("No market data was downloaded.")
        return pd.DataFrame(), {}

    print("\nDownload completed. Analysing stocks...")

    # Analyse each stock using the downloaded batch data
    for ticker in stocks:
        try:
            # Extract one stock's data from the batch
            data = batch_data[ticker].copy()

            # Remove rows where every value is missing
            data = data.dropna(how="all")

            # Skip stocks with no usable data
            if data.empty:
                print(f"Warning: No data for {ticker}. Skipping.")
                continue

            # Ensure there is enough history for the long moving average
            if len(data) < LONG_MA:
                print(
                    f"Warning: Not enough data for {ticker}. "
                    f"Only {len(data)} trading days found."
                )
                continue

            # Calculate all technical indicators
            (
                close,
                ma_short,
                ma_long,
                rsi,
                latest_close,
                latest_ma_short,
                latest_ma_long,
                latest_rsi,
                latest_volume,
                average_volume,
                strength
            ) = calculate_indicators(
                data,
                SHORT_MA,
                LONG_MA
            )

            # Skip incomplete results
            if pd.isna(latest_close):
                print(f"Warning: Missing closing price for {ticker}.")
                continue

            if pd.isna(latest_ma_short) or pd.isna(latest_ma_long):
                print(f"Warning: Missing moving averages for {ticker}.")
                continue

            if pd.isna(latest_rsi):
                print(f"Warning: Missing RSI for {ticker}.")
                continue

            if pd.isna(latest_volume) or pd.isna(average_volume):
                print(f"Warning: Missing volume data for {ticker}.")
                continue

            # Generate the basic BUY, SELL, or HOLD signal
            signal = generate_signal(
                latest_ma_short,
                latest_ma_long
            )

            # Calculate the overall score and explanatory reasons
            score, reasons = calculate_score(
                signal,
                strength,
                latest_rsi,
                latest_volume,
                average_volume
            )

            # Store the stock's summary data
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
                "RSI": round(float(latest_rsi), 2),
                "Volume": int(latest_volume),
                "Average Volume": int(average_volume),
                "Signal": signal,
                "Score": score,
                "Reasons": ", ".join(reasons)
            })

            # Keep the historical data for charting later
            chart_data[ticker] = {
                "close": close,
                "ma_short": ma_short,
                "ma_long": ma_long,
                "rsi": rsi
            }

        except KeyError:
            # This may happen if Yahoo did not return the ticker
            print(f"Warning: {ticker} was not downloaded. Skipping.")

        except Exception as error:
            # One failed stock should not stop the whole scan
            print(f"Error analysing {ticker}: {error}")

    # Convert the result dictionaries into a DataFrame
    df = pd.DataFrame(results)

    # Rank stocks by score, then by trend strength
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