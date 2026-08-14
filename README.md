# Project Atlas — Sprint 32.7

Automatic Entry-Time Regime Detection is live.

When a new forward-test decision is recorded, Atlas can automatically analyse
SPY and preserve the market environment that existed at that moment.

Captured evidence:
- Bullish / Neutral / Bearish market regime
- Quiet / Normal / Volatile volatility regime
- Strong / Moderate / Weak trend strength
- SPY price
- 50-day moving average
- 200-day moving average
- percentage distance from both averages
- 20-day annualised realised volatility

The market classifier uses SPY price structure relative to its 50-day and
200-day moving averages. A manual fallback remains available when market data
cannot be downloaded.

Existing databases migrate automatically. Historical records are not rewritten
with hindsight.

Next: Sprint 32.8 — regime-aware validation insights and warnings.
