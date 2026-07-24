"""
alert_engine.py

Persistent alert generation and alert-centre UI for Project Atlas.

Alerts are created by comparing a newly saved historical scan with the scan
immediately before it. Each scan pair is processed idempotently, so rerunning
the app does not create duplicate alerts.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st

from historical_scans import DATABASE_PATH, initialise_history_database


BUY_LABELS = {"BUY", "STRONG BUY"}
SELL_LABELS = {"SELL", "STRONG SELL", "AVOID"}
NEUTRAL_LABELS = {"HOLD", "WATCH", "NEUTRAL"}

ALERT_CATEGORIES = {
    "Score",
    "Verdict",
    "Volume",
    "RSI",
    "Trend",
}


def _connect(database_path: Path = DATABASE_PATH) -> sqlite3.Connection:
    """Open the Atlas database with foreign-key support."""

    database_path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialise_alert_database(
    database_path: Path = DATABASE_PATH,
) -> None:
    """Create persistent alert tables and indexes."""

    initialise_history_database(database_path)

    with _connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                scan_id INTEGER NOT NULL,
                previous_scan_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                category TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                explanation TEXT,
                priority INTEGER NOT NULL,
                old_value TEXT,
                new_value TEXT,
                score_change REAL,
                is_read INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (scan_id)
                    REFERENCES scans(scan_id)
                    ON DELETE CASCADE,
                FOREIGN KEY (previous_scan_id)
                    REFERENCES scans(scan_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_created_at
                ON alerts(created_at);

            CREATE INDEX IF NOT EXISTS idx_alerts_scan_id
                ON alerts(scan_id);

            CREATE INDEX IF NOT EXISTS idx_alerts_ticker
                ON alerts(ticker);

            CREATE INDEX IF NOT EXISTS idx_alerts_category
                ON alerts(category);

            CREATE INDEX IF NOT EXISTS idx_alerts_is_read
                ON alerts(is_read);
            """
        )


def _safe_number(value: Any) -> float | None:
    """Convert a value to float when possible."""

    try:
        if value is None or pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_text(value: Any, default: str = "") -> str:
    """Convert a value to trimmed text safely."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()
    return text or default


def _normalise_label(value: Any) -> str:
    """Normalise a verdict or signal label."""

    return _safe_text(value, "UNKNOWN").upper()


def _first_number(row: dict[str, Any], names: Iterable[str]) -> float | None:
    """Return the first valid numeric value from alternate field names."""

    for name in names:
        if name in row:
            number = _safe_number(row.get(name))
            if number is not None:
                return number
    return None


def _first_text(row: dict[str, Any], names: Iterable[str]) -> str:
    """Return the first non-empty text value from alternate field names."""

    for name in names:
        text = _safe_text(row.get(name))
        if text:
            return text
    return ""


def _load_scan_rows(
    scan_id: int,
    database_path: Path = DATABASE_PATH,
) -> dict[str, dict[str, Any]]:
    """Load one saved scan as a ticker-indexed dictionary."""

    with _connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT
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
            FROM scan_results
            WHERE scan_id = ?
            """,
            (int(scan_id),),
        ).fetchall()

    result: dict[str, dict[str, Any]] = {}

    for database_row in rows:
        try:
            payload = json.loads(database_row["row_json"] or "{}")
        except (TypeError, json.JSONDecodeError):
            payload = {}

        payload.setdefault("Ticker", database_row["ticker"])
        payload.setdefault("Atlas Score", database_row["atlas_score"])
        payload.setdefault("Score", database_row["scanner_score"])
        payload.setdefault("Atlas Grade", database_row["atlas_grade"])
        payload.setdefault("Atlas Verdict", database_row["atlas_verdict"])
        payload.setdefault("Signal", database_row["signal"])
        payload.setdefault("Close", database_row["close_price"])
        payload.setdefault("Strength (%)", database_row["strength_percent"])
        payload.setdefault("RSI", database_row["rsi"])
        payload.setdefault("Relative Volume", database_row["relative_volume"])

        ticker = _safe_text(database_row["ticker"]).upper()
        if ticker:
            result[ticker] = payload

    return result


