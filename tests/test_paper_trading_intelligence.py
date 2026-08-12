import pytest
from paper_trading import PaperAccountService, PaperOrderService
from paper_trading.trading_intelligence import (
    derive_intelligence_summary, performance_by_atlas_score,
    performance_by_confidence, performance_by_ticker, performance_by_verdict)

@pytest.fixture()
def db_path(tmp_path): return tmp_path/"intel.db"

def seed(db_path):
    a=PaperAccountService(str(db_path)); a.initialise_account(starting_balance=20000)
    o=PaperOrderService(str(db_path),commission=0,slippage_pct=0)
    o.buy_market(ticker="AAPL",shares=10,market_price=100,reason="Strong Buy",confidence=9,atlas_score=95)
    o.sell_market(ticker="AAPL",shares=10,market_price=120,reason="Strong Buy",confidence=9,atlas_score=95)
    o.buy_market(ticker="MSFT",shares=5,market_price=200,reason="Buy",confidence=6,atlas_score=78)
    o.sell_market(ticker="MSFT",shares=5,market_price=180,reason="Buy",confidence=6,atlas_score=78)
    return a

def test_ticker(db_path):
    assert list(performance_by_ticker(seed(db_path))["ticker"])==["AAPL","MSFT"]

def test_confidence(db_path):
    f=performance_by_confidence(seed(db_path))
    assert set(f["confidence"])=={6,9} and f.iloc[0]["confidence"]==9

def test_score(db_path):
    f=performance_by_atlas_score(seed(db_path))
    assert not f.empty and str(f.iloc[0]["Atlas Score Band"])=="90+"

def test_verdict(db_path):
    assert set(performance_by_verdict(seed(db_path))["Verdict"])=={"Strong Buy","Buy"}

def test_summary(db_path):
    s=derive_intelligence_summary(seed(db_path))
    assert s.total_trades==2 and s.best_ticker=="AAPL" and s.best_atlas_score_band=="90+" and s.best_confidence_level==9

def test_empty(db_path):
    a=PaperAccountService(str(db_path)); a.initialise_account()
    s=derive_intelligence_summary(a)
    assert s.total_trades==0 and s.best_ticker is None
