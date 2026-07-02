from __future__ import annotations

from pathlib import Path
from typing import Any

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_review_helpers import *

def _candidate_table_update_audit_package(
    persistence_package: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    boundary_warning = list(persistence_package.get("boundary_warning", []))
    for item in [
        "candidate_table_update_audit_is_not_table_write",
        "candidate_table_update_writer_requires_separate_explicit_call",
        "candidate_table_update_audit_does_not_open_trading_layer",
        "trading_layer_read_requires_separate_gate",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "candidate_table_update_audit_result": "pass",
            "qualification_record_status": persistence_package.get("qualification_record_status"),
            "qualification_record_id": persistence_package.get("qualification_record_id"),
            "ashare_sample_id": persistence_package.get("ashare_sample_id"),
            "ts_code": persistence_package.get("ts_code"),
            "symbol_name": persistence_package.get("symbol_name"),
            "sample_window_start": persistence_package.get("sample_window_start"),
            "sample_window_end": persistence_package.get("sample_window_end"),
            "qualification_rule_id": persistence_package.get("qualification_rule_id"),
            "rhythm_meaning": persistence_package.get("rhythm_meaning"),
            "tachibana_applicability": persistence_package.get("tachibana_applicability"),
            "source_qualification_record_persistence_performed": persistence_package.get(
                "qualification_record_persistence_performed"
            ),
            "candidate_table_update_audited_at": generated_at,
            "candidate_table_update_package_prepared": True,
            "candidate_table_update_performed": False,
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_explicit_candidate_table_update_writer",
        }
    )


def _held_candidate_table_update_audit_item(
    persistence_package: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "qualification_record_id": persistence_package.get("qualification_record_id"),
            "ts_code": persistence_package.get("ts_code"),
            "qualification_rule_id": persistence_package.get("qualification_rule_id"),
            "qualification_record_status": persistence_package.get("qualification_record_status"),
            "candidate_table_update_audit_result": "hold",
            "candidate_table_update_audit_reason": reason,
            "candidate_table_update_package_prepared": False,
            "candidate_table_update_performed": False,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_candidate_table_update_audit_inputs",
        }
    )


def _qualification_record_staging_record(
    audit_package: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    boundary_warning = list(audit_package.get("boundary_warning", []))
    for item in [
        "staging_persistence_is_not_candidate_table_update",
        "staging_persistence_does_not_open_trading_layer",
        "candidate_table_update_requires_separate_explicit_call",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            **audit_package,
            "qualification_record_status": "formal_record_persisted_to_staging",
            "source_candidate_table_update_audit_result": audit_package.get("candidate_table_update_audit_result"),
            "qualification_record_persisted_at": generated_at,
            "qualification_record_persistence_performed": True,
            "qualification_record_persistence_target": "staging",
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_candidate_table_update_staging_review",
        }
    )


def _held_qualification_record_staging_item(
    audit_package: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "qualification_record_id": audit_package.get("qualification_record_id"),
            "ts_code": audit_package.get("ts_code"),
            "qualification_rule_id": audit_package.get("qualification_rule_id"),
            "candidate_table_update_audit_result": audit_package.get("candidate_table_update_audit_result"),
            "qualification_record_persistence_status": "hold",
            "qualification_record_persistence_reason": reason,
            "qualification_record_persistence_performed": False,
            "qualification_record_write_allowed": False,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_qualification_record_staging_inputs",
        }
    )


def _qualification_record_staging_blocked_report(
    candidate_table_update_audit_report: dict[str, Any],
    generated_at: str,
    issues: list[str],
    held_items: list[dict[str, Any]],
) -> dict[str, Any]:
    if not issues and not held_items:
        issues = ["qualification_record_staging_records_missing"]

    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "package_id": "qualification_record_staging_persistence_v0.1",
            "source_audit_id": candidate_table_update_audit_report.get("audit_id"),
            "issues": issues,
            "qualification_record_staging_count": 0,
            "held_qualification_record_staging_count": len(held_items),
            "held_qualification_record_staging_items": held_items,
            "qualification_record_persistence_performed": False,
            "qualification_record_persistence_target": "staging",
            "candidate_table_update_performed": False,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_qualification_record_staging_inputs",
        }
    )


def _qualification_record_staging_manifest(
    candidate_table_update_audit_report: dict[str, Any],
    generated_at: str,
    record_files: list[str],
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "manifest_id": "qualification_record_staging_manifest_v0.1",
            "generated_at": generated_at,
            "source_audit_id": candidate_table_update_audit_report.get("audit_id"),
            "qualification_record_count": len(record_files),
            "record_files": record_files,
            "qualification_record_persistence_performed": True,
            "qualification_record_persistence_target": "staging",
            "candidate_table_update_performed": False,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_candidate_table_update_staging_review",
        }
    )


