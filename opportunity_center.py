"""
opportunity_center.py

Project Atlas Opportunity Centre.

Displays the highest-ranked opportunities, stocks approaching buy territory,
risk alerts, market health, and the top-ranked stocks from the latest scan.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


def _safe_number(value: Any, default: float = 0.0) -> float:
    """Convert a value to float safely."""

    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _get_score_column(df: pd.DataFrame) -> str | None:
    """Return the best available score column."""

    for column in ("Atlas Score", "Score"):
        if column in df.columns:
            return column

    return None


def _get_grade(row: pd.Series) -> str:
    """Return the best available grade label."""

    grade = row.get("Atlas Grade", "")
    return str(grade) if pd.notna(grade) else ""


def _get_verdict(row: pd.Series) -> str:
    """Return the best available verdict."""

    verdict = row.get("Atlas Verdict", row.get("Signal", "Unknown"))
    return str(verdict) if pd.notna(verdict) else "Unknown"


def _get_stars(row: pd.Series) -> str:
    """Return the Atlas star display when available."""

    stars = row.get("Atlas Stars", "")
    return str(stars) if pd.notna(stars) else ""


def _split_explanations(value: Any) -> list[str]:
    """Convert stored explanation data into a clean list of strings."""

    if value is None:
        return []

    if isinstance(value, (list, tuple, set)):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return []

    # Scanner rows store explanations with pipes. This also supports
    # semicolons and line breaks without ever passing an empty separator
    # to str.split().
    normalised_text = (
        text.replace("\r\n", "|")
        .replace("\r", "|")
        .replace("\n", "|")
        .replace(";", "|")
    )

    return [
        item.strip()
        for item in normalised_text.split("|")
        if item.strip()
    ]


def _prepare_ranked_data(df: pd.DataFrame) -> tuple[pd.DataFrame, str | None]:
    """Return a cleaned and ranked copy of the scan results."""

    if df is None or df.empty:
        return pd.DataFrame(), None

    score_column = _get_score_column(df)

    if score_column is None:
        return df.copy(), None

    ranked = df.copy()
    ranked[score_column] = pd.to_numeric(
        ranked[score_column],
        errors="coerce",
    )

    ranked = ranked.dropna(subset=[score_column])

    sort_columns = [score_column]

    if "Strength (%)" in ranked.columns:
        ranked["Strength (%)"] = pd.to_numeric(
            ranked["Strength (%)"],
            errors="coerce",
        )
        sort_columns.append("Strength (%)")

    ranked = ranked.sort_values(
        by=sort_columns,
        ascending=[False] * len(sort_columns),
    ).reset_index(drop=True)

    return ranked, score_column


def display_market_health(
    df: pd.DataFrame,
    score_column: str,
) -> None:
    """Display headline market statistics."""

    st.subheader("📊 Market Health")

    total_stocks = len(df)
    average_score = _safe_number(df[score_column].mean())

    verdict_series = (
        df["Atlas Verdict"].astype(str).str.upper()
        if "Atlas Verdict" in df.columns
        else df.get("Signal", pd.Series(dtype=str)).astype(str).str.upper()
    )

    buy_count = int(
        verdict_series.isin(["STRONG BUY", "BUY"]).sum()
    )
    hold_count = int(
        verdict_series.isin(["HOLD", "WATCH", "WEAK"]).sum()
    )
    avoid_count = int(
        verdict_series.isin(["SELL", "AVOID"]).sum()
    )

    metric1, metric2, metric3, metric4, metric5 = st.columns(5)

    metric1.metric("Stocks Scanned", total_stocks)
    metric2.metric("Buy Opportunities", buy_count)
    metric3.metric("Hold / Watch", hold_count)
    metric4.metric("Avoid / Sell", avoid_count)
    metric5.metric("Average Atlas Score", f"{average_score:.1f}")

    st.progress(
        int(max(0, min(average_score, 100))),
        text=f"Average market opportunity: {average_score:.1f}%",
    )

    if average_score >= 80:
        st.success("Excellent buying environment based on the current scan.")
    elif average_score >= 65:
        st.info("Constructive market with selective opportunities available.")
    elif average_score >= 50:
        st.warning("Mixed market conditions. Prioritise stronger setups.")
    else:
        st.error("Weak market conditions. Capital preservation may be appropriate.")


def display_best_opportunity(
    df: pd.DataFrame,
    score_column: str,
) -> None:
    """Display the highest-ranked stock from the scan."""

    if df.empty:
        return

    best = df.iloc[0]

    ticker = str(best.get("Ticker", "Unknown"))
    score = _safe_number(best.get(score_column))
    grade = _get_grade(best)
    verdict = _get_verdict(best)
    stars = _get_stars(best)

    st.subheader("🔥 Best Opportunity")

    st.markdown(f"## {ticker}")

    metric1, metric2, metric3, metric4 = st.columns(4)

    metric1.metric("Atlas Score", f"{score:.1f}/100")
    metric2.metric("Grade", grade or "—")
    metric3.metric("Verdict", verdict)
    metric4.metric("Confidence", stars or str(best.get("Atlas Confidence", "—")))

    strengths = _split_explanations(
        best.get("Atlas Strengths", best.get("Reasons"))
    )

    weaknesses = _split_explanations(
        best.get("Atlas Weaknesses")
    )

    left_column, right_column = st.columns(2)

    with left_column:
        st.markdown("#### ✅ Why It Ranks First")

        if strengths:
            for strength in strengths[:5]:
                st.write(f"• {strength}")
        else:
            st.info("No detailed strengths are available.")

    with right_column:
        st.markdown("#### ⚠️ What to Watch")

        if weaknesses:
            for weakness in weaknesses[:5]:
                st.write(f"• {weakness}")
        else:
            st.info("No major weaknesses were detected.")


def display_watch_candidates(
    df: pd.DataFrame,
    score_column: str,
    minimum_score: float = 70.0,
    maximum_score: float = 89.99,
    limit: int = 5,
) -> None:
    """Display stocks approaching the strongest opportunity range."""

    watch_df = df[
        (df[score_column] >= minimum_score)
        & (df[score_column] <= maximum_score)
    ].head(limit)

    st.subheader("👀 Stocks to Watch")

    if watch_df.empty:
        st.info("No watch candidates matched the current score range.")
        return

    for _, row in watch_df.iterrows():
        ticker = str(row.get("Ticker", "Unknown"))
        score = _safe_number(row.get(score_column))
        grade = _get_grade(row)
        verdict = _get_verdict(row)
        points_needed = max(0.0, 90.0 - score)

        with st.container(border=True):
            metric1, metric2, metric3, metric4 = st.columns(4)

            metric1.metric("Ticker", ticker)
            metric2.metric("Atlas Score", f"{score:.1f}")
            metric3.metric("Grade", grade or "—")
            metric4.metric("Points to Strong Buy", f"{points_needed:.1f}")

            st.caption(f"Current verdict: {verdict}")

            weaknesses = _split_explanations(
                row.get("Atlas Weaknesses")
            )

            if weaknesses:
                st.write(f"Main watch item: {weaknesses[0]}")


def display_risk_alerts(
    df: pd.DataFrame,
    limit: int = 6,
) -> None:
    """Display stocks with notable technical risk flags."""

    alerts: list[dict[str, Any]] = []

    for _, row in df.iterrows():
        ticker = str(row.get("Ticker", "Unknown"))
        rsi = _safe_number(row.get("RSI"), default=50.0)
        relative_volume = _safe_number(
            row.get("Relative Volume"),
            default=1.0,
        )
        verdict = _get_verdict(row).upper()

        weaknesses = _split_explanations(
            row.get("Atlas Weaknesses")
        )

        if rsi >= 75:
            alerts.append(
                {
                    "ticker": ticker,
                    "alert": f"RSI is elevated at {rsi:.1f}.",
                }
            )
        elif rsi <= 30:
            alerts.append(
                {
                    "ticker": ticker,
                    "alert": f"RSI is oversold at {rsi:.1f}.",
                }
            )
        elif relative_volume < 0.75:
            alerts.append(
                {
                    "ticker": ticker,
                    "alert": (
                        f"Relative volume is weak at "
                        f"{relative_volume:.2f}x."
                    ),
                }
            )
        elif verdict in {"AVOID", "SELL"}:
            alerts.append(
                {
                    "ticker": ticker,
                    "alert": f"Atlas verdict is {verdict.title()}.",
                }
            )
        elif weaknesses and "No major" not in weaknesses[0]:
            alerts.append(
                {
                    "ticker": ticker,
                    "alert": weaknesses[0],
                }
            )

        if len(alerts) >= limit:
            break

    st.subheader("🚨 Risk Alerts")

    if not alerts:
        st.success("No major risk alerts were detected in the leading results.")
        return

    for alert in alerts:
        st.warning(
            f"**{alert['ticker']}** — {alert['alert']}"
        )


def display_top_rankings(
    df: pd.DataFrame,
    score_column: str,
    limit: int = 10,
) -> None:
    """Display a compact table of the highest-ranked stocks."""

    st.subheader(f"⭐ Top {min(limit, len(df))} Opportunities")

    display_columns = [
        column
        for column in [
            "Ticker",
            score_column,
            "Atlas Grade",
            "Atlas Verdict",
            "Atlas Confidence",
            "Atlas Stars",
            "Signal",
            "Strength (%)",
            "RSI",
            "Relative Volume",
        ]
        if column in df.columns
    ]

    top_df = df.head(limit)[display_columns].copy()

    st.dataframe(
        top_df,
        width="stretch",
        hide_index=True,
    )


def display_opportunity_center(
    df: pd.DataFrame,
) -> None:
    """
    Display the complete Project Atlas Opportunity Centre.

    Parameters
    ----------
    df:
        Market scan results containing Atlas Decision Engine columns.
    """

    st.header("🎯 Atlas Opportunity Centre")
    st.caption(
        "A ranked overview of the strongest opportunities, "
        "watch candidates, and current technical risks."
    )

    ranked_df, score_column = _prepare_ranked_data(df)

    if ranked_df.empty:
        st.info(
            "Run a market scan to populate the Opportunity Centre."
        )
        return

    if score_column is None:
        st.error(
            "The scan results do not contain an Atlas Score or Score column."
        )
        return

    display_market_health(ranked_df, score_column)

    st.divider()

    display_best_opportunity(ranked_df, score_column)

    st.divider()

    left_column, right_column = st.columns([1.1, 0.9])

    with left_column:
        display_watch_candidates(
            ranked_df,
            score_column,
        )

    with right_column:
        display_risk_alerts(ranked_df)

    st.divider()

    display_top_rankings(
        ranked_df,
        score_column,
    )
