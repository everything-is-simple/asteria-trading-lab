from __future__ import annotations

from pathlib import Path
from typing import Any

from ashare_intake_constants import *
from ashare_intake_contracts import audit_ashare_institution_fact_package
from ashare_first_batch_pipeline import audit_first_batch_backtest_input_snapshot_drafts
from ashare_intake_utils import *
from ashare_execution_constraint_helpers import *

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
    relation_evidence_dir: str | Path | None = None,
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

    relation_evidence_index, relation_evidence_blocked_items = _price_limit_relation_evidence_index(
        relation_evidence_dir
    )
    if relation_evidence_blocked_items:
        return {
            "result": "blocked",
            "execution_constraint_snapshot_count": 0,
            "execution_constraint_snapshots": [],
            "execution_constraint_snapshot_blocked_count": len(relation_evidence_blocked_items),
            "execution_constraint_snapshot_blocked_items": relation_evidence_blocked_items,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_price_limit_event_relation_evidence",
            "issues": ["price_limit_event_relation_evidence_invalid"],
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
            relation_key = (
                str(record.get("ashare_sample_id")),
                str(fact.get("ts_code")),
                str(fact.get("trade_date")),
                str(record.get("planned_event") or record.get("execution_event_type") or ""),
            )
            snapshots.append(
                _execution_constraint_snapshot(
                    record,
                    fact,
                    relation_evidence_index.get(relation_key),
                )
            )

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
    relation_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    snapshot_report = audit_first_batch_execution_constraint_snapshots(
        data_root,
        plan_dir,
        institution_fact_root,
        relation_evidence_dir,
    )
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
    relation_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    gate_report = audit_first_batch_execution_feasibility_gate(
        data_root,
        plan_dir,
        institution_fact_root,
        relation_evidence_dir,
    )
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
    relation_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    draft_report = audit_first_batch_execution_feasibility_verdicts(
        data_root,
        plan_dir,
        institution_fact_root,
        relation_evidence_dir,
    )
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
    relation_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    merge_report = audit_first_batch_execution_feasibility_verdict_merge(
        data_root,
        plan_dir,
        institution_fact_root,
        verdict_dir,
        relation_evidence_dir,
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
