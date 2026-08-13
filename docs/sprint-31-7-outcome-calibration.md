# Project Atlas — Sprint 31.7 Outcome Calibration

Atlas now compares saved entry-time intelligence with realised paper-trade outcomes.

Calibration groups Historical Match scores into 80–100, 60–79, 40–59 and
0–39 bands and measures:

- completed calibrated trades
- win rate
- average return
- net P&L
- expectancy
- average reliability
- correlation between Historical Match score and realised return
- high-score versus low-score win-rate direction

Only snapshots recorded at or before trade entry are eligible, preventing
future information from contaminating calibration.

The current trade schema does not directly store the originating BUY order ID
on each realised trade. For positions with multiple BUY entries, calibration
therefore uses the latest same-ticker snapshot available at or before the
recorded position entry time. A future schema sprint can make this linkage exact.
