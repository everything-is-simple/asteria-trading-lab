from __future__ import annotations

from pathlib import Path
from typing import Any

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_rule_definition_helpers import *
from .trading_readiness_gates import *

def audit_institution_rule_definition_readiness_when_explicitly_requested(
    p6_contract_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        p6_contract_report,
        t1_rule_draft_input,
        price_limit_rule_draft_input,
        suspension_resume_rule_draft_input,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("institution_rule_definition_readiness_forbidden_output_field_present")

    _validate_p6_contract_for_institution_rule_definition_readiness(p6_contract_report, issues)
    _validate_rule_draft_input_for_institution_rule_definition_readiness(
        t1_rule_draft_input,
        "t1",
        "institution_rule_definition_readiness_requires_t1_draft_input",
        issues,
    )
    _validate_rule_draft_input_for_institution_rule_definition_readiness(
        price_limit_rule_draft_input,
        "price_limit",
        "institution_rule_definition_readiness_requires_price_limit_draft_input",
        issues,
    )
    _validate_rule_draft_input_for_institution_rule_definition_readiness(
        suspension_resume_rule_draft_input,
        "suspension_resume",
        "institution_rule_definition_readiness_requires_suspension_resume_draft_input",
        issues,
    )

    if issues:
        return _institution_rule_definition_readiness_blocked_report(generated_at_value, issues)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "institution_rule_definition_readiness_audit_v0.1",
            "institution_rule_definition_readiness_audit_result": "pass",
            "institution_rule_definition_readiness_status": "ready_for_institution_rule_definition_draft_review",
            "p6_contract_audit_result": "pass",
            "required_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "draft_input_only": True,
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_institution_rule_definition_drafts",
        }
    )


def audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
    p7a_readiness_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        p7a_readiness_report,
        t1_rule_draft_input,
        price_limit_rule_draft_input,
        suspension_resume_rule_draft_input,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("institution_rule_definition_draft_review_forbidden_output_field_present")

    _validate_p7a_readiness_for_institution_rule_definition_draft_review(p7a_readiness_report, issues)
    _validate_review_ready_draft_for_institution_rule_definition_draft_review(
        t1_rule_draft_input,
        "t1",
        "institution_rule_definition_draft_review_requires_t1_review_ready_draft",
        issues,
    )
    _validate_review_ready_draft_for_institution_rule_definition_draft_review(
        price_limit_rule_draft_input,
        "price_limit",
        "institution_rule_definition_draft_review_requires_price_limit_review_ready_draft",
        issues,
    )
    _validate_review_ready_draft_for_institution_rule_definition_draft_review(
        suspension_resume_rule_draft_input,
        "suspension_resume",
        "institution_rule_definition_draft_review_requires_suspension_resume_review_ready_draft",
        issues,
    )

    if issues:
        return _institution_rule_definition_draft_review_gate_blocked_report(generated_at_value, issues)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "institution_rule_definition_draft_review_gate_audit_v0.1",
            "institution_rule_definition_draft_review_gate_result": "pass",
            "institution_rule_definition_draft_review_status": "ready_for_institution_rule_definition_contract_review",
            "p7a_readiness_audit_result": "pass",
            "reviewed_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "draft_review_gate_only": True,
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:write_p7c_institution_rule_definition_contract_review_spec",
        }
    )


def audit_institution_rule_definition_contract_review_when_explicitly_requested(
    p7b_draft_review_gate_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        p7b_draft_review_gate_report,
        t1_rule_draft_input,
        price_limit_rule_draft_input,
        suspension_resume_rule_draft_input,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("institution_rule_definition_contract_review_forbidden_output_field_present")

    _validate_p7b_draft_review_for_institution_rule_definition_contract_review(
        p7b_draft_review_gate_report,
        issues,
    )
    _validate_contract_ready_draft_for_institution_rule_definition_contract_review(
        t1_rule_draft_input,
        "t1",
        "institution_rule_definition_contract_review_requires_t1_contract_ready_draft",
        issues,
    )
    _validate_contract_ready_draft_for_institution_rule_definition_contract_review(
        price_limit_rule_draft_input,
        "price_limit",
        "institution_rule_definition_contract_review_requires_price_limit_contract_ready_draft",
        issues,
    )
    _validate_contract_ready_draft_for_institution_rule_definition_contract_review(
        suspension_resume_rule_draft_input,
        "suspension_resume",
        "institution_rule_definition_contract_review_requires_suspension_resume_contract_ready_draft",
        issues,
    )

    if issues:
        return _institution_rule_definition_contract_review_blocked_report(generated_at_value, issues)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "institution_rule_definition_contract_review_audit_v0.1",
            "institution_rule_definition_contract_review_result": "pass",
            "institution_rule_definition_contract_review_status": (
                "ready_for_explicit_institution_rule_definition_open_gate_review"
            ),
            "p7b_draft_review_gate_result": "pass",
            "contract_reviewed_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "contract_review_only": True,
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_explicit_institution_rule_definition_open_gate",
        }
    )


def audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
    p7c_contract_review_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    explicit_open_gate_decision: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        p7c_contract_review_report,
        t1_rule_draft_input,
        price_limit_rule_draft_input,
        suspension_resume_rule_draft_input,
        explicit_open_gate_decision,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("explicit_institution_rule_definition_open_gate_forbidden_output_field_present")

    _validate_p7c_contract_review_for_explicit_institution_rule_definition_open_gate(
        p7c_contract_review_report,
        issues,
    )
    _validate_contract_ready_draft_for_explicit_institution_rule_definition_open_gate(
        t1_rule_draft_input,
        "t1",
        "explicit_institution_rule_definition_open_gate_requires_t1_contract_ready_draft",
        issues,
    )
    _validate_contract_ready_draft_for_explicit_institution_rule_definition_open_gate(
        price_limit_rule_draft_input,
        "price_limit",
        "explicit_institution_rule_definition_open_gate_requires_price_limit_contract_ready_draft",
        issues,
    )
    _validate_contract_ready_draft_for_explicit_institution_rule_definition_open_gate(
        suspension_resume_rule_draft_input,
        "suspension_resume",
        "explicit_institution_rule_definition_open_gate_requires_suspension_resume_contract_ready_draft",
        issues,
    )
    _validate_explicit_open_gate_decision_for_institution_rule_definition(
        explicit_open_gate_decision,
        issues,
    )

    if issues:
        return _explicit_institution_rule_definition_open_gate_blocked_report(generated_at_value, issues)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "explicit_institution_rule_definition_open_gate_audit_v0.1",
            "explicit_institution_rule_definition_open_gate_result": "pass",
            "explicit_institution_rule_definition_open_gate_status": (
                "institution_rule_definition_opened_for_rule_definition_only"
            ),
            "p7c_contract_review_result": "pass",
            "opened_rule_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "institution_rule_definition_allowed": True,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:define_formal_institution_rules_only",
        }
    )


def audit_formal_institution_rule_definition_when_explicitly_requested(
    p7d_open_gate_report: dict[str, Any] | None,
    t1_rule_draft_input: dict[str, Any] | None,
    price_limit_rule_draft_input: dict[str, Any] | None,
    suspension_resume_rule_draft_input: dict[str, Any] | None,
    formal_institution_rule_definition_input: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        p7d_open_gate_report,
        t1_rule_draft_input,
        price_limit_rule_draft_input,
        suspension_resume_rule_draft_input,
        formal_institution_rule_definition_input,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("formal_institution_rule_definition_forbidden_output_field_present")

    _validate_p7d_open_gate_for_formal_institution_rule_definition(p7d_open_gate_report, issues)
    _validate_contract_ready_draft_for_formal_institution_rule_definition(
        t1_rule_draft_input,
        "t1",
        "formal_institution_rule_definition_requires_t1_contract_ready_draft",
        issues,
    )
    _validate_contract_ready_draft_for_formal_institution_rule_definition(
        price_limit_rule_draft_input,
        "price_limit",
        "formal_institution_rule_definition_requires_price_limit_contract_ready_draft",
        issues,
    )
    _validate_contract_ready_draft_for_formal_institution_rule_definition(
        suspension_resume_rule_draft_input,
        "suspension_resume",
        "formal_institution_rule_definition_requires_suspension_resume_contract_ready_draft",
        issues,
    )
    _validate_formal_institution_rule_definition_input(
        formal_institution_rule_definition_input,
        issues,
    )

    if issues:
        return _formal_institution_rule_definition_blocked_report(generated_at_value, issues)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "formal_institution_rule_definition_audit_v0.1",
            "formal_institution_rule_definition_result": "pass",
            "formal_institution_rule_definition_status": (
                "formal_institution_rule_definition_audited_for_rule_definition_only"
            ),
            "p7d_open_gate_result": "pass",
            "consumed_reviewed_draft_inputs": ["t1", "price_limit", "suspension_resume"],
            "formal_institution_rule_definition_field_contract_status": "complete",
            "formal_institution_rule_definition_boundary_status": "clean",
            "formal_institution_rule_definition_evidence_status": "ready",
            "institution_rule_definition_allowed": True,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": (
                "action:prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested"
            ),
        }
    )


def prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
    p7e_formal_rule_definition_report: dict[str, Any] | None,
    formal_institution_rule_definition_payload: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        p7e_formal_rule_definition_report,
        formal_institution_rule_definition_payload,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("formal_institution_rule_definition_persistence_package_forbidden_output_field_present")

    _validate_p7e_report_for_formal_institution_rule_definition_persistence_package(
        p7e_formal_rule_definition_report,
        issues,
    )
    _validate_formal_institution_rule_definition_payload_for_persistence_package(
        formal_institution_rule_definition_payload,
        issues,
    )

    if issues:
        return _formal_institution_rule_definition_persistence_package_blocked_report(
            generated_at_value,
            issues,
        )

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "formal_institution_rule_definition_persistence_package_v0.1",
            "report_id": "formal_institution_rule_definition_persistence_package_report_v0.1",
            "package_id": "formal_institution_rule_definition_persistence_package_v0.1",
            "package_version": "v0.1",
            "formal_institution_rule_definition_persistence_package_result": "pass",
            "formal_institution_rule_definition_persistence_package_status": (
                "formal_institution_rule_definition_persistence_package_prepared"
            ),
            "formal_institution_rule_definition_persistence_package_prepared": True,
            "formal_institution_rule_definition_persistence_performed": False,
            "source_formal_institution_rule_definition_result": "pass",
            "packaged_rule_definition_inputs": ["t1", "price_limit", "suspension_resume"],
            "package_field_contract_status": "complete",
            "package_boundary_status": "clean",
            "package_evidence_status": "ready",
            "institution_rule_definition_allowed": True,
            "institution_rule_definition_scope": "rule-definition-only",
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:audit_formal_institution_rule_definition_write_when_explicitly_requested",
        }
    )


def audit_formal_institution_rule_definition_write_when_explicitly_requested(
    formal_rule_definition_persistence_package_report: dict[str, Any] | None,
    formal_rule_definition_write_audit_request: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        formal_rule_definition_persistence_package_report,
        formal_rule_definition_write_audit_request,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("formal_institution_rule_definition_write_audit_forbidden_output_field_present")

    _validate_p8_package_for_formal_institution_rule_definition_write_audit(
        formal_rule_definition_persistence_package_report,
        issues,
    )
    _validate_formal_institution_rule_definition_write_audit_request(
        formal_rule_definition_write_audit_request,
        formal_rule_definition_persistence_package_report,
        issues,
    )

    if issues:
        return _formal_institution_rule_definition_write_audit_blocked_report(
            generated_at_value,
            issues,
        )

    assert isinstance(formal_rule_definition_persistence_package_report, dict)
    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "formal_institution_rule_definition_write_audit_v0.1",
            "formal_institution_rule_definition_write_audit_result": "pass",
            "formal_institution_rule_definition_write_audit_status": (
                "ready_for_formal_institution_rule_definition_explicit_write_confirmation_gate"
            ),
            "formal_institution_rule_definition_write_allowed": False,
            "formal_institution_rule_definition_persistence_performed": False,
            "source_package_id": formal_rule_definition_persistence_package_report.get("package_id"),
            "source_package_version": formal_rule_definition_persistence_package_report.get("package_version"),
            "institution_rule_definition_allowed": True,
            "institution_rule_definition_scope": "rule-definition-only",
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_gate": "gate:formal_institution_rule_definition_explicit_write_confirmation",
            "package_staleness_policy": "not_enforced_v0.1",
            "write_audit_idempotency_policy": "same_package_identity_is_idempotent_v0.1",
        }
    )
