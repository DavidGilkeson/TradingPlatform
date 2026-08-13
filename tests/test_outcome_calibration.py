from paper_trading.outcome_calibration import _score_band

def test_calibration_score_bands():
    assert _score_band(90)=="80-100"
    assert _score_band(80)=="80-100"
    assert _score_band(70)=="60-79"
    assert _score_band(60)=="60-79"
    assert _score_band(50)=="40-59"
    assert _score_band(20)=="0-39"
