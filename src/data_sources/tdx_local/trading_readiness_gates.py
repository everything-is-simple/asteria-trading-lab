from __future__ import annotations

from pathlib import Path
from typing import Any

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_candidate_helpers import *
from .first_batch_formal_candidate_helpers import *
from .first_batch_rule_definition_helpers import *
from .candidate_table_gates import *

def audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
    formal_candidate_table_manifest_path: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    manifest_path = Path(formal_candidate_table_manifest_path)
    issues: list[str] = []

    if not manifest_path.exists():
        return _candidate_table_trading_readiness_blocked_report(
            generated_at_value,
            ["candidate_table_formal_manifest_missing"],
        )

    manifest = _read_json_file(manifest_path)
    if manifest is None:
        return _candidate_table_trading_readiness_blocked_report(
            generated_at_value,
            ["candidate_table_formal_manifest_invalid"],
        )

    _validate_candidate_table_formal_manifest_for_trading_readiness(manifest, issues)
    table_path = _candidate_table_jsonl_path_from_manifest(manifest_path, manifest, issues)
    table_exists = table_path.exists()
    rows = _read_candidate_table_jsonl(table_path) if not issues else None
    if rows is None:
        issues.append("candidate_table_formal_jsonl_invalid" if table_exists else "candidate_table_formal_jsonl_missing")
        rows = []
    elif not table_exists:
        issues.append("candidate_table_formal_jsonl_missing")
    _validate_candidate_table_formal_rows_for_trading_readiness(
        rows,
        manifest.get("candidate_table_row_count"),
        issues,
    )

    if issues:
        return _candidate_table_trading_readiness_blocked_report(generated_at_value, issues)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "candidate_table_trading_layer_readiness_audit_v0.1",
            "candidate_table_trading_layer_readiness_audit_result": "pass",
            "candidate_table_trading_layer_readiness_checked": True,
            "candidate_table_trading_layer_readiness_status": "ready_for_trading_layer_read_gate_review",
            "formal_candidate_table_manifest_path": str(manifest_path),
            "formal_candidate_table_path": str(table_path),
            "candidate_table_row_count": len(rows),
            "candidate_table_update_performed": True,
            "candidate_table_update_target": "formal_data_root",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:write_p5_implementation_plan_for_trading_layer_readiness_audit",
        }
    )


def audit_trading_layer_read_gate_contract_when_explicitly_requested(
    p5_readiness_report: dict[str, Any] | None,
    formal_candidate_table_manifest: dict[str, Any] | None,
    method_pm_gate: dict[str, Any] | None,
    backtest_input_gate: dict[str, Any] | None,
    execution_constraint_artifact: dict[str, Any] | None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    issues: list[str] = []

    inputs = [
        p5_readiness_report,
        formal_candidate_table_manifest,
        method_pm_gate,
        backtest_input_gate,
        execution_constraint_artifact,
    ]
    if any(isinstance(item, dict) and _first_forbidden_output_field_present(item) is not None for item in inputs):
        issues.append("trading_layer_read_gate_forbidden_output_field_present")

    _validate_p5_readiness_for_trading_layer_read_gate(p5_readiness_report, issues)
    _validate_formal_candidate_table_for_trading_layer_read_gate(formal_candidate_table_manifest, issues)
    _validate_method_pm_gate_for_trading_layer_read_gate(method_pm_gate, issues)
    _validate_backtest_input_gate_for_trading_layer_read_gate(backtest_input_gate, issues)
    _validate_execution_constraint_for_trading_layer_read_gate(execution_constraint_artifact, issues)

    if issues:
        return _trading_layer_read_gate_contract_blocked_report(generated_at_value, issues)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "trading_layer_read_gate_contract_audit_v0.1",
            "trading_layer_read_gate_contract_audit_result": "pass",
            "trading_layer_read_gate_contract_status": "ready_for_trading_layer_read_contract_review",
            "candidate_table_trading_layer_readiness_audit_result": "pass",
            "method_pm_gate_result": "pass",
            "backtest_input_gate_result": "pass",
            "execution_constraint_audit_only": True,
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_trading_layer_read_gate_contract",
        }
    )
