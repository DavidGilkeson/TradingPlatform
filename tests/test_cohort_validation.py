import pandas as pd
import pytest
from paper_trading.cohort_validation import (
    _score_band,_confidence_band,score_band_validation,
    strongest_cohort,score_monotonicity)

def sample():
    return pd.DataFrame({
        "horizon_days":[5]*10,
        "decision":["TAKEN"]*5+["SKIPPED"]*5,
        "atlas_score":[85,90,88,82,95,65,70,72,68,75],
        "confidence":[9,9,8,8,10,6,6,7,5,7],
        "return_pct":[8,10,7,6,9,1,2,-1,0,1],
        "excess_return_pct":[6,8,5,4,7,-1,0,-3,-2,-1],
    })

def test_bands():
    assert _score_band(85)=="80–100"
    assert _score_band(65)=="60–79"
    assert _confidence_band(9)=="High (8–10)"
    assert _confidence_band(6)=="Medium (5–7.9)"

def test_score_cohorts():
    t=score_band_validation(sample())
    assert set(t["Score Band"])=={"80–100","60–79"}
    assert t["Evidence Ready"].all()

def test_strongest_score_cohort():
    t=score_band_validation(sample())
    leader=strongest_cohort(t,"Score Band")
    assert leader["cohort"]=="80–100"
    assert leader["avg_excess_return"]>0

def test_score_monotonicity():
    c=score_monotonicity(sample(),5)
    assert c is not None and c>0.5

def test_empty():
    assert score_band_validation(pd.DataFrame()).empty
