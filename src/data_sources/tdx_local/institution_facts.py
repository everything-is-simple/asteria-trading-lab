from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import tempfile
from typing import Any
from decimal import Decimal, ROUND_HALF_UP

import duckdb

from .readers import _normalize_duckdb_symbol, _resolve_duckdb_table_ref, read_daily_bars


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
    offline_root: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(data_root)
    output_dir = root / "ashare" / "institution-facts-v0.1"
    output_dir.mkdir(parents=True, exist_ok=True)

    rows_by_code = _read_tradability_rows(
        Path(duckdb_root),
        ts_codes,
        window_start,
        window_end,
        Path(offline_root) if offline_root is not None else None,
    )
    missing_codes: list[str] = []
    for ts_code in ts_codes:
        if not rows_by_code.get(ts_code, []):
            missing_codes.append(ts_code)

    if missing_codes:
        _remove_target_files(output_dir, ts_codes)
        return _strip_forbidden_fields(
            {
                "result": "blocked",
                "institution_fact_count": 0,
                "institution_fact_files": [],
                "missing_ts_codes": missing_codes,
                "source_ref": "market_meta.duckdb:market_meta.tradability_fact",
                "limit_price_policy": "derived_bounds_explicit_status_only",
                "institution_rule_definition_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
                "next_action": "action:repair_institution_fact_package",
            }
        )

    fact_files: list[str] = []
    fact_count = 0
    with tempfile.TemporaryDirectory(dir=output_dir) as tmp:
        staging_dir = Path(tmp)
        for ts_code in ts_codes:
            rows = rows_by_code[ts_code]
            path = staging_dir / f"{ts_code}.csv"
            _write_csv(path, rows)
            fact_count += len(rows)
            fact_files.append((output_dir / f"{ts_code}.csv").relative_to(root).as_posix())
        _replace_target_files(staging_dir, output_dir, ts_codes)

    return _strip_forbidden_fields(
        {
            "result": "pass",
            "institution_fact_count": fact_count,
            "institution_fact_files": fact_files,
            "missing_ts_codes": missing_codes,
            "source_ref": "market_meta.duckdb:market_meta.tradability_fact",
            "limit_price_policy": "derived_bounds_explicit_status_only",
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:audit_institution_fact_package",
        }
    )


