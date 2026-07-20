"""
portfolio.py

Persistent portfolio tracking for Project Atlas.
"""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

PORTFOLIO_FILE = Path("portfolio.json")


def load_portfolio() -> list[dict]:
    """
    Load portfolio positions from portfolio.json.
    """

    if not PORTFOLIO_FILE.exists():
        return []

    try:
        with PORTFOLIO_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, list):
            return []

        return data

    except (
        OSError,
        json.JSONDecodeError,
    ):
        return []


def save_portfolio(
    portfolio: list[dict],
) -> bool:
    """
    Save portfolio positions to portfolio.json.
    """

    try:
        with PORTFOLIO_FILE.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                portfolio,
                file,
                indent=4,
            )

        return True

    except OSError:
        return False


def add_position(
    portfolio: list[dict],
    ticker: str,
    quantity: float,
    average_price: float,
) -> bool:
    """
    Add a new position or combine it with an existing one.
    """

    ticker = ticker.strip().upper()

    if not ticker:
        return False

    if quantity <= 0 or average_price <= 0:
        return False

    for position in portfolio:
        if position["ticker"] == ticker:
            existing_quantity = float(position["quantity"])

            existing_price = float(position["average_price"])

            total_quantity = existing_quantity + quantity

            total_cost = existing_quantity * existing_price + quantity * average_price

            position["quantity"] = total_quantity
            position["average_price"] = total_cost / total_quantity

            return save_portfolio(portfolio)

    portfolio.append(
        {
            "ticker": ticker,
            "quantity": quantity,
            "average_price": average_price,
        }
    )

    return save_portfolio(portfolio)


def remove_position(
    portfolio: list[dict],
    ticker: str,
) -> bool:
    """
    Remove a portfolio position.
    """

    updated_portfolio = [
        position for position in portfolio if position["ticker"] != ticker
    ]

    portfolio.clear()
    portfolio.extend(updated_portfolio)

    return save_portfolio(portfolio)


def _get_current_price(
    ticker: str,
    df: pd.DataFrame,
) -> float | None:
    """
    Get the latest price from the scanner results.
    """

    ticker_rows = df.loc[df["Ticker"] == ticker]

    if ticker_rows.empty:
        return None

    stock = ticker_rows.iloc[0]

    possible_price_columns = [
        "Current Price",
        "Close",
        "Price",
        "Latest Price",
    ]

    for column in possible_price_columns:
        if column not in stock.index:
            continue

        try:
            price = float(stock[column])

            if pd.notna(price):
                return price

        except (TypeError, ValueError):
            continue

    return None


def calculate_portfolio(
    portfolio: list[dict],
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Calculate value and profit/loss for each position.
    """

    rows = []

    for position in portfolio:
        ticker = position["ticker"]
        quantity = float(position["quantity"])
        average_price = float(position["average_price"])

        current_price = _get_current_price(
            ticker,
            df,
        )

        cost_basis = quantity * average_price

        if current_price is None:
            market_value = None
            profit_loss = None
            profit_loss_percent = None
        else:
            market_value = quantity * current_price

            profit_loss = market_value - cost_basis

            profit_loss_percent = (
                profit_loss / cost_basis * 100 if cost_basis > 0 else 0
            )

        rows.append(
            {
                "Ticker": ticker,
                "Quantity": quantity,
                "Average Price": average_price,
                "Current Price": current_price,
                "Cost Basis": cost_basis,
                "Market Value": market_value,
                "Profit/Loss": profit_loss,
                "Return (%)": profit_loss_percent,
            }
        )

    return pd.DataFrame(rows)


def display_add_position_form(
    portfolio: list[dict],
) -> None:
    """
    Display the add-position form.
    """

    with st.form(
        "add_portfolio_position",
        clear_on_submit=True,
    ):
        st.markdown("#### Add Position")

        ticker_column, quantity_column, price_column = st.columns(3)

        ticker = ticker_column.text_input(
            "Ticker",
            placeholder="AAPL",
        )

        quantity = quantity_column.number_input(
            "Quantity",
            min_value=0.0001,
            value=1.0,
            step=1.0,
        )

        average_price = price_column.number_input(
            "Average purchase price",
            min_value=0.01,
            value=100.0,
            step=1.0,
        )

        submitted = st.form_submit_button(
            "➕ Add Position",
            type="primary",
            width="stretch",
        )

        if submitted:
            saved = add_position(
                portfolio=portfolio,
                ticker=ticker,
                quantity=quantity,
                average_price=average_price,
            )

            if saved:
                st.success(f"{ticker.strip().upper()} added to your portfolio.")
                st.rerun()
            else:
                st.error("The position could not be saved.")


def display_portfolio(
    portfolio: list[dict],
    df: pd.DataFrame,
) -> None:
    """
    Display the complete portfolio dashboard.
    """

    st.header("💼 Portfolio Tracker")

    display_add_position_form(portfolio)

    if not portfolio:
        st.info("Your portfolio is empty. Add your first position above.")
        return

    portfolio_df = calculate_portfolio(
        portfolio,
        df,
    )

    valid_values = portfolio_df.dropna(subset=["Market Value"])

    total_cost = float(portfolio_df["Cost Basis"].sum())

    total_value = float(valid_values["Market Value"].sum())

    total_profit_loss = total_value - total_cost

    total_return = total_profit_loss / total_cost * 100 if total_cost > 0 else 0

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        "Total Cost",
        f"${total_cost:,.2f}",
    )

    metric2.metric(
        "Market Value",
        f"${total_value:,.2f}",
    )

    metric3.metric(
        "Profit/Loss",
        f"${total_profit_loss:,.2f}",
        delta=f"{total_return:.2f}%",
    )

    metric4.metric(
        "Positions",
        len(portfolio_df),
    )

    st.divider()

    st.subheader("Portfolio Positions")

    st.dataframe(
        portfolio_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Quantity": st.column_config.NumberColumn(
                format="%.4f",
            ),
            "Average Price": (
                st.column_config.NumberColumn(
                    format="$%.2f",
                )
            ),
            "Current Price": (
                st.column_config.NumberColumn(
                    format="$%.2f",
                )
            ),
            "Cost Basis": (
                st.column_config.NumberColumn(
                    format="$%.2f",
                )
            ),
            "Market Value": (
                st.column_config.NumberColumn(
                    format="$%.2f",
                )
            ),
            "Profit/Loss": (
                st.column_config.NumberColumn(
                    format="$%.2f",
                )
            ),
            "Return (%)": (
                st.column_config.NumberColumn(
                    format="%.2f%%",
                )
            ),
        },
    )

    if not valid_values.empty:
        st.subheader("Portfolio Allocation")

        allocation_chart = px.pie(
            valid_values,
            names="Ticker",
            values="Market Value",
            hole=0.45,
        )

        allocation_chart.update_traces(
            textposition="inside",
            textinfo="label+percent",
        )

        allocation_chart.update_layout(
            height=450,
            margin={
                "l": 20,
                "r": 20,
                "t": 20,
                "b": 20,
            },
        )

        st.plotly_chart(
            allocation_chart,
            width="stretch",
        )

    st.subheader("Manage Positions")

    for position in portfolio:
        ticker = position["ticker"]

        position_column, remove_column = st.columns([4, 1])

        position_column.write(f"**{ticker}** — {position['quantity']:.4f} shares")

        if remove_column.button(
            "Remove",
            key=f"remove_position_{ticker}",
            width="stretch",
        ):
            removed = remove_position(
                portfolio,
                ticker,
            )

            if removed:
                st.success(f"{ticker} removed.")
                st.rerun()
            else:
                st.error(f"{ticker} could not be removed.")
