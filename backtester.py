"""
backtester.py

Backtests the moving-average crossover strategy used by Project Atlas.
"""

import pandas as pd


def run_backtest(
    open_prices,
    close_prices,
    ma_short,
    ma_long,
    starting_balance=10_000
):
    """
    Backtest a moving-average crossover strategy.

    Rules:
    - Buy at the next day's opening price after a bullish crossover.
    - Sell at the next day's opening price after a bearish crossover.
    - Invest the full available balance in each position.
    """

    data = pd.DataFrame({
        "Open": open_prices,
        "Close": close_prices,
        "MA Short": ma_short,
        "MA Long": ma_long
    }).dropna()

    if len(data) < 2:
        raise ValueError("Not enough historical data to run the backtest.")

    # Identify crossover signals
    data["Bullish Cross"] = (
        (data["MA Short"] > data["MA Long"])
        & (data["MA Short"].shift(1) <= data["MA Long"].shift(1))
    )

    data["Bearish Cross"] = (
        (data["MA Short"] < data["MA Long"])
        & (data["MA Short"].shift(1) >= data["MA Long"].shift(1))
    )

    cash = float(starting_balance)
    shares = 0.0

    entry_price = None
    entry_date = None

    trades = []
    equity_values = []

    # A signal generated on one trading day is executed
    # at the next trading day's opening price.
    for index in range(1, len(data)):
        previous_row = data.iloc[index - 1]
        current_row = data.iloc[index]
        current_date = data.index[index]

        if previous_row["Bullish Cross"] and shares == 0:
            entry_price = float(current_row["Open"])
            entry_date = current_date

            shares = cash / entry_price
            cash = 0.0

        elif previous_row["Bearish Cross"] and shares > 0:
            exit_price = float(current_row["Open"])

            cash = shares * exit_price

            trade_return = (
                (exit_price - entry_price)
                / entry_price
            ) * 100

            trades.append({
                "Entry Date": entry_date,
                "Entry Price": round(entry_price, 2),
                "Exit Date": current_date,
                "Exit Price": round(exit_price, 2),
                "Return (%)": round(trade_return, 2)
            })

            shares = 0.0
            entry_price = None
            entry_date = None

        portfolio_value = cash

        if shares > 0:
            portfolio_value += (
                shares * float(current_row["Close"])
            )

        equity_values.append({
            "Date": current_date,
            "Strategy": portfolio_value
        })

    # Close any remaining position at the final closing price
    if shares > 0:
        final_date = data.index[-1]
        final_price = float(data["Close"].iloc[-1])

        cash = shares * final_price

        trade_return = (
            (final_price - entry_price)
            / entry_price
        ) * 100

        trades.append({
            "Entry Date": entry_date,
            "Entry Price": round(entry_price, 2),
            "Exit Date": final_date,
            "Exit Price": round(final_price, 2),
            "Return (%)": round(trade_return, 2)
        })

        shares = 0.0

    ending_balance = cash

    total_return = (
        (ending_balance - starting_balance)
        / starting_balance
    ) * 100

    first_close = float(data["Close"].iloc[0])
    final_close = float(data["Close"].iloc[-1])

    buy_hold_return = (
        (final_close - first_close)
        / first_close
    ) * 100

    winning_trades = sum(
        trade["Return (%)"] > 0
        for trade in trades
    )

    win_rate = (
        winning_trades / len(trades) * 100
        if trades
        else 0.0
    )

    equity_curve = pd.DataFrame(equity_values)

    if not equity_curve.empty:
        equity_curve = equity_curve.set_index("Date")

        rolling_peak = equity_curve["Strategy"].cummax()

        drawdown = (
            equity_curve["Strategy"] - rolling_peak
        ) / rolling_peak

        maximum_drawdown = abs(drawdown.min()) * 100
    else:
        maximum_drawdown = 0.0

    trade_log = pd.DataFrame(trades)

    return {
        "Starting Balance": starting_balance,
        "Ending Balance": ending_balance,
        "Strategy Return (%)": total_return,
        "Buy and Hold Return (%)": buy_hold_return,
        "Outperformance (%)": total_return - buy_hold_return,
        "Number of Trades": len(trades),
        "Winning Trades": winning_trades,
        "Win Rate (%)": win_rate,
        "Maximum Drawdown (%)": maximum_drawdown,
        "Equity Curve": equity_curve,
        "Trade Log": trade_log
    }