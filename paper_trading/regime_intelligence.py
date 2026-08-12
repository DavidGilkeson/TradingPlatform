"""Join completed trade history with saved entry-time market regimes."""

from __future__ import annotations

import pandas as pd

from .account import PaperAccountService
from .journal_analytics import build_trade_journal_frame
from .market_regime import regime_performance
from .pattern_confidence import add_sample_quality
from .regime_repository import TradeRegimeRepository


def build_regime_trade_frame(
    service: PaperAccountService,
    *,
    db_path: str = "data/paper_trading.db",
) -> pd.DataFrame:
    trades = build_trade_journal_frame(service)
    if trades is None or trades.empty:
        return pd.DataFrame()

    result = trades.copy()
    ids = [int(value) for value in result["trade_id"].tolist()]
    records = TradeRegimeRepository(db_path).all_for_trade_ids(ids)

    result["market_regime"] = result["trade_id"].map(
        lambda value: (
            records[int(value)].market_regime
            if int(value) in records else None
        )
    )
    result["trend_regime"] = result["trade_id"].map(
        lambda value: (
            records[int(value)].trend_regime
            if int(value) in records else None
        )
    )
    result["volatility_regime"] = result["trade_id"].map(
        lambda value: (
            records[int(value)].volatility_regime
            if int(value) in records else None
        )
    )
    return result


def market_regime_intelligence(
    service: PaperAccountService,
    *,
    db_path: str = "data/paper_trading.db",
    minimum_trades: int = 1,
    minimum_evidence_trades: int = 10,
) -> pd.DataFrame:
    trades = build_regime_trade_frame(service, db_path=db_path)
    performance = regime_performance(
        trades,
        minimum_trades=minimum_trades,
    )
    return add_sample_quality(
        performance,
        minimum_evidence_trades=minimum_evidence_trades,
    )