def _get_scan_pair(
    scan_id: int,
    database_path: Path = DATABASE_PATH,
) -> tuple[int, int] | None:
    """Return the current and immediately previous scan IDs."""

    with _connect(database_path) as connection:
        current = connection.execute(
            "SELECT scan_id, scanned_at FROM scans WHERE scan_id = ?",
            (int(scan_id),),
        ).fetchone()

        if current is None:
            return None

        previous = connection.execute(
            """
            SELECT scan_id
            FROM scans
            WHERE scanned_at < ?
            ORDER BY scanned_at DESC
            LIMIT 1
            """,
            (current["scanned_at"],),
        ).fetchone()

    if previous is None:
        return None

    return int(current["scan_id"]), int(previous["scan_id"])


def _alert_key(
    scan_id: int,
    previous_scan_id: int,
    ticker: str,
    alert_type: str,
) -> str:
    """Build a stable idempotency key for one generated alert."""

    raw_key = f"{scan_id}|{previous_scan_id}|{ticker}|{alert_type}"
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _create_alert(
    *,
    scan_id: int,
    previous_scan_id: int,
    ticker: str,
    category: str,
    alert_type: str,
    title: str,
    message: str,
    explanation: str,
    priority: int,
    old_value: Any = None,
    new_value: Any = None,
    score_change: float | None = None,
) -> dict[str, Any]:
    """Create one normalised alert dictionary."""

    return {
        "alert_key": _alert_key(
            scan_id,
            previous_scan_id,
            ticker,
            alert_type,
        ),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scan_id": scan_id,
        "previous_scan_id": previous_scan_id,
        "ticker": ticker,
        "category": category,
        "alert_type": alert_type,
        "title": title,
        "message": message,
        "explanation": explanation,
        "priority": max(1, min(5, int(priority))),
        "old_value": None if old_value is None else str(old_value),
        "new_value": None if new_value is None else str(new_value),
        "score_change": score_change,
    }


def _score_alerts(
    current: dict[str, Any],
    previous: dict[str, Any],
    scan_id: int,
    previous_scan_id: int,
    ticker: str,
    threshold: float,
) -> list[dict[str, Any]]:
    """Generate meaningful Atlas-score movement alerts."""

    current_score = _first_number(current, ["Atlas Score", "Score"])
    previous_score = _first_number(previous, ["Atlas Score", "Score"])

    if current_score is None or previous_score is None:
        return []

    change = current_score - previous_score

    if abs(change) < threshold:
        return []

    improving = change > 0
    priority = 5 if abs(change) >= 15 else 4 if abs(change) >= 10 else 3
    direction = "increased" if improving else "fell"
    alert_type = "score_increase" if improving else "score_decrease"

    return [
        _create_alert(
            scan_id=scan_id,
            previous_scan_id=previous_scan_id,
            ticker=ticker,
            category="Score",
            alert_type=alert_type,
            title=(
                f"{ticker} Atlas Score "
                f"{'improved' if improving else 'weakened'}"
            ),
            message=(
                f"Atlas Score {direction} from {previous_score:.1f} "
                f"to {current_score:.1f} ({change:+.1f})."
            ),
            explanation=(
                "The latest scan produced a material change in the combined "
                "trend, momentum, volume, and risk assessment."
            ),
            priority=priority,
            old_value=f"{previous_score:.1f}",
            new_value=f"{current_score:.1f}",
            score_change=change,
        )
    ]


