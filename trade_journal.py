"""
trade_journal.py

Persistent trade journal and performance analytics for Project Atlas.
"""

import json
from datetime import date
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st


JOURNAL_FILE = Path("trade_journal.json")


def load_trade_journal() -> list[dict]:
    """
    Load all saved trades from trade_journal.json.
    """

    if not JOURNAL_FILE.exists():
        return []

    try:
        with JOURNAL_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            trades = json.load(file)

        if not isinstance(trades, list):
            return []

        return trades

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return []


def save_trade_journal(
    trades: list[dict],
) -> bool:
    """
    Save all trade records to trade_journal.json.
    """

    try:
        with JOURNAL_FILE.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                trades,
                file,
                indent=4,
            )

        return True

    except OSError:
        return False


def calculate_trade_result(
    direction: str,
    entry_price: float,
    exit_price: float,
    quantity: float,
    fees: float = 0.0,
) -> tuple[float, float]:
    """
    Calculate realised profit/loss and percentage return.
    """

    direction = direction.upper()

    entry_value = entry_price * quantity

    if direction == "LONG":
        gross_result = (
            exit_price - entry_price
        ) * quantity

    elif direction == "SHORT":
        gross_result = (
            entry_price - exit_price
        ) * quantity

    else:
        gross_result = 0.0

    net_result = gross_result - fees

    return_percent = (
        net_result / entry_value * 100
        if entry_value > 0
        else 0.0
    )

    return net_result, return_percent


def add_trade(
    trades: list[dict],
    ticker: str,
    direction: str,
    entry_date: date,
    exit_date: date,
    entry_price: float,
    exit_price: float,
    quantity: float,
    fees: float,
    strategy: str,
    setup: str,
    notes: str,
) -> bool:
    """
    Add a completed trade to the journal.
    """

    ticker = ticker.strip().upper()

    if not ticker:
        return False

    if entry_price <= 0:
        return False

    if exit_price <= 0:
        return False

    if quantity <= 0:
        return False

    if exit_date < entry_date:
        return False

    profit_loss, return_percent = (
        calculate_trade_result(
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=quantity,
            fees=fees,
        )
    )

    trade = {
        "id": str(uuid4()),
        "ticker": ticker,
        "direction": direction.upper(),
        "entry_date": entry_date.isoformat(),
        "exit_date": exit_date.isoformat(),
        "entry_price": float(entry_price),
        "exit_price": float(exit_price),
        "quantity": float(quantity),
        "fees": float(fees),
        "profit_loss": round(
            profit_loss,
            2,
        ),
        "return_percent": round(
            return_percent,
            2,
        ),
        "strategy": strategy.strip(),
        "setup": setup.strip(),
        "notes": notes.strip(),
    }

    trades.append(trade)

    return save_trade_journal(trades)


def delete_trade(
    trades: list[dict],
    trade_id: str,
) -> bool:
    """
    Delete a trade using its unique ID.
    """

    updated_trades = [
        trade
        for trade in trades
        if trade.get("id") != trade_id
    ]

    trades.clear()
    trades.extend(updated_trades)

    return save_trade_journal(trades)


def trades_to_dataframe(
    trades: list[dict],
) -> pd.DataFrame:
    """
    Convert journal records into a display DataFrame.
    """

    if not trades:
        return pd.DataFrame()

    rows = []

    for trade in trades:
        profit_loss = float(
            trade.get(
                "profit_loss",
                0,
            )
        )

        rows.append(
            {
                "Trade ID": trade.get(
                    "id",
                    "",
                ),
                "Ticker": trade.get(
                    "ticker",
                    "",
                ),
                "Direction": trade.get(
                    "direction",
                    "",
                ),
                "Entry Date": trade.get(
                    "entry_date",
                    "",
                ),
                "Exit Date": trade.get(
                    "exit_date",
                    "",
                ),
                "Entry Price": trade.get(
                    "entry_price",
                    0,
                ),
                "Exit Price": trade.get(
                    "exit_price",
                    0,
                ),
                "Quantity": trade.get(
                    "quantity",
                    0,
                ),
                "Fees": trade.get(
                    "fees",
                    0,
                ),
                "Profit/Loss": profit_loss,
                "Return (%)": trade.get(
                    "return_percent",
                    0,
                ),
                "Result": (
                    "WIN"
                    if profit_loss > 0
                    else (
                        "LOSS"
                        if profit_loss < 0
                        else "BREAK EVEN"
                    )
                ),
                "Strategy": trade.get(
                    "strategy",
                    "",
                ),
                "Setup": trade.get(
                    "setup",
                    "",
                ),
                "Notes": trade.get(
                    "notes",
                    "",
                ),
            }
        )

    journal_df = pd.DataFrame(rows)

    journal_df["Entry Date"] = pd.to_datetime(
        journal_df["Entry Date"],
        errors="coerce",
    )

    journal_df["Exit Date"] = pd.to_datetime(
        journal_df["Exit Date"],
        errors="coerce",
    )

    journal_df = journal_df.sort_values(
        by="Exit Date",
        ascending=False,
    )

    return journal_df


