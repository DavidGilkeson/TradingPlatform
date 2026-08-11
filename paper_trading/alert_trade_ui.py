import pandas as pd
from .quick_trade_ui import display_selected_quick_trade

def display_alert_quick_trade(alerts_df: pd.DataFrame|None):
    display_selected_quick_trade(
        alerts_df, source="Alert Centre",
        key_prefix="alert_quick_trade",
        heading="⚡ Alert Quick Paper Trade",
    )
