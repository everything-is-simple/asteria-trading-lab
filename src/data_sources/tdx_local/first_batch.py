from __future__ import annotations

import csv
from copy import deepcopy
from datetime import datetime
import json
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


def audit_add_on_price_limit_shortlist_time_alignment(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
    sample_entries: list[dict[str, Any]] | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    entries = deepcopy(sample_entries) if sample_entries is not None else default_add_on_price_limit_shortlist_sample_entries()
    industry_index = _industry_membership_index(Path(duckdb_root))

    samples: list[dict[str, Any]] = []
    for entry in entries:
        ts_code = str(entry.get("ts_code", ""))
        industry_rows = industry_index.get(ts_code, [])
        overlapping_industry_row = _select_industry_row(
            industry_rows,
            str(entry.get("sample_window_start", "")),
            str(entry.get("sample_window_end", "")),
        )
        current_industry_row = _select_current_industry_row(industry_rows)

        original_status = "overlapping" if overlapping_industry_row is not None else "not_overlapping"
        original_issue = (
            "pipeline_requires_ready_malf_snapshot"
            if overlapping_industry_row is not None
            else f"industry_membership_window_not_overlapping:{ts_code}"
        )
        if current_industry_row is None:
            original_status = "missing"
            original_issue = f"industry_membership_reference_missing:{ts_code}"

        offline_daily_rows = read_daily_bars(offline_root, ts_code)
        updated_daily_rows = read_daily_bars(tdx_root, ts_code)
        if updated_daily_rows:
            selected_daily_rows = updated_daily_rows
            selected_daily_root = "tdx_root"
        else:
            selected_daily_rows = offline_daily_rows
            selected_daily_root = "offline_root"

        current_valid_from = str(current_industry_row.get("valid_from", "")) if current_industry_row else ""
        post_label_rows = [
            row for row in selected_daily_rows if current_valid_from and str(row.get("trade_date", "")) >= current_valid_from
        ]
        if original_status == "overlapping":
            next_action = "action:prepare_ready_malf_snapshot"
        elif post_label_rows:
            next_action = "action:rescreen_post_industry_effective_window"
        else:
            next_action = "action:source_time_aligned_industry_membership"

        samples.append(
            _strip_forbidden_fields(
                {
                    "ts_code": ts_code,
                    "trade_date": str(entry.get("trade_date", "")),
                    "sample_window_start": str(entry.get("sample_window_start", "")),
                    "sample_window_end": str(entry.get("sample_window_end", "")),
                    "research_priority_group": _research_priority_group(entry),
                    "original_industry_window_status": original_status,
                    "original_formal_front_filter_issue": original_issue,
                    "current_industry_code": str(current_industry_row.get("relation_code", "")) if current_industry_row else None,
                    "current_industry_name": str(current_industry_row.get("relation_name", "")) if current_industry_row else None,
                    "current_industry_valid_from": current_valid_from if current_industry_row else None,
                    "current_industry_valid_to": str(current_industry_row.get("valid_to", "")) if current_industry_row else None,
                    "offline_daily_last_trade_date": _last_trade_date(offline_daily_rows),
                    "updated_daily_source_root": selected_daily_root,
                    "updated_daily_last_trade_date": _last_trade_date(selected_daily_rows),
                    "post_label_daily_row_count": len(post_label_rows),
                    "post_label_first_trade_date": str(post_label_rows[0].get("trade_date", "")) if post_label_rows else None,
                    "post_label_last_trade_date": str(post_label_rows[-1].get("trade_date", "")) if post_label_rows else None,
                    "time_alignment_next_action": next_action,
                }
            )
        )

    original_blocked_count = sum(1 for item in samples if item.get("original_industry_window_status") != "overlapping")
    post_label_daily_available_count = sum(1 for item in samples if int(item.get("post_label_daily_row_count", 0)) > 0)
    return _strip_forbidden_fields(
        {
            "result": "pass" if original_blocked_count == 0 else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "sample_count": len(samples),
            "original_window_blocked_count": original_blocked_count,
            "post_label_daily_available_count": post_label_daily_available_count,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "samples": samples,
            "next_action": (
                "action:prepare_ready_malf_snapshot"
                if original_blocked_count == 0
                else "action:rescreen_post_industry_effective_window"
                if post_label_daily_available_count
                else "action:source_time_aligned_industry_membership"
            ),
        }
    )


def rescreen_add_on_price_limit_post_industry_window(
    tdx_root: str | Path,
    duckdb_root: str | Path,
    window_start: str,
    window_end: str,
    ts_codes: list[str] | None = None,
    limit: int = 20,
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    if ts_codes is None:
        return _rescreen_add_on_price_limit_post_industry_window_from_duckdb(
            duckdb_root=duckdb_root,
            window_start=window_start,
            window_end=window_end,
            limit=limit,
            generated_at=generated_at_value,
        )

    symbol_rows = read_symbol_master(tdx_root, tdx_root, duckdb_root=duckdb_root)
    symbol_index = {row["ts_code"]: row for row in symbol_rows if isinstance(row, dict) and row.get("ts_code")}
    selected_ts_codes = ts_codes
    industry_index = _industry_membership_index(Path(duckdb_root))

    candidates: list[dict[str, Any]] = []
    issues: list[str] = []
    scanned_symbol_count = 0
    time_aligned_symbol_count = 0

    for ts_code in selected_ts_codes:
        scanned_symbol_count += 1
        symbol_row = symbol_index.get(ts_code)
        if symbol_row is None:
            issues.append(f"missing_symbol_master:{ts_code}")
            continue

        industry_rows = industry_index.get(ts_code, [])
        industry_row = _select_industry_row(industry_rows, window_start, window_end)
        current_industry_row = _select_current_industry_row(industry_rows)
        if industry_row is None:
            continue
        time_aligned_symbol_count += 1

        daily_rows = read_daily_bars(tdx_root, ts_code)
        candidate = _select_post_label_price_limit_candidate(
            daily_rows=daily_rows,
            symbol_row=symbol_row,
            industry_row=industry_row,
            current_industry_row=current_industry_row,
            ts_code=ts_code,
            window_start=window_start,
            window_end=window_end,
            generated_at=generated_at_value,
        )
        if candidate is not None:
            candidates.append(candidate)

    candidates.sort(
        key=lambda item: (
            float(item["nearest_limit_gap_pct"]),
            -float(item["runup_pct"]),
            abs(float(item["close_return_pct"])),
            str(item["ts_code"]),
        )
    )
    candidates = candidates[:limit]
    for index, candidate in enumerate(candidates, 1):
        candidate["post_label_rescreen_rank"] = index

    next_action = "action:review_intraday_price_limit_reopen" if candidates else "action:expand_post_industry_rescreen_window"
    result = "pass" if candidates else "blocked"
    if issues and not candidates:
        next_action = "action:repair_post_industry_rescreen_sources"

    return _strip_forbidden_fields(
        {
            "result": result,
            "generated_at": generated_at_value,
            "research_only": True,
            "rescreen_id": "add_on_price_limit_post_industry_rescreen_v0.1",
            "rescreen_scope": "add_on_pullback_add_price_limit_post_industry_effective_window",
            "window_start": window_start,
            "window_end": window_end,
            "source_daily_root": "tdx_root",
            "scanned_symbol_count": scanned_symbol_count,
            "time_aligned_symbol_count": time_aligned_symbol_count,
            "candidate_count": len(candidates),
            "formal_front_filter_ready_count": 0,
            "snapshot_pending_formal_front_filter_count": len(candidates),
            "issues": issues,
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def _rescreen_add_on_price_limit_post_industry_window_from_duckdb(
    duckdb_root: str | Path,
    window_start: str,
    window_end: str,
    limit: int,
    generated_at: str,
) -> dict[str, Any]:
    rows = screen_pullback_add_price_limit_candidates(
        duckdb_root=duckdb_root,
        window_start=window_start,
        window_end=window_end,
        limit=limit,
        require_industry_window_overlap=True,
    )
    industry_index = _industry_membership_index(Path(duckdb_root))
    candidates = [
        _duckdb_post_label_candidate_report(row, industry_index, window_start, window_end, generated_at)
        for row in rows
    ]
    for index, candidate in enumerate(candidates, 1):
        candidate["post_label_rescreen_rank"] = index

    return _strip_forbidden_fields(
        {
            "result": "pass" if candidates else "blocked",
            "generated_at": generated_at,
            "research_only": True,
            "rescreen_id": "add_on_price_limit_post_industry_rescreen_v0.1",
            "rescreen_scope": "add_on_pullback_add_price_limit_post_industry_effective_window",
            "window_start": window_start,
            "window_end": window_end,
            "source_daily_root": "duckdb_market_base_day",
            "scanned_symbol_count": None,
            "time_aligned_symbol_count": len(rows),
            "candidate_count": len(candidates),
            "formal_front_filter_ready_count": 0,
            "snapshot_pending_formal_front_filter_count": len(candidates),
            "issues": [],
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": (
                "action:review_intraday_price_limit_reopen"
                if candidates
                else "action:expand_post_industry_rescreen_window"
            ),
        }
    )


def review_add_on_price_limit_post_label_intraday_reopen(
    tdx_root: str | Path,
    rescreen_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in rescreen_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_rescreen_candidate")
            continue
        reviewed = _attach_post_label_intraday_reopen_review(Path(tdx_root), candidate)
        candidates.append(reviewed)

    reopened_count = sum(
        1 for item in candidates if item.get("intraday_limit_reopen_status") == "reopened_after_limit_touch"
    )
    closed_count = sum(
        1 for item in candidates if item.get("intraday_limit_reopen_status") == "closed_at_limit_after_touch"
    )
    near_count = sum(
        1 for item in candidates if item.get("intraday_limit_reopen_status") == "near_limit_without_touch"
    )
    blocked_count = sum(1 for item in candidates if item.get("intraday_review_result") == "blocked")
    daily_level_pending_count = sum(
        1 for item in candidates if item.get("daily_level_malf_review_status") == "pending"
    )

    next_action = (
        "action:review_malf_structure_evidence"
        if reopened_count or near_count
        else "action:review_daily_level_malf_structure"
        if daily_level_pending_count
        else "action:source_intraday_price_limit_review"
    )
    if issues and not candidates:
        next_action = "action:repair_post_label_intraday_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if candidates and (blocked_count < len(candidates) or daily_level_pending_count) else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "add_on_price_limit_post_label_intraday_reopen_review_v0.1",
            "review_scope": "daily_level_malf_structure_with_optional_intraday_enhancement",
            "source_rescreen_id": rescreen_report.get("rescreen_id"),
            "window_start": rescreen_report.get("window_start"),
            "window_end": rescreen_report.get("window_end"),
            "reviewed_candidate_count": len(candidates),
            "reopened_after_limit_touch_count": reopened_count,
            "closed_at_limit_after_touch_count": closed_count,
            "near_limit_without_touch_count": near_count,
            "blocked_intraday_review_count": blocked_count,
            "daily_level_malf_review_pending_count": daily_level_pending_count,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def review_add_on_price_limit_post_label_daily_malf_structure(
    source_review_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in source_review_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_daily_malf_candidate")
            continue
        candidates.append(_attach_post_label_daily_malf_structure_review(candidate))

    pass_count = sum(1 for item in candidates if item.get("daily_level_malf_review_status") == "pass")
    manual_count = sum(
        1 for item in candidates if item.get("daily_level_malf_review_status") == "manual_review_required"
    )
    blocked_count = sum(1 for item in candidates if item.get("daily_level_malf_review_status") == "blocked")
    next_action = (
        "action:prepare_malf_snapshot_draft_review"
        if pass_count
        else "action:hold_for_daily_level_malf_evidence"
    )
    if issues and not candidates:
        next_action = "action:repair_daily_level_malf_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if pass_count else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "add_on_price_limit_post_label_daily_malf_structure_review_v0.1",
            "source_review_id": source_review_report.get("review_id") or source_review_report.get("rescreen_id"),
            "window_start": source_review_report.get("window_start"),
            "window_end": source_review_report.get("window_end"),
            "reviewed_candidate_count": len(candidates),
            "daily_level_malf_review_pass_count": pass_count,
            "daily_level_malf_manual_review_required_count": manual_count,
            "daily_level_malf_blocked_count": blocked_count,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_malf_snapshot_draft_review(
    daily_malf_review_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in daily_malf_review_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_snapshot_draft_review_candidate")
            continue
        candidates.append(_attach_malf_snapshot_draft_review(candidate, generated_at_value))

    ready_count = sum(
        1 for item in candidates if item.get("snapshot_draft_review_status") == "ready_for_manual_review"
    )
    hold_count = sum(1 for item in candidates if item.get("snapshot_draft_review_status") == "hold")
    next_action = (
        "action:manual_review_malf_snapshot_drafts"
        if ready_count
        else "action:hold_for_malf_snapshot_draft_inputs"
    )
    if issues and not candidates:
        next_action = "action:repair_malf_snapshot_draft_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if ready_count else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "malf_snapshot_draft_review_prep_v0.1",
            "source_review_id": daily_malf_review_report.get("review_id"),
            "window_start": daily_malf_review_report.get("window_start"),
            "window_end": daily_malf_review_report.get("window_end"),
            "draft_review_candidate_count": len(candidates),
            "draft_review_ready_count": ready_count,
            "draft_review_hold_count": hold_count,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def apply_malf_snapshot_manual_review_verdicts(
    draft_review_report: dict[str, Any],
    manual_verdicts: dict[str, dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in draft_review_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_manual_snapshot_review_candidate")
            continue
        ts_code = str(candidate.get("ts_code", ""))
        candidates.append(_attach_malf_snapshot_manual_verdict(candidate, manual_verdicts.get(ts_code), generated_at_value))

    approved_count = sum(1 for item in candidates if item.get("manual_review_status") == "reviewed_ready_candidate")
    hold_count = sum(1 for item in candidates if item.get("manual_review_status") != "reviewed_ready_candidate")
    next_action = (
        "action:prepare_formal_front_filter_review_package"
        if approved_count
        else "action:hold_for_manual_malf_snapshot_review"
    )
    if issues and not candidates:
        next_action = "action:repair_manual_malf_snapshot_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if approved_count else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "malf_snapshot_manual_review_verdicts_v0.1",
            "source_review_id": draft_review_report.get("review_id"),
            "manual_reviewed_candidate_count": len(candidates),
            "manual_review_approved_count": approved_count,
            "manual_review_hold_count": hold_count,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "candidates": candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_formal_front_filter_review_package(
    manual_review_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    review_inputs: list[dict[str, Any]] = []
    held_candidates: list[dict[str, Any]] = []
    issues: list[str] = []

    for candidate in manual_review_report.get("candidates", []):
        if not isinstance(candidate, dict):
            issues.append("invalid_formal_front_filter_review_candidate")
            continue
        review_input = _formal_front_filter_review_input(candidate)
        if review_input is None:
            held_candidates.append(
                {
                    "ts_code": candidate.get("ts_code"),
                    "trade_date": candidate.get("trade_date"),
                    "front_filter_review_package_status": "hold",
                    "front_filter_review_package_reason": "reviewed_snapshot_candidate_missing",
                }
            )
            continue
        review_inputs.append(review_input)

    next_action = (
        "action:run_formal_front_filter_audit_when_explicitly_requested"
        if review_inputs
        else "action:hold_for_reviewed_malf_snapshot_candidates"
    )
    if issues and not review_inputs and not held_candidates:
        next_action = "action:repair_formal_front_filter_review_package_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if review_inputs else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "formal_front_filter_review_package_v0.1",
            "source_review_id": manual_review_report.get("review_id"),
            "front_filter_review_input_count": len(review_inputs),
            "front_filter_review_hold_count": len(held_candidates),
            "front_filter_execution_allowed": False,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "front_filter_review_inputs": review_inputs,
            "held_candidates": held_candidates,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def audit_formal_front_filter_review_package(
    review_package: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    from tachibana_front_filter import run_front_filter

    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    review_inputs = review_package.get("front_filter_review_inputs", [])
    issues: list[str] = []
    audit_results: list[dict[str, Any]] = []

    if not isinstance(review_inputs, list) or not review_inputs:
        issues.append("front_filter_review_inputs_missing")
        review_inputs = []

    with tempfile.TemporaryDirectory(prefix="formal-front-filter-audit-") as tmp:
        tmp_root = Path(tmp)
        for index, review_input in enumerate(review_inputs):
            if not isinstance(review_input, dict):
                issues.append("invalid_front_filter_review_input")
                audit_results.append(
                    {
                        "formal_front_filter_audit_status": "blocked",
                        "audit_issues": ["invalid_front_filter_review_input"],
                    }
                )
                continue

            audit_snapshot, snapshot_issues = _formal_front_filter_audit_snapshot(review_input)
            if snapshot_issues:
                audit_results.append(_blocked_formal_front_filter_audit_result(review_input, snapshot_issues))
                continue

            snapshot_path = tmp_root / f"front-filter-audit-{index}.json"
            snapshot_path.write_text(json.dumps(audit_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            front_filter_report = run_front_filter(snapshot_path)
            audit_results.append(_formal_front_filter_audit_result(review_input, audit_snapshot, front_filter_report))

    blocked_results = [
        item for item in audit_results if item.get("formal_front_filter_audit_status") != "pass"
    ]
    pass_count = len(audit_results) - len(blocked_results)

    if not audit_results:
        next_action = "action:hold_for_formal_front_filter_review_inputs"
    elif blocked_results:
        next_action = "action:repair_formal_front_filter_review_inputs"
    else:
        next_action = "action:prepare_qualification_record_draft_review_when_explicitly_requested"

    return _strip_forbidden_fields(
        {
            "result": "pass" if audit_results and not blocked_results else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "formal_front_filter_review_audit_v0.1",
            "source_package_id": review_package.get("package_id"),
            "audited_front_filter_input_count": len(audit_results),
            "formal_front_filter_audit_pass_count": pass_count,
            "formal_front_filter_audit_blocked_count": len(blocked_results),
            "front_filter_execution_allowed": False,
            "formal_front_filter_ready_count": 0,
            "issues": issues,
            "front_filter_audit_results": audit_results,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_qualification_record_draft_review(
    front_filter_audit_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    from tachibana_front_filter import build_qualification_record_draft

    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    review_inputs: list[dict[str, Any]] = []
    held_results: list[dict[str, Any]] = []
    issues: list[str] = []

    audit_results = front_filter_audit_report.get("front_filter_audit_results", [])
    if not isinstance(audit_results, list) or not audit_results:
        issues.append("front_filter_audit_results_missing")
        audit_results = []

    for audit_result in audit_results:
        if not isinstance(audit_result, dict):
            issues.append("invalid_front_filter_audit_result")
            continue
        if audit_result.get("formal_front_filter_audit_status") != "pass":
            held_results.append(_held_qualification_record_draft_review_result(audit_result, "formal_front_filter_audit_not_pass"))
            continue
        if audit_result.get("front_filter_result") != "pass":
            held_results.append(_held_qualification_record_draft_review_result(audit_result, "front_filter_result_not_pass"))
            continue

        front_filter_report = _qualification_record_draft_front_filter_report(audit_result)
        draft = build_qualification_record_draft(
            front_filter_report,
            ashare_sample_id=str(audit_result.get("ashare_sample_id") or audit_result.get("ashare_sample_id_suggestion") or _fallback_ashare_sample_id(audit_result)),
            symbol_name=str(audit_result.get("symbol_name") or "UNKNOWN"),
            candidate_stage_before="structure_candidate",
        )
        review_inputs.append(_qualification_record_draft_review_input(audit_result, draft))

    next_action = (
        "action:manual_review_qualification_record_drafts"
        if review_inputs
        else "action:hold_for_formal_front_filter_audit_passes"
    )
    if issues and not review_inputs and not held_results:
        next_action = "action:repair_qualification_record_draft_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if review_inputs else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "qualification_record_draft_review_package_v0.1",
            "source_audit_id": front_filter_audit_report.get("audit_id"),
            "qualification_record_draft_review_input_count": len(review_inputs),
            "qualification_record_draft_review_hold_count": len(held_results),
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "qualification_record_draft_review_inputs": review_inputs,
            "held_audit_results": held_results,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def apply_qualification_record_draft_manual_verdicts(
    draft_review_report: dict[str, Any],
    manual_verdicts: dict[str, dict[str, Any]],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    reviewed_drafts: list[dict[str, Any]] = []
    issues: list[str] = []

    review_inputs = draft_review_report.get("qualification_record_draft_review_inputs", [])
    if not isinstance(review_inputs, list) or not review_inputs:
        issues.append("qualification_record_draft_review_inputs_missing")
        review_inputs = []

    for draft_input in review_inputs:
        if not isinstance(draft_input, dict):
            issues.append("invalid_qualification_record_draft_review_input")
            continue
        record_id = str(draft_input.get("qualification_record_id", ""))
        reviewed_drafts.append(
            _attach_qualification_record_draft_manual_verdict(
                draft_input,
                manual_verdicts.get(record_id),
                generated_at_value,
            )
        )

    approved_count = sum(
        1
        for item in reviewed_drafts
        if item.get("qualification_record_manual_review_status")
        == "approved_for_formal_record_write_audit_candidate"
    )
    hold_count = len(reviewed_drafts) - approved_count
    next_action = (
        "action:prepare_formal_qualification_record_write_audit_when_explicitly_requested"
        if approved_count
        else "action:hold_for_manual_qualification_record_draft_review"
    )
    if issues and not reviewed_drafts:
        next_action = "action:repair_qualification_record_draft_manual_review_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if approved_count else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "review_id": "qualification_record_draft_manual_verdicts_v0.1",
            "source_package_id": draft_review_report.get("package_id"),
            "manual_reviewed_draft_count": len(reviewed_drafts),
            "manual_review_approved_count": approved_count,
            "manual_review_hold_count": hold_count,
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "qualification_record_draft_manual_verdicts": reviewed_drafts,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_formal_qualification_record_write_audit(
    manual_review_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    audit_candidates: list[dict[str, Any]] = []
    held_results: list[dict[str, Any]] = []
    issues: list[str] = []

    manual_results = manual_review_report.get("qualification_record_draft_manual_verdicts", [])
    if not isinstance(manual_results, list) or not manual_results:
        issues.append("qualification_record_draft_manual_verdicts_missing")
        manual_results = []

    for manual_result in manual_results:
        if not isinstance(manual_result, dict):
            issues.append("invalid_qualification_record_draft_manual_verdict")
            continue
        if (
            manual_result.get("qualification_record_manual_review_status")
            != "approved_for_formal_record_write_audit_candidate"
        ):
            held_results.append(
                _held_formal_qualification_record_write_audit_result(
                    manual_result,
                    "manual_review_not_approved_for_formal_record_write_audit",
                )
            )
            continue
        audit_candidates.append(_formal_qualification_record_write_audit_candidate(manual_result, generated_at_value))

    next_action = (
        "action:prepare_formal_qualification_record_persistence_package_when_explicitly_requested"
        if audit_candidates
        else "action:hold_for_formal_qualification_record_write_audit_candidates"
    )
    if issues and not audit_candidates and not held_results:
        next_action = "action:repair_formal_qualification_record_write_audit_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if audit_candidates else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "audit_id": "formal_qualification_record_write_audit_v0.1",
            "source_review_id": manual_review_report.get("review_id"),
            "formal_record_write_audit_candidate_count": len(audit_candidates),
            "formal_record_write_audit_hold_count": len(held_results),
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "formal_record_write_audit_candidates": audit_candidates,
            "held_manual_review_results": held_results,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def prepare_formal_qualification_record_persistence_package_when_explicitly_requested(
    write_audit_report: dict[str, Any],
    generated_at: str | None = None,
) -> dict[str, Any]:
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    persistence_packages: list[dict[str, Any]] = []
    held_items: list[dict[str, Any]] = []
    issues: list[str] = []

    audit_candidates = write_audit_report.get("formal_record_write_audit_candidates", [])
    if not isinstance(audit_candidates, list) or not audit_candidates:
        issues.append("formal_record_write_audit_candidates_missing")
        audit_candidates = []

    for audit_candidate in audit_candidates:
        if not isinstance(audit_candidate, dict):
            issues.append("invalid_formal_record_write_audit_candidate")
            continue
        if audit_candidate.get("formal_record_write_audit_status") != "pass":
            held_items.append(
                _held_formal_qualification_record_persistence_item(
                    audit_candidate,
                    "formal_record_write_audit_not_pass",
                )
            )
            continue
        persistence_packages.append(_formal_qualification_record_persistence_package(audit_candidate, generated_at_value))

    next_action = (
        "action:prepare_candidate_table_update_audit_when_explicitly_requested"
        if persistence_packages
        else "action:hold_for_formal_qualification_record_write_audit_passes"
    )
    if issues and not persistence_packages and not held_items:
        next_action = "action:repair_formal_qualification_record_persistence_package_input"

    return _strip_forbidden_fields(
        {
            "result": "pass" if persistence_packages else "blocked",
            "generated_at": generated_at_value,
            "research_only": True,
            "package_id": "formal_qualification_record_persistence_package_v0.1",
            "source_audit_id": write_audit_report.get("audit_id"),
            "qualification_record_persistence_package_prepared": bool(persistence_packages),
            "qualification_record_persistence_performed": False,
            "qualification_record_persistence_package_count": len(persistence_packages),
            "held_qualification_record_persistence_count": len(held_items),
            "formal_front_filter_ready_count": 0,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "issues": issues,
            "qualification_record_persistence_packages": persistence_packages,
            "held_qualification_record_persistence_items": held_items,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


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


def materialize_default_add_on_price_limit_core_malf_research_bundle(
    data_root: str | Path,
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = Path(data_root)
    generated_at_value = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")
    report = build_default_add_on_price_limit_shortlist_malf_research_prep(
        tdx_root=tdx_root,
        offline_root=offline_root,
        duckdb_root=duckdb_root,
        generated_at=generated_at_value,
    )
    if report.get("result") != "pass":
        return _strip_forbidden_fields(dict(report))

    bundle_root = root / "research" / "add_on-price-limit-shortlist-v0.1"
    daily_root = bundle_root / "daily-window-v0.1"
    stub_root = bundle_root / "malf-snapshot-stubs-v0.1"
    draft_root = bundle_root / "malf-snapshot-drafts-v0.1"
    sample_manifest = default_add_on_price_limit_shortlist_sample_entries()
    sample_entry_index = {str(item.get("ts_code", "")): item for item in sample_manifest if item.get("ts_code")}

    core_samples = [item for item in report.get("samples", []) if item.get("research_priority_group") == "core"]
    backup_samples = [item for item in report.get("samples", []) if item.get("research_priority_group") == "backup"]

    materialized_core_samples: list[dict[str, Any]] = []
    materialized_backup_samples: list[dict[str, Any]] = []

    for sample in core_samples:
        ts_code = str(sample.get("ts_code", ""))
        entry = sample_entry_index.get(ts_code)
        if entry is None:
            continue
        daily_rows = _window_rows(read_daily_bars(offline_root, ts_code), entry)
        if not daily_rows:
            continue

        daily_file = daily_root / f"{ts_code}.csv"
        _write_csv(daily_file, DAILY_HEADER, [_daily_row(ts_code, row) for row in daily_rows])

        snapshot_stub = dict(sample.get("snapshot_stub", {}))
        snapshot_stub["source_daily_file"] = f"daily-window-v0.1/{ts_code}.csv"
        snapshot_stub["research_prep_status"] = "stub_pending_manual_malf_fill"
        snapshot_stub = _apply_manual_malf_fill_contract(snapshot_stub, entry)
        snapshot_file_rel = f"malf-snapshot-stubs-v0.1/{ts_code}-{str(snapshot_stub.get('window_start', 'UNKNOWN'))[0:7]}.json"
        stub_file = stub_root / f"{ts_code}-{str(snapshot_stub.get('window_start', 'UNKNOWN'))[0:7]}.json"
        stub_file.parent.mkdir(parents=True, exist_ok=True)
        stub_file.write_text(json.dumps(snapshot_stub, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        snapshot_draft = _research_snapshot_draft(snapshot_stub, entry)
        draft_file = draft_root / f"{ts_code}-{str(snapshot_stub.get('window_start', 'UNKNOWN'))[0:7]}.json"
        draft_file.parent.mkdir(parents=True, exist_ok=True)
        draft_file.write_text(json.dumps(snapshot_draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        draft_file_rel = f"malf-snapshot-drafts-v0.1/{draft_file.name}"

        materialized_front_filter_command = _front_filter_command(
            f"research/add_on-price-limit-shortlist-v0.1/{snapshot_file_rel}"
        )
        materialized_record_draft_command = _record_draft_command(
            f"research/add_on-price-limit-shortlist-v0.1/{snapshot_file_rel}",
            str(sample.get("symbol_name", "UNKNOWN")),
            str(sample.get("ashare_sample_id_suggestion", "")),
        )
        materialized_core_samples.append(
            _strip_forbidden_fields(
                {
                    **sample,
                    "snapshot_stub": snapshot_stub,
                    "snapshot_draft": snapshot_draft,
                    "materialized_daily_window_file": f"research/add_on-price-limit-shortlist-v0.1/daily-window-v0.1/{ts_code}.csv",
                    "materialized_snapshot_stub_file": f"research/add_on-price-limit-shortlist-v0.1/{snapshot_file_rel}",
                    "materialized_snapshot_draft_file": f"research/add_on-price-limit-shortlist-v0.1/{draft_file_rel}",
                    "materialized_front_filter_command": materialized_front_filter_command,
                    "materialized_record_draft_command": materialized_record_draft_command,
                }
            )
        )

    for sample in backup_samples:
        materialized_backup_samples.append(
            _strip_forbidden_fields(
                {
                    **sample,
                    "compare_role": "near_limit_backup_control",
                    "materialized_daily_window_file": None,
                    "materialized_snapshot_stub_file": None,
                    "materialized_snapshot_draft_file": None,
                    "materialized_front_filter_command": None,
                    "materialized_record_draft_command": None,
                }
            )
        )

    core_manifest = _strip_forbidden_fields(
        {
            "research_only": True,
            "research_shortlist_id": report.get("research_shortlist_id"),
            "research_shortlist_scope": report.get("research_shortlist_scope"),
            "bundle_role": "core_malf_snapshot_prep",
            "generated_at": generated_at_value,
            "sample_count": len(materialized_core_samples),
            "samples": materialized_core_samples,
        }
    )
    backup_manifest = _strip_forbidden_fields(
        {
            "research_only": True,
            "research_shortlist_id": report.get("research_shortlist_id"),
            "research_shortlist_scope": report.get("research_shortlist_scope"),
            "bundle_role": "near_limit_compare_backup",
            "generated_at": generated_at_value,
            "sample_count": len(materialized_backup_samples),
            "samples": materialized_backup_samples,
        }
    )
    front_filter_prep = _strip_forbidden_fields(
        {
            **dict(report),
            "samples": materialized_core_samples,
            "core_sample_count": len(materialized_core_samples),
            "backup_sample_count": len(materialized_backup_samples),
            "blocked_formal_front_filter_count": sum(
                1 for item in materialized_core_samples if item.get("formal_front_filter_status") == "blocked"
            ),
            "snapshot_pending_formal_front_filter_count": sum(
                1 for item in materialized_core_samples if item.get("formal_front_filter_status") == "snapshot_pending"
            ),
        }
    )

    bundle_root.mkdir(parents=True, exist_ok=True)
    (bundle_root / "core-malf-snapshot-prep-manifest-v0.1.json").write_text(
        json.dumps(core_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (bundle_root / "near-limit-compare-manifest-v0.1.json").write_text(
        json.dumps(backup_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (bundle_root / "front-filter-research-prep-v0.1.json").write_text(
        json.dumps(front_filter_prep, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "generated_at": generated_at_value,
            "research_only": True,
            "research_bundle_root": "research/add_on-price-limit-shortlist-v0.1",
            "research_shortlist_id": report.get("research_shortlist_id"),
            "research_shortlist_scope": report.get("research_shortlist_scope"),
            "core_sample_count": len(materialized_core_samples),
            "backup_sample_count": len(materialized_backup_samples),
            "core_daily_window_count": len(materialized_core_samples),
            "core_snapshot_stub_count": len(materialized_core_samples),
            "core_snapshot_draft_count": len(materialized_core_samples),
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "core_manifest_file": "research/add_on-price-limit-shortlist-v0.1/core-malf-snapshot-prep-manifest-v0.1.json",
            "backup_manifest_file": "research/add_on-price-limit-shortlist-v0.1/near-limit-compare-manifest-v0.1.json",
            "front_filter_prep_file": "research/add_on-price-limit-shortlist-v0.1/front-filter-research-prep-v0.1.json",
            "next_action": "action:fill_core_malf_snapshot_stubs",
        }
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


def _select_post_label_price_limit_candidate(
    daily_rows: list[dict[str, Any]],
    symbol_row: dict[str, Any],
    industry_row: dict[str, str | None],
    current_industry_row: dict[str, str | None] | None,
    ts_code: str,
    window_start: str,
    window_end: str,
    generated_at: str,
) -> dict[str, Any] | None:
    indexed_rows = sorted(daily_rows, key=lambda item: str(item.get("trade_date", "")))
    rows_by_date = {str(row.get("trade_date", "")): index for index, row in enumerate(indexed_rows)}
    selected: list[dict[str, Any]] = []

    for index, row in enumerate(indexed_rows):
        trade_date = str(row.get("trade_date", ""))
        if trade_date < window_start or trade_date > window_end:
            continue
        if index < 6:
            continue
        prev_row = indexed_rows[index - 1]
        prior_rows = indexed_rows[max(0, index - 6) : index]
        if len(prior_rows) < 4:
            continue
        prev_close = _to_float(prev_row.get("close"))
        close_price = _to_float(row.get("close"))
        high_price = _to_float(row.get("high"))
        low_price = _to_float(row.get("low"))
        prior_highs = [_to_float(item.get("high")) for item in prior_rows]
        prior_lows = [_to_float(item.get("low")) for item in prior_rows]
        prev4_closes = [_to_float(item.get("close")) for item in indexed_rows[max(0, index - 4) : index]]
        if (
            prev_close is None
            or close_price is None
            or high_price is None
            or low_price is None
            or any(value is None for value in prior_highs + prior_lows + prev4_closes)
        ):
            continue

        prior_6d_high = max(value for value in prior_highs if value is not None)
        prior_6d_low = min(value for value in prior_lows if value is not None)
        avg_prev4_close = sum(value for value in prev4_closes if value is not None) / len(prev4_closes)
        if prior_6d_low == 0 or avg_prev4_close == 0 or prev_close == 0:
            continue

        limit_pct = _limit_pct_for_ts_code(ts_code)
        limit_up_price = round(prev_close * (1.0 + limit_pct), 4)
        limit_down_price = round(prev_close * (1.0 - limit_pct), 4)
        runup_pct = (prior_6d_high / prior_6d_low - 1.0) * 100.0
        prior_peak_vs_recent_avg_pct = (prior_6d_high / avg_prev4_close - 1.0) * 100.0
        close_return_pct = (close_price / prev_close - 1.0) * 100.0
        gap_to_up_limit_pct = abs(high_price - limit_up_price) / limit_up_price * 100.0
        gap_to_down_limit_pct = abs(low_price - limit_down_price) / limit_down_price * 100.0
        nearest_limit_gap_pct = min(gap_to_up_limit_pct, gap_to_down_limit_pct)

        if runup_pct < 12.0:
            continue
        if prior_peak_vs_recent_avg_pct < 4.0:
            continue
        if close_return_pct > -2.0:
            continue
        if nearest_limit_gap_pct > 3.0:
            continue

        selected.append(
            _post_label_candidate_report(
                ts_code=ts_code,
                symbol_row=symbol_row,
                industry_row=industry_row,
                current_industry_row=current_industry_row,
                row=row,
                window_start=window_start,
                window_end=window_end,
                generated_at=generated_at,
                prev_close=prev_close,
                prior_6d_high=prior_6d_high,
                prior_6d_low=prior_6d_low,
                avg_prev4_close=avg_prev4_close,
                limit_up_price=limit_up_price,
                limit_down_price=limit_down_price,
                runup_pct=runup_pct,
                prior_peak_vs_recent_avg_pct=prior_peak_vs_recent_avg_pct,
                close_return_pct=close_return_pct,
                gap_to_up_limit_pct=gap_to_up_limit_pct,
                gap_to_down_limit_pct=gap_to_down_limit_pct,
                rows_by_date=rows_by_date,
            )
        )

    if not selected:
        return None
    selected.sort(
        key=lambda item: (
            float(item["nearest_limit_gap_pct"]),
            -float(item["runup_pct"]),
            abs(float(item["close_return_pct"])),
            str(item["trade_date"]),
        )
    )
    return selected[0]


def _post_label_candidate_report(
    ts_code: str,
    symbol_row: dict[str, Any],
    industry_row: dict[str, str | None],
    current_industry_row: dict[str, str | None] | None,
    row: dict[str, Any],
    window_start: str,
    window_end: str,
    generated_at: str,
    prev_close: float,
    prior_6d_high: float,
    prior_6d_low: float,
    avg_prev4_close: float,
    limit_up_price: float,
    limit_down_price: float,
    runup_pct: float,
    prior_peak_vs_recent_avg_pct: float,
    close_return_pct: float,
    gap_to_up_limit_pct: float,
    gap_to_down_limit_pct: float,
    rows_by_date: dict[str, int],
) -> dict[str, Any]:
    nearest_limit_side = "up_limit_side" if gap_to_up_limit_pct <= gap_to_down_limit_pct else "down_limit_side"
    nearest_limit_gap_pct = min(gap_to_up_limit_pct, gap_to_down_limit_pct)
    trade_date = str(row.get("trade_date", ""))
    symbol_name = str(symbol_row.get("symbol_name") or "UNKNOWN")
    entry = {
        "ts_code": ts_code,
        "trade_date": trade_date,
        "sample_window_start": window_start,
        "sample_window_end": window_end,
        "research_priority_group": "core",
        "formal_review_bucket": "post_label_rescreen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Post-industry-effective-window add_on / price_limit research candidate.",
        "evidence_ref": "post_industry_effective_window_rescreen_v0.1",
    }
    snapshot_stub = _apply_manual_malf_fill_contract(
        _research_snapshot_stub(ts_code, [row], entry, generated_at),
        entry,
    )
    return {
        "ts_code": ts_code,
        "symbol_name": symbol_name,
        "trade_date": trade_date,
        "sample_window_start": window_start,
        "sample_window_end": window_end,
        "industry_window_status": "overlapping",
        "current_industry_code": str((current_industry_row or industry_row).get("relation_code", "")),
        "current_industry_name": str((current_industry_row or industry_row).get("relation_name", "")),
        "current_industry_valid_from": str((current_industry_row or industry_row).get("valid_from", "")),
        "current_industry_valid_to": str((current_industry_row or industry_row).get("valid_to", "")),
        "event_day_summary": _event_day_summary(row),
        "prev_close": round(prev_close, 4),
        "prior_6d_high": round(prior_6d_high, 4),
        "prior_6d_low": round(prior_6d_low, 4),
        "avg_prev4_close": round(avg_prev4_close, 4),
        "limit_up_price": round(limit_up_price, 4),
        "limit_down_price": round(limit_down_price, 4),
        "runup_pct": round(runup_pct, 2),
        "prior_peak_vs_recent_avg_pct": round(prior_peak_vs_recent_avg_pct, 2),
        "close_return_pct": round(close_return_pct, 2),
        "gap_to_up_limit_pct": round(gap_to_up_limit_pct, 2),
        "gap_to_down_limit_pct": round(gap_to_down_limit_pct, 2),
        "nearest_limit_side": nearest_limit_side,
        "nearest_limit_gap_pct": round(nearest_limit_gap_pct, 2),
        "proximity_bucket": "at_limit_candidate" if nearest_limit_gap_pct <= 0.05 else "near_limit_candidate",
        "formal_review_bucket": "post_label_rescreen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "formal_front_filter_status": "snapshot_pending",
        "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
        "snapshot_stub": snapshot_stub,
        "suggested_snapshot_file": _suggested_snapshot_file(snapshot_stub),
        "ashare_sample_id_suggestion": _ashare_sample_id_suggestion(ts_code, window_start, window_end),
        "research_boundary_warning": [
            "post_label_rescreen_is_not_formal_front_filter_ready",
            "do_not_upgrade_without_ready_malf_snapshot",
            "do_not_generate_trade_from_research_prep",
        ],
        "next_action": "action:review_intraday_price_limit_reopen",
        "post_label_window_row_index": rows_by_date.get(trade_date),
    }


def _duckdb_post_label_candidate_report(
    row: dict[str, Any],
    industry_index: dict[str, list[dict[str, str | None]]],
    window_start: str,
    window_end: str,
    generated_at: str,
) -> dict[str, Any]:
    ts_code = str(row.get("ts_code", ""))
    trade_date = str(row.get("trade_date", ""))
    industry_rows = industry_index.get(ts_code, [])
    industry_row = _select_industry_row(industry_rows, window_start, window_end) or {}
    current_industry_row = _select_current_industry_row(industry_rows) or industry_row
    entry = {
        "ts_code": ts_code,
        "trade_date": trade_date,
        "sample_window_start": window_start,
        "sample_window_end": window_end,
        "research_priority_group": "core",
        "formal_review_bucket": "post_label_rescreen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "selection_reason": "Post-industry-effective-window add_on / price_limit research candidate.",
        "evidence_ref": "duckdb_market_base_day:post_industry_effective_window_rescreen_v0.1",
    }
    daily_like_row = {
        "trade_date": trade_date,
        "open": row.get("open"),
        "high": row.get("high"),
        "low": row.get("low"),
        "close": row.get("close"),
        "volume": None,
        "amount": None,
    }
    snapshot_stub = _apply_manual_malf_fill_contract(
        _research_snapshot_stub(ts_code, [daily_like_row], entry, generated_at),
        entry,
    )
    return {
        "ts_code": ts_code,
        "symbol_name": str(row.get("symbol_name") or "UNKNOWN"),
        "trade_date": trade_date,
        "sample_window_start": window_start,
        "sample_window_end": window_end,
        "industry_window_status": str(row.get("industry_window_status", "overlapping")),
        "current_industry_code": str(current_industry_row.get("relation_code", "")),
        "current_industry_name": str(current_industry_row.get("relation_name", "")),
        "current_industry_valid_from": str(current_industry_row.get("valid_from", "")),
        "current_industry_valid_to": str(current_industry_row.get("valid_to", "")),
        "event_day_summary": _event_day_summary(daily_like_row),
        "prev_close": row.get("prev_close"),
        "prior_6d_high": row.get("prior_6d_high"),
        "prior_6d_low": row.get("prior_6d_low"),
        "avg_prev4_close": row.get("avg_prev4_close"),
        "limit_up_price": row.get("limit_up_price"),
        "limit_down_price": row.get("limit_down_price"),
        "runup_pct": row.get("runup_pct"),
        "prior_peak_vs_recent_avg_pct": row.get("prior_peak_vs_recent_avg_pct"),
        "close_return_pct": row.get("close_return_pct"),
        "gap_to_up_limit_pct": row.get("gap_to_up_limit_pct"),
        "gap_to_down_limit_pct": row.get("gap_to_down_limit_pct"),
        "nearest_limit_side": row.get("nearest_limit_side"),
        "nearest_limit_gap_pct": row.get("nearest_limit_gap_pct"),
        "proximity_bucket": row.get("proximity_bucket"),
        "formal_review_bucket": "post_label_rescreen",
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "formal_front_filter_status": "snapshot_pending",
        "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
        "snapshot_stub": snapshot_stub,
        "suggested_snapshot_file": _suggested_snapshot_file(snapshot_stub),
        "ashare_sample_id_suggestion": _ashare_sample_id_suggestion(ts_code, window_start, window_end),
        "research_boundary_warning": [
            "post_label_rescreen_is_not_formal_front_filter_ready",
            "do_not_upgrade_without_ready_malf_snapshot",
            "do_not_generate_trade_from_research_prep",
        ],
        "next_action": "action:review_intraday_price_limit_reopen",
        "post_label_window_row_index": None,
    }


def _attach_post_label_intraday_reopen_review(tdx_root: Path, candidate: dict[str, Any]) -> dict[str, Any]:
    ts_code = str(candidate.get("ts_code", ""))
    trade_date = str(candidate.get("trade_date", ""))
    report = read_intraday_range(tdx_root, ts_code, trade_date)
    enriched = dict(candidate)
    enriched["intraday_review_result"] = report.get("result")
    enriched["intraday_review_reason"] = report.get("reason")

    intraday_range = report.get("intraday_range")
    if not isinstance(intraday_range, dict):
        enriched.update(
            {
                "intraday_bar_count": None,
                "intraday_open": None,
                "intraday_high": None,
                "intraday_low": None,
                "intraday_close": None,
                "intraday_nearest_limit_side": None,
                "intraday_nearest_limit_gap_pct": None,
                "intraday_close_gap_pct": None,
                "intraday_limit_reopen_status": "intraday_optional_evidence_missing",
                "intraday_source_ref": None,
                "daily_level_malf_review_status": "pending",
                "formal_front_filter_status": "snapshot_pending",
                "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
                "research_boundary_warning": _intraday_review_boundary_warning(
                    candidate,
                    blocked=True,
                    intraday_optional_missing=True,
                ),
                "next_action": "action:review_daily_level_malf_structure",
            }
        )
        return enriched

    limit_up_price = _to_float(candidate.get("limit_up_price"))
    limit_down_price = _to_float(candidate.get("limit_down_price"))
    intraday_high = _to_float(intraday_range.get("intraday_high"))
    intraday_low = _to_float(intraday_range.get("intraday_low"))
    intraday_close = _to_float(intraday_range.get("intraday_close"))
    if (
        limit_up_price is None
        or limit_down_price is None
        or intraday_high is None
        or intraday_low is None
        or intraday_close is None
        or limit_up_price == 0
        or limit_down_price == 0
    ):
        enriched.update(
            {
                "intraday_limit_reopen_status": None,
                "intraday_review_reason": "intraday_or_limit_price_invalid",
                "research_boundary_warning": _intraday_review_boundary_warning(candidate, blocked=True),
                "next_action": "action:repair_intraday_price_limit_review_input",
            }
        )
        return enriched

    gap_to_up_limit_pct = abs(intraday_high - limit_up_price) / limit_up_price * 100.0
    gap_to_down_limit_pct = abs(intraday_low - limit_down_price) / limit_down_price * 100.0
    intraday_nearest_limit_side = "up_limit_side" if gap_to_up_limit_pct <= gap_to_down_limit_pct else "down_limit_side"
    intraday_nearest_limit_gap_pct = min(gap_to_up_limit_pct, gap_to_down_limit_pct)
    if intraday_nearest_limit_side == "up_limit_side":
        intraday_close_gap_pct = abs(intraday_close - limit_up_price) / limit_up_price * 100.0
    else:
        intraday_close_gap_pct = abs(intraday_close - limit_down_price) / limit_down_price * 100.0

    touched_limit = intraday_nearest_limit_gap_pct <= 0.05
    if touched_limit and intraday_close_gap_pct > 0.05:
        intraday_limit_reopen_status = "reopened_after_limit_touch"
    elif touched_limit:
        intraday_limit_reopen_status = "closed_at_limit_after_touch"
    else:
        intraday_limit_reopen_status = "near_limit_without_touch"

    enriched.update(
        {
            "intraday_bar_count": int(intraday_range["bar_count"]),
            "intraday_open": round(float(intraday_range["intraday_open"]), 4),
            "intraday_high": round(intraday_high, 4),
            "intraday_low": round(intraday_low, 4),
            "intraday_close": round(intraday_close, 4),
            "intraday_nearest_limit_side": intraday_nearest_limit_side,
            "intraday_nearest_limit_gap_pct": round(intraday_nearest_limit_gap_pct, 2),
            "intraday_close_gap_pct": round(intraday_close_gap_pct, 2),
            "intraday_limit_reopen_status": intraday_limit_reopen_status,
            "intraday_source_ref": intraday_range.get("source_ref"),
            "daily_level_malf_review_status": "pending",
            "formal_front_filter_status": "snapshot_pending",
            "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
            "research_boundary_warning": _intraday_review_boundary_warning(candidate, blocked=False),
            "next_action": "action:review_malf_structure_evidence",
        }
    )
    return enriched


def _attach_post_label_daily_malf_structure_review(candidate: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(candidate)
    runup_pct = _to_float(candidate.get("runup_pct"))
    close_return_pct = _to_float(candidate.get("close_return_pct"))
    nearest_limit_gap_pct = _to_float(candidate.get("nearest_limit_gap_pct"))

    if runup_pct is None or close_return_pct is None or nearest_limit_gap_pct is None:
        status = "manual_review_required"
        hint = "structure_unclear"
        reason = "missing_daily_level_malf_metrics"
        next_action = "action:hold_for_daily_level_malf_evidence"
    elif runup_pct >= 12.0 and close_return_pct <= -2.0 and nearest_limit_gap_pct <= 3.0:
        status = "pass"
        hint = "pullback_pressure_adjustment"
        reason = "daily_pullback_pressure_adjustment_candidate"
        next_action = "action:prepare_malf_snapshot_draft_review"
    else:
        status = "blocked"
        hint = "not_applicable"
        reason = "daily_structure_threshold_not_met"
        next_action = "action:hold_for_daily_level_malf_evidence"

    enriched.update(
        {
            "daily_level_malf_review_status": status,
            "daily_level_malf_structure_hint": hint,
            "daily_level_malf_review_reason": reason,
            "formal_front_filter_status": "snapshot_pending",
            "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
            "research_boundary_warning": _daily_level_malf_review_boundary_warning(candidate),
            "next_action": next_action,
        }
    )
    return enriched


def _attach_malf_snapshot_draft_review(candidate: dict[str, Any], generated_at: str) -> dict[str, Any]:
    enriched = dict(candidate)
    daily_status = str(candidate.get("daily_level_malf_review_status", ""))
    snapshot_stub = candidate.get("snapshot_stub")

    if daily_status != "pass":
        enriched.update(
            {
                "snapshot_draft_review_status": "hold",
                "snapshot_draft_review_reason": "daily_level_malf_review_not_pass",
                "suggested_snapshot_draft": None,
                "formal_front_filter_status": "snapshot_pending",
                "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
                "research_boundary_warning": _snapshot_draft_review_boundary_warning(candidate),
                "next_action": "action:hold_for_daily_level_malf_evidence",
            }
        )
        return enriched

    if not isinstance(snapshot_stub, dict):
        enriched.update(
            {
                "snapshot_draft_review_status": "hold",
                "snapshot_draft_review_reason": "snapshot_stub_missing",
                "suggested_snapshot_draft": None,
                "formal_front_filter_status": "snapshot_pending",
                "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
                "research_boundary_warning": _snapshot_draft_review_boundary_warning(candidate),
                "next_action": "action:hold_for_malf_snapshot_draft_inputs",
            }
        )
        return enriched

    entry = {
        "core_snapshot_focus": "pressure_adjust_reopen_core",
        "evidence_ref": candidate.get("evidence_ref", snapshot_stub.get("evidence_ref", "")),
    }
    draft_stub = dict(snapshot_stub)
    draft_stub["generated_at"] = generated_at
    suggested_snapshot_draft = _research_snapshot_draft(draft_stub, entry)
    enriched.update(
        {
            "snapshot_draft_review_status": "ready_for_manual_review",
            "snapshot_draft_review_reason": "daily_level_malf_structure_passed",
            "suggested_snapshot_draft": suggested_snapshot_draft,
            "formal_front_filter_status": "snapshot_pending",
            "formal_front_filter_issue": "pipeline_requires_ready_malf_snapshot",
            "research_boundary_warning": _snapshot_draft_review_boundary_warning(candidate),
            "next_action": "action:manual_review_malf_snapshot_draft",
        }
    )
    return enriched


def _attach_malf_snapshot_manual_verdict(
    candidate: dict[str, Any],
    verdict: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    enriched = dict(candidate)
    if candidate.get("snapshot_draft_review_status") != "ready_for_manual_review":
        status = "needs_manual_review"
        reason = "snapshot_draft_not_ready_for_manual_review"
        reviewed_snapshot = None
        next_action = "action:hold_for_malf_snapshot_draft_inputs"
    elif not isinstance(verdict, dict):
        status = "needs_manual_review"
        reason = "manual_review_verdict_missing"
        reviewed_snapshot = None
        next_action = "action:manual_review_malf_snapshot_draft"
    else:
        manual_verdict = str(verdict.get("manual_review_verdict", ""))
        if manual_verdict == "approved_for_formal_front_filter_review":
            status = "reviewed_ready_candidate"
            reason = "manual_review_approved_for_formal_front_filter_review"
            reviewed_snapshot = _reviewed_snapshot_candidate(candidate, verdict, generated_at)
            next_action = "action:prepare_formal_front_filter_review_package"
        elif manual_verdict == "rejected":
            status = "rejected"
            reason = "manual_review_rejected"
            reviewed_snapshot = None
            next_action = "action:hold_for_manual_malf_snapshot_review"
        elif manual_verdict == "needs_revision":
            status = "needs_revision"
            reason = "manual_review_needs_revision"
            reviewed_snapshot = None
            next_action = "action:revise_malf_snapshot_draft"
        else:
            status = "needs_manual_review"
            reason = "manual_review_verdict_invalid"
            reviewed_snapshot = None
            next_action = "action:manual_review_malf_snapshot_draft"

    enriched.update(
        {
            "manual_review_status": status,
            "manual_review_reason": reason,
            "manual_review_verdict": verdict.get("manual_review_verdict") if isinstance(verdict, dict) else None,
            "manual_review_note": verdict.get("reviewer_note") if isinstance(verdict, dict) else None,
            "reviewed_snapshot_candidate": reviewed_snapshot,
            "formal_front_filter_status": "snapshot_pending",
            "formal_front_filter_issue": "pipeline_requires_formal_front_filter_review_package",
            "research_boundary_warning": _manual_snapshot_review_boundary_warning(candidate),
            "next_action": next_action,
        }
    )
    return enriched


def _formal_front_filter_review_input(candidate: dict[str, Any]) -> dict[str, Any] | None:
    if candidate.get("manual_review_status") != "reviewed_ready_candidate":
        return None
    reviewed_snapshot = candidate.get("reviewed_snapshot_candidate")
    if not isinstance(reviewed_snapshot, dict):
        return None

    expected_rule_id = str(
        reviewed_snapshot.get("draft_front_filter_expected_rule_id")
        or candidate.get("draft_front_filter_expected_rule_id")
        or "Q-PRESSURE-ADJUST"
    )
    ts_code = str(reviewed_snapshot.get("ts_code") or candidate.get("ts_code", ""))
    window_start = str(reviewed_snapshot.get("window_start") or candidate.get("sample_window_start", ""))
    window_end = str(reviewed_snapshot.get("window_end") or candidate.get("sample_window_end", ""))
    snapshot_ref = str(reviewed_snapshot.get("malf_snapshot_ref", ""))
    return _strip_forbidden_fields(
        {
            "ts_code": ts_code,
            "trade_date": candidate.get("trade_date"),
            "window_start": window_start,
            "window_end": window_end,
            "malf_snapshot_ref": snapshot_ref,
            "snapshot_quality_status": reviewed_snapshot.get("snapshot_quality_status"),
            "malf_background": reviewed_snapshot.get("malf_background"),
            "wave_range_break_fields": reviewed_snapshot.get("wave_range_break_fields"),
            "expected_front_filter_rule_id": expected_rule_id,
            "reviewed_snapshot_candidate": reviewed_snapshot,
            "review_command_preview": (
                "$env:PYTHONPATH='src'; python -m tachibana_front_filter "
                f"--snapshot <review-package>\\{ts_code}-{window_start[0:7]}.json"
            ),
            "front_filter_execution_allowed": False,
            "boundary_warning": [
                "front_filter_review_package_is_not_execution",
                "do_not_run_front_filter_without_explicit_audit_step",
                "do_not_generate_trade_from_front_filter_review_package",
            ],
            "next_action": "action:run_formal_front_filter_audit_when_explicitly_requested",
        }
    )


def _formal_front_filter_audit_snapshot(review_input: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    reviewed_snapshot = review_input.get("reviewed_snapshot_candidate")
    if isinstance(reviewed_snapshot, dict):
        snapshot = dict(reviewed_snapshot)
    else:
        snapshot = {
            "malf_snapshot_ref": review_input.get("malf_snapshot_ref"),
            "ts_code": review_input.get("ts_code"),
            "window_start": review_input.get("window_start"),
            "window_end": review_input.get("window_end"),
            "malf_background": review_input.get("malf_background"),
            "wave_range_break_fields": review_input.get("wave_range_break_fields"),
        }

    for key in [
        "malf_snapshot_ref",
        "ts_code",
        "window_start",
        "window_end",
        "malf_background",
        "wave_range_break_fields",
    ]:
        if snapshot.get(key) in (None, "") and review_input.get(key) not in (None, ""):
            snapshot[key] = review_input.get(key)

    issues: list[str] = []
    for key in ["ts_code", "window_start", "window_end", "malf_background"]:
        if not snapshot.get(key):
            issues.append(f"audit_snapshot_missing_{key}")
    if not isinstance(snapshot.get("wave_range_break_fields"), dict):
        issues.append("audit_snapshot_missing_wave_range_break_fields")

    source_quality = snapshot.get("snapshot_quality_status") or review_input.get("snapshot_quality_status")
    if source_quality != "reviewed_ready_candidate":
        issues.append(f"source_snapshot_quality_not_reviewed_ready_candidate:{source_quality}")

    snapshot["snapshot_quality_status"] = "ready"
    snapshot["audit_source_snapshot_quality_status"] = source_quality
    snapshot["audit_only"] = True
    snapshot["audit_boundary_warning"] = [
        "temporary_ready_snapshot_used_for_audit_only",
        "reviewed_ready_candidate_not_promoted_in_source_package",
        "do_not_generate_trade_from_formal_front_filter_audit",
    ]
    return snapshot, issues


def _formal_front_filter_audit_result(
    review_input: dict[str, Any],
    audit_snapshot: dict[str, Any],
    front_filter_report: dict[str, Any],
) -> dict[str, Any]:
    expected_rule_id = review_input.get("expected_front_filter_rule_id")
    actual_rule_id = front_filter_report.get("qualification_rule_id")
    audit_issues: list[str] = []
    if front_filter_report.get("front_filter_result") != "pass":
        audit_issues.append(f"front_filter_result_not_pass:{front_filter_report.get('front_filter_result')}")
    if expected_rule_id and actual_rule_id != expected_rule_id:
        audit_issues.append(f"front_filter_rule_mismatch:expected={expected_rule_id}:actual={actual_rule_id}")

    boundary_warning = list(front_filter_report.get("boundary_warning", []))
    for item in [
        "temporary_ready_snapshot_used_for_audit_only",
        "formal_front_filter_audit_is_not_trade_signal",
        "formal_front_filter_audit_does_not_open_backtest",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "ts_code": review_input.get("ts_code") or audit_snapshot.get("ts_code"),
            "symbol_name": review_input.get("symbol_name"),
            "ashare_sample_id": review_input.get("ashare_sample_id"),
            "ashare_sample_id_suggestion": review_input.get("ashare_sample_id_suggestion"),
            "trade_date": review_input.get("trade_date"),
            "window_start": audit_snapshot.get("window_start"),
            "window_end": audit_snapshot.get("window_end"),
            "malf_snapshot_ref": audit_snapshot.get("malf_snapshot_ref"),
            "malf_background": audit_snapshot.get("malf_background"),
            "formal_front_filter_audit_status": "pass" if not audit_issues else "blocked",
            "audit_issues": audit_issues,
            "front_filter_result": front_filter_report.get("front_filter_result"),
            "qualification_rule_id": actual_rule_id,
            "expected_front_filter_rule_id": expected_rule_id,
            "rhythm_meaning": front_filter_report.get("rhythm_meaning"),
            "tachibana_applicability": front_filter_report.get("tachibana_applicability"),
            "pm_required": front_filter_report.get("pm_required"),
            "rule_match_reason": front_filter_report.get("rule_match_reason", []),
            "applicability_reason": front_filter_report.get("applicability_reason", []),
            "audit_snapshot_quality_status": audit_snapshot.get("snapshot_quality_status"),
            "source_snapshot_quality_status": audit_snapshot.get("audit_source_snapshot_quality_status"),
            "boundary_warning": boundary_warning,
            "front_filter_execution_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": (
                "action:prepare_qualification_record_draft_review_when_explicitly_requested"
                if not audit_issues
                else "action:repair_formal_front_filter_review_input"
            ),
        }
    )


def _blocked_formal_front_filter_audit_result(
    review_input: dict[str, Any],
    audit_issues: list[str],
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "ts_code": review_input.get("ts_code"),
            "trade_date": review_input.get("trade_date"),
            "window_start": review_input.get("window_start"),
            "window_end": review_input.get("window_end"),
            "formal_front_filter_audit_status": "blocked",
            "audit_issues": audit_issues,
            "front_filter_execution_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:repair_formal_front_filter_review_input",
        }
    )


def _qualification_record_draft_front_filter_report(audit_result: dict[str, Any]) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "malf_snapshot_ref": audit_result.get("malf_snapshot_ref"),
            "ts_code": audit_result.get("ts_code"),
            "window_start": audit_result.get("window_start"),
            "window_end": audit_result.get("window_end"),
            "malf_background": audit_result.get("malf_background", "pullback"),
            "snapshot_quality_status": audit_result.get("audit_snapshot_quality_status", "ready"),
            "front_filter_result": audit_result.get("front_filter_result"),
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": audit_result.get("rhythm_meaning", "unknown"),
            "tachibana_applicability": audit_result.get("tachibana_applicability", "unknown"),
            "qualification_rule_id": audit_result.get("qualification_rule_id"),
            "pm_required": audit_result.get("pm_required", False),
            "rule_match_reason": audit_result.get("rule_match_reason", []),
            "applicability_reason": audit_result.get("applicability_reason", []),
            "boundary_warning": audit_result.get("boundary_warning", []),
            "next_action": "action:fill_qualification_record",
        }
    )


def _qualification_record_draft_review_input(
    audit_result: dict[str, Any],
    draft: dict[str, Any],
) -> dict[str, Any]:
    boundary_warning = list(draft.get("boundary_warning", []))
    for item in [
        "qualification_record_draft_review_is_not_formal_record",
        "manual_review_required_before_writing_qualification_record",
        "do_not_open_trade_or_backtest_from_qualification_draft",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "qualification_record_draft_review_status": "ready_for_manual_review",
            "qualification_record_draft_review_reason": "formal_front_filter_audit_passed",
            "qualification_record_id": draft.get("qualification_record_id"),
            "ashare_sample_id": draft.get("ashare_sample_id"),
            "ts_code": draft.get("ts_code"),
            "symbol_name": draft.get("symbol_name"),
            "sample_window_start": draft.get("sample_window_start"),
            "sample_window_end": draft.get("sample_window_end"),
            "malf_snapshot_ref": draft.get("malf_snapshot_ref"),
            "qualification_rule_id": draft.get("qualification_rule_id"),
            "rhythm_meaning": draft.get("rhythm_meaning"),
            "tachibana_applicability": draft.get("tachibana_applicability"),
            "pm_required": draft.get("pm_required"),
            "source_record_status": draft.get("record_status"),
            "source_front_filter_audit_status": audit_result.get("formal_front_filter_audit_status"),
            "source_front_filter_result": audit_result.get("front_filter_result"),
            "source_audit_issues": audit_result.get("audit_issues", []),
            "record_consistency": draft.get("record_consistency"),
            "rhythm_sample_row_gate": _closed_review_only_gate(
                draft.get("rhythm_sample_row_gate"),
                "rhythm_sample_row_not_writable_from_qualification_draft_review",
            ),
            "candidate_table_gate": _closed_review_only_gate(
                draft.get("candidate_table_gate"),
                "candidate_table_update_requires_post_review_approval",
            ),
            "method_pm_bridge_gate": draft.get("method_pm_bridge_gate"),
            "interface_boundary_gate": draft.get("interface_boundary_gate"),
            "backtest_input_gate": _closed_review_only_gate(
                draft.get("backtest_input_gate"),
                "backtest_input_not_allowed_from_qualification_draft_review",
            ),
            "cognitive_pipeline_gate": draft.get("cognitive_pipeline_gate"),
            "front_filter_system_audit": draft.get("front_filter_system_audit"),
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:manual_review_qualification_record_draft",
        }
    )


def _closed_review_only_gate(gate: Any, issue: str) -> dict[str, Any]:
    if not isinstance(gate, dict):
        return {"result": "blocked", "issues": [issue], "next_action": "action:manual_review_qualification_record_draft"}
    closed = dict(gate)
    issues = list(closed.get("issues", []))
    if issue not in issues:
        issues.append(issue)
    closed["result"] = "blocked"
    closed["issues"] = issues
    closed["next_action"] = "action:manual_review_qualification_record_draft"
    return closed


def _held_qualification_record_draft_review_result(
    audit_result: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "ts_code": audit_result.get("ts_code"),
            "trade_date": audit_result.get("trade_date"),
            "qualification_rule_id": audit_result.get("qualification_rule_id"),
            "formal_front_filter_audit_status": audit_result.get("formal_front_filter_audit_status"),
            "qualification_record_draft_review_status": "hold",
            "qualification_record_draft_review_reason": reason,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_formal_front_filter_audit_passes",
        }
    )


def _fallback_ashare_sample_id(audit_result: dict[str, Any]) -> str:
    ts_code = str(audit_result.get("ts_code") or "UNKNOWN")
    window_end = str(audit_result.get("window_end") or audit_result.get("trade_date") or "UNKNOWN")
    return f"ASHARE-QUAL-DRAFT-{ts_code}-{window_end}"


def _attach_qualification_record_draft_manual_verdict(
    draft_input: dict[str, Any],
    verdict: dict[str, Any] | None,
    generated_at: str,
) -> dict[str, Any]:
    if draft_input.get("qualification_record_draft_review_status") != "ready_for_manual_review":
        status = "hold"
        reason = "qualification_record_draft_not_ready_for_manual_review"
        next_action = "action:hold_for_manual_qualification_record_draft_review"
    elif not isinstance(verdict, dict):
        status = "needs_manual_review"
        reason = "manual_review_verdict_missing"
        next_action = "action:hold_for_manual_qualification_record_draft_review"
    else:
        manual_verdict = str(verdict.get("manual_review_verdict", ""))
        if manual_verdict == "approved_for_formal_record_write_audit":
            status = "approved_for_formal_record_write_audit_candidate"
            reason = "manual_review_approved_for_formal_record_write_audit"
            next_action = "action:prepare_formal_qualification_record_write_audit_when_explicitly_requested"
        elif manual_verdict == "rejected":
            status = "rejected"
            reason = "manual_review_rejected"
            next_action = "action:hold_for_manual_qualification_record_draft_review"
        elif manual_verdict == "needs_revision":
            status = "needs_revision"
            reason = "manual_review_needs_revision"
            next_action = "action:hold_for_manual_qualification_record_draft_review"
        else:
            status = "needs_manual_review"
            reason = "manual_review_verdict_invalid"
            next_action = "action:hold_for_manual_qualification_record_draft_review"

    boundary_warning = list(draft_input.get("boundary_warning", []))
    for item in [
        "manual_verdict_is_not_qualification_record_write",
        "formal_write_audit_required_before_record_write",
        "do_not_update_candidate_table_from_manual_qualification_verdict",
        "do_not_generate_trade_from_manual_qualification_verdict",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            **draft_input,
            "qualification_record_manual_review_status": status,
            "qualification_record_manual_review_reason": reason,
            "manual_review_verdict": verdict.get("manual_review_verdict") if isinstance(verdict, dict) else None,
            "manual_review_note": verdict.get("reviewer_note") if isinstance(verdict, dict) else None,
            "manual_reviewed_at": generated_at,
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": next_action,
        }
    )


def _formal_qualification_record_write_audit_candidate(
    manual_result: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    boundary_warning = list(manual_result.get("boundary_warning", []))
    for item in [
        "write_audit_is_not_record_write",
        "explicit_commit_layer_required_before_formal_record_write",
        "do_not_update_candidate_table_from_write_audit",
        "do_not_open_trading_layer_read_from_write_audit",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            **manual_result,
            "formal_record_write_audit_status": "pass",
            "formal_record_write_audit_reason": "manual_review_approved_and_boundary_gates_closed",
            "source_manual_review_status": manual_result.get("qualification_record_manual_review_status"),
            "formal_record_write_audited_at": generated_at,
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:prepare_formal_qualification_record_persistence_package_when_explicitly_requested",
        }
    )


def _held_formal_qualification_record_write_audit_result(
    manual_result: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "qualification_record_id": manual_result.get("qualification_record_id"),
            "ts_code": manual_result.get("ts_code"),
            "trade_date": manual_result.get("trade_date"),
            "qualification_rule_id": manual_result.get("qualification_rule_id"),
            "qualification_record_manual_review_status": manual_result.get("qualification_record_manual_review_status"),
            "formal_record_write_audit_status": "hold",
            "formal_record_write_audit_reason": reason,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_formal_qualification_record_write_audit_candidate",
        }
    )


def _formal_qualification_record_persistence_package(
    audit_candidate: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    boundary_warning = list(audit_candidate.get("boundary_warning", []))
    for item in [
        "persistence_package_is_not_record_write",
        "explicit_persistence_writer_required_before_record_write",
        "persistence_package_does_not_update_candidate_table",
        "persistence_package_does_not_open_trading_layer",
        "candidate_table_update_requires_separate_audit",
        "trading_layer_read_requires_separate_gate",
    ]:
        if item not in boundary_warning:
            boundary_warning.append(item)

    return _strip_forbidden_fields(
        {
            "qualification_record_status": "formal_record_ready_for_persistence",
            "qualification_record_id": audit_candidate.get("qualification_record_id"),
            "ashare_sample_id": audit_candidate.get("ashare_sample_id"),
            "ts_code": audit_candidate.get("ts_code"),
            "symbol_name": audit_candidate.get("symbol_name"),
            "sample_window_start": audit_candidate.get("sample_window_start"),
            "sample_window_end": audit_candidate.get("sample_window_end"),
            "qualification_rule_id": audit_candidate.get("qualification_rule_id"),
            "rhythm_meaning": audit_candidate.get("rhythm_meaning"),
            "tachibana_applicability": audit_candidate.get("tachibana_applicability"),
            "source_manual_review_verdict": audit_candidate.get("manual_review_verdict"),
            "source_formal_record_write_audit_status": audit_candidate.get("formal_record_write_audit_status"),
            "source_formal_record_write_audit_reason": audit_candidate.get("formal_record_write_audit_reason"),
            "persistence_package_prepared_at": generated_at,
            "qualification_record_persistence_performed": False,
            "boundary_warning": boundary_warning,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:prepare_candidate_table_update_audit_when_explicitly_requested",
        }
    )


def _held_formal_qualification_record_persistence_item(
    audit_candidate: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return _strip_forbidden_fields(
        {
            "qualification_record_id": audit_candidate.get("qualification_record_id"),
            "ts_code": audit_candidate.get("ts_code"),
            "qualification_rule_id": audit_candidate.get("qualification_rule_id"),
            "formal_record_write_audit_status": audit_candidate.get("formal_record_write_audit_status"),
            "qualification_record_persistence_status": "hold",
            "qualification_record_persistence_reason": reason,
            "qualification_record_persistence_performed": False,
            "qualification_record_write_allowed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "formal_data_write_allowed": False,
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:hold_for_formal_qualification_record_write_audit_pass",
        }
    )


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
