"""
Tests for the Project Atlas decision engine.
"""

import pytest

from decision_engine import (
    calculate_confidence,
    calculate_grade,
    calculate_verdict,
    evaluate_stock,
)


def test_strong_bullish_stock_receives_high_rating():
    """
    A technically strong stock should receive a strong grade
    and positive verdict.
    """

    metrics = {
        "Ticker": "ATLS",
        "price": 150.0,
        "ma20": 145.0,
        "ma50": 135.0,
        "ma200": 110.0,
        "momentum_score": 92.0,
        "relative_volume": 1.8,
        "rsi": 59.0,
        "risk_score": 90.0,
        "macd": 4.0,
        "macd_signal": 2.0,
    }

    result = evaluate_stock(metrics)

    assert result["ticker"] == "ATLS"
    assert result["score"] >= 85.0
    assert result["grade"] in {
        "A+",
        "A",
        "A-",
    }
    assert result["verdict"] in {
        "Strong Buy",
        "Buy",
    }
    assert result["stars"] >= 4
    assert result["strengths"]


def test_weak_stock_receives_low_rating():
    """
    A weak technical setup should not receive a buy verdict.
    """

    metrics = {
        "Ticker": "WEAK",
        "price": 70.0,
        "ma20": 80.0,
        "ma50": 90.0,
        "ma200": 100.0,
        "momentum_score": 20.0,
        "relative_volume": 0.5,
        "rsi": 25.0,
        "risk_score": 20.0,
        "macd": -4.0,
        "macd_signal": -1.0,
    }

    result = evaluate_stock(metrics)

    assert result["score"] < 65.0
    assert result["grade"] == "D"
    assert result["verdict"] in {
        "Weak",
        "Avoid",
    }
    assert result["stars"] == 1
    assert result["weaknesses"]


@pytest.mark.parametrize(
    ("score", "expected_grade"),
    [
        (95.0, "A+"),
        (94.99, "A"),
        (90.0, "A"),
        (89.99, "A-"),
        (85.0, "A-"),
        (84.99, "B+"),
        (80.0, "B+"),
        (75.0, "B"),
        (70.0, "B-"),
        (65.0, "C+"),
        (60.0, "C"),
        (59.99, "D"),
    ],
)
def test_grade_boundaries(
    score,
    expected_grade,
):
    assert calculate_grade(score) == expected_grade


@pytest.mark.parametrize(
    ("score", "expected_verdict"),
    [
        (95.0, "Strong Buy"),
        (90.0, "Strong Buy"),
        (89.99, "Buy"),
        (80.0, "Buy"),
        (79.99, "Hold"),
        (65.0, "Hold"),
        (64.99, "Weak"),
        (50.0, "Weak"),
        (49.99, "Avoid"),
    ],
)
def test_verdict_boundaries(
    score,
    expected_verdict,
):
    assert calculate_verdict(score) == expected_verdict


def test_confidence_output():
    confidence, stars, star_display = calculate_confidence(88.0)

    assert confidence == "High"
    assert stars == 4
    assert star_display == "★★★★☆"


def test_explanations_match_known_metrics():
    metrics = {
        "price": 150.0,
        "ma20": 140.0,
        "ma50": 130.0,
        "ma200": 100.0,
        "rsi": 82.0,
        "relative_volume": 1.7,
        "distance_to_resistance": 1.0,
        "momentum_score": 90.0,
        "risk_score": 70.0,
    }

    result = evaluate_stock(metrics)

    strengths_text = " ".join(result["strengths"])

    weaknesses_text = " ".join(result["weaknesses"])

    assert "20-day moving average" in strengths_text
    assert "relative volume" in strengths_text.lower()
    assert "overbought" in weaknesses_text.lower()
    assert "resistance" in weaknesses_text.lower()


def test_missing_metrics_do_not_crash_engine():
    result = evaluate_stock(
        {
            "Ticker": "SAFE",
        }
    )

    assert result["ticker"] == "SAFE"
    assert 0.0 <= result["score"] <= 100.0
    assert result["grade"]
    assert result["verdict"]
    assert result["breakdown"]
