from datetime import datetime,timedelta,timezone
import pytest
from paper_trading import PaperAccountService, PaperOrderService
from paper_trading.performance_analytics import trade_performance_breakdown, performance_trend, risk_adjusted_metrics

@pytest.fixture()
def db_path(tmp_path): return tmp_path/"perf34_2.db"

def seeded(db_path):
    s=PaperAccountService(str(db_path)); a=s.initialise_account(starting_balance=10000)
    o=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    for i,(ticker,buy,sell) in enumerate([("AAPL",100,110),("MSFT",100,95),("NVDA",100,120),("AMD",100,90)]):
        o.buy_market(ticker=ticker,shares=1,market_price=buy); o.sell_market(ticker=ticker,shares=1,market_price=sell)
    with s.database.connect() as c:
        c.execute("DELETE FROM paper_account_snapshots WHERE account_id=?",(a.id,))
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        for i,e in enumerate([10000,10100,10050,10200,10150,10300]):
            c.execute("""INSERT INTO paper_account_snapshots(account_id,cash,positions_value,equity,unrealised_pnl,realised_pnl,captured_at) VALUES(?,?,?,?,?,?,?)""",(a.id,e,0,e,0,e-10000,(base+timedelta(days=i)).isoformat()))
    return s

def test_ticker_breakdown(db_path):
    f=trade_performance_breakdown(seeded(db_path),"ticker")
    assert len(f)==4 and {"Trades","Win Rate","Net P&L","Avg Return"}.issubset(f.columns)

def test_unknown_breakdown_returns_empty(db_path):
    assert trade_performance_breakdown(seeded(db_path),"does_not_exist").empty

def test_performance_trend_has_evidence(db_path):
    t=performance_trend(seeded(db_path),2)
    assert t["recent_count"]==2 and t["prior_count"]==2 and t["status"] in {"Improving","Stable","Declining"}

def test_performance_trend_validation(db_path):
    with pytest.raises(ValueError): performance_trend(seeded(db_path),1)

def test_risk_adjusted_metrics(db_path):
    r=risk_adjusted_metrics(seeded(db_path))
    assert r["annualised_volatility"] is not None and r["positive_day_rate"] is not None
