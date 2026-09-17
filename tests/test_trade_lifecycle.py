from paper_trading.lifecycle import lifecycle_state, lifecycle_text


def test_lifecycle_tracks_end_to_end_progress():
    state = lifecycle_state(
        has_scan=True, has_analysis=True, has_plan=True,
        readiness_status="Ready", has_open_position=True,
        has_completed_trade=False, has_review=False, has_learning=False,
    )
    assert state["completed"] == 5
    assert state["total"] == 8
    assert state["next_stage"] == "Completed Trade"
    assert "✓ Find Opportunity" in lifecycle_text(state)


def test_caution_is_a_completed_readiness_review():
    state = lifecycle_state(readiness_status="Caution")
    assert state["stages"][3]["complete"] is True


def test_not_ready_keeps_readiness_open():
    state = lifecycle_state(readiness_status="Not Ready")
    assert state["stages"][3]["complete"] is False
    assert state["next_stage"] == "Find Opportunity"


def test_complete_cycle():
    state = lifecycle_state(
        has_scan=True, has_analysis=True, has_plan=True,
        readiness_status="Ready", has_open_position=True,
        has_completed_trade=True, has_review=True, has_learning=True,
    )
    assert state["pct"] == 1.0
    assert state["next_stage"] == "Cycle complete"
