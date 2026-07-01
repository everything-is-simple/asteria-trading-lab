from __future__ import annotations

from pathlib import Path
from typing import Any

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_candidate_helpers import *

def _institution_rule_definition_readiness_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["institution_rule_definition_readiness_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "institution_rule_definition_readiness_audit_v0.1",
            "institution_rule_definition_readiness_audit_result": "blocked",
            "institution_rule_definition_readiness_status": "blocked_before_institution_rule_definition_draft_review",
            "issues": sorted(set(issues)),
            "required_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_institution_rule_definition_readiness_inputs",
        }
    )


def _institution_rule_definition_draft_review_gate_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["institution_rule_definition_draft_review_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "institution_rule_definition_draft_review_gate_audit_v0.1",
            "institution_rule_definition_draft_review_gate_result": "blocked",
            "institution_rule_definition_draft_review_status": "blocked_before_institution_rule_definition_contract_review",
            "issues": sorted(set(issues)),
            "reviewed_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_institution_rule_definition_draft_review_inputs",
        }
    )


def _institution_rule_definition_contract_review_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["institution_rule_definition_contract_review_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "institution_rule_definition_contract_review_audit_v0.1",
            "institution_rule_definition_contract_review_result": "blocked",
            "institution_rule_definition_contract_review_status": (
                "blocked_before_explicit_institution_rule_definition_open_gate_review"
            ),
            "issues": sorted(set(issues)),
            "contract_reviewed_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_institution_rule_definition_contract_review_inputs",
        }
    )


def _explicit_institution_rule_definition_open_gate_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["explicit_institution_rule_definition_open_gate_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "explicit_institution_rule_definition_open_gate_audit_v0.1",
            "explicit_institution_rule_definition_open_gate_result": "blocked",
            "explicit_institution_rule_definition_open_gate_status": (
                "blocked_before_institution_rule_definition_open"
            ),
            "issues": sorted(set(issues)),
            "opened_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_explicit_institution_rule_definition_open_gate_inputs",
        }
    )


def _formal_institution_rule_definition_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["formal_institution_rule_definition_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "formal_institution_rule_definition_audit_v0.1",
            "formal_institution_rule_definition_result": "blocked",
            "formal_institution_rule_definition_status": (
                "blocked_before_formal_institution_rule_definition_audit_pass"
            ),
            "issues": sorted(set(issues)),
            "consumed_reviewed_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_formal_institution_rule_definition_inputs",
        }
    )


def _formal_institution_rule_definition_persistence_package_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["formal_institution_rule_definition_persistence_package_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "formal_institution_rule_definition_persistence_package_v0.1",
            "formal_institution_rule_definition_persistence_package_result": "blocked",
            "formal_institution_rule_definition_persistence_package_status": (
                "blocked_before_formal_institution_rule_definition_persistence_package_prepared"
            ),
            "formal_institution_rule_definition_persistence_package_prepared": False,
            "formal_institution_rule_definition_persistence_performed": False,
            "issues": sorted(set(issues)),
            "packaged_rule_definition_inputs": ["t1", "price_limit", "suspension_resume"],
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_formal_institution_rule_definition_persistence_package_inputs",
        }
    )


