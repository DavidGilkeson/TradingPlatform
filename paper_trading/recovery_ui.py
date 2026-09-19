"""Streamlit presentation helpers for recoverable Atlas failures."""
from __future__ import annotations

from .resilience import RecoveryResult


def render_recovery(result: RecoveryResult, *, st_module=None) -> None:
    if result.ok:
        return
    if st_module is None:
        import streamlit as st_module
    st_module.error(result.message or "Atlas could not complete this action.")
    if result.recovery:
        st_module.info(f"Recovery: {result.recovery}")


def render_server_reconnect_help(*, st_module=None) -> None:
    if st_module is None:
        import streamlit as st_module
    st_module.warning("Atlas temporarily lost connection to the local Streamlit server.")
    st_module.info("Refresh the page. If it does not reconnect, confirm the Streamlit terminal is still running and restart Atlas.")
