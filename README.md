# Project Atlas — Sprint 32.9

Decision Support Overlay is live.

The Paper Order Ticket now surfaces forward-tested regime evidence immediately
beside a proposed trade.

It displays:
- current market regime
- current volatility regime
- overall regime-evidence assessment
- favourable evidence messages
- caution messages when matching resolved evidence has underperformed SPY
- insufficient-evidence messages when the sample is still too small

The initial decision-support horizon is five trading days and retains the
minimum five-observation evidence threshold from cohort validation.

Important: this overlay is advisory. It does not automatically place, reject,
block or resize a paper order. Atlas is still collecting prospective evidence
before regime statistics are allowed to influence execution rules.

Next candidate: Sprint 33 — Paper Trading Workflow & Trade Journal refinement,
bringing the scanner, decision support, order, thesis and post-trade review
into one cleaner workflow.
