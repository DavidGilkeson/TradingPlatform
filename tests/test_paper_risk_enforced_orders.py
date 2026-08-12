import pytest
from paper_trading.risk_manager import calculate_position_size, validate_order_risk

def test_safe_order_passes():
    d = validate_order_risk(
        account_equity=10000,
        cash=10000,
        shares=20,
        entry_price=100,
        stop_price=95,
        risk_pct_limit=1,
        max_position_pct=25,
        minimum_reward_risk=2,
        target_price=110,
    )
    assert d.allowed
    assert d.blockers == []

def test_order_blocked_when_risk_too_high():
    d = validate_order_risk(
        account_equity=10000,
        cash=10000,
        shares=30,
        entry_price=100,
        stop_price=95,
        risk_pct_limit=1,
        max_position_pct=100,
        minimum_reward_risk=2,
        target_price=110,
    )
    assert not d.allowed
    assert any("risk limit" in x for x in d.blockers)

def test_order_blocked_when_position_too_large():
    d = validate_order_risk(
        account_equity=10000,
        cash=10000,
        shares=30,
        entry_price=100,
        stop_price=99.5,
        risk_pct_limit=5,
        max_position_pct=20,
        minimum_reward_risk=2,
        target_price=110,
    )
    assert not d.allowed
    assert any("exposure limit" in x for x in d.blockers)

def test_recommended_size_matches_limits():
    p = calculate_position_size(
        account_equity=25000,
        entry_price=50,
        stop_price=48,
        risk_pct=1,
        max_position_pct=10,
    )
    assert p.recommended_shares == 50

def test_reward_risk_warning_does_not_block():
    d = validate_order_risk(
        account_equity=10000,
        cash=10000,
        shares=10,
        entry_price=100,
        stop_price=95,
        risk_pct_limit=1,
        max_position_pct=20,
        minimum_reward_risk=2,
        target_price=107,
    )
    assert d.allowed
    assert d.warnings
