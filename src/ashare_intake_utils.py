from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from ashare_intake_constants import *

def _constraint_types_from_fact(fact: dict[str, str]) -> list[str]:
    types = ["trading_calendar", "price_limit", "board_lot"]
    if fact.get("is_suspended") == "true":
        types.append("suspension")
    return types


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)

def _current_blocking_layer(pipeline_summary: dict[str, str]) -> str | None:
    for layer, result in pipeline_summary.items():
        if result != "pass":
            return layer
    return None


def _pipeline_next_action(
    current_blocking_layer: str | None,
    readiness: dict[str, Any],
    front_filter_run: dict[str, Any],
    record_drafts: dict[str, Any],
    sample_table_trial: dict[str, Any],
    method_pm_readiness: dict[str, Any],
    backtest_input_readiness: dict[str, Any],
) -> str:
    reports = {
        "readiness": readiness,
        "front_filter_run": front_filter_run,
        "record_drafts": record_drafts,
        "sample_table_trial": sample_table_trial,
        "method_pm_readiness": method_pm_readiness,
        "backtest_input_readiness": backtest_input_readiness,
    }
    if current_blocking_layer is None:
        return "action:institution_constraint_gate_review"
    return str(reports[current_blocking_layer].get("next_action", "action:keep_pending"))


def _pipeline_blocking_evidence(
    method_pm_readiness: dict[str, Any],
    backtest_input_readiness: dict[str, Any],
) -> dict[str, Any]:
    return {
        "method_pm_review_required_count": method_pm_readiness.get("method_pm_review_required_count", 0),
        "backtest_input_blocked_count": backtest_input_readiness.get("backtest_input_blocked_count", 0),
        "backtest_input_snapshot_allowed": backtest_input_readiness.get("backtest_input_snapshot_allowed", False),
        "method_pm_auto_generation_allowed": method_pm_readiness.get("method_pm_auto_generation_allowed", False),
        "malf_action_backflow_allowed": method_pm_readiness.get("malf_action_backflow_allowed", False),
    }


def _backtest_input_blocked_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": item.get("ashare_sample_id"),
        "ts_code": item.get("ts_code"),
        "symbol_name": item.get("symbol_name"),
        "candidate_stage": item.get("candidate_stage"),
        "qualification_rule_id": item.get("qualification_rule_id"),
        "blocker": "method_pm_not_ready",
        "method_pm_bridge_result": item.get("method_pm_bridge_result"),
        "next_action": item.get("next_action"),
        "boundary_warning": [
            "backtest_input_requires_independent_method_pm_plan",
            "do_not_build_backtest_input_from_structure_only",
            "do_not_start_institution_adaptation_before_backtest_input",
        ],
    }


def _backtest_input_ready_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": item.get("ashare_sample_id"),
        "ts_code": item.get("ts_code"),
        "symbol_name": item.get("symbol_name"),
        "candidate_stage": item.get("candidate_stage"),
        "qualification_rule_id": item.get("qualification_rule_id"),
        "next_action": "action:build_backtest_input_snapshot",
    }


def _method_pm_gate_record_from_trial_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **row,
        "candidate_stage_after": row.get("candidate_stage"),
        "pm_required": _pm_required_from_trial_row(row),
        "interface_layer": "tachibana_adapter",
    }


def _pm_required_from_trial_row(row: dict[str, Any]) -> bool:
    rhythm_meaning = row.get("rhythm_meaning")
    qualification_rule_id = row.get("qualification_rule_id")
    if rhythm_meaning == "limited":
        return True
    return qualification_rule_id not in {"Q-ALIVE-CLEAN", "Q-NO-TRADE"}


def _method_pm_review_item(row: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": row.get("ashare_sample_id"),
        "ts_code": row.get("ts_code"),
        "symbol_name": row.get("symbol_name"),
        "candidate_stage": row.get("candidate_stage"),
        "rhythm_meaning": row.get("rhythm_meaning"),
        "tachibana_applicability": row.get("tachibana_applicability"),
        "qualification_rule_id": row.get("qualification_rule_id"),
        "pm_required_from_structure": _pm_required_from_trial_row(row),
        "method_pm_bridge_result": gate.get("result"),
        "missing_method_pm_fields": _missing_method_pm_fields(gate),
        "blocked_reason_codes": gate.get("issues", []),
        "next_action": gate.get("next_action"),
        "boundary_warning": [
            "method_pm_must_be_independent_from_malf",
            "do_not_generate_method_action_from_malf",
            "do_not_generate_pm_action_from_malf",
        ],
    }


