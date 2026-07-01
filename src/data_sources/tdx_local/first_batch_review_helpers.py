from __future__ import annotations

from pathlib import Path
from typing import Any

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_shortlist_helpers import *
from .first_batch_formal_candidate_helpers import *

def _attach_malf_snapshot_draft_review(candidate: dict[str, Any], generated_at: str) -> dict[str, Any]:
    enriched = dict(candidate)
    daily_status = str(candidate.get("daily_level_malf_review_status", ""))
    snapshot_stub = candidate.get("snapshot_stub")

    if daily_status != "pass":
        enriched.update(
            {
                "snapshot_draft_review_status": "hold",
                "snapshot_draft_review_reason": "daily_level_malf_review_not_pass",
                "suggested_snapshot_draft": None,
                "formal_front_filter_status": "snapshot_pending",
                "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
                "research_boundary_warning": _snapshot_draft_review_boundary_warning(candidate),
                "next_action": "action:hold_for_daily_level_malf_evidence",
            }
        )
        return enriched

    if not isinstance(snapshot_stub, dict):
        enriched.update(
            {
                "snapshot_draft_review_status": "hold",
                "snapshot_draft_review_reason": "snapshot_stub_missing",
                "suggested_snapshot_draft": None,
                "formal_front_filter_status": "snapshot_pending",
                "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
                "research_boundary_warning": _snapshot_draft_review_boundary_warning(candidate),
                "next_action": "action:hold_for_malf_snapshot_draft_inputs",
            }
        )
        return enriched

    entry = {
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "evidence_ref": candidate.get("evidence_ref", snapshot_stub.get("evidence_ref", "")),
    }
    draft_stub = dict(snapshot_stub)
    draft_stub["generated_at"] = generated_at
    suggested_snapshot_draft = _research_snapshot_draft(draft_stub, entry)
    enriched.update(
        {
            "snapshot_draft_review_status": "ready_for_manual_review",
            "snapshot_draft_review_reason": "daily_level_malf_structure_passed",
            "suggested_snapshot_draft": suggested_snapshot_draft,
            "formal_front_filter_status": "snapshot_pending",
            "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
            "research_boundary_warning": _snapshot_draft_review_boundary_warning(candidate),
            "next_action": "action:manual_review_malf_snapshot_draft",
        }
    )
    return enriched


