from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable

from original_tachibana.pm_state import run_backtest, write_jsonl


TRADING_DAYS_PER_YEAR = 252
SHARES_PER_HAND_NOTE = (
    "v0.1 reports PnL in price-point × recorded unit before share multiplier; "
    "Pioneer records note the trading unit changed from 1000 shares to 100 shares on 1976-09-21"
)


@dataclass
class CostState:
    long_qty: int = 0
    long_cost: float = 0.0
    short_qty: int = 0
    short_proceeds: float = 0.0
    realized_pnl: float = 0.0

    @property
    def avg_long(self) -> float | None:
        return self.long_cost / self.long_qty if self.long_qty else None

    @property
    def avg_short(self) -> float | None:
        return self.short_proceeds / self.short_qty if self.short_qty else None


def run_performance(files: Iterable[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    daily_rows, pm_summary = run_backtest(files)
    cost = CostState()
    previous_long = 0
    previous_short = 0
    previous_equity = 0.0
    previous_mark: float | None = None
    equity_rows: list[dict[str, Any]] = []
    segment_pnl: dict[str, float] = {}

    for row in daily_rows:
        trade_price = row["trade_price"]
        realized_delta = 0.0
        long_delta = 0
        short_delta = 0
        inventory_before = {
            "gross_long": previous_long,
            "gross_short": previous_short,
        }
        trade_operations: list[dict[str, Any]] = []

        if row["position_raw"] is not None:
            if trade_price is None:
                raise ValueError(f"Missing trade_price on {row['date_key']}")
            current_long = int(row["gross_long"])
            current_short = int(row["gross_short"])
            long_delta = current_long - previous_long
            short_delta = current_short - previous_short
            avg_long_before = cost.avg_long
            avg_short_before = cost.avg_short

            if long_delta > 0:
                trade_operations.append(
                    {
                        "operation": "buy_long",
                        "quantity": long_delta,
                        "price": trade_price,
                        "notional_point_hand": long_delta * trade_price,
                        "realized_pnl": 0.0,
                    }
                )
                cost.long_cost += long_delta * trade_price
                cost.long_qty += long_delta
            elif long_delta < 0:
                close_qty = -long_delta
                avg_long = cost.avg_long or 0.0
                op_pnl = close_qty * (trade_price - avg_long)
                realized_delta += op_pnl
                trade_operations.append(
                    {
                        "operation": "sell_long",
                        "quantity": close_qty,
                        "price": trade_price,
                        "average_cost": avg_long_before,
                        "notional_point_hand": close_qty * trade_price,
                        "realized_pnl": op_pnl,
                    }
                )
                cost.long_qty -= close_qty
                cost.long_cost = avg_long * cost.long_qty

            if short_delta > 0:
                trade_operations.append(
                    {
                        "operation": "sell_short",
                        "quantity": short_delta,
                        "price": trade_price,
                        "notional_point_hand": short_delta * trade_price,
                        "realized_pnl": 0.0,
                    }
                )
                cost.short_proceeds += short_delta * trade_price
                cost.short_qty += short_delta
            elif short_delta < 0:
                close_qty = -short_delta
                avg_short = cost.avg_short or 0.0
                op_pnl = close_qty * (avg_short - trade_price)
                realized_delta += op_pnl
                trade_operations.append(
                    {
                        "operation": "buy_to_cover_short",
                        "quantity": close_qty,
                        "price": trade_price,
                        "average_cost": avg_short_before,
                        "notional_point_hand": close_qty * trade_price,
                        "realized_pnl": op_pnl,
                    }
                )
                cost.short_qty -= close_qty
                cost.short_proceeds = avg_short * cost.short_qty

            cost.realized_pnl += realized_delta
            previous_long = current_long
            previous_short = current_short
            if row["segment_id"] is not None and realized_delta:
                segment_pnl[row["segment_id"]] = segment_pnl.get(row["segment_id"], 0.0) + realized_delta

        mark_price = row["close_price"] or row["trade_price"] or previous_mark
        if mark_price is None:
            mark_price = 0.0
        previous_mark = mark_price

        unrealized_long = cost.long_qty * (mark_price - (cost.avg_long or mark_price))
        unrealized_short = cost.short_qty * ((cost.avg_short or mark_price) - mark_price)
        unrealized_pnl = unrealized_long + unrealized_short
        equity = cost.realized_pnl + unrealized_pnl
        daily_pnl = equity - previous_equity
        previous_equity = equity
        gross_notional = (row["gross_long"] + row["gross_short"]) * mark_price

        equity_rows.append(
            {
                "date_key": row["date_key"],
                "close_price": row["close_price"],
                "trade_price": row["trade_price"],
                "mark_price": mark_price,
                "segment_id": row["segment_id"],
                "decision_basis_date": row["decision_basis_date"],
                "execution_timing": row["execution_timing"],
                "gross_long": row["gross_long"],
                "gross_short": row["gross_short"],
                "inventory_before": inventory_before,
                "inventory_after": {
                    "gross_long": row["gross_long"],
                    "gross_short": row["gross_short"],
                },
                "long_delta": long_delta,
                "short_delta": short_delta,
                "gross_notional": gross_notional,
                "realized_pnl": cost.realized_pnl,
                "realized_delta": realized_delta,
                "unrealized_pnl": unrealized_pnl,
                "equity": equity,
                "daily_pnl": daily_pnl,
                "trade_raw": row["trade_raw"],
                "trade_operations": trade_operations,
                "position_raw": row["position_raw"],
                "pm_action": row["pm_action"],
            }
        )

    metrics = build_metrics(equity_rows, pm_summary, segment_pnl)
    return equity_rows, metrics


def build_metrics(
    equity_rows: list[dict[str, Any]],
    pm_summary: dict[str, Any],
    segment_pnl: dict[str, float],
) -> dict[str, Any]:
    max_gross_notional = max((row["gross_notional"] for row in equity_rows), default=0.0)
    capital_base = max_gross_notional or 1.0
    daily_returns = [row["daily_pnl"] / capital_base for row in equity_rows if row["close_price"] is not None]
    total_pnl = equity_rows[-1]["equity"] if equity_rows else 0.0
    total_return = total_pnl / capital_base
    years = len(equity_rows) / 365.0 if equity_rows else 0.0
    cagr = (1 + total_return) ** (1 / years) - 1 if years > 0 and total_return > -1 else None
    daily_mean = mean(daily_returns) if daily_returns else 0.0
    daily_std = pstdev(daily_returns) if len(daily_returns) > 1 else 0.0
    sharpe = daily_mean / daily_std * math.sqrt(TRADING_DAYS_PER_YEAR) if daily_std else None

    downside = [min(0.0, item) for item in daily_returns]
    downside_std = math.sqrt(mean([item * item for item in downside])) if downside else 0.0
    sortino = daily_mean / downside_std * math.sqrt(TRADING_DAYS_PER_YEAR) if downside_std else None

    drawdown = calculate_drawdown(equity_rows, capital_base)
    segment_stats = build_segment_stats(pm_summary["segment_summary"], segment_pnl)
    gross_profit = sum(item["pnl"] for item in segment_stats if item["pnl"] > 0)
    gross_loss = sum(item["pnl"] for item in segment_stats if item["pnl"] < 0)
    winning = [item for item in segment_stats if item["pnl"] > 0]
    losing = [item for item in segment_stats if item["pnl"] < 0]
    trade_count = len(segment_stats)
    best_trade = max(segment_stats, key=lambda item: item["pnl"]) if segment_stats else None
    worst_trade = min(segment_stats, key=lambda item: item["pnl"]) if segment_stats else None
    win_rate = len(winning) / trade_count if trade_count else None
    avg_win = gross_profit / len(winning) if winning else 0.0
    avg_loss = gross_loss / len(losing) if losing else 0.0
    payoff_ratio = avg_win / abs(avg_loss) if avg_loss else None
    profit_factor = gross_profit / abs(gross_loss) if gross_loss else None
    expectancy = total_pnl / trade_count if trade_count else None

    return {
        "assumptions": {
            "unit_size": "1 hand = 1 unit in v0.1 PnL arithmetic",
            "shares_per_hand_note": SHARES_PER_HAND_NOTE,
            "transaction_cost": 0,
            "slippage": 0,
            "decision_basis": "previous available close_price from newspaper",
            "execution_timing": "pre-open market order on the next trading day",
            "execution_price": "trade_price, interpreted as the execution day's opening price",
            "mark_to_market": "close_price, or trade_price when close_price is missing",
            "capital_base": capital_base,
            "risk_free_rate": 0,
            "trade_sample": "closed segment",
        },
        "coverage": {
            "daily_rows": len(equity_rows),
            "trading_day_rows": len(daily_returns),
            "segments": trade_count,
        },
        "performance": {
            "total_pnl": total_pnl,
            "capital_base": capital_base,
            "total_return": total_return,
            "cagr": cagr,
            "annualized_volatility": daily_std * math.sqrt(TRADING_DAYS_PER_YEAR),
            "sharpe": sharpe,
            "sortino": sortino,
            "max_drawdown": drawdown["max_drawdown"],
            "max_drawdown_start": drawdown["start"],
            "max_drawdown_end": drawdown["end"],
        },
        "trade_statistics": {
            "trade_count": trade_count,
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "flat_trades": trade_count - len(winning) - len(losing),
            "win_rate": win_rate,
            "gross_profit": gross_profit,
            "gross_loss": gross_loss,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "payoff_ratio": payoff_ratio,
            "profit_factor": profit_factor,
            "expectancy_per_trade": expectancy,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
        },
        "segment_pnl": segment_stats,
    }


def calculate_drawdown(equity_rows: list[dict[str, Any]], capital_base: float) -> dict[str, Any]:
    peak = capital_base
    peak_date = None
    max_drawdown = 0.0
    start = None
    end = None
    for row in equity_rows:
        account_value = capital_base + row["equity"]
        if account_value > peak:
            peak = account_value
            peak_date = row["date_key"]
        drawdown = account_value / peak - 1
        if drawdown < max_drawdown:
            max_drawdown = drawdown
            start = peak_date
            end = row["date_key"]
    return {"max_drawdown": max_drawdown, "start": start, "end": end}


def build_segment_stats(
    segment_summary: list[dict[str, Any]],
    segment_pnl: dict[str, float],
) -> list[dict[str, Any]]:
    rows = []
    for segment in segment_summary:
        segment_id = segment["segment_id"]
        rows.append(
            {
                "segment_id": segment_id,
                "start_date": segment["start_date"],
                "end_date": segment["end_date"],
                "center_side": segment["center_side"],
                "max_gross_long": segment["max_gross_long"],
                "max_gross_short": segment["max_gross_short"],
                "pnl": segment_pnl.get(segment_id, 0.0),
            }
        )
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the original Tachibana v0.1 performance report.")
    parser.add_argument("--data-dir", default="data/pioneer-1975-1976/json")
    parser.add_argument("--out-dir", default="data/pioneer-1975-1976/backtest-v0.1")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    files = [path for path in data_dir.glob("*.json") if path.name[:4].isdigit()]
    if not files:
        raise SystemExit(f"No monthly JSON files found in {data_dir}")

    equity_rows, metrics = run_performance(files)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "equity_curve.jsonl", equity_rows)
    write_json(out_dir / "performance_metrics.json", metrics)
    print(f"wrote {len(equity_rows)} equity rows to {out_dir / 'equity_curve.jsonl'}")
    print(f"wrote performance metrics to {out_dir / 'performance_metrics.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
