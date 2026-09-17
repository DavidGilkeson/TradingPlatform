from paper_trading.trade_readiness import assess_trade_readiness

BASE=dict(
    has_market_price=True, thesis="Breakout with momentum",
    invalidation="Close below support", risk_allowed=True,
    guardrails_allowed=True, planned_rr=2.5, minimum_rr=2,
    atlas_score=88, regime_evidence="Favourable",
    behaviour_level="reminder", confirmed=True,
)

def test_ready_when_checklist_complete():
    r=assess_trade_readiness(**BASE)
    assert r["status"]=="Ready"
    assert r["score"]==100
    assert not r["blockers"]

def test_not_ready_on_hard_risk_failure():
    values={**BASE,"risk_allowed":False}
    r=assess_trade_readiness(**values)
    assert r["status"]=="Not Ready"
    assert "Risk controls passed" in r["blockers"]

def test_not_ready_when_rr_below_minimum():
    r=assess_trade_readiness(**{**BASE,"planned_rr":1.5})
    assert r["status"]=="Not Ready"

def test_behaviour_warning_is_caution_not_blocker():
    r=assess_trade_readiness(**{**BASE,"behaviour_level":"caution"})
    assert r["status"]=="Caution"
    assert not r["blockers"]

def test_missing_atlas_score_does_not_block_safe_paper_trade():
    r=assess_trade_readiness(**{**BASE,"atlas_score":None})
    assert r["status"]=="Caution"
    assert not r["blockers"]

def test_confirmation_is_required():
    r=assess_trade_readiness(**{**BASE,"confirmed":False})
    assert r["status"]=="Not Ready"
