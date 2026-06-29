from __future__ import annotations

from pathlib import Path
import re
import struct
from typing import Any

import duckdb


DAY_RECORD_SIZE = 32
MARKET_TO_SUFFIX = {"sh": "SH", "sz": "SZ", "bj": "BJ"}
SUFFIX_TO_MARKET = {"SH": "sh", "SZ": "sz", "BJ": "bj"}
TEXT_ADJUSTMENT_DIRS = {
    "non_adjusted": "Non-Adjusted",
    "forward_adjusted": "Forward-Adjusted",
    "backward_adjusted": "Backward-Adjusted",
}
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


def read_symbol_master(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if duckdb_root is not None:
        rows = _read_symbol_master_from_duckdb(Path(duckdb_root), limit)
        if rows:
            return rows
    roots = [
        Path(tdx_root) / "vipdoc",
        Path(offline_root) / "raw",
        Path(offline_root) / "stock",
        Path(offline_root) / "block",
    ]
    rows: dict[str, dict[str, Any]] = {}
    for root in roots:
        for path in _iter_symbol_files(root):
            parsed = _parse_symbol_from_path(path)
            if parsed is None:
                continue
            ts_code, market = parsed
            rows.setdefault(
                ts_code,
                _strip_forbidden_fields(
                    {
                        "ts_code": ts_code,
                        "market": market,
                        "symbol_name": None,
                        "source_type": _source_type(path),
                        "source_path": path.as_posix(),
                        "source_ref": path.as_posix(),
                    }
                ),
            )
            if limit is not None and len(rows) >= limit:
                return list(rows.values())
    return list(rows.values())


def read_trading_calendar(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path | None = None,
    limit_files: int = 200,
) -> list[dict[str, Any]]:
    if duckdb_root is not None:
        rows = _read_trading_calendar_from_duckdb(Path(duckdb_root), limit_files)
        if rows:
            return rows
    dates: dict[tuple[str, str], dict[str, Any]] = {}
    files = [
        *list(_iter_day_files(Path(offline_root) / "raw"))[:limit_files],
        *list(_iter_day_files(Path(tdx_root) / "vipdoc"))[:limit_files],
        *list(_iter_text_bar_files(Path(offline_root) / "stock"))[:limit_files],
    ][:limit_files]
    for path in files:
        parsed_symbol = _parse_symbol_from_path(path)
        market = parsed_symbol[1] if parsed_symbol else "UNKNOWN"
        for trade_date in _dates_from_bar_file(path):
            dates[(market, trade_date)] = _strip_forbidden_fields(
                {
                    "trade_date": trade_date,
                    "market": market,
                    "source_ref": path.as_posix(),
                }
            )
    return sorted(dates.values(), key=lambda row: (row["trade_date"], row["market"]))


def read_daily_bars(
    offline_root: str | Path,
    ts_code: str,
    adjustment: str = "raw",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    root = Path(offline_root)
    if adjustment == "raw":
        path = _raw_day_path(root, ts_code)
        if not path.exists():
            return []
        return _read_day_file(path, ts_code, limit, root)
    if adjustment not in TEXT_ADJUSTMENT_DIRS:
        raise ValueError(f"unsupported_adjustment:{adjustment}")
    path = _text_bar_path(root, ts_code, adjustment)
    if not path.exists():
        return []
    return _read_text_bar_file(path, ts_code, limit, root)


def read_sector_membership(
    offline_root: str | Path,
    tdx_root: str | Path | None = None,
    duckdb_root: str | Path | None = None,
    limit_files: int = 200,
) -> dict[str, Any]:
    root = Path(offline_root)
    if duckdb_root is not None:
        report = _read_sector_membership_from_duckdb(Path(duckdb_root), limit_files)
        if report.get("result") == "pass":
            return report
    if tdx_root is not None:
        report = _read_sector_membership_from_tdx_hq_cache(Path(tdx_root), limit_files)
        if report.get("result") != "blocked":
            return report
    candidates: list[Path] = []
    block_root = root / "block"
    if block_root.exists():
        candidates.extend(list(block_root.rglob("*member*"))[:limit_files])
        candidates.extend(list(block_root.rglob("*component*"))[:limit_files])
        candidates.extend(list(block_root.rglob("*成分*"))[:limit_files])
    if not candidates:
        return {
            "result": "blocked",
            "reason": "sector_membership_source_missing",
            "sector_membership": [],
            "candidate_source_files": [],
            "sector_membership_inferred_from_index_bars": False,
            "formal_data_write_allowed": False,
        }
    return {
        "result": "source_review_required",
        "reason": "sector_membership_source_candidates_found",
        "sector_membership": [],
        "candidate_source_files": [path.as_posix() for path in candidates[:limit_files]],
        "sector_membership_inferred_from_index_bars": False,
        "formal_data_write_allowed": False,
    }


def build_minimal_read_report(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
) -> dict[str, Any]:
    symbols = read_symbol_master(tdx_root, offline_root, duckdb_root=duckdb_root, limit=200)
    calendar = read_trading_calendar(tdx_root, offline_root, duckdb_root=duckdb_root, limit_files=200)
    sample_daily = _sample_daily_bars(offline_root, symbols)
    sector = read_sector_membership(offline_root, tdx_root=tdx_root, duckdb_root=duckdb_root, limit_files=200)
    report = {
        "result": "pass" if symbols or calendar or sample_daily else "blocked",
        "symbol_master": {
            "result": "pass" if symbols else "blocked",
            "count": len(symbols),
            "sample": symbols[:5],
            "selected_source": "duckdb_first",
            "fallback_source": "file_name_scan",
        },
        "trading_calendar": {
            "result": "pass" if calendar else "blocked",
            "count": len(calendar),
            "sample": calendar[:5],
            "selected_source": "duckdb_first",
            "fallback_source": "local_bar_dates",
        },
        "daily_bars": {
            "result": "pass" if sample_daily else "blocked",
            "count": len(sample_daily),
            "sample": sample_daily[:5],
            "selected_source": "file_first",
            "fallback_source": "text_adjustment_files",
        },
        "sector_membership": sector,
        "duckdb_introspection": inspect_duckdb_assets(duckdb_root),
        "pytdx_reader_probe": probe_pytdx_reader(tdx_root),
        "duckdb_root": str(Path(duckdb_root)),
        "formal_data_write_allowed": False,
        "raw_market_file_export_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
    }
    return _strip_forbidden_fields(report)


def inspect_duckdb_assets(duckdb_root: str | Path) -> dict[str, Any]:
    root = Path(duckdb_root)
    if not root.exists():
        return {"result": "blocked", "reason": "duckdb_root_missing", "databases": []}
    databases = []
    for db_path in sorted(root.glob("*.duckdb")):
        try:
            con = duckdb.connect(str(db_path), read_only=True)
        except Exception as exc:
            databases.append(
                {
                    "database_name": db_path.name,
                    "result": "blocked",
                    "reason": f"duckdb_open_failed:{type(exc).__name__}",
                    "tables": [],
                }
            )
            continue
        tables = con.execute(
            """
            select table_catalog, table_schema, table_name
            from information_schema.tables
            where table_schema not in ('information_schema', 'pg_catalog')
            order by table_schema, table_name
            """
        ).fetchall()
        table_reports = []
        for catalog_name, schema_name, table_name in tables:
            columns = con.execute(
                """
                select column_name, data_type
                from information_schema.columns
                where table_catalog = ? and table_schema = ? and table_name = ?
                order by ordinal_position
                """,
                [catalog_name, schema_name, table_name],
            ).fetchall()
            row_estimate = con.execute(
                f"select count(*) from {_duckdb_qualified_ref(catalog_name, schema_name, table_name)}"
            ).fetchone()[0]
            table_reports.append(
                {
                    "table_catalog": catalog_name,
                    "table_schema": schema_name,
                    "table_name": table_name,
                    "row_estimate": row_estimate,
                    "columns": [
                        {"column_name": column_name, "data_type": data_type}
                        for column_name, data_type in columns
                    ],
                }
            )
        con.close()
        databases.append(
            {
                "database_name": db_path.name,
                "tables": table_reports,
            }
        )
    return {"result": "pass", "databases": databases}


def probe_pytdx_reader(tdx_root: str | Path) -> dict[str, Any]:
    try:
        from pytdx.reader import BlockReader, TdxDailyBarReader
    except Exception as exc:
        return {
            "pytdx_reader_available": False,
            "daily_bar_reader_available": False,
            "block_reader_available": False,
            "vipdoc_detected": False,
            "available_readers": [],
            "bulk_read_performed": False,
            "reason": f"pytdx_reader_import_failed:{type(exc).__name__}",
        }
    root = Path(tdx_root)
    return {
        "pytdx_reader_available": True,
        "daily_bar_reader_available": TdxDailyBarReader is not None,
        "block_reader_available": BlockReader is not None,
        "vipdoc_detected": (root / "vipdoc").exists(),
        "available_readers": ["TdxDailyBarReader", "BlockReader"],
        "bulk_read_performed": False,
    }


def _iter_symbol_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        [
            *root.rglob("*.day"),
            *root.rglob("*.txt"),
        ]
    )


def _iter_day_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.day"))


def _iter_text_bar_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.rglob("*.txt"))