def _missing_method_pm_fields(gate: dict[str, Any]) -> list[str]:
    mapping = {
        "method_pm_invalid_method_action:None": "method_action",
        "method_pm_invalid_method_status:None": "method_status",
        "method_pm_requires_method_reason": "method_reason",
        "method_pm_requires_pm_required_boolean": "pm_required",
        "method_pm_requires_pm_action_when_pm_required": "pm_action",
        "method_pm_requires_execution_intent": "execution_intent",
        "method_pm_requires_execution_event_type": "execution_event_type",
    }
    missing: list[str] = []
    for issue in gate.get("issues", []):
        field = mapping.get(issue)
        if field and field not in missing:
            missing.append(field)
    return missing


def _sample_table_trial_row(draft: dict[str, Any]) -> dict[str, Any]:
    return {
        "ashare_sample_id": draft.get("ashare_sample_id"),
        "ts_code": draft.get("ts_code"),
        "symbol_name": draft.get("symbol_name"),
        "sample_window_start": draft.get("sample_window_start"),
        "sample_window_end": draft.get("sample_window_end"),
        "candidate_stage": draft.get("candidate_stage_after"),
        "malf_snapshot_ref": draft.get("malf_snapshot_ref"),
        "malf_background": draft.get("malf_background"),
        "rhythm_meaning": draft.get("rhythm_meaning"),
        "tachibana_applicability": draft.get("tachibana_applicability"),
        "qualification_rule_id": draft.get("qualification_rule_id"),
        "boundary_warning": draft.get("boundary_warning"),
        "evidence_level": draft.get("evidence_level"),
        "next_action": draft.get("next_action"),
        "candidate_table_gate_result": draft.get("candidate_table_gate", {}).get("result")
        if isinstance(draft.get("candidate_table_gate"), dict)
        else None,
        "record_consistency_result": draft.get("record_consistency", {}).get("result")
        if isinstance(draft.get("record_consistency"), dict)
        else None,
    }


def _front_filter_command(malf_snapshot_file: str | None) -> str | None:
    if not malf_snapshot_file:
        return None
    snapshot_path = malf_snapshot_file.replace("/", "\\")
    return f"$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot <data_root>\\{snapshot_path}"


def _record_draft_command(malf_snapshot_file: str | None, symbol_name: str, ashare_sample_id: str) -> str | None:
    front_filter_command = _front_filter_command(malf_snapshot_file)
    if front_filter_command is None:
        return None
    escaped_symbol = symbol_name.replace('"', '\\"')
    return (
        f"{front_filter_command} --record-draft "
        f"--ashare-sample-id {ashare_sample_id} --symbol-name \"{escaped_symbol}\""
    )


def _ashare_sample_id_suggestion(ts_code: str, window_start: str | None, window_end: str | None) -> str:
    if window_start and window_end:
        return f"ASHARE-{ts_code}-{window_start}-{window_end}"
    return f"ASHARE-{ts_code}-<window>"


def _candidate_symbol_index(data_root: Path) -> dict[str, str]:
    candidate_file = data_root / "ashare" / "candidate-universe-v0.1.csv"
    if not candidate_file.exists():
        return {}
    return {
        row.get("ts_code", ""): row.get("symbol_name", "")
        for row in _read_csv_rows(candidate_file)
        if row.get("ts_code", "")
    }


