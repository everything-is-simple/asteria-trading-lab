from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from tachibana_front_filter import (
    audit_backtest_input_gate,
    audit_front_filter_system,
    audit_method_pm_bridge_gate,
    build_qualification_record_draft,
    run_front_filter,
)


REQUIRED_CANDIDATE_FIELDS = [
    "ts_code",
    "symbol_name",
    "board_type",
    "list_date",
    "is_st",
    "is_new_stock_window",
    "data_quality_status",
    "source_ref",
]

REQUIRED_SW_FIELDS = [
    "ts_code",
    "sw_l1_name",
    "sw_l2_name",
    "valid_from",
    "valid_to",
    "source_ref",
]

REQUIRED_DAILY_FIELDS = [
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

REQUIRED_SNAPSHOT_FIELDS = [
    "malf_snapshot_ref",
    "ts_code",
    "window_start",
    "window_end",
    "source_daily_file",
    "generated_at",
    "malf_version",
    "malf_background",
    "wave_range_break_fields",
    "evidence_ref",
    "snapshot_quality_status",
]

REQUIRED_INSTITUTION_FACT_FIELDS = [
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

FORBIDDEN_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "limit_up_strategy",
    "limit_down_strategy",
    "industry_hot_score",
    "liquidity_rank_as_applicability",
}

BOARD_TYPES = {"main", "gem", "star", "bse", "unknown"}
QUALITY_STATUSES = {"ready", "incomplete", "source_missing", "disputed"}
BOOLEAN_VALUES = {"true", "false"}
LIMIT_CLOSE_STATUSES = {"none", "limit_up", "limit_down", "near_limit_up", "near_limit_down", "unknown"}
TOUCHED_LIMIT_STATUSES = {"none", "touched_up", "touched_down", "both", "unknown"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
METHOD_PM_PLAN_DRAFT_FIELDS = [
    "ashare_sample_id",
    "ts_code",
    "method_action",
    "method_status",
    "method_reason",
    "pm_required",
    "pm_action",
    "execution_intent",
    "execution_event_type",
    "method_evidence_ref",
]

INSTITUTION_GATE_FORBIDDEN_FIELDS = {
    "ashare_t1_action",
    "limit_up_strategy",
    "limit_down_strategy",
    "trade_accept",
    "trade_reject",
    "trade_defer",
    "signal_decision",
    "target_position",
    "structure_suitable",
    "rhythm_meaning_override",
    "tachibana_applicability_override",
}

EXECUTION_FEASIBILITY_VERDICT_STATUSES = [
    "not_evaluated",
    "evidence_ready",
    "executable",
    "constrained",
    "blocked",
    "carry_forward_required",
    "blocked_by_fact_review",
]
MANUAL_EXECUTION_FEASIBILITY_VERDICT_STATUSES = [
    "not_evaluated",
    "executable",
    "constrained",
    "blocked",
    "carry_forward_required",
]
MANUAL_EXECUTION_FEASIBILITY_VERDICT_FIELDS = [
    "ashare_sample_id",
    "ts_code",
    "feasibility_status",
    "verdict_reason",
    "blocked_reason",
    "carry_forward_required",
    "evidence_ref",
]
EXECUTION_POLICY_CANDIDATE_TYPES = [
    "t1",
    "price_limit",
    "suspension_resume",
]
MANUAL_EXECUTION_POLICY_REVIEW_STATUSES = [
    "review_required",
    "evidence_incomplete",
    "carry_forward_required",
    "blocked",
]
MANUAL_EXECUTION_POLICY_REVIEW_FIELDS = [
    "ashare_sample_id",
    "ts_code",
    "candidate_reviews",
]
MANUAL_EXECUTION_POLICY_REVIEW_CANDIDATE_FIELDS = [
    "candidate_constraint_type",
    "review_status",
    "review_reason",
    "blocked_reason",
    "evidence_ref",
]


def audit_ashare_institution_fact_package(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    fact_dir = root / "ashare" / "institution-facts-v0.1"
    failed: list[str] = []
    fact_files: list[str] = []
    fact_count = 0

    _require_dir(fact_dir, "ashare/institution-facts-v0.1", failed)
    if fact_dir.exists():
        csv_files = sorted(fact_dir.glob("*.csv"))
        if not csv_files:
            failed.append("empty_dir:ashare/institution-facts-v0.1")
        for fact_file in csv_files:
            _check_institution_fact_file(fact_file, root, failed)
            rows = _read_csv_rows(fact_file)
            fact_count += len(rows)
            try:
                fact_files.append(fact_file.relative_to(root).as_posix())
            except ValueError:
                fact_files.append(str(fact_file))

    result = "pass" if not failed else "blocked"
    return {
        "result": result,
        "institution_fact_status": "ready" if result == "pass" else ("missing" if not fact_dir.exists() else "invalid"),
        "institution_fact_count": fact_count if result == "pass" else 0,
        "institution_fact_files": fact_files if result == "pass" else [],
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:build_execution_constraint_snapshots"
        if result == "pass"
        else "action:repair_institution_fact_package",
        "failed_contract_items": failed,
        "required_fields": REQUIRED_INSTITUTION_FACT_FIELDS,
        "boundary_warning": [
            "institution_facts_are_execution_facts_not_rules",
            "do_not_use_institution_facts_as_structure_qualification",
            "do_not_emit_signal_from_institution_facts",
        ],
    }


def validate_intake_package(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    ashare_dir = root / "ashare"
    candidate_file = ashare_dir / "candidate-universe-v0.1.csv"
    sw_file = ashare_dir / "sw-industry-membership-v0.1.csv"
    daily_dir = ashare_dir / "daily-window-v0.1"
    snapshot_dir = ashare_dir / "malf-snapshots-v0.1"

    failed: list[str] = []
    warnings: list[str] = []

    _require_file(candidate_file, "ashare/candidate-universe-v0.1.csv", failed)
    _require_file(sw_file, "ashare/sw-industry-membership-v0.1.csv", failed)
    _require_dir(daily_dir, "ashare/daily-window-v0.1", failed)
    _require_dir(snapshot_dir, "ashare/malf-snapshots-v0.1", failed)

    if candidate_file.exists():
        _check_csv_file(candidate_file, REQUIRED_CANDIDATE_FIELDS, failed)
        _check_candidate_rows(candidate_file, failed)
    if sw_file.exists():
        _check_csv_file(sw_file, REQUIRED_SW_FIELDS, failed)
        _check_sw_rows(sw_file, failed)
    if daily_dir.exists():
        daily_files = sorted(daily_dir.glob("*.csv"))
        if not daily_files:
            failed.append("empty_dir:ashare/daily-window-v0.1")
        for daily_file in daily_files:
            _check_csv_file(daily_file, REQUIRED_DAILY_FIELDS, failed)
            _check_daily_rows(daily_file, failed)
    if snapshot_dir.exists():
        snapshot_files = sorted(snapshot_dir.glob("*.json"))
        if not snapshot_files:
            failed.append("empty_dir:ashare/malf-snapshots-v0.1")
        for snapshot_file in snapshot_files:
            _check_snapshot_file(snapshot_file, failed)

    if candidate_file.exists() and sw_file.exists() and daily_dir.exists() and snapshot_dir.exists():
        _check_cross_file_consistency(candidate_file, sw_file, daily_dir, snapshot_dir, failed)

    stage_summary = _build_candidate_stage_summary(candidate_file, sw_file, daily_dir, snapshot_dir)
    failed_reason_codes = _map_failed_items_to_reason_codes(failed)
    stage_reason_consistency = _audit_stage_reason_consistency(stage_summary, failed_reason_codes)
    status = _package_status(candidate_file, sw_file, daily_dir, snapshot_dir, failed)
    result = "fail" if failed else ("warn" if warnings else "pass")
    eligible = result == "pass" and status == "ready"

    return {
        "data_root": str(root),
        "ashare_dir": str(ashare_dir),
        "intake_package_status": status,
        "contract_check_result": result,
        "eligible_for_malf_run": eligible,
        "eligible_for_structure_candidate": eligible,
        "eligible_for_tachibana_candidate": False,
        "candidate_stage_summary": stage_summary,
        "stage_reason_consistency": stage_reason_consistency,
        "failed_contract_items": failed,
        "failed_contract_reason_codes": failed_reason_codes,
        "warnings": warnings,
    }


def audit_first_batch_readiness(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    front_filter_system_audit = audit_front_filter_system()
    intake_contract = validate_intake_package(root)
    issues: list[str] = []
    failed_reason_codes = set(intake_contract.get("failed_contract_reason_codes", []))
    stage_summary = intake_contract.get("candidate_stage_summary", {})
    ready_snapshot_index = _ready_snapshot_index(root)
    symbol_index = _candidate_symbol_index(root)
    front_filter_ready_candidates = [
        {
            "ts_code": ts_code,
            "symbol_name": symbol_index.get(ts_code, ""),
            "candidate_stage_after": item.get("candidate_stage_after"),
            "next_action": item.get("next_action"),
            "malf_snapshot_ref": ready_snapshot_index.get(ts_code, {}).get("malf_snapshot_ref"),
            "malf_snapshot_file": ready_snapshot_index.get(ts_code, {}).get("malf_snapshot_file"),
            "ashare_sample_id_suggestion": _ashare_sample_id_suggestion(
                ts_code,
                ready_snapshot_index.get(ts_code, {}).get("window_start"),
                ready_snapshot_index.get(ts_code, {}).get("window_end"),
            ),
            "front_filter_command": _front_filter_command(
                ready_snapshot_index.get(ts_code, {}).get("malf_snapshot_file")
            ),
            "record_draft_command": _record_draft_command(
                ready_snapshot_index.get(ts_code, {}).get("malf_snapshot_file"),
                symbol_index.get(ts_code, ""),
                _ashare_sample_id_suggestion(
                    ts_code,
                    ready_snapshot_index.get(ts_code, {}).get("window_start"),
                    ready_snapshot_index.get(ts_code, {}).get("window_end"),
                ),
            ),
        }
        for ts_code, item in sorted(stage_summary.items())
        if isinstance(item, dict)
        and item.get("candidate_stage_after") == "structure_candidate"
        and item.get("next_action") == "action:run_front_filter"
    ]
    has_front_filter_candidate = any(
        item.get("candidate_stage_after") == "structure_candidate"
        and item.get("next_action") == "action:run_front_filter"
        for item in stage_summary.values()
        if isinstance(item, dict)
    )
    data_ready_for_malf = any(
        item.get("eligible_for_malf_run") is True
        for item in stage_summary.values()
        if isinstance(item, dict)
    )

    if front_filter_system_audit.get("result") != "pass":
        issues.append("first_batch_requires_front_filter_system_audit_pass")
        for audit_name in front_filter_system_audit.get("blocked_audits", []):
            issues.append(f"front_filter_system_audit_issue:{audit_name}")

    if intake_contract.get("contract_check_result") not in {"pass", "warn"}:
        issues.append("first_batch_requires_intake_contract_pass_or_warn")
    if intake_contract.get("eligible_for_malf_run") is not True:
        issues.append("first_batch_requires_eligible_for_malf_run")
    if intake_contract.get("eligible_for_tachibana_candidate") is True:
        issues.append("first_batch_must_not_preapprove_tachibana_candidate")
    if "missing_malf_snapshot" in failed_reason_codes or "malf_snapshot_not_ready" in failed_reason_codes:
        issues.append("first_batch_requires_ready_malf_snapshot")
    if intake_contract.get("contract_check_result") == "pass" and not has_front_filter_candidate:
        issues.append("first_batch_requires_structure_candidate_with_run_front_filter_action")

    first_batch_ready = not issues
    next_action = "action:run_front_filter" if first_batch_ready else "action:repair_intake_package"
    snapshot_only_block = (
        not first_batch_ready
        and data_ready_for_malf
        and "first_batch_requires_ready_malf_snapshot" in issues
        and not {
            "missing_candidate_universe",
            "missing_sw_industry_membership",
            "missing_daily_window",
            "missing_ts_code",
            "duplicate_key_present",
            "invalid_enum_value",
            "invalid_date_value",
            "invalid_boolean_value",
            "invalid_numeric_value",
            "invalid_daily_ohlc",
            "forbidden_field_present",
        }.intersection(failed_reason_codes)
    )
    if snapshot_only_block:
        next_action = "action:prepare_ready_malf_snapshot"

    return {
        "result": "pass" if first_batch_ready else "blocked",
        "first_batch_ready_for_front_filter": first_batch_ready,
        "front_filter_ready_candidate_count": len(front_filter_ready_candidates),
        "front_filter_ready_candidates": front_filter_ready_candidates,
        "institution_adaptation_allowed": False,
        "next_action": next_action,
        "issues": issues,
        "required_audits": [
            "front_filter_system_audit",
            "intake_contract",
        ],
        "front_filter_system_audit": front_filter_system_audit,
        "intake_contract": {
            "intake_package_status": intake_contract["intake_package_status"],
            "contract_check_result": intake_contract["contract_check_result"],
            "eligible_for_malf_run": intake_contract["eligible_for_malf_run"],
            "eligible_for_structure_candidate": intake_contract["eligible_for_structure_candidate"],
            "eligible_for_tachibana_candidate": intake_contract["eligible_for_tachibana_candidate"],
            "stage_reason_consistency": intake_contract["stage_reason_consistency"],
            "failed_contract_items": intake_contract["failed_contract_items"],
            "failed_contract_reason_codes": intake_contract["failed_contract_reason_codes"],
            "warnings": intake_contract["warnings"],
        },
    }


def audit_method_pm_plan_draft_contract(draft: dict[str, Any]) -> dict[str, Any]:
    gate = audit_method_pm_bridge_gate(draft)
    issues = list(gate.get("issues", []))
    method_evidence_ref = draft.get("method_evidence_ref")
    if not isinstance(method_evidence_ref, list) or not method_evidence_ref:
        issues.append("method_pm_plan_requires_method_evidence_ref")
    result = "pass" if not issues else "blocked"
    return {
        "result": result,
        "next_action": "action:build_backtest_input_snapshot" if result == "pass" else "action:method_pm_review",
        "method_pm_bridge_gate": gate,
        "malf_action_backflow_allowed": False,
        "method_pm_auto_generation_allowed": False,
        "required_fields_checked": METHOD_PM_PLAN_DRAFT_FIELDS,
        "issues": _unique_preserve_order(issues),
    }


def audit_first_batch_front_filter_run(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    readiness = audit_first_batch_readiness(root)
    if readiness["result"] != "pass":
        return {
            "result": "blocked",
            "front_filter_run_count": 0,
            "front_filter_results": [],
            "candidate_table_update_allowed": False,
            "institution_adaptation_allowed": False,
            "next_action": readiness["next_action"],
            "issues": readiness["issues"],
            "readiness": readiness,
        }

    results: list[dict[str, Any]] = []
    for candidate in readiness["front_filter_ready_candidates"]:
        snapshot_file = candidate.get("malf_snapshot_file")
        if not snapshot_file:
            continue
        front_filter_report = run_front_filter(root / snapshot_file)
        results.append(
            {
                "ts_code": candidate.get("ts_code"),
                "symbol_name": candidate.get("symbol_name"),
                "ashare_sample_id_suggestion": candidate.get("ashare_sample_id_suggestion"),
                "malf_snapshot_ref": front_filter_report.get("malf_snapshot_ref"),
                "malf_snapshot_file": snapshot_file,
                "front_filter_result": front_filter_report.get("front_filter_result"),
                "candidate_stage_after": front_filter_report.get("candidate_stage_after"),
                "rhythm_meaning": front_filter_report.get("rhythm_meaning"),
                "tachibana_applicability": front_filter_report.get("tachibana_applicability"),
                "qualification_rule_id": front_filter_report.get("qualification_rule_id"),
                "next_action": front_filter_report.get("next_action"),
                "candidate_table_update_allowed": False,
            }
        )

    return {
        "result": "pass",
        "front_filter_run_count": len(results),
        "front_filter_results": results,
        "candidate_table_update_allowed": False,
        "institution_adaptation_allowed": False,
        "next_action": "action:review_record_drafts",
        "issues": [],
        "readiness": readiness,
    }


def audit_first_batch_record_drafts(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    front_filter_run = audit_first_batch_front_filter_run(root)
    if front_filter_run["result"] != "pass":
        return {
            "result": "blocked",
            "record_draft_count": 0,
            "record_drafts": [],
            "candidate_table_update_allowed": False,
            "institution_adaptation_allowed": False,
            "next_action": front_filter_run["next_action"],
            "issues": front_filter_run["issues"],
            "front_filter_run": front_filter_run,
        }

    readiness_candidates = {
        candidate.get("ts_code"): candidate
        for candidate in front_filter_run.get("readiness", {}).get("front_filter_ready_candidates", [])
        if isinstance(candidate, dict)
    }
    drafts: list[dict[str, Any]] = []
    for result in front_filter_run["front_filter_results"]:
        if result.get("front_filter_result") != "pass":
            continue
        if result.get("next_action") != "action:fill_qualification_record":
            continue
        ts_code = result.get("ts_code")
        candidate = readiness_candidates.get(ts_code, {})
        snapshot_file = result.get("malf_snapshot_file")
        if not snapshot_file:
            continue
        front_filter_report = run_front_filter(root / snapshot_file)
        drafts.append(
            build_qualification_record_draft(
                front_filter_report,
                ashare_sample_id=str(result.get("ashare_sample_id_suggestion", "")),
                symbol_name=str(result.get("symbol_name", "")),
                candidate_stage_before=str(candidate.get("candidate_stage_after", "structure_candidate")),
            )
        )

    return {
        "result": "pass",
        "record_draft_count": len(drafts),
        "record_drafts": drafts,
        "candidate_table_update_allowed": False,
        "institution_adaptation_allowed": False,
        "next_action": "action:manual_review_record_drafts",
        "issues": [],
        "front_filter_run": front_filter_run,
    }


def audit_first_batch_sample_table_trial(data_root: str | Path) -> dict[str, Any]:
    record_drafts_report = audit_first_batch_record_drafts(data_root)
    if record_drafts_report["result"] != "pass":
        return {
            "result": "blocked",
            "trial_row_count": 0,
            "trial_rows": [],
            "candidate_table_write_mode": "manual_review_only",
            "candidate_table_update_allowed": False,
            "institution_adaptation_allowed": False,
            "next_action": record_drafts_report["next_action"],
            "issues": record_drafts_report["issues"],
            "record_drafts_report": record_drafts_report,
        }

    trial_rows: list[dict[str, Any]] = []
    for draft in record_drafts_report["record_drafts"]:
        record_consistency = draft.get("record_consistency")
        candidate_table_gate = draft.get("candidate_table_gate")
        if not isinstance(record_consistency, dict) or record_consistency.get("result") != "pass":
            continue
        if not isinstance(candidate_table_gate, dict) or candidate_table_gate.get("result") != "pass":
            continue
        trial_rows.append(_sample_table_trial_row(draft))

    return {
        "result": "pass",
        "trial_row_count": len(trial_rows),
        "trial_rows": trial_rows,
        "candidate_table_write_mode": "manual_review_only",
        "candidate_table_update_allowed": False,
        "institution_adaptation_allowed": False,
        "next_action": "action:manual_trial_fill_candidate_table",
        "issues": [],
        "record_drafts_report": record_drafts_report,
    }


def audit_first_batch_method_pm_readiness(data_root: str | Path) -> dict[str, Any]:
    sample_table_trial = audit_first_batch_sample_table_trial(data_root)
    if sample_table_trial["result"] != "pass":
        return {
            "result": "blocked",
            "method_pm_ready_count": 0,
            "method_pm_review_required_count": 0,
            "method_pm_ready_items": [],
            "method_pm_review_items": [],
            "method_pm_auto_generation_allowed": False,
            "malf_action_backflow_allowed": False,
            "institution_adaptation_allowed": False,
            "next_action": sample_table_trial["next_action"],
            "issues": sample_table_trial["issues"],
            "sample_table_trial": sample_table_trial,
        }

    ready_items: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    for row in sample_table_trial["trial_rows"]:
        gate_record = _method_pm_gate_record_from_trial_row(row)
        gate = audit_method_pm_bridge_gate(gate_record)
        item = _method_pm_review_item(row, gate)
        if gate["result"] == "pass":
            ready_items.append(item)
        else:
            review_items.append(item)

    result = "pass" if ready_items and not review_items else "blocked"
    return {
        "result": result,
        "method_pm_ready_count": len(ready_items),
        "method_pm_review_required_count": len(review_items),
        "method_pm_ready_items": ready_items,
        "method_pm_review_items": review_items,
        "method_pm_auto_generation_allowed": False,
        "malf_action_backflow_allowed": False,
        "institution_adaptation_allowed": False,
        "next_action": "action:build_backtest_input_snapshot" if result == "pass" else "action:method_pm_review",
        "issues": [] if result == "pass" else ["first_batch_requires_independent_method_pm_review"],
        "sample_table_trial": sample_table_trial,
    }


def audit_first_batch_backtest_input_readiness(data_root: str | Path) -> dict[str, Any]:
    method_pm_readiness = audit_first_batch_method_pm_readiness(data_root)
    if method_pm_readiness["result"] != "pass":
        blocked_items = [
            _backtest_input_blocked_item(item)
            for item in method_pm_readiness.get("method_pm_review_items", [])
        ]
        return {
            "result": "blocked",
            "backtest_input_ready_count": 0,
            "backtest_input_blocked_count": len(blocked_items),
            "backtest_input_ready_items": [],
            "backtest_input_blocked_items": blocked_items,
            "backtest_input_snapshot_allowed": False,
            "institution_adaptation_allowed": False,
            "next_action": method_pm_readiness["next_action"],
            "issues": ["first_batch_requires_method_pm_ready_before_backtest_input"],
            "method_pm_readiness": method_pm_readiness,
        }

    ready_items = [
        _backtest_input_ready_item(item)
        for item in method_pm_readiness.get("method_pm_ready_items", [])
    ]
    return {
        "result": "pass",
        "backtest_input_ready_count": len(ready_items),
        "backtest_input_blocked_count": 0,
        "backtest_input_ready_items": ready_items,
        "backtest_input_blocked_items": [],
        "backtest_input_snapshot_allowed": True,
        "institution_adaptation_allowed": False,
        "next_action": "action:build_backtest_input_snapshot",
        "issues": [],
        "method_pm_readiness": method_pm_readiness,
    }


def audit_first_batch_method_pm_plan_merge(data_root: str | Path, plan_dir: str | Path) -> dict[str, Any]:
    method_pm_readiness = audit_first_batch_method_pm_readiness(data_root)
    plan_index = _method_pm_plan_draft_index(Path(plan_dir))
    ready_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    unmatched_items: list[dict[str, Any]] = []

    for review_item in method_pm_readiness.get("method_pm_review_items", []):
        sample_id = str(review_item.get("ashare_sample_id", ""))
        plan = plan_index.get(sample_id)
        if plan is None:
            unmatched_items.append(review_item)
            continue
        contract = audit_method_pm_plan_draft_contract(plan)
        if contract["result"] == "pass":
            ready_items.append(_method_pm_plan_ready_item(plan, contract))
        else:
            blocked_items.append(_method_pm_plan_blocked_item(plan, contract))

    result = "pass" if ready_items and not blocked_items and not unmatched_items else "blocked"
    return {
        "result": result,
        "method_pm_plan_ready_count": len(ready_items),
        "method_pm_plan_blocked_count": len(blocked_items),
        "unmatched_review_count": len(unmatched_items),
        "method_pm_plan_ready_items": ready_items,
        "method_pm_plan_blocked_items": blocked_items,
        "unmatched_review_items": unmatched_items,
        "backtest_input_ready_count": len(ready_items) if result == "pass" else 0,
        "backtest_input_ready_items": [_backtest_input_ready_item(item) for item in ready_items] if result == "pass" else [],
        "backtest_input_snapshot_allowed": result == "pass",
        "institution_adaptation_allowed": False,
        "method_pm_auto_generation_allowed": False,
        "malf_action_backflow_allowed": False,
        "next_action": "action:build_backtest_input_snapshot" if result == "pass" else "action:method_pm_review",
        "issues": [] if result == "pass" else ["first_batch_requires_matching_valid_method_pm_plan"],
        "method_pm_readiness": method_pm_readiness,
    }


def audit_first_batch_backtest_input_snapshot_drafts(data_root: str | Path, plan_dir: str | Path) -> dict[str, Any]:
    merge_report = audit_first_batch_method_pm_plan_merge(data_root, plan_dir)
    if merge_report["result"] != "pass":
        return {
            "result": "blocked",
            "backtest_input_snapshot_count": 0,
            "backtest_input_snapshots": [],
            "backtest_input_snapshot_allowed": False,
            "institution_adaptation_allowed": False,
            "next_action": merge_report["next_action"],
            "issues": merge_report["issues"],
            "method_pm_plan_merge": merge_report,
        }

    sample_table_trial = audit_first_batch_sample_table_trial(data_root)
    trial_index = {
        row.get("ashare_sample_id"): row
        for row in sample_table_trial.get("trial_rows", [])
        if isinstance(row, dict) and row.get("ashare_sample_id")
    }
    plan_index = _method_pm_plan_draft_index(Path(plan_dir))

    snapshots: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    for ready_item in merge_report.get("method_pm_plan_ready_items", []):
        sample_id = ready_item.get("ashare_sample_id")
        row = trial_index.get(sample_id)
        plan = plan_index.get(str(sample_id))
        if row is None or plan is None:
            blocked_items.append(
                {
                    "ashare_sample_id": sample_id,
                    "blocker": "missing_trial_row_or_method_pm_plan",
                    "next_action": "action:method_pm_review",
                }
            )
            continue
        snapshot = _backtest_input_snapshot_draft(row, plan)
        if snapshot["backtest_input_gate_result"] == "pass":
            snapshots.append(snapshot)
        else:
            blocked_items.append(
                {
                    "ashare_sample_id": sample_id,
                    "ts_code": row.get("ts_code"),
                    "blocker": "backtest_input_gate_blocked",
                    "issues": snapshot.get("backtest_input_gate", {}).get("issues", []),
                    "next_action": snapshot.get("backtest_input_gate", {}).get("next_action"),
                }
            )

    result = "pass" if snapshots and not blocked_items else "blocked"
    return {
        "result": result,
        "backtest_input_snapshot_count": len(snapshots),
        "backtest_input_snapshots": snapshots,
        "backtest_input_snapshot_blocked_count": len(blocked_items),
        "backtest_input_snapshot_blocked_items": blocked_items,
        "backtest_input_snapshot_allowed": result == "pass",
        "institution_adaptation_allowed": False,
        "next_action": "action:institution_constraint_gate_review" if result == "pass" else "action:method_pm_review",
        "issues": [] if result == "pass" else ["first_batch_requires_backtest_input_gate_pass"],
        "method_pm_plan_merge": merge_report,
    }


def audit_first_batch_institution_constraint_gate(
    data_root: str | Path,
    plan_dir: str | Path | None,
    *,
    backtest_input_snapshots: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if backtest_input_snapshots is None:
        if plan_dir is None:
            snapshot_report = {
                "result": "blocked",
                "backtest_input_snapshots": [],
                "issues": ["institution_gate_requires_backtest_input_snapshots_or_plan_dir"],
                "next_action": "action:build_backtest_input_snapshot",
            }
        else:
            snapshot_report = audit_first_batch_backtest_input_snapshot_drafts(data_root, plan_dir)
        snapshots = snapshot_report.get("backtest_input_snapshots", [])
    else:
        snapshot_report = {
            "result": "pass" if backtest_input_snapshots else "blocked",
            "backtest_input_snapshots": backtest_input_snapshots,
            "issues": [] if backtest_input_snapshots else ["institution_gate_requires_backtest_input_snapshot"],
            "next_action": "action:institution_constraint_gate_review",
        }
        snapshots = backtest_input_snapshots

    if snapshot_report["result"] != "pass":
        return {
            "result": "blocked",
            "institution_gate_count": 0,
            "institution_gate_blocked_count": 0,
            "institution_gate_items": [],
            "institution_gate_blocked_items": [],
            "institution_constraint_audit_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "next_action": snapshot_report.get("next_action", "action:build_backtest_input_snapshot"),
            "issues": snapshot_report.get("issues", []),
            "backtest_input_snapshot_drafts": snapshot_report,
        }

    gate_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    for snapshot in snapshots:
        gate_item = _institution_constraint_gate_item(snapshot)
        if gate_item["gate_status"] == "pass":
            gate_items.append(gate_item)
        else:
            blocked_items.append(gate_item)

    result = "pass" if gate_items and not blocked_items else "blocked"
    next_action = "action:start_institution_constraint_audit" if result == "pass" else _institution_gate_blocked_next_action(blocked_items)
    return {
        "result": result,
        "institution_gate_count": len(gate_items),
        "institution_gate_blocked_count": len(blocked_items),
        "institution_gate_items": gate_items,
        "institution_gate_blocked_items": blocked_items,
        "institution_constraint_audit_allowed": result == "pass",
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "next_action": next_action,
        "issues": [] if result == "pass" else ["first_batch_requires_clean_backtest_input_before_institution_gate"],
        "backtest_input_snapshot_drafts": snapshot_report,
    }


def audit_first_batch_institution_feasibility_records(
    data_root: str | Path,
    plan_dir: str | Path | None,
) -> dict[str, Any]:
    gate_report = audit_first_batch_institution_constraint_gate(data_root, plan_dir)
    if gate_report["result"] != "pass":
        next_action = _institution_feasibility_blocked_next_action(gate_report)
        return {
            "result": "blocked",
            "institution_feasibility_record_count": 0,
            "institution_feasibility_records": [],
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
            "issues": gate_report["issues"],
            "institution_constraint_gate": gate_report,
        }

    snapshots = gate_report.get("backtest_input_snapshot_drafts", {}).get("backtest_input_snapshots", [])
    snapshot_index = {
        snapshot.get("ashare_sample_id"): snapshot
        for snapshot in snapshots
        if isinstance(snapshot, dict) and snapshot.get("ashare_sample_id")
    }
    records = [
        _institution_feasibility_record(gate_item, snapshot_index.get(gate_item.get("ashare_sample_id"), {}))
        for gate_item in gate_report.get("institution_gate_items", [])
    ]
    return {
        "result": "pass" if records else "blocked",
        "institution_feasibility_record_count": len(records),
        "institution_feasibility_records": records,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:collect_institution_constraint_evidence" if records else "action:start_institution_constraint_audit",
        "issues": [] if records else ["institution_feasibility_requires_gate_items"],
        "institution_constraint_gate": gate_report,
    }


def audit_first_batch_execution_constraint_snapshots(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
) -> dict[str, Any]:
    feasibility_report = audit_first_batch_institution_feasibility_records(data_root, plan_dir)
    if feasibility_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_constraint_snapshot_count": 0,
            "execution_constraint_snapshots": [],
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": feasibility_report["next_action"],
            "issues": feasibility_report["issues"],
            "institution_feasibility_records": feasibility_report,
        }

    fact_report = audit_ashare_institution_fact_package(institution_fact_root)
    if fact_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_constraint_snapshot_count": 0,
            "execution_constraint_snapshots": [],
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": fact_report["next_action"],
            "issues": fact_report["failed_contract_items"],
            "institution_fact_package": fact_report,
            "institution_feasibility_records": feasibility_report,
        }

    fact_rows = _institution_fact_rows(Path(institution_fact_root))
    snapshots: list[dict[str, Any]] = []
    for record in feasibility_report.get("institution_feasibility_records", []):
        planned_date = _planned_event_date_from_feasibility(record, feasibility_report)
        for fact in fact_rows:
            if fact.get("ts_code") != record.get("ts_code"):
                continue
            if planned_date and fact.get("trade_date") != planned_date:
                continue
            snapshots.append(_execution_constraint_snapshot(record, fact))

    result = "pass" if snapshots else "blocked"
    return {
        "result": result,
        "execution_constraint_snapshot_count": len(snapshots),
        "execution_constraint_snapshots": snapshots,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_execution_constraint_snapshots"
        if result == "pass"
        else "action:collect_institution_constraint_evidence",
        "issues": [] if result == "pass" else ["execution_constraint_requires_matching_institution_fact_row"],
        "institution_fact_package": fact_report,
        "institution_feasibility_records": feasibility_report,
    }


def audit_first_batch_execution_feasibility_gate(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
) -> dict[str, Any]:
    snapshot_report = audit_first_batch_execution_constraint_snapshots(data_root, plan_dir, institution_fact_root)
    if snapshot_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_feasibility_gate_count": 0,
            "execution_feasibility_gate_items": [],
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": snapshot_report["next_action"],
            "issues": snapshot_report["issues"],
            "execution_constraint_snapshots": snapshot_report,
        }

    snapshots_by_sample = {
        snapshot.get("ashare_sample_id"): snapshot
        for snapshot in snapshot_report.get("execution_constraint_snapshots", [])
        if isinstance(snapshot, dict) and snapshot.get("ashare_sample_id")
    }
    feasibility_report = snapshot_report.get("institution_feasibility_records", {})
    items = [
        _execution_feasibility_gate_item(record, snapshots_by_sample.get(record.get("ashare_sample_id"), {}))
        for record in feasibility_report.get("institution_feasibility_records", [])
    ]
    result = "pass" if items else "blocked"
    return {
        "result": result,
        "execution_feasibility_gate_count": len(items),
        "execution_feasibility_gate_items": items,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:manual_review_execution_feasibility"
        if result == "pass"
        else "action:review_execution_constraint_snapshots",
        "issues": [] if result == "pass" else ["execution_feasibility_gate_requires_constraint_snapshot"],
        "execution_constraint_snapshots": snapshot_report,
    }


def audit_first_batch_execution_feasibility_verdicts(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
) -> dict[str, Any]:
    gate_report = audit_first_batch_execution_feasibility_gate(data_root, plan_dir, institution_fact_root)
    if gate_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_feasibility_verdict_count": 0,
            "execution_feasibility_verdicts": [],
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": gate_report["next_action"],
            "issues": gate_report["issues"],
            "execution_feasibility_gate": gate_report,
        }

    verdicts = [
        _execution_feasibility_verdict(item)
        for item in gate_report.get("execution_feasibility_gate_items", [])
        if isinstance(item, dict)
    ]
    ready_verdicts = [
        verdict
        for verdict in verdicts
        if verdict.get("evidence_status") == "evidence_ready"
    ]
    result = "pass" if ready_verdicts else "blocked"
    return {
        "result": result,
        "execution_feasibility_verdict_count": len(ready_verdicts),
        "execution_feasibility_verdicts": ready_verdicts,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_execution_feasibility_verdicts"
        if result == "pass"
        else "action:manual_review_execution_feasibility",
        "issues": [] if result == "pass" else ["execution_feasibility_verdict_requires_evidence_ready"],
        "execution_feasibility_gate": gate_report,
    }


def audit_execution_feasibility_verdict_draft_contract(draft: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    required_fields = ["ashare_sample_id", "ts_code", "feasibility_status", "verdict_reason"]
    for field in required_fields:
        if field not in draft:
            issues.append(f"execution_feasibility_verdict_missing_field:{field}")

    unexpected_fields = sorted(set(draft.keys()) - set(MANUAL_EXECUTION_FEASIBILITY_VERDICT_FIELDS))
    for field in unexpected_fields:
        issues.append(f"execution_feasibility_verdict_unexpected_field:{field}")

    forbidden_fields = sorted(FORBIDDEN_FIELDS.intersection(draft.keys()))
    for field in forbidden_fields:
        issues.append(f"execution_feasibility_verdict_forbidden_field:{field}")

    feasibility_status = draft.get("feasibility_status")
    if feasibility_status not in MANUAL_EXECUTION_FEASIBILITY_VERDICT_STATUSES:
        issues.append(f"execution_feasibility_verdict_invalid_status:{feasibility_status}")

    verdict_reason = draft.get("verdict_reason")
    if not isinstance(verdict_reason, list) or not verdict_reason:
        issues.append("execution_feasibility_verdict_requires_verdict_reason")

    blocked_reason = draft.get("blocked_reason")
    if blocked_reason is not None and not isinstance(blocked_reason, list):
        issues.append("execution_feasibility_verdict_requires_blocked_reason_list")

    evidence_ref = draft.get("evidence_ref")
    if evidence_ref is not None and not isinstance(evidence_ref, list):
        issues.append("execution_feasibility_verdict_requires_evidence_ref_list")

    carry_forward_required = draft.get("carry_forward_required")
    if carry_forward_required is not None and not isinstance(carry_forward_required, bool):
        issues.append("execution_feasibility_verdict_requires_carry_forward_required_boolean")

    result = "pass" if not issues else "blocked"
    return {
        "result": result,
        "next_action": "action:review_execution_feasibility_outcome"
        if result == "pass"
        else "action:review_execution_feasibility_verdicts",
        "required_fields_checked": MANUAL_EXECUTION_FEASIBILITY_VERDICT_FIELDS,
        "allowed_manual_statuses": MANUAL_EXECUTION_FEASIBILITY_VERDICT_STATUSES,
        "issues": _unique_preserve_order(issues),
    }


def audit_first_batch_execution_feasibility_verdict_merge(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    review_dir: str | Path,
) -> dict[str, Any]:
    draft_report = audit_first_batch_execution_feasibility_verdicts(data_root, plan_dir, institution_fact_root)
    if draft_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_feasibility_verdict_ready_count": 0,
            "execution_feasibility_verdict_blocked_count": 0,
            "unmatched_review_count": 0,
            "execution_feasibility_verdicts": [],
            "execution_feasibility_verdict_ready_items": [],
            "execution_feasibility_verdict_blocked_items": [],
            "unmatched_review_items": [],
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": draft_report["next_action"],
            "issues": draft_report["issues"],
            "execution_feasibility_verdict_drafts": draft_report,
        }

    review_index = _execution_feasibility_verdict_review_index(Path(review_dir))
    ready_items: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    unmatched_items: list[dict[str, Any]] = []

    for verdict in draft_report.get("execution_feasibility_verdicts", []):
        sample_id = str(verdict.get("ashare_sample_id", ""))
        review = review_index.get(sample_id)
        if review is None:
            unmatched_items.append(verdict)
            continue
        contract = audit_execution_feasibility_verdict_draft_contract(review)
        if contract["result"] != "pass":
            blocked_items.append(_execution_feasibility_verdict_blocked_item(verdict, review, contract))
            continue
        if review.get("ts_code") != verdict.get("ts_code"):
            blocked_items.append(
                _execution_feasibility_verdict_blocked_item(
                    verdict,
                    review,
                    {
                        "issues": ["execution_feasibility_verdict_ts_code_mismatch"],
                        "next_action": "action:review_execution_feasibility_verdicts",
                    },
                )
            )
            continue
        ready_items.append(_execution_feasibility_verdict_ready_item(verdict, review))

    result = "pass" if ready_items and not blocked_items and not unmatched_items else "blocked"
    return {
        "result": result,
        "execution_feasibility_verdict_ready_count": len(ready_items),
        "execution_feasibility_verdict_blocked_count": len(blocked_items),
        "unmatched_review_count": len(unmatched_items),
        "execution_feasibility_verdicts": ready_items if result == "pass" else [],
        "execution_feasibility_verdict_ready_items": ready_items,
        "execution_feasibility_verdict_blocked_items": blocked_items,
        "unmatched_review_items": unmatched_items,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_execution_feasibility_outcome"
        if result == "pass"
        else "action:review_execution_feasibility_verdicts",
        "issues": [] if result == "pass" else ["execution_feasibility_requires_matching_valid_manual_verdict"],
        "execution_feasibility_verdict_drafts": draft_report,
    }


def audit_first_batch_execution_feasibility_outcomes(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    verdict_dir: str | Path,
) -> dict[str, Any]:
    merge_report = audit_first_batch_execution_feasibility_verdict_merge(
        data_root,
        plan_dir,
        institution_fact_root,
        verdict_dir,
    )
    if merge_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_feasibility_outcome_count": 0,
            "execution_feasibility_outcomes": [],
            "outcome_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": merge_report["next_action"],
            "issues": merge_report["issues"],
            "execution_feasibility_verdict_merge": merge_report,
        }

    outcomes: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    for verdict in merge_report.get("execution_feasibility_verdicts", []):
        outcome = _execution_feasibility_outcome_item(verdict)
        if outcome is None:
            blocked_items.append(
                {
                    "ashare_sample_id": verdict.get("ashare_sample_id"),
                    "ts_code": verdict.get("ts_code"),
                    "issues": [f"execution_feasibility_outcome_invalid_status:{verdict.get('feasibility_status')}"],
                    "next_action": "action:review_execution_feasibility_verdicts",
                }
            )
            continue
        outcomes.append(outcome)

    result = "pass" if outcomes and not blocked_items else "blocked"
    return {
        "result": result,
        "execution_feasibility_outcome_count": len(outcomes) if result == "pass" else 0,
        "execution_feasibility_outcomes": outcomes if result == "pass" else [],
        "execution_feasibility_outcome_blocked_items": blocked_items,
        "outcome_status_counts": _status_counts(outcomes) if result == "pass" else {},
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": _execution_feasibility_outcome_report_next_action(outcomes)
        if result == "pass"
        else "action:review_execution_feasibility_verdicts",
        "issues": [] if result == "pass" else ["execution_feasibility_outcome_requires_valid_merged_verdicts"],
        "execution_feasibility_verdict_merge": merge_report,
    }


def audit_first_batch_execution_policy_candidates(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    verdict_dir: str | Path,
) -> dict[str, Any]:
    outcome_report = audit_first_batch_execution_feasibility_outcomes(
        data_root,
        plan_dir,
        institution_fact_root,
        verdict_dir,
    )
    if outcome_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_policy_candidate_count": 0,
            "execution_policy_candidates": [],
            "execution_policy_candidate_blocked_count": 0,
            "execution_policy_candidate_blocked_items": [],
            "candidate_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": outcome_report["next_action"],
            "issues": outcome_report["issues"],
            "execution_feasibility_outcomes_report": outcome_report,
        }

    snapshots_by_sample = _execution_constraint_snapshot_index_from_outcome_report(outcome_report)
    candidates: list[dict[str, Any]] = []
    blocked_items: list[dict[str, Any]] = []
    for outcome in outcome_report.get("execution_feasibility_outcomes", []):
        feasibility_status = str(outcome.get("feasibility_status"))
        if feasibility_status in {"blocked", "carry_forward_required", "not_evaluated"}:
            blocked_items.append(_execution_policy_candidate_blocked_item(outcome))
            continue
        if feasibility_status not in {"executable", "constrained"}:
            blocked_items.append(
                {
                    "ashare_sample_id": outcome.get("ashare_sample_id"),
                    "ts_code": outcome.get("ts_code"),
                    "feasibility_status": feasibility_status,
                    "issues": [f"execution_policy_candidates_invalid_outcome_status:{feasibility_status}"],
                    "next_action": "action:review_execution_feasibility_verdicts",
                }
            )
            continue
        snapshot = snapshots_by_sample.get(str(outcome.get("ashare_sample_id")))
        if snapshot is None:
            blocked_items.append(
                {
                    "ashare_sample_id": outcome.get("ashare_sample_id"),
                    "ts_code": outcome.get("ts_code"),
                    "feasibility_status": feasibility_status,
                    "issues": ["execution_policy_candidates_missing_constraint_snapshot"],
                    "next_action": "action:collect_additional_execution_evidence",
                }
            )
            continue
        candidates.extend(_execution_policy_candidate_items(outcome, snapshot))

    return {
        "result": "pass",
        "execution_policy_candidate_count": len(candidates),
        "execution_policy_candidates": candidates,
        "execution_policy_candidate_blocked_count": len(blocked_items),
        "execution_policy_candidate_blocked_items": blocked_items,
        "candidate_status_counts": _count_by_field(candidates, "candidate_status"),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": _execution_policy_candidate_report_next_action(candidates, blocked_items),
        "issues": [],
        "execution_feasibility_outcomes_report": outcome_report,
    }


def audit_execution_policy_review_draft_contract(draft: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    for field in ["ashare_sample_id", "ts_code", "candidate_reviews"]:
        if field not in draft:
            issues.append(f"execution_policy_review_missing_field:{field}")

    unexpected_fields = sorted(set(draft.keys()) - set(MANUAL_EXECUTION_POLICY_REVIEW_FIELDS))
    for field in unexpected_fields:
        issues.append(f"execution_policy_review_unexpected_field:{field}")

    forbidden_fields = sorted(FORBIDDEN_FIELDS.intersection(draft.keys()))
    for field in forbidden_fields:
        issues.append(f"execution_policy_review_forbidden_field:{field}")

    candidate_reviews = draft.get("candidate_reviews")
    if not isinstance(candidate_reviews, list) or not candidate_reviews:
        issues.append("execution_policy_review_requires_candidate_reviews")
        candidate_reviews = []

    seen_types: set[str] = set()
    for review in candidate_reviews:
        if not isinstance(review, dict):
            issues.append("execution_policy_review_candidate_entry_must_be_object")
            continue
        unexpected_candidate_fields = sorted(
            set(review.keys()) - set(MANUAL_EXECUTION_POLICY_REVIEW_CANDIDATE_FIELDS)
        )
        for field in unexpected_candidate_fields:
            issues.append(f"execution_policy_review_unexpected_candidate_field:{field}")
        forbidden_candidate_fields = sorted(FORBIDDEN_FIELDS.intersection(review.keys()))
        for field in forbidden_candidate_fields:
            issues.append(f"execution_policy_review_forbidden_candidate_field:{field}")
        for field in ["candidate_constraint_type", "review_status", "review_reason"]:
            if field not in review:
                issues.append(f"execution_policy_review_missing_candidate_field:{field}")

        candidate_constraint_type = review.get("candidate_constraint_type")
        if candidate_constraint_type not in EXECUTION_POLICY_CANDIDATE_TYPES:
            issues.append(
                f"execution_policy_review_invalid_candidate_constraint_type:{candidate_constraint_type}"
            )
        elif str(candidate_constraint_type) in seen_types:
            issues.append(
                f"execution_policy_review_duplicate_candidate_constraint_type:{candidate_constraint_type}"
            )
        else:
            seen_types.add(str(candidate_constraint_type))

        review_status = review.get("review_status")
        if review_status not in MANUAL_EXECUTION_POLICY_REVIEW_STATUSES:
            issues.append(f"execution_policy_review_invalid_review_status:{review_status}")

        review_reason = review.get("review_reason")
        if not isinstance(review_reason, list) or not review_reason:
            issues.append("execution_policy_review_requires_review_reason")

        blocked_reason = review.get("blocked_reason")
        if blocked_reason is not None and not isinstance(blocked_reason, list):
            issues.append("execution_policy_review_requires_blocked_reason_list")

        evidence_ref = review.get("evidence_ref")
        if evidence_ref is not None and not isinstance(evidence_ref, list):
            issues.append("execution_policy_review_requires_evidence_ref_list")

    result = "pass" if not issues else "blocked"
    return {
        "result": result,
        "next_action": "action:review_execution_policy_archive"
        if result == "pass"
        else "action:review_execution_policy_candidates",
        "required_fields_checked": MANUAL_EXECUTION_POLICY_REVIEW_FIELDS,
        "required_candidate_fields_checked": MANUAL_EXECUTION_POLICY_REVIEW_CANDIDATE_FIELDS,
        "allowed_candidate_constraint_types": EXECUTION_POLICY_CANDIDATE_TYPES,
        "allowed_review_statuses": MANUAL_EXECUTION_POLICY_REVIEW_STATUSES,
        "issues": _unique_preserve_order(issues),
    }


def audit_first_batch_execution_policy_review_merge(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    review_dir: str | Path,
) -> dict[str, Any]:
    verdict_dir = _execution_feasibility_verdict_dir_for_policy_review(Path(review_dir), Path(plan_dir))
    candidate_report = audit_first_batch_execution_policy_candidates(
        data_root,
        plan_dir,
        institution_fact_root,
        verdict_dir,
    )
    if candidate_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_policy_review_count": 0,
            "execution_policy_reviews": [],
            "execution_policy_review_blocked_count": 0,
            "execution_policy_review_blocked_items": [],
            "execution_policy_review_unmatched_count": 0,
            "execution_policy_review_unmatched_items": [],
            "review_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": candidate_report["next_action"],
            "issues": candidate_report["issues"],
            "execution_policy_candidates_report": candidate_report,
        }

    review_index = _execution_policy_review_index(Path(review_dir))
    review_records: list[dict[str, Any]] = []
    fatal_blocked_items: list[dict[str, Any]] = []
    passthrough_blocked_items = list(candidate_report.get("execution_policy_candidate_blocked_items", []))
    unmatched_items: list[dict[str, Any]] = []
    invalid_samples: set[str] = set()

    candidate_groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidate_report.get("execution_policy_candidates", []):
        if not isinstance(candidate, dict):
            continue
        sample_id = str(candidate.get("ashare_sample_id", ""))
        if sample_id:
            candidate_groups.setdefault(sample_id, []).append(candidate)

    for sample_id, candidates in candidate_groups.items():
        required_candidates = [
            candidate
            for candidate in candidates
            if _execution_policy_candidate_requires_manual_review(candidate)
        ]
        sample_review = review_index.get(sample_id)
        candidate_review_index: dict[str, dict[str, Any]] = {}
        if required_candidates:
            if sample_review is None:
                for candidate in required_candidates:
                    unmatched_items.append(_execution_policy_review_unmatched_item(candidate))
                continue

            contract = audit_execution_policy_review_draft_contract(sample_review)
            if contract["result"] != "pass":
                fatal_blocked_items.append(
                    _execution_policy_review_contract_blocked_item(candidates[0], sample_review, contract)
                )
                invalid_samples.add(sample_id)
                continue
            if sample_review.get("ts_code") != candidates[0].get("ts_code"):
                fatal_blocked_items.append(
                    _execution_policy_review_contract_blocked_item(
                        candidates[0],
                        sample_review,
                        {
                            "issues": ["execution_policy_review_ts_code_mismatch"],
                            "next_action": "action:review_execution_policy_candidates",
                        },
                    )
                )
                invalid_samples.add(sample_id)
                continue
            candidate_review_index = _execution_policy_review_candidate_index(sample_review)

        if sample_id in invalid_samples:
            continue

        for candidate in candidates:
            if candidate.get("candidate_status") == "not_triggered_in_fact_window":
                review_records.append(_execution_policy_auto_review_item(candidate))
                continue
            candidate_constraint_type = str(candidate.get("candidate_constraint_type"))
            manual_review = candidate_review_index.get(candidate_constraint_type)
            if manual_review is None:
                unmatched_items.append(_execution_policy_review_unmatched_item(candidate))
                continue
            review_records.append(_execution_policy_manual_review_item(candidate, manual_review))

    blocked_items = [*fatal_blocked_items, *passthrough_blocked_items]
    result = "pass" if not fatal_blocked_items and not unmatched_items and (review_records or passthrough_blocked_items) else "blocked"
    return {
        "result": result,
        "execution_policy_review_count": len(review_records) if result == "pass" else 0,
        "execution_policy_reviews": review_records if result == "pass" else [],
        "execution_policy_review_blocked_count": len(blocked_items),
        "execution_policy_review_blocked_items": blocked_items,
        "execution_policy_review_unmatched_count": len(unmatched_items),
        "execution_policy_review_unmatched_items": unmatched_items,
        "review_status_counts": _count_by_field(review_records, "review_status") if result == "pass" else {},
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": _execution_policy_review_report_next_action(
            review_records,
            fatal_blocked_items,
            passthrough_blocked_items,
            unmatched_items,
        ),
        "issues": [] if result == "pass" else ["execution_policy_review_requires_matching_valid_manual_review"],
        "execution_policy_candidates_report": candidate_report,
    }


def audit_first_batch_execution_policy_archive(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    review_dir: str | Path,
) -> dict[str, Any]:
    review_report = audit_first_batch_execution_policy_review_merge(
        data_root,
        plan_dir,
        institution_fact_root,
        review_dir,
    )
    if review_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_policy_archive_count": 0,
            "execution_policy_archives": [],
            "execution_policy_archive_blocked_count": 0,
            "execution_policy_archive_blocked_items": [],
            "archive_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": review_report["next_action"],
            "issues": ["execution_policy_archive_requires_valid_execution_policy_reviews"],
            "execution_policy_review_report": review_report,
        }

    archives: list[dict[str, Any]] = []
    blocked_items = list(review_report.get("execution_policy_review_blocked_items", []))
    invalid_statuses: list[dict[str, Any]] = []
    for review in review_report.get("execution_policy_reviews", []):
        archive_item = _execution_policy_archive_item(review)
        if archive_item is None:
            invalid_statuses.append(
                {
                    "ashare_sample_id": review.get("ashare_sample_id"),
                    "ts_code": review.get("ts_code"),
                    "candidate_constraint_type": review.get("candidate_constraint_type"),
                    "issues": [f"execution_policy_archive_invalid_review_status:{review.get('review_status')}"],
                    "next_action": "action:review_execution_policy_archive",
                }
            )
            continue
        archives.append(archive_item)

    if invalid_statuses:
        return {
            "result": "blocked",
            "execution_policy_archive_count": 0,
            "execution_policy_archives": [],
            "execution_policy_archive_blocked_count": len(blocked_items) + len(invalid_statuses),
            "execution_policy_archive_blocked_items": [*blocked_items, *invalid_statuses],
            "archive_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_execution_policy_archive",
            "issues": ["execution_policy_archive_requires_valid_execution_policy_reviews"],
            "execution_policy_review_report": review_report,
        }

    return {
        "result": "pass",
        "execution_policy_archive_count": len(archives),
        "execution_policy_archives": archives,
        "execution_policy_archive_blocked_count": len(blocked_items),
        "execution_policy_archive_blocked_items": blocked_items,
        "archive_status_counts": _count_by_field(archives, "archive_status"),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": _execution_policy_archive_report_next_action(archives, blocked_items),
        "issues": [],
        "execution_policy_review_report": review_report,
    }


