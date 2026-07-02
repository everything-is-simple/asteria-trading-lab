from __future__ import annotations

from pathlib import Path
from typing import Any

from ashare_intake_constants import *
from ashare_execution_constraint_pipeline import audit_first_batch_execution_feasibility_outcomes
from ashare_intake_utils import *
from ashare_execution_constraint_helpers import *
from ashare_execution_policy_helpers import *

def audit_first_batch_execution_policy_candidates(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    verdict_dir: str | Path,
    relation_evidence_dir: str | Path | None = None,
) -> dict[str, Any]:
    outcome_report = audit_first_batch_execution_feasibility_outcomes(
        data_root,
        plan_dir,
        institution_fact_root,
        verdict_dir,
        relation_evidence_dir,
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


def audit_first_batch_execution_policy_research_agenda(
    data_root: str | Path,
    plan_dir: str | Path,
    institution_fact_root: str | Path,
    review_dir: str | Path,
) -> dict[str, Any]:
    prep_report = audit_first_batch_execution_policy_research_prep(
        data_root,
        plan_dir,
        institution_fact_root,
        review_dir,
    )
    if prep_report["result"] != "pass":
        return {
            "result": "blocked",
            "execution_policy_research_agenda_count": 0,
            "execution_policy_research_agendas": [],
            "execution_policy_research_agenda_blocked_count": 0,
            "execution_policy_research_agenda_blocked_items": [],
            "agenda_status_counts": {},
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": prep_report["next_action"],
            "issues": ["execution_policy_research_agenda_requires_valid_research_prep"],
            "execution_policy_research_prep_report": prep_report,
        }

    agendas = _execution_policy_research_agenda_items(
        prep_report.get("execution_policy_research_preps", [])
    )
    blocked_items = list(prep_report.get("execution_policy_research_prep_blocked_items", []))
    return {
        "result": "pass",
        "execution_policy_research_agenda_count": len(agendas),
        "execution_policy_research_agendas": agendas,
        "execution_policy_research_agenda_blocked_count": len(blocked_items),
        "execution_policy_research_agenda_blocked_items": blocked_items,
        "agenda_status_counts": _count_by_field(agendas, "agenda_status"),
        "institution_rule_definition_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": _execution_policy_research_agenda_report_next_action(agendas, blocked_items),
        "issues": [],
        "execution_policy_research_prep_report": prep_report,
    }
