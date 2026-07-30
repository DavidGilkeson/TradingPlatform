"""Signal-to-trade simulation for the Atlas backtesting engine."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .metrics import calculate_metrics
from .models import BacktestConfig, BacktestResult, OpenPosition, Trade


def _validate_signals(signals: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(signals, pd.DataFrame):
        raise TypeError("signals must be a pandas DataFrame.")
    if signals.empty:
        raise ValueError("signals cannot be empty.")
    if "Close" not in signals.columns:
        raise ValueError("signals must contain a Close column.")
    if "Signal" not in signals.columns:
        raise ValueError("signals must contain a Signal column.")

    clean = signals.copy()
    clean["Close"] = pd.to_numeric(clean["Close"], errors="coerce")
    clean["Signal"] = (
        clean["Signal"]
        .fillna("HOLD")
        .astype(str)
        .str.upper()
        .str.strip()
    )
    clean = clean.dropna(subset=["Close"]).sort_index()

    invalid = set(clean["Signal"].unique()) - {"BUY", "SELL", "HOLD"}
    if invalid:
        raise ValueError(
            "Unsupported signal values: " + ", ".join(sorted(invalid))
        )

    if clean.empty:
        raise ValueError("No usable signal rows remain after cleaning.")

    return clean


def _buy_price(close_price: float, slippage_pct: float) -> float:
    return close_price * (1 + slippage_pct)


def _sell_price(close_price: float, slippage_pct: float) -> float:
    return close_price * (1 - slippage_pct)


def run_backtest(
    signals: pd.DataFrame,
    *,
    strategy_name: str,
    config: BacktestConfig | None = None,
    metadata: dict[str, Any] | None = None,
) -> BacktestResult:
    """Run a single-asset, long-only backtest from strategy signals."""

    config = config or BacktestConfig()
    clean = _validate_signals(signals)

    cash = float(config.initial_capital)
    position: OpenPosition | None = None
    trades: list[Trade] = []
    equity_rows: list[dict[str, Any]] = []

    for bar_number, (date, row) in enumerate(clean.iterrows()):
        timestamp = pd.Timestamp(date)
        close_price = float(row["Close"])
        signal = str(row["Signal"])

        if signal == "BUY" and position is None:
            execution_price = _buy_price(close_price, config.slippage_pct)
            capital_to_use = cash * config.position_size_pct
            available_for_shares = capital_to_use - config.commission

            if available_for_shares > 0 and execution_price > 0:
                shares = available_for_shares / execution_price

                if shares > 0:
                    position = OpenPosition(
                        ticker=config.ticker,
                        entry_date=timestamp,
                        entry_price=execution_price,
                        shares=shares,
                        entry_commission=config.commission,
                        entry_bar=bar_number,
                        metadata={
                            "entry_signal": signal,
                        },
                    )
                    cash -= position.cost_basis

        elif signal == "SELL" and position is not None:
            execution_price = _sell_price(close_price, config.slippage_pct)
            proceeds = (execution_price * position.shares) - config.commission
            cash += proceeds

            pnl = (
                (execution_price - position.entry_price) * position.shares
                - position.entry_commission
                - config.commission
            )
            return_pct = pnl / position.cost_basis

            trades.append(
                Trade(
                    ticker=config.ticker,
                    entry_date=position.entry_date,
                    exit_date=timestamp,
                    entry_price=position.entry_price,
                    exit_price=execution_price,
                    shares=position.shares,
                    entry_commission=position.entry_commission,
                    exit_commission=config.commission,
                    pnl=pnl,
                    return_pct=return_pct,
                    bars_held=bar_number - position.entry_bar,
                    exit_reason="SELL",
                    metadata=position.metadata,
                )
            )
            position = None

        position_value = (
            position.shares * close_price
            if position is not None
            else 0.0
        )
        equity = cash + position_value

        equity_rows.append(
            {
                "Date": timestamp,
                "Close": close_price,
                "Signal": signal,
                "Cash": cash,
                "Position Value": position_value,
                "Equity": equity,
                "In Position": position is not None,
            }
        )

    if position is not None and config.close_open_position:
        final_date = pd.Timestamp(clean.index[-1])
        final_close = float(clean["Close"].iloc[-1])
        execution_price = _sell_price(final_close, config.slippage_pct)
        proceeds = (execution_price * position.shares) - config.commission
        cash += proceeds

        pnl = (
            (execution_price - position.entry_price) * position.shares
            - position.entry_commission
            - config.commission
        )
        return_pct = pnl / position.cost_basis

        trades.append(
            Trade(
                ticker=config.ticker,
                entry_date=position.entry_date,
                exit_date=final_date,
                entry_price=position.entry_price,
                exit_price=execution_price,
                shares=position.shares,
                entry_commission=position.entry_commission,
                exit_commission=config.commission,
                pnl=pnl,
                return_pct=return_pct,
                bars_held=(len(clean) - 1) - position.entry_bar,
                exit_reason="END_OF_DATA",
                metadata=position.metadata,
            )
        )

        position = None
        equity_rows[-1]["Cash"] = cash
        equity_rows[-1]["Position Value"] = 0.0
        equity_rows[-1]["Equity"] = cash
        equity_rows[-1]["In Position"] = False

    equity_curve = (
        pd.DataFrame(equity_rows)
        .set_index("Date")
        .sort_index()
    )

    metrics = calculate_metrics(equity_curve, trades, config)

    return BacktestResult(
        strategy_name=strategy_name,
        ticker=config.ticker,
        config=config,
        trades=trades,
        equity_curve=equity_curve,
        metrics=metrics,
        signals=clean,
        metadata=metadata or {},
    )
