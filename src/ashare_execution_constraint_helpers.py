from __future__ import annotations

from pathlib import Path
from typing import Any

from tachibana_front_filter import audit_backtest_input_gate, audit_method_pm_bridge_gate

from ashare_intake_constants import *
from ashare_intake_utils import *

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


def _price_limit_event_evidence(record: dict[str, Any], fact: dict[str, Any]) -> dict[str, Any]:
    planned_event = str(record.get("planned_event") or record.get("execution_event_type") or "")
    evidence_ref = _list_value(fact.get("source_ref"))
    if fact.get("is_suspended") == "true":
        return {
            "status": "event_fact_conflicted",
            "reason": ["planned_event_conflicts_with_suspension_fact"],
            "evidence_ref": evidence_ref,
        }
    if fact.get("limit_up_price") in {"", None} or fact.get("limit_down_price") in {"", None}:
        return {
            "status": "event_fact_missing",
            "reason": ["planned_event_missing_price_limit_bounds"],
            "evidence_ref": evidence_ref,
        }
    if planned_event in {"", "wait", "hold", "lock_candidate"}:
        return {
            "status": "event_fact_missing",
            "reason": ["planned_event_does_not_require_price_limit_policy_review"],
            "evidence_ref": evidence_ref,
        }
    return {
        "status": "event_fact_ready",
        "reason": ["planned_event_has_price_limit_bounds_without_explicit_blocking_fact"],
        "evidence_ref": evidence_ref,
    }


def _price_limit_event_relation(
    record: dict[str, Any],
    fact: dict[str, Any],
    relation_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    planned_event = str(record.get("planned_event") or record.get("execution_event_type") or "")
    evidence_ref = _list_value(fact.get("source_ref"))
    is_suspended = fact.get("is_suspended") == "true"
    has_bounds = fact.get("limit_up_price") not in {"", None} and fact.get("limit_down_price") not in {"", None}

    if is_suspended:
        return {
            "status": "relation_blocked",
            "fill_blocking_status": "explicit_fill_blocking_fact",
            "limit_proximity": "not_applicable",
            "reason": ["planned_event_has_explicit_price_limit_blocking_fact"],
            "evidence_ref": evidence_ref,
        }

    if not has_bounds:
        return {
            "status": "relation_unknown",
            "fill_blocking_status": "fill_blocking_unknown",
            "limit_proximity": "proximity_unknown",
            "reason": ["planned_event_limit_proximity_is_unknown"],
            "evidence_ref": evidence_ref,
        }

    if planned_event == "open_center":
        return {
            "status": "relation_clear",
            "fill_blocking_status": "no_explicit_fill_blocking_fact",
            "limit_proximity": "not_applicable",
            "reason": ["planned_event_has_no_explicit_price_limit_blocking_fact"],
            "evidence_ref": evidence_ref,
        }

    if relation_evidence is not None:
        return {
            "status": relation_evidence["price_limit_event_relation_status"],
            "fill_blocking_status": relation_evidence["price_limit_event_fill_blocking_status"],
            "limit_proximity": relation_evidence["price_limit_event_limit_proximity"],
            "reason": _list_value(relation_evidence.get("price_limit_event_relation_reason")),
            "evidence_ref": _unique_preserve_order(
                [
                    *evidence_ref,
                    *_list_value(relation_evidence.get("price_limit_event_relation_ref")),
                ]
            ),
        }

    if planned_event == "add_on":
        return {
            "status": "relation_constrained",
            "fill_blocking_status": "fill_blocking_unknown",
            "limit_proximity": "proximity_unknown",
            "reason": [
                "planned_event_limit_proximity_is_unknown",
                "planned_event_requires_higher_price_limit_resolution",
            ],
            "evidence_ref": evidence_ref,
        }

    return {
        "status": "relation_unknown",
        "fill_blocking_status": "fill_blocking_unknown",
        "limit_proximity": "proximity_unknown",
        "reason": ["planned_event_limit_proximity_is_unknown"],
        "evidence_ref": evidence_ref,
    }


def _execution_constraint_snapshot(
    record: dict[str, Any],
    fact: dict[str, str],
    relation_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ts_code = fact.get("ts_code")
    trade_date = fact.get("trade_date")
    constraint_ref = f"ASHARE-CONSTRAINT-{ts_code}-{trade_date}-v0.1"
    price_limit_event_evidence = _price_limit_event_evidence(record, fact)
    price_limit_event_relation = _price_limit_event_relation(record, fact, relation_evidence)
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
        "price_limit_event_evidence_status": price_limit_event_evidence["status"],
        "price_limit_event_evidence_reason": price_limit_event_evidence["reason"],
        "price_limit_event_evidence_ref": price_limit_event_evidence["evidence_ref"],
        "price_limit_event_relation_status": price_limit_event_relation["status"],
        "price_limit_event_fill_blocking_status": price_limit_event_relation["fill_blocking_status"],
        "price_limit_event_limit_proximity": price_limit_event_relation["limit_proximity"],
        "price_limit_event_relation_reason": price_limit_event_relation["reason"],
        "price_limit_event_relation_ref": price_limit_event_relation["evidence_ref"],
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


def _count_by_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _status_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    return _count_by_field(items, "feasibility_status")


__all__ = [name for name in globals() if not name.startswith("__")]
