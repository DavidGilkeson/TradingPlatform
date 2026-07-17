"""
analysis.py

Reusable stock-analysis UI components for Project Atlas.
"""

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def _safe_number(value, default=0.0):
    """
    Convert a value to float safely.
    """

    try:
        if pd.isna(value):
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _clamp(value, minimum=0.0, maximum=100.0):
    """
    Restrict a number to a defined range.
    """

    return max(minimum, min(maximum, value))


def _score_to_stars(score):
    """
    Convert a 0-100 score into a five-star rating.
    """

    score = _clamp(_safe_number(score))
    filled_stars = round(score / 20)

    return "★" * filled_stars + "☆" * (5 - filled_stars)


def _get_rating_label(score):
    """
    Return a readable rating label.
    """

    score = _safe_number(score)

    if score >= 90:
        return "Excellent"
    if score >= 80:
        return "Very Strong"
    if score >= 70:
        return "Strong"
    if score >= 60:
        return "Moderate"
    if score >= 50:
        return "Neutral"

    return "Weak"


def _calculate_health_scores(stock):
    """
    Build health scores from the available stock-analysis fields.
    """

    overall_score = _clamp(
        _safe_number(stock.get("Score", 0))
    )

    rsi = _safe_number(
        stock.get("RSI", 50),
        default=50,
    )

    volume_ratio = _safe_number(
        stock.get(
            "Volume Ratio",
            stock.get("Relative Volume", 1),
        ),
        default=1,
    )

    strength = _safe_number(
        stock.get(
            "Strength (%)",
            stock.get("Strength", 0),
        )
    )

    signal = str(
        stock.get("Signal", "HOLD")
    ).upper()

    trend_score = overall_score

    if signal == "BUY":
        trend_score = max(trend_score, 75)
    elif signal == "SELL":
        trend_score = min(trend_score, 35)

    momentum_score = _clamp(
        50 + strength
    )

    rsi_score = _clamp(
        100 - abs(rsi - 50) * 2
    )

    volume_score = _clamp(
        volume_ratio * 50
    )

    risk_score = _clamp(
        abs(rsi - 50) * 2
    )

    return {
        "Trend": round(trend_score, 1),
        "Momentum": round(momentum_score, 1),
        "Volume": round(volume_score, 1),
        "RSI": round(rsi_score, 1),
        "Risk": round(risk_score, 1),
    }


def display_stock_summary(stock):
    """
    Display the main stock heading and headline metrics.
    """

    ticker = str(
        stock.get("Ticker", "Unknown")
    )

    signal = str(
        stock.get("Signal", "HOLD")
    ).upper()

    score = _safe_number(
        stock.get("Score", 0)
    )

    confidence = stock.get(
        "Confidence",
        _get_rating_label(score),
    )

    st.subheader(f"📋 {ticker} Analysis Report")

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric(
        label="Ticker",
        value=ticker,
    )

    metric2.metric(
        label="Signal",
        value=signal,
    )

    metric3.metric(
        label="Atlas Score",
        value=f"{score:.0f}/100",
    )

    metric4.metric(
        label="Confidence",
        value=str(confidence),
    )

    st.markdown(
        f"### {_score_to_stars(score)} "
        f"{_get_rating_label(score)}"
    )


def display_price_statistics(stock):
    """
    Display price and indicator statistics when available.
    """

    metric_values = []

    possible_metrics = [
        ("Current Price", "Current Price", "${:,.2f}"),
        ("Close", "Current Price", "${:,.2f}"),
        ("RSI", "RSI", "{:.1f}"),
        ("MA Short", "Short MA", "${:,.2f}"),
        ("MA Long", "Long MA", "${:,.2f}"),
        ("Strength (%)", "Strength", "{:.2f}%"),
        ("Volume Ratio", "Volume Ratio", "{:.2f}x"),
    ]

    used_labels = set()

    for column_name, label, formatter in possible_metrics:
        if column_name not in stock.index:
            continue

        if label in used_labels:
            continue

        value = stock.get(column_name)

        if pd.isna(value):
            continue

        numeric_value = _safe_number(value)

        metric_values.append(
            (
                label,
                formatter.format(numeric_value),
            )
        )

        used_labels.add(label)

    if not metric_values:
        return

    st.markdown("#### Price and Indicator Statistics")

    columns = st.columns(
        min(len(metric_values), 4)
    )

    for index, (label, value) in enumerate(metric_values):
        columns[index % len(columns)].metric(
            label=label,
            value=value,
        )


