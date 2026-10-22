import time
import pandas as pd
import pytest
from atlas_cache import TTLCache


def test_cache_computes_once_and_tracks_hits():
    cache = TTLCache(ttl_seconds=10)
    calls = []
    fn = lambda: calls.append(1) or 42
    assert cache.get_or_compute('x', fn) == 42
    assert cache.get_or_compute('x', fn) == 42
    assert len(calls) == 1
    assert cache.info().hits == 1
    assert cache.info().misses == 1


def test_cache_expiry_recomputes():
    cache = TTLCache(ttl_seconds=0.01)
    cache.set('x', 1)
    time.sleep(0.02)
    assert cache.get('x') is None


def test_none_is_not_cached():
    cache = TTLCache()
    calls = []
    fn = lambda: calls.append(1) or None
    assert cache.get_or_compute('x', fn) is None
    assert cache.get_or_compute('x', fn) is None
    assert len(calls) == 2


def test_mutable_values_are_defensively_copied():
    cache = TTLCache()
    original = pd.DataFrame({'price': [10]})
    cache.set('df', original)
    returned = cache.get('df')
    returned.loc[0, 'price'] = 999
    assert cache.get('df').loc[0, 'price'] == 10


def test_lru_capacity_and_clear():
    cache = TTLCache(max_entries=2)
    cache.set('a', 1); cache.set('b', 2); cache.set('c', 3)
    assert cache.info().entries == 2
    assert cache.get('a') is None
    cache.clear('b')
    assert cache.get('b') is None
    cache.clear()
    assert cache.info().entries == 0


def test_invalid_cache_configuration():
    with pytest.raises(ValueError):
        TTLCache(ttl_seconds=0)
    with pytest.raises(ValueError):
        TTLCache(max_entries=0)
