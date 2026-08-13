# Project Atlas — Sprint 31.8 Exact Entry Snapshot Linkage

Atlas now records exact lineage between future paper BUY orders and realised
paper trades.

New BUYs create FIFO position lots identified by BUY order ID. When shares are
sold, Atlas records the exact BUY order(s) that supplied the sold shares and
their allocation weights.

Outcome Calibration now joins realised outcomes directly to the saved
entry-time intelligence snapshot through those BUY order IDs.

For a SELL spanning multiple entry lots, realised P&L is allocated according
to sold-share weight. This preserves the existing weighted-average paper P&L
engine while providing exact entry-decision lineage.

Older positions and completed trades created before Sprint 31.8 remain valid.
They are not guessed or retroactively linked; legacy unlinked trades are
reported separately and excluded from exact calibration.
