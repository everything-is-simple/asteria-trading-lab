from __future__ import annotations

# This tiny program exists so major trade S012 can be replayed alone.
# It keeps the audit surface small: one flat-to-flat trade, one ledger,
# one markdown report, without hiding mistakes inside the full backtest.

from original_tachibana.single_trade_runner import main_for_segment


if __name__ == "__main__":
    raise SystemExit(main_for_segment("S012"))
