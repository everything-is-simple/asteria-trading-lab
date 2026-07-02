import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ashare_intake_validator import (
    _audit_stage_reason_consistency,
    audit_ashare_institution_fact_package,
    audit_first_batch_execution_feasibility_gate,
    audit_first_batch_execution_feasibility_outcomes,
    audit_first_batch_execution_policy_archive,
    audit_first_batch_execution_policy_research_agenda,
    audit_first_batch_execution_policy_research_prep,
    audit_first_batch_execution_policy_candidates,
    audit_first_batch_execution_policy_review_merge,
    audit_first_batch_execution_feasibility_verdict_merge,
    audit_first_batch_execution_feasibility_verdicts,
    audit_first_batch_execution_constraint_snapshots,
    audit_first_batch_backtest_input_readiness,
    audit_first_batch_backtest_input_snapshot_drafts,
    audit_first_batch_cognitive_pipeline,
    audit_first_batch_institution_constraint_gate,
    audit_first_batch_institution_feasibility_records,
    audit_first_batch_method_pm_plan_merge,
    audit_first_batch_method_pm_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
    audit_first_batch_front_filter_run,
    audit_first_batch_readiness,
    audit_method_pm_plan_draft_contract,
    validate_intake_package,
)


CANDIDATE_HEADER = [
    "ts_code",
    "symbol_name",
    "board_type",
    "list_date",
    "is_st",
    "is_new_stock_window",
    "data_quality_status",
    "source_ref",
]

SW_HEADER = [
    "ts_code",
    "sw_l1_name",
    "sw_l2_name",
    "valid_from",
    "valid_to",
    "source_ref",
]

DAILY_HEADER = [
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adj_ref",
    "suspension_flag",
    "corporate_action_flag",
    "missing_bar_flag",
]

INSTITUTION_FACT_HEADER = [
    "ts_code",
    "trade_date",
    "is_trading_day",
    "is_suspended",
    "limit_up_price",
    "limit_down_price",
    "close_limit_status",
    "touched_limit_status",
    "board_lot_size",
    "source_ref",
]


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header), *[",".join(row) for row in rows]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_execution_policy_case(
    tmp_path: Path,
    *,
    ts_code: str = "000001.SZ",
    execution_event_type: str = "open_center",
    method_action: str = "trend_probe_entry",
    pm_action: str | None = None,
    feasibility_status: str = "executable",
    verdict_reason: list[str] | None = None,
    blocked_reason: list[str] | None = None,
    carry_forward_required: bool | None = None,
    close_limit_status: str = "unknown",
    touched_limit_status: str = "unknown",
    is_suspended: str = "false",
) -> tuple[Path, Path, Path]:
    sample_id = f"ASHARE-{ts_code}-2026-01-05-2026-01-06"
    plan_dir = tmp_path / "plans"
    plan_dir.mkdir()
    (plan_dir / f"{ts_code}-method-pm-plan.json").write_text(
        json.dumps(
            {
                "ashare_sample_id": sample_id,
                "ts_code": ts_code,
                "method_action": method_action,
                "method_status": "hypothesis",
                "method_reason": ["structure_suitable_but_no_action_yet"],
                "pm_required": pm_action is not None,
                "pm_action": pm_action,
                "execution_intent": "replay_hypothesis_plan",
                "execution_event_type": execution_event_type,
                "method_evidence_ref": ["manual:method-review-001"],
            }
        ),
        encoding="utf-8",
    )
    fact_root = tmp_path / "facts"
    write_csv(
        fact_root / "ashare" / "institution-facts-v0.1" / f"{ts_code}.csv",
        INSTITUTION_FACT_HEADER,
        [[
            ts_code,
            "2026-01-06",
            "true",
            is_suspended,
            "11.77",
            "9.63",
            close_limit_status,
            touched_limit_status,
            "100",
            "unit-test:exchange-calendar-and-price-limit",
        ]],
    )
    review_dir = tmp_path / "execution-verdicts"
    review_dir.mkdir()
    review_payload = {
        "ashare_sample_id": sample_id,
        "ts_code": ts_code,
        "feasibility_status": feasibility_status,
        "verdict_reason": verdict_reason or [f"manual_{feasibility_status}"],
    }
    if blocked_reason is not None:
        review_payload["blocked_reason"] = blocked_reason
    if carry_forward_required is not None:
        review_payload["carry_forward_required"] = carry_forward_required
    (review_dir / f"{ts_code}-execution-feasibility-verdict.json").write_text(
        json.dumps(review_payload),
        encoding="utf-8",
    )
    return plan_dir, fact_root, review_dir


def write_price_limit_relation_evidence(
    relation_root: Path,
    *,
    sample_id: str,
    ts_code: str,
    trade_date: str = "2026-01-06",
    planned_event: str = "add_on",
    method_action: str = "pullback_add",
    relation_status: str = "relation_constrained",
    fill_blocking_status: str = "fill_blocking_unknown",
    limit_proximity: str = "not_near_limit",
) -> Path:
    relation_root.mkdir(parents=True, exist_ok=True)
    path = relation_root / f"{sample_id}.json"
    path.write_text(
        json.dumps(
            {
                "record_type": "ASharePriceLimitEventRelationEvidence",
                "schema_version": "v0.1",
                "ashare_sample_id": sample_id,
                "ts_code": ts_code,
                "trade_date": trade_date,
                "planned_event": planned_event,
                "method_action": method_action,
                "price_limit_event_relation_status": relation_status,
                "price_limit_event_fill_blocking_status": fill_blocking_status,
                "price_limit_event_limit_proximity": limit_proximity,
                "price_limit_event_relation_reason": [
                    "planned_event_intraday_range_far_from_limit_bounds",
                    "planned_event_not_near_limit_supported_by_reviewed_lc5_evidence",
                ],
                "price_limit_event_relation_ref": [
                    "unit-test:reviewed-lc5-evidence",
                    "unit-test:not-near-limit-review",
                ],
                "boundary_warning": [
                    "relation_evidence_is_research_input_not_execution_rule",
                    "do_not_emit_signal_from_relation_evidence",
                    "do_not_infer_trade_accept_from_relation_evidence",
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def write_execution_policy_review_file(
    review_root: Path,
    *,
    sample_id: str,
    ts_code: str,
    candidate_reviews: list[dict[str, object]],
    filename: str | None = None,
) -> Path:
    review_root.mkdir(parents=True, exist_ok=True)
    path = review_root / (filename or f"{sample_id}.json")
    path.write_text(
        json.dumps(
            {
                "ashare_sample_id": sample_id,
                "ts_code": ts_code,
                "candidate_reviews": candidate_reviews,
            }
        ),
        encoding="utf-8",
    )
    return path


__all__ = [name for name in globals() if not name.startswith("__")]
