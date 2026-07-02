from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from .readers import read_daily_bars, read_symbol_master
from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_formal_candidate_helpers import *

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
