"""
strategy.py

Contains the trading strategy and stock scoring logic.
"""


def calculate_score(signal, strength):
    """
    Calculate a basic score using the trading signal
    and moving-average trend strength.

    Maximum current score: 80 points.
    """

    score = 0

    # Award points for a bullish moving-average signal
    if signal == "BUY":
        score += 50

    # Award additional points based on trend strength
    if strength > 10:
        score += 30
    elif strength > 5:
        score += 20
    elif strength > 2:
        score += 10

    return score