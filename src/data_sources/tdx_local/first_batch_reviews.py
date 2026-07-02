from __future__ import annotations

from pathlib import Path
from typing import Any

from ashare_intake_validator import audit_first_batch_front_filter_run, audit_first_batch_record_drafts
from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_review_helpers import *
from .first_batch_shortlist import *

def prepare_malf_snapshot_draft_review(
    daily_malf_review_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in daily_malf_review_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_snapshot_draft_review_candidate")
            continue
        candidates.append(_attach_malf_snapshot_draft_review(candidate, generated_at_value))

    ready_count = sum(
        1 for item in candidates if item.get("snapshot_draft_review_status") == "ready_for_manual_review"
    )
    hold_count = sum(1 for item in candidates if item.get("snapshot_draft_review_status") == "hold")
    next_action = (
        "action:manual_review_malf_snapshot_drafts"
        if ready_count
        else "action:hold_for_malf_snapshot_draft_inputs"
    )
    if issues and not candidates:
        next_action = "action:repair_malf_snapshot_draft_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if ready_count else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "malf_snapshot_draft_review_prep_v0.1",
            "source_review_id": daily_malf_review_report.get("review_id"),
            "window_start": daily_malf_review_report.get("window_start"),
            "window_end": daily_malf_review_report.get("window_end"),
            "draft_review_candidate_count": len(candidates),
            "draft_review_ready_count": ready_count,
            "draft_review_hold_count": hold_count,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def apply_malf_snapshot_manual_review_verdicts(
    draft_review_report: dict[str, Any],
    manual_verdicts: dict[str, dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in draft_review_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_manual_snapshot_review_candidate")
            continue
        ts_code = str(candidate.get("ts_code", ""))
        candidates.append(_attach_malf_snapshot_manual_verdict(candidate, manual_verdicts.get(ts_code), generated_at_value))

    approved_count = sum(1 for item in candidates if item.get("manual_review_status") == "reviewed_ready_candidate")
    hold_count = sum(1 for item in candidates if item.get("manual_review_status") != "reviewed_ready_candidate")
    next_action = (
        "action:prepare_formal_front_filter_review_package"
        if approved_count
        else "action:hold_for_manual_malf_snapshot_review"
    )
    if issues and not candidates:
        next_action = "action:repair_manual_malf_snapshot_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if approved_count else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "malf_snapshot_manual_review_verdicts_v0.1",
            "source_review_id": draft_review_report.get("review_id"),
            "manual_reviewed_candidate_count": len(candidates),
            "manual_review_approved_count": approved_count,
            "manual_review_hold_count": hold_count,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_formal_front_filter_review_package(
    manual_review_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    review_inputs: list[dict[str, Any]] = []
    held_candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in manual_review_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_formal_front_filter_review_candidate")
            continue
        review_input = _formal_front_filter_review_input(candidate)
        if review_input is None:
            held_candidates.append(
                {
                    "ts_code": candidate.get("ts_code"),
                    "trade_date": candidate.get("trade_date"),
                    "front_filter_review_package_status": "hold",
                    "front_filter_review_package_reason": "reviewed_snapshot_candidate_missing",
                }
            )
            continue
        review_inputs.append(review_input)

    next_action = (
        "action:run_formal_front_filter_audit_when_explicitly_requested"
        if review_inputs
        else "action:hold_for_reviewed_malf_snapshot_candidates"
    )
    if issues and not review_inputs and not held_candidates:
        next_action = "action:repair_formal_front_filter_review_package_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if review_inputs else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "formal_front_filter_review_package_v0.1",
            "source_review_id": manual_review_report.get("review_id"),
            "front_filter_review_input_count": len(review_inputs),
            "front_filter_review_hold_count": len(held_candidates),
            "front_filter_execution_allowed": False,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "front_filter_review_inputs": review_inputs,
            "held_candidates": held_candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def audit_formal_front_filter_review_package(
    review_package: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    from tachibana_front_filter import run_front_filter

    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    review_inputs = review_package.get("front_filter_review_inputs", [])
    issues: list[str] = []
    audit_results: list[dict[str, Any]] = []

    if not isinstance(review_inputs, list) or not review_inputs:
        issues.append("front_filter_review_inputs_missing")
        review_inputs = []

    with tempfile.TemporaryDirectory(prefix="formal-front-filter-audit-") as tmp:
        tmp_root = Path(tmp)
        for index, review_input in enumerate(review_inputs):
            if not isinstance(review_input, dict):
                issues.append("invalid_front_filter_review_input")
                audit_results.append(
                    {
                        "formal_front_filter_audit_status": "blocked",
                        "audit_issues": ["invalid_front_filter_review_input"],
                    }
                )
                continue

            audit_snapshot, snapshot_issues = _formal_front_filter_audit_snapshot(review_input)
            if snapshot_issues:
                audit_results.append(_blocked_formal_front_filter_audit_result(review_input, snapshot_issues))
                continue

            snapshot_path = tmp_root / f"front-filter-audit-{index}.json"
            snapshot_path.write_text(json.dumps(audit_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            front_filter_report = run_front_filter(snapshot_path)
            audit_results.append(_formal_front_filter_audit_result(review_input, audit_snapshot, front_filter_report))

    blocked_results = [
        item for item in audit_results if item.get("formal_front_filter_audit_status") != "pass"
    ]
    pass_count = len(audit_results) - len(blocked_results)

    if not audit_results:
        next_action = "action:hold_for_formal_front_filter_review_inputs"
    elif blocked_results:
        next_action = "action:repair_formal_front_filter_review_inputs"
    else:
        next_action = "action:prepare_qualification_record_draft_review_when_explicitly_requested"

    return _strip_forbidden_fields(
        {
            "result": "pass" if audit_results and not blocked_results else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "formal_front_filter_review_audit_v0.1",
            "source_package_id": review_package.get("package_id"),
            "audited_front_filter_input_count": len(audit_results),
            "formal_front_filter_audit_pass_count": pass_count,
            "formal_front_filter_audit_blocked_count": len(blocked_results),
            "front_filter_execution_allowed": False,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "front_filter_audit_results": audit_results,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_qualification_record_draft_review(
    front_filter_audit_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    from tachibana_front_filter import build_qualification_record_draft

    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    review_inputs: list[dict[str, Any]] = []
    held_results: list[dict[str, Any]] = []
    issues: list[str] = []

    audit_results = front_filter_audit_report.get("front_filter_audit_results", [])
    if not isinstance(audit_results, list) or not audit_results:
        issues.append("front_filter_audit_results_missing")
        audit_results = []

    for audit_result in audit_results:
        if not isinstance(audit_result, dict):
            issues.append("invalid_front_filter_audit_result")
            continue
        if audit_result.get("formal_front_filter_audit_status") != "pass":
            held_results.append(_held_qualification_record_draft_review_result(audit_result, "formal_front_filter_audit_not_pass"))
            continue
        if audit_result.get("front_filter_result") != "pass":
            held_results.append(_held_qualification_record_draft_review_result(audit_result, "front_filter_result_not_pass"))
            continue

        front_filter_report = _qualification_record_draft_front_filter_report(audit_result)
        draft = build_qualification_record_draft(
            front_filter_report,
            ashare_sample_id=str(audit_result.get("ashare_sample_id") or audit_result.get("ashare_sample_id_suggestion") or _fallback_ashare_sample_id(audit_result)),
            symbol_name=str(audit_result.get("symbol_name") or "UNKNOWN"),
            candidate_stage_before="structure_candidate",
        )
        review_inputs.append(_qualification_record_draft_review_input(audit_result, draft))

    next_action = (
        "action:manual_review_qualification_record_drafts"
        if review_inputs
        else "action:hold_for_formal_front_filter_audit_passes"
    )
    if issues and not review_inputs and not held_results:
        next_action = "action:repair_qualification_record_draft_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if review_inputs else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "qualification_record_draft_review_package_v0.1",
            "source_audit_id": front_filter_audit_report.get("audit_id"),
            "qualification_record_draft_review_input_count": len(review_inputs),
            "qualification_record_draft_review_hold_count": len(held_results),
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "qualification_record_draft_review_inputs": review_inputs,
            "held_audit_results": held_results,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def apply_qualification_record_draft_manual_verdicts(
    draft_review_report: dict[str, Any],
    manual_verdicts: dict[str, dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    reviewed_drafts: list[dict[str, Any]] = []
    issues: list[str] = []

    review_inputs = draft_review_report.get("qualification_record_draft_review_inputs", [])
    if not isinstance(review_inputs, list) or not review_inputs:
        issues.append("qualification_record_draft_review_inputs_missing")
        review_inputs = []

    for draft_input in review_inputs:
        if not isinstance(draft_input, dict):
            issues.append("invalid_qualification_record_draft_review_input")
            continue
        record_id = str(draft_input.get("qualification_record_id", ""))
        reviewed_drafts.append(
            _attach_qualification_record_draft_manual_verdict(
                draft_input,
                manual_verdicts.get(record_id),
                generated_at_value,
            )
        )

    approved_count = sum(
        1
        for item in reviewed_drafts
        if item.get("qualification_record_manual_review_status")
        == "approved_for_formal_record_write_audit_candidate"
    )
    hold_count = len(reviewed_drafts) - approved_count
    next_action = (
        "action:prepare_formal_qualification_record_write_audit_when_explicitly_requested"
        if approved_count
        else "action:hold_for_manual_qualification_record_draft_review"
    )
    if issues and not reviewed_drafts:
        next_action = "action:repair_qualification_record_draft_manual_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if approved_count else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "qualification_record_draft_manual_verdicts_v0.1",
            "source_package_id": draft_review_report.get("package_id"),
            "manual_reviewed_draft_count": len(reviewed_drafts),
            "manual_review_approved_count": approved_count,
            "manual_review_hold_count": hold_count,
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "qualification_record_draft_manual_verdicts": reviewed_drafts,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_formal_qualification_record_write_audit(
    manual_review_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    audit_candidates: list[dict[str, Any]] = []
    held_results: list[dict[str, Any]] = []
    issues: list[str] = []

    manual_results = manual_review_report.get("qualification_record_draft_manual_verdicts", [])
    if not isinstance(manual_results, list) or not manual_results:
        issues.append("qualification_record_draft_manual_verdicts_missing")
        manual_results = []

    for manual_result in manual_results:
        if not isinstance(manual_result, dict):
            issues.append("invalid_qualification_record_draft_manual_verdict")
            continue
        if (
            manual_result.get("qualification_record_manual_review_status")
            != "approved_for_formal_record_write_audit_candidate"
        ):
            held_results.append(
                _held_formal_qualification_record_write_audit_result(
                    manual_result,
                    "manual_review_not_approved_for_formal_record_write_audit",
                )
            )
            continue
        audit_candidates.append(_formal_qualification_record_write_audit_candidate(manual_result, generated_at_value))

    next_action = (
        "action:prepare_formal_qualification_record_persistence_package_when_explicitly_requested"
        if audit_candidates
        else "action:hold_for_formal_qualification_record_write_audit_candidates"
    )
    if issues and not audit_candidates and not held_results:
        next_action = "action:repair_formal_qualification_record_write_audit_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if audit_candidates else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "formal_qualification_record_write_audit_v0.1",
            "source_review_id": manual_review_report.get("review_id"),
            "formal_record_write_audit_candidate_count": len(audit_candidates),
            "formal_record_write_audit_hold_count": len(held_results),
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "formal_record_write_audit_candidates": audit_candidates,
            "held_manual_review_results": held_results,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_formal_qualification_record_persistence_package_when_explicitly_requested(
    write_audit_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    persistence_packages: list[dict[str, Any]] = []
    held_items: list[dict[str, Any]] = []
    issues: list[str] = []

    audit_candidates = write_audit_report.get("formal_record_write_audit_candidates", [])
    if not isinstance(audit_candidates, list) or not audit_candidates:
        issues.append("formal_record_write_audit_candidates_missing")
        audit_candidates = []

    for audit_candidate in audit_candidates:
        if not isinstance(audit_candidate, dict):
            issues.append("invalid_formal_record_write_audit_candidate")
            continue
        if audit_candidate.get("formal_record_write_audit_status") != "pass":
            held_items.append(
                _held_formal_qualification_record_persistence_item(
                    audit_candidate,
                    "formal_record_write_audit_not_pass",
                )
            )
            continue
        persistence_packages.append(_formal_qualification_record_persistence_package(audit_candidate, generated_at_value))

    next_action = (
        "action:prepare_candidate_table_update_audit_when_explicitly_requested"
        if persistence_packages
        else "action:hold_for_formal_qualification_record_write_audit_passes"
    )
    if issues and not persistence_packages and not held_items:
        next_action = "action:repair_formal_qualification_record_persistence_package_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if persistence_packages else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "formal_qualification_record_persistence_package_v0.1",
            "source_audit_id": write_audit_report.get("audit_id"),
            "qualification_record_persistence_package_prepared": bool(persistence_packages),
            "qualification_record_persistence_performed": False,
            "qualification_record_persistence_package_count": len(persistence_packages),
            "held_qualification_record_persistence_count": len(held_items),
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "qualification_record_persistence_packages": persistence_packages,
            "held_qualification_record_persistence_items": held_items,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )
