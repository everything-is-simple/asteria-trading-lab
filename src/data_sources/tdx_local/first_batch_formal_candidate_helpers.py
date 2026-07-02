from __future__ import annotations

from pathlib import Path
from typing import Any

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_candidate_helpers import *

def _validate_candidate_table_formal_manifest_for_trading_readiness(
    manifest: dict[str, Any],
    issues: list[str],
) -> None:
    if manifest.get("manifest_id") != "candidate_table_formal_manifest_v0.1":
        issues.append("candidate_table_formal_manifest_invalid")
    if manifest.get("candidate_table_update_performed") is not True:
        issues.append("candidate_table_formal_manifest_update_not_performed")
    if manifest.get("candidate_table_update_target") != "formal_data_root":
        issues.append("candidate_table_trading_readiness_not_formal_target")
    if manifest.get("candidate_table_update_allowed") is not False:
        issues.append("candidate_table_trading_readiness_downstream_gate_open")
    row_count = manifest.get("candidate_table_row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
        issues.append("candidate_table_formal_row_count_mismatch")
    if manifest.get("candidate_table_file") != "candidate-table.jsonl":
        issues.append("candidate_table_formal_jsonl_missing")
    if _first_forbidden_output_field_present(manifest) is not None:
        issues.append("candidate_table_trading_readiness_forbidden_output_field_present")
    for field in [
        "institution_rule_definition_allowed",
        "trading_layer_read_allowed",
        "signal_generation_allowed",
        "backtest_execution_allowed",
    ]:
        if manifest.get(field) is not False:
            issues.append("candidate_table_trading_readiness_downstream_gate_open")


def _candidate_table_jsonl_path_from_manifest(
    manifest_path: Path,
    manifest: dict[str, Any],
    issues: list[str],
) -> Path:
    table_file = manifest.get("candidate_table_file")
    if not isinstance(table_file, str) or not table_file:
        issues.append("candidate_table_formal_jsonl_missing")
        return manifest_path.parent / "candidate-table.jsonl"

    candidate_path = Path(table_file)
    if candidate_path.is_absolute() or len(candidate_path.parts) != 1 or table_file in {".", ".."}:
        issues.append("candidate_table_formal_jsonl_invalid")
        return manifest_path.parent / "candidate-table.jsonl"
    if ".." in candidate_path.parts:
        issues.append("candidate_table_formal_jsonl_invalid")
        return manifest_path.parent / "candidate-table.jsonl"
    return manifest_path.parent / candidate_path


def _validate_candidate_table_formal_rows_for_trading_readiness(
    rows: list[dict[str, Any]],
    expected_count: Any,
    issues: list[str],
) -> None:
    if not rows:
        issues.append("candidate_table_formal_jsonl_invalid")
        return
    if len(rows) != expected_count:
        issues.append("candidate_table_formal_row_count_mismatch")

    seen_row_ids: set[str] = set()
    required_fields = ["candidate_table_row_id", "qualification_record_id", "ts_code"]
    for row in rows:
        if _first_forbidden_output_field_present(row) is not None:
            issues.append("candidate_table_trading_readiness_forbidden_output_field_present")
            continue
        for field in required_fields:
            if not row.get(field):
                issues.append("candidate_table_formal_required_field_missing")
        row_id = row.get("candidate_table_row_id")
        if isinstance(row_id, str):
            if row_id in seen_row_ids:
                issues.append("candidate_table_formal_duplicate_row_id")
            seen_row_ids.add(row_id)
        if row.get("candidate_table_update_performed") is not True:
            issues.append("candidate_table_formal_required_field_missing")
        if row.get("candidate_table_update_target") != "formal_data_root":
            issues.append("candidate_table_trading_readiness_not_formal_target")
        if row.get("candidate_table_update_allowed") is not False:
            issues.append("candidate_table_trading_readiness_downstream_gate_open")
        for field in [
            "institution_rule_definition_allowed",
            "trading_layer_read_allowed",
            "signal_generation_allowed",
            "backtest_execution_allowed",
        ]:
            if row.get(field) is not False:
                issues.append("candidate_table_trading_readiness_downstream_gate_open")


def _backup_existing_candidate_table_dir(table_root: Path, generated_at: str) -> Path | None:
    if not table_root.exists():
        return None
    backup_suffix = generated_at.replace(":", "").replace("+", "").replace("-", "").replace("T", "-")
    backup_path = table_root.with_name(f"{table_root.name}.backup.{backup_suffix}")
    if backup_path.exists():
        shutil.rmtree(backup_path)
    shutil.copytree(table_root, backup_path)
    return backup_path


def _replace_candidate_table_dir(tmp_root: Path, table_root: Path) -> None:
    side_root = table_root.with_name(f"{table_root.name}.__old__")
    if side_root.exists():
        shutil.rmtree(side_root)
    table_root.parent.mkdir(parents=True, exist_ok=True)
    moved_live = False
    if table_root.exists():
        table_root.rename(side_root)
        moved_live = True
    try:
        tmp_root.rename(table_root)
    except Exception:
        if moved_live and side_root.exists() and not table_root.exists():
            side_root.rename(table_root)
        raise
    if side_root.exists():
        shutil.rmtree(side_root)


def _reviewed_snapshot_candidate(candidate: dict[str, Any], verdict: dict[str, Any], generated_at: str) -> dict[str, Any] | None:
    draft = candidate.get("suggested_snapshot_draft")
    if not isinstance(draft, dict):
        return None
    reviewed = dict(draft)
    reviewed.update(
        {
            "snapshot_quality_status": "reviewed_ready_candidate",
            "manual_reviewed_at": generated_at,
            "manual_review_verdict": verdict.get("manual_review_verdict"),
            "manual_review_note": verdict.get("reviewer_note"),
            "reviewed_candidate_boundary_warning": [
                "reviewed_candidate_is_not_formal_front_filter_ready",
                "formal_front_filter_review_package_required_before_ready",
                "do_not_generate_trade_from_reviewed_snapshot_candidate",
            ],
        }
    )
    return reviewed


def _intraday_review_boundary_warning(
    candidate: dict[str, Any],
    blocked: bool,
    intraday_optional_missing: bool = False,
) -> list[str]:
    warnings = list(candidate.get("research_boundary_warning", []))
    for item in [
        "intraday_review_is_not_formal_front_filter_ready",
        "do_not_upgrade_without_ready_malf_snapshot",
        "do_not_generate_trade_from_research_prep",
    ]:
        if item not in warnings:
            warnings.append(item)
    if intraday_optional_missing:
        for item in [
            "intraday_missing_is_optional_enhancement_only",
            "daily_level_malf_structure_review_remains_open",
        ]:
            if item not in warnings:
                warnings.append(item)
    if blocked and "intraday_review_source_blocked" not in warnings:
        warnings.append("intraday_review_source_blocked")
    return warnings


def _daily_level_malf_review_boundary_warning(candidate: dict[str, Any]) -> list[str]:
    warnings = list(candidate.get("research_boundary_warning", []))
    for item in [
        "daily_level_review_is_not_formal_front_filter_ready",
        "do_not_upgrade_without_ready_malf_snapshot",
        "do_not_generate_trade_from_daily_level_review",
    ]:
        if item not in warnings:
            warnings.append(item)
    return warnings


def _snapshot_draft_review_boundary_warning(candidate: dict[str, Any]) -> list[str]:
    warnings = list(candidate.get("research_boundary_warning", []))
    for item in [
        "snapshot_draft_review_is_not_formal_front_filter_ready",
        "manual_review_required_before_marking_snapshot_ready",
        "do_not_generate_trade_from_snapshot_draft_review",
    ]:
        if item not in warnings:
            warnings.append(item)
    return warnings


def _manual_snapshot_review_boundary_warning(candidate: dict[str, Any]) -> list[str]:
    warnings = list(candidate.get("research_boundary_warning", []))
    for item in [
        "reviewed_candidate_is_not_formal_front_filter_ready",
        "formal_front_filter_review_package_required_before_ready",
        "do_not_generate_trade_from_manual_snapshot_review",
    ]:
        if item not in warnings:
            warnings.append(item)
    return warnings


def _suggested_snapshot_file(snapshot_stub: dict[str, Any]) -> str:
    ts_code = str(snapshot_stub.get("ts_code", "UNKNOWN"))
    window_start = str(snapshot_stub.get("window_start", "UNKNOWN"))
    return f"ashare/malf-snapshots-v0.1/{ts_code}-{window_start[0:7]}.json"


__all__ = [name for name in globals() if not name.startswith("__")]