def audit_first_batch_execution_policy_research_prep(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    review_dir: str | Path,
) -> dict[str, Any]:
    archive_report = audit_first_batch_execution_policy_archive(
        data_root,
        plan_dir,
        institution_fact_root,
        review_dir,
    )
    if archive_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_policy_research_prep_count": 0,
            "execution_policy_research_preps": [],
            "execution_policy_research_prep_blocked_count": 0,
            "execution_policy_research_prep_blocked_items": [],
            "research_prep_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": archive_report["next_action"],
            "issues": ["execution_policy_research_prep_requires_valid_execution_policy_archive"],
            "execution_policy_archive_report": archive_report,
        }

    preps: list[dict[str, Any]] = []
    blocked_items = list(archive_report.get("execution_policy_archive_blocked_items", []))
    invalid_statuses: list[dict[str, Any]] = []
    for archive in archive_report.get("execution_policy_archives", []):
        prep_item = _execution_policy_research_prep_item(archive)
        if prep_item is None:
            invalid_statuses.append(
                {
                    "ashare_sample_id": archive.get("ashare_sample_id"),
                    "ts_code": archive.get("ts_code"),
                    "candidate_constraint_type": archive.get("candidate_constraint_type"),
                    "issues": [
                        f"execution_policy_research_prep_invalid_archive_status:{archive.get('archive_status')}"
                    ],
                    "next_action": archive.get("next_action", "action:prepare_execution_policy_research"),
                }
            )
            continue
        preps.append(prep_item)

    if invalid_statuses:
        return {
            "result": "blocked",
            "execution_policy_research_prep_count": 0,
            "execution_policy_research_preps": [],
            "execution_policy_research_prep_blocked_count": len(blocked_items) + len(invalid_statuses),
            "execution_policy_research_prep_blocked_items": [*blocked_items, *invalid_statuses],
            "research_prep_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": _execution_policy_research_prep_report_next_action([], [*blocked_items, *invalid_statuses]),
            "issues": ["execution_policy_research_prep_requires_valid_execution_policy_archive"],
            "execution_policy_archive_report": archive_report,
        }

    return {
        "result": "pass",
        "execution_policy_research_prep_count": len(preps),
        "execution_policy_research_preps": preps,
        "execution_policy_research_prep_blocked_count": len(blocked_items),
        "execution_policy_research_prep_blocked_items": blocked_items,
        "research_prep_status_counts": _count_by_field(preps, "research_prep_status"),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": _execution_policy_research_prep_report_next_action(preps, blocked_items),
        "issues": [],
        "execution_policy_archive_report": archive_report,
    }


