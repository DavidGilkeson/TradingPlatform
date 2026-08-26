import pandas as pd
from paper_trading.behaviour_guard import (
    build_behaviour_guard, behaviour_guard_message,
)


def recurring_frame():
    return pd.DataFrame([
        {
            "mistake": "FOMO / chased entry", "realised_pnl": -100,
            "return_pct": -5, "next_time_action": "Wait for confirmation",
            "lesson_learned": "Do not chase",
        },
        {
            "mistake": "FOMO / chased entry", "realised_pnl": -50,
            "return_pct": -2, "next_time_action": "Wait for confirmation",
            "lesson_learned": "Size patiently",
        },
        {
            "mistake": "Exited too early", "realised_pnl": 20,
            "return_pct": 1, "next_time_action": "Trust the target",
            "lesson_learned": "Follow plan",
        },
    ])


def test_recurring_costly_pattern_creates_caution():
    guard = build_behaviour_guard(recurring_frame())
    assert guard["level"] == "caution"
    assert guard["primary_mistake"]["Mistake"] == "FOMO / chased entry"
    assert guard["primary_mistake"]["Occurrences"] == 2


def test_one_off_pattern_is_early_not_strong_warning():
    guard = build_behaviour_guard(recurring_frame().head(1))
    assert guard["level"] == "early"


def test_lessons_are_carried_forward():
    guard = build_behaviour_guard(recurring_frame())
    assert "Wait for confirmation" in guard["lessons"]
    assert guard["lessons"].count("Wait for confirmation") == 1


def test_message_contains_cost_and_pattern():
    guard = build_behaviour_guard(recurring_frame())
    message = behaviour_guard_message(guard)
    assert "FOMO / chased entry" in message
    assert "-150.00" in message


def test_empty_history_safe():
    guard = build_behaviour_guard(pd.DataFrame())
    assert guard["level"] == "insufficient"
    assert guard["primary_mistake"] is None
