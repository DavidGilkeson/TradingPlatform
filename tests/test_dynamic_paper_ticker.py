import pandas as pd

from paper_trading.dynamic_ticker import scan_tickers, valid_scan_price


def test_scan_tickers_preserve_scan_order():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA", "MSFT", "AAPL", "NVDA"],
            "Close": [120, 400, 220, 120],
        }
    )
    assert scan_tickers(frame) == ["NVDA", "MSFT", "AAPL"]


def test_scan_tickers_normalise_case_and_spaces():
    frame = pd.DataFrame(
        {
            "Ticker": [" nvda ", "msft", None],
            "Close": [120, 400, 10],
        }
    )
    assert scan_tickers(frame) == ["NVDA", "MSFT"]


def test_valid_scan_price_reads_close():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA"],
            "Close": [123.45],
        }
    )
    assert valid_scan_price("NVDA", frame) == 123.45


def test_invalid_price_has_no_100_dollar_fallback():
    frame = pd.DataFrame(
        {
            "Ticker": ["NVDA"],
            "Close": [None],
        }
    )
    assert valid_scan_price("NVDA", frame) is None


def test_missing_ticker_has_no_fake_price():
    frame = pd.DataFrame(
        {
            "Ticker": ["MSFT"],
            "Close": [400.0],
        }
    )
    assert valid_scan_price("NVDA", frame) is None
