# Project Atlas — Sprint 31.8

Exact entry-to-outcome lineage is now live.

- BUY orders create FIFO position lots
- partial SELLs consume lots correctly
- realised trades link to exact originating BUY order IDs
- multiple-entry positions preserve all contributing entry links
- calibration uses exact entry intelligence snapshots
- legacy trades remain supported but are never guessed

This removes the main calibration-quality limitation identified in Sprint 31.7.

Next: close Sprint 31 with calibration-quality diagnostics and a consolidated
Intelligence Scorecard.
