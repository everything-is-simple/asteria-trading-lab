from __future__ import annotations

import csv
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import shutil
import tempfile
from typing import Any

import duckdb

from ashare_intake_validator import (
    audit_first_batch_front_filter_run,
    audit_first_batch_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
)
from .readers import (
    _normalize_duckdb_symbol,
    _resolve_duckdb_table_ref,
    read_daily_bars,
    read_intraday_range,
    read_symbol_master,
)
from .price_limit_sample_pool import screen_pullback_add_price_limit_candidates
from .first_batch_constants import *

def _industry_membership_index(duckdb_root: Path) -> dict[str, list[dict[str, str | None]]]:
    db_path = duckdb_root / "market_meta.duckdb"
    if not db_path.exists():
        return {}
    con = duckdb.connect(str(db_path), read_only=True)
    table_ref = _resolve_duckdb_table_ref(con, "industry_block_relation")
    if table_ref is None:
        con.close()
        return {}
    rows = con.execute(
        f"""
        select symbol, relation_type, relation_code, relation_name, effective_from, effective_to
        from {table_ref}
        where coalesce(asset_type, 'stock') in ('equity', 'stock')
          and relation_type = 'industry'
        order by symbol, effective_from
        """
    ).fetchall()
    con.close()

    index: dict[str, list[dict[str, str | None]]] = {}
    for symbol, relation_type, relation_code, relation_name, effective_from, effective_to in rows:
        ts_code = _normalize_duckdb_symbol(symbol, None)[0]
        index.setdefault(ts_code, []).append(
            {
                "relation_type": str(relation_type),
                "relation_code": str(relation_code),
                "relation_name": str(relation_name),
                "valid_from": str(effective_from) if effective_from is not None else None,
                "valid_to": str(effective_to) if effective_to is not None else None,
                "source_ref": "market_meta.duckdb:market_meta.industry_block_relation",
            }
        )
    return index


def _window_rows(daily_rows: list[dict[str, Any]], entry: dict[str, Any]) -> list[dict[str, Any]]:
    start = str(entry.get("sample_window_start", ""))
    end = str(entry.get("sample_window_end", ""))
    return [row for row in daily_rows if start <= str(row.get("trade_date", "")) <= end]


def _select_industry_row(
    rows: list[dict[str, str | None]],
    window_start: str,
    window_end: str,
) -> dict[str, str | None] | None:
    window_start_dt = _parse_iso_date(window_start)
    window_end_dt = _parse_iso_date(window_end)
    if window_start_dt is None or window_end_dt is None:
        return None
    overlapping: list[tuple[datetime, dict[str, str | None]]] = []
    for row in rows:
        valid_from_dt = _parse_iso_date(str(row.get("valid_from") or ""))
        valid_to_dt = _parse_iso_date(str(row.get("valid_to") or "")) or datetime.max
        if valid_from_dt is None:
            valid_from_dt = datetime.min
        if valid_from_dt <= window_end_dt and window_start_dt <= valid_to_dt:
            overlapping.append((valid_from_dt, row))
    if not overlapping:
        return None
    overlapping.sort(key=lambda item: item[0])
    return overlapping[-1][1]


def _candidate_row(symbol_row: dict[str, Any], entry: dict[str, Any]) -> dict[str, str]:
    symbol_name = str(symbol_row.get("symbol_name", ""))
    list_date = str(symbol_row.get("list_date", ""))
    sample_window_start = str(entry.get("sample_window_start", ""))
    return {
        "ts_code": str(symbol_row.get("ts_code", "")),
        "symbol_name": symbol_name,
        "board_type": _board_type(str(symbol_row.get("ts_code", ""))),
        "list_date": list_date,
        "is_st": "true" if _is_st_name(symbol_name) else "false",
        "is_new_stock_window": "true" if _is_new_stock_window(list_date, sample_window_start) else "false",
        "data_quality_status": "ready",
        "source_ref": str(symbol_row.get("source_ref", "market_meta.duckdb:market_meta.instrument_master")),
    }


def _sw_row(ts_code: str, row: dict[str, str | None]) -> dict[str, str]:
    return {
        "ts_code": ts_code,
        "sw_l1_name": str(row.get("relation_name", "")),
        "sw_l2_name": "",
        "valid_from": str(row.get("valid_from", "")),
        "valid_to": str(row.get("valid_to", "") or ""),
        "source_ref": str(row.get("source_ref", "market_meta.duckdb:market_meta.industry_block_relation")),
    }


