import pandas as pd
import pytest
from paper_trading.forward_testing import (
    ForwardTestRepository,
    ForwardTestOutcomeRepository,
    due_forward_test_observations,
    update_due_forward_outcomes,
    benchmark_comparison,
)

class FakeMarket:
    benchmark_ticker="SPY"
    def close_on_or_after(self,ticker,date,max_calendar_days=7):
        prices={"AAPL":110.0,"SPY":105.0}
        return prices[ticker],str(pd.Timestamp(date).date())
    def benchmark_return(self,recorded_at,due_date):
        return 100.0,105.0,5.0,str(pd.Timestamp(due_date).date())

def test_due_horizons():
    decisions=pd.DataFrame([{
        "id":1,"ticker":"AAPL","decision":"TAKEN",
        "recorded_at":"2026-01-05T10:00:00+00:00"
    }])
    due=due_forward_test_observations(
        decisions,pd.DataFrame(),now="2026-02-10T00:00:00+00:00")
    assert set(due["horizon_days"])=={1,3,5,10,20}

def test_existing_outcome_not_due():
    decisions=pd.DataFrame([{
        "id":1,"ticker":"AAPL","decision":"TAKEN",
        "recorded_at":"2026-01-05T10:00:00+00:00"
    }])
    outcomes=pd.DataFrame([{"forward_test_id":1,"horizon_days":5}])
    due=due_forward_test_observations(
        decisions,outcomes,now="2026-01-20T00:00:00+00:00")
    assert 5 not in set(due["horizon_days"])

def test_automatic_update_and_excess_return(tmp_path):
    path=str(tmp_path/"auto.db")
    d=ForwardTestRepository(path)
    o=ForwardTestOutcomeRepository(path)
    d.record(account_id=1,ticker="AAPL",decision="TAKEN",
             market_price=100)
    # Rewrite timestamp to make 1-day observation deterministically due.
    with d.database.connect() as c:
        c.execute(
            "UPDATE paper_forward_tests SET recorded_at=?",
            ("2026-01-05T10:00:00+00:00",)
        )
    result=update_due_forward_outcomes(
        db_path=path,account_id=1,market_data=FakeMarket(),
        now="2026-01-07T00:00:00+00:00")
    assert result["updated"]==1
    frame=o.outcomes(1)
    assert frame.iloc[0]["return_pct"]==pytest.approx(10.0)
    assert frame.iloc[0]["benchmark_return_pct"]==pytest.approx(5.0)
    assert frame.iloc[0]["excess_return_pct"]==pytest.approx(5.0)

def test_benchmark_comparison():
    f=pd.DataFrame({
        "horizon_days":[5,5],
        "decision":["TAKEN","SKIPPED"],
        "excess_return_pct":[3.0,-2.0],
    })
    r=benchmark_comparison(f)
    assert len(r)==2
    assert r.loc[r["Decision"]=="TAKEN","Beat Benchmark Rate"].iloc[0]==1.0