def display_trade_form(
    trades: list[dict],
) -> None:
    """
    Display the completed-trade entry form.
    """

    st.subheader("➕ Record Completed Trade")

    with st.form(
        "trade_journal_form",
        clear_on_submit=True,
    ):
        ticker_column, direction_column = (
            st.columns(2)
        )

        ticker = ticker_column.text_input(
            label="Ticker",
            placeholder="AAPL",
        )

        direction = direction_column.selectbox(
            label="Direction",
            options=[
                "LONG",
                "SHORT",
            ],
        )

        entry_date_column, exit_date_column = (
            st.columns(2)
        )

        entry_date = entry_date_column.date_input(
            label="Entry date",
            value=date.today(),
        )

        exit_date = exit_date_column.date_input(
            label="Exit date",
            value=date.today(),
        )

        entry_column, exit_column, quantity_column = (
            st.columns(3)
        )

        entry_price = entry_column.number_input(
            label="Entry price",
            min_value=0.01,
            value=100.0,
            step=0.01,
        )

        exit_price = exit_column.number_input(
            label="Exit price",
            min_value=0.01,
            value=105.0,
            step=0.01,
        )

        quantity = quantity_column.number_input(
            label="Quantity",
            min_value=0.0001,
            value=1.0,
            step=1.0,
        )

        fees = st.number_input(
            label="Total fees",
            min_value=0.0,
            value=0.0,
            step=0.01,
        )

        strategy = st.selectbox(
            label="Strategy",
            options=[
                "Moving Average Crossover",
                "Breakout",
                "Pullback",
                "Momentum",
                "Mean Reversion",
                "Support and Resistance",
                "Manual Discretionary Trade",
                "Other",
            ],
        )

        setup = st.text_input(
            label="Trade setup",
            placeholder=(
                "Example: Price crossed above the "
                "50-day moving average"
            ),
        )

        notes = st.text_area(
            label="Trade notes",
            placeholder=(
                "Why did you enter? What went well? "
                "What would you change?"
            ),
            height=120,
        )

        submitted = st.form_submit_button(
            label="💾 Save Trade",
            type="primary",
            width="stretch",
        )

        if submitted:
            if exit_date < entry_date:
                st.error(
                    "Exit date cannot be before the entry date."
                )
                return

            saved = add_trade(
                trades=trades,
                ticker=ticker,
                direction=direction,
                entry_date=entry_date,
                exit_date=exit_date,
                entry_price=entry_price,
                exit_price=exit_price,
                quantity=quantity,
                fees=fees,
                strategy=strategy,
                setup=setup,
                notes=notes,
            )

            if saved:
                st.success(
                    f"{ticker.strip().upper()} trade saved."
                )
                st.rerun()

            else:
                st.error(
                    "The trade could not be saved. "
                    "Check the values and try again."
                )


def display_journal_metrics(
    journal_df: pd.DataFrame,
) -> None:
    """
    Display trade performance statistics.
    """

    if journal_df.empty:
        return

    total_trades = len(journal_df)

    winning_trades = journal_df.loc[
        journal_df["Profit/Loss"] > 0
    ]

    losing_trades = journal_df.loc[
        journal_df["Profit/Loss"] < 0
    ]

    win_rate = (
        len(winning_trades) / total_trades * 100
        if total_trades > 0
        else 0
    )

    net_profit = float(
        journal_df["Profit/Loss"].sum()
    )

    average_return = float(
        journal_df["Return (%)"].mean()
    )

    average_winner = (
        float(
            winning_trades[
                "Profit/Loss"
            ].mean()
        )
        if not winning_trades.empty
        else 0.0
    )

    average_loser = (
        float(
            losing_trades[
                "Profit/Loss"
            ].mean()
        )
        if not losing_trades.empty
        else 0.0
    )

    profit_factor = (
        winning_trades["Profit/Loss"].sum()
        / abs(
            losing_trades["Profit/Loss"].sum()
        )
        if not losing_trades.empty
        and losing_trades["Profit/Loss"].sum() != 0
        else 0.0
    )

    metric1, metric2, metric3 = st.columns(3)
    metric4, metric5, metric6 = st.columns(3)

    metric1.metric(
        label="Completed Trades",
        value=total_trades,
    )

    metric2.metric(
        label="Win Rate",
        value=f"{win_rate:.1f}%",
    )

    metric3.metric(
        label="Net Profit/Loss",
        value=f"${net_profit:,.2f}",
    )

    metric4.metric(
        label="Average Return",
        value=f"{average_return:.2f}%",
    )

    metric5.metric(
        label="Average Winner",
        value=f"${average_winner:,.2f}",
    )

    metric6.metric(
        label="Profit Factor",
        value=f"{profit_factor:.2f}",
        help=(
            "Gross winning profits divided by "
            "gross losing profits."
        ),
    )

    st.caption(
        f"Average losing trade: ${average_loser:,.2f}"
    )