def _attach_malf_snapshot_manual_verdict(
    candidate: dict[str, Any],
    verdict: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    enriched = dict(candidate)
    if candidate.get("snapshot_draft_review_status") != "ready_for_manual_review":
        status = "needs_manual_review"
        reason = "snapshot_draft_not_ready_for_manual_review"
        reviewed_snapshot = None
        next_action = "action:hold_for_malf_snapshot_draft_inputs"
    elif not isinstance(verdict, dict):
        status = "needs_manual_review"
        reason = "manual_review_verdict_missing"
        reviewed_snapshot = None
        next_action = "action:manual_review_malf_snapshot_draft"
    else:
        manual_verdict = str(verdict.get("manual_review_verdict", ""))
        if manual_verdict == "approved_for_formal_front_filter_review":
            status = "reviewed_ready_candidate"
            reason = "manual_review_approved_for_formal_front_filter_review"
            reviewed_snapshot = _reviewed_snapshot_candidate(candidate, verdict, generated_at)
            next_action = "action:prepare_formal_front_filter_review_package"
        elif manual_verdict == "rejected":
            status = "rejected"
            reason = "manual_review_rejected"
            reviewed_snapshot = None
            next_action = "action:hold_for_manual_malf_snapshot_review"
        elif manual_verdict == "needs_revision":
            status = "needs_revision"
            reason = "manual_review_needs_revision"
            reviewed_snapshot = None
            next_action = "action:revise_malf_snapshot_draft"
        else:
            status = "needs_manual_review"
            reason = "manual_review_verdict_invalid"
            reviewed_snapshot = None
            next_action = "action:manual_review_malf_snapshot_draft"

    enriched.update(
        {
            "manual_review_status": status,
            "manual_review_reason": reason,
            "manual_review_verdict": verdict.get("manual_review_verdict") if isinstance(verdict, dict) else None,
            "manual_review_note": verdict.get("reviewer_note") if isinstance(verdict, dict) else None,
            "reviewed_snapshot_candidate": reviewed_snapshot,
            "formal_front_filter_status": "snapshot_pending",
            "formal_front_filter_issue": "pipeline_requires_formal_front_filter_review_package",
            "research_boundary_warning": _manual_snapshot_review_boundary_warning(candidate),
            "next_action": next_action,
        }
    )
    return enriched


def _formal_front_filter_review_input(candidate: dict[str, Any]) -> dict[str, Any] | None:
    if candidate.get("manual_review_status") != "reviewed_ready_candidate":
        return None
    reviewed_snapshot = candidate.get("reviewed_snapshot_candidate")
    if not isinstance(reviewed_snapshot, dict):
        return None

    expected_rule_id = str(
        reviewed_snapshot.get("draft_front_filter_expected_rule_id")
        or candidate.get("draft_front_filter_expected_rule_id")
        or "Q-PRESSURE-ADJUST"
    )
    ts_code = str(reviewed_snapshot.get("ts_code") or candidate.get("ts_code", ""))
    window_start = str(reviewed_snapshot.get("window_start") or candidate.get("sample_window_start", ""))
    window_end = str(reviewed_snapshot.get("window_end") or candidate.get("sample_window_end", ""))
    snapshot_ref = str(reviewed_snapshot.get("malf_snapshot_ref", ""))
    return _strip_forbidden_fields(
        {
            "ts_code": ts_code,
            "trade_date": candidate.get("trade_date"),
            "window_start": window_start,
            "window_end": window_end,
            "malf_snapshot_ref": snapshot_ref,
            "snapshot_quality_status": reviewed_snapshot.get("snapshot_quality_status"),
            "malf_background": reviewed_snapshot.get("malf_background"),
            "wave_range_break_fields": reviewed_snapshot.get("wave_range_break_fields"),
            "expected_front_filter_rule_id": expected_rule_id,
            "reviewed_snapshot_candidate": reviewed_snapshot,
            "review_command_preview": (
                "$env:PYTHONPATH='src'; python -m tachibana_front_filter "
                f"--snapshot <review-package>\\{ts_code}-{window_start[0:7]}.json"
            ),
            "front_filter_execution_allowed": False,
            "boundary_warning": [
                "front_filter_review_package_is_not_execution",
                "do_not_run_front_filter_without_explicit_audit_step",
                "do_not_generate_trade_from_front_filter_review_package",
            ],
            "next_action": "action:run_formal_front_filter_audit_when_explicitly_requested",
        }
    )


def _formal_front_filter_audit_snapshot(review_input: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    reviewed_snapshot = review_input.get("reviewed_snapshot_candidate")
    if isinstance(reviewed_snapshot, dict):
        snapshot = dict(reviewed_snapshot)
    else:
        snapshot = {
            "malf_snapshot_ref": review_input.get("malf_snapshot_ref"),
            "ts_code": review_input.get("ts_code"),
            "window_start": review_input.get("window_start"),
            "window_end": review_input.get("window_end"),
            "malf_background": review_input.get("malf_background"),
            "wave_range_break_fields": review_input.get("wave_range_break_fields"),
        }

    for key in [
        "malf_snapshot_ref",
        "ts_code",
        "window_start",
        "window_end",
        "malf_background",
        "wave_range_break_fields",
    ]:
        if snapshot.get(key) in (None, "") and review_input.get(key) not in (None, ""):
            snapshot[key] = review_input.get(key)

    issues: list[str] = []
    for key in ["ts_code", "window_start", "window_end", "malf_background"]:
        if not snapshot.get(key):
            issues.append(f"audit_snapshot_missing_{key}")
    if not isinstance(snapshot.get("wave_range_break_fields"), dict):
        issues.append("audit_snapshot_missing_wave_range_break_fields")

    source_quality = snapshot.get("snapshot_quality_status") or review_input.get("snapshot_quality_status")
    if source_quality != "reviewed_ready_candidate":
        issues.append(f"source_snapshot_quality_not_reviewed_ready_candidate:{source_quality}")

    snapshot["snapshot_quality_status"] = "ready"
    snapshot["audit_source_snapshot_quality_status"] = source_quality
    snapshot["audit_only"] = True
    snapshot["audit_boundary_warning"] = [
        "temporary_ready_snapshot_used_for_audit_only",
        "reviewed_ready_candidate_not_promoted_in_source_package",
        "do_not_generate_trade_from_formal_front_filter_audit",
    ]
    return snapshot, issues


def _formal_front_filter_audit_result(
    review_input: dict[str, Any],
    audit_snapshot: dict[str, Any],
    front_filter_report: dict[str, Any],
) -> dict[str, Any]:
    expected_rule_id = review_input.get("expected_front_filter_rule_id")
    actual_rule_id = front_filter_report.get("qualification_rule_id")
    audit_issues: list[str] = []
    if front_filter_report.get("front_filter_result") != "pass":
        audit_issues.append(f"front_filter_result_not_pass:{front_filter_report.get('front_filter_result')}")
    if expected_rule_id and actual_rule_id != expected_rule_id:
        audit_issues.append(f"front_filter_rule_mismatch:expected={expected_rule_id}:actual={actual_rule_id}")

    boundary_warning = list(front_filter_report.get("boundary_warning", []))
    for item in [
        "temporary_ready_snapshot_used_for_audit_only",
        "formal_front_filter_audit_is_not_trade_signal",
        "formal_front_filter_audit_does_not_open_backtest",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "ts_code": review_input.get("ts_code") or audit_snapshot.get("ts_code"),
            "symbol_name": review_input.get("symbol_name"),
            "ashare_sample_id": review_input.get("ashare_sample_id"),
            "ashare_sample_id_suggestion": review_input.get("ashare_sample_id_suggestion"),
            "trade_date": review_input.get("trade_date"),
            "window_start": audit_snapshot.get("window_start"),
            "window_end": audit_snapshot.get("window_end"),
            "malf_snapshot_ref": audit_snapshot.get("malf_snapshot_ref"),
            "malf_background": audit_snapshot.get("malf_background"),
            "formal_front_filter_audit_status": "pass" if not audit_issues else "blocked",
            "audit_issues": audit_issues,
            "front_filter_result": front_filter_report.get("front_filter_result"),
            "qualification_rule_id": actual_rule_id,
            "expected_front_filter_rule_id": expected_rule_id,
            "rhythm_meaning": front_filter_report.get("rhythm_meaning"),
            "tachibana_applicability": front_filter_report.get("tachibana_applicability"),
            "pm_required": front_filter_report.get("pm_required"),
            "rule_match_reason": front_filter_report.get("rule_match_reason", []),
            "applicability_reason": front_filter_report.get("applicability_reason", []),
            "audit_snapshot_quality_status": audit_snapshot.get("snapshot_quality_status"),
            "source_snapshot_quality_status": audit_snapshot.get("audit_source_snapshot_quality_status"),
            "boundary_warning": boundary_warning,
            "front_filter_execution_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": (
                "action:prepare_qualification_record_draft_review_when_explicitly_requested"
                if not audit_issues
                else "action:repair_formal_front_filter_review_input"
            ),
        }
    )


def _blocked_formal_front_filter_audit_result(
    review_input: dict[str, Any],
    audit_issues: list[str],
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "ts_code": review_input.get("ts_code"),
            "trade_date": review_input.get("trade_date"),
            "window_start": review_input.get("window_start"),
            "window_end": review_input.get("window_end"),
            "formal_front_filter_audit_status": "blocked",
            "audit_issues": audit_issues,
            "front_filter_execution_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_formal_front_filter_review_input",
        }
    )