def _ready_snapshot_index(data_root: Path) -> dict[str, dict[str, str]]:
    snapshot_dir = data_root / "ashare" / "malf-snapshots-v0.1"
    index: dict[str, dict[str, str]] = {}
    if not snapshot_dir.exists():
        return index
    for snapshot_file in sorted(snapshot_dir.glob("*.json")):
        payload = _read_json_object(snapshot_file)
        if payload is None or payload.get("snapshot_quality_status") != "ready":
            continue
        ts_code = str(payload.get("ts_code", ""))
        if not ts_code or ts_code in index:
            continue
        try:
            relative_path = snapshot_file.relative_to(data_root).as_posix()
        except ValueError:
            relative_path = str(snapshot_file)
        index[ts_code] = {
            "malf_snapshot_ref": str(payload.get("malf_snapshot_ref", "")),
            "malf_snapshot_file": relative_path,
            "window_start": str(payload.get("window_start", "")),
            "window_end": str(payload.get("window_end", "")),
        }
    return index


def _require_file(path: Path, label: str, failed: list[str]) -> None:
    if not path.is_file():
        failed.append(f"missing_file:{label}")


def _require_dir(path: Path, label: str, failed: list[str]) -> None:
    if not path.is_dir():
        failed.append(f"missing_dir:{label}")


def _check_csv_file(path: Path, required_fields: list[str], failed: list[str]) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames or []
    except UnicodeDecodeError:
        failed.append(f"invalid_encoding:{path.name}")
        return

    _check_required_fields(path, header, required_fields, failed)
    _check_forbidden_fields(header, failed)


def _check_candidate_rows(path: Path, failed: list[str]) -> None:
    rows = _read_csv_rows(path)
    _check_duplicate_keys(path, rows, ["ts_code"], failed)
    for row in rows:
        _check_enum(path, "board_type", row.get("board_type", ""), BOARD_TYPES, failed)
        _check_date(path, "list_date", row.get("list_date", ""), failed)
        _check_boolean(path, "is_st", row.get("is_st", ""), failed)
        _check_boolean(path, "is_new_stock_window", row.get("is_new_stock_window", ""), failed)
        _check_enum(path, "data_quality_status", row.get("data_quality_status", ""), QUALITY_STATUSES, failed)
        if row.get("data_quality_status", "") == "ready":
            for field in ["board_type", "list_date", "is_st", "is_new_stock_window", "source_ref"]:
                if not row.get(field, ""):
                    failed.append(f"missing_ready_field:{path.name}:{field}:{row.get('ts_code', '')}")


def _check_sw_rows(path: Path, failed: list[str]) -> None:
    rows = _read_csv_rows(path)
    _check_duplicate_keys(path, rows, ["ts_code", "valid_from"], failed)
    for row in rows:
        valid_from = row.get("valid_from", "")
        valid_to = row.get("valid_to", "")
        _check_date(path, "valid_from", valid_from, failed)
        if valid_to:
            _check_date(path, "valid_to", valid_to, failed)
            if _is_date(valid_from) and _is_date(valid_to) and valid_to < valid_from:
                failed.append(f"invalid_date_order:{path.name}:{valid_from}>{valid_to}")


def _check_daily_rows(path: Path, failed: list[str]) -> None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    except UnicodeDecodeError:
        return

    if not rows:
        failed.append(f"empty_file:{path.name}")
        return

    _check_duplicate_keys(path, rows, ["ts_code", "trade_date"], failed)
    previous_date = ""
    for index, row in enumerate(rows, start=2):
        trade_date = row.get("trade_date", "")
        if not _is_date(trade_date):
            failed.append(f"invalid_date:{path.name}:trade_date:{trade_date}")
        if previous_date and trade_date <= previous_date:
            failed.append(f"daily_date_not_ascending:{path.name}:line_{index}")
        previous_date = trade_date

        try:
            open_price = float(row.get("open", ""))
            high_price = float(row.get("high", ""))
            low_price = float(row.get("low", ""))
            close_price = float(row.get("close", ""))
        except ValueError:
            failed.append(f"invalid_ohlc:{path.name}:line_{index}")
            continue

        if low_price > min(open_price, close_price) or high_price < max(open_price, close_price):
            failed.append(f"invalid_ohlc:{path.name}:line_{index}")

        for field in ["open", "high", "low", "close", "volume", "amount"]:
            _check_non_negative_number(path, field, row.get(field, ""), index, failed)
        for field in ["suspension_flag", "corporate_action_flag", "missing_bar_flag"]:
            _check_boolean(path, field, row.get(field, ""), failed, line=index)


