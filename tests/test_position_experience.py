import pytest
from paper_trading.position_experience import build_position_experience

def test_position_in_profit():
    x=build_position_experience(entry_price=100,current_price=110,stop_price=95,target_price=120)
    assert x.status == "In profit"
    assert x.reward_risk_ratio == pytest.approx(4)

def test_near_stop_has_priority():
    x=build_position_experience(entry_price=100,current_price=97,stop_price=95,target_price=120)
    assert x.status == "Near stop"

def test_target_reached():
    x=build_position_experience(entry_price=100,current_price=121,stop_price=95,target_price=120)
    assert x.status == "Target reached"

def test_invalid_prices_rejected():
    with pytest.raises(ValueError): build_position_experience(entry_price=0,current_price=100)
