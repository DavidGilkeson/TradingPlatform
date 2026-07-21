"""
scanner.py

Downloads market data in small stable batches, calculates indicators,
scores each stock, applies the Atlas Decision Engine, and returns
ranked results with chart data.
"""

from __future__ import annotations

import gc
import time
from typing import Any

import pandas as pd
import yfinance as yf

from config import LONG_MA, PERIOD, SHORT_MA
from decision_engine import evaluate_stock
from indicators import calculate_indicators, generate_signal
from strategy import calculate_score, confidence_rating


def _build_decision_metrics(
    *,
    ticker: str,
    latest_close: float,
    latest_ma_short: float,
    latest_ma_long: float,
    latest_rsi: float,
    latest_volume: float,
    average_volume: float,
    strength: float,
    scanner_score: float,
) -> dict[str, Any]:
    """Build the metric dictionary expected by the Atlas Decision Engine."""

    relative_volume = (
        float(latest_volume) / float(average_volume)
        if average_volume and average_volume > 0
        else 1.0
    )

    return {
        "Ticker": ticker,
        "price": float(latest_close),
        "close": float(latest_close),
        "current_price": float(latest_close),
        "ma20": float(latest_ma_short),
        "ma50": float(latest_ma_long),
        "rsi": float(latest_rsi),
        "strength": float(strength),
        "strength_percent": float(strength),
        "relative_volume": relative_volume,
        "volume_change_percent": (relative_volume - 1.0) * 100.0,
        "momentum_score": float(scanner_score),
    }


def _build_result_row(
    *,
    ticker: str,
    latest_close: float,
    latest_ma_short: float,
    latest_ma_long: float,
    latest_rsi: float,
    latest_volume: float,
    average_volume: float,
    strength: float,
    signal: str,
    score: float,
    confidence: str,
    reasons: list[str],
) -> dict[str, Any]:
    """Build one scanner result row with original and Atlas ratings."""

    decision_metrics = _build_decision_metrics(
        ticker=ticker,
        latest_close=latest_close,
        latest_ma_short=latest_ma_short,
        latest_ma_long=latest_ma_long,
        latest_rsi=latest_rsi,
        latest_volume=latest_volume,
        average_volume=average_volume,
        strength=strength,
        scanner_score=score,
    )

    decision = evaluate_stock(decision_metrics)

    relative_volume = (
        float(latest_volume) / float(average_volume)
        if average_volume and average_volume > 0
        else 1.0
    )

    return {
        "Ticker": ticker,
        "Close": round(float(latest_close), 2),
        f"{SHORT_MA}-Day MA": round(float(latest_ma_short), 2),
        f"{LONG_MA}-Day MA": round(float(latest_ma_long), 2),
        "Strength (%)": round(float(strength), 2),
        "RSI": round(float(latest_rsi), 2),
        "Volume": int(latest_volume),
        "Average Volume": int(average_volume),
        "Relative Volume": round(relative_volume, 2),
        "Signal": signal,
        "Score": round(float(score), 2),
        "Confidence": confidence,
        "Reasons": ", ".join(reasons),
        "Atlas Score": round(float(decision["score"]), 2),
        "Atlas Grade": decision["grade"],
        "Atlas Verdict": decision["verdict"],
        "Atlas Confidence": decision["confidence"],
        "Atlas Stars": decision["star_display"],
        "Atlas Strengths": " | ".join(decision["strengths"]),
        "Atlas Weaknesses": " | ".join(decision["weaknesses"]),
    }


def _build_chart_data(
    data: pd.DataFrame,
    close: pd.Series,
    ma_short: pd.Series,
    ma_long: pd.Series,
    rsi: pd.Series,
) -> dict[str, pd.Series]:
    """Build the chart-data dictionary stored for one ticker."""

    return {
        "open": data["Open"].squeeze(),
        "high": data["High"].squeeze(),
        "low": data["Low"].squeeze(),
        "close": close,
        "volume": data["Volume"].squeeze(),
        "ma_short": ma_short,
        "ma_long": ma_long,
        "rsi": rsi,
    }


def scan_stocks(
    stocks: list[str],
) -> tuple[pd.DataFrame, dict[str, dict[str, pd.Series]]]:
    """
    Scan stock tickers in small batches.

    Parameters
    ----------
    stocks:
        Ticker symbols to analyse.

    Returns
    -------
    tuple
        Ranked pandas DataFrame and a dictionary containing chart data.
    """

    results: list[dict[str, Any]] = []
    chart_data: dict[str, dict[str, pd.Series]] = {}

    batch_size = 25
    total_batches = (len(stocks) + batch_size - 1) // batch_size

    print(f"Downloading market data for {len(stocks)} stocks...")

    for start in range(0, len(stocks), batch_size):
        ticker_batch = stocks[start : start + batch_size]
        batch_number = (start // batch_size) + 1

        print(
            f"Downloading batch {batch_number}/{total_batches} "
            f"({len(ticker_batch)} stocks)..."
        )

        try:
            batch_data = yf.download(
                tickers=ticker_batch,
                period=PERIOD,
                group_by="ticker",
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=30,
            )
        except Exception as error:
            print(f"Batch {batch_number} failed: {error}")
            continue

        if batch_data.empty:
            print(f"Batch {batch_number} returned no data.")
            continue

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
                    strength,
                ) = calculate_indicators(data, SHORT_MA, LONG_MA)

                required_values = [
                    latest_close,
                    latest_ma_short,
                    latest_ma_long,
                    latest_rsi,
                    latest_volume,
                    average_volume,
                    strength,
                ]

                if any(pd.isna(value) for value in required_values):
                    print(
                        f"Warning: Incomplete indicator data for "
                        f"{ticker}. Skipping."
                    )
                    continue

                signal = generate_signal(
                    latest_ma_short,
                    latest_ma_long,
                )

                score, reasons = calculate_score(
                    signal,
                    strength,
                    latest_rsi,
                    latest_volume,
                    average_volume,
                )

                confidence = confidence_rating(score)

                result_row = _build_result_row(
                    ticker=ticker,
                    latest_close=latest_close,
                    latest_ma_short=latest_ma_short,
                    latest_ma_long=latest_ma_long,
                    latest_rsi=latest_rsi,
                    latest_volume=latest_volume,
                    average_volume=average_volume,
                    strength=strength,
                    signal=signal,
                    score=score,
                    confidence=confidence,
                    reasons=reasons,
                )

                results.append(result_row)

                chart_data[ticker] = _build_chart_data(
                    data=data,
                    close=close,
                    ma_short=ma_short,
                    ma_long=ma_long,
                    rsi=rsi,
                )

            except KeyError:
                print(
                    f"Warning: {ticker} was not returned "
                    f"in batch {batch_number}."
                )

            except Exception as error:
                print(f"Error analysing {ticker}: {error}")

        del batch_data
        gc.collect()
        time.sleep(1)

    df = pd.DataFrame(results)

    if not df.empty:
        sort_columns = [
            column
            for column in ["Atlas Score", "Score", "Strength (%)"]
            if column in df.columns
        ]

        df = df.sort_values(
            by=sort_columns,
            ascending=[False] * len(sort_columns),
        ).reset_index(drop=True)

    print(f"\nSuccessfully analysed {len(df)} stocks.")

    return df, chart_data