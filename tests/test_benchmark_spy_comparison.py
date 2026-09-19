from datetime import datetime,timedelta,timezone
import pandas as pd
import pytest
from paper_trading import PaperAccountService
from paper_trading.performance_analytics import benchmark_comparison_from_history

@pytest.fixture()
def db_path(tmp_path): return tmp_path/"bench34_4.db"

def service_with_history(db_path):
    s=PaperAccountService(str(db_path)); a=s.initialise_account(starting_balance=10000)
    with s.database.connect() as c:
        c.execute("DELETE FROM paper_account_snapshots WHERE account_id=?",(a.id,))
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        for i,e in enumerate([10000,10100,10050,10200,10300,10400]):
            c.execute("INSERT INTO paper_account_snapshots(account_id,cash,positions_value,equity,unrealised_pnl,realised_pnl,captured_at) VALUES(?,?,?,?,?,?,?)",(a.id,e,0,e,0,e-10000,(base+timedelta(days=i)).isoformat()))
    return s

def benchmark():
    return pd.DataFrame({"Date":pd.date_range("2026-01-01",periods=6,tz="UTC"),"Close":[100,100.5,101,101.5,102,102.5]})

def test_benchmark_aligns_same_period(db_path):
    r=benchmark_comparison_from_history(service_with_history(db_path),benchmark())
    assert r["observations"]==6
    assert r["status"]=="Evidence available"
    assert r["account_return"]==pytest.approx(.04)
    assert r["benchmark_return"]==pytest.approx(.025)
    assert r["excess_return"]==pytest.approx(.015)

def test_benchmark_has_drawdown_and_risk_metrics(db_path):
    r=benchmark_comparison_from_history(service_with_history(db_path),benchmark())
    assert r["account_max_drawdown"] < 0
    assert r["benchmark_max_drawdown"] == pytest.approx(0)
    assert r["account_volatility"] is not None
    assert r["benchmark_sharpe"] is not None

def test_benchmark_short_sample_is_labelled(db_path):
    r=benchmark_comparison_from_history(service_with_history(db_path),benchmark().head(3),minimum_days=5)
    assert r["observations"]==3 and r["status"]=="Insufficient evidence"

def test_benchmark_missing_columns_is_safe(db_path):
    r=benchmark_comparison_from_history(service_with_history(db_path),pd.DataFrame({"x":[1]}))
    assert r["status"]=="Insufficient evidence" and r["frame"].empty
