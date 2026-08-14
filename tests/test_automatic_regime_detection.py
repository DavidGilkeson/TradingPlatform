import numpy as np
import pandas as pd
import pytest

from paper_trading.regime_classifier import classify_regime_from_prices
from paper_trading.forward_testing import ForwardTestRepository


def test_bullish_regime():
    prices=pd.Series(np.linspace(100,200,220))
    result=classify_regime_from_prices(prices)
    assert result.market_regime=="Bullish"
    assert result.benchmark_ticker=="SPY"
    assert result.benchmark_price==pytest.approx(200)


def test_bearish_regime():
    prices=pd.Series(np.linspace(200,100,220))
    result=classify_regime_from_prices(prices)
    assert result.market_regime=="Bearish"


def test_flat_market_is_neutral():
    prices=pd.Series([100.0]*220)
    result=classify_regime_from_prices(prices)
    assert result.market_regime=="Neutral"
    assert result.volatility_regime=="Quiet"
    assert result.trend_strength=="Weak"


def test_requires_200_prices():
    with pytest.raises(ValueError):
        classify_regime_from_prices(pd.Series(range(50)))


def test_regime_snapshot_evidence_persists(tmp_path):
    repo=ForwardTestRepository(str(tmp_path/"regime.db"))
    repo.record(
        account_id=1,
        ticker="AAPL",
        decision="WATCH",
        market_price=100,
        market_regime="Bullish",
        volatility_regime="Normal",
        trend_strength="Strong",
        regime_benchmark="SPY",
        regime_benchmark_price=500,
        regime_ma50=490,
        regime_ma200=450,
        regime_price_vs_ma50_pct=2.04,
        regime_price_vs_ma200_pct=11.11,
        regime_volatility_pct=18.5,
    )

    frame=repo.history(1)
    row=frame.iloc[0]

    assert row["trend_strength"]=="Strong"
    assert row["regime_benchmark"]=="SPY"
    assert row["regime_benchmark_price"]==pytest.approx(500)
    assert row["regime_volatility_pct"]==pytest.approx(18.5)


def test_regime_schema_migrates(tmp_path):
    repo=ForwardTestRepository(str(tmp_path/"migration.db"))

    with repo.database.connect() as connection:
        columns={
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(paper_forward_tests)"
            ).fetchall()
        }

    required={
        "trend_strength",
        "regime_benchmark",
        "regime_benchmark_price",
        "regime_ma50",
        "regime_ma200",
        "regime_price_vs_ma50_pct",
        "regime_price_vs_ma200_pct",
        "regime_volatility_pct",
    }
    assert required <= columns
