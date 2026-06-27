from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import duckdb

from .readers import _resolve_duckdb_table_ref


INSTITUTION_FACT_HEADER = [
    "ts_code",
    "trade_date",
    "is_trading_day",
    "is_suspended",
    "limit_up_price",
    "limit_down_price",
    "close_limit_status",
    "touched_limit_status",
    "board_lot_size",
    "source_ref",
]

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


def build_minimal_institution_fact_package(
    duckdb_root: str | Path,
    data_root: str | Path,
    ts_codes: list[str],
    window_start: str,
    window_end: str,
) -> dict[str, Any]:
    root = Path(data_root)
    output_dir = root / "ashare" / "institution-facts-v0.1"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_by_code = _read_tradability_rows(Path(duckdb_root), ts_codes, window_start, window_end)
    fact_files: list[str] = []
    fact_count = 0
    missing_codes: list[str] = []

    for ts_code in ts_codes:
        rows = rows_by_code.get(ts_code, [])
        if not rows:
            missing_codes.append(ts_code)
            continue
        path = output_dir / f"{ts_code}.csv"
        _write_csv(path, rows)
        fact_count += len(rows)
        fact_files.append(path.relative_to(root).as_posix())

    result = "pass" if fact_count > 0 and not missing_codes else "blocked"
    return _strip_forbidden_fields(
        {
            "result": result,
            "institution_fact_count": fact_count if result == "pass" else 0,
            "institution_fact_files": fact_files if result == "pass" else [],
            "missing_ts_codes": missing_codes,
            "source_ref": "market_meta.duckdb:market_meta.tradability_fact",
            "limit_price_policy": "minimal_power_on_unknown",
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:audit_institution_fact_package"
            if result == "pass"
            else "action:repair_institution_fact_package",
        }
    )


def _read_tradability_rows(
    duckdb_root: Path,
    ts_codes: list[str],
    window_start: str,
    window_end: str,
) -> dict[str, list[dict[str, str]]]:
    db_path = duckdb_root / "market_meta.duckdb"
    if not db_path.exists():
        return {}
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception:
        return {}
    table_ref = _resolve_duckdb_table_ref(con, "tradability_fact")
    if table_ref is None:
        con.close()
        return {}

    symbol_to_ts = {_ts_code_to_duckdb_symbol(ts_code): ts_code for ts_code in ts_codes}
    if not symbol_to_ts:
        con.close()
        return {}
    placeholders = ", ".join(["?"] * len(symbol_to_ts))
    rows = con.execute(
        f"""
        select symbol, trade_dt, tradability_status, blocked_reason, source_manifest_hash
        from {table_ref}
        where symbol in ({placeholders})
          and trade_dt between ? and ?
          and coalesce(asset_type, 'stock') in ('stock', 'equity')
        order by symbol, trade_dt
        """,
        [*symbol_to_ts.keys(), window_start, window_end],
    ).fetchall()
    con.close()

    grouped: dict[str, list[dict[str, str]]] = {ts_code: [] for ts_code in ts_codes}
    for symbol, trade_dt, tradability_status, blocked_reason, source_manifest_hash in rows:
        symbol_text = str(symbol)
        ts_code = symbol_to_ts.get(symbol_text)
        if ts_code is None:
            continue
        trade_date = str(trade_dt)
        grouped[ts_code].append(
            {
                "ts_code": ts_code,
                "trade_date": trade_date,
                "is_trading_day": "true",
                "is_suspended": "true" if _is_suspended(tradability_status, blocked_reason) else "false",
                "limit_up_price": "",
                "limit_down_price": "",
                "close_limit_status": "unknown",
                "touched_limit_status": "unknown",
                "board_lot_size": "100",
                "source_ref": (
                    "market_meta.duckdb:market_meta.tradability_fact:"
                    f"{symbol_text}:{trade_date}:{source_manifest_hash}"
                ),
            }
        )
    return grouped


def _ts_code_to_duckdb_symbol(ts_code: str) -> str:
    code, suffix = ts_code.split(".", 1)
    return f"{suffix.lower()}{code}"


def _is_suspended(tradability_status: Any, blocked_reason: Any) -> bool:
    status = str(tradability_status or "").lower()
    reason = str(blocked_reason or "").lower()
    return "suspend" in status or "suspend" in reason or "停牌" in reason


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INSTITUTION_FACT_HEADER)
        writer.writeheader()
        writer.writerows(rows)


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Build minimal A-share institution fact CSVs from local DuckDB.")
    parser.add_argument("--duckdb-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--ts-code", action="append", required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end", required=True)
    args = parser.parse_args()
    report = build_minimal_institution_fact_package(
        duckdb_root=args.duckdb_root,
        data_root=args.data_root,
        ts_codes=args.ts_code,
        window_start=args.window_start,
        window_end=args.window_end,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