def _daily_row(ts_code: str, row: dict[str, Any]) -> dict[str, str]:
    return {
        "ts_code": ts_code,
        "trade_date": str(row.get("trade_date", "")),
        "open": str(row.get("open", "")),
        "high": str(row.get("high", "")),
        "low": str(row.get("low", "")),
        "close": str(row.get("close", "")),
        "volume": str(row.get("volume", "")),
        "amount": str(row.get("amount", "")),
        "adj_ref": "tdx_local_file_first_raw",
        "suspension_flag": "false",
        "corporate_action_flag": "false",
        "missing_bar_flag": "false",
    }


def _snapshot_payload(
    ts_code: str,
    daily_rows: list[dict[str, Any]],
    entry: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    preset_name = str(entry.get("snapshot_preset", entry.get("expected_structure_target", "unknown")))
    preset = SNAPSHOT_PRESETS[preset_name]
    window_start = str(entry.get("sample_window_start", daily_rows[0]["trade_date"]))
    window_end = str(entry.get("sample_window_end", daily_rows[-1]["trade_date"]))
    return {
        "malf_snapshot_ref": f"MALF-SNAP-{ts_code}-{window_start}-{window_end}-RMAP-v0.1",
        "ts_code": ts_code,
        "window_start": window_start,
        "window_end": window_end,
        "source_daily_file": f"daily-window-v0.1/{ts_code}.csv",
        "generated_at": generated_at,
        "malf_version": "MALF_Definitive_v2_0+research_mapping_v0.1",
        "malf_background": preset["malf_background"],
        "wave_range_break_fields": deepcopy(preset["wave_range_break_fields"]),
        "evidence_ref": str(entry.get("evidence_ref", "")),
        "snapshot_quality_status": "ready",
    }


def _write_csv(path: Path, header: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _board_type(ts_code: str) -> str:
    code, suffix = ts_code.split(".", 1)
    suffix = suffix.upper()
    if suffix == "BJ":
        return "bse"
    if suffix == "SH" and code.startswith("688"):
        return "star"
    if suffix == "SZ" and code.startswith(("300", "301")):
        return "gem"
    return "main"


def _is_st_name(symbol_name: str) -> bool:
    uppercase_name = symbol_name.upper()
    return "ST" in uppercase_name or "*ST" in uppercase_name


def _is_new_stock_window(list_date: str, sample_window_start: str) -> bool:
    if not list_date or not sample_window_start:
        return False
    try:
        list_dt = datetime.fromisoformat(list_date)
        sample_dt = datetime.fromisoformat(sample_window_start)
    except ValueError:
        return False
    return (sample_dt - list_dt).days <= 365


def _parse_iso_date(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _load_manifest_entries(data_root: Path) -> list[dict[str, Any]]:
    manifest_path = data_root / "ashare" / "first-batch-sample-manifest-v0.1.json"
    if manifest_path.exists():
        return json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    return deepcopy(DEFAULT_FIRST_BATCH_SAMPLE_ENTRIES)


def _select_current_industry_row(rows: list[dict[str, str | None]]) -> dict[str, str | None] | None:
    if not rows:
        return None
    ranked: list[tuple[datetime, dict[str, str | None]]] = []
    for row in rows:
        valid_from_dt = _parse_iso_date(str(row.get("valid_from") or "")) or datetime.min
        ranked.append((valid_from_dt, row))
    ranked.sort(key=lambda item: item[0])
    return ranked[-1][1]


def _research_priority_group(entry: dict[str, Any]) -> str:
    priority_group = str(entry.get("research_priority_group", "")).strip().lower()
    if priority_group in {"core", "backup"}:
        return priority_group
    core_focus = str(entry.get("core_snapshot_focus", ""))
    if core_focus == "near_limit_compare_backup":
        return "backup"
    return "core"


def _event_day_summary(event_row: dict[str, Any] | None) -> dict[str, Any] | None:
    if event_row is None:
        return None
    return {
        "trade_date": str(event_row.get("trade_date", "")),
        "open": event_row.get("open"),
        "high": event_row.get("high"),
        "low": event_row.get("low"),
        "close": event_row.get("close"),
        "volume": event_row.get("volume"),
        "amount": event_row.get("amount"),
    }


def _research_snapshot_stub(
    ts_code: str,
    daily_rows: list[dict[str, Any]],
    entry: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    window_start = str(entry.get("sample_window_start", daily_rows[0]["trade_date"]))
    window_end = str(entry.get("sample_window_end", daily_rows[-1]["trade_date"]))
    return {
        "malf_snapshot_ref": f"MALF-SNAP-{ts_code}-{window_start}-{window_end}-RESEARCH-PREP-v0.1",
        "ts_code": ts_code,
        "window_start": window_start,
        "window_end": window_end,
        "generated_at": generated_at,
        "malf_version": "MALF_Definitive_v2_0+research_mapping_v0.1",
        "malf_background": "unknown",
        "wave_range_break_fields": {},
        "evidence_ref": str(entry.get("evidence_ref", "")),
        "snapshot_quality_status": "source_missing",
    }


def _apply_manual_malf_fill_contract(snapshot_stub: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    core_focus = str(entry.get("core_snapshot_focus", ""))
    if core_focus != "pressure_adjust_reopen_core":
        return snapshot_stub
    snapshot_stub.update(
        {
            "intended_front_filter_rule_id": "Q-PRESSURE-ADJUST",
            "intended_malf_background": "pullback",
            "manual_malf_fill_required_fields": [
                "snapshot_quality_status=ready",
                "malf_background=pullback",
                "wave_range_break_fields.pressure_adjustment=true",
            ],
            "research_boundary_warning": [
                "stub_is_not_formal_front_filter_ready",
                "manual_malf_fill_required_before_front_filter",
                "do_not_mark_ready_until_structure_evidence_is_reviewed",
                "do_not_generate_trade_from_research_prep",
            ],
        }
    )
    return snapshot_stub


def _research_snapshot_draft(snapshot_stub: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    snapshot_draft = dict(snapshot_stub)
    core_focus = str(entry.get("core_snapshot_focus", ""))
    if core_focus == "pressure_adjust_reopen_core":
        snapshot_draft.update(
            {
                "snapshot_quality_status": "incomplete",
                "research_prep_status": "draft_pending_manual_evidence_review",
                "malf_background": "pullback",
                "wave_range_break_fields": {"pressure_adjustment": True},
                "draft_front_filter_expected_rule_id": "Q-PRESSURE-ADJUST",
                "draft_boundary_warning": [
                    "draft_is_not_formal_front_filter_ready",
                    "snapshot_quality_status_must_remain_incomplete_until_reviewed",
                    "do_not_generate_trade_from_research_draft",
                ],
            }
        )
    return snapshot_draft

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


def _research_boundary_warning(research_priority_group: str, formal_front_filter_status: str) -> list[str]:
    warnings = [
        "research_prep_is_not_formal_front_filter_ready",
        "do_not_generate_trade_from_research_prep",
    ]
    if research_priority_group == "backup":
        warnings.append("near_limit_compare_reserved_as_backup")
    if formal_front_filter_status == "blocked":
        warnings.append("do_not_borrow_future_industry_label")
    if formal_front_filter_status == "snapshot_pending":
        warnings.append("do_not_upgrade_without_ready_malf_snapshot")
    return warnings


def _research_next_action(formal_front_filter_status: str) -> str:
    if formal_front_filter_status == "blocked":
        return "action:hold_for_industry_time_alignment"
    if formal_front_filter_status == "snapshot_pending":
        return "action:prepare_malf_snapshot"
    return "action:run_front_filter"


def _last_trade_date(rows: list[dict[str, Any]]) -> str | None:
    if not rows:
        return None
    return str(rows[-1].get("trade_date", ""))


def _limit_pct_for_ts_code(ts_code: str) -> float:
    code, suffix = ts_code.split(".", 1)
    suffix = suffix.upper()
    if suffix == "SZ" and code.startswith(("300", "301")):
        return 0.20
    if suffix == "SH" and code.startswith("688"):
        return 0.20
    return 0.10


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f"{path.name}.tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows)
    path.write_text(payload, encoding="utf-8")


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _read_candidate_table_jsonl(path: Path) -> list[dict[str, Any]] | None:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                return None
            rows.append(row)
    except (OSError, json.JSONDecodeError):
        return None
    return rows


def _safe_json_file_stem(value: str) -> str:
    safe_chars = []
    for char in value:
        if char.isalnum() or char in {".", "-", "_"}:
            safe_chars.append(char)
        else:
            safe_chars.append("_")
    safe_value = "".join(safe_chars).strip("._")
    return safe_value or "UNKNOWN"


def _strip_forbidden_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_forbidden_fields(item)
            for key, item in value.items()
            if key not in FORBIDDEN_OUTPUT_FIELDS
        }
    if isinstance(value, list):
        return [_strip_forbidden_fields(item) for item in value]
    return value


def _first_forbidden_output_field_present(value: dict[str, Any]) -> str | None:
    for field in sorted(FORBIDDEN_OUTPUT_FIELDS):
        if field in value:
            return field
    return None


__all__ = [name for name in globals() if not name.startswith("__")]
