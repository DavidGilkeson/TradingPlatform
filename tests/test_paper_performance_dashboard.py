from datetime import datetime,timedelta,timezone
import pytest
from paper_trading import PaperAccountService, PaperOrderService
from paper_trading.performance_analytics import build_equity_history, calculate_performance_summary, daily_performance, rolling_performance

@pytest.fixture()
def db_path(tmp_path): return tmp_path/"perf.db"

def seed(db_path):
    s=PaperAccountService(str(db_path)); a=s.initialise_account(starting_balance=10000)
    o=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    o.buy_market(ticker="AAPL",shares=10,market_price=100); o.sell_market(ticker="AAPL",shares=10,market_price=120)
    o.buy_market(ticker="MSFT",shares=5,market_price=200); o.sell_market(ticker="MSFT",shares=5,market_price=180)
    with s.database.connect() as c:
        c.execute("DELETE FROM paper_account_snapshots WHERE account_id=?",(a.id,))
        base=datetime(2026,1,1,tzinfo=timezone.utc)
        for i,e in enumerate([10000,10200,10100,10300,10050]):
            c.execute("""INSERT INTO paper_account_snapshots(account_id,cash,positions_value,equity,unrealised_pnl,realised_pnl,captured_at)
                         VALUES(?,?,?,?,?,?,?)""",(a.id,e,0,e,0,e-10000,(base+timedelta(days=i)).isoformat()))
    return s

def test_equity_history(db_path):
    h=build_equity_history(seed(db_path))
    assert len(h)==5 and h["peak_equity"].max()==10300 and h["drawdown_pct"].min()<0

def test_summary(db_path):
    s=calculate_performance_summary(seed(db_path))
    assert s.win_rate==pytest.approx(.5)
    assert s.best_trade_return>0 and s.worst_trade_return<0
    assert s.longest_win_streak>=1 and s.longest_loss_streak>=1

def test_daily(db_path):
    d=daily_performance(seed(db_path))
    assert len(d)==5 and "daily_pnl" in d and "daily_return" in d

def test_rolling_validation(db_path):
    with pytest.raises(ValueError): rolling_performance(seed(db_path),1)

def test_rolling_columns(db_path):
    r=rolling_performance(seed(db_path),2)
    assert "rolling_return" in r and "rolling_volatility" in r

def test_empty_history(db_path):
    s=PaperAccountService(str(db_path)); s.initialise_account(starting_balance=5000)
    assert build_equity_history(s).empty
