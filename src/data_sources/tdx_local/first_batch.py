from __future__ import annotations

import csv
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
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
    read_symbol_master,
)


CANDIDATE_HEADER = [
    "ts_code",
    "symbol_name",
    "board_type",
    "list_date",
    "is_st",
    "is_new_stock_window",
    "data_quality_status",
    "source_ref",
]

SW_HEADER = [
    "ts_code",
    "sw_l1_name",
    "sw_l2_name",
    "valid_from",
    "valid_to",
    "source_ref",
]

DAILY_HEADER = [
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adj_ref",
    "suspension_flag",
    "corporate_action_flag",
    "missing_bar_flag",
]

DEFAULT_FIRST_BATCH_SAMPLE_ENTRIES = [
    {
        "ts_code": "000001.SZ",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "meaningful",
        "selection_reason": "Bank sample with a relatively clean upward push for first-batch meaningful coverage.",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#000001sz",
    },
    {
        "ts_code": "300750.SZ",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "limited",
        "selection_reason": "High-volatility pullback sample for PM-dependent limited coverage.",
        "snapshot_preset": "pullback_pressure",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#300750sz",
    },
    {
        "ts_code": "600000.SH",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "limited",
        "selection_reason": "Range-wait banking sample to preserve a second limited case.",
        "snapshot_preset": "range_wait",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#600000sh",
    },
    {
        "ts_code": "601127.SH",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "unknown",
        "selection_reason": "Structure still left in research-pending state, used to keep unknown coverage honest.",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#601127sh",
    },
    {
        "ts_code": "002714.SZ",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "expected_structure_target": "not_meaningful",
        "selection_reason": "Noise-dominated sample used for explicit not-meaningful coverage.",
        "evidence_ref": "docs/a-share/first-batch-real-samples.md#002714sz",
    },
]

SNAPSHOT_PRESETS = {
    "meaningful": {
        "malf_background": "alive_wave",
        "wave_range_break_fields": {
            "wave_core_state": "alive",
            "progress_state": "research_selected_clean_window",
        },
    },
    "limited": {
        "malf_background": "pullback",
        "wave_range_break_fields": {
            "pressure_adjustment": True,
        },
    },
    "unknown": {
        "malf_background": "unknown",
        "wave_range_break_fields": {},
    },
    "not_meaningful": {
        "malf_background": "no_structure",
        "wave_range_break_fields": {
            "negative_type": "NM-NO-STRUCTURE",
        },
    },
    "pullback_pressure": {
        "malf_background": "pullback",
        "wave_range_break_fields": {
            "pressure_adjustment": True,
        },
    },
    "range_wait": {
        "malf_background": "range",
        "wave_range_break_fields": {
            "range_state": "alive",
            "no_trade_wait": True,
        },
    },
}


