from __future__ import annotations

import argparse
import math
from collections import defaultdict
from pathlib import Path
from statistics import median, mean, pstdev
from typing import Any, Iterable

from original_tachibana.major_trades import build_major_trades
from original_tachibana.performance import run_performance, write_json


def build_quant_report(equity_rows: list[dict[str, Any]], metrics: dict[str, Any]) -> dict[str, Any]:
    major_report = build_major_trades(equity_rows, metrics)
    trades = major_report["major_trades"]
    pnl_values = [trade["pnl"] for trade in trades]
    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = sum(trade["pnl"] for trade in losses)
    avg_win = gross_profit / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    payoff_ratio = avg_win / abs(avg_loss) if avg_loss else None
    profit_factor = gross_profit / abs(gross_loss) if gross_loss else None
    expectancy = sum(pnl_values) / len(pnl_values) if pnl_values else None
    pnl_std = pstdev(pnl_values) if len(pnl_values) > 1 else 0.0
    trade_sample_sharpe = mean(pnl_values) / pnl_std * math.sqrt(len(pnl_values)) if pnl_std else None
    sqn = mean(pnl_values) / pnl_std * math.sqrt(len(pnl_values)) if pnl_std else None
    returns = [trade["return_on_max_gross_notional"] for trade in trades]
    return_std = pstdev(returns) if len(returns) > 1 else 0.0
    trade_return_sharpe = mean(returns) / return_std * math.sqrt(len(returns)) if return_std else None
    sorted_wins = sorted(wins, key=lambda trade: trade["pnl"], reverse=True)

    return {
        "scope": {
            "sample": "Pioneer 1975-1976 original Tachibana v0.1, 15 closed major trades",
            "unit": "point-hand: execution price point × recorded hands/units, before any date-dependent share multiplier",
            "cost_model": metrics["assumptions"]["transaction_cost"],
            "slippage_model": metrics["assumptions"]["slippage"],
            "execution_model": metrics["assumptions"]["execution_timing"],
            "decision_basis": metrics["assumptions"]["decision_basis"],
        },
        "coverage": {
            **major_report["coverage"],
            "major_trade_count": len(trades),
        },
        "account_performance": metrics["performance"],
        "trade_statistics": {
            "trade_count": len(trades),
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "flat_trades": len(trades) - len(wins) - len(losses),
            "win_rate": len(wins) / len(trades) if trades else None,
            "loss_rate": len(losses) / len(trades) if trades else None,
            "total_pnl": sum(pnl_values),
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "net_profit": gross_profit + gross_loss,
            "average_trade": expectancy,
            "median_trade": median(pnl_values) if pnl_values else None,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "payoff_ratio": payoff_ratio,
            "profit_factor": profit_factor,
            "expectancy_per_trade": expectancy,
            "pnl_standard_deviation": pnl_std,
            "trade_sample_sharpe_like": trade_sample_sharpe,
            "trade_return_sharpe_like": trade_return_sharpe,
            "system_quality_number": sqn,
            "best_trade": max(trades, key=lambda trade: trade["pnl"]) if trades else None,
            "worst_trade": min(trades, key=lambda trade: trade["pnl"]) if trades else None,
            "max_consecutive_wins": max_streak(trades, "win"),
            "max_consecutive_losses": max_streak(trades, "loss"),
            "best_trade_share_of_total_pnl": (max(pnl_values) / sum(pnl_values)) if pnl_values and sum(pnl_values) else None,
            "top_3_win_share_of_total_pnl": (
                sum(trade["pnl"] for trade in sorted_wins[:3]) / sum(pnl_values)
                if pnl_values and sum(pnl_values)
                else None
            ),
        },
        "direction_breakdown": breakdown_by_key(trades, "direction"),
        "year_breakdown": breakdown_by_year(trades),
        "major_trades": trades,
    }


