"""Unit tests for the Atlas universal backtesting engine."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from backtesting import (
    BacktestConfig,
    backtest_strategy,
    calculate_drawdown,
    compare_strategies,
    run_backtest,
)


def _signals() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Close": [100, 102, 105, 103, 108, 110],
            "Signal": ["BUY", "HOLD", "HOLD", "SELL", "BUY", "SELL"],
        },
        index=pd.date_range("2026-01-01", periods=6, freq="D"),
    )


def test_backtest_generates_trades_and_equity_curve() -> None:
    result = run_backtest(
        _signals(),
        strategy_name="Test Strategy",
        config=BacktestConfig(
            ticker="TEST",
            initial_capital=10_000,
            commission=0,
            slippage_pct=0,
        ),
    )

    assert len(result.trades) == 2
    assert len(result.equity_curve) == 6
    assert result.metrics["total_trades"] == 2
    assert result.metrics["final_equity"] > 10_000


def test_commission_and_slippage_reduce_returns() -> None:
    clean = run_backtest(
        _signals(),
        strategy_name="Clean",
        config=BacktestConfig(
            ticker="TEST",
            commission=0,
            slippage_pct=0,
        ),
    )
    costly = run_backtest(
        _signals(),
        strategy_name="Costly",
        config=BacktestConfig(
            ticker="TEST",
            commission=10,
            slippage_pct=0.005,
        ),
    )

    assert costly.metrics["final_equity"] < clean.metrics["final_equity"]


def test_open_position_is_closed_at_end_of_data() -> None:
    signals = pd.DataFrame(
        {
            "Close": [100, 105, 110],
            "Signal": ["BUY", "HOLD", "HOLD"],
        },
        index=pd.date_range("2026-01-01", periods=3, freq="D"),
    )

    result = run_backtest(
        signals,
        strategy_name="Open Position",
        config=BacktestConfig(ticker="TEST", close_open_position=True),
    )

    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "END_OF_DATA"


def test_invalid_signal_is_rejected() -> None:
    signals = _signals()
    signals.loc[signals.index[0], "Signal"] = "WAIT"

    with pytest.raises(ValueError, match="Unsupported signal"):
        run_backtest(signals, strategy_name="Invalid")


def test_drawdown_detects_peak_decline() -> None:
    equity = pd.Series(
        [100, 120, 90, 110],
        index=pd.date_range("2026-01-01", periods=4),
    )
    drawdown = calculate_drawdown(equity)

    assert drawdown["Drawdown Pct"].min() == pytest.approx(-0.25)


def test_position_size_preserves_unused_cash() -> None:
    result = run_backtest(
        _signals(),
        strategy_name="Half Size",
        config=BacktestConfig(
            ticker="TEST",
            initial_capital=10_000,
            position_size_pct=0.5,
        ),
    )

    first_entry_row = result.equity_curve.iloc[0]
    assert first_entry_row["Cash"] > 4_900


class DummyStrategyResult:
    def __init__(self, signals: pd.DataFrame) -> None:
        self.strategy_name = "Dummy"
        self.signals = signals
        self.metadata = {}


class DummyStrategy:
    name = "Dummy"

    def run(self, data: pd.DataFrame) -> DummyStrategyResult:
        signals = data.copy()
        signals["Signal"] = "HOLD"
        signals.iloc[0, signals.columns.get_loc("Signal")] = "BUY"
        signals.iloc[-1, signals.columns.get_loc("Signal")] = "SELL"
        return DummyStrategyResult(signals)


def test_strategy_runner_accepts_common_strategy_interface() -> None:
    data = pd.DataFrame(
        {"Close": np.linspace(100, 120, 30)},
        index=pd.date_range("2026-01-01", periods=30),
    )

    result = backtest_strategy(
        DummyStrategy(),
        data,
        config=BacktestConfig(ticker="TEST"),
    )

    assert result.strategy_name == "Dummy"
    assert result.metrics["total_trades"] == 1


def test_strategy_comparison_returns_ranked_table() -> None:
    data = pd.DataFrame(
        {"Close": np.linspace(100, 120, 30)},
        index=pd.date_range("2026-01-01", periods=30),
    )

    comparison, results = compare_strategies(
        {
            "dummy_one": DummyStrategy(),
            "dummy_two": DummyStrategy(),
        },
        data,
        config=BacktestConfig(ticker="TEST"),
    )

    assert len(comparison) == 2
    assert set(results) == {"dummy_one", "dummy_two"}
    assert comparison.index.name == "Rank"
