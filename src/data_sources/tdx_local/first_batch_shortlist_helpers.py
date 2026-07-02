from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from .first_batch_constants import *
from .first_batch_common import *
from .first_batch_formal_candidate_helpers import *

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


def _attach_post_label_intraday_reopen_review(
    tdx_root: Path,
    candidate: dict[str, Any],
    intraday_reader=read_intraday_range,
) -> dict[str, Any]:
    ts_code = str(candidate.get("ts_code", ""))
    trade_date = str(candidate.get("trade_date", ""))
    report = intraday_reader(tdx_root, ts_code, trade_date)
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


__all__ = [name for name in globals() if not name.startswith("__")]