def _check_snapshot_file(path: Path, failed: list[str]) -> None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        failed.append(f"invalid_json:{path.name}")
        return

    if not isinstance(payload, dict):
        failed.append(f"invalid_json_object:{path.name}")
        return

    _check_required_fields(path, list(payload.keys()), REQUIRED_SNAPSHOT_FIELDS, failed)
    _check_forbidden_fields(list(payload.keys()), failed)
    _check_date(path, "window_start", str(payload.get("window_start", "")), failed)
    _check_date(path, "window_end", str(payload.get("window_end", "")), failed)
    _check_enum(path, "snapshot_quality_status", str(payload.get("snapshot_quality_status", "")), QUALITY_STATUSES, failed)


def _check_cross_file_consistency(
    candidate_file: Path,
    sw_file: Path,
    daily_dir: Path,
    snapshot_dir: Path,
    failed: list[str],
) -> None:
    candidate_codes = _read_csv_codes(candidate_file)
    for ts_code in _read_csv_codes(sw_file):
        if ts_code and ts_code not in candidate_codes:
            failed.append(f"orphan_sw_ts_code:{ts_code}")

    daily_ranges: dict[str, tuple[str, str]] = {}
    for daily_file in sorted(daily_dir.glob("*.csv")):
        file_code = daily_file.stem
        rows = _read_csv_rows(daily_file)
        row_codes = {row.get("ts_code", "") for row in rows if row.get("ts_code", "")}
        if file_code not in candidate_codes:
            failed.append(f"orphan_daily_ts_code:{file_code}")
        for row_code in sorted(row_codes):
            if row_code != file_code:
                failed.append(f"daily_filename_ts_code_mismatch:{daily_file.name}:{row_code}")
        dates = sorted(row.get("trade_date", "") for row in rows if row.get("trade_date", ""))
        if dates:
            daily_ranges[file_code] = (dates[0], dates[-1])

    for snapshot_file in sorted(snapshot_dir.glob("*.json")):
        payload = _read_json_object(snapshot_file)
        if payload is None:
            continue
        ts_code = str(payload.get("ts_code", ""))
        if ts_code and ts_code not in candidate_codes:
            failed.append(f"orphan_snapshot_ts_code:{ts_code}")

        source_daily_file = str(payload.get("source_daily_file", ""))
        source_path = snapshot_file.parent.parent / source_daily_file
        if not source_path.is_file():
            failed.append(f"snapshot_source_daily_missing:{snapshot_file.name}:{source_daily_file}")

        range_code = source_path.stem if source_path.suffix == ".csv" else ts_code
        daily_range = daily_ranges.get(range_code)
        window_start = str(payload.get("window_start", ""))
        window_end = str(payload.get("window_end", ""))
        if daily_range is None or window_start < daily_range[0] or window_end > daily_range[1] or window_start > window_end:
            failed.append(f"snapshot_window_outside_daily_range:{snapshot_file.name}")