def _qualification_record_draft_front_filter_report(audit_result: dict[str, Any]) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "malf_snapshot_ref": audit_result.get("malf_snapshot_ref"),
            "ts_code": audit_result.get("ts_code"),
            "window_start": audit_result.get("window_start"),
            "window_end": audit_result.get("window_end"),
            "malf_background": audit_result.get("malf_background", "pullback"),
            "snapshot_quality_status": audit_result.get("audit_snapshot_quality_status", "ready"),
            "front_filter_result": audit_result.get("front_filter_result"),
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": audit_result.get("rhythm_meaning", "unknown"),
            "tachibana_applicability": audit_result.get("tachibana_applicability", "unknown"),
            "qualification_rule_id": audit_result.get("qualification_rule_id"),
            "pm_required": audit_result.get("pm_required", False),
            "rule_match_reason": audit_result.get("rule_match_reason", []),
            "applicability_reason": audit_result.get("applicability_reason", []),
            "boundary_warning": audit_result.get("boundary_warning", []),
            "next_action": "action:fill_qualification_record",
        }
    )


def _qualification_record_draft_review_input(
    audit_result: dict[str, Any],
    draft: dict[str, Any],
) -> dict[str, Any]:
    boundary_warning = list(draft.get("boundary_warning", []))
    for item in [
        "qualification_record_draft_review_is_not_formal_record",
        "manual_review_required_before_writing_qualification_record",
        "do_not_open_trade_or_backtest_from_qualification_draft",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "qualification_record_draft_review_status": "ready_for_manual_review",
            "qualification_record_draft_review_reason": "formal_front_filter_audit_passed",
            "qualification_record_id": draft.get("qualification_record_id"),
            "ashare_sample_id": draft.get("ashare_sample_id"),
            "ts_code": draft.get("ts_code"),
            "symbol_name": draft.get("symbol_name"),
            "sample_window_start": draft.get("sample_window_start"),
            "sample_window_end": draft.get("sample_window_end"),
            "malf_snapshot_ref": draft.get("malf_snapshot_ref"),
            "qualification_rule_id": draft.get("qualification_rule_id"),
            "rhythm_meaning": draft.get("rhythm_meaning"),
            "tachibana_applicability": draft.get("tachibana_applicability"),
            "pm_required": draft.get("pm_required"),
            "source_record_status": draft.get("record_status"),
            "source_front_filter_audit_status": audit_result.get("formal_front_filter_audit_status"),
            "source_front_filter_result": audit_result.get("front_filter_result"),
            "source_audit_issues": audit_result.get("audit_issues", []),
            "record_consistency": draft.get("record_consistency"),
            "rhythm_sample_row_gate": _closed_review_only_gate(
                draft.get("rhythm_sample_row_gate"),
                "rhythm_sample_row_not_writable_from_qualification_draft_review",
            ),
            "candidate_table_gate": _closed_review_only_gate(
                draft.get("candidate_table_gate"),
                "candidate_table_update_requires_post_review_approval",
            ),
            "method_pm_bridge_gate": draft.get("method_pm_bridge_gate"),
            "interface_boundary_gate": draft.get("interface_boundary_gate"),
            "backtest_input_gate": _closed_review_only_gate(
                draft.get("backtest_input_gate"),
                "backtest_input_not_allowed_from_qualification_draft_review",
            ),
            "cognitive_pipeline_gate": draft.get("cognitive_pipeline_gate"),
            "front_filter_system_audit": draft.get("front_filter_system_audit"),
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:manual_review_qualification_record_draft",
        }
    )