def _verdict_alerts(
    current: dict[str, Any],
    previous: dict[str, Any],
    scan_id: int,
    previous_scan_id: int,
    ticker: str,
) -> list[dict[str, Any]]:
    """Generate verdict-upgrade and verdict-downgrade alerts."""

    current_label = _normalise_label(
        _first_text(current, ["Atlas Verdict", "Signal"])
    )
    previous_label = _normalise_label(
        _first_text(previous, ["Atlas Verdict", "Signal"])
    )

    if current_label == previous_label:
        return []

    alerts: list[dict[str, Any]] = []

    if current_label == "STRONG BUY" and previous_label != "STRONG BUY":
        alerts.append(
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="Verdict",
                alert_type="entered_strong_buy",
                title=f"{ticker} entered Strong Buy",
                message=f"Verdict changed from {previous_label} to STRONG BUY.",
                explanation=(
                    "Atlas now sees a high-quality combination of technical "
                    "conditions. Review the underlying evidence and risk plan."
                ),
                priority=5,
                old_value=previous_label,
                new_value=current_label,
            )
        )
    elif previous_label in BUY_LABELS and current_label not in BUY_LABELS:
        alerts.append(
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="Verdict",
                alert_type="lost_buy_rating",
                title=f"{ticker} lost its Buy rating",
                message=f"Verdict changed from {previous_label} to {current_label}.",
                explanation=(
                    "One or more supporting technical conditions weakened "
                    "enough to remove the previous Buy classification."
                ),
                priority=5,
                old_value=previous_label,
                new_value=current_label,
            )
        )
    elif current_label in BUY_LABELS and previous_label not in BUY_LABELS:
        alerts.append(
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="Verdict",
                alert_type="entered_buy_rating",
                title=f"{ticker} entered a Buy rating",
                message=f"Verdict changed from {previous_label} to {current_label}.",
                explanation=(
                    "The latest scan improved sufficiently to satisfy Atlas's "
                    "Buy-side decision criteria."
                ),
                priority=4,
                old_value=previous_label,
                new_value=current_label,
            )
        )
    elif current_label in SELL_LABELS and previous_label not in SELL_LABELS:
        alerts.append(
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="Verdict",
                alert_type="entered_sell_rating",
                title=f"{ticker} entered a risk-off rating",
                message=f"Verdict changed from {previous_label} to {current_label}.",
                explanation=(
                    "The technical picture deteriorated enough for Atlas to "
                    "classify the setup as Sell or Avoid."
                ),
                priority=5,
                old_value=previous_label,
                new_value=current_label,
            )
        )
    else:
        alerts.append(
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="Verdict",
                alert_type="verdict_changed",
                title=f"{ticker} verdict changed",
                message=f"Verdict changed from {previous_label} to {current_label}.",
                explanation=(
                    "The latest scan changed the overall Atlas classification."
                ),
                priority=3,
                old_value=previous_label,
                new_value=current_label,
            )
        )

    return alerts


def _volume_alerts(
    current: dict[str, Any],
    previous: dict[str, Any],
    scan_id: int,
    previous_scan_id: int,
    ticker: str,
) -> list[dict[str, Any]]:
    """Generate relative-volume spike alerts."""

    current_volume = _first_number(
        current,
        ["Relative Volume", "Volume Ratio", "relative_volume"],
    )
    previous_volume = _first_number(
        previous,
        ["Relative Volume", "Volume Ratio", "relative_volume"],
    )

    if current_volume is None or previous_volume is None:
        return []

    entered_spike = current_volume >= 1.5 and previous_volume < 1.5
    material_jump = (
        current_volume >= 1.5
        and current_volume - previous_volume >= 0.5
    )

    if not (entered_spike or material_jump):
        return []

    priority = 4 if current_volume >= 2.0 else 3

    return [
        _create_alert(
            scan_id=scan_id,
            previous_scan_id=previous_scan_id,
            ticker=ticker,
            category="Volume",
            alert_type="volume_spike",
            title=f"{ticker} volume spike",
            message=(
                f"Relative volume moved from {previous_volume:.2f}x "
                f"to {current_volume:.2f}x average."
            ),
            explanation=(
                "Above-normal participation can strengthen a technical move, "
                "but direction and price structure still need confirmation."
            ),
            priority=priority,
            old_value=f"{previous_volume:.2f}x",
            new_value=f"{current_volume:.2f}x",
        )
    ]


