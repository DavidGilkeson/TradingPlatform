import pandas as pd
from paper_trading.forward_validation import (
    _grade,_evidence_level,build_validation_scorecard,horizon_validation)

def test_evidence_thresholds():
    assert _evidence_level(10)=="Early"
    assert _evidence_level(20)=="Developing"
    assert _evidence_level(50)=="Moderate"
    assert _evidence_level(100)=="Strong"

def test_empty_scorecard():
    c=build_validation_scorecard(pd.DataFrame())
    assert c.score==0 and c.grade=="Early"

def test_tiny_good_sample_cannot_get_high_grade():
    f=pd.DataFrame({
        "forward_test_id":[1,2],
        "horizon_days":[5,5],
        "decision":["TAKEN","SKIPPED"],
        "return_pct":[20,-10],
        "excess_return_pct":[18,-12],
    })
    c=build_validation_scorecard(f)
    assert c.evidence_level=="Early"
    assert c.score<70

def test_horizon_evidence_requires_five_each():
    rows=[]
    for i in range(5):
        rows.append({"horizon_days":5,"decision":"TAKEN",
                     "return_pct":5,"excess_return_pct":2})
        rows.append({"horizon_days":5,"decision":"SKIPPED",
                     "return_pct":1,"excess_return_pct":-1})
    t=horizon_validation(pd.DataFrame(rows))
    assert bool(t.iloc[0]["Evidence Ready"]) is True
    assert t.iloc[0]["Decision Edge"]==4

def test_grade_boundaries():
    assert _grade(85)=="A"
    assert _grade(70)=="B"
    assert _grade(55)=="C"
    assert _grade(40)=="D"
