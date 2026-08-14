"""Bridge the latest Atlas scan into Paper Trading across Streamlit reruns."""

from __future__ import annotations

from typing import Any
import pandas as pd


SESSION_SCAN_KEY = "atlas_latest_market_scan"

# Common keys used by Streamlit apps for scan/result DataFrames. This makes
# Paper Trading tolerant of older app.py versions while the canonical key is
# rolled out.
SESSION_SCAN_CANDIDATES = (
    SESSION_SCAN_KEY,
    "market_df",
    "scan_df",
    "scan_results",
    "latest_scan",
    "latest_scan_df",
    "results_df",
    "df",
)


def is_market_scan_frame(value: Any) -> bool:
    """Return True when value looks like an Atlas market-scan DataFrame."""
    return (
        isinstance(value, pd.DataFrame)
        and not value.empty
        and "Ticker" in value.columns
    )


def publish_scan_to_mapping(
    state: Any,
    market_df: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """Save a fresh scan to a dict/session-state-like mapping."""
    if not is_market_scan_frame(market_df):
        return None

    # Copy so later display filtering does not mutate the canonical scan.
    stored = market_df.copy()
    state[SESSION_SCAN_KEY] = stored
    return stored


def resolve_scan_from_mapping(
    state: Any,
    market_df: pd.DataFrame | None = None,
) -> pd.DataFrame | None:
    """Prefer an explicitly passed scan, then recover one from session state."""
    if is_market_scan_frame(market_df):
        publish_scan_to_mapping(state, market_df)
        return market_df

    # First check known/canonical keys.
    for key in SESSION_SCAN_CANDIDATES:
        try:
            candidate = state.get(key)
        except Exception:
            candidate = None

        if is_market_scan_frame(candidate):
            publish_scan_to_mapping(state, candidate)
            return candidate

    # Last-resort compatibility pass: find any DataFrame in state that has a
    # Ticker column. This avoids depending on a specific old app.py variable.
    try:
        items = list(state.items())
    except Exception:
        items = []

    for _, candidate in items:
        if is_market_scan_frame(candidate):
            publish_scan_to_mapping(state, candidate)
            return candidate

    return None


def publish_scan_to_streamlit(
    market_df: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """Publish scan data into Streamlit session state."""
    import streamlit as st

    return publish_scan_to_mapping(st.session_state, market_df)


def resolve_streamlit_scan(
    market_df: pd.DataFrame | None = None,
) -> pd.DataFrame | None:
    """Resolve the latest scan from explicit input or Streamlit state."""
    import streamlit as st

    return resolve_scan_from_mapping(st.session_state, market_df)