def _build_candidate_stage_summary(
    candidate_file: Path,
    sw_file: Path,
    daily_dir: Path,
    snapshot_dir: Path,
) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    candidate_codes = sorted(_read_csv_codes(candidate_file)) if candidate_file.exists() else []
    sw_codes = _read_csv_codes(sw_file) if sw_file.exists() else set()
    daily_codes = {path.stem for path in daily_dir.glob("*.csv")} if daily_dir.exists() else set()
    ready_snapshot_codes = _read_ready_snapshot_codes(snapshot_dir) if snapshot_dir.exists() else set()

    for ts_code in candidate_codes:
        failed_reason_codes: list[str] = []
        rule_match_reason: list[str] = []
        applicability_reason: list[str] = []
        boundary_warning: list[str] = []
        has_industry = ts_code in sw_codes
        has_daily = ts_code in daily_codes
        has_ready_snapshot = ts_code in ready_snapshot_codes

        if not has_industry:
            failed_reason_codes.append("missing_industry_label")
            rule_match_reason.append("blocked_by_missing_industry_label")
            applicability_reason.append("no_industry_label")
        if not has_daily:
            failed_reason_codes.append("missing_daily_window")
            rule_match_reason.append("blocked_by_missing_daily_window")
            applicability_reason.append("no_daily_window")
        if not has_ready_snapshot:
            failed_reason_codes.append("missing_malf_snapshot")
            rule_match_reason.append("blocked_by_missing_malf_snapshot")
            applicability_reason.append("no_ready_malf_snapshot")
            boundary_warning.append("do_not_upgrade_without_malf_snapshot")

        eligible_for_malf_run = has_industry and has_daily
        if has_ready_snapshot and eligible_for_malf_run:
            candidate_stage_after = "structure_candidate"
            next_action = "action:run_front_filter"
            applicability_reason.append("no_qualification_rule")
            boundary_warning.append("do_not_upgrade_ready_snapshot_without_front_filter")
        elif candidate_file.exists():
            candidate_stage_after = "universe_candidate"
            next_action = "action:complete_industry_and_daily_window"
        else:
            candidate_stage_after = "unknown"
            next_action = "action:repair_data"

        blocking_reasons = _unique_preserve_order([*failed_reason_codes, *rule_match_reason, *boundary_warning])

        summary[ts_code] = {
            "candidate_stage_after": candidate_stage_after,
            "eligible_for_malf_run": eligible_for_malf_run,
            "tachibana_applicability": "unknown",
            "failed_contract_reason_codes": failed_reason_codes,
            "rule_match_reason": rule_match_reason,
            "applicability_reason": applicability_reason,
            "boundary_warning": boundary_warning,
            "blocking_reasons": blocking_reasons,
            "next_action": next_action,
        }

    return summary


def _audit_stage_reason_consistency(
    stage_summary: dict[str, dict[str, Any]],
    failed_reason_codes: list[str],
) -> dict[str, Any]:
    issues: list[str] = []
    top_level_failed = set(failed_reason_codes)

    for ts_code, item in stage_summary.items():
        stage = item.get("candidate_stage_after", "unknown")
        eligible_for_malf = bool(item.get("eligible_for_malf_run", False))
        applicability = item.get("tachibana_applicability", "unknown")
        next_action = item.get("next_action", "")
        item_failed = set(item.get("failed_contract_reason_codes", []))
        boundary_warning = set(item.get("boundary_warning", []))

        if stage in {"structure_candidate", "tachibana_candidate"} and not eligible_for_malf:
            issues.append(f"stage_without_malf_run:{ts_code}:{stage}")
        if stage == "tachibana_candidate":
            issues.append(f"stage_skips_front_filter:{ts_code}")
        if applicability != "unknown":
            issues.append(f"tachibana_applicability_decided_before_front_filter:{ts_code}:{applicability}")
        if next_action and not str(next_action).startswith("action:"):
            issues.append(f"next_action_missing_action_prefix:{ts_code}:{next_action}")
        if "missing_malf_snapshot" in item_failed and "do_not_upgrade_without_malf_snapshot" not in boundary_warning:
            issues.append(f"missing_malf_snapshot_without_boundary_warning:{ts_code}")

        summary_scoped_codes = {"missing_industry_label", "missing_daily_window", "missing_malf_snapshot"}
        unexplained_codes = item_failed - top_level_failed - summary_scoped_codes
        for code in sorted(unexplained_codes):
            issues.append(f"stage_reason_not_in_top_level:{ts_code}:{code}")

    return {
        "result": "fail" if issues else "pass",
        "issues": issues,
    }


def _check_required_fields(path: Path, actual: list[str], required: list[str], failed: list[str]) -> None:
    actual_set = set(actual)
    for field in required:
        if field not in actual_set:
            failed.append(f"missing_field:{path.name}:{field}")


