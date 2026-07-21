"""
decision_engine.py

Deterministic stock evaluation engine for Project Atlas.

The module converts technical metrics into a structured decision
containing a score, grade, confidence level, verdict, explanations,
and category-level scoring details.

It contains no Streamlit or chart code and can therefore be reused
by the dashboard, scanner, tests, APIs, or future AI features.
"""

from __future__ import annotations

from typing import Any

from decision_weights import (
    DECISION_WEIGHTS,
    GRADE_THRESHOLDS,
    VERDICT_THRESHOLDS,
)


def _to_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Convert a value to float without allowing invalid data
    to crash the decision engine.
    """

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def _clamp(
    value: float,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    """
    Restrict a numeric value to a defined range.
    """

    return max(
        minimum,
        min(value, maximum),
    )


def _get_metric(
    metrics: dict[str, Any],
    *names: str,
    default: float = 0.0,
) -> float:
    """
    Return the first available metric from a collection of aliases.

    This allows Atlas to support names such as:

    - RSI
    - rsi
    - rsi_value
    - RSI Value
    """

    normalised_metrics = {
        str(key).strip().lower().replace(" ", "_"): value
        for key, value in metrics.items()
    }

    for name in names:
        normalised_name = name.strip().lower().replace(" ", "_")

        if normalised_name in normalised_metrics:
            return _to_float(
                normalised_metrics[normalised_name],
                default=default,
            )

    return default


def _get_boolean(
    metrics: dict[str, Any],
    *names: str,
    default: bool = False,
) -> bool:
    """
    Read a Boolean-style metric using common representations.
    """

    normalised_metrics = {
        str(key).strip().lower().replace(" ", "_"): value
        for key, value in metrics.items()
    }

    for name in names:
        normalised_name = name.strip().lower().replace(" ", "_")

        if normalised_name not in normalised_metrics:
            continue

        value = normalised_metrics[normalised_name]

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        if isinstance(value, str):
            return value.strip().lower() in {
                "true",
                "yes",
                "1",
                "buy",
                "bullish",
                "above",
            }

    return default


def _normalise_component_score(
    score: float,
    weight: float,
) -> float:
    """
    Convert a zero-to-100 component score into weighted points.
    """

    score = _clamp(score)

    return round(
        score / 100.0 * weight,
        2,
    )


def score_trend(
    metrics: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """
    Score trend quality using moving-average position,
    moving-average alignment, and any existing trend metric.
    """

    existing_trend_score = _get_metric(
        metrics,
        "trend_score",
        "trend_strength",
        "trend",
        default=-1.0,
    )

    price = _get_metric(
        metrics,
        "price",
        "close",
        "current_price",
        "latest_close",
    )

    ma20 = _get_metric(
        metrics,
        "ma20",
        "20_day_ma",
        "sma20",
        "ma_20",
    )

    ma50 = _get_metric(
        metrics,
        "ma50",
        "50_day_ma",
        "sma50",
        "ma_50",
    )

    ma200 = _get_metric(
        metrics,
        "ma200",
        "200_day_ma",
        "sma200",
        "ma_200",
    )

    if existing_trend_score >= 0:
        raw_score = _clamp(existing_trend_score)

    else:
        raw_score = 40.0

        if price > 0 and ma20 > 0:
            raw_score += 15.0 if price > ma20 else -10.0

        if price > 0 and ma50 > 0:
            raw_score += 20.0 if price > ma50 else -15.0

        if price > 0 and ma200 > 0:
            raw_score += 15.0 if price > ma200 else -15.0

        if ma20 > 0 and ma50 > 0:
            raw_score += 5.0 if ma20 > ma50 else -5.0

        if ma50 > 0 and ma200 > 0:
            raw_score += 5.0 if ma50 > ma200 else -5.0

        raw_score = _clamp(raw_score)

    points = _normalise_component_score(
        raw_score,
        DECISION_WEIGHTS["trend"],
    )

    return points, {
        "raw_score": round(raw_score, 2),
        "maximum_points": DECISION_WEIGHTS["trend"],
    }


def score_momentum(
    metrics: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """
    Score momentum using an existing momentum score,
    price strength, and MACD-style data when available.
    """

    existing_score = _get_metric(
        metrics,
        "momentum_score",
        "momentum",
        default=-1.0,
    )

    strength_percent = _get_metric(
        metrics,
        "strength_%",
        "strength_percent",
        "strength",
        "price_change_percent",
        "return_percent",
    )

    macd = _get_metric(
        metrics,
        "macd",
        "macd_value",
    )

    macd_signal = _get_metric(
        metrics,
        "macd_signal",
        "signal_line",
    )

    if existing_score >= 0:
        raw_score = _clamp(existing_score)

    else:
        raw_score = 50.0

        raw_score += _clamp(
            strength_percent * 2.5,
            minimum=-25.0,
            maximum=25.0,
        )

        if macd != 0 or macd_signal != 0:
            raw_score += 15.0 if macd > macd_signal else -15.0

        raw_score = _clamp(raw_score)

    points = _normalise_component_score(
        raw_score,
        DECISION_WEIGHTS["momentum"],
    )

    return points, {
        "raw_score": round(raw_score, 2),
        "maximum_points": DECISION_WEIGHTS["momentum"],
    }


def score_volume(
    metrics: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """
    Score volume confirmation using relative volume or
    percentage volume change.
    """

    existing_score = _get_metric(
        metrics,
        "volume_score",
        default=-1.0,
    )

    relative_volume = _get_metric(
        metrics,
        "relative_volume",
        "relative_vol",
        "volume_ratio",
        "rvol",
    )

    volume_change = _get_metric(
        metrics,
        "volume_change",
        "volume_change_percent",
        "volume_%",
        "volume_percent",
    )

    if existing_score >= 0:
        raw_score = _clamp(existing_score)

    elif relative_volume > 0:
        if relative_volume >= 2.0:
            raw_score = 100.0
        elif relative_volume >= 1.5:
            raw_score = 90.0
        elif relative_volume >= 1.2:
            raw_score = 80.0
        elif relative_volume >= 1.0:
            raw_score = 70.0
        elif relative_volume >= 0.8:
            raw_score = 55.0
        else:
            raw_score = 35.0

    elif volume_change != 0:
        raw_score = _clamp(
            50.0 + volume_change,
        )

    else:
        raw_score = 50.0

    points = _normalise_component_score(
        raw_score,
        DECISION_WEIGHTS["volume"],
    )

    return points, {
        "raw_score": round(raw_score, 2),
        "maximum_points": DECISION_WEIGHTS["volume"],
    }


def score_rsi(
    metrics: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """
    Score RSI based on a balanced bullish range.

    Atlas favours RSI values that show positive momentum without
    indicating that a stock is severely overbought.
    """

    rsi = _get_metric(
        metrics,
        "rsi",
        "rsi_value",
        "rsi_14",
        default=50.0,
    )

    if 50.0 <= rsi <= 65.0:
        raw_score = 100.0
    elif 45.0 <= rsi < 50.0:
        raw_score = 85.0
    elif 65.0 < rsi <= 70.0:
        raw_score = 80.0
    elif 40.0 <= rsi < 45.0:
        raw_score = 65.0
    elif 70.0 < rsi <= 75.0:
        raw_score = 55.0
    elif 30.0 <= rsi < 40.0:
        raw_score = 45.0
    elif 75.0 < rsi <= 80.0:
        raw_score = 30.0
    elif rsi < 30.0:
        raw_score = 35.0
    else:
        raw_score = 10.0

    points = _normalise_component_score(
        raw_score,
        DECISION_WEIGHTS["rsi"],
    )

    return points, {
        "raw_score": round(raw_score, 2),
        "rsi": round(rsi, 2),
        "maximum_points": DECISION_WEIGHTS["rsi"],
    }


def score_risk(
    metrics: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """
    Score risk favourably when volatility and drawdown are controlled.

    A high risk score means the stock currently has a healthier
    risk profile.
    """

    existing_score = _get_metric(
        metrics,
        "risk_score",
        "risk_health_score",
        default=-1.0,
    )

    volatility = _get_metric(
        metrics,
        "volatility",
        "volatility_percent",
        "annualised_volatility",
    )

    drawdown = abs(
        _get_metric(
            metrics,
            "drawdown",
            "maximum_drawdown",
            "max_drawdown",
        )
    )

    distance_to_resistance = _get_metric(
        metrics,
        "distance_to_resistance",
        "resistance_distance_percent",
        default=10.0,
    )

    if existing_score >= 0:
        raw_score = _clamp(existing_score)

    else:
        raw_score = 80.0

        if volatility > 0:
            if volatility > 60.0:
                raw_score -= 35.0
            elif volatility > 40.0:
                raw_score -= 25.0
            elif volatility > 25.0:
                raw_score -= 12.0
            else:
                raw_score += 5.0

        if drawdown > 0:
            if drawdown > 30.0:
                raw_score -= 30.0
            elif drawdown > 20.0:
                raw_score -= 20.0
            elif drawdown > 10.0:
                raw_score -= 10.0

        if 0 <= distance_to_resistance < 2.0:
            raw_score -= 15.0
        elif distance_to_resistance >= 5.0:
            raw_score += 5.0

        raw_score = _clamp(raw_score)

    points = _normalise_component_score(
        raw_score,
        DECISION_WEIGHTS["risk"],
    )

    return points, {
        "raw_score": round(raw_score, 2),
        "maximum_points": DECISION_WEIGHTS["risk"],
    }


def calculate_grade(
    score: float,
) -> str:
    """
    Convert the Atlas score into a letter grade.
    """

    score = _clamp(score)

    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade

    return "D"


def calculate_confidence(
    score: float,
) -> tuple[str, int, str]:
    """
    Return confidence label, star count, and visual stars.
    """

    score = _clamp(score)

    if score >= 95.0:
        label = "Very High"
        stars = 5
    elif score >= 85.0:
        label = "High"
        stars = 4
    elif score >= 75.0:
        label = "Moderate"
        stars = 3
    elif score >= 65.0:
        label = "Low"
        stars = 2
    else:
        label = "Very Low"
        stars = 1

    star_display = "★" * stars + "☆" * (5 - stars)

    return label, stars, star_display


def calculate_verdict(
    score: float,
) -> str:
    """
    Convert the Atlas score into a consistent verdict.
    """

    score = _clamp(score)

    for threshold, verdict in VERDICT_THRESHOLDS:
        if score >= threshold:
            return verdict

    return "Avoid"


def generate_strengths(
    metrics: dict[str, Any],
) -> list[str]:
    """
    Build deterministic positive explanations.
    """

    strengths: list[str] = []

    price = _get_metric(
        metrics,
        "price",
        "close",
        "current_price",
        "latest_close",
    )

    ma20 = _get_metric(
        metrics,
        "ma20",
        "20_day_ma",
        "sma20",
    )

    ma50 = _get_metric(
        metrics,
        "ma50",
        "50_day_ma",
        "sma50",
    )

    ma200 = _get_metric(
        metrics,
        "ma200",
        "200_day_ma",
        "sma200",
    )

    rsi = _get_metric(
        metrics,
        "rsi",
        "rsi_value",
        "rsi_14",
        default=50.0,
    )

    relative_volume = _get_metric(
        metrics,
        "relative_volume",
        "relative_vol",
        "volume_ratio",
        "rvol",
    )

    volume_change = _get_metric(
        metrics,
        "volume_change",
        "volume_change_percent",
        "volume_%",
    )

    momentum = _get_metric(
        metrics,
        "momentum_score",
        "momentum",
        default=50.0,
    )

    macd = _get_metric(
        metrics,
        "macd",
    )

    macd_signal = _get_metric(
        metrics,
        "macd_signal",
        "signal_line",
    )

    if price > 0 and ma20 > 0 and price > ma20:
        strengths.append("Price is trading above the 20-day moving average.")

    if price > 0 and ma50 > 0 and price > ma50:
        strengths.append("Price is trading above the 50-day moving average.")

    if ma20 > 0 and ma50 > 0 and ma20 > ma50:
        strengths.append("Short-term trend is aligned above the medium-term trend.")

    if ma50 > 0 and ma200 > 0 and ma50 > ma200:
        strengths.append("The long-term moving-average structure is bullish.")

    if 50.0 <= rsi <= 65.0:
        strengths.append("RSI shows healthy bullish momentum without being overbought.")
    elif 45.0 <= rsi < 50.0:
        strengths.append("RSI is improving from a neutral level.")

    if relative_volume >= 1.5:
        strengths.append("Strong relative volume confirms increased market interest.")
    elif relative_volume >= 1.1:
        strengths.append("Volume is above its recent average.")
    elif volume_change >= 15.0:
        strengths.append("Trading volume is increasing.")

    if momentum >= 75.0:
        strengths.append("Momentum is currently strong.")

    if (macd != 0 or macd_signal != 0) and macd > macd_signal:
        strengths.append("MACD is above its signal line.")

    bullish_breakout = _get_boolean(
        metrics,
        "bullish_breakout",
        "breakout",
    )

    if bullish_breakout:
        strengths.append("Price has produced a bullish breakout signal.")

    if not strengths:
        strengths.append("The stock has a broadly neutral technical profile.")

    return strengths


def generate_weaknesses(
    metrics: dict[str, Any],
) -> list[str]:
    """
    Build deterministic risk and weakness explanations.
    """

    weaknesses: list[str] = []

    price = _get_metric(
        metrics,
        "price",
        "close",
        "current_price",
        "latest_close",
    )

    ma20 = _get_metric(
        metrics,
        "ma20",
        "20_day_ma",
        "sma20",
    )

    ma50 = _get_metric(
        metrics,
        "ma50",
        "50_day_ma",
        "sma50",
    )

    ma200 = _get_metric(
        metrics,
        "ma200",
        "200_day_ma",
        "sma200",
    )

    rsi = _get_metric(
        metrics,
        "rsi",
        "rsi_value",
        "rsi_14",
        default=50.0,
    )

    relative_volume = _get_metric(
        metrics,
        "relative_volume",
        "relative_vol",
        "volume_ratio",
        "rvol",
    )

    volatility = _get_metric(
        metrics,
        "volatility",
        "volatility_percent",
        "annualised_volatility",
    )

    distance_to_resistance = _get_metric(
        metrics,
        "distance_to_resistance",
        "resistance_distance_percent",
        default=10.0,
    )

    if price > 0 and ma20 > 0 and price < ma20:
        weaknesses.append("Price is trading below the 20-day moving average.")

    if price > 0 and ma50 > 0 and price < ma50:
        weaknesses.append("Price is trading below the 50-day moving average.")

    if price > 0 and ma200 > 0 and price < ma200:
        weaknesses.append("Price remains below the long-term moving average.")

    if rsi > 80.0:
        weaknesses.append("RSI indicates severely overbought conditions.")
    elif rsi > 70.0:
        weaknesses.append("RSI indicates potentially overbought conditions.")
    elif rsi < 30.0:
        weaknesses.append("RSI indicates weak momentum and oversold conditions.")

    if 0 < relative_volume < 0.8:
        weaknesses.append("Trading volume is below its recent average.")

    if volatility > 60.0:
        weaknesses.append("The stock currently has very high volatility.")
    elif volatility > 40.0:
        weaknesses.append("The stock currently has elevated volatility.")

    if 0 <= distance_to_resistance < 2.0:
        weaknesses.append("Price is trading close to a resistance level.")

    bearish_divergence = _get_boolean(
        metrics,
        "bearish_divergence",
    )

    if bearish_divergence:
        weaknesses.append("A bearish momentum divergence may be developing.")

    if not weaknesses:
        weaknesses.append("No major technical weaknesses were detected.")

    return weaknesses


def evaluate_stock(
    metrics: dict[str, Any],
) -> dict[str, Any]:
    """
    Evaluate one stock and return the complete Atlas decision.

    Parameters
    ----------
    metrics:
        Dictionary containing scanner or indicator values.

    Returns
    -------
    dict:
        Structured Atlas decision suitable for dashboards,
        reports, ranking, testing, and future AI explanations.
    """

    trend_points, trend_details = score_trend(metrics)

    momentum_points, momentum_details = score_momentum(metrics)

    volume_points, volume_details = score_volume(metrics)

    rsi_points, rsi_details = score_rsi(metrics)

    risk_points, risk_details = score_risk(metrics)

    score = round(
        trend_points + momentum_points + volume_points + rsi_points + risk_points,
        2,
    )

    score = _clamp(score)

    confidence, stars, star_display = calculate_confidence(score)

    breakdown = {
        "Trend": {
            "points": trend_points,
            **trend_details,
        },
        "Momentum": {
            "points": momentum_points,
            **momentum_details,
        },
        "Volume": {
            "points": volume_points,
            **volume_details,
        },
        "RSI": {
            "points": rsi_points,
            **rsi_details,
        },
        "Risk": {
            "points": risk_points,
            **risk_details,
        },
    }

    ticker = str(
        metrics.get(
            "Ticker",
            metrics.get(
                "ticker",
                "",
            ),
        )
    ).upper()

    return {
        "ticker": ticker,
        "score": round(score, 2),
        "grade": calculate_grade(score),
        "confidence": confidence,
        "stars": stars,
        "star_display": star_display,
        "verdict": calculate_verdict(score),
        "strengths": generate_strengths(metrics),
        "weaknesses": generate_weaknesses(metrics),
        "breakdown": breakdown,
    }