def max_streak(trades: Iterable[dict[str, Any]], result: str) -> int:
    best = 0
    current = 0
    for trade in trades:
        if trade["result"] == result:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def breakdown_by_key(trades: Iterable[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        grouped[str(trade[key])].append(trade)
    return [summarize_group(name, rows) for name, rows in sorted(grouped.items())]


def breakdown_by_year(trades: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for trade in trades:
        grouped[trade["start_date"][:4]].append(trade)
    return [summarize_group(name, rows) for name, rows in sorted(grouped.items())]


def summarize_group(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    pnl = [row["pnl"] for row in rows]
    wins = [row for row in rows if row["pnl"] > 0]
    losses = [row for row in rows if row["pnl"] < 0]
    gross_loss = sum(row["pnl"] for row in losses)
    gross_profit = sum(row["pnl"] for row in wins)
    return {
        "name": name,
        "trade_count": len(rows),
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": len(wins) / len(rows) if rows else None,
        "total_pnl": sum(pnl),
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "profit_factor": gross_profit / abs(gross_loss) if gross_loss else None,
        "average_trade": mean(pnl) if pnl else None,
        "best_trade": max(rows, key=lambda row: row["pnl"])["major_trade_id"] if rows else None,
        "worst_trade": min(rows, key=lambda row: row["pnl"])["major_trade_id"] if rows else None,
    }


def render_markdown(report: dict[str, Any]) -> str:
    scope = report["scope"]
    coverage = report["coverage"]
    account = report["account_performance"]
    stats = report["trade_statistics"]
    lines = [
        "# 原始立花法 v0.1 十五大交易量化回测报告",
        "",
        "## 口径",
        "",
        f"- 样本：{scope['sample']}",
        f"- 单位：{scope['unit']}",
        f"- 下单：{scope['decision_basis']}；{scope['execution_model']}",
        f"- 成本：手续费 {scope['cost_model']}，滑点 {scope['slippage_model']}",
        "- 说明：资金层需按日期/交易单位表换算；part4 记录 PIONEER 自 1976-09-21 起交易单位改为 100 股，不能把全样本金额统一乘 1000。胜率、夏普率、盈亏比、Profit Factor 等比率不受股数乘数影响。",
        "",
        "## 核心指标",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 净利润 | {fmt_number(stats['net_profit'])} 点手 |",
        f"| 总收益率 | {fmt_percent(account['total_return'])} |",
        f"| CAGR | {fmt_percent(account['cagr'])} |",
        f"| 年化波动率 | {fmt_percent(account['annualized_volatility'])} |",
        f"| 夏普率 Sharpe | {fmt_number(account['sharpe'], 2)} |",
        f"| Sortino | {fmt_number(account['sortino'], 2)} |",
        f"| 最大回撤 | {fmt_percent(account['max_drawdown'])} |",
        f"| 最大回撤区间 | {account['max_drawdown_start']} 至 {account['max_drawdown_end']} |",
        f"| 资本基准 | {fmt_number(account['capital_base'])} 点手 |",
        "",
        "## 交易统计",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 大交易数 | {stats['trade_count']} |",
        f"| 盈利笔数 | {stats['winning_trades']} |",
        f"| 亏损笔数 | {stats['losing_trades']} |",
        f"| 胜率 | {fmt_percent(stats['win_rate'])} |",
        f"| 毛利润 Gross Profit | {fmt_number(stats['gross_profit'])} 点手 |",
        f"| 毛亏损 Gross Loss | {fmt_number(stats['gross_loss'])} 点手 |",
        f"| Profit Factor | {fmt_number(stats['profit_factor'], 2)} |",
        f"| 平均盈利 | {fmt_number(stats['average_win'], 2)} 点手 |",
        f"| 平均亏损 | {fmt_number(stats['average_loss'], 2)} 点手 |",
        f"| 盈亏比 Payoff Ratio | {fmt_number(stats['payoff_ratio'], 2)} |",
        f"| 单笔期望值 | {fmt_number(stats['expectancy_per_trade'], 2)} 点手 |",
        f"| 中位数单笔 | {fmt_number(stats['median_trade'], 2)} 点手 |",
        f"| 单笔 PnL 标准差 | {fmt_number(stats['pnl_standard_deviation'], 2)} 点手 |",
        f"| 交易样本 Sharpe-like | {fmt_number(stats['trade_sample_sharpe_like'], 2)} |",
        f"| SQN | {fmt_number(stats['system_quality_number'], 2)} |",
        f"| 最大连续盈利 | {stats['max_consecutive_wins']} 笔 |",
        f"| 最大连续亏损 | {stats['max_consecutive_losses']} 笔 |",
        f"| 最佳交易 | {stats['best_trade']['major_trade_id']} / {fmt_number(stats['best_trade']['pnl'])} 点手 |",
        f"| 最差交易 | {stats['worst_trade']['major_trade_id']} / {fmt_number(stats['worst_trade']['pnl'])} 点手 |",
        "",
        "交易样本 Sharpe-like 只用于观察 15 笔大交易的离散程度；正式夏普率以上方日权益曲线 Sharpe 为准。",
        "",
        "## 盈利集中度",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 最佳单笔占总净利润 | {fmt_percent(stats['best_trade_share_of_total_pnl'])} |",
        f"| 前三盈利单笔占总净利润 | {fmt_percent(stats['top_3_win_share_of_total_pnl'])} |",
        "",
        "## 方向拆分",
        "",
        "| 方向 | 笔数 | 胜率 | 净利润 | Profit Factor | 平均单笔 | 最佳 | 最差 |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]
    lines.extend(render_group_rows(report["direction_breakdown"]))
    lines.extend(
        [
            "",
            "## 年度拆分",
            "",
            "| 年份 | 笔数 | 胜率 | 净利润 | Profit Factor | 平均单笔 | 最佳 | 最差 |",
            "|---|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    lines.extend(render_group_rows(report["year_breakdown"]))
    lines.extend(
        [
            "",
            "## 十五大交易明细",
            "",
            "| ID | 起始 | 结束 | 方向 | 成交行 | 最大多头 | 最大空头 | PnL | 最大名义收益率 | 结果 |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for trade in report["major_trades"]:
        lines.append(
            "| {id} | {start} | {end} | {direction} | {count} | {long} | {short} | {pnl} | {ret} | {result} |".format(
                id=trade["major_trade_id"],
                start=trade["start_date"],
                end=trade["end_date"],
                direction=trade["direction"],
                count=trade["trade_count"],
                long=trade["max_gross_long"],
                short=trade["max_gross_short"],
                pnl=fmt_number(trade["pnl"]),
                ret=fmt_percent(trade["return_on_max_gross_notional"]),
                result=trade["result"],
            )
        )
    lines.extend(
        [
            "",
            "## 数据完整性",
            "",
            "| 项目 | 数值 |",
            "|---|---:|",
            f"| 日级记录 | {coverage['daily_rows']} |",
            f"| 交易行 | {coverage['trade_rows']} |",
            f"| 大交易 | {coverage['major_trade_count']} |",
            f"| 交易行缺成交价 | {coverage['missing_trade_price_on_trade_rows']} |",
            f"| 交易行缺未平仓 | {coverage['missing_position_on_trade_rows']} |",
            "",
            "## 读法",
            "",
            "- 这份报告回答“十五大交易作为一个交易系统，量化统计如何”。",
            "- 查某一笔为什么赚亏，仍看 `docs/backtest-spec/original-tachibana-major-trades/Sxxx.md` 的逐笔成交价、手数、库存和实现 PnL。",
            "- 本 v0.1 不加入手续费、滑点、税费，也不把点手金额统一乘 1000；这些是后续日期依赖资金口径版本的工作。",
        ]
    )
    return "\n".join(lines) + "\n"


def render_group_rows(rows: list[dict[str, Any]]) -> list[str]:
    return [
        "| {name} | {count} | {win_rate} | {pnl} | {pf} | {avg} | {best} | {worst} |".format(
            name=row["name"],
            count=row["trade_count"],
            win_rate=fmt_percent(row["win_rate"]),
            pnl=fmt_number(row["total_pnl"]),
            pf=fmt_number(row["profit_factor"], 2),
            avg=fmt_number(row["average_trade"], 2),
            best=row["best_trade"],
            worst=row["worst_trade"],
        )
        for row in rows
    ]


def fmt_number(value: Any, digits: int = 0) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def fmt_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.2%}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build quant report for original Tachibana v0.1 major trades.")
    parser.add_argument("--data-dir", default="data/pioneer-1975-1976/json")
    parser.add_argument("--out-dir", default="data/pioneer-1975-1976/backtest-v0.1")
    parser.add_argument(
        "--report-path",
        default="docs/backtest-spec/original-tachibana-v0.1-quant-report.md",
    )
    args = parser.parse_args(argv)

    files = sorted(Path(args.data_dir).glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json"))
    if not files:
        raise SystemExit(f"No monthly JSON files found in {args.data_dir}")

    equity_rows, metrics = run_performance(files)
    report = build_quant_report(equity_rows, metrics)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "quant_report.json", report)

    report_path = Path(args.report_path)
    report_path.write_text(render_markdown(report), encoding="utf-8", newline="\n")
    print(f"wrote quant report to {report_path}")
    print(f"wrote quant metrics to {out_dir / 'quant_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
