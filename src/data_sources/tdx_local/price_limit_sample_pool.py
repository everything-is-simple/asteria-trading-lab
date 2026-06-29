from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from .readers import _normalize_duckdb_symbol


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
