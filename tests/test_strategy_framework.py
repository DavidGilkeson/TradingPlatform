"""Tests for the Atlas modular strategy framework."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from strategies import (
    BaseStrategy,
    get_strategy,
    load_strategies,
    strategy_options,
)


@pytest.fixture()
def market_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    periods = 180
    returns = rng.normal(0.0008, 0.018, periods)
    close = 100 * np.cumprod(1 + returns)
    volume = rng.integers(800_000, 2_000_000, periods)

    return pd.DataFrame(
        {
            "Close": close,
            "Volume": volume,
        },
        index=pd.date_range("2025-01-01", periods=periods, freq="B"),
    )


def test_all_registered_strategies_load() -> None:
    loaded = load_strategies()

    assert len(loaded) >= 4
    assert all(isinstance(strategy, BaseStrategy) for strategy in loaded.values())


@pytest.mark.parametrize(
    "strategy_key",
    [
        "moving_average_cross",
        "rsi_pullback",
        "momentum",
        "atlas_composite",
    ],
)
def test_strategy_returns_standard_result(
    strategy_key: str,
    market_data: pd.DataFrame,
) -> None:
    result = get_strategy(strategy_key).run(market_data)

    assert result.strategy_name
    assert "Signal" in result.signals.columns
    assert set(result.signals["Signal"].unique()) <= {"BUY", "SELL", "HOLD"}
    assert (
        result.buy_count + result.sell_count + result.hold_count
        == len(result.signals)
    )


def test_strategy_does_not_mutate_input(market_data: pd.DataFrame) -> None:
    original = market_data.copy(deep=True)

    get_strategy("atlas_composite").run(market_data)

    pd.testing.assert_frame_equal(market_data, original)


def test_missing_close_column_is_rejected() -> None:
    with pytest.raises(ValueError, match="Missing required columns"):
        get_strategy("momentum").run(pd.DataFrame({"Open": [1, 2, 3]}))


def test_unknown_strategy_is_rejected() -> None:
    with pytest.raises(KeyError, match="Unknown strategy"):
        get_strategy("does_not_exist")


def test_strategy_options_are_ui_friendly() -> None:
    options = strategy_options()

    assert options["moving_average_cross"] == "Moving Average Cross"
    assert options["atlas_composite"] == "Atlas Composite"