def _parse_symbol_from_path(path: Path) -> tuple[str, str] | None:
    stem = path.stem
    if "#" in stem:
        market_part, code = stem.split("#", 1)
        market = market_part.lower()
    else:
        match = re.match(r"^(sh|sz|bj)(\d{6})$", stem, re.IGNORECASE)
        if not match:
            return None
        market = match.group(1).lower()
        code = match.group(2)
    suffix = MARKET_TO_SUFFIX.get(market)
    if not suffix or not re.fullmatch(r"\d{6}", code):
        return None
    return f"{code}.{suffix}", suffix


def _source_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".day":
        return "tdx_day_file"
    if suffix == ".txt":
        return "tdx_text_bar_file"
    return "unknown_file"


def _dates_from_bar_file(path: Path) -> list[str]:
    if path.suffix.lower() == ".day":
        return [row["trade_date"] for row in _read_day_file(path, _ts_code_from_path(path), limit=None)]
    if path.suffix.lower() == ".txt":
        return [row["trade_date"] for row in _read_text_bar_file(path, _ts_code_from_path(path), limit=None)]
    return []


def _ts_code_from_path(path: Path) -> str:
    parsed = _parse_symbol_from_path(path)
    return parsed[0] if parsed else "UNKNOWN"


def _raw_day_path(root: Path, ts_code: str) -> Path:
    code, suffix = _split_ts_code(ts_code)
    market = SUFFIX_TO_MARKET[suffix]
    return root / "raw" / market / "lday" / f"{market}{code}.day"


