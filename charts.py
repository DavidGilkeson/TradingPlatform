"""
charts.py

Builds interactive Plotly charts for Project Atlas.
"""

import plotly.graph_objects as go


def create_stock_chart(
    ticker,
    close,
    ma_short,
    ma_long
):
    """
    Create an interactive stock chart.

    Parameters:
        ticker: Stock ticker symbol.
        close: Historical closing-price Series.
        ma_short: Short moving-average Series.
        ma_long: Long moving-average Series.

    Returns:
        Plotly Figure.
    """

    figure = go.Figure()

    # Add the closing-price line
    figure.add_trace(
        go.Scatter(
            x=close.index,
            y=close,
            mode="lines",
            name="Closing Price"
        )
    )

    # Add the short moving average
    figure.add_trace(
        go.Scatter(
            x=ma_short.index,
            y=ma_short,
            mode="lines",
            name="20-Day Moving Average"
        )
    )

    # Add the long moving average
    figure.add_trace(
        go.Scatter(
            x=ma_long.index,
            y=ma_long,
            mode="lines",
            name="50-Day Moving Average"
        )
    )

    figure.update_layout(
        title=f"{ticker} Stock Analysis",
        xaxis_title="Date",
        yaxis_title="Price ($)",
        hovermode="x unified",
        height=600,
        template="plotly_dark",
        legend_title="Indicators"
    )

    figure.update_xaxes(
        rangeslider_visible=True
    )

    return figure