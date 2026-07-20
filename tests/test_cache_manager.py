"""
Tests for the Project Atlas market cache.
"""

from datetime import datetime, timedelta

import pandas as pd

from cache import cache_manager


def test_save_and_load_market_cache(
    tmp_path,
    monkeypatch,
):
    """
    A saved market scan should load successfully.
    """

    cache_folder = tmp_path / "cache"
    cache_file = cache_folder / "market_scan.pkl"

    monkeypatch.setattr(
        cache_manager,
        "CACHE_FOLDER",
        cache_folder,
    )

    monkeypatch.setattr(
        cache_manager,
        "CACHE_FILE",
        cache_file,
    )

    scan_results = pd.DataFrame(
        {
            "Ticker": ["AAPL", "MSFT"],
            "Score": [85, 90],
        }
    )

    chart_data = {"AAPL": {"close": pd.Series([100.0, 102.0, 105.0])}}

    saved = cache_manager.save_market_cache(
        df=scan_results,
        chart_data=chart_data,
        scan_time=12.5,
    )

    loaded_cache = cache_manager.load_market_cache()

    assert saved is True
    assert cache_file.exists()
    assert loaded_cache is not None
    assert loaded_cache["scan_time"] == 12.5
    assert len(loaded_cache["scan_results"]) == 2
    assert "AAPL" in loaded_cache["chart_data"]


def test_missing_cache_returns_none(
    tmp_path,
    monkeypatch,
):
    """
    Loading a missing cache should return None.
    """

    cache_file = tmp_path / "cache" / "market_scan.pkl"

    monkeypatch.setattr(
        cache_manager,
        "CACHE_FILE",
        cache_file,
    )

    assert cache_manager.load_market_cache() is None


def test_expired_cache_returns_none(
    tmp_path,
    monkeypatch,
):
    """
    An expired cache should not be loaded.
    """

    cache_folder = tmp_path / "cache"
    cache_file = cache_folder / "market_scan.pkl"

    monkeypatch.setattr(
        cache_manager,
        "CACHE_FOLDER",
        cache_folder,
    )

    monkeypatch.setattr(
        cache_manager,
        "CACHE_FILE",
        cache_file,
    )

    scan_results = pd.DataFrame(
        {
            "Ticker": ["AAPL"],
            "Score": [85],
        }
    )

    cache_manager.save_market_cache(
        df=scan_results,
        chart_data={},
        scan_time=10.0,
    )

    import pickle

    with cache_file.open("rb") as file:
        cached_data = pickle.load(file)

    cached_data["timestamp"] = datetime.now() - timedelta(
        minutes=(cache_manager.CACHE_DURATION_MINUTES + 1)
    )

    with cache_file.open("wb") as file:
        pickle.dump(
            cached_data,
            file,
        )

    assert cache_manager.load_market_cache() is None


def test_clear_market_cache(
    tmp_path,
    monkeypatch,
):
    """
    Clearing the cache should delete its file.
    """

    cache_folder = tmp_path / "cache"
    cache_file = cache_folder / "market_scan.pkl"

    monkeypatch.setattr(
        cache_manager,
        "CACHE_FOLDER",
        cache_folder,
    )

    monkeypatch.setattr(
        cache_manager,
        "CACHE_FILE",
        cache_file,
    )

    cache_manager.save_market_cache(
        df=pd.DataFrame({"Ticker": ["AAPL"]}),
        chart_data={},
        scan_time=1.0,
    )

    assert cache_file.exists()

    cleared = cache_manager.clear_market_cache()

    assert cleared is True
    assert not cache_file.exists()
