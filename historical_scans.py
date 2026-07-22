"""
historical_scans.py

SQLite persistence and trend dashboard for Project Atlas market scans.

The database stores each completed fresh scan and its individual stock rows.
It is designed to tolerate new scanner columns by preserving the full row as
JSON while indexing the most useful Atlas metrics separately.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st


DATABASE_PATH = Path("data") / "atlas_history.db"


def _connect(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open the Atlas history database and enable foreign keys."""

    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialise_history_database(
    database_path: Path = DATABASE_PATH,
) -> None:
    """Create the historical scan tables when they do not yet exist."""

    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS scans (
                scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scanned_at TEXT NOT NULL,
                stock_count INTEGER NOT NULL,
                scan_duration_seconds REAL NOT NULL DEFAULT 0,
                average_atlas_score REAL,
                buy_count INTEGER NOT NULL DEFAULT 0,
                hold_count INTEGER NOT NULL DEFAULT 0,
                sell_count INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS scan_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                atlas_score REAL,
                scanner_score REAL,
                atlas_grade TEXT,
                atlas_verdict TEXT,
                signal TEXT,
                close_price REAL,
                strength_percent REAL,
                rsi REAL,
                relative_volume REAL,
                row_json TEXT NOT NULL,
                FOREIGN KEY (scan_id)
                    REFERENCES scans(scan_id)
                    ON DELETE CASCADE,
                UNIQUE (scan_id, ticker)
            );

            CREATE INDEX IF NOT EXISTS idx_scan_results_ticker
                ON scan_results(ticker);

            CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id
                ON scan_results(scan_id);

            CREATE INDEX IF NOT EXISTS idx_scans_scanned_at
                ON scans(scanned_at);
            """
        )


def _safe_number(value: Any) -> float | None:
    """Convert a value to a database-safe float."""

    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_text(value: Any) -> str | None:
    """Convert a value to clean text safely."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    text = str(value).strip()
    return text or None


def _json_safe(value: Any) -> Any:
    """Convert pandas and NumPy values into JSON-safe Python values."""

    if value is None:
        return None

    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if hasattr(value, "item"):
        try:
            return value.item()
        except (ValueError, TypeError):
            pass

    if isinstance(value, (datetime, pd.Timestamp)):
        return value.isoformat()

    return value


def _verdict_counts(df: pd.DataFrame) -> tuple[int, int, int]:
    """Return buy, hold, and sell counts from the best available label."""

    if "Atlas Verdict" in df.columns:
        labels = df["Atlas Verdict"].astype(str).str.upper()
    elif "Signal" in df.columns:
        labels = df["Signal"].astype(str).str.upper()
    else:
        return 0, 0, 0

    buy_count = int(labels.isin(["BUY", "STRONG BUY"]).sum())
    hold_count = int(labels.isin(["HOLD", "WATCH", "NEUTRAL"]).sum())
    sell_count = int(labels.isin(["SELL", "AVOID", "STRONG SELL"]).sum())

    return buy_count, hold_count, sell_count