def _map_failed_items_to_reason_codes(failed_items: list[str]) -> list[str]:
    codes: list[str] = []
    for item in failed_items:
        if item == "missing_file:ashare/candidate-universe-v0.1.csv":
            codes.append("missing_candidate_universe")
        elif item == "missing_file:ashare/sw-industry-membership-v0.1.csv":
            codes.append("missing_sw_industry_membership")
        elif item in {"missing_dir:ashare/daily-window-v0.1", "empty_dir:ashare/daily-window-v0.1"}:
            codes.append("missing_daily_window")
        elif item in {"missing_dir:ashare/malf-snapshots-v0.1", "empty_dir:ashare/malf-snapshots-v0.1"}:
            codes.append("missing_malf_snapshot")
        elif item.startswith("missing_field:"):
            codes.extend(_missing_field_reason_codes(item))
        elif item.startswith("missing_ready_field:"):
            codes.extend(_missing_ready_field_reason_codes(item))
        elif item.startswith("missing_key:"):
            codes.append("missing_ts_code")
        elif item.startswith("duplicate_key:"):
            codes.append("duplicate_key_present")
        elif item.startswith("invalid_enum:"):
            codes.append("invalid_enum_value")
            if item.endswith(":snapshot_quality_status:bad_status") or ":snapshot_quality_status:" in item:
                codes.append("malf_snapshot_not_ready")
        elif item.startswith("invalid_date:") or item.startswith("invalid_date_order:") or item.startswith("daily_date_not_ascending:"):
            codes.append("invalid_date_value")
        elif item.startswith("invalid_boolean:"):
            codes.append("invalid_boolean_value")
        elif item.startswith("invalid_number:") or item.startswith("negative_number:"):
            codes.append("invalid_numeric_value")
        elif item.startswith("invalid_ohlc:"):
            codes.append("invalid_daily_ohlc")
        elif item.startswith("forbidden_field:"):
            codes.append("forbidden_field_present")
        elif item.startswith("orphan_sw_ts_code:"):
            codes.append("missing_industry_label")
        elif item.startswith("orphan_daily_ts_code:") or item.startswith("daily_filename_ts_code_mismatch:"):
            codes.append("missing_daily_window")
        elif item.startswith("orphan_snapshot_ts_code:") or item.startswith("snapshot_source_daily_missing:"):
            codes.append("missing_malf_snapshot")
        elif item.startswith("snapshot_window_outside_daily_range:"):
            codes.append("malf_snapshot_window_mismatch")
        elif item.startswith("invalid_json:") or item.startswith("invalid_json_object:"):
            codes.append("malf_snapshot_not_ready")
        elif item.startswith("invalid_encoding:"):
            codes.append("source_disrupted")
    return _unique_preserve_order(codes)


def _missing_field_reason_codes(item: str) -> list[str]:
    parts = item.split(":")
    if len(parts) < 3:
        return []
    filename = parts[1]
    field = parts[2]
    if filename == "candidate-universe-v0.1.csv":
        return _candidate_missing_field_reason(field)
    if filename == "sw-industry-membership-v0.1.csv":
        return ["missing_industry_label"]
    if filename.endswith(".csv"):
        return ["missing_daily_window"]
    if filename.endswith(".json"):
        return ["missing_malf_snapshot"]
    return []


def _missing_ready_field_reason_codes(item: str) -> list[str]:
    parts = item.split(":")
    if len(parts) < 3:
        return []
    return _candidate_missing_field_reason(parts[2])


def _candidate_missing_field_reason(field: str) -> list[str]:
    mapping = {
        "ts_code": ["missing_ts_code"],
        "symbol_name": ["missing_symbol_name"],
        "board_type": ["missing_board_type"],
        "list_date": ["missing_list_date"],
        "is_st": ["missing_st_flag"],
        "is_new_stock_window": ["missing_new_stock_window"],
        "source_ref": ["missing_source_ref"],
    }
    return mapping.get(field, [])


def _check_forbidden_fields(fields: list[str], failed: list[str]) -> None:
    for field in fields:
        if field in FORBIDDEN_FIELDS:
            item = f"forbidden_field:{field}"
            if item not in failed:
                failed.append(item)