def _rsi_alerts(
    current: dict[str, Any],
    previous: dict[str, Any],
    scan_id: int,
    previous_scan_id: int,
    ticker: str,
) -> list[dict[str, Any]]:
    """Generate RSI threshold-crossing alerts."""

    current_rsi = _first_number(current, ["RSI", "rsi"])
    previous_rsi = _first_number(previous, ["RSI", "rsi"])

    if current_rsi is None or previous_rsi is None:
        return []

    if current_rsi >= 70 and previous_rsi < 70:
        return [
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="RSI",
                alert_type="entered_overbought",
                title=f"{ticker} entered overbought RSI",
                message=f"RSI moved from {previous_rsi:.1f} to {current_rsi:.1f}.",
                explanation=(
                    "Momentum is strong, but the probability of short-term "
                    "consolidation or a pullback may be higher."
                ),
                priority=4 if current_rsi >= 75 else 3,
                old_value=f"{previous_rsi:.1f}",
                new_value=f"{current_rsi:.1f}",
            )
        ]

    if current_rsi <= 30 and previous_rsi > 30:
        return [
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="RSI",
                alert_type="entered_oversold",
                title=f"{ticker} entered oversold RSI",
                message=f"RSI moved from {previous_rsi:.1f} to {current_rsi:.1f}.",
                explanation=(
                    "Selling pressure is elevated. This may signal continued "
                    "weakness or an early rebound area requiring confirmation."
                ),
                priority=4 if current_rsi <= 25 else 3,
                old_value=f"{previous_rsi:.1f}",
                new_value=f"{current_rsi:.1f}",
            )
        ]

    return []


def _trend_alerts(
    current: dict[str, Any],
    previous: dict[str, Any],
    scan_id: int,
    previous_scan_id: int,
    ticker: str,
) -> list[dict[str, Any]]:
    """Generate price-versus-moving-average crossing alerts."""

    current_price = _first_number(
        current,
        ["Close", "Current Price", "price"],
    )
    previous_price = _first_number(
        previous,
        ["Close", "Current Price", "price"],
    )

    if current_price is None or previous_price is None:
        return []

    average_aliases = [
        ("20-day MA", ["20-Day MA", "MA20", "20 Day MA", "ma20"]),
        ("50-day MA", ["50-Day MA", "MA50", "50 Day MA", "ma50"]),
    ]

    alerts: list[dict[str, Any]] = []

    for average_name, aliases in average_aliases:
        current_average = _first_number(current, aliases)
        previous_average = _first_number(previous, aliases)

        if current_average is None or previous_average is None:
            continue

        crossed_above = (
            previous_price <= previous_average
            and current_price > current_average
        )
        crossed_below = (
            previous_price >= previous_average
            and current_price < current_average
        )

        if not crossed_above and not crossed_below:
            continue

        direction = "above" if crossed_above else "below"
        alert_type = (
            f"crossed_above_{average_name.split('-')[0]}"
            if crossed_above
            else f"crossed_below_{average_name.split('-')[0]}"
        )

        alerts.append(
            _create_alert(
                scan_id=scan_id,
                previous_scan_id=previous_scan_id,
                ticker=ticker,
                category="Trend",
                alert_type=alert_type,
                title=f"{ticker} crossed {direction} its {average_name}",
                message=(
                    f"Price is now {current_price:.2f} versus the "
                    f"{average_name} at {current_average:.2f}."
                ),
                explanation=(
                    "A moving-average cross can indicate a change in trend "
                    "structure. Confirm it with volume, momentum, and the "
                    "broader Atlas score."
                ),
                priority=4 if "50" in average_name else 3,
                old_value=(
                    f"Price {previous_price:.2f} / MA {previous_average:.2f}"
                ),
                new_value=(
                    f"Price {current_price:.2f} / MA {current_average:.2f}"
                ),
            )
        )

    return alerts