def _closed_review_only_gate(gate: Any, issue: str) -> dict[str, Any]:
    if not isinstance(gate, dict):
        return {"result": "blocked", "issues": [issue], "next_action": "action:manual_review_qualification_record_draft"}
    closed = dict(gate)
    issues = list(closed.get("issues", []))
    if issue not in issues:
        issues.append(issue)
    closed["result"] = "blocked"
    closed["issues"] = issues
    closed["next_action"] = "action:manual_review_qualification_record_draft"
    return closed


def _held_qualification_record_draft_review_result(
    audit_result: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "ts_code": audit_result.get("ts_code"),
            "trade_date": audit_result.get("trade_date"),
            "qualification_rule_id": audit_result.get("qualification_rule_id"),
            "formal_front_filter_audit_status": audit_result.get("formal_front_filter_audit_status"),
            "qualification_record_draft_review_status": "hold",
            "qualification_record_draft_review_reason": reason,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_formal_front_filter_audit_passes",
        }
    )


def _fallback_ashare_sample_id(audit_result: dict[str, Any]) -> str:
    ts_code = str(audit_result.get("ts_code") or "UNKNOWN")
    window_end = str(audit_result.get("window_end") or audit_result.get("trade_date") or "UNKNOWN")
    return f"ASHARE-QUAL-DRAFT-{ts_code}-{window_end}"