def _check_institution_fact_file(path: Path, data_root: Path, failed: list[str]) -> None:
    _check_csv_file(path, REQUIRED_INSTITUTION_FACT_FIELDS, failed)
    rows = _read_csv_rows(path)
    _check_duplicate_keys(path, rows, ["ts_code", "trade_date"], failed)
    _check_forbidden_institution_fact_fields(path, rows, failed)
    expected_code = path.stem
    for line_number, row in enumerate(rows, start=2):
        ts_code = row.get("ts_code", "")
        if ts_code != expected_code:
            failed.append(f"institution_fact_filename_ts_code_mismatch:{path.name}:line_{line_number}")
        _check_date(path, "trade_date", row.get("trade_date", ""), failed)
        _check_boolean(path, "is_trading_day", row.get("is_trading_day", ""), failed, line=line_number)
        _check_boolean(path, "is_suspended", row.get("is_suspended", ""), failed, line=line_number)
        _check_optional_non_negative_number(path, "limit_up_price", row.get("limit_up_price", ""), line_number, failed)
        _check_optional_non_negative_number(path, "limit_down_price", row.get("limit_down_price", ""), line_number, failed)
        _check_non_negative_number(path, "board_lot_size", row.get("board_lot_size", ""), line_number, failed)
        _check_enum(path, "close_limit_status", row.get("close_limit_status", ""), LIMIT_CLOSE_STATUSES, failed)
        _check_enum(path, "touched_limit_status", row.get("touched_limit_status", ""), TOUCHED_LIMIT_STATUSES, failed)
        if not row.get("source_ref"):
            failed.append(f"missing_ready_field:{path.name}:source_ref:line_{line_number}")


def _check_forbidden_institution_fact_fields(path: Path, rows: list[dict[str, str]], failed: list[str]) -> None:
    fields: set[str] = set()
    for row in rows:
        fields.update(row.keys())
    for field in sorted(fields.intersection(FORBIDDEN_FIELDS.union(INSTITUTION_GATE_FORBIDDEN_FIELDS))):
        failed.append(f"forbidden_field:{path.name}:{field}")


def _check_duplicate_keys(path: Path, rows: list[dict[str, str]], fields: list[str], failed: list[str]) -> None:
    seen: set[tuple[str, ...]] = set()
    key_label = "+".join(fields)
    for row in rows:
        key = tuple(row.get(field, "") for field in fields)
        if any(not value for value in key):
            failed.append(f"missing_key:{path.name}:{key_label}")
            continue
        if key in seen:
            failed.append(f"duplicate_key:{path.name}:{key_label}:{'+'.join(key)}")
        seen.add(key)


def _check_enum(path: Path, field: str, value: str, allowed: set[str], failed: list[str]) -> None:
    if value not in allowed:
        failed.append(f"invalid_enum:{path.name}:{field}:{value}")


def _check_boolean(path: Path, field: str, value: str, failed: list[str], line: int | None = None) -> None:
    if value not in BOOLEAN_VALUES:
        suffix = f":line_{line}" if line is not None else f":{value}"
        failed.append(f"invalid_boolean:{path.name}:{field}{suffix}")


def _check_date(path: Path, field: str, value: str, failed: list[str]) -> None:
    if not _is_date(value):
        failed.append(f"invalid_date:{path.name}:{field}:{value}")


def _check_non_negative_number(path: Path, field: str, value: str, line: int, failed: list[str]) -> None:
    try:
        number = float(value)
    except ValueError:
        failed.append(f"invalid_number:{path.name}:{field}:line_{line}")
        return
    if number < 0:
        failed.append(f"negative_number:{path.name}:{field}:line_{line}")


def _check_optional_non_negative_number(path: Path, field: str, value: str, line: int, failed: list[str]) -> None:
    if value == "":
        return
    _check_non_negative_number(path, field, value, line, failed)


def _is_date(value: str) -> bool:
    return bool(DATE_PATTERN.match(value))


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))
    except UnicodeDecodeError:
        return []


def _unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _read_csv_codes(path: Path) -> set[str]:
    return {row.get("ts_code", "") for row in _read_csv_rows(path) if row.get("ts_code", "")}