def display_signal_strength(stock):
    """
    Display progress bars for major stock-health categories.
    """

    scores = _calculate_health_scores(stock)

    st.markdown("#### Stock Health")

    for name, value in scores.items():
        if name == "Risk":
            label = (
                f"{name}: {value:.0f}% "
                "(lower is better)"
            )
        else:
            label = f"{name}: {value:.0f}%"

        st.progress(
            value / 100,
            text=label,
        )


def create_stock_health_chart(stock):
    """
    Create a Plotly radar chart for stock health.
    """

    scores = _calculate_health_scores(stock)

    categories = list(scores.keys())
    values = list(scores.values())

    categories.append(categories[0])
    values.append(values[0])

    figure = go.Figure()

    figure.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            name="Stock Health",
        )
    )

    figure.update_layout(
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0, 100],
            }
        },
        showlegend=False,
        height=420,
        margin={
            "l": 40,
            "r": 40,
            "t": 40,
            "b": 40,
        },
    )

    return figure


def display_reason_list(stock):
    """
    Display the reasons behind the Atlas recommendation.
    """

    reasons = stock.get(
        "Reasons",
        "No detailed reasons are available.",
    )

    st.markdown("#### Why Atlas Chose This Rating")

    if isinstance(reasons, str):
        reason_items = [
            item.strip()
            for item in reasons.replace(
                ";",
                "\n",
            ).splitlines()
            if item.strip()
        ]

    elif isinstance(reasons, (list, tuple)):
        reason_items = [
            str(item).strip()
            for item in reasons
            if str(item).strip()
        ]

    else:
        reason_items = [str(reasons)]

    if not reason_items:
        st.info(
            "No detailed reasons are available."
        )
        return

    for reason in reason_items:
        st.write(f"✔ {reason}")


def display_recommendation(stock):
    """
    Display a simple recommendation summary.
    """

    signal = str(
        stock.get("Signal", "HOLD")
    ).upper()

    score = _safe_number(
        stock.get("Score", 0)
    )

    rsi = _safe_number(
        stock.get("RSI", 50),
        default=50,
    )

    if signal == "BUY":
        st.success(
            f"Suggested action: BUY — "
            f"Atlas score {score:.0f}/100."
        )

    elif signal == "SELL":
        st.error(
            f"Suggested action: SELL or AVOID — "
            f"Atlas score {score:.0f}/100."
        )

    else:
        st.info(
            f"Suggested action: HOLD or WATCH — "
            f"Atlas score {score:.0f}/100."
        )

    if rsi >= 70:
        st.warning(
            "RSI is in an overbought range. "
            "Momentum may be strong, but pullback risk is elevated."
        )

    elif rsi <= 30:
        st.warning(
            "RSI is in an oversold range. "
            "The stock may be weak or approaching a rebound area."
        )

    else:
        st.caption(
            "RSI is currently within a broadly neutral range."
        )


def display_stock_analysis(stock):
    """
    Display the complete Project Atlas stock-analysis report.
    """

    display_stock_summary(stock)

    display_price_statistics(stock)

    left_column, right_column = st.columns(
        [1, 1]
    )

    with left_column:
        display_signal_strength(stock)

    with right_column:
        st.markdown("#### Health Radar")

        figure = create_stock_health_chart(stock)

        st.plotly_chart(
            figure,
            width="stretch",
        )

    display_recommendation(stock)

    display_reason_list(stock)