def _attach_qualification_record_draft_manual_verdict(
    draft_input: dict[str, Any],
    verdict: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    if draft_input.get("qualification_record_draft_review_status") != "ready_for_manual_review":
        status = "hold"
        reason = "qualification_record_draft_not_ready_for_manual_review"
        next_action = "action:hold_for_manual_qualification_record_draft_review"
    elif not isinstance(verdict, dict):
        status = "needs_manual_review"
        reason = "manual_review_verdict_missing"
        next_action = "action:hold_for_manual_qualification_record_draft_review"
    else:
        manual_verdict = str(verdict.get("manual_review_verdict", ""))
        if manual_verdict == "approved_for_formal_record_write_audit":
            status = "approved_for_formal_record_write_audit_candidate"
            reason = "manual_review_approved_for_formal_record_write_audit"
            next_action = "action:prepare_formal_qualification_record_write_audit_when_explicitly_requested"
        elif manual_verdict == "rejected":
            status = "rejected"
            reason = "manual_review_rejected"
            next_action = "action:hold_for_manual_qualification_record_draft_review"
        elif manual_verdict == "needs_revision":
            status = "needs_revision"
            reason = "manual_review_needs_revision"
            next_action = "action:hold_for_manual_qualification_record_draft_review"
        else:
            status = "needs_manual_review"
            reason = "manual_review_verdict_invalid"
            next_action = "action:hold_for_manual_qualification_record_draft_review"

    boundary_warning = list(draft_input.get("boundary_warning", []))
    for item in [
        "manual_verdict_is_not_qualification_record_write",
        "formal_write_audit_required_before_record_write",
        "do_not_update_candidate_table_from_manual_qualification_verdict",
        "do_not_generate_trade_from_manual_qualification_verdict",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            **draft_input,
            "qualification_record_manual_review_status": status,
            "qualification_record_manual_review_reason": reason,
            "manual_review_verdict": verdict.get("manual_review_verdict") if isinstance(verdict, dict) else None,
            "manual_review_note": verdict.get("reviewer_note") if isinstance(verdict, dict) else None,
            "manual_reviewed_at": generated_at,
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def _formal_qualification_record_write_audit_candidate(
    manual_result: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    boundary_warning = list(manual_result.get("boundary_warning", []))
    for item in [
        "write_audit_is_not_record_write",
        "explicit_commit_layer_required_before_formal_record_write",
        "do_not_update_candidate_table_from_write_audit",
        "do_not_open_trading_layer_read_from_write_audit",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            **manual_result,
            "formal_record_write_audit_status": "pass",
            "formal_record_write_audit_reason": "manual_review_approved_and_boundary_gates_closed",
            "source_manual_review_status": manual_result.get("qualification_record_manual_review_status"),
            "formal_record_write_audited_at": generated_at,
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:prepare_formal_qualification_record_persistence_package_when_explicitly_requested",
        }
    )


def _held_formal_qualification_record_write_audit_result(
    manual_result: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "qualification_record_id": manual_result.get("qualification_record_id"),
            "ts_code": manual_result.get("ts_code"),
            "trade_date": manual_result.get("trade_date"),
            "qualification_rule_id": manual_result.get("qualification_rule_id"),
            "qualification_record_manual_review_status": manual_result.get("qualification_record_manual_review_status"),
            "formal_record_write_audit_status": "hold",
            "formal_record_write_audit_reason": reason,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_formal_qualification_record_write_audit_candidate",
        }
    )


def _formal_qualification_record_persistence_package(
    audit_candidate: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    boundary_warning = list(audit_candidate.get("boundary_warning", []))
    for item in [
        "persistence_package_is_not_record_write",
        "explicit_persistence_writer_required_before_record_write",
        "persistence_package_does_not_update_candidate_table",
        "persistence_package_does_not_open_trading_layer",
        "candidate_table_update_requires_separate_audit",
        "trading_layer_read_requires_separate_gate",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "qualification_record_status": "formal_record_ready_for_persistence",
            "qualification_record_id": audit_candidate.get("qualification_record_id"),
            "ashare_sample_id": audit_candidate.get("ashare_sample_id"),
            "ts_code": audit_candidate.get("ts_code"),
            "symbol_name": audit_candidate.get("symbol_name"),
            "sample_window_start": audit_candidate.get("sample_window_start"),
            "sample_window_end": audit_candidate.get("sample_window_end"),
            "qualification_rule_id": audit_candidate.get("qualification_rule_id"),
            "rhythm_meaning": audit_candidate.get("rhythm_meaning"),
            "tachibana_applicability": audit_candidate.get("tachibana_applicability"),
            "source_manual_review_verdict": audit_candidate.get("manual_review_verdict"),
            "source_formal_record_write_audit_status": audit_candidate.get("formal_record_write_audit_status"),
            "source_formal_record_write_audit_reason": audit_candidate.get("formal_record_write_audit_reason"),
            "persistence_package_prepared_at": generated_at,
            "qualification_record_persistence_performed": False,
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:prepare_candidate_table_update_audit_when_explicitly_requested",
        }
    )


def _held_formal_qualification_record_persistence_item(
    audit_candidate: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "qualification_record_id": audit_candidate.get("qualification_record_id"),
            "ts_code": audit_candidate.get("ts_code"),
            "qualification_rule_id": audit_candidate.get("qualification_rule_id"),
            "formal_record_write_audit_status": audit_candidate.get("formal_record_write_audit_status"),
            "qualification_record_persistence_status": "hold",
            "qualification_record_persistence_reason": reason,
            "qualification_record_persistence_performed": False,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_formal_qualification_record_write_audit_pass",
        }
    )


__all__ = [name for name in globals() if not name.startswith("__")]
