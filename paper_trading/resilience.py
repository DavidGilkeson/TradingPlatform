"""Atlas runtime resilience helpers.

Small, dependency-light helpers for turning expected operational failures into
clear user-facing states without hiding programming errors.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Callable, Generic, Optional, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RecoveryResult(Generic[T]):
    ok: bool
    value: Optional[T] = None
    message: str = ""
    recovery: str = ""
    error_type: str = ""


def friendly_error(exc: BaseException, *, context: str = "Atlas") -> RecoveryResult[None]:
    """Translate known operational failures into safe, actionable messages."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return RecoveryResult(False, message=f"{context} temporarily lost its connection.",
                              recovery="Refresh the page or retry the action. If Atlas is running locally, confirm the Streamlit server is still running.",
                              error_type=type(exc).__name__)
    if isinstance(exc, sqlite3.DatabaseError):
        return RecoveryResult(False, message=f"{context} could not read the paper-trading database.",
                              recovery="Do not delete the database. Run Database Health and restore only from a validated backup if required.",
                              error_type=type(exc).__name__)
    if isinstance(exc, (FileNotFoundError, OSError)):
        return RecoveryResult(False, message=f"{context} could not access a required file.",
                              recovery="Check that the Atlas data folder exists and retry. Your trading data has not been intentionally modified.",
                              error_type=type(exc).__name__)
    return RecoveryResult(False, message=f"{context} could not complete this action.",
                          recovery="Retry once. If the problem continues, keep the error details and restart Atlas.",
                          error_type=type(exc).__name__)


def safe_call(fn: Callable[..., T], *args, context: str = "Atlas", **kwargs) -> RecoveryResult[T]:
    """Execute an operational action and return a recovery state instead of crashing."""
    try:
        return RecoveryResult(True, value=fn(*args, **kwargs))
    except (ConnectionError, TimeoutError, sqlite3.DatabaseError, FileNotFoundError, OSError) as exc:
        info = friendly_error(exc, context=context)
        return RecoveryResult(False, message=info.message, recovery=info.recovery, error_type=info.error_type)


def database_available(db_path: str | Path) -> RecoveryResult[bool]:
    """Lightweight preflight that never creates a missing database."""
    path = Path(db_path)
    if not path.exists():
        return RecoveryResult(False, value=False, message="Paper-trading database was not found.",
                              recovery="Check the configured database path or restore a validated Atlas backup.",
                              error_type="FileNotFoundError")
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
        try:
            row = con.execute("PRAGMA quick_check").fetchone()
        finally:
            con.close()
        ok = bool(row and str(row[0]).lower() == "ok")
        return RecoveryResult(ok, value=ok,
                              message="" if ok else "Paper-trading database failed its quick integrity check.",
                              recovery="Run Database Health before placing or reviewing paper trades." if not ok else "",
                              error_type="DatabaseIntegrityError" if not ok else "")
    except sqlite3.DatabaseError as exc:
        info = friendly_error(exc, context="Atlas")
        return RecoveryResult(False, value=False, message=info.message, recovery=info.recovery, error_type=info.error_type)