def generate_alerts_for_scan(
    scan_id: int,
    *,
    score_change_threshold: float = 7.0,
    database_path: Path = DATABASE_PATH,
) -> list[dict[str, Any]]:
    """Compare a scan with its predecessor and return structured alerts."""

    initialise_alert_database(database_path)

    pair = _get_scan_pair(scan_id, database_path)

    if pair is None:
        return []

    current_scan_id, previous_scan_id = pair
    current_rows = _load_scan_rows(current_scan_id, database_path)
    previous_rows = _load_scan_rows(previous_scan_id, database_path)

    alerts: list[dict[str, Any]] = []

    for ticker in sorted(set(current_rows).intersection(previous_rows)):
        current = current_rows[ticker]
        previous = previous_rows[ticker]

        alerts.extend(
            _score_alerts(
                current,
                previous,
                current_scan_id,
                previous_scan_id,
                ticker,
                score_change_threshold,
            )
        )
        alerts.extend(
            _verdict_alerts(
                current,
                previous,
                current_scan_id,
                previous_scan_id,
                ticker,
            )
        )
        alerts.extend(
            _volume_alerts(
                current,
                previous,
                current_scan_id,
                previous_scan_id,
                ticker,
            )
        )
        alerts.extend(
            _rsi_alerts(
                current,
                previous,
                current_scan_id,
                previous_scan_id,
                ticker,
            )
        )
        alerts.extend(
            _trend_alerts(
                current,
                previous,
                current_scan_id,
                previous_scan_id,
                ticker,
            )
        )

    return alerts


def store_alerts(
    alerts: list[dict[str, Any]],
    database_path: Path = DATABASE_PATH,
) -> int:
    """Persist generated alerts and return the number newly inserted."""

    if not alerts:
        return 0

    initialise_alert_database(database_path)

    inserted = 0

    with _connect(database_path) as connection:
        for alert in alerts:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO alerts (
                    alert_key,
                    created_at,
                    scan_id,
                    previous_scan_id,
                    ticker,
                    category,
                    alert_type,
                    title,
                    message,
                    explanation,
                    priority,
                    old_value,
                    new_value,
                    score_change
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert["alert_key"],
                    alert["created_at"],
                    alert["scan_id"],
                    alert["previous_scan_id"],
                    alert["ticker"],
                    alert["category"],
                    alert["alert_type"],
                    alert["title"],
                    alert["message"],
                    alert["explanation"],
                    alert["priority"],
                    alert["old_value"],
                    alert["new_value"],
                    alert["score_change"],
                ),
            )
            inserted += int(cursor.rowcount > 0)

    return inserted


def generate_and_store_alerts(
    scan_id: int,
    *,
    score_change_threshold: float = 7.0,
    database_path: Path = DATABASE_PATH,
) -> int:
    """Generate and persist alerts for a newly saved scan."""

    alerts = generate_alerts_for_scan(
        scan_id,
        score_change_threshold=score_change_threshold,
        database_path=database_path,
    )
    return store_alerts(alerts, database_path)


def get_alerts(
    *,
    limit: int = 500,
    category: str | None = None,
    minimum_priority: int = 1,
    ticker: str | None = None,
    unread_only: bool = False,
    database_path: Path = DATABASE_PATH,
) -> pd.DataFrame:
    """Return saved alerts using optional filters."""

    initialise_alert_database(database_path)

    clauses = ["priority >= ?"]
    params: list[Any] = [max(1, min(5, int(minimum_priority)))]

    if category and category != "All":
        clauses.append("category = ?")
        params.append(category)

    if ticker:
        clauses.append("UPPER(ticker) LIKE UPPER(?)")
        params.append(f"%{ticker.strip()}%")

    if unread_only:
        clauses.append("is_read = 0")

    params.append(int(limit))

    with _connect(database_path) as connection:
        return pd.read_sql_query(
            f"""
            SELECT
                alert_id,
                created_at,
                scan_id,
                previous_scan_id,
                ticker,
                category,
                alert_type,
                title,
                message,
                explanation,
                priority,
                old_value,
                new_value,
                score_change,
                is_read
            FROM alerts
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC, priority DESC
            LIMIT ?
            """,
            connection,
            params=params,
            parse_dates=["created_at"],
        )


