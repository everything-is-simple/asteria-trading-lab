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


FORBIDDEN_OUTPUT_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "position_size",
    "ashare_t1_action",
    "limit_up_strategy",
    "limit_down_strategy",
}


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


DEFAULT_ADD_ON_PRICE_LIMIT_SHORTLIST_SAMPLE_ENTRIES = [
    {
        "ts_code": "603538.SH",
        "trade_date": "2026-04-01",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate with down-limit-side pressure-adjust value.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "603008.SH",
        "trade_date": "2026-03-30",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate with cleaner down-limit-side pressure-adjust shape.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "600310.SH",
        "trade_date": "2026-03-30",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate preserving scarce up-limit-side comparison value.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "603687.SH",
        "trade_date": "2026-03-27",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "core",
        "formal_review_bucket": "pressure_adjust_reopen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Core reopened-touch candidate extending the pressure-adjust comparison set to a fourth sample.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "002663.SZ",
        "trade_date": "2026-04-03",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "backup",
        "formal_review_bucket": "near_limit_compare",
        "core_snapshot_focus": "near_limit_compare_backup",
        "selection_reason": "Backup near-limit comparison sample kept for extreme down-limit-side proximity without touch.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
    },
    {
        "ts_code": "000899.SZ",
        "trade_date": "2026-03-30",
        "sample_window_start": "2026-03-24",
        "sample_window_end": "2026-04-03",
        "research_priority_group": "backup",
        "formal_review_bucket": "near_limit_compare",
        "core_snapshot_focus": "near_limit_compare_backup",
        "selection_reason": "Backup near-limit comparison sample kept as a steadier down-limit-side proximity control.",
        "evidence_ref": "docs/tachibana/index/Tachibana-A股-add_on-price_limit-shortlist-intraday-review-v0.1.md#formal-review-shortlist",
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


def build_shortlist_malf_research_prep(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
    sample_entries: list[dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    sample_manifest = deepcopy(sample_entries)
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")

    symbol_rows = read_symbol_master(tdx_root, offline_root, duckdb_root=duckdb_root)
    symbol_index = {row["ts_code"]: row for row in symbol_rows if isinstance(row, dict) and row.get("ts_code")}
    industry_index = _industry_membership_index(Path(duckdb_root))

    samples: list[dict[str, Any]] = []
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

        trade_date = str(entry.get("trade_date", ""))
        event_row = next((row for row in daily_rows if str(row.get("trade_date", "")) == trade_date), None)
        if trade_date and event_row is None:
            issues.append(f"event_trade_date_not_in_daily_window:{ts_code}:{trade_date}")
            continue

        industry_rows = industry_index.get(ts_code, [])
        overlapping_industry_row = _select_industry_row(
            industry_rows,
            str(entry.get("sample_window_start", "")),
            str(entry.get("sample_window_end", "")),
        )
        current_industry_row = _select_current_industry_row(industry_rows)

        industry_window_status = "overlapping" if overlapping_industry_row is not None else "not_overlapping"
        formal_front_filter_status = "snapshot_pending" if overlapping_industry_row is not None else "blocked"
        formal_front_filter_issue = (
            "pipeline_requires_ready_malf_snapshot"
            if overlapping_industry_row is not None
            else f"industry_membership_window_not_overlapping:{ts_code}"
        )
        if current_industry_row is None:
            industry_window_status = "missing"
            formal_front_filter_status = "blocked"
            formal_front_filter_issue = f"industry_membership_reference_missing:{ts_code}"

        symbol_name = str(symbol_row.get("symbol_name") or "UNKNOWN")
        snapshot_stub = _research_snapshot_stub(ts_code, daily_rows, entry, generated_at_value)
        suggested_snapshot_file = _suggested_snapshot_file(snapshot_stub)
        ashare_sample_id = _ashare_sample_id_suggestion(
            ts_code,
            snapshot_stub.get("window_start"),
            snapshot_stub.get("window_end"),
        )
        sample_report = {
            "ts_code": ts_code,
            "symbol_name": symbol_name,
            "trade_date": trade_date,
            "sample_window_start": str(entry.get("sample_window_start", "")),
            "sample_window_end": str(entry.get("sample_window_end", "")),
            "research_priority_group": _research_priority_group(entry),
            "formal_review_bucket": str(entry.get("formal_review_bucket", "unknown")),
            "core_snapshot_focus": str(entry.get("core_snapshot_focus", "research_prep_pending")),
            "selection_reason": str(entry.get("selection_reason", "")),
            "evidence_ref": str(entry.get("evidence_ref", "")),
            "event_trade_date_in_window": event_row is not None,
            "daily_window_row_count": len(daily_rows),
            "daily_window_source_ref": str(daily_rows[0].get("source_ref", "")),
            "event_day_summary": _event_day_summary(event_row),
            "current_industry_code": str(current_industry_row.get("relation_code", "")) if current_industry_row else None,
            "current_industry_name": str(current_industry_row.get("relation_name", "")) if current_industry_row else None,
            "current_industry_valid_from": str(current_industry_row.get("valid_from", "")) if current_industry_row else None,
            "current_industry_valid_to": str(current_industry_row.get("valid_to", "")) if current_industry_row else None,
            "current_industry_source_ref": str(current_industry_row.get("source_ref", "")) if current_industry_row else None,
            "current_industry_time_alignment_status": (
                "window_overlapping" if overlapping_industry_row is not None else "current_reference_only"
            ),
            "industry_window_status": industry_window_status,
            "formal_front_filter_status": formal_front_filter_status,
            "formal_front_filter_issue": formal_front_filter_issue,
            "snapshot_stub": snapshot_stub,
            "suggested_snapshot_file": suggested_snapshot_file,
            "ashare_sample_id_suggestion": ashare_sample_id,
            "suggested_front_filter_command": _front_filter_command(suggested_snapshot_file),
            "suggested_record_draft_command": _record_draft_command(
                suggested_snapshot_file,
                symbol_name,
                ashare_sample_id,
            ),
            "research_boundary_warning": _research_boundary_warning(
                research_priority_group=_research_priority_group(entry),
                formal_front_filter_status=formal_front_filter_status,
            ),
            "next_action": _research_next_action(formal_front_filter_status),
        }
        samples.append(sample_report)

    if issues:
        return _strip_forbidden_fields(
            {
                "result": "blocked",
                "issues": issues,
                "sample_count": len(samples),
                "research_only": True,
                "formal_data_write_allowed": False,
                "institution_rule_definition_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
            }
        )

    core_sample_count = sum(1 for item in samples if item.get("research_priority_group") == "core")
    backup_sample_count = sum(1 for item in samples if item.get("research_priority_group") == "backup")
    formal_front_filter_ready_count = sum(1 for item in samples if item.get("formal_front_filter_status") == "ready")
    blocked_formal_front_filter_count = sum(1 for item in samples if item.get("formal_front_filter_status") == "blocked")
    snapshot_pending_formal_front_filter_count = sum(
        1 for item in samples if item.get("formal_front_filter_status") == "snapshot_pending"
    )

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "sample_count": len(samples),
            "core_sample_count": core_sample_count,
            "backup_sample_count": backup_sample_count,
            "formal_front_filter_ready_count": formal_front_filter_ready_count,
            "blocked_formal_front_filter_count": blocked_formal_front_filter_count,
            "snapshot_pending_formal_front_filter_count": snapshot_pending_formal_front_filter_count,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "samples": samples,
            "next_action": "action:prepare_research_malf_snapshot",
        }
    )


def default_add_on_price_limit_shortlist_sample_entries() -> list[dict[str, Any]]:
    return deepcopy(DEFAULT_ADD_ON_PRICE_LIMIT_SHORTLIST_SAMPLE_ENTRIES)


def build_default_add_on_price_limit_shortlist_malf_research_prep(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    report = build_shortlist_malf_research_prep(
        tdx_root=tdx_root,
        offline_root=offline_root,
        duckdb_root=duckdb_root,
        sample_entries=default_add_on_price_limit_shortlist_sample_entries(),
        generated_at=generated_at,
    )
    report = dict(report)
    report["research_shortlist_id"] = "add_on_price_limit_shortlist_v0.1"
    report["research_shortlist_scope"] = "add_on_pullback_add_price_limit"
    return _strip_forbidden_fields(report)


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


def _suggested_snapshot_file(snapshot_stub: dict[str, Any]) -> str:
    ts_code = str(snapshot_stub.get("ts_code", "UNKNOWN"))
    window_start = str(snapshot_stub.get("window_start", "UNKNOWN"))
    return f"ashare/malf-snapshots-v0.1/{ts_code}-{window_start[0:7]}.json"


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
