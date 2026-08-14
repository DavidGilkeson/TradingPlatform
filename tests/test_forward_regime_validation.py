import pandas as pd
from paper_trading.forward_testing import ForwardTestRepository
from paper_trading.cohort_validation import market_regime_validation, volatility_regime_validation

def test_regimes_persist(tmp_path):
    r=ForwardTestRepository(str(tmp_path/"r.db"))
    r.record(account_id=1,ticker="AAPL",decision="TAKEN",market_price=100,
             market_regime="Bullish",volatility_regime="Normal")
    f=r.history(1)
    assert f.iloc[0]["market_regime"]=="Bullish"
    assert f.iloc[0]["volatility_regime"]=="Normal"

def test_regime_columns_exist(tmp_path):
    r=ForwardTestRepository(str(tmp_path/"r.db"))
    with r.database.connect() as c:
        cols={x["name"] for x in c.execute(
            "PRAGMA table_info(paper_forward_tests)").fetchall()}
    assert {"market_regime","volatility_regime"} <= cols

def test_regime_cohorts():
    f=pd.DataFrame({
        "horizon_days":[5]*6,"decision":["TAKEN"]*3+["SKIPPED"]*3,
        "return_pct":[5,6,4,1,0,-1],"excess_return_pct":[3,4,2,-1,-2,-3],
        "atlas_score":[80]*6,"confidence":[8]*6,
        "market_regime":["Bullish"]*6,"volatility_regime":["Normal"]*6})
    assert market_regime_validation(f).iloc[0]["market_regime"]=="Bullish"
    assert volatility_regime_validation(f).iloc[0]["volatility_regime"]=="Normal"
