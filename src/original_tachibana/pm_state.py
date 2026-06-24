from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class Inventory:
    gross_long: int = 0
    gross_short: int = 0

    @property
    def net_position(self) -> int:
        return self.gross_long - self.gross_short

    @property
    def is_flat(self) -> bool:
        return self.gross_long == 0 and self.gross_short == 0

    @property
    def is_dual(self) -> bool:
        return self.gross_long > 0 and self.gross_short > 0

    @property
    def side(self) -> str:
        if self.is_flat:
            return "none"
        if self.is_dual:
            return "mixed"
        if self.gross_long > 0:
            return "long"
        return "short"


@dataclass
class EngineState:
    inventory: Inventory = Inventory()
    segment_index: int = 0
    active_segment_id: str | None = None
    center_side: str = "none"
    center_size: int = 0
    add_on_size: int = 0
    lock_status: str = "none"
    lock_candidate_size: int = 0
    max_position_step: int = 0


def parse_inventory(raw: str | None) -> Inventory | None:
    if raw is None:
        return None

    text = raw.strip()
    if not text:
        return None
    if text == "0":
        return Inventory()

    normalized = text.replace("-", "—")
    parts = [part.strip() for part in normalized.split("—")]
    if len(parts) != 2:
        raise ValueError(f"Unsupported position_raw format: {raw!r}")

    left_text, right_text = parts
    gross_short = int(left_text) if left_text else 0
    gross_long = int(right_text) if right_text else 0
    return Inventory(gross_long=gross_long, gross_short=gross_short)


def parse_trade_size(raw: str | None) -> int:
    if raw is None:
        return 0
    digits = "".join(char for char in raw if char.isdigit())
    return int(digits) if digits else 0


def date_key(year: int, month: int, day: int) -> str:
    return f"{year:04d}-{month:02d}-{day:02d}"


def next_segment_id(index: int) -> str:
    return f"S{index:03d}"


def classify_transition(
    previous: Inventory,
    current: Inventory,
    state: EngineState,
    has_position_update: bool,
    trade_size: int,
) -> tuple[str, str, bool, bool]:
    reset_after_clear = False

    if not has_position_update:
        return "wait_no_action", "none", False, False

    if current.is_flat and not previous.is_flat:
        state.center_side = "none"
        state.center_size = 0
        state.add_on_size = 0
        state.lock_status = "none"
        state.lock_candidate_size = 0
        state.active_segment_id = None
        state.max_position_step = 0
        return "clear", "one_shot_clear", True, False

    if previous.is_flat and not current.is_flat:
        state.segment_index += 1
        state.active_segment_id = next_segment_id(state.segment_index)
        state.center_side = current.side
        state.center_size = abs(current.net_position)
        state.add_on_size = 0
        state.lock_status = "candidate" if current.is_dual else "none"
        state.lock_candidate_size = min(current.gross_long, current.gross_short)
        state.max_position_step = max(state.max_position_step, trade_size)
        return "inventory_seed", "none", False, False

    if current.is_dual:
        state.lock_status = "candidate"
        state.lock_candidate_size = min(current.gross_long, current.gross_short)
        if previous.is_dual:
            return ("rebalance" if current != previous else "wait_no_action"), "none", False, False
        return "lock_candidate", "none", False, False

    if previous.is_dual and not current.is_dual:
        state.lock_status = "released"
        state.lock_candidate_size = 0
        return "unlock", "unlock_then_clear", False, False

    previous_abs = abs(previous.net_position)
    current_abs = abs(current.net_position)
    if current.side == previous.side and current_abs > previous_abs:
        added = current_abs - previous_abs
        if state.center_side in ("none", "mixed"):
            state.center_side = current.side
            state.center_size = previous_abs if previous_abs else current_abs
        state.add_on_size += added
        step_size = max(added, trade_size)
        previous_max_step = state.max_position_step
        scale_alert = previous_max_step > 0 and step_size >= max(20, previous_max_step * 2)
        state.max_position_step = max(previous_max_step, step_size)
        return "add_on", "none", False, scale_alert

    if current.side == previous.side and current_abs < previous_abs:
        if current_abs == 0:
            return "clear", "one_shot_clear", True, False
        exit_mode = "staged_distribution" if state.add_on_size or previous_abs > state.center_size else "none"
        return "reduce_add_on", exit_mode, False, False

    if current != previous:
        state.center_side = current.side
        state.center_size = current_abs
        state.add_on_size = 0
        return "rebalance", "none", False, False

    return "wait_no_action", "none", False, False


