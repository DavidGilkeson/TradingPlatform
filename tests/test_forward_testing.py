import pandas as pd, pytest
from paper_trading.forward_testing import ForwardTestRepository, forward_test_summary

def test_record(tmp_path):
    r=ForwardTestRepository(str(tmp_path/"f.db"))
    i=r.record(account_id=1,ticker="aapl",decision="TAKEN",atlas_score=85)
    f=r.history(1)
    assert i>0 and f.iloc[0]["ticker"]=="AAPL" and f.iloc[0]["decision"]=="TAKEN"

def test_invalid(tmp_path):
    r=ForwardTestRepository(str(tmp_path/"f.db"))
    with pytest.raises(ValueError): r.record(account_id=1,ticker="AAPL",decision="MAYBE")

def test_summary():
    x=forward_test_summary(pd.DataFrame({"decision":["TAKEN","SKIPPED","WATCH","TAKEN"]}))
    assert x["total"]==4 and x["taken"]==2 and x["discipline_rate"]==pytest.approx(.75)

def test_empty():
    assert forward_test_summary(pd.DataFrame())["discipline_rate"] is None
