"""
scanner.py

Downloads market data in small stable batches, calculates indicators,
scores each stock, and returns ranked results.
"""

import gc
import time

import pandas as pd
import yfinance as yf

from config import PERIOD, SHORT_MA, LONG_MA
from indicators import calculate_indicators, generate_signal
from strategy import calculate_score, confidence_rating


def scan_stocks(stocks):
    """
    Scan stock tickers in small batches.

    Parameters:
        stocks (list): Ticker symbols to analyse.

    Returns:
        tuple:
            - Ranked pandas DataFrame
            - Dictionary containing chart data
    """

    results = []
    chart_data = {}

    # Smaller batches reduce memory use and improve stability
    batch_size = 25

    total_batches = (
        len(stocks) + batch_size - 1
    ) // batch_size

    print(f"Downloading market data for {len(stocks)} stocks...")

    for start in range(0, len(stocks), batch_size):
        ticker_batch = stocks[start:start + batch_size]

        batch_number = (start // batch_size) + 1

        print(
            f"Downloading batch {batch_number}/{total_batches} "
            f"({len(ticker_batch)} stocks)..."
        )

        try:
            # Disable threading because the process was terminating
            # during larger threaded downloads
            batch_data = yf.download(
                tickers=ticker_batch,
                period=PERIOD,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=30
            )

        except Exception as error:
            print(f"Batch {batch_number} failed: {error}")
            continue

        if batch_data.empty:
            print(f"Batch {batch_number} returned no data.")
            continue

        # Analyse this batch immediately rather than storing
        # every downloaded batch in memory
        for ticker in ticker_batch:
            try:
                data = batch_data[ticker].copy()
                data = data.dropna(how="all")

                if data.empty:
                    print(f"Warning: No data for {ticker}. Skipping.")
                    continue

                if len(data) < LONG_MA:
                    print(
                        f"Warning: Not enough data for {ticker}. "
                        f"Only {len(data)} trading days found."
                    )
                    continue

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

                required_values = [
                    latest_close,
                    latest_ma_short,
                    latest_ma_long,
                    latest_rsi,
                    latest_volume,
                    average_volume,
                    strength
                ]

                if any(pd.isna(value) for value in required_values):
                    print(
                        f"Warning: Incomplete indicator data "
                        f"for {ticker}. Skipping."
                    )
                    continue

                signal = generate_signal(
                    latest_ma_short,
                    latest_ma_long
                )

                score, reasons = calculate_score(
                    signal,
                    strength,
                    latest_rsi,
                    latest_volume,
                    average_volume
                )

                confidence = confidence_rating(score)

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
                    "Strength (%)": round(
                        float(strength),
                        2
                    ),
                    "RSI": round(float(latest_rsi), 2),
                    "Volume": int(latest_volume),
                    "Average Volume": int(average_volume),
                    "Signal": signal,
                    "Score": score,
                    "Confidence": confidence,
                    "Reasons": ", ".join(reasons)
                })

                chart_data[ticker] = {
                    "open": data["Open"].squeeze(),
                    "high": data["High"].squeeze(),
                    "low": data["Low"].squeeze(),
                    "close": close,
                    "volume": data["Volume"].squeeze(),
                    "ma_short": ma_short,
                    "ma_long": ma_long,
                    "rsi": rsi
                }

            except KeyError:
                print(
                    f"Warning: {ticker} was not returned "
                    f"in batch {batch_number}."
                )

            except Exception as error:
                print(f"Error analysing {ticker}: {error}")

        # Release the completed batch before downloading the next one
        del batch_data
        gc.collect()

        # Brief pause reduces pressure on Yahoo Finance
        time.sleep(1)

    df = pd.DataFrame(results)

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