"""Performance metrics for Atlas backtests."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .equity_curve import calculate_drawdown, daily_returns
from .models import BacktestConfig, Trade


def _safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0 or not math.isfinite(denominator):
        return None
    value = numerator / denominator
    return float(value) if math.isfinite(value) else None


def _cagr(
    initial_capital: float,
    final_equity: float,
    periods: int,
    annual_periods: int,
) -> float | None:
    if initial_capital <= 0 or final_equity <= 0 or periods <= 0:
        return None

    years = periods / annual_periods
    if years <= 0:
        return None

    return float((final_equity / initial_capital) ** (1 / years) - 1)


def calculate_metrics(
    equity_curve: pd.DataFrame,
    trades: list[Trade],
    config: BacktestConfig,
) -> dict[str, float | int | None]:
    """Calculate professional performance metrics for a backtest."""

    if equity_curve.empty:
        final_equity = config.initial_capital
        periods = 0
    else:
        final_equity = float(equity_curve["Equity"].iloc[-1])
        periods = max(len(equity_curve) - 1, 0)

    total_return = final_equity / config.initial_capital - 1.0
    returns = daily_returns(equity_curve)
    excess_returns = returns - (config.risk_free_rate / config.annual_periods)

    volatility = (
        float(returns.std(ddof=1) * math.sqrt(config.annual_periods))
        if len(returns) > 1
        else 0.0
    )

    sharpe = None
    if len(excess_returns) > 1 and excess_returns.std(ddof=1) > 0:
        sharpe = float(
            excess_returns.mean()
            / excess_returns.std(ddof=1)
            * math.sqrt(config.annual_periods)
        )

    downside = excess_returns[excess_returns < 0]
    sortino = None
    if len(downside) > 1 and downside.std(ddof=1) > 0:
        sortino = float(
            excess_returns.mean()
            / downside.std(ddof=1)
            * math.sqrt(config.annual_periods)
        )

    drawdown_frame = calculate_drawdown(equity_curve["Equity"])
    max_drawdown = (
        float(drawdown_frame["Drawdown Pct"].min())
        if not drawdown_frame.empty
        else 0.0
    )

    cagr = _cagr(
        config.initial_capital,
        final_equity,
        periods,
        config.annual_periods,
    )

    calmar = None
    if cagr is not None and max_drawdown < 0:
        calmar = _safe_ratio(cagr, abs(max_drawdown))

    winning_trades = [trade for trade in trades if trade.pnl > 0]
    losing_trades = [trade for trade in trades if trade.pnl < 0]
    total_trades = len(trades)

    win_rate = (
        len(winning_trades) / total_trades
        if total_trades
        else 0.0
    )

    gross_profit = float(sum(trade.pnl for trade in winning_trades))
    gross_loss = abs(float(sum(trade.pnl for trade in losing_trades)))

    profit_factor = None
    if gross_loss > 0:
        profit_factor = gross_profit / gross_loss
    elif gross_profit > 0:
        profit_factor = float("inf")

    average_win = (
        float(np.mean([trade.pnl for trade in winning_trades]))
        if winning_trades
        else 0.0
    )
    average_loss = (
        float(np.mean([trade.pnl for trade in losing_trades]))
        if losing_trades
        else 0.0
    )
    average_trade = (
        float(np.mean([trade.pnl for trade in trades]))
        if trades
        else 0.0
    )
    average_return_pct = (
        float(np.mean([trade.return_pct for trade in trades]))
        if trades
        else 0.0
    )
    average_holding_period = (
        float(np.mean([trade.bars_held for trade in trades]))
        if trades
        else 0.0
    )

    expectancy = (
        (win_rate * average_win)
        + ((1 - win_rate) * average_loss)
        if trades
        else 0.0
    )

    exposure = (
        float(pd.to_numeric(equity_curve["Position Value"]).gt(0).mean())
        if not equity_curve.empty and "Position Value" in equity_curve.columns
        else 0.0
    )

    recovery_factor = None
    total_profit = final_equity - config.initial_capital
    max_drawdown_amount = (
        abs(float(drawdown_frame["Drawdown"].min()))
        if not drawdown_frame.empty
        else 0.0
    )
    if max_drawdown_amount > 0:
        recovery_factor = total_profit / max_drawdown_amount

    return {
        "initial_capital": float(config.initial_capital),
        "final_equity": final_equity,
        "net_profit": total_profit,
        "total_return": total_return,
        "cagr": cagr,
        "annualised_volatility": volatility,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": max_drawdown,
        "calmar_ratio": calmar,
        "recovery_factor": recovery_factor,
        "total_trades": total_trades,
        "winning_trades": len(winning_trades),
        "losing_trades": len(losing_trades),
        "win_rate": win_rate,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": profit_factor,
        "average_win": average_win,
        "average_loss": average_loss,
        "average_trade": average_trade,
        "average_return_pct": average_return_pct,
        "expectancy": expectancy,
        "average_holding_period": average_holding_period,
        "exposure": exposure,
    }
