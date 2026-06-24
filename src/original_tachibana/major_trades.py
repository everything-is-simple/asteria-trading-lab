from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from original_tachibana.performance import run_performance, write_json


def build_major_trades(equity_rows: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    segment_pnl = {row["segment_id"]: row for row in metrics["segment_pnl"]}
    rows_by_segment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in equity_rows:
        if row["segment_id"] is not None:
            rows_by_segment[row["segment_id"]].append(row)

    major_trades: list[dict[str, Any]] = []
    for segment in metrics["segment_pnl"]:
        segment_id = segment["segment_id"]
        rows = rows_by_segment[segment_id]
        trade_rows = [row for row in rows if row["trade_raw"] is not None]
        entry_rows = [row for row in trade_rows if row["pm_action"] in {"inventory_seed", "add_on", "lock_candidate", "rebalance"}]
        exit_rows = [row for row in trade_rows if row["pm_action"] in {"reduce_add_on", "unlock", "clear"}]
        execution_prices = [row["trade_price"] for row in trade_rows]
        max_gross = max(segment["max_gross_long"], segment["max_gross_short"])
        pnl = segment["pnl"]
        major_trades.append(
            {
                "major_trade_id": segment_id,
                "start_date": segment["start_date"],
                "end_date": segment["end_date"],
                "direction": segment["center_side"],
                "trade_count": len(trade_rows),
                "entry_trade_sequence": " / ".join(row["trade_raw"] for row in entry_rows),
                "exit_trade_sequence": " / ".join(row["trade_raw"] for row in exit_rows),
                "trade_sequence": " / ".join(row["trade_raw"] for row in trade_rows),
                "execution_prices": execution_prices,
                "max_gross_long": segment["max_gross_long"],
                "max_gross_short": segment["max_gross_short"],
                "max_gross_position": max_gross,
                "has_dual_inventory": segment["max_gross_long"] > 0 and segment["max_gross_short"] > 0,
                "pnl": pnl,
                "return_on_max_gross_notional": pnl / (max_gross * max(row["mark_price"] for row in rows)) if max_gross else 0,
                "result": "win" if pnl > 0 else "loss" if pnl < 0 else "flat",
                "source_months": sorted({row["date_key"][:7] for row in rows}),
            }
        )

    wins = [row for row in major_trades if row["pnl"] > 0]
    losses = [row for row in major_trades if row["pnl"] < 0]
    gross_profit = sum(row["pnl"] for row in wins)
    gross_loss = sum(row["pnl"] for row in losses)
    trade_rows = [row for row in equity_rows if row["trade_raw"] is not None]
    return {
        "coverage": {
            "daily_rows": len(equity_rows),
            "trade_rows": len(trade_rows),
            "source_months": sorted({row["date_key"][:7] for row in equity_rows}),
            "missing_trade_price_on_trade_rows": sum(1 for row in trade_rows if row["trade_price"] is None),
            "missing_position_on_trade_rows": sum(1 for row in trade_rows if row["position_raw"] is None),
        },
        "summary": {
            "major_trade_count": len(major_trades),
            "winning_major_trades": len(wins),
            "losing_major_trades": len(losses),
            "win_rate": len(wins) / len(major_trades) if major_trades else None,
            "total_pnl": sum(row["pnl"] for row in major_trades),
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "profit_factor": gross_profit / abs(gross_loss) if gross_loss else None,
            "best_major_trade": max(major_trades, key=lambda row: row["pnl"]) if major_trades else None,
            "worst_major_trade": min(major_trades, key=lambda row: row["pnl"]) if major_trades else None,
        },
        "major_trades": major_trades,
    }


def render_markdown(report: dict[str, Any]) -> str:
    coverage = report["coverage"]
    summary = report["summary"]
    lines = [
        "# 原始立花法 v0.1 每一大笔交易回测报告",
        "",
        "## 定义",
        "",
        "本报告按用户定义的“一大笔交易”统计：从第一笔开仓/加码开始，经过未平仓库存累积，直到库存归零平仓为止。",
        "",
        "记号语义：`—5` 表示买入 5 张并增加多头；`5—` 表示卖出 5 张并增加空头或减少多头；未平仓横杠左侧为空头，右侧为多头。",
        "",
        "## 总览",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 大笔交易数 | {summary['major_trade_count']} |",
        f"| 盈利大笔交易 | {summary['winning_major_trades']} |",
        f"| 亏损大笔交易 | {summary['losing_major_trades']} |",
        f"| 胜率 | {summary['win_rate']:.2%} |",
        f"| 总 PnL | {summary['total_pnl']:.0f} |",
        f"| Gross Profit | {summary['gross_profit']:.0f} |",
        f"| Gross Loss | {summary['gross_loss']:.0f} |",
        f"| Profit Factor | {summary['profit_factor']:.2f} |",
        f"| 最佳大笔交易 | {summary['best_major_trade']['major_trade_id']} / {summary['best_major_trade']['pnl']:.0f} |",
        f"| 最差大笔交易 | {summary['worst_major_trade']['major_trade_id']} / {summary['worst_major_trade']['pnl']:.0f} |",
        "",
        "## 数据完整性检查",
        "",
        "| 项目 | 数值 |",
        "|---|---:|",
        f"| 月度 JSON | {len(coverage['source_months'])} |",
        f"| 日级记录 | {coverage['daily_rows']} |",
        f"| 交易记录 | {coverage['trade_rows']} |",
        f"| 交易行缺成交价 | {coverage['missing_trade_price_on_trade_rows']} |",
        f"| 交易行缺未平仓 | {coverage['missing_position_on_trade_rows']} |",
        "",
        "## 逐笔明细",
        "",
        "| ID | 起始 | 结束 | 方向 | 最大多头 | 最大空头 | PnL | 结果 | 开单/加码序列 | 平仓序列 |",
        "|---|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for trade in report["major_trades"]:
        lines.append(
            "| {major_trade_id} | {start_date} | {end_date} | {direction} | {max_gross_long} | {max_gross_short} | {pnl:.0f} | {result} | {entry} | {exit} |".format(
                major_trade_id=trade["major_trade_id"],
                start_date=trade["start_date"],
                end_date=trade["end_date"],
                direction=trade["direction"],
                max_gross_long=trade["max_gross_long"],
                max_gross_short=trade["max_gross_short"],
                pnl=trade["pnl"],
                result=trade["result"],
                entry=trade["entry_trade_sequence"] or "-",
                exit=trade["exit_trade_sequence"] or "-",
            )
        )
    lines.extend(
        [
            "",
            "## 重点样本",
            "",
            "S013 是 1976-10 到 1976-11 的大笔多头交易：`—10 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —20 / —50 / —102` 买入累积到多头 200 张，随后 `200 —` 卖出清仓，PnL 约 +41140。",
            "",
            "## 限制",
            "",
            "- 本报告基于现有 JSON 重建。若后续逐图校对发现 `trade_raw`、`position_raw` 或价格字段抄录错误，需要重跑本报告。",
            "- 双侧库存段先按库存事实归入同一大笔交易；锁单是否成立仍需人工校勘。",
            "- 本报告不使用执行日同日收盘价生成交易，只用它做成交后的盯市。",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build major-trade report for original Tachibana v0.1.")
    parser.add_argument("--data-dir", default="data/pioneer-1975-1976/json")
    parser.add_argument("--out-dir", default="data/pioneer-1975-1976/backtest-v0.1")
    parser.add_argument(
        "--report-path",
        default="docs/backtest-spec/original-tachibana-v0.1-major-trades-report.md",
    )
    args = parser.parse_args(argv)

    files = [path for path in Path(args.data_dir).glob("*.json") if path.name[:4].isdigit()]
    equity_rows, metrics = run_performance(files)
    report = build_major_trades(equity_rows, metrics)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "major_trades.json", report)
    Path(args.report_path).write_text(render_markdown(report), encoding="utf-8", newline="\n")
    print(f"wrote {len(report['major_trades'])} major trades to {out_dir / 'major_trades.json'}")
    print(f"wrote report to {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
