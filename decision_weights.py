"""
Configuration for the Project Atlas decision engine.

Each weight represents the maximum number of points that
a category can contribute to the final Atlas score.
"""

DECISION_WEIGHTS = {
    "trend": 35.0,
    "momentum": 25.0,
    "volume": 15.0,
    "rsi": 15.0,
    "risk": 10.0,
}

GRADE_THRESHOLDS = [
    (95.0, "A+"),
    (90.0, "A"),
    (85.0, "A-"),
    (80.0, "B+"),
    (75.0, "B"),
    (70.0, "B-"),
    (65.0, "C+"),
    (60.0, "C"),
    (0.0, "D"),
]

VERDICT_THRESHOLDS = [
    (90.0, "Strong Buy"),
    (80.0, "Buy"),
    (65.0, "Hold"),
    (50.0, "Weak"),
    (0.0, "Avoid"),
]