def build_first_batch_sample_package(
    data_root: str | Path,
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
    sample_entries: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = Path(data_root)
    ashare_root = root / "ashare"
    sample_manifest = deepcopy(sample_entries or DEFAULT_FIRST_BATCH_SAMPLE_ENTRIES)
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")

    symbol_rows = read_symbol_master(tdx_root, offline_root, duckdb_root=duckdb_root)
    symbol_index = {row["ts_code"]: row for row in symbol_rows if isinstance(row, dict) and row.get("ts_code")}
    industry_index = _industry_membership_index(Path(duckdb_root))

    candidate_rows: list[dict[str, str]] = []
    sw_rows: list[dict[str, str]] = []
    daily_windows: dict[str, list[dict[str, str]]] = {}
    snapshot_payloads: dict[str, dict[str, Any]] = {}
    issues: list[str] = []

    for entry in sample_manifest:
        ts_code = str(entry.get("ts_code", ""))
        if not ts_code:
            issues.append("missing_ts_code_in_sample_manifest")
            continue
        symbol_row = symbol_index.get(ts_code)
        if symbol_row is None:
            issues.append(f"missing_symbol_master:{ts_code}")
            continue
        daily_rows = _window_rows(read_daily_bars(offline_root, ts_code), entry)
        if not daily_rows:
            issues.append(f"missing_daily_window:{ts_code}")
            continue
        industry_row = _select_industry_row(
            industry_index.get(ts_code, []),
            str(entry.get("sample_window_start", "")),
            str(entry.get("sample_window_end", "")),
        )
        if industry_row is None:
            issues.append(f"industry_membership_window_not_overlapping:{ts_code}")
            continue

        candidate_rows.append(_candidate_row(symbol_row, entry))
        sw_rows.append(_sw_row(ts_code, industry_row))
        daily_windows[ts_code] = [_daily_row(ts_code, row) for row in daily_rows]
        snapshot_payloads[ts_code] = _snapshot_payload(ts_code, daily_rows, entry, generated_at_value)

    if issues:
        return {
            "result": "blocked",
            "issues": issues,
            "generated_sample_count": len(snapshot_payloads),
            "formal_data_write_allowed": True,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
        }

    (ashare_root / "daily-window-v0.1").mkdir(parents=True, exist_ok=True)
    (ashare_root / "malf-snapshots-v0.1").mkdir(parents=True, exist_ok=True)

    _write_csv(ashare_root / "candidate-universe-v0.1.csv", CANDIDATE_HEADER, candidate_rows)
    _write_csv(ashare_root / "sw-industry-membership-v0.1.csv", SW_HEADER, sw_rows)
    for ts_code, rows in daily_windows.items():
        _write_csv(ashare_root / "daily-window-v0.1" / f"{ts_code}.csv", DAILY_HEADER, rows)
    for ts_code, payload in snapshot_payloads.items():
        snapshot_name = f"{ts_code}-{payload['window_start'][0:7]}.json"
        (ashare_root / "malf-snapshots-v0.1" / snapshot_name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    (ashare_root / "first-batch-sample-manifest-v0.1.json").write_text(
        json.dumps(sample_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    readiness = audit_first_batch_readiness(root)
    front_filter = audit_first_batch_front_filter_run(root)
    record_drafts = audit_first_batch_record_drafts(root)
    sample_table_trial = audit_first_batch_sample_table_trial(root)
    coverage = audit_first_batch_sample_coverage(root)

    return {
        "result": "pass",
        "generated_sample_count": len(sample_manifest),
        "sample_manifest_file": "ashare/first-batch-sample-manifest-v0.1.json",
        "candidate_file": "ashare/candidate-universe-v0.1.csv",
        "sw_file": "ashare/sw-industry-membership-v0.1.csv",
        "daily_window_count": len(daily_windows),
        "snapshot_count": len(snapshot_payloads),
        "coverage_targets": sorted({str(item.get("expected_structure_target", "")) for item in sample_manifest if item.get("expected_structure_target")}),
        "formal_data_write_allowed": True,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "readiness_report": readiness,
        "front_filter_report": front_filter,
        "record_draft_report": record_drafts,
        "sample_table_trial_report": sample_table_trial,
        "coverage_report": coverage,
    }


def build_shortlist_sample_package(
    data_root: str | Path,
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
    sample_entries: list[dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    return build_first_batch_sample_package(
        data_root=data_root,
        tdx_root=tdx_root,
        offline_root=offline_root,
        duckdb_root=duckdb_root,
        sample_entries=sample_entries,
        generated_at=generated_at,
    )


def audit_first_batch_sample_coverage(data_root: str | Path) -> dict[str, Any]:
    root = Path(data_root)
    manifest_entries = _load_manifest_entries(root)
    target_by_ts_code = {
        str(entry.get("ts_code", "")): str(entry.get("expected_structure_target", ""))
        for entry in manifest_entries
        if entry.get("ts_code")
    }
    readiness = audit_first_batch_readiness(root)
    front_filter = audit_first_batch_front_filter_run(root)
    record_drafts = audit_first_batch_record_drafts(root)
    sample_table_trial = audit_first_batch_sample_table_trial(root)

    covered_targets = {
        target_by_ts_code.get(item.get("ts_code", ""), "")
        for item in front_filter.get("front_filter_results", [])
        if target_by_ts_code.get(item.get("ts_code", ""), "")
    }
    expected_targets = {
        str(entry.get("expected_structure_target", ""))
        for entry in manifest_entries
        if entry.get("expected_structure_target")
    }
    missing_targets = sorted(expected_targets.difference(covered_targets))
    trial_row_ids = [row.get("ashare_sample_id") for row in sample_table_trial.get("trial_rows", []) if row.get("ashare_sample_id")]

    return {
        "result": "pass" if readiness.get("result") == "pass" and front_filter.get("result") == "pass" else "blocked",
        "expected_structure_targets": sorted(expected_targets),
        "covered_structure_targets": sorted(covered_targets),
        "missing_structure_targets": missing_targets,
        "sample_gate_positions": [
            {
                "ts_code": item.get("ts_code"),
                "rhythm_meaning": item.get("rhythm_meaning"),
                "tachibana_applicability": item.get("tachibana_applicability"),
                "front_filter_result": item.get("front_filter_result"),
                "candidate_stage_after": item.get("candidate_stage_after"),
                "next_action": item.get("next_action"),
                "expected_structure_target": target_by_ts_code.get(item.get("ts_code", ""), "unknown"),
            }
            for item in front_filter.get("front_filter_results", [])
        ],
        "trial_row_sample_ids": trial_row_ids,
        "front_filter_ready_candidate_count": readiness.get("front_filter_ready_candidate_count", 0),
        "record_draft_count": record_drafts.get("record_draft_count", 0),
        "trial_row_count": sample_table_trial.get("trial_row_count", 0),
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_sample_table_trial" if not missing_targets else "action:register_missing_structure_targets",
    }


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
