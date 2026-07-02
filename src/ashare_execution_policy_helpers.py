from __future__ import annotations

from pathlib import Path
from typing import Any

from ashare_intake_constants import *
from ashare_intake_utils import *
from ashare_execution_constraint_helpers import *

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
    price_limit_event_evidence_status = str(snapshot.get("price_limit_event_evidence_status", "event_fact_missing"))
    price_limit_event_evidence_reason = _list_value(snapshot.get("price_limit_event_evidence_reason"))
    price_limit_event_relation_status = str(
        snapshot.get("price_limit_event_relation_status", "relation_unknown")
    )
    price_limit_event_relation_reason = _list_value(snapshot.get("price_limit_event_relation_reason"))
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
            "candidate_status": "review_required"
            if price_limit_event_relation_status in {"relation_clear", "relation_constrained"}
            else "evidence_incomplete",
            "candidate_reason": ["price_limit_relation_ready_for_candidate_review"]
            if price_limit_event_relation_status in {"relation_clear", "relation_constrained"}
            else ["price_limit_relation_still_unknown_on_planned_event"],
            "price_limit_event_evidence_status": price_limit_event_evidence_status,
            "price_limit_event_evidence_reason": price_limit_event_evidence_reason,
            "price_limit_event_evidence_ref": _list_value(snapshot.get("price_limit_event_evidence_ref")),
            "price_limit_event_relation_status": price_limit_event_relation_status,
            "price_limit_event_fill_blocking_status": snapshot.get("price_limit_event_fill_blocking_status"),
            "price_limit_event_limit_proximity": snapshot.get("price_limit_event_limit_proximity"),
            "price_limit_event_relation_reason": price_limit_event_relation_reason,
            "price_limit_event_relation_ref": _list_value(snapshot.get("price_limit_event_relation_ref")),
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


def _execution_policy_research_agenda_items(preps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for prep in preps:
        grouped.setdefault(str(prep.get("candidate_constraint_type")), []).append(prep)

    items: list[dict[str, Any]] = []
    for constraint_type, records in grouped.items():
        statuses = {str(item.get("research_prep_status")) for item in records}
        if "review_required" in statuses:
            agenda_status = "ready_for_research"
            agenda_reason = ["execution_policy_research_topic_has_ready_candidates"]
            next_action = "action:prepare_execution_policy_research"
        elif "evidence_incomplete" in statuses:
            agenda_status = "await_additional_evidence"
            agenda_reason = ["execution_policy_research_topic_requires_additional_evidence"]
            next_action = "action:collect_additional_execution_evidence"
        elif "carry_forward_required" in statuses:
            agenda_status = "carry_forward_required"
            agenda_reason = ["execution_policy_research_topic_carry_forward_required"]
            next_action = "action:collect_additional_execution_evidence"
        else:
            agenda_status = "blocked"
            agenda_reason = ["execution_policy_research_topic_blocked"]
            next_action = "action:collect_additional_execution_evidence"

        items.append(
            {
                "record_type": "AShareExecutionPolicyResearchAgendaItem",
                "candidate_constraint_type": constraint_type,
                "agenda_status": agenda_status,
                "agenda_reason": agenda_reason,
                "sample_count": len(records),
                "ready_sample_ids": [
                    item.get("ashare_sample_id")
                    for item in records
                    if str(item.get("research_prep_status")) == "review_required"
                ],
                "blocked_sample_ids": [
                    item.get("ashare_sample_id")
                    for item in records
                    if str(item.get("research_prep_status")) != "review_required"
                ],
                "evidence_ref": _unique_preserve_order(
                    [
                        ref
                        for item in records
                        for ref in _list_value(item.get("evidence_ref"))
                    ]
                ),
                "institution_rule_definition_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
                "next_action": next_action,
            }
        )

    return sorted(items, key=lambda item: str(item.get("candidate_constraint_type")))


def _execution_policy_research_agenda_report_next_action(
    agendas: list[dict[str, Any]],
    blocked_items: list[dict[str, Any]],
) -> str:
    if any(str(item.get("agenda_status")) == "ready_for_research" for item in agendas):
        return "action:prepare_execution_policy_research"
    if agendas or blocked_items:
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


__all__ = [name for name in globals() if not name.startswith("__")]