def save_historical_scan(
    df: pd.DataFrame,
    scan_duration_seconds: float = 0.0,
    scanned_at: datetime | None = None,
    database_path: Path = DATABASE_PATH,
) -> int | None:
    """
    Save one completed market scan.

    Returns the new scan ID, or None when there is no data to save.
    """

    if df is None or df.empty:
        return None

    initialise_history_database(database_path)

    scan_timestamp = scanned_at or datetime.now(timezone.utc)
    scanned_at_text = scan_timestamp.isoformat()

    score_column = (
        "Atlas Score"
        if "Atlas Score" in df.columns
        else "Score"
        if "Score" in df.columns
        else None
    )

    average_score = (
        _safe_number(pd.to_numeric(df[score_column], errors="coerce").mean())
        if score_column
        else None
    )

    buy_count, hold_count, sell_count = _verdict_counts(df)

    with _connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (
                scanned_at,
                stock_count,
                scan_duration_seconds,
                average_atlas_score,
                buy_count,
                hold_count,
                sell_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scanned_at_text,
                int(len(df)),
                float(scan_duration_seconds or 0.0),
                average_score,
                buy_count,
                hold_count,
                sell_count,
            ),
        )

        scan_id = int(cursor.lastrowid)

        rows_to_insert = []

        for _, row in df.iterrows():
            row_payload = {
                str(column): _json_safe(row[column])
                for column in df.columns
            }

            rows_to_insert.append(
                (
                    scan_id,
                    _safe_text(row.get("Ticker")) or "UNKNOWN",
                    _safe_number(row.get("Atlas Score")),
                    _safe_number(row.get("Score")),
                    _safe_text(row.get("Atlas Grade")),
                    _safe_text(row.get("Atlas Verdict")),
                    _safe_text(row.get("Signal")),
                    _safe_number(row.get("Close")),
                    _safe_number(row.get("Strength (%)")),
                    _safe_number(row.get("RSI")),
                    _safe_number(row.get("Relative Volume")),
                    json.dumps(row_payload, ensure_ascii=False),
                )
            )

        connection.executemany(
            """
            INSERT INTO scan_results (
                scan_id,
                ticker,
                atlas_score,
                scanner_score,
                atlas_grade,
                atlas_verdict,
                signal,
                close_price,
                strength_percent,
                rsi,
                relative_volume,
                row_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows_to_insert,
        )

    return scan_id


def get_scan_history(
    limit: int = 100,
    database_path: Path = DATABASE_PATH,
) -> pd.DataFrame:
    """Return recent scan summaries, newest first."""

    initialise_history_database(database_path)

    with _connect(database_path) as connection:
        return pd.read_sql_query(
            """
            SELECT
                scan_id,
                scanned_at,
                stock_count,
                scan_duration_seconds,
                average_atlas_score,
                buy_count,
                hold_count,
                sell_count
            FROM scans
            ORDER BY scanned_at DESC
            LIMIT ?
            """,
            connection,
            params=(int(limit),),
            parse_dates=["scanned_at"],
        )


def get_ticker_history(
    ticker: str,
    limit: int = 100,
    database_path: Path = DATABASE_PATH,
) -> pd.DataFrame:
    """Return historical Atlas readings for one ticker."""

    initialise_history_database(database_path)

    with _connect(database_path) as connection:
        return pd.read_sql_query(
            """
            SELECT
                s.scanned_at,
                r.ticker,
                r.atlas_score,
                r.scanner_score,
                r.atlas_grade,
                r.atlas_verdict,
                r.signal,
                r.close_price,
                r.strength_percent,
                r.rsi,
                r.relative_volume
            FROM scan_results AS r
            INNER JOIN scans AS s
                ON s.scan_id = r.scan_id
            WHERE UPPER(r.ticker) = UPPER(?)
            ORDER BY s.scanned_at DESC
            LIMIT ?
            """,
            connection,
            params=(ticker.strip(), int(limit)),
            parse_dates=["scanned_at"],
        )


def get_latest_scan_comparison(
    database_path: Path = DATABASE_PATH,
) -> pd.DataFrame:
    """Compare Atlas scores in the two most recent saved scans."""

    history = get_scan_history(limit=2, database_path=database_path)

    if len(history) < 2:
        return pd.DataFrame()

    latest_scan_id = int(history.iloc[0]["scan_id"])
    previous_scan_id = int(history.iloc[1]["scan_id"])

    with _connect(database_path) as connection:
        comparison = pd.read_sql_query(
            """
            SELECT
                latest.ticker,
                latest.atlas_score AS latest_score,
                previous.atlas_score AS previous_score,
                latest.atlas_verdict AS latest_verdict,
                latest.atlas_grade AS latest_grade,
                latest.close_price AS latest_close,
                latest.atlas_score - previous.atlas_score AS score_change
            FROM scan_results AS latest
            INNER JOIN scan_results AS previous
                ON previous.ticker = latest.ticker
            WHERE latest.scan_id = ?
              AND previous.scan_id = ?
              AND latest.atlas_score IS NOT NULL
              AND previous.atlas_score IS NOT NULL
            ORDER BY score_change DESC
            """,
            connection,
            params=(latest_scan_id, previous_scan_id),
        )

    return comparison


def delete_scan(
    scan_id: int,
    database_path: Path = DATABASE_PATH,
) -> bool:
    """Delete one historical scan and all of its rows."""

    initialise_history_database(database_path)

    with _connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM scans WHERE scan_id = ?",
            (int(scan_id),),
        )

    return cursor.rowcount > 0


def display_historical_trends(
    current_df: pd.DataFrame | None = None,
    database_path: Path = DATABASE_PATH,
) -> None:
    """Display the Atlas historical trends dashboard."""

    initialise_history_database(database_path)

    st.header("🕒 Atlas Trends")
    st.caption(
        "Track how Atlas scores, market health, and individual stocks change "
        "across saved market scans."
    )

    history = get_scan_history(limit=250, database_path=database_path)

    if history.empty:
        st.info(
            "No historical scans are stored yet. Complete a fresh market scan "
            "to create the first database snapshot."
        )
        return

    latest = history.iloc[0]

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Saved Scans", len(history))
    metric2.metric("Latest Stock Count", int(latest["stock_count"]))
    metric3.metric(
        "Latest Average Score",
        f"{float(latest['average_atlas_score'] or 0):.1f}",
    )
    metric4.metric(
        "Latest Buy Signals",
        int(latest["buy_count"]),
    )

    chronological = history.sort_values("scanned_at").copy()
    chronological = chronological.set_index("scanned_at")

    st.subheader("Market Opportunity History")

    chart_columns = [
        column
        for column in [
            "average_atlas_score",
            "buy_count",
            "hold_count",
            "sell_count",
        ]
        if column in chronological.columns
    ]

    st.line_chart(
        chronological[chart_columns],
        width="stretch",
    )

    st.divider()
    st.subheader("Biggest Score Movers")

    comparison = get_latest_scan_comparison(database_path)

    if comparison.empty:
        st.info(
            "At least two fresh scans are required before Atlas can calculate "
            "score improvements and declines."
        )
    else:
        improving = comparison.nlargest(10, "score_change")
        weakening = comparison.nsmallest(10, "score_change")

        left, right = st.columns(2)

        with left:
            st.markdown("#### 📈 Improving")

            st.dataframe(
                improving[
                    [
                        "ticker",
                        "latest_score",
                        "previous_score",
                        "score_change",
                        "latest_verdict",
                    ]
                ],
                width="stretch",
                hide_index=True,
                column_config={
                    "ticker": "Ticker",
                    "latest_score": "Latest",
                    "previous_score": "Previous",
                    "score_change": st.column_config.NumberColumn(
                        "Change",
                        format="%+.1f",
                    ),
                    "latest_verdict": "Verdict",
                },
            )

        with right:
            st.markdown("#### 📉 Weakening")

            st.dataframe(
                weakening[
                    [
                        "ticker",
                        "latest_score",
                        "previous_score",
                        "score_change",
                        "latest_verdict",
                    ]
                ],
                width="stretch",
                hide_index=True,
                column_config={
                    "ticker": "Ticker",
                    "latest_score": "Latest",
                    "previous_score": "Previous",
                    "score_change": st.column_config.NumberColumn(
                        "Change",
                        format="%+.1f",
                    ),
                    "latest_verdict": "Verdict",
                },
            )

    st.divider()
    st.subheader("Ticker Score History")

    ticker_options: list[str] = []

    if current_df is not None and not current_df.empty and "Ticker" in current_df:
        ticker_options = sorted(
            current_df["Ticker"].dropna().astype(str).unique().tolist()
        )

    if not ticker_options:
        comparison = get_latest_scan_comparison(database_path)
        if not comparison.empty:
            ticker_options = sorted(comparison["ticker"].astype(str).tolist())

    selected_ticker = st.selectbox(
        "Select a ticker",
        options=ticker_options or [""],
        index=0,
        key="historical_ticker",
    )

    if selected_ticker:
        ticker_history = get_ticker_history(
            selected_ticker,
            limit=250,
            database_path=database_path,
        )

        if ticker_history.empty:
            st.info(f"No saved history is available for {selected_ticker}.")
        else:
            ticker_history = ticker_history.sort_values("scanned_at")
            ticker_history = ticker_history.set_index("scanned_at")

            score_series = ticker_history[
                [
                    column
                    for column in ["atlas_score", "scanner_score"]
                    if column in ticker_history.columns
                ]
            ]

            st.line_chart(score_series, width="stretch")

            latest_ticker = ticker_history.iloc[-1]

            ticker_metric1, ticker_metric2, ticker_metric3 = st.columns(3)
            ticker_metric1.metric(
                "Latest Atlas Score",
                f"{float(latest_ticker['atlas_score'] or 0):.1f}",
            )
            ticker_metric2.metric(
                "Latest Close",
                (
                    f"${float(latest_ticker['close_price']):,.2f}"
                    if pd.notna(latest_ticker["close_price"])
                    else "—"
                ),
            )
            ticker_metric3.metric(
                "Latest Verdict",
                str(latest_ticker["atlas_verdict"] or "—"),
            )

            with st.expander("View saved ticker readings"):
                st.dataframe(
                    ticker_history.reset_index().sort_values(
                        "scanned_at",
                        ascending=False,
                    ),
                    width="stretch",
                    hide_index=True,
                )

    with st.expander("Manage historical scans"):
        st.dataframe(
            history,
            width="stretch",
            hide_index=True,
        )

        scan_to_delete = st.selectbox(
            "Select a scan to delete",
            options=history["scan_id"].astype(int).tolist(),
            format_func=lambda scan_id: (
                f"Scan {scan_id} — "
                f"{history.loc[history['scan_id'] == scan_id, 'scanned_at'].iloc[0]}"
            ),
            key="delete_historical_scan",
        )

        if st.button(
            "Delete Selected Historical Scan",
            type="secondary",
            width="stretch",
        ):
            if delete_scan(scan_to_delete, database_path):
                st.success("Historical scan deleted.")
                st.rerun()
            else:
                st.error("The historical scan could not be deleted.")
