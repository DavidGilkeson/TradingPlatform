# Project Atlas — Sprint 32.7.3

Paper Trading Scan Feed Fix.

The ticker and live-price fallback from Sprint 32.7.2 worked, but the latest
Atlas scanner DataFrame still was not consistently reaching Paper Trading.
That is why scanned symbols could show a real live price while Atlas Score and
Atlas Verdict remained blank.

Sprint 32.7.3 adds a canonical Streamlit scan feed:

- latest market scan can be published into `st.session_state`
- Paper Trading automatically recovers the canonical scan after reruns
- compatibility recovery checks common older session-state keys
- a final compatibility scan can detect any session-state DataFrame with a
  `Ticker` column
- explicitly passed `market_df` remains the highest-priority source
- scan DataFrame is copied before persistence so display filtering cannot
  mutate the canonical result

IMPORTANT:
The Sprint package does not contain the user's top-level `app.py`.
See `APP_PY_PATCH_32_7_3.txt` for the two small app.py integration changes.
The canonical app flow should call:

    publish_scan_to_streamlit(df)

after a successful scan and pass `market_df=df` to the Paper Trading dashboard
when convenient.

Once connected, Paper Trading receives the same Score, Signal/Verdict, moving
averages, RSI and other scan context used by the rest of Atlas.
