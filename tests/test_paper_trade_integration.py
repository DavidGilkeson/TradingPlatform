import pandas as pd
from paper_trading.trade_integration import prepare_quick_trade_candidates,trade_candidate_summary

def test_rank():
    f=pd.DataFrame([{"Ticker":"MSFT","Atlas Score":80},{"Ticker":"AAPL","Atlas Score":95},{"Ticker":"NVDA","Atlas Score":90}])
    assert list(prepare_quick_trade_candidates(f)["Ticker"])==["AAPL","NVDA","MSFT"]

def test_filter():
    f=pd.DataFrame([{"Ticker":"AAPL","Atlas Score":95},{"Ticker":"MSFT","Atlas Score":70}])
    assert list(prepare_quick_trade_candidates(f,minimum_score=80)["Ticker"])==["AAPL"]

def test_dedupe():
    f=pd.DataFrame([{"Ticker":"aapl","Atlas Score":95},{"Ticker":"AAPL","Atlas Score":90}])
    assert len(prepare_quick_trade_candidates(f))==1

def test_empty():
    assert prepare_quick_trade_candidates(None).empty

def test_summary():
    assert trade_candidate_summary({"Ticker":"nvda","Atlas Score":92,"Atlas Verdict":"Strong Buy","Atlas Confidence":"High"})=={
        "ticker":"NVDA","score":92,"verdict":"Strong Buy","confidence":"High"}
