import pandas as pd

from paper_trading.scan_feed import (
    SESSION_SCAN_KEY,
    is_market_scan_frame,
    publish_scan_to_mapping,
    resolve_scan_from_mapping,
)


def sample_frame():
    return pd.DataFrame(
        {
            "Ticker": ["NKE", "NVDA"],
            "Close": [41.23, 180.50],
            "Score": [95, 92],
            "Signal": ["BUY", "BUY"],
        }
    )


def test_market_scan_detection():
    assert is_market_scan_frame(sample_frame())
    assert not is_market_scan_frame(pd.DataFrame({"Close": [10]}))


def test_publish_scan_to_state():
    state = {}
    published = publish_scan_to_mapping(state, sample_frame())

    assert published is not None
    assert SESSION_SCAN_KEY in state
    assert list(state[SESSION_SCAN_KEY]["Ticker"]) == ["NKE", "NVDA"]


def test_explicit_scan_is_preferred_and_persisted():
    old = pd.DataFrame({"Ticker": ["AAPL"], "Close": [100]})
    fresh = sample_frame()
    state = {SESSION_SCAN_KEY: old}

    result = resolve_scan_from_mapping(state, fresh)

    assert list(result["Ticker"]) == ["NKE", "NVDA"]
    assert list(state[SESSION_SCAN_KEY]["Ticker"]) == ["NKE", "NVDA"]


def test_canonical_session_scan_is_recovered():
    frame = sample_frame()
    state = {SESSION_SCAN_KEY: frame}

    result = resolve_scan_from_mapping(state)

    assert result is frame


def test_legacy_df_key_is_recovered():
    frame = sample_frame()
    state = {"df": frame}

    result = resolve_scan_from_mapping(state)

    assert list(result["Ticker"]) == ["NKE", "NVDA"]
    assert SESSION_SCAN_KEY in state


def test_unknown_dataframe_key_is_recovered():
    frame = sample_frame()
    state = {"some_old_scan_variable": frame}

    result = resolve_scan_from_mapping(state)

    assert result is frame
    assert SESSION_SCAN_KEY in state


def test_empty_state_returns_none():
    assert resolve_scan_from_mapping({}) is None
