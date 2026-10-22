"""Small thread-safe TTL cache for expensive, repeatable Atlas reads.

Caches only successful/non-None values by default. Callers can clear individual
keys or the entire cache after data refreshes. Returned mutable values are copied
when pandas is available so callers cannot mutate the cached object by accident.
"""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Any, Callable, Hashable


def _copy_value(value: Any) -> Any:
    try:
        import pandas as pd
        if isinstance(value, (pd.DataFrame, pd.Series)):
            return value.copy(deep=True)
    except ImportError:
        pass
    if isinstance(value, (dict, list, set)):
        import copy
        return copy.deepcopy(value)
    return value


@dataclass(frozen=True)
class CacheInfo:
    hits: int
    misses: int
    entries: int


class TTLCache:
    """Bounded TTL cache with deterministic expiry and thread-safe operations."""
    def __init__(self, ttl_seconds: float = 60.0, max_entries: int = 256):
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than zero")
        if max_entries < 1:
            raise ValueError("max_entries must be at least one")
        self.ttl_seconds = float(ttl_seconds)
        self.max_entries = int(max_entries)
        self._items: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._lock = RLock()
        self._hits = self._misses = 0

    def get(self, key: Hashable, default: Any = None) -> Any:
        now = monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None or item[0] <= now:
                if item is not None:
                    self._items.pop(key, None)
                self._misses += 1
                return default
            self._items.move_to_end(key)
            self._hits += 1
            return _copy_value(item[1])

    def set(self, key: Hashable, value: Any) -> None:
        if value is None:
            return
        with self._lock:
            self._items[key] = (monotonic() + self.ttl_seconds, _copy_value(value))
            self._items.move_to_end(key)
            while len(self._items) > self.max_entries:
                self._items.popitem(last=False)

    def get_or_compute(self, key: Hashable, compute: Callable[[], Any]) -> Any:
        sentinel = object()
        value = self.get(key, sentinel)
        if value is not sentinel:
            return value
        value = compute()
        self.set(key, value)
        return _copy_value(value)

    def clear(self, key: Hashable | None = None) -> None:
        with self._lock:
            if key is None:
                self._items.clear()
                self._hits = self._misses = 0
            else:
                self._items.pop(key, None)

    def info(self) -> CacheInfo:
        now = monotonic()
        with self._lock:
            expired = [key for key, (expires, _) in self._items.items() if expires <= now]
            for key in expired:
                self._items.pop(key, None)
            return CacheInfo(self._hits, self._misses, len(self._items))
