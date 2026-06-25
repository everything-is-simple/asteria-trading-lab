from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from original_tachibana.performance import run_performance, write_json


OPERATION_LABELS = {
    "buy_long": "买入建/加多",
    "sell_long": "卖出平多",
    "sell_short": "卖出建/加空",
    "buy_to_cover_short": "买入回补空",
}

PART4_ANNOTATION_PATH = Path("data/pioneer-1975-1976/annotations/part4-pm-annotations-v0.1.json")


def load_part4_annotations(path: Path = PART4_ANNOTATION_PATH) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {item["major_trade_id"]: item for item in payload.get("major_trade_annotations", [])}


def build_major_trades(equity_rows: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    segment_pnl = {row["segment_id"]: row for row in metrics["segment_pnl"]}
    rows_by_segment: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in equity_rows:
        if row["segment_id"] is not None:
            rows_by_segment[row["segment_id"]].append(row)

    annotations = load_part4_annotations()
    major_trades: list[dict[str, Any]] = []
    for segment in metrics["segment_pnl"]:
        segment_id = segment["segment_id"]
        rows = rows_by_segment[segment_id]
        trade_rows = [row for row in rows if row["trade_raw"] is not None]
        entry_rows = [row for row in trade_rows if row["pm_action"] in {"inventory_seed", "add_on", "lock_candidate", "rebalance"}]
        exit_rows = [row for row in trade_rows if row["pm_action"] in {"reduce_add_on", "unlock", "clear"}]
        execution_prices = [row["trade_price"] for row in trade_rows]
        trade_ledger = build_trade_ledger(trade_rows)
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
                "trade_ledger": trade_ledger,
                "max_gross_long": segment["max_gross_long"],
                "max_gross_short": segment["max_gross_short"],
                "max_gross_position": max_gross,
                "has_dual_inventory": segment["max_gross_long"] > 0 and segment["max_gross_short"] > 0,
                "pnl": pnl,
                "return_on_max_gross_notional": pnl / (max_gross * max(row["mark_price"] for row in rows)) if max_gross else 0,
                "result": "win" if pnl > 0 else "loss" if pnl < 0 else "flat",
                "source_months": sorted({row["date_key"][:7] for row in rows}),
                "manual_annotations": annotations.get(segment_id),
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


def build_trade_ledger(trade_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    cumulative_realized_pnl = 0.0
    for row in trade_rows:
        row_realized = sum(operation["realized_pnl"] for operation in row["trade_operations"])
        cumulative_realized_pnl += row_realized
        ledger.append(
            {
                "date_key": row["date_key"],
                "decision_basis_date": row["decision_basis_date"],
                "execution_timing": row["execution_timing"],
                "close_price": row["close_price"],
                "trade_price": row["trade_price"],
                "trade_raw": row["trade_raw"],
                "position_raw": row["position_raw"],
                "inventory_before": row["inventory_before"],
                "inventory_after": row["inventory_after"],
                "long_delta": row["long_delta"],
                "short_delta": row["short_delta"],
                "operations": row["trade_operations"],
                "row_realized_pnl": row_realized,
                "cumulative_realized_pnl": cumulative_realized_pnl,
            }
        )
    return ledger


def format_number(value: Any, digits: int = 0) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def format_inventory(inventory: dict[str, Any]) -> str:
    return f"L{inventory['gross_long']} / S{inventory['gross_short']}"


def format_operations(operations: list[dict[str, Any]]) -> str:
    if not operations:
        return "-"
    parts = []
    for operation in operations:
        label = OPERATION_LABELS.get(operation["operation"], operation["operation"])
        pnl = operation["realized_pnl"]
        avg = operation.get("average_cost")
        avg_text = f", 均价 {avg:.2f}" if avg is not None else ""
        parts.append(
            f"{label} {operation['quantity']}单位 @ {operation['price']}{avg_text}, "
            f"成交额点单位 {operation['notional_point_hand']:.0f}, 实现 {pnl:.2f}"
        )
    return "<br>".join(parts)


def format_annotation_items(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, list):
        return ", ".join(format_annotation_items(item) for item in value) if value else "-"
    if isinstance(value, dict):
        parts = []
        for key, item in value.items():
            parts.append(f"{key}={format_annotation_items(item)}")
        return "; ".join(parts) if parts else "-"
    return str(value)


def render_annotation_summary_rows(trades: list[dict[str, Any]]) -> list[str]:
    rows = []
    for trade in trades:
        annotation = trade.get("manual_annotations")
        if not annotation:
            continue
        rows.append(
            "| {id} | {interpretation} | {mother} | {lock} | {add_on} | {risk} |".format(
                id=trade["major_trade_id"],
                interpretation=annotation.get("dominant_interpretation", "-"),
                mother=format_annotation_items(annotation.get("mother_position")),
                lock=format_annotation_items(annotation.get("lock_purpose")),
                add_on=format_annotation_items(annotation.get("add_on")),
                risk=format_annotation_items(annotation.get("risk_tags")),
            )
        )
    return rows


def render_markdown(report: dict[str, Any]) -> str:
    coverage = report["coverage"]
    summary = report["summary"]
    lines = [
        "# 原始立花法 v0.1 每一大笔交易回测报告",
        "",
        "## 定义",
        "",
        "本报告按用户定义的“一大笔交易”统计：从第一笔开仓/加码开始，经过未平仓库存累积，直到库存归零平仓为止。总表只做索引；逐笔查账见 `original-tachibana-major-trades/` 下 15 份单笔报告。",
        "",
        "记号语义：`—5` 表示买入 5 记录单位并增加多头；`5—` 表示卖出 5 记录单位并增加空头或减少多头；未平仓横杠左侧为空头，右侧为多头。",
        "",
        "单位说明：本报告按 `价格点 × 记录单位` 展开；part4 记录 PIONEER 自 1976-09-21 起交易单位改为 100 股，资金层不得全样本统一乘 1000。",
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
        "| ID | 单笔报告 | 起始 | 结束 | 方向 | 最大多头 | 最大空头 | PnL | 结果 | 开单/加码序列 | 平仓序列 |",
        "|---|---|---|---|---|---:|---:|---:|---|---|---|",
    ]
    for trade in report["major_trades"]:
        lines.append(
            "| {major_trade_id} | [明细](./original-tachibana-major-trades/{major_trade_id}.md) | {start_date} | {end_date} | {direction} | {max_gross_long} | {max_gross_short} | {pnl:.0f} | {result} | {entry} | {exit} |".format(
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
            "S013 是 1976-10 到 1976-11 的大笔多头交易：`—10 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —2 / —20 / —50 / —102` 买入累积到多头 200 记录单位，随后 `200 —` 卖出清仓，PnL 约 +41140 点单位。详见单独报告。",
            "",
            "## Part4 PM 人工标注摘要",
            "",
            "| ID | 主解释 | 母单 | 锁单目的 | 加码 | 风险标签 |",
            "|---|---|---|---|---|---|",
        ]
    )
    annotation_rows = render_annotation_summary_rows(report["major_trades"])
    lines.extend(annotation_rows if annotation_rows else ["| - | - | - | - | - | - |"])
    lines.extend(
        [
            "",
            "这些标注来自 `data/pioneer-1975-1976/annotations/part4-pm-annotations-v0.1.json`，用于把书页解释并列放在数值账本旁边；机器仍只把双侧库存自动标为 `lock_candidate`，不自动确认锁单目的。",
            "",
            "## 限制",
            "",
            "- 本报告基于现有 JSON 重建。若后续逐图校对发现 `trade_raw`、`position_raw` 或价格字段抄录错误，需要重跑本报告。",
            "- 双侧库存段先按库存事实归入同一大笔交易；锁单是否成立仍需人工校勘。",
            "- 本报告不使用执行日同日收盘价生成交易，只用它做成交后的盯市。",
        ]
    )
    return "\n".join(lines) + "\n"


def render_single_trade_markdown(trade: dict[str, Any]) -> str:
    lines = [
        f"# 原始立花法 v0.1 大笔交易 {trade['major_trade_id']} 回测报告",
        "",
        "## 摘要",
        "",
        "| 项目 | 数值 |",
        "|---|---:|",
        f"| 起始日期 | {trade['start_date']} |",
        f"| 结束日期 | {trade['end_date']} |",
        f"| 方向 | {trade['direction']} |",
        f"| 成交行数 | {trade['trade_count']} |",
        f"| 最大多头 | {trade['max_gross_long']} 记录单位 |",
        f"| 最大空头 | {trade['max_gross_short']} 记录单位 |",
        f"| PnL | {trade['pnl']:.2f} 点单位 |",
        f"| 结果 | {trade['result']} |",
        "",
        "单位说明：本报告按 `价格点 × 记录单位` 展开；1976-09-21 前后股数乘数不同，本 v0.1 明细暂不换算真实股数金额。",
        "",
        "## 逐笔成交流水",
        "",
        "| 日期 | 判断依据日 | 成交价 | 买卖原文 | 成交操作 | 成交前库存 | 成交后库存 | 当笔实现PnL | 累计实现PnL |",
        "|---|---|---:|---|---|---|---|---:|---:|",
    ]
    for ledger in trade["trade_ledger"]:
        lines.append(
            "| {date_key} | {basis} | {trade_price} | {trade_raw} | {operations} | {before} | {after} | {row_pnl} | {cum_pnl} |".format(
                date_key=ledger["date_key"],
                basis=ledger["decision_basis_date"] or "-",
                trade_price=format_number(ledger["trade_price"]),
                trade_raw=ledger["trade_raw"],
                operations=format_operations(ledger["operations"]),
                before=format_inventory(ledger["inventory_before"]),
                after=format_inventory(ledger["inventory_after"]),
                row_pnl=format_number(ledger["row_realized_pnl"], 2),
                cum_pnl=format_number(ledger["cumulative_realized_pnl"], 2),
            )
        )
    annotation = trade.get("manual_annotations")
    if annotation:
        lines.extend(
            [
                "",
                "## Part4 PM 人工标注",
                "",
                "| 字段 | 标注 |",
                "|---|---|",
                f"| 来源页 | {format_annotation_items(annotation.get('source_pages'))} |",
                f"| 主解释 | {annotation.get('dominant_interpretation', '-')} |",
                f"| 母单 | {format_annotation_items(annotation.get('mother_position'))} |",
                f"| 锁单目的 | {format_annotation_items(annotation.get('lock_purpose'))} |",
                f"| 反向测试区间 | {format_annotation_items(annotation.get('reverse_probe_ranges'))} |",
                f"| 加码 | {format_annotation_items(annotation.get('add_on'))} |",
                f"| 单位背景 | {annotation.get('unit_context', '-')} |",
                f"| 风险标签 | {format_annotation_items(annotation.get('risk_tags'))} |",
                f"| 说明 | {format_annotation_items(annotation.get('notes'))} |",
                "",
                "这一区块是书页解释层，不覆盖上方逐笔成交和 PnL 账本。",
            ]
        )
    lines.extend(
        [
            "",
            "## 原始序列",
            "",
            f"- 成交序列：`{trade['trade_sequence']}`",
            f"- 开单/加码序列：`{trade['entry_trade_sequence'] or '-'}`",
            f"- 平仓序列：`{trade['exit_trade_sequence'] or '-'}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_single_trade_reports(report: dict[str, Any], report_path: Path) -> None:
    detail_dir = report_path.parent / "original-tachibana-major-trades"
    detail_dir.mkdir(parents=True, exist_ok=True)
    for trade in report["major_trades"]:
        path = detail_dir / f"{trade['major_trade_id']}.md"
        path.write_text(render_single_trade_markdown(trade), encoding="utf-8", newline="\n")


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
    report_path = Path(args.report_path)
    report_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    write_single_trade_reports(report, report_path)
    print(f"wrote {len(report['major_trades'])} major trades to {out_dir / 'major_trades.json'}")
    print(f"wrote report to {args.report_path}")
    print(f"wrote single-trade reports to {report_path.parent / 'original-tachibana-major-trades'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
