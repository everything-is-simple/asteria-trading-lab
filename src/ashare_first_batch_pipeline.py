from __future__ import annotations

from pathlib import Path
from typing import Any

from tachibana_front_filter import (
    audit_backtest_input_gate,
    audit_front_filter_system,
    audit_method_pm_bridge_gate,
    build_qualification_record_draft,
    run_front_filter,
)

from ashare_intake_constants import *
from ashare_intake_contracts import validate_intake_package
from ashare_intake_utils import *
from ashare_execution_constraint_helpers import *

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
