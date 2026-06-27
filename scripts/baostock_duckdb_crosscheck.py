"""Baostock vs DuckDB cross-source verification.

Read-only. Not part of the formal data chain. Used to validate that the local
DuckDB base_bar layer and Baostock free public source agree on OHLCV for a
given (ts_code, date range). Result is a verification report; this script never
writes the project data directory and never emits trade/signal/position fields.

Run::

    python scripts/baostock_duckdb_crosscheck.py \
        --ts-code 000001.SZ \
        --start 2026-01-05 --end 2026-01-23

See docs/data/本地数据资产接入审计-v0.1.md §3 for the audit conclusion.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import duckdb

FORBIDDEN_OUTPUT_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "position_size",
}


def _ts_code_to_baostock(ts_code: str) -> str:
    code, exch = ts_code.split(".")
    return f"{exch.lower()}.{code}"


def _ts_code_to_duckdb(ts_code: str) -> str:
    code, exch = ts_code.split(".")
    return f"{exch.lower()}{code}"


def _fetch_baostock(ts_code: str, start: str, end: str) -> list[dict]:
    import baostock as bs

    lg = bs.login()
    if lg.error_code != "0":
        raise RuntimeError(f"baostock login failed: {lg.error_msg}")
    try:
        rs = bs.query_history_k_data_plus(
            _ts_code_to_baostock(ts_code),
            "date,code,open,high,low,close,volume,amount,adjustflag",
            start_date=start,
            end_date=end,
            frequency="d",
            adjustflag="3",
        )
        rows = []
        while rs.next():
            d = dict(zip(
                ["date", "code", "open", "high", "low", "close",
                 "volume", "amount", "adjustflag"],
                rs.get_row_data(),
            ))
            rows.append(d)
        return rows
    finally:
        bs.logout()


def _fetch_duckdb(ts_code: str, start: str, end: str, db_path: Path) -> list[dict]:
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        rs = con.execute(
            """
            SELECT trade_dt, open, high, low, close, volume, amount,
                   analysis_price_line
            FROM market_base_day.market_base_day.base_bar
            WHERE symbol = ? AND trade_dt BETWEEN ? AND ?
            ORDER BY trade_dt
            """,
            [_ts_code_to_duckdb(ts_code), start, end],
        ).fetchall()
    finally:
        con.close()
    return [
        {
            "date": r[0].isoformat(),
            "open": r[1], "high": r[2], "low": r[3], "close": r[4],
            "volume": int(r[5]), "amount": float(r[6]),
            "analysis_price_line": r[7],
        }
        for r in rs
    ]


def _compare(bao: list[dict], duck: list[dict]) -> dict:
    report = {
        "row_count_baostock": len(bao),
        "row_count_duckdb": len(duck),
        "row_count_match": len(bao) == len(duck),
        "mismatches": [],
        "amount_max_relative_diff": 0.0,
    }
    by_date_b = {r["date"]: r for r in bao}
    by_date_d = {r["date"]: r for r in duck}
    for date in sorted(set(by_date_b) | set(by_date_d)):
        b = by_date_b.get(date)
        d = by_date_d.get(date)
        if b is None or d is None:
            report["mismatches"].append({"date": date, "issue": "missing_on_one_side"})
            continue
        for field in ("open", "high", "low", "close"):
            if math.isclose(float(b[field]), d[field], rel_tol=1e-6, abs_tol=1e-4):
                continue
            report["mismatches"].append({
                "date": date, "field": field,
                "baostock": b[field], "duckdb": d[field],
            })
        if int(b["volume"]) != d["volume"]:
            report["mismatches"].append({
                "date": date, "field": "volume",
                "baostock": b["volume"], "duckdb": d["volume"],
            })
        rel = abs(float(b["amount"]) - d["amount"]) / max(abs(d["amount"]), 1.0)
        report["amount_max_relative_diff"] = max(report["amount_max_relative_diff"], rel)
    return report


def _strip_forbidden(payload: dict) -> dict:
    leaked = FORBIDDEN_OUTPUT_FIELDS.intersection(payload.keys())
    if leaked:
        raise RuntimeError(f"forbidden fields leaked: {sorted(leaked)}")
    return payload


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ts-code", default="000001.SZ")
    p.add_argument("--start", default="2026-01-05")
    p.add_argument("--end", default="2026-01-23")
    p.add_argument("--duckdb",
                   default=r"Z:\malf-data\market_base_day.duckdb",
                   help="path to market_base_day.duckdb")
    args = p.parse_args(argv)

    bao = _fetch_baostock(args.ts_code, args.start, args.end)
    duck = _fetch_duckdb(args.ts_code, args.start, args.end, Path(args.duckdb))
    report = _compare(bao, duck)
    report["ts_code"] = args.ts_code
    report["start"] = args.start
    report["end"] = args.end
    report["verdict"] = (
        "match" if report["row_count_match"] and not report["mismatches"]
        and report["amount_max_relative_diff"] < 1e-5
        else "mismatch"
    )

    _strip_forbidden(report)

    print(f"verdict={report['verdict']}")
    print(f"rows: baostock={report['row_count_baostock']} duckdb={report['row_count_duckdb']}")
    print(f"amount_max_rel_diff={report['amount_max_relative_diff']:.2e}")
    if report["mismatches"]:
        print("mismatches:")
        for m in report["mismatches"][:10]:
            print(" ", m)
    return 0 if report["verdict"] == "match" else 1


if __name__ == "__main__":
    sys.exit(main())
