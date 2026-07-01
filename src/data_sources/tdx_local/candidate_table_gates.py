from __future__ import annotations

from pathlib import Path
from typing import Any

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_candidate_helpers import *
from .first_batch_formal_candidate_helpers import *
from .first_batch_reviews import *

def prepare_candidate_table_update_audit_when_explicitly_requested(
    persistence_package_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    audit_packages: list[dict[str, Any]] = []
    held_items: list[dict[str, Any]] = []
    issues: list[str] = []

    persistence_packages = persistence_package_report.get("qualification_record_persistence_packages", [])
    if not isinstance(persistence_packages, list) or not persistence_packages:
        issues.append("qualification_record_persistence_packages_missing")
        persistence_packages = []

    for persistence_package in persistence_packages:
        if not isinstance(persistence_package, dict):
            issues.append("invalid_qualification_record_persistence_package")
            continue

        forbidden_field = _first_forbidden_output_field_present(persistence_package)
        if forbidden_field is not None:
            held_items.append(
                _held_candidate_table_update_audit_item(
                    persistence_package,
                    "candidate_table_update_forbidden_output_field_present",
                )
            )
            continue

        if persistence_package.get("qualification_record_status") != "formal_record_ready_for_persistence":
            held_items.append(
                _held_candidate_table_update_audit_item(
                    persistence_package,
                    "qualification_record_not_ready_for_persistence",
                )
            )
            continue

        if persistence_package.get("qualification_record_persistence_performed") is not False:
            held_items.append(
                _held_candidate_table_update_audit_item(
                    persistence_package,
                    "qualification_record_persistence_state_must_be_prepared_not_performed",
                )
            )
            continue

        audit_packages.append(_candidate_table_update_audit_package(persistence_package, generated_at_value))

    next_action = (
        "action:hold_for_explicit_candidate_table_update_writer"
        if audit_packages
        else "action:repair_candidate_table_update_audit_inputs"
    )

    return _strip_forbidden_fields(
        {
            "result": "pass" if audit_packages else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "source_package_id": persistence_package_report.get("package_id"),
            "candidate_table_update_audit_result": "pass" if audit_packages else "blocked",
            "candidate_table_update_package_prepared": bool(audit_packages),
            "candidate_table_update_performed": False,
            "candidate_table_update_audit_candidate_count": len(audit_packages),
            "held_candidate_table_update_audit_count": len(held_items),
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "candidate_table_update_audit_packages": audit_packages,
            "held_candidate_table_update_audit_items": held_items,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def write_qualification_records_to_staging_when_explicitly_requested(
    candidate_table_update_audit_report: dict[str, Any],
    staging_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    audit_packages = candidate_table_update_audit_report.get("candidate_table_update_audit_packages", [])
    issues: list[str] = []
    staging_records: list[dict[str, Any]] = []
    held_items: list[dict[str, Any]] = []

    if candidate_table_update_audit_report.get("candidate_table_update_audit_result") != "pass":
        issues.append("candidate_table_update_audit_not_pass")
    if candidate_table_update_audit_report.get("candidate_table_update_package_prepared") is not True:
        issues.append("candidate_table_update_package_not_prepared")
    if candidate_table_update_audit_report.get("candidate_table_update_performed") is not False:
        issues.append("candidate_table_update_must_not_be_performed_before_staging_persistence")
    if candidate_table_update_audit_report.get("candidate_table_update_allowed") is not False:
        issues.append("candidate_table_update_allowed_must_remain_false_for_staging_persistence")
    if not isinstance(audit_packages, list) or not audit_packages:
        issues.append("candidate_table_update_audit_packages_missing")
        audit_packages = []

    for audit_package in audit_packages:
        if not isinstance(audit_package, dict):
            issues.append("invalid_candidate_table_update_audit_package")
            continue

        forbidden_field = _first_forbidden_output_field_present(audit_package)
        if forbidden_field is not None:
            held_items.append(
                _held_qualification_record_staging_item(
                    audit_package,
                    "qualification_record_staging_forbidden_output_field_present",
                )
            )
            continue

        if audit_package.get("candidate_table_update_audit_result") != "pass":
            held_items.append(
                _held_qualification_record_staging_item(
                    audit_package,
                    "candidate_table_update_audit_package_not_pass",
                )
            )
            continue

        if audit_package.get("candidate_table_update_package_prepared") is not True:
            held_items.append(
                _held_qualification_record_staging_item(
                    audit_package,
                    "candidate_table_update_audit_package_not_prepared",
                )
            )
            continue

        if audit_package.get("candidate_table_update_performed") is not False:
            held_items.append(
                _held_qualification_record_staging_item(
                    audit_package,
                    "candidate_table_update_must_not_be_performed_before_staging_persistence",
                )
            )
            continue

        staging_records.append(_qualification_record_staging_record(audit_package, generated_at_value))

    if issues or held_items or not staging_records:
        return _qualification_record_staging_blocked_report(
            candidate_table_update_audit_report,
            generated_at_value,
            issues,
            held_items,
        )

    root = Path(staging_root)
    package_root = root / "qualification-records-v0.1"
    records_root = package_root / "records"
    records_root.mkdir(parents=True, exist_ok=True)

    record_files: list[str] = []
    for record in staging_records:
        file_name = f"{_safe_json_file_stem(str(record.get('qualification_record_id', 'UNKNOWN')))}.json"
        file_path = records_root / file_name
        _write_json_atomic(file_path, record)
        record_files.append(f"records/{file_name}")

    manifest = _qualification_record_staging_manifest(
        candidate_table_update_audit_report,
        generated_at_value,
        record_files,
    )
    _write_json_atomic(package_root / "manifest.json", manifest)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "qualification_record_staging_persistence_v0.1",
            "source_audit_id": candidate_table_update_audit_report.get("audit_id"),
            "manifest_file": str(package_root / "manifest.json"),
            "record_files": record_files,
            "qualification_record_staging_count": len(staging_records),
            "held_qualification_record_staging_count": 0,
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


def update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
    qualification_record_staging_manifest_path: str | Path,
    candidate_table_staging_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    manifest_path = Path(qualification_record_staging_manifest_path)
    issues: list[str] = []
    held_items: list[dict[str, Any]] = []

    manifest = _read_json_file(manifest_path)
    if manifest is None:
        issues.append("qualification_record_staging_manifest_unreadable")
        return _candidate_table_staging_blocked_report(generated_at_value, issues, held_items)

    _validate_qualification_record_staging_manifest(manifest, issues)
    record_files = manifest.get("record_files", [])
    if not isinstance(record_files, list) or not record_files:
        issues.append("qualification_record_staging_manifest_record_files_missing")
        record_files = []

    rows: list[dict[str, Any]] = []
    seen_record_ids: set[str] = set()
    manifest_root = manifest_path.parent
    for record_file in record_files:
        if not isinstance(record_file, str) or not record_file:
            issues.append("qualification_record_staging_record_file_invalid")
            continue

        record_path = manifest_root / record_file
        record = _read_json_file(record_path)
        if record is None:
            issues.append("qualification_record_staging_record_unreadable")
            continue

        forbidden_field = _first_forbidden_output_field_present(record)
        if forbidden_field is not None:
            held_items.append(
                _held_candidate_table_update_item(
                    record,
                    "candidate_table_forbidden_output_field_present",
                )
            )
            continue

        _validate_staged_qualification_record(record, issues)
        qualification_record_id = str(record.get("qualification_record_id") or "")
        if qualification_record_id in seen_record_ids:
            issues.append("candidate_table_duplicate_qualification_record_id")
            continue
        seen_record_ids.add(qualification_record_id)

        rows.append(_candidate_table_staging_row(record, manifest, record_file, generated_at_value))

    if issues or held_items or not rows:
        return _candidate_table_staging_blocked_report(generated_at_value, issues, held_items)

    candidate_root = Path(candidate_table_staging_root)
    table_root = candidate_root / "candidate-table-v0.1"
    existing_rows = _read_candidate_table_jsonl(table_root / "candidate-table-draft.jsonl")
    deduplicated_existing_row_count = 0
    if existing_rows is None:
        issues.append("candidate_table_existing_jsonl_unreadable")
    elif existing_rows:
        existing_index = {str(row.get("qualification_record_id") or ""): row for row in existing_rows}
        merged_rows = list(existing_rows)
        for row in rows:
            key = str(row.get("qualification_record_id") or "")
            existing_row = existing_index.get(key)
            if existing_row is None:
                merged_rows.append(row)
                continue
            if _candidate_table_row_merge_identity(existing_row) != _candidate_table_row_merge_identity(row):
                issues.append("candidate_table_merge_conflict")
                continue
            deduplicated_existing_row_count += 1
        rows = merged_rows

    if issues:
        return _candidate_table_staging_blocked_report(generated_at_value, issues, held_items)

    tmp_root = table_root.with_name(f"{table_root.name}.__tmp__")
    if tmp_root.exists():
        shutil.rmtree(tmp_root)

    try:
        tmp_root.mkdir(parents=True)
        _write_jsonl(tmp_root / "candidate-table-draft.jsonl", rows)
        manifest_payload = _candidate_table_staging_manifest(manifest, rows, generated_at_value)
        _write_json_atomic(tmp_root / "manifest.json", manifest_payload)
        if table_root.exists():
            shutil.rmtree(table_root)
        tmp_root.rename(table_root)
    except Exception:
        if tmp_root.exists():
            shutil.rmtree(tmp_root)
        raise

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "candidate_table_staging_update_v0.1",
            "source_qualification_record_manifest_id": manifest.get("manifest_id"),
            "candidate_table_manifest_file": str(table_root / "manifest.json"),
            "candidate_table_file": str(table_root / "candidate-table-draft.jsonl"),
            "candidate_table_row_count": len(rows),
            "held_candidate_table_update_count": 0,
            "candidate_table_deduplicated_existing_row_count": deduplicated_existing_row_count,
            "candidate_table_update_performed": True,
            "candidate_table_update_target": "staging",
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:review_staged_candidate_table_before_formal_data_root_write",
        }
    )


def write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
    candidate_table_staging_manifest_path: str | Path,
    formal_data_root: str | Path,
    confirm_formal_write: bool = False,
    generated_at: str | None = None,
    simulate_failure_step: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    if confirm_formal_write is not True:
        return _candidate_table_formal_blocked_report(generated_at_value, ["confirm_formal_write_required"])

    manifest_path = Path(candidate_table_staging_manifest_path)
    issues: list[str] = []
    manifest = _read_json_file(manifest_path)
    if manifest is None:
        issues.append("candidate_table_staging_manifest_unreadable")
        return _candidate_table_formal_blocked_report(generated_at_value, issues)

    _validate_candidate_table_staging_manifest(manifest, issues)
    draft_files = manifest.get("candidate_table_files", [])
    if not isinstance(draft_files, list) or "candidate-table-draft.jsonl" not in draft_files:
        issues.append("candidate_table_staging_manifest_draft_file_missing")
    draft_file = manifest_path.parent / "candidate-table-draft.jsonl"
    rows = _read_candidate_table_jsonl(draft_file)
    if rows is None:
        issues.append("candidate_table_staging_draft_unreadable")
        rows = []
    if not rows:
        issues.append("candidate_table_staging_draft_empty")

    formal_rows: list[dict[str, Any]] = []
    for row in rows:
        forbidden_field = _first_forbidden_output_field_present(row)
        if forbidden_field is not None:
            issues.append("candidate_table_formal_forbidden_output_field_present")
            continue
        formal_rows.append(_candidate_table_formal_row(row, manifest, generated_at_value))

    if issues:
        return _candidate_table_formal_blocked_report(generated_at_value, issues)

    data_root = Path(formal_data_root)
    ashare_root = data_root / "ashare"
    table_root = ashare_root / "candidate-table-v0.1"
    tmp_root = ashare_root / "candidate-table-v0.1.__tmp__"
    backup_path: Path | None = None

    try:
        backup_path = _backup_existing_candidate_table_dir(table_root, generated_at_value)
        if simulate_failure_step == "after_backup":
            raise RuntimeError("candidate_table_formal_write_failed_after_backup")

        if tmp_root.exists():
            shutil.rmtree(tmp_root)
        tmp_root.mkdir(parents=True)
        _write_jsonl(tmp_root / "candidate-table.jsonl", formal_rows)
        manifest_payload = _candidate_table_formal_manifest(
            manifest,
            formal_rows,
            generated_at_value,
            str(backup_path) if backup_path is not None else None,
        )
        _write_json_atomic(tmp_root / "manifest.json", manifest_payload)
        _replace_candidate_table_dir(tmp_root, table_root)
    except Exception as exc:
        if tmp_root.exists():
            shutil.rmtree(tmp_root)
        if backup_path is not None and backup_path.exists() and not table_root.exists():
            shutil.copytree(backup_path, table_root)
        issue = str(exc) or exc.__class__.__name__
        if issue not in {"candidate_table_formal_write_failed_after_backup"}:
            issue = f"candidate_table_formal_write_failed:{issue}"
        return _candidate_table_formal_blocked_report(
            generated_at_value,
            [issue],
            str(backup_path) if backup_path is not None else None,
        )

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "candidate_table_formal_write_v0.1",
            "source_staging_manifest_id": manifest.get("manifest_id"),
            "source_qualification_record_staging_manifest_id": manifest.get("source_qualification_record_manifest_id"),
            "formal_candidate_table_path": str(table_root / "candidate-table.jsonl"),
            "formal_candidate_table_manifest_path": str(table_root / "manifest.json"),
            "backup_path": str(backup_path) if backup_path is not None else None,
            "candidate_table_row_count": len(formal_rows),
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