def _read_tradability_rows(
    duckdb_root: Path,
    ts_codes: list[str],
    window_start: str,
    window_end: str,
    offline_root: Path | None,
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

    metadata_by_code = _load_symbol_metadata(duckdb_root, ts_codes)
    prev_close_maps = {ts_code: _prev_close_by_trade_date(offline_root, ts_code) for ts_code in ts_codes}
    grouped: dict[str, list[dict[str, str]]] = {ts_code: [] for ts_code in ts_codes}
    for symbol, trade_dt, tradability_status, blocked_reason, source_manifest_hash in rows:
        symbol_text = str(symbol)
        ts_code = symbol_to_ts.get(symbol_text)
        if ts_code is None:
            continue
        trade_date = str(trade_dt)
        symbol_metadata = metadata_by_code.get(ts_code, {})
        limit_up_price, limit_down_price = _derive_limit_prices(
            prev_close=prev_close_maps.get(ts_code, {}).get(trade_date, ""),
            board_type=str(symbol_metadata.get("board_type", _board_type(ts_code))),
            is_st=symbol_metadata.get("is_st"),
            is_new_stock_window=_is_new_stock_window(str(symbol_metadata.get("list_date", "")), trade_date),
        )
        grouped[ts_code].append(
            {
                "ts_code": ts_code,
                "trade_date": trade_date,
                "is_trading_day": "true",
                "is_suspended": "true" if _is_suspended(tradability_status, blocked_reason) else "false",
                "limit_up_price": limit_up_price,
                "limit_down_price": limit_down_price,
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


def _load_symbol_metadata(duckdb_root: Path, ts_codes: list[str]) -> dict[str, dict[str, Any]]:
    db_path = duckdb_root / "market_meta.duckdb"
    if not db_path.exists() or not ts_codes:
        return {}
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception:
        return {}
    table_ref = _resolve_duckdb_table_ref(con, "instrument_master")
    if table_ref is None:
        con.close()
        return {}

    symbol_to_ts = {_ts_code_to_duckdb_symbol(ts_code): ts_code for ts_code in ts_codes}
    placeholders = ", ".join(["?"] * len(symbol_to_ts))
    rows = con.execute(
        f"""
        select symbol, exchange, name, list_dt
        from {table_ref}
        where symbol in ({placeholders})
          and coalesce(asset_type, 'stock') in ('stock', 'equity')
        """,
        [*symbol_to_ts.keys()],
    ).fetchall()
    con.close()

    metadata: dict[str, dict[str, Any]] = {}
    for symbol, exchange, name, list_dt in rows:
        ts_code, _market = _normalize_duckdb_symbol(symbol, exchange)
        if ts_code not in symbol_to_ts.values():
            continue
        list_date = str(list_dt) if list_dt is not None else ""
        metadata[ts_code] = {
            "board_type": _board_type(ts_code),
            "is_st": _is_st_name(str(name or "")) if name is not None else None,
            "list_date": list_date,
        }
    return metadata


def _prev_close_by_trade_date(offline_root: Path | None, ts_code: str) -> dict[str, str]:
    if offline_root is None:
        return {}
    daily_rows = read_daily_bars(offline_root, ts_code)
    if not daily_rows:
        return {}

    result: dict[str, str] = {}
    previous_close = ""
    for row in daily_rows:
        trade_date = str(row.get("trade_date", ""))
        if trade_date:
            result[trade_date] = previous_close
        close_value = row.get("close")
        previous_close = "" if close_value in (None, "") else f"{Decimal(str(close_value)):.2f}"
    return result


def _derive_limit_prices(
    prev_close: str,
    board_type: str,
    is_st: bool | None,
    is_new_stock_window: bool | None,
) -> tuple[str, str]:
    if not prev_close:
        return "", ""
    if is_st is None or is_new_stock_window is None:
        return "", ""
    if is_new_stock_window:
        return "", ""

    ratio = Decimal("0.05") if is_st else _limit_ratio(board_type)
    if ratio is None:
        return "", ""

    prev_close_decimal = Decimal(prev_close)
    limit_up = (prev_close_decimal * (Decimal("1") + ratio)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    limit_down = (prev_close_decimal * (Decimal("1") - ratio)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{limit_up:.2f}", f"{limit_down:.2f}"


def _limit_ratio(board_type: str) -> Decimal | None:
    if board_type == "main":
        return Decimal("0.10")
    if board_type in {"gem", "star"}:
        return Decimal("0.20")
    if board_type == "bse":
        return Decimal("0.30")
    return None


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


def _is_new_stock_window(list_date: str, trade_date: str) -> bool | None:
    if not list_date:
        return None
    if not trade_date:
        return None
    try:
        list_dt = datetime.fromisoformat(list_date)
        trade_dt = datetime.fromisoformat(trade_date)
    except ValueError:
        return None
    return (trade_dt - list_dt).days <= 365


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


def _remove_target_files(output_dir: Path, ts_codes: list[str]) -> None:
    for ts_code in ts_codes:
        path = output_dir / f"{ts_code}.csv"
        if path.exists():
            path.unlink()


def _replace_target_files(staging_dir: Path, output_dir: Path, ts_codes: list[str]) -> None:
    _remove_target_files(output_dir, ts_codes)
    for ts_code in ts_codes:
        (staging_dir / f"{ts_code}.csv").replace(output_dir / f"{ts_code}.csv")


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
    parser.add_argument("--offline-root")
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
        offline_root=args.offline_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
