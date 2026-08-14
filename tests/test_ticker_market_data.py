import pandas as pd

from paper_trading.ticker_market_data import (
    build_ticker_options,
    load_local_ticker_universe,
)


def test_build_options_works_without_scan():
    result=build_ticker_options(
        scan_tickers=[],
        local_tickers=["NVDA","MSFT","AAPL"],
        position_tickers=["AAPL"],
    )
    assert result==["NVDA","MSFT","AAPL"]


def test_intent_ticker_has_priority():
    result=build_ticker_options(
        scan_tickers=["AAPL","MSFT"],
        local_tickers=["NVDA"],
        intent_ticker="TSLA",
    )
    assert result[0]=="TSLA"


def test_load_local_ticker_universe(tmp_path):
    path=tmp_path/"sp500.csv"
    pd.DataFrame({"Ticker":["NVDA","MSFT","BRK.B"]}).to_csv(path,index=False)
    assert load_local_ticker_universe(str(path))==["NVDA","MSFT","BRK-B"]


def test_missing_local_csv_safe(tmp_path):
    assert load_local_ticker_universe(str(tmp_path/"missing.csv"))==[]
