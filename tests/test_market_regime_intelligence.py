import pandas as pd
import pytest

from paper_trading.market_regime import (
    classify_market_regime,
    regime_performance,
)
from paper_trading.regime_repository import TradeRegimeRepository


def test_bullish_lower_volatility():
    regime = classify_market_regime(
        close=110,
        ma_short=105,
        ma_long=100,
        volatility_pct=1.2,
    )
    assert regime.trend == "Bullish"
    assert regime.volatility == "Lower Volatility"


def test_bearish_high_volatility():
    regime = classify_market_regime(
        close=90,
        ma_short=95,
        ma_long=100,
        volatility_pct=3.5,
    )
    assert regime.label == "Bearish · High Volatility"


def test_sideways_regime():
    regime = classify_market_regime(
        close=100,
        ma_short=100.2,
        ma_long=100,
        volatility_pct=1,
        trend_buffer_pct=0.5,
    )
    assert regime.trend == "Sideways"


def test_mixed_regime():
    regime = classify_market_regime(
        close=99,
        ma_short=105,
        ma_long=100,
        volatility_pct=1,
    )
    assert regime.trend == "Mixed"


def test_invalid_prices_rejected():
    with pytest.raises(ValueError):
        classify_market_regime(
            close=0,
            ma_short=100,
            ma_long=100,
        )


def test_regime_performance_ranks_expectancy():
    trades = pd.DataFrame(
        {
            "trade_id": [1, 2, 3],
            "market_regime": ["Bullish", "Bullish", "Bearish"],
            "realised_pnl": [100, 50, -20],
            "return_pct": [10, 5, -2],
        }
    )
    result = regime_performance(trades)
    assert result.iloc[0]["market_regime"] == "Bullish"
    assert result.iloc[0]["Trades"] == 2


def test_regime_performance_respects_minimum():
    trades = pd.DataFrame(
        {
            "trade_id": [1, 2],
            "market_regime": ["Bullish", "Bearish"],
            "realised_pnl": [100, 200],
            "return_pct": [10, 20],
        }
    )
    assert regime_performance(trades, minimum_trades=2).empty


def test_repository_roundtrip(tmp_path):
    path = tmp_path / "regimes.db"
    repo = TradeRegimeRepository(str(path))
    repo.save(
        trade_id=42,
        market_regime="Bullish · Lower Volatility",
        trend_regime="Bullish",
        volatility_regime="Lower Volatility",
    )
    record = repo.get(42)
    assert record is not None
    assert record.market_regime == "Bullish · Lower Volatility"


def test_repository_upsert(tmp_path):
    path = tmp_path / "regimes.db"
    repo = TradeRegimeRepository(str(path))
    repo.save(
        trade_id=1,
        market_regime="Bullish",
        trend_regime="Bullish",
        volatility_regime="Lower Volatility",
    )
    repo.save(
        trade_id=1,
        market_regime="Bearish",
        trend_regime="Bearish",
        volatility_regime="High Volatility",
    )
    assert repo.get(1).market_regime == "Bearish"
