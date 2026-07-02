from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from .readers import _normalize_duckdb_symbol, read_intraday_range


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


def screen_pullback_add_price_limit_candidates(
    duckdb_root: str | Path,
    window_start: str,
    window_end: str,
    limit: int = 50,
    require_industry_window_overlap: bool = False,
) -> list[dict[str, Any]]:
    root = Path(duckdb_root)
    market_base_day_db = root / "market_base_day.duckdb"
    market_meta_db = root / "market_meta.duckdb"
    con = duckdb.connect()
    try:
        con.execute(f"ATTACH '{market_base_day_db.as_posix()}' AS market_base_day_db")
        con.execute(f"ATTACH '{market_meta_db.as_posix()}' AS market_meta_db")
        overlap_filter = "and industry_window_overlap" if require_industry_window_overlap else ""
        rows = con.execute(
            f"""
            with bars as (
                select
                    b.symbol,
                    b.trade_dt,
                    b.open,
                    b.high,
                    b.low,
                    b.close,
                    lag(b.close, 1) over (partition by b.symbol order by b.trade_dt) as prev_close,
                    max(b.high) over (
                        partition by b.symbol order by b.trade_dt
                        rows between 6 preceding and 1 preceding
                    ) as prior_6d_high,
                    min(b.low) over (
                        partition by b.symbol order by b.trade_dt
                        rows between 6 preceding and 1 preceding
                    ) as prior_6d_low,
                    avg(b.close) over (
                        partition by b.symbol order by b.trade_dt
                        rows between 4 preceding and 1 preceding
                    ) as avg_prev4_close
                from market_base_day_db.market_base_day.base_bar b
                where b.asset_type = 'stock'
                  and b.timeframe = 'day'
                  and b.trade_dt between date '{window_start}' - interval 8 day and date '{window_end}'
            ),
            joined as (
                select
                    bars.*,
                    i.exchange,
                    i.name,
                    i.list_dt,
                    exists (
                        select 1
                        from market_meta_db.market_meta.industry_block_relation rel
                        where rel.symbol = bars.symbol
                          and coalesce(rel.asset_type, 'stock') in ('stock', 'equity')
                          and rel.relation_type = 'industry'
                          and coalesce(rel.effective_from, date '1900-01-01') <= bars.trade_dt
                          and coalesce(rel.effective_to, date '2999-12-31') >= bars.trade_dt
                    ) as industry_window_overlap,
                    t.tradability_status,
                    case
                        when i.exchange = 'SZ' and starts_with(bars.symbol, 'sz30') then 0.20
                        when i.exchange = 'SH' and starts_with(bars.symbol, 'sh688') then 0.20
                        else 0.10
                    end as limit_pct
                from bars
                join market_meta_db.market_meta.instrument_master i
                  on bars.symbol = i.symbol
                 and coalesce(i.asset_type, 'stock') in ('stock', 'equity')
                join market_meta_db.market_meta.tradability_fact t
                  on bars.symbol = t.symbol
                 and bars.trade_dt = t.trade_dt
                 and coalesce(t.asset_type, 'stock') in ('stock', 'equity')
                where t.tradability_status = 'tradable'
                  and i.list_dt <= date '{window_start}' - interval 365 day
                  and i.name not like 'ST%'
                  and i.name not like '*ST%'
                  and i.name not like 'S*ST%'
                  and i.name not like 'PT%'
                  and i.name not like '%ETF%'
                  and i.name not like '%LOF%'
                  and i.name not like '%基金%'
                  and i.name not like '%退%'
            ),
            features as (
                select
                    symbol,
                    exchange,
                    name,
                    industry_window_overlap,
                    trade_dt,
                    open,
                    high,
                    low,
                    close,
                    prev_close,
                    prior_6d_high,
                    prior_6d_low,
                    avg_prev4_close,
                    round(prev_close * (1 + limit_pct), 4) as limit_up_price,
                    round(prev_close * (1 - limit_pct), 4) as limit_down_price,
                    (prior_6d_high / nullif(prior_6d_low, 0) - 1.0) as runup_pct,
                    (prior_6d_high / nullif(avg_prev4_close, 0) - 1.0) as prior_peak_vs_recent_avg_pct,
                    (close / nullif(prev_close, 0) - 1.0) as close_return_pct,
                    abs(high - round(prev_close * (1 + limit_pct), 4)) / nullif(round(prev_close * (1 + limit_pct), 4), 0) as gap_to_up_limit_pct,
                    abs(low - round(prev_close * (1 - limit_pct), 4)) / nullif(round(prev_close * (1 - limit_pct), 4), 0) as gap_to_down_limit_pct
                from joined
                where trade_dt between date '{window_start}' and date '{window_end}'
                  and prev_close is not null
                  and prior_6d_high is not null
                  and prior_6d_low is not null
                  and avg_prev4_close is not null
            ),
            ranked as (
                select
                    symbol,
                    exchange,
                    name,
                    industry_window_overlap,
                    trade_dt,
                    open,
                    high,
                    low,
                    close,
                    prev_close,
                    prior_6d_high,
                    prior_6d_low,
                    avg_prev4_close,
                    limit_up_price,
                    limit_down_price,
                    runup_pct,
                    prior_peak_vs_recent_avg_pct,
                    close_return_pct,
                    gap_to_up_limit_pct,
                    gap_to_down_limit_pct,
                    row_number() over (
                        partition by symbol
                        order by least(gap_to_up_limit_pct, gap_to_down_limit_pct) asc,
                                 runup_pct desc,
                                 abs(close_return_pct) desc,
                                 trade_dt asc
                    ) as candidate_rank
                from features
                where runup_pct >= 0.12
                  and prior_peak_vs_recent_avg_pct >= 0.04
                  and close_return_pct <= -0.02
                  and least(gap_to_up_limit_pct, gap_to_down_limit_pct) <= 0.03
            )
            select
                symbol,
                exchange,
                name,
                industry_window_overlap,
                trade_dt,
                open,
                high,
                low,
                close,
                prev_close,
                prior_6d_high,
                prior_6d_low,
                avg_prev4_close,
                limit_up_price,
                limit_down_price,
                runup_pct,
                prior_peak_vs_recent_avg_pct,
                close_return_pct,
                gap_to_up_limit_pct,
                gap_to_down_limit_pct
            from ranked
            where candidate_rank = 1
              {overlap_filter}
            order by least(gap_to_up_limit_pct, gap_to_down_limit_pct) asc,
                     runup_pct desc,
                     abs(close_return_pct) desc
            limit {int(limit)}
            """
        ).fetchall()
    finally:
        con.close()
    return [_normalize_candidate_row(row) for row in rows]


