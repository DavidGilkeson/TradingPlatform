"""Convenience import for the Atlas paper-trading dashboard."""

from paper_trading.ui import display_paper_trading_dashboard
from paper_trading.scan_feed import publish_scan_to_streamlit

__all__ = ["display_paper_trading_dashboard", "publish_scan_to_streamlit"]
