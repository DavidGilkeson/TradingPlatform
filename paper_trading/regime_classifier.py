"""Automatic entry-time market regime classification for Atlas."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd


@dataclass(slots=True)
class MarketRegimeSnapshot:
    market_regime: str
    volatility_regime: str
    trend_strength: str
    benchmark_ticker: str
    benchmark_price: float
    ma50: float
    ma200: float
    price_vs_ma50_pct: float
    price_vs_ma200_pct: float
    realised_volatility_pct: float


def classify_regime_from_prices(
    prices: pd.Series,
    *,
    benchmark_ticker: str = "SPY",
) -> MarketRegimeSnapshot:
    """Classify the market from closing-price history known at decision time."""
    close = pd.to_numeric(prices, errors="coerce").dropna()

    if len(close) < 200:
        raise ValueError("At least 200 closing prices are required.")

    price = float(close.iloc[-1])
    ma50 = float(close.tail(50).mean())
    ma200 = float(close.tail(200).mean())

    price_vs_ma50_pct = (price / ma50 - 1.0) * 100.0
    price_vs_ma200_pct = (price / ma200 - 1.0) * 100.0

    returns = close.pct_change().dropna()
    realised_volatility_pct = float(
        returns.tail(20).std() * (252 ** 0.5) * 100.0
    )

    if price > ma50 > ma200:
        market_regime = "Bullish"
    elif price < ma50 < ma200:
        market_regime = "Bearish"
    else:
        market_regime = "Neutral"

    if realised_volatility_pct < 12:
        volatility_regime = "Quiet"
    elif realised_volatility_pct < 25:
        volatility_regime = "Normal"
    else:
        volatility_regime = "Volatile"

    distance = abs(price_vs_ma50_pct)
    if distance >= 5:
        trend_strength = "Strong"
    elif distance >= 2:
        trend_strength = "Moderate"
    else:
        trend_strength = "Weak"

    return MarketRegimeSnapshot(
        market_regime=market_regime,
        volatility_regime=volatility_regime,
        trend_strength=trend_strength,
        benchmark_ticker=benchmark_ticker.upper().strip(),
        benchmark_price=price,
        ma50=ma50,
        ma200=ma200,
        price_vs_ma50_pct=price_vs_ma50_pct,
        price_vs_ma200_pct=price_vs_ma200_pct,
        realised_volatility_pct=realised_volatility_pct,
    )


class YFinanceRegimeProvider:
    """Fetch SPY history and classify the current market environment."""

    def __init__(self, benchmark_ticker: str = "SPY"):
        self.benchmark_ticker = benchmark_ticker.upper().strip()

    def snapshot(self) -> MarketRegimeSnapshot:
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "yfinance is required for automatic regime detection."
            ) from exc

        data = yf.download(
            self.benchmark_ticker,
            period="18mo",
            progress=False,
            auto_adjust=False,
            threads=False,
        )

        if data is None or data.empty:
            raise ValueError(
                f"No market data returned for {self.benchmark_ticker}."
            )

        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]

        return classify_regime_from_prices(
            close,
            benchmark_ticker=self.benchmark_ticker,
        )
