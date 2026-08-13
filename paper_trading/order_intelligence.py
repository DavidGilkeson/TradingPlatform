"""Build pre-trade intelligence from the current Atlas scanner context."""

from __future__ import annotations
from typing import Any
import pandas as pd
from .market_regime import classify_market_regime

def _first_numeric(context:dict[str,Any], names:tuple[str,...])->float|None:
    for name in names:
        if name in context:
            try:
                value=float(context[name])
                if pd.notna(value): return value
            except (TypeError,ValueError):
                pass
    return None

def derive_regime_from_context(context:dict[str,Any]):
    close=_first_numeric(context,("Close","Current Price","Price","Latest Price"))
    short=_first_numeric(context,("20-Day MA","MA Short","Short MA"))
    long=_first_numeric(context,("50-Day MA","MA Long","Long MA"))
    volatility=_first_numeric(context,("Volatility (%)","Volatility","ATR (%)"))
    if close is None or short is None or long is None:
        return None
    try:
        return classify_market_regime(
            close=close,ma_short=short,ma_long=long,volatility_pct=volatility)
    except ValueError:
        return None