def display_equity_curve(
    journal_df: pd.DataFrame,
) -> None:
    """
    Display cumulative realised profit/loss.
    """

    if journal_df.empty:
        return

    curve_df = journal_df.copy()

    curve_df = curve_df.sort_values(
        by="Exit Date",
        ascending=True,
    )

    curve_df["Cumulative Profit/Loss"] = (
        curve_df["Profit/Loss"].cumsum()
    )

    curve_df = curve_df.set_index(
        "Exit Date"
    )

    st.subheader("📈 Realised Profit/Loss Curve")

    st.line_chart(
        curve_df["Cumulative Profit/Loss"],
        width="stretch",
    )


def display_trade_history(
    trades: list[dict],
    journal_df: pd.DataFrame,
) -> None:
    """
    Display, filter and manage journal history.
    """

    if journal_df.empty:
        return

    st.subheader("📓 Trade History")

    filter_column1, filter_column2 = st.columns(2)

    result_filter = filter_column1.selectbox(
        label="Result filter",
        options=[
            "All",
            "WIN",
            "LOSS",
            "BREAK EVEN",
        ],
        key="journal_result_filter",
    )

    ticker_filter = filter_column2.text_input(
        label="Ticker filter",
        placeholder="Example: NVDA",
        key="journal_ticker_filter",
    )

    filtered_df = journal_df.copy()

    if result_filter != "All":
        filtered_df = filtered_df.loc[
            filtered_df["Result"]
            == result_filter
        ]

    if ticker_filter.strip():
        filtered_df = filtered_df.loc[
            filtered_df["Ticker"]
            .astype(str)
            .str.contains(
                ticker_filter.strip().upper(),
                case=False,
                na=False,
            )
        ]

    display_columns = [
        "Ticker",
        "Direction",
        "Entry Date",
        "Exit Date",
        "Entry Price",
        "Exit Price",
        "Quantity",
        "Fees",
        "Profit/Loss",
        "Return (%)",
        "Result",
        "Strategy",
        "Setup",
        "Notes",
    ]

    st.dataframe(
        filtered_df[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "Entry Date": st.column_config.DateColumn(
                format="DD MMM YYYY",
            ),
            "Exit Date": st.column_config.DateColumn(
                format="DD MMM YYYY",
            ),
            "Entry Price": st.column_config.NumberColumn(
                format="$%.2f",
            ),
            "Exit Price": st.column_config.NumberColumn(
                format="$%.2f",
            ),
            "Quantity": st.column_config.NumberColumn(
                format="%.4f",
            ),
            "Fees": st.column_config.NumberColumn(
                format="$%.2f",
            ),
            "Profit/Loss": st.column_config.NumberColumn(
                format="$%.2f",
            ),
            "Return (%)": st.column_config.NumberColumn(
                format="%.2f%%",
            ),
        },
    )

    csv_data = filtered_df[
        display_columns
    ].to_csv(
        index=False
    )

    st.download_button(
        label="📥 Download Trade Journal",
        data=csv_data,
        file_name="project_atlas_trade_journal.csv",
        mime="text/csv",
        width="stretch",
    )

    st.subheader("Delete Trade")

    trade_options = {
        (
            f'{trade.get("ticker", "Unknown")} | '
            f'{trade.get("exit_date", "")} | '
            f'${float(trade.get("profit_loss", 0)):,.2f}'
        ): trade.get("id")
        for trade in trades
    }

    selected_trade_label = st.selectbox(
        label="Select a trade to delete",
        options=list(trade_options.keys()),
        key="delete_trade_selection",
    )

    if st.button(
        label="🗑 Delete Selected Trade",
        width="stretch",
    ):
        trade_id = trade_options[
            selected_trade_label
        ]

        deleted = delete_trade(
            trades,
            trade_id,
        )

        if deleted:
            st.success("Trade deleted.")
            st.rerun()

        else:
            st.error(
                "The trade could not be deleted."
            )


def display_trade_journal(
    trades: list[dict],
) -> None:
    """
    Display the complete Project Atlas trade journal.
    """

    st.header("📓 Trade Journal")

    st.caption(
        "Record completed trades, review performance "
        "and identify patterns in your decision-making."
    )

    display_trade_form(trades)

    st.divider()

    if not trades:
        st.info(
            "No completed trades have been recorded yet."
        )
        return

    journal_df = trades_to_dataframe(
        trades
    )

    display_journal_metrics(
        journal_df
    )

    st.divider()

    display_equity_curve(
        journal_df
    )

    st.divider()

    display_trade_history(
        trades,
        journal_df,
    )