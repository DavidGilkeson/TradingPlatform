import pytest
from paper_trading.risk_manager import calculate_position_size,validate_order_risk

def test_position_size_by_one_percent_risk():
    p=calculate_position_size(
        account_equity=10000,entry_price=100,stop_price=95,
        risk_pct=1,max_position_pct=100)
    assert p.max_risk_amount==pytest.approx(100)
    assert p.risk_per_share==pytest.approx(5)
    assert p.recommended_shares==20

def test_position_size_respects_exposure_cap():
    p=calculate_position_size(
        account_equity=10000,entry_price=100,stop_price=99,
        risk_pct=5,max_position_pct=10)
    assert p.recommended_shares==10
    assert p.position_value==pytest.approx(1000)

def test_reward_risk():
    p=calculate_position_size(
        account_equity=10000,entry_price=100,stop_price=95,
        target_price=110,risk_pct=1,max_position_pct=100)
    assert p.reward_risk_ratio==pytest.approx(2)

def test_invalid_long_stop():
    with pytest.raises(ValueError):
        calculate_position_size(
            account_equity=10000,entry_price=100,stop_price=101)

def test_risk_validator_blocks_excess_trade_risk():
    d=validate_order_risk(
        account_equity=10000,cash=10000,shares=50,
        entry_price=100,stop_price=95,risk_pct_limit=1,
        max_position_pct=100,target_price=110)
    assert not d.allowed
    assert d.blockers

def test_risk_validator_warns_low_reward_risk():
    d=validate_order_risk(
        account_equity=10000,cash=10000,shares=10,
        entry_price=100,stop_price=95,risk_pct_limit=1,
        max_position_pct=100,target_price=104,
        minimum_reward_risk=2)
    assert d.allowed
    assert d.warnings

def test_risk_validator_blocks_cash_overrun():
    d=validate_order_risk(
        account_equity=10000,cash=500,shares=10,
        entry_price=100,stop_price=99,risk_pct_limit=5,
        max_position_pct=100,target_price=110)
    assert not d.allowed
    assert any("cash" in x.lower() for x in d.blockers)