def run_backtest(files: Iterable[Path]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state = EngineState()
    daily_rows: list[dict[str, Any]] = []
    event_log: list[dict[str, Any]] = []
    segment_summary: dict[str, dict[str, Any]] = {}
    last_close_date: str | None = None

    for file_path in sorted(files):
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        year = int(payload["year"])
        month = int(payload["month"])
        symbol = payload["symbol"]

        for row in payload["rows"]:
            current_date_key = date_key(year, month, int(row["day"]))
            raw_inventory = parse_inventory(row.get("position_raw"))
            has_position_update = raw_inventory is not None
            previous_inventory = state.inventory
            previous_segment_id = state.active_segment_id
            current_inventory = raw_inventory if raw_inventory is not None else previous_inventory
            trade_size = parse_trade_size(row.get("trade_raw"))

            pm_action, exit_mode, reset_after_clear, scale_alert = classify_transition(
                previous_inventory,
                current_inventory,
                state,
                has_position_update,
                trade_size,
            )

            state.inventory = current_inventory
            segment_id = previous_segment_id if reset_after_clear else state.active_segment_id
            if segment_id is not None:
                summary = segment_summary.setdefault(
                    segment_id,
                    {
                        "segment_id": segment_id,
                        "start_date": current_date_key,
                        "end_date": None,
                        "max_gross_long": 0,
                        "max_gross_short": 0,
                        "center_side": state.center_side,
                        "center_size": state.center_size,
                        "exit_mode": "none",
                    },
                )
                summary["end_date"] = current_date_key
                summary["max_gross_long"] = max(summary["max_gross_long"], current_inventory.gross_long)
                summary["max_gross_short"] = max(summary["max_gross_short"], current_inventory.gross_short)
                if state.center_side != "none":
                    summary["center_side"] = state.center_side
                    summary["center_size"] = state.center_size
                if exit_mode != "none":
                    summary["exit_mode"] = exit_mode

            output = {
                "date_key": current_date_key,
                "symbol": symbol,
                "close_price": row.get("close_price"),
                "trade_price": row.get("trade_price"),
                "decision_basis_date": last_close_date if row.get("trade_raw") is not None else None,
                "execution_timing": "pre_open_market_order" if row.get("trade_raw") is not None else None,
                "same_day_close_available_at_order": False if row.get("trade_raw") is not None else None,
                "trade_raw": row.get("trade_raw"),
                "position_raw": row.get("position_raw"),
                "gross_long": current_inventory.gross_long,
                "gross_short": current_inventory.gross_short,
                "net_position": current_inventory.net_position,
                "segment_id": segment_id,
                "method_action": infer_method_action(pm_action),
                "pm_action": pm_action,
                "center_side": state.center_side,
                "center_size": state.center_size,
                "add_on_size": state.add_on_size,
                "lock_status": state.lock_status,
                "lock_candidate_size": state.lock_candidate_size,
                "exit_mode": exit_mode,
                "scale_alert": scale_alert,
                "reset_after_clear": reset_after_clear,
                "evidence_level": "fact" if has_position_update else "our_interpretation",
                "source_anchor": [f"{year:04d}-{month:02d}.json"],
            }
            daily_rows.append(output)

            if pm_action != "wait_no_action":
                event_log.append(
                    {
                        "date_key": output["date_key"],
                        "segment_id": segment_id,
                        "pm_action": pm_action,
                        "exit_mode": exit_mode,
                        "gross_long": current_inventory.gross_long,
                        "gross_short": current_inventory.gross_short,
                        "scale_alert": scale_alert,
                    }
                )

            if row.get("close_price") is not None:
                last_close_date = current_date_key

    return daily_rows, {
        "segment_summary": list(segment_summary.values()),
        "pm_event_log": event_log,
        "strong_sample_report": build_strong_sample_report(daily_rows),
        "rule_coverage_report": {
            "automated": [
                "parse_daily_prices",
                "parse_trade_and_position_raw",
                "gross_long_gross_short",
                "clear",
                "reset_after_clear",
                "add_on",
                "lock_candidate",
                "unlock",
                "wait_no_action",
                "scale_alert_candidate",
            ],
            "manual_required": [
                "center_position_final_confirmation",
                "method_action_reason",
                "lock_status_confirmed",
                "profit_protection_final_judgment",
                "reversal_flip_final_confirmation",
                "malf_context_interpretation",
            ],
            "not_backtested_v0_1": [
                "a_share_rules",
                "stock_selection",
                "capital_curve",
                "psychology_automation",
                "weekly_monthly_structure",
                "trade_signal_generation",
            ],
        },
        "manual_review_queue": build_manual_review_queue(daily_rows),
    }


def infer_method_action(pm_action: str) -> str:
    mapping = {
        "inventory_seed": "trend_probe_entry",
        "open_center": "trend_probe_entry",
        "add_on": "trend_confirmation_add",
        "reduce_add_on": "distribution_reduce",
        "reduce_center": "distribution_reduce",
        "lock_candidate": "inventory_rebalance",
        "rebalance": "inventory_rebalance",
        "unlock": "inventory_rebalance",
        "clear": "exit_on_rhythm_failure",
        "reset_after_clear": "exit_on_rhythm_failure",
        "wait_no_action": "wait_no_action",
    }
    return mapping.get(pm_action, "wait_no_action")


def build_manual_review_queue(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for row in rows:
        reasons: list[str] = []
        if row["pm_action"] in {"inventory_seed", "add_on"}:
            reasons.append("center_position_final_confirmation")
        if row["lock_status"] == "candidate":
            reasons.append("lock_status_confirmed")
        if row["exit_mode"] in {"staged_distribution", "one_shot_clear"}:
            reasons.append("profit_protection_or_rhythm_failure")
        if row["scale_alert"]:
            reasons.append("add_on_scale_alert_threshold_review")
        if reasons:
            queue.append(
                {
                    "date_key": row["date_key"],
                    "segment_id": row["segment_id"],
                    "pm_action": row["pm_action"],
                    "reasons": reasons,
                    "source_anchor": row["source_anchor"],
                }
            )
    return queue


def build_strong_sample_report(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    by_date = {row["date_key"]: row for row in rows}
    samples = [
        {
            "sample": "1976-03 reset_after_clear",
            "description": "—12 -> 0 -> —10 should clear, reset, then create a new long inventory seed.",
            "checks": [
                check_row(by_date, "1976-03-24", {"pm_action": "clear", "reset_after_clear": True}),
                check_row(by_date, "1976-03-29", {"pm_action": "inventory_seed", "gross_long": 2}),
            ],
        },
        {
            "sample": "1976-04 lock_candidate",
            "description": "—10 -> 2 — 20 -> 4 — 5 should preserve dual inventory and mark lock candidates.",
            "checks": [
                check_row(
                    by_date,
                    "1976-04-05",
                    {"pm_action": "lock_candidate", "gross_short": 2, "gross_long": 10},
                ),
                check_row(
                    by_date,
                    "1976-04-13",
                    {"pm_action": "rebalance", "gross_short": 2, "gross_long": 20},
                ),
            ],
        },
        {
            "sample": "1976-05 unlock_then_clear",
            "description": "4 — 5 -> 10 — 5 -> 10 — -> 0 should unlock, continue single-side inventory, then clear.",
            "checks": [
                check_row(by_date, "1976-05-10", {"pm_action": "unlock", "gross_short": 10, "gross_long": 0}),
                check_row(by_date, "1976-05-21", {"pm_action": "clear", "reset_after_clear": True}),
            ],
        },
        {
            "sample": "1976-10 center_then_add_on",
            "description": "—10 -> —24 should create a long inventory seed and same-side add-ons.",
            "checks": [
                check_row(by_date, "1976-10-08", {"pm_action": "inventory_seed", "gross_long": 10}),
                check_row(by_date, "1976-10-30", {"pm_action": "add_on", "gross_long": 24}),
            ],
        },
        {
            "sample": "1976-11 add_on_scale_alert_clear",
            "description": "—24 -> —200 -> 0 should flag large add-ons and then clear/reset.",
            "checks": [
                check_row(by_date, "1976-11-09", {"pm_action": "add_on", "scale_alert": True}),
                check_row(by_date, "1976-11-10", {"pm_action": "add_on", "scale_alert": True}),
                check_row(by_date, "1976-11-13", {"pm_action": "clear", "reset_after_clear": True}),
            ],
        },
        {
            "sample": "1976-11 probe_clear_probe_flip_candidate",
            "description": "—5 -> 0 -> —5 -> 35 — should preserve the clear/probe sequence for manual reversal review.",
            "checks": [
                check_row(by_date, "1976-11-17", {"pm_action": "inventory_seed", "gross_long": 5}),
                check_row(by_date, "1976-11-18", {"pm_action": "clear", "reset_after_clear": True}),
                check_row(by_date, "1976-11-19", {"pm_action": "inventory_seed", "gross_long": 5}),
                check_row(by_date, "1976-11-27", {"pm_action": "add_on", "gross_short": 35}),
            ],
            "manual_review_required": ["reversal_flip_final_confirmation", "center_position_final_confirmation"],
        },
        {
            "sample": "1976-12 staged_distribution",
            "description": "35 — -> 150 — -> 100 — -> 50 — -> 0 should add on, flag scale, distribute, then clear.",
            "checks": [
                check_row(by_date, "1976-12-13", {"pm_action": "add_on", "gross_short": 150, "scale_alert": True}),
                check_row(by_date, "1976-12-20", {"pm_action": "reduce_add_on", "exit_mode": "staged_distribution"}),
                check_row(by_date, "1976-12-24", {"pm_action": "clear", "reset_after_clear": True}),
            ],
        },
    ]

    for sample in samples:
        sample["passed"] = all(check["passed"] for check in sample["checks"])
    return samples


def check_row(
    by_date: dict[str, dict[str, Any]],
    date: str,
    expected: dict[str, Any],
) -> dict[str, Any]:
    row = by_date.get(date)
    actual = {key: row.get(key) if row else None for key in expected}
    return {
        "date_key": date,
        "expected": expected,
        "actual": actual,
        "passed": row is not None and actual == expected,
    }


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the minimal original Tachibana PM prototype.")
    parser.add_argument(
        "--data-dir",
        default="data/pioneer-1975-1976/json",
        help="Directory containing monthly Pioneer JSON files.",
    )
    parser.add_argument(
        "--out-dir",
        default="data/pioneer-1975-1976/backtest-v0.1",
        help="Directory for generated prototype outputs.",
    )
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    out_dir = Path(args.out_dir)
    files = [path for path in data_dir.glob("*.json") if path.name[:4].isdigit()]
    if not files:
        raise SystemExit(f"No monthly JSON files found in {data_dir}")

    daily_rows, summary = run_backtest(files)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_dir / "daily_replay.jsonl", daily_rows)
    (out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(f"wrote {len(daily_rows)} daily rows to {out_dir / 'daily_replay.jsonl'}")
    print(f"wrote summary to {out_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