def _method_pm_plan_draft_index(plan_dir: Path) -> dict[str, dict[str, Any]]:
    if not plan_dir.exists() or not plan_dir.is_dir():
        return {}
    plans: dict[str, dict[str, Any]] = {}
    for path in sorted(plan_dir.glob("*.json")):
        payload = _read_json_object(path)
        if payload is None:
            continue
        sample_id = payload.get("ashare_sample_id")
        if sample_id:
            plans[str(sample_id)] = payload
    return plans


def _method_pm_plan_ready_item(plan: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": plan.get("ashare_sample_id"),
        "ts_code": plan.get("ts_code"),
        "method_action": plan.get("method_action"),
        "pm_required": plan.get("pm_required"),
        "pm_action": plan.get("pm_action"),
        "execution_intent": plan.get("execution_intent"),
        "next_action": contract.get("next_action"),
    }


def _method_pm_plan_blocked_item(plan: dict[str, Any], contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": plan.get("ashare_sample_id"),
        "ts_code": plan.get("ts_code"),
        "method_action": plan.get("method_action"),
        "next_action": contract.get("next_action"),
        "issues": contract.get("issues", []),
    }


def _backtest_input_snapshot_draft(row: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    boundary_warning = _unique_preserve_order(
        [
            *_list_value(row.get("boundary_warning")),
            "do_not_treat_backtest_input_as_signal",
            "do_not_start_institution_adaptation_from_snapshot",
        ]
    )
    method_pm_bridge_gate = audit_method_pm_bridge_gate(plan)
    gate_record = {
        **row,
        "candidate_stage_after": row.get("candidate_stage"),
        "candidate_table_gate": {
            "result": row.get("candidate_table_gate_result"),
            "next_action": "action:fill_candidate_table",
            "issues": [],
        },
        "method_pm_bridge_gate": method_pm_bridge_gate,
        "boundary_warning": boundary_warning,
        "method_action": plan.get("method_action"),
        "method_status": plan.get("method_status"),
        "method_reason": plan.get("method_reason"),
        "pm_required": plan.get("pm_required"),
        "pm_action": plan.get("pm_action"),
        "execution_intent": plan.get("execution_intent"),
        "execution_event_type": plan.get("execution_event_type"),
    }
    gate = audit_backtest_input_gate(gate_record)
    return {
        "adapter_version": "tachibana_backtest_input_v0.1",
        "snapshot_granularity": "event_row",
        "mode": gate.get("mode"),
        "ashare_sample_id": row.get("ashare_sample_id"),
        "sample_id": row.get("ashare_sample_id"),
        "segment_id": None,
        "ts_code": row.get("ts_code"),
        "symbol": row.get("ts_code"),
        "symbol_name": row.get("symbol_name"),
        "bar_dt": row.get("sample_window_end"),
        "timeframe": "daily",
        "source_anchor": _unique_preserve_order(
            [
                str(row.get("malf_snapshot_ref", "")),
                *_list_value(plan.get("method_evidence_ref")),
            ]
        ),
        "candidate_stage": row.get("candidate_stage"),
        "malf_snapshot_ref": row.get("malf_snapshot_ref"),
        "malf_background": row.get("malf_background"),
        "rhythm_meaning": row.get("rhythm_meaning"),
        "meaning_reason": [],
        "meaning_boundary_warning": boundary_warning,
        "qualification_rule_id": row.get("qualification_rule_id"),
        "secondary_rule_ids": [],
        "tachibana_applicability": row.get("tachibana_applicability"),
        "applicability_reason": [],
        "boundary_warning": boundary_warning,
        "evidence_level": row.get("evidence_level"),
        "method_action": plan.get("method_action"),
        "method_status": plan.get("method_status"),
        "method_reason": plan.get("method_reason"),
        "method_evidence_ref": plan.get("method_evidence_ref"),
        "pm_required": plan.get("pm_required"),
        "pm_action": plan.get("pm_action"),
        "execution_intent": plan.get("execution_intent"),
        "execution_event_type": plan.get("execution_event_type"),
        "execution_constraints_ref": None,
        "backtest_notes": [
            "read_only_snapshot_draft",
            "method_pm_plan_reviewed_manually",
            "institution_constraints_not_applied",
        ],
        "candidate_table_gate": gate_record["candidate_table_gate"],
        "method_pm_bridge_gate": method_pm_bridge_gate,
        "backtest_input_gate": gate,
        "backtest_input_gate_result": gate.get("result"),
        "next_action": gate.get("next_action"),
    }


def _list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None or value == "":
        return []
    return [value]


def _institution_constraint_gate_item(snapshot: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    forbidden_fields = sorted(INSTITUTION_GATE_FORBIDDEN_FIELDS.intersection(snapshot.keys()))
    for field in forbidden_fields:
        issues.append(f"institution_gate_forbidden_field:{field}")

    if snapshot.get("backtest_input_gate_result") != "pass":
        issues.append("institution_gate_requires_backtest_input_gate_pass")
    gate = snapshot.get("backtest_input_gate")
    if not isinstance(gate, dict) or gate.get("result") != "pass":
        issues.append("institution_gate_requires_backtest_input_gate_object_pass")
    if snapshot.get("method_pm_bridge_gate", {}).get("result") != "pass":
        issues.append("institution_gate_requires_method_pm_bridge_gate_pass")
    if snapshot.get("rhythm_meaning") not in {"meaningful", "limited"}:
        issues.append("institution_gate_requires_meaningful_or_limited")
    if snapshot.get("tachibana_applicability") not in {"suitable", "conditional"}:
        issues.append("institution_gate_requires_suitable_or_conditional")

    boundary_warning = _unique_preserve_order(
        [
            *_list_value(snapshot.get("boundary_warning")),
            "do_not_define_t1_or_limit_rules_in_gate",
            "do_not_rewrite_structure_from_institution_constraint",
            "do_not_emit_signal_from_institution_gate",
        ]
    )
    gate_status = "pass" if not issues else "blocked"
    return {
        "ashare_institution_gate_id": f"ASHARE-INST-GATE-{snapshot.get('ashare_sample_id', 'UNKNOWN')}-v0.1",
        "ashare_sample_id": snapshot.get("ashare_sample_id"),
        "ts_code": snapshot.get("ts_code"),
        "malf_snapshot_ref": snapshot.get("malf_snapshot_ref"),
        "qualification_rule_id": snapshot.get("qualification_rule_id"),
        "gate_status": gate_status,
        "institution_constraint_need": "execution_feasibility",
        "allowed_constraint_scope": ["execution_feasibility_audit"] if gate_status == "pass" else [],
        "backtest_input_gate_result": snapshot.get("backtest_input_gate_result"),
        "method_pm_bridge_result": snapshot.get("method_pm_bridge_gate", {}).get("result")
        if isinstance(snapshot.get("method_pm_bridge_gate"), dict)
        else None,
        "institution_constraint_audit_allowed": gate_status == "pass",
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "boundary_warning": boundary_warning,
        "next_action": "action:start_institution_constraint_audit"
        if gate_status == "pass"
        else "action:clean_backtest_input_snapshot",
        "issues": issues,
    }


def _institution_gate_blocked_next_action(blocked_items: list[dict[str, Any]]) -> str:
    for item in blocked_items:
        if any(str(issue).startswith("institution_gate_forbidden_field:") for issue in item.get("issues", [])):
            return "action:clean_backtest_input_snapshot"
    return "action:build_backtest_input_snapshot"


def _institution_feasibility_record(gate_item: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    boundary_warning = _unique_preserve_order(
        [
            *_list_value(gate_item.get("boundary_warning")),
            "do_not_convert_pending_evidence_to_rule",
            "do_not_write_execution_constraint_into_structure_fields",
        ]
    )
    return {
        "record_type": "AShareExecutionFeasibilityAudit",
        "ashare_institution_gate_id": gate_item.get("ashare_institution_gate_id"),
        "ashare_sample_id": gate_item.get("ashare_sample_id"),
        "ts_code": gate_item.get("ts_code"),
        "planned_event": snapshot.get("execution_event_type"),
        "method_action": snapshot.get("method_action"),
        "pm_action": snapshot.get("pm_action"),
        "constraint_snapshot_ref": None,
        "executable_status": "pending_constraint_evidence",
        "blocked_reason": ["institution_constraint_evidence_not_loaded"],
        "carry_forward_required": True,
        "allowed_constraint_scope": gate_item.get("allowed_constraint_scope", []),
        "audit_note": "collect A-share institution facts before defining execution constraints",
        "boundary_warning": boundary_warning,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:collect_institution_constraint_evidence",
    }


def _institution_feasibility_blocked_next_action(gate_report: dict[str, Any]) -> str:
    snapshot_report = gate_report.get("backtest_input_snapshot_drafts")
    if isinstance(snapshot_report, dict):
        merge_report = snapshot_report.get("method_pm_plan_merge")
        if isinstance(merge_report, dict):
            method_pm_readiness = merge_report.get("method_pm_readiness")
            if isinstance(method_pm_readiness, dict) and method_pm_readiness.get("next_action"):
                return str(method_pm_readiness["next_action"])
        if snapshot_report.get("next_action"):
            return str(snapshot_report["next_action"])
    return str(gate_report.get("next_action", "action:start_institution_constraint_audit"))


def _institution_fact_rows(data_root: Path) -> list[dict[str, str]]:
    fact_dir = data_root / "ashare" / "institution-facts-v0.1"
    rows: list[dict[str, str]] = []
    if not fact_dir.exists():
        return rows
    for path in sorted(fact_dir.glob("*.csv")):
        rows.extend(_read_csv_rows(path))
    return rows


def _planned_event_date_from_feasibility(record: dict[str, Any], feasibility_report: dict[str, Any]) -> str | None:
    gate_report = feasibility_report.get("institution_constraint_gate", {})
    snapshots = gate_report.get("backtest_input_snapshot_drafts", {}).get("backtest_input_snapshots", [])
    sample_id = record.get("ashare_sample_id")
    for snapshot in snapshots:
        if isinstance(snapshot, dict) and snapshot.get("ashare_sample_id") == sample_id:
            return snapshot.get("bar_dt")
    return None


def _execution_constraint_snapshot(record: dict[str, Any], fact: dict[str, str]) -> dict[str, Any]:
    ts_code = fact.get("ts_code")
    trade_date = fact.get("trade_date")
    constraint_ref = f"ASHARE-CONSTRAINT-{ts_code}-{trade_date}-v0.1"
    boundary_warning = [
        "constraint_snapshot_is_fact_reference_not_execution_rule",
        "do_not_infer_executability_from_constraint_snapshot",
        "do_not_emit_signal_from_constraint_snapshot",
    ]
    return {
        "record_type": "AShareExecutionConstraintSnapshot",
        "constraint_ref": constraint_ref,
        "ashare_sample_id": record.get("ashare_sample_id"),
        "ts_code": ts_code,
        "trade_date": trade_date,
        "constraint_type": _constraint_types_from_fact(fact),
        "affected_execution_event": record.get("planned_event"),
        "evidence_ref": _list_value(fact.get("source_ref")),
        "is_trading_day": fact.get("is_trading_day") == "true",
        "is_suspended": fact.get("is_suspended") == "true",
        "limit_up_price": _optional_float(fact.get("limit_up_price")),
        "limit_down_price": _optional_float(fact.get("limit_down_price")),
        "close_limit_status": fact.get("close_limit_status"),
        "touched_limit_status": fact.get("touched_limit_status"),
        "board_lot_size": _optional_float(fact.get("board_lot_size")),
        "executable_status": "not_evaluated",
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "boundary_warning": boundary_warning,
        "next_action": "action:review_execution_constraint_snapshots",
    }


def _execution_feasibility_gate_item(record: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    boundary_warning = _unique_preserve_order(
        [
            *_list_value(record.get("boundary_warning")),
            *_list_value(snapshot.get("boundary_warning")),
            "do_not_convert_evidence_ready_to_trade_accept",
            "do_not_convert_evidence_ready_to_position_size",
        ]
    )
    has_snapshot = bool(snapshot.get("constraint_ref"))
    return {
        "record_type": "AShareExecutionFeasibilityAudit",
        "ashare_institution_gate_id": record.get("ashare_institution_gate_id"),
        "ashare_sample_id": record.get("ashare_sample_id"),
        "ts_code": record.get("ts_code"),
        "planned_event": record.get("planned_event"),
        "method_action": record.get("method_action"),
        "pm_action": record.get("pm_action"),
        "constraint_snapshot_ref": snapshot.get("constraint_ref"),
        "executable_status": "evidence_ready" if has_snapshot else "blocked_by_fact_review",
        "blocked_reason": [] if has_snapshot else ["execution_constraint_snapshot_missing"],
        "carry_forward_required": False if has_snapshot else True,
        "allowed_constraint_scope": record.get("allowed_constraint_scope", []),
        "audit_note": "constraint evidence is ready for manual execution-feasibility review"
        if has_snapshot
        else "constraint evidence review is blocked",
        "boundary_warning": boundary_warning,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:manual_review_execution_feasibility"
        if has_snapshot
        else "action:review_execution_constraint_snapshots",
    }


def _execution_feasibility_verdict(item: dict[str, Any]) -> dict[str, Any]:
    evidence_status = str(item.get("executable_status", "not_evaluated"))
    if evidence_status != "evidence_ready":
        feasibility_status = "blocked_by_fact_review"
    else:
        feasibility_status = "not_evaluated"
    boundary_warning = _unique_preserve_order(
        [
            *_list_value(item.get("boundary_warning")),
            "manual_verdict_must_not_be_trade_accept",
            "manual_verdict_must_not_set_position_size",
            "manual_verdict_must_not_define_t1_or_limit_strategy",
        ]
    )
    return {
        "record_type": "AShareExecutionFeasibilityVerdict",
        "ashare_institution_gate_id": item.get("ashare_institution_gate_id"),
        "ashare_sample_id": item.get("ashare_sample_id"),
        "ts_code": item.get("ts_code"),
        "planned_event": item.get("planned_event"),
        "method_action": item.get("method_action"),
        "pm_action": item.get("pm_action"),
        "constraint_snapshot_ref": item.get("constraint_snapshot_ref"),
        "evidence_status": evidence_status,
        "feasibility_status": feasibility_status,
        "allowed_feasibility_statuses": EXECUTION_FEASIBILITY_VERDICT_STATUSES,
        "blocked_reason": item.get("blocked_reason", []),
        "carry_forward_required": item.get("carry_forward_required", False),
        "verdict_source": "manual_review_required",
        "verdict_reason": ["awaiting_manual_execution_feasibility_review"]
        if feasibility_status == "not_evaluated"
        else ["execution_fact_review_not_ready"],
        "evidence_ref": _list_value(item.get("constraint_snapshot_ref")),
        "boundary_warning": boundary_warning,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_execution_feasibility_verdicts"
        if feasibility_status == "not_evaluated"
        else "action:review_execution_constraint_snapshots",
    }


def _execution_feasibility_verdict_review_index(review_dir: Path) -> dict[str, dict[str, Any]]:
    if not review_dir.exists() or not review_dir.is_dir():
        return {}
    reviews: dict[str, dict[str, Any]] = {}
    for path in sorted(review_dir.glob("*.json")):
        payload = _read_json_object(path)
        if payload is None:
            continue
        sample_id = payload.get("ashare_sample_id")
        if sample_id:
            reviews[str(sample_id)] = payload
    return reviews


def _execution_feasibility_verdict_ready_item(
    verdict: dict[str, Any],
    review: dict[str, Any],
) -> dict[str, Any]:
    feasibility_status = str(review.get("feasibility_status"))
    carry_forward_required = bool(review.get("carry_forward_required", False))
    if feasibility_status == "carry_forward_required":
        carry_forward_required = True
    next_action = "action:review_execution_feasibility_verdicts"
    if feasibility_status != "not_evaluated":
        next_action = "action:review_execution_feasibility_outcome"
    return {
        **verdict,
        "feasibility_status": feasibility_status,
        "blocked_reason": review.get("blocked_reason", []),
        "carry_forward_required": carry_forward_required,
        "verdict_source": "manual_review",
        "verdict_reason": review.get("verdict_reason", []),
        "evidence_ref": _unique_preserve_order(
            [
                *_list_value(verdict.get("evidence_ref")),
                *_list_value(review.get("evidence_ref")),
            ]
        ),
        "next_action": next_action,
    }


def _execution_feasibility_outcome_item(verdict: dict[str, Any]) -> dict[str, Any] | None:
    feasibility_status = str(verdict.get("feasibility_status", "not_evaluated"))
    next_action_by_status = {
        "executable": "action:review_execution_policy_candidates",
        "constrained": "action:review_execution_policy_candidates",
        "blocked": "action:collect_additional_execution_evidence",
        "carry_forward_required": "action:collect_additional_execution_evidence",
        "not_evaluated": "action:review_execution_feasibility_verdicts",
    }
    outcome_note_by_status = {
        "executable": "execution_fact_outcome_ready_for_policy_candidate_review",
        "constrained": "execution_fact_outcome_requires_policy_constraint_review",
        "blocked": "execution_fact_outcome_blocked_by_current_fact_set",
        "carry_forward_required": "execution_fact_outcome_requires_additional_evidence",
        "not_evaluated": "execution_fact_outcome_still_waiting_manual_verdict",
    }
    next_action = next_action_by_status.get(feasibility_status)
    if next_action is None:
        return None
    boundary_warning = _unique_preserve_order(
        [
            *_list_value(verdict.get("boundary_warning")),
            "execution_outcome_is_not_trade_decision",
            "execution_outcome_must_not_emit_signal",
            "execution_outcome_must_not_set_position",
        ]
    )
    return {
        "record_type": "AShareExecutionFeasibilityOutcome",
        "ashare_institution_gate_id": verdict.get("ashare_institution_gate_id"),
        "ashare_sample_id": verdict.get("ashare_sample_id"),
        "ts_code": verdict.get("ts_code"),
        "planned_event": verdict.get("planned_event"),
        "method_action": verdict.get("method_action"),
        "pm_action": verdict.get("pm_action"),
        "constraint_snapshot_ref": verdict.get("constraint_snapshot_ref"),
        "evidence_status": verdict.get("evidence_status"),
        "feasibility_status": feasibility_status,
        "blocked_reason": verdict.get("blocked_reason", []),
        "carry_forward_required": bool(verdict.get("carry_forward_required", False)),
        "outcome_note": outcome_note_by_status[feasibility_status],
        "outcome_source": "execution_feasibility_verdict_merge",
        "evidence_ref": _list_value(verdict.get("evidence_ref")),
        "boundary_warning": boundary_warning,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": next_action,
    }


def _execution_feasibility_verdict_blocked_item(
    verdict: dict[str, Any],
    review: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ashare_sample_id": verdict.get("ashare_sample_id"),
        "ts_code": verdict.get("ts_code"),
        "feasibility_status": review.get("feasibility_status"),
        "issues": contract.get("issues", []),
        "next_action": contract.get("next_action", "action:review_execution_feasibility_verdicts"),
    }


def _execution_feasibility_outcome_report_next_action(outcomes: list[dict[str, Any]]) -> str:
    statuses = {str(item.get("feasibility_status")) for item in outcomes}
    if "not_evaluated" in statuses:
        return "action:review_execution_feasibility_verdicts"
    if statuses.intersection({"executable", "constrained"}):
        return "action:review_execution_policy_candidates"
    if statuses.intersection({"blocked", "carry_forward_required"}):
        return "action:collect_additional_execution_evidence"
    return "action:review_execution_feasibility_verdicts"


def _execution_constraint_snapshot_index_from_outcome_report(
    outcome_report: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    merge_report = outcome_report.get("execution_feasibility_verdict_merge", {})
    if not isinstance(merge_report, dict):
        return {}
    draft_report = merge_report.get("execution_feasibility_verdict_drafts", {})
    if not isinstance(draft_report, dict):
        return {}
    gate_report = draft_report.get("execution_feasibility_gate", {})
    if not isinstance(gate_report, dict):
        return {}
    snapshot_report = gate_report.get("execution_constraint_snapshots", {})
    if not isinstance(snapshot_report, dict):
        return {}
    snapshots = snapshot_report.get("execution_constraint_snapshots", [])
    if not isinstance(snapshots, list):
        return {}
    return {
        str(snapshot.get("ashare_sample_id")): snapshot
        for snapshot in snapshots
        if isinstance(snapshot, dict) and snapshot.get("ashare_sample_id")
    }


def _execution_policy_candidate_items(
    outcome: dict[str, Any],
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    evidence_ref = _unique_preserve_order(
        [
            *_list_value(outcome.get("evidence_ref")),
            *_list_value(snapshot.get("evidence_ref")),
        ]
    )
    boundary_warning = _unique_preserve_order(
        [
            *_list_value(outcome.get("boundary_warning")),
            *_list_value(snapshot.get("boundary_warning")),
            "execution_policy_candidate_is_not_rule_definition",
            "execution_policy_candidate_must_not_emit_signal",
            "execution_policy_candidate_must_not_set_position",
        ]
    )
    base = {
        "record_type": "AShareExecutionPolicyCandidateAudit",
        "ashare_institution_gate_id": outcome.get("ashare_institution_gate_id"),
        "ashare_sample_id": outcome.get("ashare_sample_id"),
        "ts_code": outcome.get("ts_code"),
        "planned_event": outcome.get("planned_event"),
        "feasibility_status": outcome.get("feasibility_status"),
        "constraint_snapshot_ref": outcome.get("constraint_snapshot_ref"),
        "evidence_ref": evidence_ref,
        "boundary_warning": boundary_warning,
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_execution_policy_candidates",
    }

    t1_required = _planned_event_requires_t1_review(outcome.get("planned_event"))
    price_limit_unknown = snapshot.get("close_limit_status") == "unknown" or snapshot.get("touched_limit_status") == "unknown"
    suspension_required = bool(snapshot.get("is_suspended"))
    return [
        {
            **base,
            "candidate_constraint_type": "t1",
            "candidate_status": "review_required" if t1_required else "not_triggered_in_fact_window",
            "candidate_reason": ["planned_event_requires_t1_review"]
            if t1_required
            else ["planned_event_does_not_trigger_t1_review"],
        },
        {
            **base,
            "candidate_constraint_type": "price_limit",
            "candidate_status": "evidence_incomplete" if price_limit_unknown else "review_required",
            "candidate_reason": ["price_limit_fact_unknown_on_planned_event"]
            if price_limit_unknown
            else ["price_limit_fact_ready_for_candidate_review"],
        },
        {
            **base,
            "candidate_constraint_type": "suspension_resume",
            "candidate_status": "review_required" if suspension_required else "not_triggered_in_fact_window",
            "candidate_reason": ["suspension_or_resume_fact_present_on_planned_event"]
            if suspension_required
            else ["no_suspension_or_resume_fact_in_window"],
        },
    ]


def _execution_policy_review_index(review_dir: Path) -> dict[str, dict[str, Any]]:
    if not review_dir.exists() or not review_dir.is_dir():
        return {}
    reviews: dict[str, dict[str, Any]] = {}
    for path in sorted(review_dir.glob("*.json")):
        payload = _read_json_object(path)
        if payload is None:
            continue
        sample_id = payload.get("ashare_sample_id")
        if sample_id:
            reviews[str(sample_id)] = payload
    return reviews


def _execution_feasibility_verdict_dir_for_policy_review(review_dir: Path, plan_dir: Path) -> Path:
    candidates = [
        review_dir.parent / "execution-verdicts",
        review_dir.parent / "execution-feasibility-verdicts",
        review_dir.parent / "execution-feasibility-verdicts" / review_dir.name,
        plan_dir.parent.parent / "execution-feasibility-verdicts" / plan_dir.name,
    ]
    if "execution-policy-reviews" in review_dir.parts:
        replaced = Path(
            *[
                "execution-feasibility-verdicts" if part == "execution-policy-reviews" else part
                for part in review_dir.parts
            ]
        )
        candidates.insert(0, replaced)
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return review_dir


def _execution_policy_review_candidate_index(review: dict[str, Any]) -> dict[str, dict[str, Any]]:
    candidate_reviews = review.get("candidate_reviews")
    if not isinstance(candidate_reviews, list):
        return {}
    return {
        str(candidate_review.get("candidate_constraint_type")): candidate_review
        for candidate_review in candidate_reviews
        if isinstance(candidate_review, dict) and candidate_review.get("candidate_constraint_type")
    }


def _execution_policy_candidate_requires_manual_review(candidate: dict[str, Any]) -> bool:
    return str(candidate.get("candidate_status")) in {"review_required", "evidence_incomplete"}


def _execution_policy_review_boundary_warning(candidate: dict[str, Any]) -> list[str]:
    return _unique_preserve_order(
        [
            *_list_value(candidate.get("boundary_warning")),
            "execution_policy_review_is_not_rule_definition",
            "execution_policy_review_must_not_emit_signal",
            "execution_policy_review_must_not_set_position",
        ]
    )


def _execution_policy_manual_review_item(
    candidate: dict[str, Any],
    manual_review: dict[str, Any],
) -> dict[str, Any]:
    review_status = str(manual_review.get("review_status"))
    return {
        "record_type": "AShareExecutionPolicyCandidateReview",
        "ashare_institution_gate_id": candidate.get("ashare_institution_gate_id"),
        "ashare_sample_id": candidate.get("ashare_sample_id"),
        "ts_code": candidate.get("ts_code"),
        "planned_event": candidate.get("planned_event"),
        "feasibility_status": candidate.get("feasibility_status"),
        "candidate_constraint_type": candidate.get("candidate_constraint_type"),
        "machine_candidate_status": candidate.get("candidate_status"),
        "review_status": review_status,
        "review_reason": _list_value(manual_review.get("review_reason")),
        "blocked_reason": _list_value(manual_review.get("blocked_reason")),
        "constraint_snapshot_ref": candidate.get("constraint_snapshot_ref"),
        "evidence_ref": _unique_preserve_order(
            [
                *_list_value(candidate.get("evidence_ref")),
                *_list_value(manual_review.get("evidence_ref")),
            ]
        ),
        "review_source": "manual_review",
        "boundary_warning": _execution_policy_review_boundary_warning(candidate),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": _execution_policy_review_item_next_action(review_status),
    }


def _execution_policy_auto_review_item(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "record_type": "AShareExecutionPolicyCandidateReview",
        "ashare_institution_gate_id": candidate.get("ashare_institution_gate_id"),
        "ashare_sample_id": candidate.get("ashare_sample_id"),
        "ts_code": candidate.get("ts_code"),
        "planned_event": candidate.get("planned_event"),
        "feasibility_status": candidate.get("feasibility_status"),
        "candidate_constraint_type": candidate.get("candidate_constraint_type"),
        "machine_candidate_status": candidate.get("candidate_status"),
        "review_status": "carry_forward_required",
        "review_reason": ["candidate_not_triggered_in_fact_window_auto_carry_forward"],
        "blocked_reason": [],
        "constraint_snapshot_ref": candidate.get("constraint_snapshot_ref"),
        "evidence_ref": _list_value(candidate.get("evidence_ref")),
        "review_source": "auto_carry_forward_from_not_triggered_fact_window",
        "boundary_warning": _execution_policy_review_boundary_warning(candidate),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_execution_policy_archive",
    }


def _execution_policy_review_item_next_action(review_status: str) -> str:
    if review_status == "blocked":
        return "action:collect_additional_execution_evidence"
    return "action:review_execution_policy_archive"


def _execution_policy_archive_item(review: dict[str, Any]) -> dict[str, Any] | None:
    review_status = str(review.get("review_status"))
    archive_reason_by_status = {
        "review_required": ["execution_policy_candidate_archived_for_policy_research"],
        "evidence_incomplete": ["execution_policy_candidate_archived_with_incomplete_evidence"],
        "carry_forward_required": ["execution_policy_candidate_archived_for_carry_forward"],
        "blocked": ["execution_policy_candidate_archived_as_blocked"],
    }
    next_action_by_status = {
        "review_required": "action:prepare_execution_policy_research",
        "evidence_incomplete": "action:collect_additional_execution_evidence",
        "carry_forward_required": "action:collect_additional_execution_evidence",
        "blocked": "action:collect_additional_execution_evidence",
    }
    if review_status not in archive_reason_by_status:
        return None
    return {
        "record_type": "AShareExecutionPolicyArchive",
        "ashare_institution_gate_id": review.get("ashare_institution_gate_id"),
        "ashare_sample_id": review.get("ashare_sample_id"),
        "ts_code": review.get("ts_code"),
        "planned_event": review.get("planned_event"),
        "feasibility_status": review.get("feasibility_status"),
        "candidate_constraint_type": review.get("candidate_constraint_type"),
        "machine_candidate_status": review.get("machine_candidate_status"),
        "review_status": review_status,
        "archive_status": review_status,
        "archive_reason": archive_reason_by_status[review_status],
        "blocked_reason": _list_value(review.get("blocked_reason")),
        "constraint_snapshot_ref": review.get("constraint_snapshot_ref"),
        "evidence_ref": _list_value(review.get("evidence_ref")),
        "review_source": review.get("review_source"),
        "archive_source": "execution_policy_review_merge",
        "boundary_warning": _unique_preserve_order(
            [
                *_list_value(review.get("boundary_warning")),
                "execution_policy_archive_is_not_rule_definition",
                "execution_policy_archive_must_not_emit_signal",
                "execution_policy_archive_must_not_set_position",
            ]
        ),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": next_action_by_status[review_status],
    }


def _execution_policy_archive_report_next_action(
    archives: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
) -> str:
    if any(str(item.get("archive_status")) == "review_required" for item in archives):
        return "action:prepare_execution_policy_research"
    if archives or blocked_items:
        return "action:collect_additional_execution_evidence"
    return "action:review_execution_policy_archive"


def _execution_policy_research_prep_item(archive: dict[str, Any]) -> dict[str, Any] | None:
    archive_status = str(archive.get("archive_status"))
    prep_reason_by_status = {
        "review_required": ["execution_policy_candidate_ready_for_research_preparation"],
        "evidence_incomplete": ["execution_policy_candidate_research_preparation_requires_additional_evidence"],
        "carry_forward_required": ["execution_policy_candidate_research_preparation_carry_forward"],
        "blocked": ["execution_policy_candidate_research_preparation_blocked"],
    }
    next_action_by_status = {
        "review_required": "action:prepare_execution_policy_research",
        "evidence_incomplete": "action:collect_additional_execution_evidence",
        "carry_forward_required": "action:collect_additional_execution_evidence",
        "blocked": "action:collect_additional_execution_evidence",
    }
    if archive_status not in prep_reason_by_status:
        return None
    return {
        "record_type": "AShareExecutionPolicyResearchPrep",
        "ashare_institution_gate_id": archive.get("ashare_institution_gate_id"),
        "ashare_sample_id": archive.get("ashare_sample_id"),
        "ts_code": archive.get("ts_code"),
        "planned_event": archive.get("planned_event"),
        "feasibility_status": archive.get("feasibility_status"),
        "candidate_constraint_type": archive.get("candidate_constraint_type"),
        "machine_candidate_status": archive.get("machine_candidate_status"),
        "review_status": archive.get("review_status"),
        "archive_status": archive_status,
        "research_prep_status": archive_status,
        "research_prep_reason": prep_reason_by_status[archive_status],
        "blocked_reason": _list_value(archive.get("blocked_reason")),
        "constraint_snapshot_ref": archive.get("constraint_snapshot_ref"),
        "evidence_ref": _list_value(archive.get("evidence_ref")),
        "review_source": archive.get("review_source"),
        "archive_source": archive.get("archive_source"),
        "research_prep_source": "execution_policy_archive",
        "boundary_warning": _unique_preserve_order(
            [
                *_list_value(archive.get("boundary_warning")),
                "execution_policy_research_prep_is_not_rule_definition",
                "execution_policy_research_prep_must_not_emit_signal",
                "execution_policy_research_prep_must_not_set_position",
            ]
        ),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": next_action_by_status[archive_status],
    }


def _execution_policy_research_prep_report_next_action(
    preps: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
) -> str:
    if any(str(item.get("research_prep_status")) == "review_required" for item in preps):
        return "action:prepare_execution_policy_research"
    if preps or blocked_items:
        return "action:collect_additional_execution_evidence"
    return "action:prepare_execution_policy_research"


def _execution_policy_review_contract_blocked_item(
    candidate: dict[str, Any],
    review: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ashare_sample_id": candidate.get("ashare_sample_id"),
        "ts_code": candidate.get("ts_code"),
        "feasibility_status": candidate.get("feasibility_status"),
        "issues": contract.get("issues", []),
        "next_action": contract.get("next_action", "action:review_execution_policy_candidates"),
        "review_ts_code": review.get("ts_code"),
    }


def _execution_policy_review_unmatched_item(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": candidate.get("ashare_sample_id"),
        "ts_code": candidate.get("ts_code"),
        "candidate_constraint_type": candidate.get("candidate_constraint_type"),
        "machine_candidate_status": candidate.get("candidate_status"),
        "issues": [
            f"execution_policy_review_missing_required_candidate_review:{candidate.get('candidate_constraint_type')}"
        ],
        "next_action": "action:review_execution_policy_candidates",
    }


def _planned_event_requires_t1_review(planned_event: Any) -> bool:
    return str(planned_event or "") not in {"", "hold", "wait", "lock_candidate"}


def _execution_policy_candidate_blocked_item(outcome: dict[str, Any]) -> dict[str, Any]:
    feasibility_status = str(outcome.get("feasibility_status"))
    issue_by_status = {
        "carry_forward_required": "execution_policy_candidates_require_additional_execution_evidence",
        "blocked": "execution_policy_candidates_blocked_by_outcome",
        "not_evaluated": "execution_policy_candidates_require_manual_verdict",
    }
    next_action_by_status = {
        "carry_forward_required": "action:collect_additional_execution_evidence",
        "blocked": "action:collect_additional_execution_evidence",
        "not_evaluated": "action:review_execution_feasibility_verdicts",
    }
    return {
        "ashare_sample_id": outcome.get("ashare_sample_id"),
        "ts_code": outcome.get("ts_code"),
        "feasibility_status": feasibility_status,
        "issues": [issue_by_status.get(feasibility_status, "execution_policy_candidates_invalid_outcome_status")],
        "next_action": next_action_by_status.get(
            feasibility_status,
            "action:review_execution_feasibility_verdicts",
        ),
    }


def _execution_policy_candidate_report_next_action(
    candidates: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
) -> str:
    if candidates:
        return "action:review_execution_policy_candidates"
    statuses = {str(item.get("feasibility_status")) for item in blocked_items}
    if statuses.intersection({"carry_forward_required", "blocked"}):
        return "action:collect_additional_execution_evidence"
    if statuses == {"not_evaluated"}:
        return "action:review_execution_feasibility_verdicts"
    return "action:review_execution_feasibility_verdicts"


def _execution_policy_review_report_next_action(
    review_records: list[dict[str, Any]],
    fatal_blocked_items: list[dict[str, Any]],
    passthrough_blocked_items: list[dict[str, Any]],
    unmatched_items: list[dict[str, Any]],
) -> str:
    if fatal_blocked_items or unmatched_items:
        return "action:review_execution_policy_candidates"
    if review_records:
        return "action:review_execution_policy_archive"
    if passthrough_blocked_items:
        return "action:collect_additional_execution_evidence"
    return "action:review_execution_policy_candidates"


def _count_by_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return _count_by_field(items, "feasibility_status")


def _constraint_types_from_fact(fact: dict[str, str]) -> list[str]:
    types = ["trading_calendar", "price_limit", "board_lot"]
    if fact.get("is_suspended") == "true":
        types.append("suspension")
    return types


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def audit_first_batch_cognitive_pipeline(data_root: str | Path) -> dict[str, Any]:
    readiness = audit_first_batch_readiness(data_root)
    front_filter_run = audit_first_batch_front_filter_run(data_root)
    record_drafts = audit_first_batch_record_drafts(data_root)
    sample_table_trial = audit_first_batch_sample_table_trial(data_root)
    method_pm_readiness = audit_first_batch_method_pm_readiness(data_root)
    backtest_input_readiness = audit_first_batch_backtest_input_readiness(data_root)
    pipeline_summary = {
        "readiness": readiness["result"],
        "front_filter_run": front_filter_run["result"],
        "record_drafts": record_drafts["result"],
        "sample_table_trial": sample_table_trial["result"],
        "method_pm_readiness": method_pm_readiness["result"],
        "backtest_input_readiness": backtest_input_readiness["result"],
    }
    current_blocking_layer = _current_blocking_layer(pipeline_summary)
    result = "pass" if current_blocking_layer is None else "blocked"
    return {
        "result": result,
        "current_blocking_layer": current_blocking_layer,
        "next_action": _pipeline_next_action(
            current_blocking_layer,
            readiness,
            front_filter_run,
            record_drafts,
            sample_table_trial,
            method_pm_readiness,
            backtest_input_readiness,
        ),
        "institution_adaptation_allowed": False,
        "structure_to_institution_transition_allowed": False,
        "pipeline_summary": pipeline_summary,
        "blocking_evidence": _pipeline_blocking_evidence(method_pm_readiness, backtest_input_readiness),
        "issues": [] if result == "pass" else ["pipeline_stops_before_institution_adaptation"],
        "required_sequence": [
            "readiness",
            "front_filter_run",
            "record_drafts",
            "sample_table_trial",
            "method_pm_readiness",
            "backtest_input_readiness",
        ],
    }


def _current_blocking_layer(pipeline_summary: dict[str, str]) -> str | None:
    for layer, result in pipeline_summary.items():
        if result != "pass":
            return layer
    return None


def _pipeline_next_action(
    current_blocking_layer: str | None,
    readiness: dict[str, Any],
    front_filter_run: dict[str, Any],
    record_drafts: dict[str, Any],
    sample_table_trial: dict[str, Any],
    method_pm_readiness: dict[str, Any],
    backtest_input_readiness: dict[str, Any],
) -> str:
    reports = {
        "readiness": readiness,
        "front_filter_run": front_filter_run,
        "record_drafts": record_drafts,
        "sample_table_trial": sample_table_trial,
        "method_pm_readiness": method_pm_readiness,
        "backtest_input_readiness": backtest_input_readiness,
    }
    if current_blocking_layer is None:
        return "action:institution_constraint_gate_review"
    return str(reports[current_blocking_layer].get("next_action", "action:keep_pending"))


def _pipeline_blocking_evidence(
    method_pm_readiness: dict[str, Any],
    backtest_input_readiness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "method_pm_review_required_count": method_pm_readiness.get("method_pm_review_required_count", 0),
        "backtest_input_blocked_count": backtest_input_readiness.get("backtest_input_blocked_count", 0),
        "backtest_input_snapshot_allowed": backtest_input_readiness.get("backtest_input_snapshot_allowed", False),
        "method_pm_auto_generation_allowed": method_pm_readiness.get("method_pm_auto_generation_allowed", False),
        "malf_action_backflow_allowed": method_pm_readiness.get("malf_action_backflow_allowed", False),
    }


def _backtest_input_blocked_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": item.get("ashare_sample_id"),
        "ts_code": item.get("ts_code"),
        "symbol_name": item.get("symbol_name"),
        "candidate_stage": item.get("candidate_stage"),
        "qualification_rule_id": item.get("qualification_rule_id"),
        "blocker": "method_pm_not_ready",
        "method_pm_bridge_result": item.get("method_pm_bridge_result"),
        "next_action": item.get("next_action"),
        "boundary_warning": [
            "backtest_input_requires_independent_method_pm_plan",
            "do_not_build_backtest_input_from_structure_only",
            "do_not_start_institution_adaptation_before_backtest_input",
        ],
    }


def _backtest_input_ready_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": item.get("ashare_sample_id"),
        "ts_code": item.get("ts_code"),
        "symbol_name": item.get("symbol_name"),
        "candidate_stage": item.get("candidate_stage"),
        "qualification_rule_id": item.get("qualification_rule_id"),
        "next_action": "action:build_backtest_input_snapshot",
    }


def _method_pm_gate_record_from_trial_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "candidate_stage_after": row.get("candidate_stage"),
        "pm_required": _pm_required_from_trial_row(row),
        "interface_layer": "tachibana_adapter",
    }


def _pm_required_from_trial_row(row: dict[str, Any]) -> bool:
    rhythm_meaning = row.get("rhythm_meaning")
    qualification_rule_id = row.get("qualification_rule_id")
    if rhythm_meaning == "limited":
        return True
    return qualification_rule_id not in {"Q-ALIVE-CLEAN", "Q-NO-TRADE"}


def _method_pm_review_item(row: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": row.get("ashare_sample_id"),
        "ts_code": row.get("ts_code"),
        "symbol_name": row.get("symbol_name"),
        "candidate_stage": row.get("candidate_stage"),
        "rhythm_meaning": row.get("rhythm_meaning"),
        "tachibana_applicability": row.get("tachibana_applicability"),
        "qualification_rule_id": row.get("qualification_rule_id"),
        "pm_required_from_structure": _pm_required_from_trial_row(row),
        "method_pm_bridge_result": gate.get("result"),
        "missing_method_pm_fields": _missing_method_pm_fields(gate),
        "blocked_reason_codes": gate.get("issues", []),
        "next_action": gate.get("next_action"),
        "boundary_warning": [
            "method_pm_must_be_independent_from_malf",
            "do_not_generate_method_action_from_malf",
            "do_not_generate_pm_action_from_malf",
        ],
    }


def _missing_method_pm_fields(gate: dict[str, Any]) -> list[str]:
    mapping = {
        "method_pm_invalid_method_action:None": "method_action",
        "method_pm_invalid_method_status:None": "method_status",
        "method_pm_requires_method_reason": "method_reason",
        "method_pm_requires_pm_required_boolean": "pm_required",
        "method_pm_requires_pm_action_when_pm_required": "pm_action",
        "method_pm_requires_execution_intent": "execution_intent",
        "method_pm_requires_execution_event_type": "execution_event_type",
    }
    missing: list[str] = []
    for issue in gate.get("issues", []):
        field = mapping.get(issue)
        if field and field not in missing:
            missing.append(field)
    return missing


def _sample_table_trial_row(draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": draft.get("ashare_sample_id"),
        "ts_code": draft.get("ts_code"),
        "symbol_name": draft.get("symbol_name"),
        "sample_window_start": draft.get("sample_window_start"),
        "sample_window_end": draft.get("sample_window_end"),
        "candidate_stage": draft.get("candidate_stage_after"),
        "malf_snapshot_ref": draft.get("malf_snapshot_ref"),
        "malf_background": draft.get("malf_background"),
        "rhythm_meaning": draft.get("rhythm_meaning"),
        "tachibana_applicability": draft.get("tachibana_applicability"),
        "qualification_rule_id": draft.get("qualification_rule_id"),
        "boundary_warning": draft.get("boundary_warning"),
        "evidence_level": draft.get("evidence_level"),
        "next_action": draft.get("next_action"),
        "candidate_table_gate_result": draft.get("candidate_table_gate", {}).get("result")
        if isinstance(draft.get("candidate_table_gate"), dict)
        else None,
        "record_consistency_result": draft.get("record_consistency", {}).get("result")
        if isinstance(draft.get("record_consistency"), dict)
        else None,
    }


def _front_filter_command(malf_snapshot_file: str | None) -> str | None:
    if not malf_snapshot_file:
        return None
    snapshot_path = malf_snapshot_file.replace("/", "\\")
    return f"$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot <data_root>\\{snapshot_path}"


def _record_draft_command(malf_snapshot_file: str | None, symbol_name: str, ashare_sample_id: str) -> str | None:
    front_filter_command = _front_filter_command(malf_snapshot_file)
    if front_filter_command is None:
        return None
    escaped_symbol = symbol_name.replace('"', '\\"')
    return (
        f"{front_filter_command} --record-draft "
        f"--ashare-sample-id {ashare_sample_id} --symbol-name \"{escaped_symbol}\""
    )


def _ashare_sample_id_suggestion(ts_code: str, window_start: str | None, window_end: str | None) -> str:
    if window_start and window_end:
        return f"ASHARE-{ts_code}-{window_start}-{window_end}"
    return f"ASHARE-{ts_code}-<window>"


def _candidate_symbol_index(data_root: Path) -> dict[str, str]:
    candidate_file = data_root / "ashare" / "candidate-universe-v0.1.csv"
    if not candidate_file.exists():
        return {}
    return {
        row.get("ts_code", ""): row.get("symbol_name", "")
        for row in _read_csv_rows(candidate_file)
        if row.get("ts_code", "")
    }


def _ready_snapshot_index(data_root: Path) -> dict[str, dict[str, str]]:
    snapshot_dir = data_root / "ashare" / "malf-snapshots-v0.1"
    index: dict[str, dict[str, str]] = {}
    if not snapshot_dir.exists():
        return index
    for snapshot_file in sorted(snapshot_dir.glob("*.json")):
        payload = _read_json_object(snapshot_file)
        if payload is None or payload.get("snapshot_quality_status") != "ready":
            continue
        ts_code = str(payload.get("ts_code", ""))
        if not ts_code or ts_code in index:
            continue
        try:
            relative_path = snapshot_file.relative_to(data_root).as_posix()
        except ValueError:
            relative_path = str(snapshot_file)
        index[ts_code] = {
            "malf_snapshot_ref": str(payload.get("malf_snapshot_ref", "")),
            "malf_snapshot_file": relative_path,
            "window_start": str(payload.get("window_start", "")),
            "window_end": str(payload.get("window_end", "")),
        }
    return index


def _require_file(path: Path, label: str, failed: list[str]) -> None:
    if not path.is_file():
        failed.append(f"missing_file:{label}")


def _require_dir(path: Path, label: str, failed: list[str]) -> None:
    if not path.is_dir():
        failed.append(f"missing_dir:{label}")


def _check_csv_file(path: Path, required_fields: list[str], failed: list[str]) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames or []
    except UnicodeDecodeError:
        failed.append(f"invalid_encoding:{path.name}")
        return

    _check_required_fields(path, header, required_fields, failed)
    _check_forbidden_fields(header, failed)


def _check_candidate_rows(path: Path, failed: list[str]) -> None:
    rows = _read_csv_rows(path)
    _check_duplicate_keys(path, rows, ["ts_code"], failed)
    for row in rows:
        _check_enum(path, "board_type", row.get("board_type", ""), BOARD_TYPES, failed)
        _check_date(path, "list_date", row.get("list_date", ""), failed)
        _check_boolean(path, "is_st", row.get("is_st", ""), failed)
        _check_boolean(path, "is_new_stock_window", row.get("is_new_stock_window", ""), failed)
        _check_enum(path, "data_quality_status", row.get("data_quality_status", ""), QUALITY_STATUSES, failed)
        if row.get("data_quality_status", "") == "ready":
            for field in ["board_type", "list_date", "is_st", "is_new_stock_window", "source_ref"]:
                if not row.get(field, ""):
                    failed.append(f"missing_ready_field:{path.name}:{field}:{row.get('ts_code', '')}")


def _check_sw_rows(path: Path, failed: list[str]) -> None:
    rows = _read_csv_rows(path)
    _check_duplicate_keys(path, rows, ["ts_code", "valid_from"], failed)
    for row in rows:
        valid_from = row.get("valid_from", "")
        valid_to = row.get("valid_to", "")
        _check_date(path, "valid_from", valid_from, failed)
        if valid_to:
            _check_date(path, "valid_to", valid_to, failed)
            if _is_date(valid_from) and _is_date(valid_to) and valid_to < valid_from:
                failed.append(f"invalid_date_order:{path.name}:{valid_from}>{valid_to}")


def _check_daily_rows(path: Path, failed: list[str]) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except UnicodeDecodeError:
        return

    if not rows:
        failed.append(f"empty_file:{path.name}")
        return

    _check_duplicate_keys(path, rows, ["ts_code", "trade_date"], failed)
    previous_date = ""
    for index, row in enumerate(rows, start=2):
        trade_date = row.get("trade_date", "")
        if not _is_date(trade_date):
            failed.append(f"invalid_date:{path.name}:trade_date:{trade_date}")
        if previous_date and trade_date <= previous_date:
            failed.append(f"daily_date_not_ascending:{path.name}:line_{index}")
        previous_date = trade_date

        try:
            open_price = float(row.get("open", ""))
            high_price = float(row.get("high", ""))
            low_price = float(row.get("low", ""))
            close_price = float(row.get("close", ""))
        except ValueError:
            failed.append(f"invalid_ohlc:{path.name}:line_{index}")
            continue

        if low_price > min(open_price, close_price) or high_price < max(open_price, close_price):
            failed.append(f"invalid_ohlc:{path.name}:line_{index}")

        for field in ["open", "high", "low", "close", "volume", "amount"]:
            _check_non_negative_number(path, field, row.get(field, ""), index, failed)
        for field in ["suspension_flag", "corporate_action_flag", "missing_bar_flag"]:
            _check_boolean(path, field, row.get(field, ""), failed, line=index)


def _check_snapshot_file(path: Path, failed: list[str]) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        failed.append(f"invalid_json:{path.name}")
        return

    if not isinstance(payload, dict):
        failed.append(f"invalid_json_object:{path.name}")
        return

    _check_required_fields(path, list(payload.keys()), REQUIRED_SNAPSHOT_FIELDS, failed)
    _check_forbidden_fields(list(payload.keys()), failed)
    _check_date(path, "window_start", str(payload.get("window_start", "")), failed)
    _check_date(path, "window_end", str(payload.get("window_end", "")), failed)
    _check_enum(path, "snapshot_quality_status", str(payload.get("snapshot_quality_status", "")), QUALITY_STATUSES, failed)


def _check_cross_file_consistency(
    candidate_file: Path,
    sw_file: Path,
    daily_dir: Path,
    snapshot_dir: Path,
    failed: list[str],
) -> None:
    candidate_codes = _read_csv_codes(candidate_file)
    for ts_code in _read_csv_codes(sw_file):
        if ts_code and ts_code not in candidate_codes:
            failed.append(f"orphan_sw_ts_code:{ts_code}")

    daily_ranges: dict[str, tuple[str, str]] = {}
    for daily_file in sorted(daily_dir.glob("*.csv")):
        file_code = daily_file.stem
        rows = _read_csv_rows(daily_file)
        row_codes = {row.get("ts_code", "") for row in rows if row.get("ts_code", "")}
        if file_code not in candidate_codes:
            failed.append(f"orphan_daily_ts_code:{file_code}")
        for row_code in sorted(row_codes):
            if row_code != file_code:
                failed.append(f"daily_filename_ts_code_mismatch:{daily_file.name}:{row_code}")
        dates = sorted(row.get("trade_date", "") for row in rows if row.get("trade_date", ""))
        if dates:
            daily_ranges[file_code] = (dates[0], dates[-1])

    for snapshot_file in sorted(snapshot_dir.glob("*.json")):
        payload = _read_json_object(snapshot_file)
        if payload is None:
            continue
        ts_code = str(payload.get("ts_code", ""))
        if ts_code and ts_code not in candidate_codes:
            failed.append(f"orphan_snapshot_ts_code:{ts_code}")

        source_daily_file = str(payload.get("source_daily_file", ""))
        source_path = snapshot_file.parent.parent / source_daily_file
        if not source_path.is_file():
            failed.append(f"snapshot_source_daily_missing:{snapshot_file.name}:{source_daily_file}")

        range_code = source_path.stem if source_path.suffix == ".csv" else ts_code
        daily_range = daily_ranges.get(range_code)
        window_start = str(payload.get("window_start", ""))
        window_end = str(payload.get("window_end", ""))
        if daily_range is None or window_start < daily_range[0] or window_end > daily_range[1] or window_start > window_end:
            failed.append(f"snapshot_window_outside_daily_range:{snapshot_file.name}")


def _build_candidate_stage_summary(
    candidate_file: Path,
    sw_file: Path,
    daily_dir: Path,
    snapshot_dir: Path,
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    candidate_codes = sorted(_read_csv_codes(candidate_file)) if candidate_file.exists() else []
    sw_codes = _read_csv_codes(sw_file) if sw_file.exists() else set()
    daily_codes = {path.stem for path in daily_dir.glob("*.csv")} if daily_dir.exists() else set()
    ready_snapshot_codes = _read_ready_snapshot_codes(snapshot_dir) if snapshot_dir.exists() else set()

    for ts_code in candidate_codes:
        failed_reason_codes: list[str] = []
        rule_match_reason: list[str] = []
        applicability_reason: list[str] = []
        boundary_warning: list[str] = []
        has_industry = ts_code in sw_codes
        has_daily = ts_code in daily_codes
        has_ready_snapshot = ts_code in ready_snapshot_codes

        if not has_industry:
            failed_reason_codes.append("missing_industry_label")
            rule_match_reason.append("blocked_by_missing_industry_label")
            applicability_reason.append("no_industry_label")
        if not has_daily:
            failed_reason_codes.append("missing_daily_window")
            rule_match_reason.append("blocked_by_missing_daily_window")
            applicability_reason.append("no_daily_window")
        if not has_ready_snapshot:
            failed_reason_codes.append("missing_malf_snapshot")
            rule_match_reason.append("blocked_by_missing_malf_snapshot")
            applicability_reason.append("no_ready_malf_snapshot")
            boundary_warning.append("do_not_upgrade_without_malf_snapshot")

        eligible_for_malf_run = has_industry and has_daily
        if has_ready_snapshot and eligible_for_malf_run:
            candidate_stage_after = "structure_candidate"
            next_action = "action:run_front_filter"
            applicability_reason.append("no_qualification_rule")
            boundary_warning.append("do_not_upgrade_ready_snapshot_without_front_filter")
        elif candidate_file.exists():
            candidate_stage_after = "universe_candidate"
            next_action = "action:complete_industry_and_daily_window"
        else:
            candidate_stage_after = "unknown"
            next_action = "action:repair_data"

        blocking_reasons = _unique_preserve_order([*failed_reason_codes, *rule_match_reason, *boundary_warning])

        summary[ts_code] = {
            "candidate_stage_after": candidate_stage_after,
            "eligible_for_malf_run": eligible_for_malf_run,
            "tachibana_applicability": "unknown",
            "failed_contract_reason_codes": failed_reason_codes,
            "rule_match_reason": rule_match_reason,
            "applicability_reason": applicability_reason,
            "boundary_warning": boundary_warning,
            "blocking_reasons": blocking_reasons,
            "next_action": next_action,
        }

    return summary


def _audit_stage_reason_consistency(
    stage_summary: dict[str, dict[str, Any]],
    failed_reason_codes: list[str],
) -> dict[str, Any]:
    issues: list[str] = []
    top_level_failed = set(failed_reason_codes)

    for ts_code, item in stage_summary.items():
        stage = item.get("candidate_stage_after", "unknown")
        eligible_for_malf = bool(item.get("eligible_for_malf_run", False))
        applicability = item.get("tachibana_applicability", "unknown")
        next_action = item.get("next_action", "")
        item_failed = set(item.get("failed_contract_reason_codes", []))
        boundary_warning = set(item.get("boundary_warning", []))

        if stage in {"structure_candidate", "tachibana_candidate"} and not eligible_for_malf:
            issues.append(f"stage_without_malf_run:{ts_code}:{stage}")
        if stage == "tachibana_candidate":
            issues.append(f"stage_skips_front_filter:{ts_code}")
        if applicability != "unknown":
            issues.append(f"tachibana_applicability_decided_before_front_filter:{ts_code}:{applicability}")
        if next_action and not str(next_action).startswith("action:"):
            issues.append(f"next_action_missing_action_prefix:{ts_code}:{next_action}")
        if "missing_malf_snapshot" in item_failed and "do_not_upgrade_without_malf_snapshot" not in boundary_warning:
            issues.append(f"missing_malf_snapshot_without_boundary_warning:{ts_code}")

        summary_scoped_codes = {"missing_industry_label", "missing_daily_window", "missing_malf_snapshot"}
        unexplained_codes = item_failed - top_level_failed - summary_scoped_codes
        for code in sorted(unexplained_codes):
            issues.append(f"stage_reason_not_in_top_level:{ts_code}:{code}")

    return {
        "result": "fail" if issues else "pass",
        "issues": issues,
    }


def _check_required_fields(path: Path, actual: list[str], required: list[str], failed: list[str]) -> None:
    actual_set = set(actual)
    for field in required:
        if field not in actual_set:
            failed.append(f"missing_field:{path.name}:{field}")


def _map_failed_items_to_reason_codes(failed_items: list[str]) -> list[str]:
    codes: list[str] = []
    for item in failed_items:
        if item == "missing_file:ashare/candidate-universe-v0.1.csv":
            codes.append("missing_candidate_universe")
        elif item == "missing_file:ashare/sw-industry-membership-v0.1.csv":
            codes.append("missing_sw_industry_membership")
        elif item in {"missing_dir:ashare/daily-window-v0.1", "empty_dir:ashare/daily-window-v0.1"}:
            codes.append("missing_daily_window")
        elif item in {"missing_dir:ashare/malf-snapshots-v0.1", "empty_dir:ashare/malf-snapshots-v0.1"}:
            codes.append("missing_malf_snapshot")
        elif item.startswith("missing_field:"):
            codes.extend(_missing_field_reason_codes(item))
        elif item.startswith("missing_ready_field:"):
            codes.extend(_missing_ready_field_reason_codes(item))
        elif item.startswith("missing_key:"):
            codes.append("missing_ts_code")
        elif item.startswith("duplicate_key:"):
            codes.append("duplicate_key_present")
        elif item.startswith("invalid_enum:"):
            codes.append("invalid_enum_value")
            if item.endswith(":snapshot_quality_status:bad_status") or ":snapshot_quality_status:" in item:
                codes.append("malf_snapshot_not_ready")
        elif item.startswith("invalid_date:") or item.startswith("invalid_date_order:") or item.startswith("daily_date_not_ascending:"):
            codes.append("invalid_date_value")
        elif item.startswith("invalid_boolean:"):
            codes.append("invalid_boolean_value")
        elif item.startswith("invalid_number:") or item.startswith("negative_number:"):
            codes.append("invalid_numeric_value")
        elif item.startswith("invalid_ohlc:"):
            codes.append("invalid_daily_ohlc")
        elif item.startswith("forbidden_field:"):
            codes.append("forbidden_field_present")
        elif item.startswith("orphan_sw_ts_code:"):
            codes.append("missing_industry_label")
        elif item.startswith("orphan_daily_ts_code:") or item.startswith("daily_filename_ts_code_mismatch:"):
            codes.append("missing_daily_window")
        elif item.startswith("orphan_snapshot_ts_code:") or item.startswith("snapshot_source_daily_missing:"):
            codes.append("missing_malf_snapshot")
        elif item.startswith("snapshot_window_outside_daily_range:"):
            codes.append("malf_snapshot_window_mismatch")
        elif item.startswith("invalid_json:") or item.startswith("invalid_json_object:"):
            codes.append("malf_snapshot_not_ready")
        elif item.startswith("invalid_encoding:"):
            codes.append("source_disrupted")
    return _unique_preserve_order(codes)


def _missing_field_reason_codes(item: str) -> list[str]:
    parts = item.split(":")
    if len(parts) < 3:
        return []
    filename = parts[1]
    field = parts[2]
    if filename == "candidate-universe-v0.1.csv":
        return _candidate_missing_field_reason(field)
    if filename == "sw-industry-membership-v0.1.csv":
        return ["missing_industry_label"]
    if filename.endswith(".csv"):
        return ["missing_daily_window"]
    if filename.endswith(".json"):
        return ["missing_malf_snapshot"]
    return []


def _missing_ready_field_reason_codes(item: str) -> list[str]:
    parts = item.split(":")
    if len(parts) < 3:
        return []
    return _candidate_missing_field_reason(parts[2])


def _candidate_missing_field_reason(field: str) -> list[str]:
    mapping = {
        "ts_code": ["missing_ts_code"],
        "symbol_name": ["missing_symbol_name"],
        "board_type": ["missing_board_type"],
        "list_date": ["missing_list_date"],
        "is_st": ["missing_st_flag"],
        "is_new_stock_window": ["missing_new_stock_window"],
        "source_ref": ["missing_source_ref"],
    }
    return mapping.get(field, [])


def _check_forbidden_fields(fields: list[str], failed: list[str]) -> None:
    for field in fields:
        if field in FORBIDDEN_FIELDS:
            item = f"forbidden_field:{field}"
            if item not in failed:
                failed.append(item)


def _check_institution_fact_file(path: Path, data_root: Path, failed: list[str]) -> None:
    _check_csv_file(path, REQUIRED_INSTITUTION_FACT_FIELDS, failed)
    rows = _read_csv_rows(path)
    _check_duplicate_keys(path, rows, ["ts_code", "trade_date"], failed)
    _check_forbidden_institution_fact_fields(path, rows, failed)
    expected_code = path.stem
    for line_number, row in enumerate(rows, start=2):
        ts_code = row.get("ts_code", "")
        if ts_code != expected_code:
            failed.append(f"institution_fact_filename_ts_code_mismatch:{path.name}:line_{line_number}")
        _check_date(path, "trade_date", row.get("trade_date", ""), failed)
        _check_boolean(path, "is_trading_day", row.get("is_trading_day", ""), failed, line=line_number)
        _check_boolean(path, "is_suspended", row.get("is_suspended", ""), failed, line=line_number)
        _check_optional_non_negative_number(path, "limit_up_price", row.get("limit_up_price", ""), line_number, failed)
        _check_optional_non_negative_number(path, "limit_down_price", row.get("limit_down_price", ""), line_number, failed)
        _check_non_negative_number(path, "board_lot_size", row.get("board_lot_size", ""), line_number, failed)
        _check_enum(path, "close_limit_status", row.get("close_limit_status", ""), LIMIT_CLOSE_STATUSES, failed)
        _check_enum(path, "touched_limit_status", row.get("touched_limit_status", ""), TOUCHED_LIMIT_STATUSES, failed)
        if not row.get("source_ref"):
            failed.append(f"missing_ready_field:{path.name}:source_ref:line_{line_number}")


def _check_forbidden_institution_fact_fields(path: Path, rows: list[dict[str, str]], failed: list[str]) -> None:
    fields: set[str] = set()
    for row in rows:
        fields.update(row.keys())
    for field in sorted(fields.intersection(FORBIDDEN_FIELDS.union(INSTITUTION_GATE_FORBIDDEN_FIELDS))):
        failed.append(f"forbidden_field:{path.name}:{field}")


def _check_duplicate_keys(path: Path, rows: list[dict[str, str]], fields: list[str], failed: list[str]) -> None:
    seen: set[tuple[str, ...]] = set()
    key_label = "+".join(fields)
    for row in rows:
        key = tuple(row.get(field, "") for field in fields)
        if any(not value for value in key):
            failed.append(f"missing_key:{path.name}:{key_label}")
            continue
        if key in seen:
            failed.append(f"duplicate_key:{path.name}:{key_label}:{'+'.join(key)}")
        seen.add(key)


def _check_enum(path: Path, field: str, value: str, allowed: set[str], failed: list[str]) -> None:
    if value not in allowed:
        failed.append(f"invalid_enum:{path.name}:{field}:{value}")


def _check_boolean(path: Path, field: str, value: str, failed: list[str], line: int | None = None) -> None:
    if value not in BOOLEAN_VALUES:
        suffix = f":line_{line}" if line is not None else f":{value}"
        failed.append(f"invalid_boolean:{path.name}:{field}{suffix}")


def _check_date(path: Path, field: str, value: str, failed: list[str]) -> None:
    if not _is_date(value):
        failed.append(f"invalid_date:{path.name}:{field}:{value}")


def _check_non_negative_number(path: Path, field: str, value: str, line: int, failed: list[str]) -> None:
    try:
        number = float(value)
    except ValueError:
        failed.append(f"invalid_number:{path.name}:{field}:line_{line}")
        return
    if number < 0:
        failed.append(f"negative_number:{path.name}:{field}:line_{line}")


def _check_optional_non_negative_number(path: Path, field: str, value: str, line: int, failed: list[str]) -> None:
    if value == "":
        return
    _check_non_negative_number(path, field, value, line, failed)


def _is_date(value: str) -> bool:
    return bool(DATE_PATTERN.match(value))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        return []


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _read_csv_codes(path: Path) -> set[str]:
    return {row.get("ts_code", "") for row in _read_csv_rows(path) if row.get("ts_code", "")}


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _read_ready_snapshot_codes(snapshot_dir: Path) -> set[str]:
    codes: set[str] = set()
    for snapshot_file in snapshot_dir.glob("*.json"):
        payload = _read_json_object(snapshot_file)
        if payload is None:
            continue
        if payload.get("snapshot_quality_status") == "ready":
            codes.add(str(payload.get("ts_code", "")))
    return {code for code in codes if code}


def _package_status(candidate_file: Path, sw_file: Path, daily_dir: Path, snapshot_dir: Path, failed: list[str]) -> str:
    required_paths = [candidate_file, sw_file, daily_dir, snapshot_dir]
    present_count = sum(1 for path in required_paths if path.exists())
    if present_count == 0:
        return "missing"
    if failed:
        return "partial"
    return "ready"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate the read-only A-share MALF/Tachibana intake package.")
    parser.add_argument("--root", required=True, help="Formal data root, for example Z:\\asteria-trading-labs-data")
    parser.add_argument(
        "--audit-first-batch-readiness",
        action="store_true",
        help="Aggregate front-filter system audit and intake contract readiness without upgrading candidates.",
    )
    parser.add_argument(
        "--audit-first-batch-front-filter-run",
        action="store_true",
        help="Run the front filter over readiness-approved first-batch candidates without writing sample tables.",
    )
    parser.add_argument(
        "--audit-first-batch-record-drafts",
        action="store_true",
        help="Build read-only qualification record drafts for first-batch candidates that passed the front filter.",
    )
    parser.add_argument(
        "--audit-first-batch-sample-table-trial",
        action="store_true",
        help="Map gate-passed first-batch record drafts into read-only candidate sample-table trial rows.",
    )
    parser.add_argument(
        "--audit-first-batch-method-pm-readiness",
        action="store_true",
        help="Audit whether first-batch structural candidates have independent Method/PM plans without MALF backflow.",
    )
    parser.add_argument(
        "--audit-first-batch-backtest-input-readiness",
        action="store_true",
        help="Audit whether first-batch candidates can build Backtest Input without bypassing Method/PM.",
    )
    parser.add_argument(
        "--audit-first-batch-cognitive-pipeline",
        action="store_true",
        help="Summarize the full first-batch cognitive pipeline and current blocking layer.",
    )
    parser.add_argument(
        "--audit-method-pm-plan-draft",
        help="Audit one manual Method/PM plan draft JSON file without generating actions from MALF.",
    )
    parser.add_argument(
        "--audit-first-batch-method-pm-plan-merge",
        help="Merge a directory of manual Method/PM plan draft JSON files into first-batch readiness.",
    )
    parser.add_argument(
        "--audit-first-batch-backtest-input-snapshots",
        help="Build read-only Backtest Input snapshot drafts from valid first-batch Method/PM plan JSON files.",
    )
    parser.add_argument(
        "--audit-first-batch-institution-constraint-gate",
        help="Audit whether first-batch Backtest Input snapshots may start institution-constraint review without defining rules.",
    )
    parser.add_argument(
        "--audit-first-batch-institution-feasibility-records",
        help="Build read-only A-share execution feasibility audit records after the institution constraint gate.",
    )
    parser.add_argument(
        "--audit-institution-fact-package",
        action="store_true",
        help="Validate read-only A-share institution fact CSVs without defining execution rules.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-constraint-snapshots",
        help="Build read-only execution constraint snapshot drafts from first-batch plans and institution facts.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-gate",
        help="Mark execution feasibility audits as evidence-ready when constraint snapshots are linked, without trade decisions.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-verdicts",
        help="Build manual-review execution feasibility verdict drafts without trade decisions or position sizing.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-verdict-merge",
        help="Merge a directory of manual execution feasibility verdict JSON files into the audit-only verdict layer.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-feasibility-outcomes",
        help="Build read-only execution feasibility outcome records from merged manual verdicts.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-candidates",
        help="Build read-only execution policy candidate audit records from execution feasibility outcomes.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-review-merge",
        help="Merge per-sample manual execution policy review JSON files into read-only candidate review records.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-archive",
        help="Build read-only execution policy archive records from merged candidate reviews.",
    )
    parser.add_argument(
        "--audit-first-batch-execution-policy-research-prep",
        help="Build read-only execution policy research prep records from execution policy archive results.",
    )
    parser.add_argument(
        "--method-pm-plan-dir",
        help="Method/PM plan directory required by execution-feasibility verdict merge.",
    )
    parser.add_argument(
        "--institution-fact-root",
        help="Institution fact package root for execution constraint snapshot drafts; defaults to --root.",
    )
    args = parser.parse_args(argv)

    if args.audit_first_batch_execution_policy_research_prep:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:prepare_execution_policy_research",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_research_prep"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_research_prep(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_research_prep,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_policy_archive:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_policy_archive",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_archive"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_archive(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_archive,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_policy_review_merge:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_policy_candidates",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_review_merge"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_review_merge(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_review_merge,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_policy_candidates:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_feasibility_verdicts",
                "issues": ["missing_method_pm_plan_dir_for_execution_policy_candidates"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_policy_candidates(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_policy_candidates,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_outcomes:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_feasibility_verdicts",
                "issues": ["missing_method_pm_plan_dir_for_execution_feasibility_outcomes"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_outcomes(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_feasibility_outcomes,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_verdict_merge:
        if not args.method_pm_plan_dir:
            report = {
                "result": "blocked",
                "next_action": "action:review_execution_feasibility_verdicts",
                "issues": ["missing_method_pm_plan_dir_for_execution_feasibility_verdict_merge"],
            }
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_verdict_merge(
            args.root,
            args.method_pm_plan_dir,
            fact_root,
            args.audit_first_batch_execution_feasibility_verdict_merge,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_verdicts:
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_verdicts(
            args.root,
            args.audit_first_batch_execution_feasibility_verdicts,
            fact_root,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_feasibility_gate:
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_feasibility_gate(
            args.root,
            args.audit_first_batch_execution_feasibility_gate,
            fact_root,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_execution_constraint_snapshots:
        fact_root = args.institution_fact_root or args.root
        report = audit_first_batch_execution_constraint_snapshots(
            args.root,
            args.audit_first_batch_execution_constraint_snapshots,
            fact_root,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_institution_fact_package:
        report = audit_ashare_institution_fact_package(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_institution_feasibility_records:
        report = audit_first_batch_institution_feasibility_records(args.root, args.audit_first_batch_institution_feasibility_records)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_institution_constraint_gate:
        report = audit_first_batch_institution_constraint_gate(args.root, args.audit_first_batch_institution_constraint_gate)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_backtest_input_snapshots:
        report = audit_first_batch_backtest_input_snapshot_drafts(args.root, args.audit_first_batch_backtest_input_snapshots)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_method_pm_plan_merge:
        report = audit_first_batch_method_pm_plan_merge(args.root, args.audit_first_batch_method_pm_plan_merge)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_method_pm_plan_draft:
        draft = _read_json_object(Path(args.audit_method_pm_plan_draft))
        if draft is None:
            report = {
                "result": "blocked",
                "next_action": "action:repair_method_pm_plan_draft",
                "issues": ["invalid_method_pm_plan_draft_json"],
            }
        else:
            report = audit_method_pm_plan_draft_contract(draft)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_cognitive_pipeline:
        report = audit_first_batch_cognitive_pipeline(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_backtest_input_readiness:
        report = audit_first_batch_backtest_input_readiness(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_method_pm_readiness:
        report = audit_first_batch_method_pm_readiness(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_sample_table_trial:
        report = audit_first_batch_sample_table_trial(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_record_drafts:
        report = audit_first_batch_record_drafts(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_front_filter_run:
        report = audit_first_batch_front_filter_run(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    if args.audit_first_batch_readiness:
        report = audit_first_batch_readiness(args.root)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["result"] == "pass" else 1

    report = validate_intake_package(args.root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["contract_check_result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
