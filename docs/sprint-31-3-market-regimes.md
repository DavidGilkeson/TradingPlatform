# Project Atlas — Sprint 31.3 Market Regime Intelligence

Atlas can now classify and analyse paper trades by market environment.

Regimes combine:

- trend: Bullish, Bearish, Sideways, Mixed
- volatility: High Volatility, Lower Volatility, Unknown Volatility

The intelligence layer calculates trade count, win rate, average return,
net P&L and expectancy by regime, then applies Sprint 31.2 sample-quality
grades and evidence thresholds.

Regime metadata is stored separately from the established trade schema for
backward compatibility with existing paper-trading databases.

Important: regime metadata should represent the conditions known at trade
entry. It must not be backfilled using future information.