def _validate_p7c_contract_review_for_explicit_institution_rule_definition_open_gate(
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(report, dict):
        issues.append("explicit_institution_rule_definition_open_gate_requires_p7c_contract_review_pass")
        return
    if report.get("audit_id") != "institution_rule_definition_contract_review_audit_v0.1":
        issues.append("explicit_institution_rule_definition_open_gate_requires_p7c_contract_review_pass")
    if report.get("institution_rule_definition_contract_review_result") != "pass":
        issues.append("explicit_institution_rule_definition_open_gate_requires_p7c_contract_review_pass")
    if (
        report.get("institution_rule_definition_contract_review_status")
        != "ready_for_explicit_institution_rule_definition_open_gate_review"
    ):
        issues.append("explicit_institution_rule_definition_open_gate_requires_p7c_contract_review_pass")
    _append_explicit_institution_rule_definition_open_gate_downstream_issue(report, issues)


def _validate_contract_ready_draft_for_explicit_institution_rule_definition_open_gate(
    draft_input: dict[str, Any] | None,
    expected_input_type: str,
    missing_issue: str,
    issues: list[str],
) -> None:
    if not isinstance(draft_input, dict):
        issues.append(missing_issue)
        return
    if draft_input.get("rule_draft_input_type") != expected_input_type:
        issues.append(missing_issue)
    if draft_input.get("draft_input_only") is not True:
        issues.append("explicit_institution_rule_definition_open_gate_requires_draft_input_only")
    if draft_input.get("contract_review_status") != "ready":
        issues.append("explicit_institution_rule_definition_open_gate_requires_ready_contract_review")
    definition_contract_fields = draft_input.get("definition_contract_fields")
    if not isinstance(definition_contract_fields, list) or not definition_contract_fields:
        issues.append("explicit_institution_rule_definition_open_gate_requires_definition_contract_fields")
    if draft_input.get("consumer_entrypoint") != "institution_rule_definition":
        issues.append("explicit_institution_rule_definition_open_gate_requires_definition_consumer_entrypoint")
    _append_explicit_institution_rule_definition_open_gate_downstream_issue(draft_input, issues)


def _validate_explicit_open_gate_decision_for_institution_rule_definition(
    decision: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(decision, dict):
        issues.append("explicit_institution_rule_definition_open_gate_requires_explicit_open_gate_decision")
        return
    if decision.get("gate_decision") != "approve_institution_rule_definition_only":
        issues.append("explicit_institution_rule_definition_open_gate_requires_rule_definition_only_decision")
    if decision.get("gate_scope") != "institution_rule_definition_only":
        issues.append("explicit_institution_rule_definition_open_gate_requires_rule_definition_only_scope")
    if not str(decision.get("approved_by", "")).strip():
        issues.append("explicit_institution_rule_definition_open_gate_requires_approval_identity")
    approval_evidence_refs = decision.get("approval_evidence_refs")
    if not isinstance(approval_evidence_refs, list) or not approval_evidence_refs:
        issues.append("explicit_institution_rule_definition_open_gate_requires_approval_evidence_refs")
    if (
        decision.get("acknowledged_no_trading_layer_read") is not True
        or decision.get("acknowledged_no_signal_generation") is not True
        or decision.get("acknowledged_no_backtest_execution") is not True
    ):
        issues.append("explicit_institution_rule_definition_open_gate_requires_no_downstream_acknowledgement")
    _append_explicit_institution_rule_definition_open_gate_downstream_issue(decision, issues)


def _append_explicit_institution_rule_definition_open_gate_downstream_issue(
    payload: dict[str, Any],
    issues: list[str],
) -> None:
    for field in [
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if payload.get(field) not in {None, False}:
            issues.append("explicit_institution_rule_definition_open_gate_downstream_gate_open")


def _validate_p7d_open_gate_for_formal_institution_rule_definition(
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(report, dict):
        issues.append("formal_institution_rule_definition_requires_p7d_open_gate_pass")
        return
    if report.get("audit_id") != "explicit_institution_rule_definition_open_gate_audit_v0.1":
        issues.append("formal_institution_rule_definition_requires_p7d_open_gate_pass")
    if report.get("explicit_institution_rule_definition_open_gate_result") != "pass":
        issues.append("formal_institution_rule_definition_requires_p7d_open_gate_pass")
    if (
        report.get("explicit_institution_rule_definition_open_gate_status")
        != "institution_rule_definition_opened_for_rule_definition_only"
    ):
        issues.append("formal_institution_rule_definition_requires_p7d_open_gate_pass")
    if report.get("institution_rule_definition_allowed") is not True:
        issues.append("formal_institution_rule_definition_requires_p7d_open_gate_pass")
    _append_formal_institution_rule_definition_downstream_issue(report, issues)


def _validate_contract_ready_draft_for_formal_institution_rule_definition(
    draft_input: dict[str, Any] | None,
    expected_input_type: str,
    missing_issue: str,
    issues: list[str],
) -> None:
    if not isinstance(draft_input, dict):
        issues.append(missing_issue)
        return
    if draft_input.get("rule_draft_input_type") != expected_input_type:
        issues.append(missing_issue)
    if draft_input.get("draft_input_only") is not True:
        issues.append("formal_institution_rule_definition_requires_draft_input_only")
    if draft_input.get("contract_review_status") != "ready":
        issues.append("formal_institution_rule_definition_requires_ready_contract_review")
    definition_contract_fields = draft_input.get("definition_contract_fields")
    if not isinstance(definition_contract_fields, list) or not definition_contract_fields:
        issues.append("formal_institution_rule_definition_requires_definition_contract_fields")
    if draft_input.get("consumer_entrypoint") != "institution_rule_definition":
        issues.append("formal_institution_rule_definition_requires_definition_consumer_entrypoint")
    _append_formal_institution_rule_definition_downstream_issue(draft_input, issues)


def _validate_formal_institution_rule_definition_input(
    definition_input: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(definition_input, dict):
        issues.append("formal_institution_rule_definition_requires_definition_input")
        return
    if definition_input.get("artifact_id") != "formal_institution_rule_definition_input_v0.1":
        issues.append("formal_institution_rule_definition_requires_definition_input")
    if definition_input.get("definition_scope") != "institution_rule_definition_only":
        issues.append("formal_institution_rule_definition_requires_rule_definition_only_scope")
    if definition_input.get("definition_input_status") != "ready_for_audit":
        issues.append("formal_institution_rule_definition_requires_ready_definition_input")
    consumed_reviewed_draft_inputs = definition_input.get("consumed_reviewed_draft_inputs")
    if consumed_reviewed_draft_inputs != ["t1", "price_limit", "suspension_resume"]:
        issues.append("formal_institution_rule_definition_requires_full_reviewed_draft_coverage")
    if definition_input.get("field_contract_status") != "complete":
        issues.append("formal_institution_rule_definition_requires_complete_field_contract")
    if definition_input.get("boundary_review_status") != "clean":
        issues.append("formal_institution_rule_definition_requires_clean_boundary")
    evidence_refs = definition_input.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        issues.append("formal_institution_rule_definition_requires_evidence_refs")
    formal_definition_fields = definition_input.get("formal_definition_fields")
    if not isinstance(formal_definition_fields, list) or not formal_definition_fields:
        issues.append("formal_institution_rule_definition_requires_formal_definition_fields")
    if definition_input.get("institution_rule_definition_allowed") is not True:
        issues.append("formal_institution_rule_definition_requires_rule_definition_only_gate_open")
    _append_formal_institution_rule_definition_downstream_issue(definition_input, issues)


def _append_formal_institution_rule_definition_downstream_issue(
    payload: dict[str, Any],
    issues: list[str],
) -> None:
    for field in [
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if payload.get(field) not in {None, False}:
            issues.append("formal_institution_rule_definition_downstream_gate_open")


def _validate_p7e_report_for_formal_institution_rule_definition_persistence_package(
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(report, dict):
        issues.append("formal_institution_rule_definition_persistence_package_requires_p7e_pass")
        return
    if report.get("audit_id") != "formal_institution_rule_definition_audit_v0.1":
        issues.append("formal_institution_rule_definition_persistence_package_requires_p7e_pass")
    if report.get("formal_institution_rule_definition_result") != "pass":
        issues.append("formal_institution_rule_definition_persistence_package_requires_p7e_pass")
    if (
        report.get("formal_institution_rule_definition_status")
        != "formal_institution_rule_definition_audited_for_rule_definition_only"
    ):
        issues.append("formal_institution_rule_definition_persistence_package_requires_p7e_pass")
    if report.get("institution_rule_definition_allowed") is not True:
        issues.append("formal_institution_rule_definition_persistence_package_requires_p7e_pass")
    _append_formal_institution_rule_definition_persistence_package_downstream_issue(report, issues)


def _validate_formal_institution_rule_definition_payload_for_persistence_package(
    definition_payload: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(definition_payload, dict):
        issues.append("formal_institution_rule_definition_persistence_package_requires_definition_payload")
        return
    if definition_payload.get("artifact_id") != "formal_institution_rule_definition_input_v0.1":
        issues.append("formal_institution_rule_definition_persistence_package_requires_definition_payload")
    if definition_payload.get("definition_scope") != "institution_rule_definition_only":
        issues.append("formal_institution_rule_definition_persistence_package_requires_rule_definition_only_scope")
    if definition_payload.get("definition_input_status") != "ready_for_audit":
        issues.append("formal_institution_rule_definition_persistence_package_requires_ready_definition_payload")
    consumed_reviewed_draft_inputs = definition_payload.get("consumed_reviewed_draft_inputs")
    if consumed_reviewed_draft_inputs != ["t1", "price_limit", "suspension_resume"]:
        issues.append("formal_institution_rule_definition_persistence_package_requires_full_reviewed_draft_coverage")
    if definition_payload.get("field_contract_status") != "complete":
        issues.append("formal_institution_rule_definition_persistence_package_requires_complete_field_contract")
    if definition_payload.get("boundary_review_status") != "clean":
        issues.append("formal_institution_rule_definition_persistence_package_requires_clean_boundary")
    evidence_refs = definition_payload.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        issues.append("formal_institution_rule_definition_persistence_package_requires_evidence_refs")
    formal_definition_fields = definition_payload.get("formal_definition_fields")
    if not isinstance(formal_definition_fields, list) or not formal_definition_fields:
        issues.append("formal_institution_rule_definition_persistence_package_requires_formal_definition_fields")
    if definition_payload.get("institution_rule_definition_allowed") is not True:
        issues.append("formal_institution_rule_definition_persistence_package_requires_rule_definition_only_gate_open")
    _append_formal_institution_rule_definition_persistence_package_downstream_issue(definition_payload, issues)


def _append_formal_institution_rule_definition_persistence_package_downstream_issue(
    payload: dict[str, Any],
    issues: list[str],
) -> None:
    for field in [
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if payload.get(field) not in {None, False}:
            issues.append("formal_institution_rule_definition_persistence_package_downstream_gate_open")


def _validate_p7b_draft_review_for_institution_rule_definition_contract_review(
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(report, dict):
        issues.append("institution_rule_definition_contract_review_requires_p7b_draft_review_gate_pass")
        return
    if report.get("audit_id") != "institution_rule_definition_draft_review_gate_audit_v0.1":
        issues.append("institution_rule_definition_contract_review_requires_p7b_draft_review_gate_pass")
    if report.get("institution_rule_definition_draft_review_gate_result") != "pass":
        issues.append("institution_rule_definition_contract_review_requires_p7b_draft_review_gate_pass")
    if report.get("institution_rule_definition_draft_review_status") != "ready_for_institution_rule_definition_contract_review":
        issues.append("institution_rule_definition_contract_review_requires_p7b_draft_review_gate_pass")
    _append_institution_rule_definition_contract_review_downstream_issue(report, issues)


def _validate_contract_ready_draft_for_institution_rule_definition_contract_review(
    draft_input: dict[str, Any] | None,
    expected_input_type: str,
    missing_issue: str,
    issues: list[str],
) -> None:
    if not isinstance(draft_input, dict):
        issues.append(missing_issue)
        return
    if draft_input.get("rule_draft_input_type") != expected_input_type:
        issues.append(missing_issue)
    if draft_input.get("draft_input_only") is not True:
        issues.append("institution_rule_definition_contract_review_requires_draft_input_only")
    if draft_input.get("draft_quality_status") != "ready_for_review":
        issues.append("institution_rule_definition_contract_review_requires_ready_quality")
    if draft_input.get("field_contract_status") != "complete":
        issues.append("institution_rule_definition_contract_review_requires_complete_field_contract")
    evidence_refs = draft_input.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        issues.append("institution_rule_definition_contract_review_requires_evidence_refs")
    if draft_input.get("boundary_review_status") != "clean":
        issues.append("institution_rule_definition_contract_review_requires_clean_boundary")
    if draft_input.get("contract_review_status") != "ready":
        issues.append("institution_rule_definition_contract_review_requires_ready_contract_review")
    definition_contract_fields = draft_input.get("definition_contract_fields")
    if not isinstance(definition_contract_fields, list) or not definition_contract_fields:
        issues.append("institution_rule_definition_contract_review_requires_definition_contract_fields")
    if draft_input.get("consumer_entrypoint") != "institution_rule_definition":
        issues.append("institution_rule_definition_contract_review_requires_definition_consumer_entrypoint")
    _append_institution_rule_definition_contract_review_downstream_issue(draft_input, issues)


def _append_institution_rule_definition_contract_review_downstream_issue(
    payload: dict[str, Any],
    issues: list[str],
) -> None:
    for field in [
        "institution_rule_definition_allowed",
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if payload.get(field) not in {None, False}:
            issues.append("institution_rule_definition_contract_review_downstream_gate_open")


def _validate_p7a_readiness_for_institution_rule_definition_draft_review(
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(report, dict):
        issues.append("institution_rule_definition_draft_review_requires_p7a_readiness_pass")
        return
    if report.get("audit_id") != "institution_rule_definition_readiness_audit_v0.1":
        issues.append("institution_rule_definition_draft_review_requires_p7a_readiness_pass")
    if report.get("institution_rule_definition_readiness_audit_result") != "pass":
        issues.append("institution_rule_definition_draft_review_requires_p7a_readiness_pass")
    if report.get("institution_rule_definition_readiness_status") != "ready_for_institution_rule_definition_draft_review":
        issues.append("institution_rule_definition_draft_review_requires_p7a_readiness_pass")
    _append_institution_rule_definition_draft_review_downstream_issue(report, issues)


def _validate_review_ready_draft_for_institution_rule_definition_draft_review(
    draft_input: dict[str, Any] | None,
    expected_input_type: str,
    missing_issue: str,
    issues: list[str],
) -> None:
    if not isinstance(draft_input, dict):
        issues.append(missing_issue)
        return
    if draft_input.get("rule_draft_input_type") != expected_input_type:
        issues.append(missing_issue)
    if draft_input.get("draft_input_only") is not True:
        issues.append("institution_rule_definition_draft_review_requires_draft_input_only")
    if draft_input.get("draft_quality_status") != "ready_for_review":
        issues.append("institution_rule_definition_draft_review_requires_ready_quality")
    if draft_input.get("field_contract_status") != "complete":
        issues.append("institution_rule_definition_draft_review_requires_complete_field_contract")
    evidence_refs = draft_input.get("evidence_refs")
    if not isinstance(evidence_refs, list) or not evidence_refs:
        issues.append("institution_rule_definition_draft_review_requires_evidence_refs")
    if draft_input.get("boundary_review_status") != "clean":
        issues.append("institution_rule_definition_draft_review_requires_clean_boundary")
    _append_institution_rule_definition_draft_review_downstream_issue(draft_input, issues)


def _append_institution_rule_definition_draft_review_downstream_issue(
    payload: dict[str, Any],
    issues: list[str],
) -> None:
    for field in [
        "institution_rule_definition_allowed",
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if payload.get(field) not in {None, False}:
            issues.append("institution_rule_definition_draft_review_downstream_gate_open")


def _validate_p6_contract_for_institution_rule_definition_readiness(
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(report, dict):
        issues.append("institution_rule_definition_readiness_requires_p6_contract_pass")
        return
    if report.get("audit_id") != "trading_layer_read_gate_contract_audit_v0.1":
        issues.append("institution_rule_definition_readiness_requires_p6_contract_pass")
    if report.get("trading_layer_read_gate_contract_audit_result") != "pass":
        issues.append("institution_rule_definition_readiness_requires_p6_contract_pass")
    if report.get("trading_layer_read_gate_contract_status") != "ready_for_trading_layer_read_contract_review":
        issues.append("institution_rule_definition_readiness_requires_p6_contract_pass")
    if report.get("execution_constraint_audit_only") is not True:
        issues.append("institution_rule_definition_readiness_requires_p6_contract_pass")
    _append_institution_rule_definition_readiness_downstream_issue(report, issues)


def _validate_rule_draft_input_for_institution_rule_definition_readiness(
    draft_input: dict[str, Any] | None,
    expected_input_type: str,
    missing_issue: str,
    issues: list[str],
) -> None:
    if not isinstance(draft_input, dict):
        issues.append(missing_issue)
        return
    if draft_input.get("rule_draft_input_type") != expected_input_type:
        issues.append(missing_issue)
    if draft_input.get("draft_input_only") is not True:
        issues.append("institution_rule_definition_readiness_requires_draft_input_only")
    if not _rule_draft_input_passes(draft_input):
        issues.append(missing_issue)
    _append_institution_rule_definition_readiness_downstream_issue(draft_input, issues)


def _rule_draft_input_passes(draft_input: dict[str, Any]) -> bool:
    if "result" in draft_input:
        return draft_input.get("result") == "pass"
    return draft_input.get("readiness") == "pass"


def _append_institution_rule_definition_readiness_downstream_issue(
    payload: dict[str, Any],
    issues: list[str],
) -> None:
    for field in [
        "institution_rule_definition_allowed",
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if payload.get(field) not in {None, False}:
            issues.append("institution_rule_definition_readiness_downstream_gate_open")


def _validate_p5_readiness_for_trading_layer_read_gate(
    report: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(report, dict):
        issues.append("trading_layer_read_gate_requires_p5_readiness_pass")
        return
    if report.get("audit_id") != "candidate_table_trading_layer_readiness_audit_v0.1":
        issues.append("trading_layer_read_gate_requires_p5_readiness_pass")
    if report.get("candidate_table_trading_layer_readiness_audit_result") != "pass":
        issues.append("trading_layer_read_gate_requires_p5_readiness_pass")
    if report.get("candidate_table_trading_layer_readiness_status") != "ready_for_trading_layer_read_gate_review":
        issues.append("trading_layer_read_gate_requires_p5_readiness_pass")
    _append_trading_layer_read_gate_downstream_issue(report, issues)


def _validate_formal_candidate_table_for_trading_layer_read_gate(
    manifest: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(manifest, dict):
        issues.append("trading_layer_read_gate_requires_formal_candidate_table")
        return
    if manifest.get("manifest_id") != "candidate_table_formal_manifest_v0.1":
        issues.append("trading_layer_read_gate_requires_formal_candidate_table")
    if manifest.get("candidate_table_update_target") != "formal_data_root":
        issues.append("trading_layer_read_gate_requires_formal_candidate_table")
    if manifest.get("trading_layer_read_allowed") is not False:
        issues.append("trading_layer_read_gate_requires_formal_candidate_table")
    _append_trading_layer_read_gate_downstream_issue(manifest, issues)


def _validate_method_pm_gate_for_trading_layer_read_gate(
    gate: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(gate, dict):
        issues.append("trading_layer_read_gate_requires_method_pm_gate_pass")
        return
    if not _read_gate_passes(gate, "method_pm_readiness"):
        issues.append("trading_layer_read_gate_requires_method_pm_gate_pass")
    _append_trading_layer_read_gate_downstream_issue(gate, issues)


def _validate_backtest_input_gate_for_trading_layer_read_gate(
    gate: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(gate, dict):
        issues.append("trading_layer_read_gate_requires_backtest_input_gate_pass")
        return
    if not _read_gate_passes(gate, "backtest_input_readiness"):
        issues.append("trading_layer_read_gate_requires_backtest_input_gate_pass")
    _append_trading_layer_read_gate_downstream_issue(gate, issues)


def _validate_execution_constraint_for_trading_layer_read_gate(
    artifact: dict[str, Any] | None,
    issues: list[str],
) -> None:
    if not isinstance(artifact, dict):
        issues.append("trading_layer_read_gate_requires_execution_constraint_audit_only")
        return
    if not _audit_only_artifact_passes(artifact):
        issues.append("trading_layer_read_gate_requires_execution_constraint_audit_only")
    if artifact.get("institution_rule_definition_allowed") is not False:
        issues.append("trading_layer_read_gate_requires_execution_constraint_audit_only")
    _append_trading_layer_read_gate_downstream_issue(artifact, issues)


def _read_gate_passes(gate: dict[str, Any], readiness_field: str) -> bool:
    if "result" in gate:
        return gate.get("result") == "pass"
    return gate.get(readiness_field) == "pass"


def _audit_only_artifact_passes(artifact: dict[str, Any]) -> bool:
    if "audit_only" in artifact:
        return artifact.get("audit_only") is True
    return artifact.get("execution_constraint_audit_only") is True


def _append_trading_layer_read_gate_downstream_issue(
    payload: dict[str, Any],
    issues: list[str],
) -> None:
    for field in [
        "institution_rule_definition_allowed",
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if payload.get(field) not in {None, False}:
            issues.append("trading_layer_read_gate_downstream_gate_open")


__all__ = [name for name in globals() if not name.startswith("__")]
