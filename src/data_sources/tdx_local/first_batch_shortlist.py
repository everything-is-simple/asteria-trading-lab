from __future__ import annotations

from pathlib import Path
from typing import Any

from .readers import read_daily_bars, read_intraday_range, read_symbol_master
from .price_limit_sample_pool import screen_pullback_add_price_limit_candidates
from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_shortlist_helpers import *

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
        reviewed = _attach_post_label_intraday_reopen_review(Path(tdx_root), candidate, read_intraday_range)
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
