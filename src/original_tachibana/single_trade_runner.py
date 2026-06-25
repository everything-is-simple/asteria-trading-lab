from __future__ import annotations

import argparse
from pathlib import Path

from original_tachibana.major_trades import (
    build_major_trades,
    render_single_trade_markdown,
    write_json,
)
from original_tachibana.performance import run_performance


def load_single_trade(segment_id: str, data_dir: Path) -> dict:
    files = sorted(data_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json"))
    equity_rows, metrics = run_performance(files)
    report = build_major_trades(equity_rows, metrics)
    for trade in report["major_trades"]:
        if trade["major_trade_id"] == segment_id:
            return trade
    raise ValueError(f"Unknown major trade id: {segment_id}")


def run_single_trade(
    segment_id: str,
    data_dir: Path = Path("data/pioneer-1975-1976/json"),
    out_dir: Path = Path("data/pioneer-1975-1976/backtest-v0.1/single-trades"),
    report_dir: Path = Path("docs/backtest-spec/original-tachibana-major-trades"),
) -> dict:
    trade = load_single_trade(segment_id, data_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / f"{segment_id}.json", trade)
    (report_dir / f"{segment_id}.md").write_text(render_single_trade_markdown(trade), encoding="utf-8", newline="\n")
    return trade


def main_for_segment(segment_id: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=f"Run single major-trade backtest for {segment_id}.")
    parser.add_argument("--data-dir", default="data/pioneer-1975-1976/json")
    parser.add_argument("--out-dir", default="data/pioneer-1975-1976/backtest-v0.1/single-trades")
    parser.add_argument("--report-dir", default="docs/backtest-spec/original-tachibana-major-trades")
    args = parser.parse_args(argv)
    trade = run_single_trade(segment_id, Path(args.data_dir), Path(args.out_dir), Path(args.report_dir))
    print(
        f"wrote {segment_id}: {trade['start_date']}..{trade['end_date']} "
        f"pnl={trade['pnl']:.2f} point-unit report={Path(args.report_dir) / (segment_id + '.md')}"
    )
    return 0
