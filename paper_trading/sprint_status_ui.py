import streamlit as st

def display_paper_trading_system_status():
    with st.expander("🚀 Sprint 29 Paper Trading System",expanded=False):
        st.success("Sprint 29 complete")
        st.markdown("""
**29.1** Foundation · **29.2** Order Engine · **29.3** Portfolio  
**29.4** Journal · **29.5** Performance · **29.6** Smart Watchlist  
**29.7** Opportunity / Alert quick-trade integration
""")
        st.caption("All orders are simulated. Paper-trading results do not guarantee future live-trading performance.")
