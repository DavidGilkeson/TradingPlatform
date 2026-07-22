"""
atlas_intelligence.py

Deterministic explanation and coaching layer for Project Atlas.

This module does not predict prices or call an external AI service. It turns
the scanner and Decision Engine outputs into readable summaries, checklists,
confidence breakdowns, and practical watch items.
"""

from __future__ import annotations

from typing import Any, Mapping

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


def _safe_text(value: Any, default: str = "") -> str:
    """Convert a value to clean text safely."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()
    return text or default


def _split_items(value: Any) -> list[str]:
    """Convert list-like or delimited explanation data into clean strings."""

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

    normalised = (
        text.replace("\r\n", "|")
        .replace("\r", "|")
        .replace("\n", "|")
        .replace(";", "|")
    )

    return [
        item.strip()
        for item in normalised.split("|")
        if item.strip()
    ]


def _metric(stock: Mapping[str, Any], *names: str, default: float = 0.0) -> float:
    """Return the first available numeric metric from a set of aliases."""

    for name in names:
        if name in stock:
            value = _safe_number(stock.get(name), default)
            return value

    return default


def _score(stock: Mapping[str, Any]) -> float:
    """Return the best available Atlas score."""

    return _metric(stock, "Atlas Score", "Score", default=0.0)


def _verdict(stock: Mapping[str, Any]) -> str:
    """Return the best available recommendation label."""

    return _safe_text(
        stock.get(
            "Atlas Verdict",
            stock.get("Signal", "Watch"),
        ),
        "Watch",
    )


def _stars(score: float) -> str:
    """Return a five-star score display."""

    filled = max(0, min(5, round(score / 20)))
    return "★" * filled + "☆" * (5 - filled)


def build_intelligence_summary(stock: Mapping[str, Any]) -> str:
    """Create a readable summary from the available technical metrics."""

    ticker = _safe_text(stock.get("Ticker"), "This stock")
    score = _score(stock)
    verdict = _verdict(stock)

    price = _metric(stock, "Close", "Current Price", "price")
    ma_short = _metric(stock, "20-Day MA", "MA Short", "ma20")
    ma_long = _metric(stock, "50-Day MA", "MA Long", "ma50")
    rsi = _metric(stock, "RSI", "rsi", default=50.0)
    strength = _metric(stock, "Strength (%)", "Strength", "strength")
    relative_volume = _metric(
        stock,
        "Relative Volume",
        "Volume Ratio",
        "relative_volume",
        default=1.0,
    )

    observations: list[str] = []

    if price and ma_short and ma_long:
        if price > ma_short > ma_long:
            observations.append(
                "price is above both moving averages and the shorter average "
                "is leading the longer average, supporting a bullish trend"
            )
        elif price < ma_short < ma_long:
            observations.append(
                "price is below both moving averages, showing that the broader "
                "trend remains weak"
            )
        elif price > ma_long:
            observations.append(
                "price remains above the longer moving average, although the "
                "short-term trend is mixed"
            )
        else:
            observations.append(
                "price remains below the longer moving average, so trend "
                "confirmation is limited"
            )

    if 45 <= rsi <= 65:
        observations.append(
            f"RSI is healthy at {rsi:.1f}, leaving room for momentum without "
            "being heavily overbought"
        )
    elif rsi > 70:
        observations.append(
            f"RSI is elevated at {rsi:.1f}, showing strong momentum but also "
            "greater pullback risk"
        )
    elif rsi < 30:
        observations.append(
            f"RSI is oversold at {rsi:.1f}, which may signal weakness or an "
            "early rebound area"
        )
    else:
        observations.append(
            f"RSI is neutral at {rsi:.1f}"
        )

    if relative_volume >= 1.3:
        observations.append(
            f"relative volume is strong at {relative_volume:.2f}x average, "
            "indicating above-normal participation"
        )
    elif relative_volume < 0.8:
        observations.append(
            f"relative volume is light at {relative_volume:.2f}x average, so "
            "the move has limited participation"
        )
    else:
        observations.append(
            f"volume participation is close to normal at "
            f"{relative_volume:.2f}x average"
        )

    if strength >= 5:
        observations.append(
            f"price strength is positive at {strength:.1f}%"
        )
    elif strength <= -5:
        observations.append(
            f"price strength is weak at {strength:.1f}%"
        )

    if not observations:
        observations.append(
            "the available scanner metrics provide limited technical detail"
        )

    detail = "; ".join(observations[:4])

    return (
        f"{ticker} currently carries an Atlas score of {score:.1f}/100 and a "
        f"{verdict} verdict. The current reading shows that {detail}. Atlas "
        "uses these conditions as decision support rather than a guarantee of "
        "future performance."
    )


def build_trade_checklist(stock: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build a deterministic pass, warning, or fail checklist."""

    price = _metric(stock, "Close", "Current Price", "price")
    ma_short = _metric(stock, "20-Day MA", "MA Short", "ma20")
    ma_long = _metric(stock, "50-Day MA", "MA Long", "ma50")
    rsi = _metric(stock, "RSI", "rsi", default=50.0)
    strength = _metric(stock, "Strength (%)", "Strength", "strength")
    relative_volume = _metric(
        stock,
        "Relative Volume",
        "Volume Ratio",
        "relative_volume",
        default=1.0,
    )

    checklist: list[dict[str, Any]] = []

    def add(label: str, status: str, detail: str) -> None:
        checklist.append(
            {
                "label": label,
                "status": status,
                "detail": detail,
            }
        )

    if price and ma_short:
        add(
            "Price above short moving average",
            "pass" if price > ma_short else "fail",
            f"Price {price:.2f} vs short MA {ma_short:.2f}",
        )

    if price and ma_long:
        add(
            "Price above long moving average",
            "pass" if price > ma_long else "fail",
            f"Price {price:.2f} vs long MA {ma_long:.2f}",
        )

    if ma_short and ma_long:
        add(
            "Bullish moving-average structure",
            "pass" if ma_short > ma_long else "fail",
            f"Short MA {ma_short:.2f} vs long MA {ma_long:.2f}",
        )

    if 40 <= rsi <= 68:
        rsi_status = "pass"
    elif 30 <= rsi < 40 or 68 < rsi <= 75:
        rsi_status = "warning"
    else:
        rsi_status = "fail"

    add(
        "RSI in a controlled range",
        rsi_status,
        f"RSI {rsi:.1f}",
    )

    if relative_volume >= 1.1:
        volume_status = "pass"
    elif relative_volume >= 0.8:
        volume_status = "warning"
    else:
        volume_status = "fail"

    add(
        "Volume confirmation",
        volume_status,
        f"Relative volume {relative_volume:.2f}x",
    )

    if strength >= 3:
        strength_status = "pass"
    elif strength >= 0:
        strength_status = "warning"
    else:
        strength_status = "fail"

    add(
        "Positive price strength",
        strength_status,
        f"Strength {strength:.1f}%",
    )

    return checklist


