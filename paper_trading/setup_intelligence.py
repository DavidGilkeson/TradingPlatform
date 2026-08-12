"""Multi-factor setup intelligence for Atlas paper trading."""

from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from .account import PaperAccountService
from .regime_intelligence import build_regime_trade_frame
from .pattern_confidence import add_sample_quality


@dataclass(slots=True)
class SetupLeader:
    setup: str
    trades: int
    win_rate: float
    expectancy: float
    net_pnl: float
    reliability: int


def _score_band(value) -> str:
    if pd.isna(value):
        return "Score Unknown"
    value = float(value)
    if value >= 90:
        return "Score 90+"
    if value >= 80:
        return "Score 80-89"
    if value >= 70:
        return "Score 70-79"
    if value >= 60:
        return "Score 60-69"
    return "Score <60"


def _confidence_band(value) -> str:
    if pd.isna(value):
        return "Confidence Unknown"
    value = float(value)
    if value >= 9:
        return "Confidence 9-10"
    if value >= 7:
        return "Confidence 7-8"
    if value >= 5:
        return "Confidence 5-6"
    return "Confidence <5"


def build_setup_trade_frame(
    service: PaperAccountService,
    *,
    db_path: str = "data/paper_trading.db",
) -> pd.DataFrame:
    """Create completed-trade rows with reusable setup dimensions."""

    frame = build_regime_trade_frame(service, db_path=db_path)
    if frame is None or frame.empty:
        return pd.DataFrame()

    result = frame.copy()

    for column in ("realised_pnl", "return_pct", "atlas_score", "confidence"):
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    result["Score Band"] = result["atlas_score"].map(_score_band)
    result["Confidence Band"] = result["confidence"].map(_confidence_band)

    result["Trend Regime"] = (
        result["trend_regime"].fillna("Regime Unknown").astype(str)
    )
    result["Volatility Regime"] = (
        result["volatility_regime"]
        .fillna("Volatility Unknown")
        .astype(str)
    )

    result["Verdict"] = (
        result["reason"]
        .fillna("Verdict Unknown")
        .astype(str)
        .str.strip()
        .replace("", "Verdict Unknown")
    )

    return result


def setup_performance(
    service: PaperAccountService,
    *,
    db_path: str = "data/paper_trading.db",
    dimensions: tuple[str, ...] = (
        "Score Band",
        "Confidence Band",
        "Trend Regime",
    ),
    minimum_trades: int = 1,
    minimum_evidence_trades: int = 10,
) -> pd.DataFrame:
    """Aggregate completed trades by a selected multi-factor setup."""

    frame = build_setup_trade_frame(service, db_path=db_path)
    if frame.empty:
        return pd.DataFrame()

    dimensions = tuple(dimensions)
    if not dimensions:
        raise ValueError("At least one setup dimension is required.")

    missing = [column for column in dimensions if column not in frame.columns]
    if missing:
        raise ValueError(f"Unknown setup dimensions: {', '.join(missing)}")

    working = frame.dropna(subset=["realised_pnl"]).copy()

    if working.empty:
        return pd.DataFrame()

    grouped = (
        working.groupby(list(dimensions), as_index=False, dropna=False)
        .agg(
            Trades=("trade_id", "count"),
            Wins=("realised_pnl", lambda s: int((s > 0).sum())),
            Win_Rate=("realised_pnl", lambda s: float((s > 0).mean())),
            Average_Return=("return_pct", "mean"),
            Net_PnL=("realised_pnl", "sum"),
            Expectancy=("realised_pnl", "mean"),
        )
    )

    grouped = grouped[grouped["Trades"] >= int(minimum_trades)].copy()

    if grouped.empty:
        return grouped

    grouped["Setup"] = grouped[list(dimensions)].astype(str).agg(" + ".join, axis=1)

    grouped = add_sample_quality(
        grouped,
        minimum_evidence_trades=int(minimum_evidence_trades),
    )

    return grouped.sort_values(
        ["Insight Ready", "Expectancy", "Trades"],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def evidence_qualified_setup_leader(frame: pd.DataFrame) -> SetupLeader | None:
    """Return the best setup that passes the evidence threshold."""

    if frame is None or frame.empty or "Insight Ready" not in frame.columns:
        return None

    ready = frame[frame["Insight Ready"]].copy()
    if ready.empty:
        return None

    best = ready.sort_values(
        ["Expectancy", "Trades"],
        ascending=[False, False],
    ).iloc[0]

    return SetupLeader(
        setup=str(best["Setup"]),
        trades=int(best["Trades"]),
        win_rate=float(best["Win_Rate"]),
        expectancy=float(best["Expectancy"]),
        net_pnl=float(best["Net_PnL"]),
        reliability=int(best["Reliability"]),
    )