def _text_bar_path(root: Path, ts_code: str, adjustment: str) -> Path:
    code, suffix = _split_ts_code(ts_code)
    return root / "stock" / TEXT_ADJUSTMENT_DIRS[adjustment] / f"{suffix}#{code}.txt"


def _split_ts_code(ts_code: str) -> tuple[str, str]:
    code, suffix = ts_code.split(".", 1)
    suffix = suffix.upper()
    if suffix not in SUFFIX_TO_MARKET:
        raise ValueError(f"unsupported_market:{ts_code}")
    return code, suffix


def _read_day_file(
    path: Path,
    ts_code: str,
    limit: int | None,
    source_root: Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    data = path.read_bytes()
    for offset in range(0, len(data) - (len(data) % DAY_RECORD_SIZE), DAY_RECORD_SIZE):
        record = data[offset : offset + DAY_RECORD_SIZE]
        trade_date, open_i, high_i, low_i, close_i, amount, volume, _reserved = struct.unpack("<IIIIIfII", record)
        rows.append(
            _strip_forbidden_fields(
                {
                    "ts_code": ts_code,
                    "trade_date": _format_yyyymmdd(trade_date),
                    "open": round(open_i / 100.0, 4),
                    "high": round(high_i / 100.0, 4),
                    "low": round(low_i / 100.0, 4),
                    "close": round(close_i / 100.0, 4),
                    "volume": volume,
                    "amount": float(amount),
                    "source_ref": _source_ref(path, source_root),
                }
            )
        )
        if limit is not None and len(rows) >= limit:
            break
    return rows


def _read_text_bar_file(
    path: Path,
    ts_code: str,
    limit: int | None,
    source_root: Path | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = [part.strip() for part in re.split(r"\s+", line.strip()) if part.strip()]
        if len(parts) < 7 or not re.match(r"^\d{4}/\d{1,2}/\d{1,2}$", parts[0]):
            continue
        rows.append(
            _strip_forbidden_fields(
                {
                    "ts_code": ts_code,
                    "trade_date": _format_slash_date(parts[0]),
                    "open": float(parts[1]),
                    "high": float(parts[2]),
                    "low": float(parts[3]),
                    "close": float(parts[4]),
                    "volume": int(float(parts[5])),
                    "amount": float(parts[6]),
                    "source_ref": _source_ref(path, source_root),
                }
            )
        )
        if limit is not None and len(rows) >= limit:
            break
    return rows


def _format_yyyymmdd(value: int) -> str:
    text = str(value)
    return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"


def _format_slash_date(value: str) -> str:
    year, month, day = value.split("/")
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _source_ref(path: Path, source_root: Path | None) -> str:
    if source_root is None:
        return path.as_posix()
    try:
        return path.relative_to(source_root).as_posix()
    except ValueError:
        return path.as_posix()


def _sample_daily_bars(offline_root: str | Path, symbols: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for symbol in symbols:
        ts_code = symbol.get("ts_code")
        if not isinstance(ts_code, str):
            continue
        rows = read_daily_bars(offline_root, ts_code, limit=5)
        if rows:
            return rows
        for adjustment in TEXT_ADJUSTMENT_DIRS:
            rows = read_daily_bars(offline_root, ts_code, adjustment=adjustment, limit=5)
            if rows:
                return rows
    return []


def _read_symbol_master_from_duckdb(root: Path, limit: int | None) -> list[dict[str, Any]]:
    db_path = root / "market_meta.duckdb"
    if not db_path.exists():
        return []
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception:
        return []
    table_ref = _resolve_duckdb_table_ref(con, "instrument_master")
    if table_ref is None:
        con.close()
        return []
    sql = f"""
        select symbol, exchange, name, list_dt, delist_dt
        from {table_ref}
        where coalesce(asset_type, 'stock') in ('equity', 'stock')
        order by symbol
    """
    if limit is not None:
        sql += f" limit {int(limit)}"
    rows = con.execute(sql).fetchall()
    con.close()
    normalized_rows = []
    for symbol, exchange, name, list_dt, delist_dt in rows:
        ts_code, market = _normalize_duckdb_symbol(symbol, exchange)
        normalized_rows.append(
            {
                "ts_code": ts_code,
                "market": market,
                "symbol_name": name,
                "list_date": str(list_dt) if list_dt is not None else None,
                "delist_date": str(delist_dt) if delist_dt is not None else None,
                "source_type": "duckdb_instrument_master",
                "source_path": "market_meta.duckdb:market_meta.instrument_master",
                "source_ref": "market_meta.duckdb:market_meta.instrument_master",
            }
        )
    return normalized_rows


def _read_trading_calendar_from_duckdb(root: Path, limit_files: int) -> list[dict[str, Any]]:
    db_path = root / "market_meta.duckdb"
    if not db_path.exists():
        return []
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception:
        return []
    table_ref = _resolve_duckdb_table_ref(con, "trade_calendar")
    if table_ref is None:
        con.close()
        return []
    rows = con.execute(
        f"""
        select exchange, trade_dt, is_open
        from {table_ref}
        order by trade_dt, exchange
        limit {int(limit_files)}
        """
    ).fetchall()
    con.close()
    return [
        {
            "trade_date": str(trade_dt),
            "market": str(exchange).upper(),
            "is_trading_day": bool(is_open),
            "source_ref": "market_meta.duckdb:market_meta.trade_calendar",
        }
        for exchange, trade_dt, is_open in rows
    ]


def _read_sector_membership_from_duckdb(root: Path, limit_files: int) -> dict[str, Any]:
    db_path = root / "market_meta.duckdb"
    if not db_path.exists():
        return {"result": "blocked", "reason": "sector_membership_source_missing", "sector_membership": []}
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except Exception:
        return {"result": "blocked", "reason": "sector_membership_source_missing", "sector_membership": []}
    table_ref = _resolve_duckdb_table_ref(con, "industry_block_relation")
    if table_ref is None:
        con.close()
        return {"result": "blocked", "reason": "sector_membership_source_missing", "sector_membership": []}
    rows = con.execute(
        f"""
        select symbol, relation_code, relation_name, effective_from, effective_to
        from {table_ref}
        where coalesce(asset_type, 'stock') in ('equity', 'stock')
          and coalesce(relation_type, 'industry') in ('industry', 'sw_l1')
        order by symbol, relation_code
        limit {int(limit_files)}
        """
    ).fetchall()
    con.close()
    if not rows:
        return {"result": "blocked", "reason": "sector_membership_source_missing", "sector_membership": []}
    return {
        "result": "pass",
        "selected_source": "duckdb_industry_block_relation",
        "sector_membership": [
            {
                "ts_code": _normalize_duckdb_symbol(symbol, None)[0],
                "sector_code": relation_code,
                "sector_name": relation_name,
                "valid_from": str(effective_from) if effective_from is not None else None,
                "valid_to": str(effective_to) if effective_to is not None else None,
                "source_ref": "market_meta.duckdb:market_meta.industry_block_relation",
            }
            for symbol, relation_code, relation_name, effective_from, effective_to in rows
        ],
        "sector_membership_inferred_from_index_bars": False,
        "formal_data_write_allowed": False,
    }


def _read_sector_membership_from_tdx_hq_cache(tdx_root: Path, limit_files: int) -> dict[str, Any]:
    hq_cache_root = tdx_root / "T0002" / "hq_cache"
    hy_path = hq_cache_root / "tdxhy.cfg"
    zs_path = hq_cache_root / "tdxzs.cfg"
    zs3_path = hq_cache_root / "tdxzs3.cfg"
    if not hy_path.exists() or not zs_path.exists():
        return {"result": "blocked", "reason": "sector_membership_source_missing", "sector_membership": []}
    level1_names = _read_tdx_sector_name_map(zs_path)
    level12_names = _read_tdx_sector_name_map(zs3_path) if zs3_path.exists() else {}
    rows = []
    for raw_line in hy_path.read_text(encoding="gbk", errors="ignore").splitlines():
        parts = raw_line.strip().split("|")
        if len(parts) < 6:
            continue
        market_flag, code, level1_code, _unused1, _unused2, level12_code = parts[:6]
        market = {"0": "SZ", "1": "SH", "2": "BJ"}.get(market_flag)
        if market is None or not re.fullmatch(r"\d{6}", code):
            continue
        sector_code = level1_code or level12_code
        sector_name = level1_names.get(level1_code) or level12_names.get(level12_code)
        sector_level = "tdx_industry_l1" if level1_code else "tdx_industry_l12"
        rows.append(
            {
                "ts_code": f"{code}.{market}",
                "sector_code": sector_code,
                "sector_name": sector_name,
                "sector_level": sector_level,
                "valid_from": None,
                "valid_to": None,
                "time_alignment_status": "current_snapshot_only",
                "source_ref": hy_path.as_posix(),
            }
        )
        if len(rows) >= limit_files:
            break
    if not rows:
        return {"result": "blocked", "reason": "sector_membership_source_missing", "sector_membership": []}
    return {
        "result": "source_review_required",
        "reason": "tdx_current_sector_snapshot_without_history",
        "selected_source": "tdx_hq_cache_sector_snapshot",
        "sector_membership": rows,
        "candidate_source_files": [path.as_posix() for path in [hy_path, zs_path, zs3_path] if path.exists()],
        "sector_membership_inferred_from_index_bars": False,
        "formal_data_write_allowed": False,
    }


def _read_tdx_sector_name_map(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    mapping: dict[str, str] = {}
    for raw_line in path.read_text(encoding="gbk", errors="ignore").splitlines():
        parts = raw_line.strip().split("|")
        if len(parts) < 6:
            continue
        name = parts[0].strip()
        code = parts[5].strip()
        if name and code:
            mapping[code] = name
    return mapping


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


def _resolve_duckdb_table_ref(con: duckdb.DuckDBPyConnection, table_name: str) -> str | None:
    rows = con.execute(
        """
        select table_catalog, table_schema
        from information_schema.tables
        where table_name = ?
          and table_schema not in ('information_schema', 'pg_catalog')
        order by
          case when table_schema = 'main' then 0 else 1 end,
          table_catalog,
          table_schema
        """,
        [table_name],
    ).fetchall()
    refs: list[str] = []
    for catalog_name, schema_name in rows:
        refs.append(_duckdb_qualified_ref(catalog_name, schema_name, table_name))
        refs.append(f'{_duckdb_quote(schema_name)}.{_duckdb_quote(table_name)}')
        if schema_name == "main":
            refs.append(_duckdb_quote(table_name))
    seen: set[str] = set()
    for ref in refs:
        if ref in seen:
            continue
        seen.add(ref)
        try:
            con.execute(f"select 1 from {ref} limit 1").fetchone()
            return ref
        except Exception:
            continue
    return None


def _duckdb_qualified_ref(catalog_name: str, schema_name: str, table_name: str) -> str:
    return ".".join(
        [
            _duckdb_quote(catalog_name),
            _duckdb_quote(schema_name),
            _duckdb_quote(table_name),
        ]
    )


def _duckdb_quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _normalize_duckdb_symbol(symbol: Any, exchange: Any) -> tuple[str, str]:
    symbol_text = str(symbol or "")
    exchange_text = str(exchange or "").upper()
    direct_match = re.fullmatch(r"(\d{6})\.(SH|SZ|BJ)", symbol_text, re.IGNORECASE)
    if direct_match:
        return f"{direct_match.group(1)}.{direct_match.group(2).upper()}", direct_match.group(2).upper()
    prefixed_match = re.fullmatch(r"(sh|sz|bj)(\d{6})", symbol_text, re.IGNORECASE)
    if prefixed_match:
        market = prefixed_match.group(1).upper()
        return f"{prefixed_match.group(2)}.{market}", market
    if exchange_text in SUFFIX_TO_MARKET and re.fullmatch(r"\d{6}", symbol_text):
        return f"{symbol_text}.{exchange_text}", exchange_text
    return symbol_text, exchange_text or "UNKNOWN"
