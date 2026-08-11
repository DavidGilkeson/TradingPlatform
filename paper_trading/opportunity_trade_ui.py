import pandas as pd
from .quick_trade_ui import display_selected_quick_trade

def display_opportunity_quick_trade(opportunities_df: pd.DataFrame|None, minimum_score=None):
    display_selected_quick_trade(
        opportunities_df, source="Opportunity Centre",
        key_prefix="opportunity_quick_trade",
        heading="⚡ Opportunity Quick Paper Trade",
        minimum_score=minimum_score,
    )
