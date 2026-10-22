# Sprint 35.2 — Performance & Caching Optimisation

## Changes
- Added a bounded, thread-safe TTL cache with expiry, LRU eviction, hit/miss metrics, and explicit invalidation.
- Added defensive copies for mutable cached values and pandas DataFrames/Series.
- Cached successful live ticker-price lookups for 60 seconds to avoid repeated market-data requests on Streamlit reruns.
- Failed/empty live-price lookups are not cached, allowing transient failures to recover on the next request.
- Added `clear_price_cache(ticker=None)` to invalidate one symbol or all cached prices after an explicit refresh.

## Safety notes
- Cache TTL is short and explicit; it is not intended as a substitute for a live quote feed.
- Failed market data is never replaced with a synthetic price.
- Price cache can be explicitly invalidated. This sprint does not cache order placement, account balances, or mutable trading state.

## Validation
Run `python -m pytest -q` from the project root.