def screen_pullback_add_price_limit_candidates_with_intraday(
    duckdb_root: str | Path,
    tdx_root: str | Path,
    window_start: str,
    window_end: str,
    limit: int = 50,
    require_industry_window_overlap: bool = False,
) -> list[dict[str, Any]]:
    rows = screen_pullback_add_price_limit_candidates(
        duckdb_root=duckdb_root,
        window_start=window_start,
        window_end=window_end,
        limit=limit,
        require_industry_window_overlap=require_industry_window_overlap,
    )
    return [_attach_intraday_review_fields(Path(tdx_root), row) for row in rows]


def shortlist_pullback_add_pressure_adjust_candidates(
    rows: list[dict[str, Any]],
    limit: int = 10,
    max_close_drop_pct: float = 8.5,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for row in rows:
        if row.get("intraday_review_result") != "source_review_required":
            continue
        reopen_status = row.get("intraday_limit_reopen_status")
        if reopen_status not in {"reopened_after_limit_touch", "near_limit_without_touch"}:
            continue
        close_return_pct = row.get("close_return_pct")
        intraday_gap_pct = row.get("intraday_nearest_limit_gap_pct")
        if not isinstance(close_return_pct, (int, float)) or not isinstance(intraday_gap_pct, (int, float)):
            continue
        if abs(float(close_return_pct)) > max_close_drop_pct:
            continue
        enriched = dict(row)
        enriched["pressure_adjust_alignment"] = "higher_priority"
        selected.append(enriched)
    selected.sort(
        key=lambda item: (
            float(item["intraday_nearest_limit_gap_pct"]),
            abs(float(item["close_return_pct"])),
            -float(item["runup_pct"]),
            str(item["ts_code"]),
        )
    )
    for index, row in enumerate(selected[:limit], 1):
        row["pressure_adjust_priority_rank"] = index
    return selected[:limit]


def shortlist_formal_pressure_adjust_review_candidates(
    rows: list[dict[str, Any]],
    reopened_limit: int = 4,
    near_limit: int = 2,
    max_close_drop_pct: float = 8.5,
) -> list[dict[str, Any]]:
    reopened_rows = shortlist_pullback_add_pressure_adjust_candidates(
        rows,
        limit=reopened_limit,
        max_close_drop_pct=max_close_drop_pct,
    )
    formal_rows: list[dict[str, Any]] = []
    seen_ts_codes: set[str] = set()
    for row in reopened_rows:
        enriched = dict(row)
        enriched["formal_review_bucket"] = "pressure_adjust_reopen"
        formal_rows.append(enriched)
        seen_ts_codes.add(str(row["ts_code"]))

    near_rows: list[dict[str, Any]] = []
    for row in rows:
        if str(row.get("ts_code")) in seen_ts_codes:
            continue
        if row.get("intraday_review_result") != "source_review_required":
            continue
        if row.get("proximity_bucket") != "near_limit_candidate":
            continue
        if row.get("intraday_limit_reopen_status") != "near_limit_without_touch":
            continue
        close_return_pct = row.get("close_return_pct")
        intraday_gap_pct = row.get("intraday_nearest_limit_gap_pct")
        if not isinstance(close_return_pct, (int, float)) or not isinstance(intraday_gap_pct, (int, float)):
            continue
        if abs(float(close_return_pct)) > max_close_drop_pct:
            continue
        enriched = dict(row)
        enriched["formal_review_bucket"] = "near_limit_compare"
        near_rows.append(enriched)
    near_rows.sort(
        key=lambda item: (
            float(item["intraday_nearest_limit_gap_pct"]),
            abs(float(item["close_return_pct"])),
            -float(item["runup_pct"]),
            str(item["ts_code"]),
        )
    )
    formal_rows.extend(near_rows[:near_limit])
    for index, row in enumerate(formal_rows, 1):
        row["formal_review_priority_rank"] = index
    return formal_rows


def shortlist_core_malf_snapshot_candidates(
    rows: list[dict[str, Any]],
    limit: int = 4,
) -> list[dict[str, Any]]:
    formal_rows = sorted(
        rows,
        key=lambda item: int(item.get("formal_review_priority_rank", 9999)),
    )

    selected: list[dict[str, Any]] = []
    seen_ts_codes: set[str] = set()

    for row in formal_rows:
        if len(selected) >= limit:
            break
        if row.get("formal_review_bucket") != "pressure_adjust_reopen":
            continue
        ts_code = str(row.get("ts_code"))
        if ts_code in seen_ts_codes:
            continue
        enriched = dict(row)
        enriched["core_review_bucket"] = "malf_snapshot_priority"
        enriched["core_snapshot_focus"] = "pressure_adjust_reopen_core"
        selected.append(enriched)
        seen_ts_codes.add(ts_code)

    if len(selected) < limit:
        for row in formal_rows:
            if len(selected) >= limit:
                break
            if row.get("formal_review_bucket") != "near_limit_compare":
                continue
            ts_code = str(row.get("ts_code"))
            if ts_code in seen_ts_codes:
                continue
            enriched = dict(row)
            enriched["core_review_bucket"] = "malf_snapshot_priority"
            enriched["core_snapshot_focus"] = "near_limit_compare_backup"
            selected.append(enriched)
            seen_ts_codes.add(ts_code)

    for index, row in enumerate(selected, 1):
        row["core_review_priority_rank"] = index
    return selected


def _normalize_candidate_row(row: tuple[Any, ...]) -> dict[str, Any]:
    (
        symbol,
        exchange,
        name,
        industry_window_overlap,
        trade_dt,
        open_price,
        high_price,
        low_price,
        close_price,
        prev_close,
        prior_6d_high,
        prior_6d_low,
        avg_prev4_close,
        limit_up_price,
        limit_down_price,
        runup_pct,
        prior_peak_vs_recent_avg_pct,
        close_return_pct,
        gap_to_up_limit_pct,
        gap_to_down_limit_pct,
    ) = row
    ts_code, market = _normalize_duckdb_symbol(symbol, exchange)
    nearest_limit_side = "up_limit_side" if gap_to_up_limit_pct <= gap_to_down_limit_pct else "down_limit_side"
    nearest_limit_gap_pct = min(gap_to_up_limit_pct, gap_to_down_limit_pct) * 100.0
    proximity_bucket = "at_limit_candidate" if nearest_limit_gap_pct <= 0.05 else "near_limit_candidate"
    return _strip_forbidden_fields(
        {
            "ts_code": ts_code,
            "market": market,
            "symbol_name": str(name),
            "industry_window_overlap": bool(industry_window_overlap),
            "industry_window_status": "overlapping" if industry_window_overlap else "not_overlapping",
            "trade_date": str(trade_dt),
            "open": float(open_price),
            "high": float(high_price),
            "low": float(low_price),
            "close": float(close_price),
            "prev_close": float(prev_close),
            "prior_6d_high": float(prior_6d_high),
            "prior_6d_low": float(prior_6d_low),
            "avg_prev4_close": float(avg_prev4_close),
            "limit_up_price": float(limit_up_price),
            "limit_down_price": float(limit_down_price),
            "runup_pct": round(float(runup_pct) * 100.0, 2),
            "prior_peak_vs_recent_avg_pct": round(float(prior_peak_vs_recent_avg_pct) * 100.0, 2),
            "close_return_pct": round(float(close_return_pct) * 100.0, 2),
            "gap_to_up_limit_pct": round(float(gap_to_up_limit_pct) * 100.0, 2),
            "gap_to_down_limit_pct": round(float(gap_to_down_limit_pct) * 100.0, 2),
            "nearest_limit_gap_pct": round(nearest_limit_gap_pct, 2),
            "nearest_limit_side": nearest_limit_side,
            "proximity_bucket": proximity_bucket,
        }
    )


def _attach_intraday_review_fields(tdx_root: Path, row: dict[str, Any]) -> dict[str, Any]:
    report = read_intraday_range(tdx_root, str(row["ts_code"]), str(row["trade_date"]))
    enriched = dict(row)
    enriched["intraday_review_result"] = report.get("result")
    enriched["intraday_review_reason"] = report.get("reason")
    intraday_range = report.get("intraday_range")
    if not isinstance(intraday_range, dict):
        enriched["intraday_bar_count"] = None
        enriched["intraday_open"] = None
        enriched["intraday_high"] = None
        enriched["intraday_low"] = None
        enriched["intraday_close"] = None
        enriched["intraday_nearest_limit_side"] = None
        enriched["intraday_nearest_limit_gap_pct"] = None
        enriched["intraday_close_gap_pct"] = None
        enriched["intraday_limit_reopen_status"] = None
        enriched["intraday_source_ref"] = None
        return _strip_forbidden_fields(enriched)

    intraday_high = float(intraday_range["intraday_high"])
    intraday_low = float(intraday_range["intraday_low"])
    intraday_close = float(intraday_range["intraday_close"])
    limit_up_price = float(row["limit_up_price"])
    limit_down_price = float(row["limit_down_price"])

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

    enriched["intraday_bar_count"] = int(intraday_range["bar_count"])
    enriched["intraday_open"] = round(float(intraday_range["intraday_open"]), 4)
    enriched["intraday_high"] = round(intraday_high, 4)
    enriched["intraday_low"] = round(intraday_low, 4)
    enriched["intraday_close"] = round(intraday_close, 4)
    enriched["intraday_nearest_limit_side"] = intraday_nearest_limit_side
    enriched["intraday_nearest_limit_gap_pct"] = round(intraday_nearest_limit_gap_pct, 2)
    enriched["intraday_close_gap_pct"] = round(intraday_close_gap_pct, 2)
    enriched["intraday_limit_reopen_status"] = intraday_limit_reopen_status
    enriched["intraday_source_ref"] = intraday_range.get("source_ref")
    return _strip_forbidden_fields(enriched)


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