def build_confidence_breakdown(stock: Mapping[str, Any]) -> dict[str, float]:
    """Create simple 0-100 confidence categories from scanner metrics."""

    score = _score(stock)
    price = _metric(stock, "Close", "Current Price", "price")
    ma_short = _metric(stock, "20-Day MA", "MA Short", "ma20")
    ma_long = _metric(stock, "50-Day MA", "MA Long", "ma50")
    rsi = _metric(stock, "RSI", "rsi", default=50.0)
    strength = _metric(stock, "Strength (%)", "Strength", "strength")
    relative_volume = _metric(
        stock,
        "Relative Volume",
        "Volume Ratio",
        "relative_volume",
        default=1.0,
    )

    trend = 50.0

    if price and ma_short:
        trend += 20 if price > ma_short else -20
    if price and ma_long:
        trend += 20 if price > ma_long else -20
    if ma_short and ma_long:
        trend += 10 if ma_short > ma_long else -10

    momentum = max(0.0, min(100.0, 50.0 + strength * 4.0))
    volume = max(0.0, min(100.0, relative_volume * 55.0))
    rsi_quality = max(0.0, min(100.0, 100.0 - abs(rsi - 55.0) * 2.4))

    risk = 80.0

    if rsi > 75 or rsi < 25:
        risk -= 35
    elif rsi > 68 or rsi < 35:
        risk -= 15

    if relative_volume < 0.75:
        risk -= 15

    if price and ma_long and price < ma_long:
        risk -= 20

    return {
        "Overall": round(max(0.0, min(100.0, score)), 1),
        "Trend": round(max(0.0, min(100.0, trend)), 1),
        "Momentum": round(momentum, 1),
        "Volume": round(volume, 1),
        "RSI Quality": round(rsi_quality, 1),
        "Risk Control": round(max(0.0, min(100.0, risk)), 1),
    }