def mark_alerts_read(
    alert_ids: list[int] | None = None,
    database_path: Path = DATABASE_PATH,
) -> int:
    """Mark selected alerts, or every alert, as read."""

    initialise_alert_database(database_path)

    with _connect(database_path) as connection:
        if alert_ids:
            placeholders = ",".join("?" for _ in alert_ids)
            cursor = connection.execute(
                f"""
                UPDATE alerts
                SET is_read = 1
                WHERE alert_id IN ({placeholders})
                """,
                [int(alert_id) for alert_id in alert_ids],
            )
        else:
            cursor = connection.execute(
                "UPDATE alerts SET is_read = 1 WHERE is_read = 0"
            )

    return int(cursor.rowcount)


def clear_alert_history(
    database_path: Path = DATABASE_PATH,
) -> int:
    """Delete all persistent alerts while preserving scan history."""

    initialise_alert_database(database_path)

    with _connect(database_path) as connection:
        cursor = connection.execute("DELETE FROM alerts")

    return int(cursor.rowcount)


def _priority_stars(priority: int) -> str:
    """Render a five-star priority label."""

    priority = max(1, min(5, int(priority)))
    return "★" * priority + "☆" * (5 - priority)


def _alert_icon(category: str, alert_type: str) -> str:
    """Choose a compact visual icon for an alert."""

    if alert_type in {
        "entered_strong_buy",
        "entered_buy_rating",
        "score_increase",
    }:
        return "🟢"
    if alert_type in {
        "lost_buy_rating",
        "entered_sell_rating",
        "score_decrease",
        "entered_overbought",
    }:
        return "🔴"
    if category == "Volume":
        return "📊"
    if category == "RSI":
        return "🔥"
    if category == "Trend":
        return "📈"
    return "🔔"


