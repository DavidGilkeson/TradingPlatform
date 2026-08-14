"""Regime-aware forward validation insights for Atlas."""

from __future__ import annotations
import pandas as pd

from .cohort_validation import (
    market_regime_validation,
    volatility_regime_validation,
)


def _ready(table: pd.DataFrame) -> pd.DataFrame:
    if table is None or table.empty or "Evidence Ready" not in table:
        return pd.DataFrame()
    ready=table[table["Evidence Ready"]==True].copy()
    if ready.empty:
        return ready
    ready["Avg Excess Return"]=pd.to_numeric(
        ready["Avg Excess Return"],errors="coerce")
    ready["Average Return"]=pd.to_numeric(
        ready["Average Return"],errors="coerce")
    return ready


def regime_leaders(frame, minimum_observations=5):
    """Return strongest/weakest evidence-ready market and volatility regimes."""
    results={}
    for label,dimension,table in (
        ("market","market_regime",
         market_regime_validation(frame,minimum_observations)),
        ("volatility","volatility_regime",
         volatility_regime_validation(frame,minimum_observations)),
    ):
        ready=_ready(table).dropna(subset=["Avg Excess Return"])
        if ready.empty:
            results[label]={"best":None,"worst":None}
            continue
        ordered=ready.sort_values(
            ["Avg Excess Return","Observations"],
            ascending=[False,False],
        )
        def pack(row):
            return {
                "regime":str(row[dimension]),
                "horizon_days":int(row["Horizon Days"]),
                "observations":int(row["Observations"]),
                "average_return":float(row["Average Return"]),
                "avg_excess_return":float(row["Avg Excess Return"]),
                "positive_rate":float(row["Positive Rate"]),
                "beat_benchmark_rate":(
                    None if pd.isna(row["Beat Benchmark Rate"])
                    else float(row["Beat Benchmark Rate"])
                ),
            }
        results[label]={
            "best":pack(ordered.iloc[0]),
            "worst":pack(ordered.iloc[-1]),
        }
    return results


def regime_warning(
    frame,
    *,
    market_regime=None,
    volatility_regime=None,
    horizon_days=None,
    minimum_observations=5,
):
    """Describe how the requested current regime has performed prospectively."""
    messages=[]
    for dimension,value,label in (
        ("market_regime",market_regime,"market"),
        ("volatility_regime",volatility_regime,"volatility"),
    ):
        if not value:
            continue
        table=(
            market_regime_validation(frame,minimum_observations)
            if dimension=="market_regime"
            else volatility_regime_validation(frame,minimum_observations)
        )
        if table.empty:
            messages.append({
                "level":"insufficient","dimension":label,"regime":value,
                "message":f"No resolved forward-test evidence for {value} {label} regime yet."
            })
            continue
        rows=table[table[dimension].astype(str)==str(value)]
        if horizon_days is not None:
            rows=rows[rows["Horizon Days"]==int(horizon_days)]
        if rows.empty or not bool(rows["Evidence Ready"].any()):
            messages.append({
                "level":"insufficient","dimension":label,"regime":value,
                "message":f"{value} {label} regime does not yet have enough resolved observations."
            })
            continue
        row=rows[rows["Evidence Ready"]==True].sort_values(
            "Observations",ascending=False).iloc[0]
        excess=row["Avg Excess Return"]
        if pd.isna(excess):
            level="neutral"
            message=f"{value} {label} regime has evidence, but benchmark comparison is unavailable."
        elif float(excess)>0:
            level="favourable"
            message=(
                f"{value} {label} regime has averaged {float(excess):+.2f}% "
                f"excess return across {int(row['Observations'])} resolved "
                f"{int(row['Horizon Days'])}-day observations."
            )
        elif float(excess)<0:
            level="caution"
            message=(
                f"{value} {label} regime has averaged {float(excess):+.2f}% "
                f"excess return across {int(row['Observations'])} resolved "
                f"{int(row['Horizon Days'])}-day observations."
            )
        else:
            level="neutral"
            message=f"{value} {label} regime has shown no average benchmark edge yet."
        messages.append({
            "level":level,"dimension":label,"regime":value,"message":message
        })
    return messages


def regime_evidence_matrix(frame, minimum_observations=5):
    """Market × volatility matrix for combinations with resolved evidence."""
    if frame is None or frame.empty:
        return pd.DataFrame()
    required={"market_regime","volatility_regime","horizon_days",
              "return_pct","excess_return_pct"}
    if not required.issubset(frame.columns):
        return pd.DataFrame()

    d=frame.copy()
    d=d.dropna(subset=["market_regime","volatility_regime","return_pct"])
    if d.empty:
        return pd.DataFrame()

    rows=[]
    for (market,vol,horizon),g in d.groupby(
        ["market_regime","volatility_regime","horizon_days"],dropna=False):
        excess=pd.to_numeric(g["excess_return_pct"],errors="coerce").dropna()
        returns=pd.to_numeric(g["return_pct"],errors="coerce").dropna()
        if returns.empty:
            continue
        rows.append({
            "Market Regime":str(market),
            "Volatility Regime":str(vol),
            "Horizon Days":int(horizon),
            "Observations":len(g),
            "Average Return":float(returns.mean()),
            "Positive Rate":float((returns>0).mean()),
            "Avg Excess Return":float(excess.mean()) if not excess.empty else None,
            "Evidence Ready":len(g)>=minimum_observations,
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        ["Horizon Days","Avg Excess Return"],
        ascending=[True,False],
        na_position="last",
    ).reset_index(drop=True)