def build_coach_message(stock: Mapping[str, Any]) -> tuple[str, str]:
    """Return an actionable but non-predictive coaching message."""

    score = _score(stock)
    verdict = _verdict(stock).upper()
    rsi = _metric(stock, "RSI", "rsi", default=50.0)
    relative_volume = _metric(
        stock,
        "Relative Volume",
        "Volume Ratio",
        "relative_volume",
        default=1.0,
    )
    price = _metric(stock, "Close", "Current Price", "price")
    ma_short = _metric(stock, "20-Day MA", "MA Short", "ma20")
    ma_long = _metric(stock, "50-Day MA", "MA Long", "ma50")

    if rsi >= 75:
        return (
            "Momentum is stretched",
            "Avoid chasing the move. Watch for RSI to cool or for price to "
            "stabilise closer to the short moving average.",
        )

    if relative_volume < 0.8:
        return (
            "Volume confirmation is weak",
            "Keep the stock on the watchlist and wait for participation to "
            "improve before treating the signal as high confidence.",
        )

    if price and ma_short and price < ma_short:
        return (
            "Short-term trend needs confirmation",
            "Wait for price to reclaim the short moving average before "
            "considering the setup technically confirmed.",
        )

    if price and ma_long and price < ma_long:
        return (
            "Long-term trend remains weak",
            "Treat rallies cautiously until price establishes itself above "
            "the longer moving average.",
        )

    if score >= 85 and verdict in {"BUY", "STRONG BUY"}:
        return (
            "Conditions are broadly constructive",
            "Review position size, define an invalidation level, and avoid "
            "entering without a clear risk plan.",
        )

    if score >= 70:
        return (
            "The setup is developing",
            "Keep it on the watchlist and look for stronger trend or volume "
            "confirmation before acting.",
        )

    return (
        "No high-confidence setup is present",
        "Preserve capital and wait for the technical picture to improve rather "
        "than forcing a trade.",
    )


def display_atlas_intelligence(stock: Mapping[str, Any]) -> None:
    """Display the full Atlas Intelligence panel."""

    score = _score(stock)
    verdict = _verdict(stock)
    grade = _safe_text(stock.get("Atlas Grade"), "—")

    st.subheader("🤖 Atlas Intelligence")

    st.markdown(build_intelligence_summary(stock))

    metric1, metric2, metric3 = st.columns(3)

    metric1.metric("Opportunity Rating", f"{score:.1f}/100")
    metric2.metric("Grade", grade)
    metric3.metric("Verdict", verdict)

    st.markdown(f"### {_stars(score)}")

    st.markdown("#### Confidence Breakdown")

    for category, value in build_confidence_breakdown(stock).items():
        st.progress(
            int(max(0, min(value, 100))),
            text=f"{category}: {value:.0f}%",
        )

    st.markdown("#### Trade Checklist")

    icons = {
        "pass": "✅",
        "warning": "⚠️",
        "fail": "❌",
    }

    checklist = build_trade_checklist(stock)

    passed = sum(item["status"] == "pass" for item in checklist)
    total = len(checklist)

    for item in checklist:
        icon = icons[item["status"]]
        st.write(
            f"{icon} **{item['label']}** — {item['detail']}"
        )

    if total:
        st.caption(f"{passed} of {total} technical checks currently pass.")

    title, guidance = build_coach_message(stock)

    st.markdown("#### 🧭 Atlas Coach")

    if score >= 80:
        st.success(f"**{title}** — {guidance}")
    elif score >= 60:
        st.info(f"**{title}** — {guidance}")
    else:
        st.warning(f"**{title}** — {guidance}")

    strengths = _split_items(stock.get("Atlas Strengths"))
    weaknesses = _split_items(stock.get("Atlas Weaknesses"))

    if strengths or weaknesses:
        with st.expander("View Decision Engine evidence"):
            left, right = st.columns(2)

            with left:
                st.markdown("**Strengths**")
                if strengths:
                    for item in strengths:
                        st.write(f"• {item}")
                else:
                    st.caption("No strengths were supplied.")

            with right:
                st.markdown("**Weaknesses**")
                if weaknesses:
                    for item in weaknesses:
                        st.write(f"• {item}")
                else:
                    st.caption("No weaknesses were supplied.")

    st.caption(
        "Atlas provides technical decision support, not financial advice or "
        "a guarantee of future returns."
    )