def _read_json_object(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _price_limit_relation_evidence_index(
    relation_evidence_dir: str | Path | None,
) -> tuple[dict[tuple[str, str, str, str], dict[str, Any]], list[dict[str, Any]]]:
    if relation_evidence_dir is None:
        return {}, []
    evidence_dir = Path(relation_evidence_dir)
    if not evidence_dir.exists():
        return {}, [
            {
                "issues": ["price_limit_event_relation_evidence_dir_missing"],
                "next_action": "action:review_price_limit_event_relation_evidence",
                "path": str(evidence_dir),
            }
        ]

    index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    blocked_items: list[dict[str, Any]] = []
    for path in sorted(evidence_dir.glob("*.json")):
        payload = _read_json_object(path)
        if payload is None:
            blocked_items.append(
                {
                    "issues": [f"invalid_price_limit_event_relation_evidence_json:{path.name}"],
                    "next_action": "action:review_price_limit_event_relation_evidence",
                    "path": str(path),
                }
            )
            continue
        issues = _price_limit_relation_evidence_issues(path, payload)
        if issues:
            blocked_items.append(
                {
                    "ashare_sample_id": payload.get("ashare_sample_id"),
                    "ts_code": payload.get("ts_code"),
                    "issues": issues,
                    "next_action": "action:review_price_limit_event_relation_evidence",
                    "path": str(path),
                }
            )
            continue
        key = (
            str(payload["ashare_sample_id"]),
            str(payload["ts_code"]),
            str(payload["trade_date"]),
            str(payload["planned_event"]),
        )
        index[key] = payload
    return index, blocked_items


def _price_limit_relation_evidence_issues(path: Path, payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    required_fields = [
        "record_type",
        "schema_version",
        "ashare_sample_id",
        "ts_code",
        "trade_date",
        "planned_event",
        "price_limit_event_relation_status",
        "price_limit_event_fill_blocking_status",
        "price_limit_event_limit_proximity",
        "price_limit_event_relation_reason",
        "price_limit_event_relation_ref",
    ]
    for field in required_fields:
        if field not in payload:
            issues.append(f"price_limit_event_relation_evidence_missing_field:{field}")
    if issues:
        return issues
    if payload.get("record_type") != "ASharePriceLimitEventRelationEvidence":
        issues.append(f"invalid_price_limit_event_relation_evidence_record_type:{path.name}")
    relation_status = str(payload.get("price_limit_event_relation_status"))
    if relation_status not in PRICE_LIMIT_EVENT_RELATION_STATUSES:
        issues.append("invalid_price_limit_event_relation_evidence_enum:price_limit_event_relation_status")
    fill_status = str(payload.get("price_limit_event_fill_blocking_status"))
    if fill_status not in PRICE_LIMIT_EVENT_FILL_BLOCKING_STATUSES:
        issues.append("invalid_price_limit_event_relation_evidence_enum:price_limit_event_fill_blocking_status")
    proximity = str(payload.get("price_limit_event_limit_proximity"))
    if proximity not in PRICE_LIMIT_EVENT_LIMIT_PROXIMITY_STATUSES:
        issues.append("invalid_price_limit_event_relation_evidence_enum:price_limit_event_limit_proximity")
    if not isinstance(payload.get("price_limit_event_relation_reason"), list):
        issues.append("invalid_price_limit_event_relation_evidence_list:price_limit_event_relation_reason")
    if not isinstance(payload.get("price_limit_event_relation_ref"), list):
        issues.append("invalid_price_limit_event_relation_evidence_list:price_limit_event_relation_ref")
    return issues


def _read_ready_snapshot_codes(snapshot_dir: Path) -> set[str]:
    codes: set[str] = set()
    for snapshot_file in snapshot_dir.glob("*.json"):
        payload = _read_json_object(snapshot_file)
        if payload is None:
            continue
        if payload.get("snapshot_quality_status") == "ready":
            codes.add(str(payload.get("ts_code", "")))
    return {code for code in codes if code}


def _package_status(candidate_file: Path, sw_file: Path, daily_dir: Path, snapshot_dir: Path, failed: list[str]) -> str:
    required_paths = [candidate_file, sw_file, daily_dir, snapshot_dir]
    present_count = sum(1 for path in required_paths if path.exists())
    if present_count == 0:
        return "missing"
    if failed:
        return "partial"
    return "ready"


__all__ = [name for name in globals() if not name.startswith("__")]