def _validate_qualification_record_staging_manifest(manifest: dict[str, Any], issues: list[str]) -> None:
    if manifest.get("manifest_id") != "qualification_record_staging_manifest_v0.1":
        issues.append("qualification_record_staging_manifest_invalid")
    if manifest.get("qualification_record_persistence_performed") is not True:
        issues.append("qualification_record_staging_manifest_persistence_not_performed")
    if manifest.get("qualification_record_persistence_target") != "staging":
        issues.append("qualification_record_staging_manifest_target_not_staging")
    if manifest.get("candidate_table_update_performed") is not False:
        issues.append("qualification_record_staging_manifest_candidate_table_update_already_performed")
    if manifest.get("candidate_table_update_allowed") is not False:
        issues.append("qualification_record_staging_manifest_candidate_table_update_allowed")
    for field in ["trading_layer_read_allowed", "signal_generation_allowed", "backtest_execution_allowed"]:
        if manifest.get(field) is not False:
            issues.append(f"qualification_record_staging_manifest_{field}_must_be_false")


def _validate_staged_qualification_record(record: dict[str, Any], issues: list[str]) -> None:
    if record.get("qualification_record_status") != "formal_record_persisted_to_staging":
        issues.append("qualification_record_staging_record_status_invalid")
    if record.get("qualification_record_persistence_performed") is not True:
        issues.append("qualification_record_staging_record_persistence_not_performed")
    if record.get("qualification_record_persistence_target") != "staging":
        issues.append("qualification_record_staging_record_target_not_staging")
    if record.get("candidate_table_update_performed") is not False:
        issues.append("qualification_record_staging_record_candidate_table_update_already_performed")
    if not record.get("qualification_record_id"):
        issues.append("qualification_record_staging_record_id_missing")
    for field in ["candidate_table_update_allowed", "trading_layer_read_allowed", "signal_generation_allowed", "backtest_execution_allowed"]:
        if record.get(field) is not False:
            issues.append(f"qualification_record_staging_record_{field}_must_be_false")


def _candidate_table_staging_row(
    record: dict[str, Any],
    manifest: dict[str, Any],
    source_record_file: str,
    generated_at: str,
) -> dict[str, Any]:
    qualification_record_id = str(record.get("qualification_record_id") or "")
    boundary_warning = list(record.get("boundary_warning", []))
    for item in [
        "candidate_table_staging_is_not_formal_data_root_write",
        "candidate_table_staging_does_not_open_trading_layer",
        "formal_data_root_write_requires_separate_review",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "candidate_table_row_id": f"CANDIDATE-TABLE-ROW::{qualification_record_id}",
            "candidate_table_row_status": "staged_candidate_table_row",
            "qualification_record_id": qualification_record_id,
            "ashare_sample_id": record.get("ashare_sample_id"),
            "ts_code": record.get("ts_code"),
            "symbol_name": record.get("symbol_name"),
            "sample_window_start": record.get("sample_window_start"),
            "sample_window_end": record.get("sample_window_end"),
            "qualification_rule_id": record.get("qualification_rule_id"),
            "rhythm_meaning": record.get("rhythm_meaning"),
            "tachibana_applicability": record.get("tachibana_applicability"),
            "source_qualification_record_manifest_id": manifest.get("manifest_id"),
            "source_qualification_record_file": source_record_file,
            "candidate_table_updated_at": generated_at,
            "candidate_table_update_performed": True,
            "candidate_table_update_target": "staging",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "boundary_warning": boundary_warning,
            "next_action": "action:review_staged_candidate_table_before_formal_data_root_write",
        }
    )


def _candidate_table_staging_manifest(
    qualification_record_manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "manifest_id": "candidate_table_staging_manifest_v0.1",
            "generated_at": generated_at,
            "source_qualification_record_manifest_id": qualification_record_manifest.get("manifest_id"),
            "candidate_table_row_count": len(rows),
            "candidate_table_files": ["candidate-table-draft.jsonl"],
            "candidate_table_update_performed": True,
            "candidate_table_update_target": "staging",
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_staged_candidate_table_before_formal_data_root_write",
        }
    )


def _candidate_table_row_merge_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "qualification_record_id": row.get("qualification_record_id"),
        "ashare_sample_id": row.get("ashare_sample_id"),
        "ts_code": row.get("ts_code"),
        "symbol_name": row.get("symbol_name"),
        "sample_window_start": row.get("sample_window_start"),
        "sample_window_end": row.get("sample_window_end"),
        "qualification_rule_id": row.get("qualification_rule_id"),
        "rhythm_meaning": row.get("rhythm_meaning"),
        "tachibana_applicability": row.get("tachibana_applicability"),
        "source_qualification_record_manifest_id": row.get("source_qualification_record_manifest_id"),
        "source_qualification_record_file": row.get("source_qualification_record_file"),
    }


def _held_candidate_table_update_item(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "qualification_record_id": record.get("qualification_record_id"),
            "ts_code": record.get("ts_code"),
            "qualification_rule_id": record.get("qualification_rule_id"),
            "candidate_table_update_status": "hold",
            "candidate_table_update_reason": reason,
            "candidate_table_update_performed": False,
            "candidate_table_update_target": "staging",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_staged_candidate_table_update_inputs",
        }
    )