def display_alert_center(
    database_path: Path = DATABASE_PATH,
) -> None:
    """Display the complete Atlas persistent alert centre."""

    initialise_alert_database(database_path)

    st.header("🔔 Atlas Alert Centre")
    st.caption(
        "Alerts compare each fresh scan with the scan immediately before it. "
        "They highlight material changes rather than predicting future prices."
    )

    all_alerts = get_alerts(limit=5000, database_path=database_path)

    if all_alerts.empty:
        st.info(
            "No alerts are stored yet. Atlas needs at least two fresh scans "
            "before it can compare changes and generate alerts."
        )
        return

    unread_count = int((all_alerts["is_read"] == 0).sum())
    critical_count = int((all_alerts["priority"] >= 5).sum())
    latest_scan_count = int(
        (all_alerts["scan_id"] == all_alerts["scan_id"].max()).sum()
    )
    unique_tickers = int(all_alerts["ticker"].nunique())

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Unread Alerts", unread_count)
    metric2.metric("Latest Scan Alerts", latest_scan_count)
    metric3.metric("Critical Alerts", critical_count)
    metric4.metric("Tickers Tracked", unique_tickers)

    filter1, filter2, filter3, filter4 = st.columns([1.2, 1.2, 1.4, 1])

    with filter1:
        category = st.selectbox(
            "Category",
            ["All"] + sorted(ALERT_CATEGORIES),
            key="alert_category_filter",
        )

    with filter2:
        minimum_priority = st.select_slider(
            "Minimum priority",
            options=[1, 2, 3, 4, 5],
            value=2,
            format_func=lambda value: _priority_stars(value),
            key="alert_priority_filter",
        )

    with filter3:
        ticker_search = st.text_input(
            "Ticker search",
            placeholder="e.g. NVDA",
            key="alert_ticker_search",
        )

    with filter4:
        unread_only = st.toggle(
            "Unread only",
            value=False,
            key="alert_unread_only",
        )

    filtered = get_alerts(
        limit=1000,
        category=category,
        minimum_priority=minimum_priority,
        ticker=ticker_search or None,
        unread_only=unread_only,
        database_path=database_path,
    )

    action1, action2 = st.columns([1, 1])

    with action1:
        if st.button(
            "Mark All Alerts Read",
            width="stretch",
            disabled=unread_count == 0,
        ):
            updated = mark_alerts_read(database_path=database_path)
            st.success(f"Marked {updated} alerts as read.")
            st.rerun()

    with action2:
        with st.popover("Alert History Settings", use_container_width=True):
            st.warning(
                "Clearing alerts cannot be undone. Historical market scans "
                "will not be deleted."
            )
            if st.button(
                "Clear All Alert History",
                type="secondary",
                width="stretch",
            ):
                deleted = clear_alert_history(database_path)
                st.success(f"Deleted {deleted} alerts.")
                st.rerun()

    st.divider()

    if filtered.empty:
        st.info("No alerts match the selected filters.")
        return

    st.subheader(f"Alert Feed ({len(filtered)})")

    for row in filtered.itertuples(index=False):
        icon = _alert_icon(row.category, row.alert_type)
        read_marker = "" if int(row.is_read) else " • NEW"
        timestamp = pd.Timestamp(row.created_at)

        with st.container(border=True):
            top_left, top_right = st.columns([4, 1])

            with top_left:
                st.markdown(
                    f"### {icon} {row.title}{read_marker}"
                )
                st.caption(
                    f"{_priority_stars(row.priority)} · {row.category} · "
                    f"{timestamp.strftime('%d %b %Y, %H:%M UTC')}"
                )

            with top_right:
                st.metric(
                    "Priority",
                    f"{int(row.priority)}/5",
                )

            st.write(row.message)

            if row.explanation:
                st.info(f"**Why Atlas flagged it:** {row.explanation}")

            detail_columns = st.columns(3)

            with detail_columns[0]:
                st.caption(f"Ticker: **{row.ticker}**")

            with detail_columns[1]:
                if row.old_value is not None:
                    st.caption(f"Previous: **{row.old_value}**")

            with detail_columns[2]:
                if row.new_value is not None:
                    st.caption(f"Current: **{row.new_value}**")

            if not int(row.is_read):
                if st.button(
                    "Mark Read",
                    key=f"mark_alert_read_{int(row.alert_id)}",
                ):
                    mark_alerts_read(
                        [int(row.alert_id)],
                        database_path,
                    )
                    st.rerun()

    with st.expander("View alerts as a table"):
        table = filtered[
            [
                "created_at",
                "ticker",
                "category",
                "title",
                "priority",
                "old_value",
                "new_value",
                "score_change",
                "is_read",
            ]
        ].copy()

        table["is_read"] = table["is_read"].map(
            {0: "Unread", 1: "Read"}
        )

        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={
                "created_at": "Created",
                "ticker": "Ticker",
                "category": "Category",
                "title": "Alert",
                "priority": st.column_config.NumberColumn(
                    "Priority",
                    min_value=1,
                    max_value=5,
                    format="%d",
                ),
                "old_value": "Previous",
                "new_value": "Current",
                "score_change": st.column_config.NumberColumn(
                    "Score Change",
                    format="%+.1f",
                ),
                "is_read": "Status",
            },
        )

    st.caption(
        "Atlas alerts are technical decision-support signals, not financial "
        "advice or guarantees of future performance."
    )
