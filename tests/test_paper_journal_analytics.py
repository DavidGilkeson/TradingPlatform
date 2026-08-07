import pytest
from paper_trading import PaperAccountService, PaperOrderService
from paper_trading.journal_analytics import build_trade_journal_frame, calculate_journal_analytics
from paper_trading.journal_review import PaperTradeReviewRepository

@pytest.fixture()
def db_path(tmp_path): return tmp_path/"journal.db"

def seed(db_path):
    a=PaperAccountService(str(db_path)); a.initialise_account(starting_balance=20000)
    o=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    o.buy_market(ticker="AAPL",shares=10,market_price=100,confidence=9,atlas_score=92)
    o.sell_market(ticker="AAPL",shares=10,market_price=120,confidence=8,atlas_score=88)
    o.buy_market(ticker="MSFT",shares=5,market_price=200,confidence=6,atlas_score=75)
    o.sell_market(ticker="MSFT",shares=5,market_price=180,confidence=4,atlas_score=60)
    return a

def test_frame(db_path):
    f=build_trade_journal_frame(seed(db_path))
    assert len(f)==2 and set(f["result"])=={"WIN","LOSS"}

def test_analytics(db_path):
    a=calculate_journal_analytics(seed(db_path))
    assert a.total_trades==2 and a.win_rate==pytest.approx(.5)
    assert a.net_pnl==pytest.approx(100)
    assert a.best_trade_ticker=="AAPL" and a.worst_trade_ticker=="MSFT"

def test_review_roundtrip(db_path):
    s=seed(db_path); trade_id=int(build_trade_journal_frame(s).iloc[0]["trade_id"])
    repo=PaperTradeReviewRepository(str(db_path))
    repo.save_review(account_id=s.active_account().id,trade_id=trade_id,followed_plan=True,
                     what_worked="Waited",what_went_wrong="Early exit",
                     lesson_learned="Follow plan",emotional_state="Calm")
    r=repo.get_review(trade_id)
    assert r["followed_plan"]==1 and r["lesson_learned"]=="Follow plan"

def test_empty(db_path):
    s=PaperAccountService(str(db_path)); s.initialise_account()
    a=calculate_journal_analytics(s)
    assert a.total_trades==0 and a.profit_factor is None