def _candidate_table_staging_blocked_report(
    generated_at: str,
    issues: list[str],
    held_items: list[dict[str, Any]],
) -> dict[str, Any]:
    if not issues and not held_items:
        issues = ["candidate_table_staging_rows_missing"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "package_id": "candidate_table_staging_update_v0.1",
            "issues": issues,
            "candidate_table_row_count": 0,
            "held_candidate_table_update_count": len(held_items),
            "held_candidate_table_update_items": held_items,
            "candidate_table_deduplicated_existing_row_count": 0,
            "candidate_table_update_performed": False,
            "candidate_table_update_target": "staging",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_staged_candidate_table_update_inputs",
        }
    )


def _validate_candidate_table_staging_manifest(manifest: dict[str, Any], issues: list[str]) -> None:
    if manifest.get("manifest_id") != "candidate_table_staging_manifest_v0.1":
        issues.append("candidate_table_staging_manifest_invalid")
    if manifest.get("candidate_table_update_performed") is not True:
        issues.append("candidate_table_staging_manifest_update_not_performed")
    if manifest.get("candidate_table_update_target") != "staging":
        issues.append("candidate_table_staging_manifest_target_not_staging")
    if manifest.get("candidate_table_update_allowed") is not False:
        issues.append("candidate_table_staging_manifest_candidate_table_update_allowed")
    if not manifest.get("source_qualification_record_manifest_id"):
        issues.append("candidate_table_staging_manifest_qualification_record_provenance_missing")
    for field in ["trading_layer_read_allowed", "signal_generation_allowed", "backtest_execution_allowed"]:
        if manifest.get(field) is not False:
            issues.append(f"candidate_table_staging_manifest_{field}_must_be_false")


def _candidate_table_formal_row(
    row: dict[str, Any],
    manifest: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    formal_row = dict(row)
    boundary_warning = list(formal_row.get("boundary_warning", []))
    for item in [
        "candidate_table_formal_data_root_write_does_not_open_trading_layer",
        "trading_layer_read_requires_separate_p5_audit",
        "do_not_generate_trade_from_candidate_table",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    formal_row.update(
        {
            "candidate_table_row_status": "formal_candidate_table_row",
            "source_staging_manifest_id": manifest.get("manifest_id"),
            "source_qualification_record_staging_manifest_id": manifest.get("source_qualification_record_manifest_id"),
            "candidate_table_updated_at": generated_at,
            "candidate_table_update_performed": True,
            "candidate_table_update_target": "formal_data_root",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "boundary_warning": boundary_warning,
            "next_action": "action:review_formal_candidate_table_before_trading_layer_audit",
        }
    )
    return _strip_forbidden_fields(formal_row)


def _candidate_table_formal_manifest(
    staging_manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    generated_at: str,
    backup_path: str | None,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "manifest_id": "candidate_table_formal_manifest_v0.1",
            "generated_at": generated_at,
            "source_staging_manifest_id": staging_manifest.get("manifest_id"),
            "source_qualification_record_staging_manifest_id": staging_manifest.get(
                "source_qualification_record_manifest_id"
            ),
            "candidate_table_row_count": len(rows),
            "candidate_table_file": "candidate-table.jsonl",
            "backup_path": backup_path,
            "candidate_table_update_performed": True,
            "candidate_table_update_target": "formal_data_root",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_formal_candidate_table_before_trading_layer_audit",
        }
    )


def _candidate_table_formal_blocked_report(
    generated_at: str,
    issues: list[str],
    backup_path: str | None = None,
) -> dict[str, Any]:
    if not issues:
        issues = ["candidate_table_formal_write_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "package_id": "candidate_table_formal_write_v0.1",
            "issues": issues,
            "backup_path": backup_path,
            "candidate_table_row_count": 0,
            "candidate_table_update_performed": False,
            "candidate_table_update_target": "formal_data_root",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_formal_candidate_table_write_inputs",
        }
    )


def _candidate_table_trading_readiness_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["candidate_table_trading_readiness_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "candidate_table_trading_layer_readiness_audit_v0.1",
            "candidate_table_trading_layer_readiness_audit_result": "blocked",
            "candidate_table_trading_layer_readiness_checked": False,
            "candidate_table_trading_layer_readiness_status": "blocked_before_trading_layer_read_gate_review",
            "issues": issues,
            "candidate_table_row_count": 0,
            "candidate_table_update_performed": False,
            "candidate_table_update_target": "formal_data_root",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_formal_candidate_table_before_trading_layer_readiness_audit",
        }
    )


def _trading_layer_read_gate_contract_blocked_report(
    generated_at: str,
    issues: list[str],
) -> dict[str, Any]:
    if not issues:
        issues = ["trading_layer_read_gate_contract_blocked"]
    return _strip_forbidden_fields(
        {
            "result": "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "audit_id": "trading_layer_read_gate_contract_audit_v0.1",
            "trading_layer_read_gate_contract_audit_result": "blocked",
            "trading_layer_read_gate_contract_status": "blocked_before_trading_layer_read_contract_review",
            "issues": sorted(set(issues)),
            "institution_rule_definition_allowed": False,
            "trading_layer_read_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_trading_layer_read_gate_contract_inputs",
        }
    )


__all__ = [name for name in globals() if not name.startswith("__")]
