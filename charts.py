"""
charts.py

Creates interactive Plotly charts for Project Atlas.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config import SHORT_MA, LONG_MA


def create_stock_chart(
    ticker,
    open_prices,
    high_prices,
    low_prices,
    close_prices,
    volume,
    ma_short,
    ma_long,
    rsi
):
    """
    Create an interactive candlestick chart with moving averages,
    volume and RSI.
    """

    figure = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        row_heights=[0.60, 0.20, 0.20],
        subplot_titles=(
            f"{ticker} Price",
            "Volume",
            "RSI"
        )
    )

    # Candlestick price chart
    figure.add_trace(
        go.Candlestick(
            x=close_prices.index,
            open=open_prices,
            high=high_prices,
            low=low_prices,
            close=close_prices,
            name="Price"
        ),
        row=1,
        col=1
    )

    # Short moving average
    figure.add_trace(
        go.Scatter(
            x=ma_short.index,
            y=ma_short,
            mode="lines",
            name=f"{SHORT_MA}-Day MA"
        ),
        row=1,
        col=1
    )

    # Long moving average
    figure.add_trace(
        go.Scatter(
            x=ma_long.index,
            y=ma_long,
            mode="lines",
            name=f"{LONG_MA}-Day MA"
        ),
        row=1,
        col=1
    )

    # Trading volume
    figure.add_trace(
        go.Bar(
            x=volume.index,
            y=volume,
            name="Volume"
        ),
        row=2,
        col=1
    )

    # RSI line
    figure.add_trace(
        go.Scatter(
            x=rsi.index,
            y=rsi,
            mode="lines",
            name="RSI"
        ),
        row=3,
        col=1
    )

    # RSI overbought line
    figure.add_hline(
        y=70,
        line_dash="dash",
        annotation_text="Overbought",
        row=3,
        col=1
    )

    # RSI oversold line
    figure.add_hline(
        y=30,
        line_dash="dash",
        annotation_text="Oversold",
        row=3,
        col=1
    )

    figure.update_layout(
        title=f"{ticker} Technical Analysis",
        height=900,
        template="plotly_dark",
        hovermode="x unified",
        xaxis_rangeslider_visible=False,
        legend_title="Indicators"
    )

    figure.update_yaxes(
        title_text="Price ($)",
        row=1,
        col=1
    )

    figure.update_yaxes(
        title_text="Volume",
        row=2,
        col=1
    )

    figure.update_yaxes(
        title_text="RSI",
        range=[0, 100],
        row=3,
        col=1
    )

    return figure