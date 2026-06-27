from __future__ import annotations

from pathlib import Path
from typing import Any

from .readers import build_minimal_read_report, inspect_duckdb_assets, probe_pytdx_reader


PRIMARY_OUTPUTS = [
    "symbol_master",
    "trading_calendar",
    "daily_bars",
    "sector_membership",
]

AUXILIARY_OUTPUTS = ["adjustment_metadata"]

FIELD_MAPPING = {
    "symbol_master": {
        "sources": [
            "tdx_local_python_pymp",
            "offline_stock_text_or_archive",
            "duckdb_market_meta",
        ],
        "fields": ["ts_code", "symbol_name", "market", "list_status", "source_ref"],
        "boundary": "identity_facts_only",
    },
    "trading_calendar": {
        "sources": ["tdx_vipdoc", "offline_daily_windows", "duckdb_market_base_day"],
        "fields": ["trade_date", "is_trading_day", "market", "source_ref"],
        "boundary": "calendar_facts_only",
    },
    "daily_bars": {
        "sources": ["offline_stock_day", "tdx_vipdoc_day", "duckdb_market_base_day"],
        "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "volume", "amount", "source_ref"],
        "boundary": "ohlcv_facts_only",
    },
    "sector_membership": {
        "sources": ["offline_block", "offline_block_day", "duckdb_market_meta"],
        "fields": ["ts_code", "sector_code", "sector_name", "valid_from", "valid_to", "source_ref"],
        "boundary": "membership_facts_only",
    },
    "adjustment_metadata": {
        "sources": ["offline_adjustment_archive", "duckdb_corporate_action_traces"],
        "fields": ["ts_code", "event_date", "adjustment_type", "source_ref"],
        "boundary": "auxiliary_fact_not_primary_output",
    },
}


def audit_local_data_assets(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
) -> dict[str, Any]:
    tdx_path = Path(tdx_root)
    offline_path = Path(offline_root)
    duckdb_path = Path(duckdb_root)
    issues = _missing_path_issues(tdx_path, offline_path, duckdb_path)
    return {
        "result": "blocked" if issues else "pass",
        "issues": issues,
        "asset_summary": {
            "tdx": _tdx_summary(tdx_path),
            "offline": _offline_summary(offline_path),
            "duckdb": _duckdb_summary(duckdb_path),
        },
        "primary_outputs": PRIMARY_OUTPUTS,
        "auxiliary_outputs": AUXILIARY_OUTPUTS,
        "field_mapping": FIELD_MAPPING,
        "minimal_read_capability": build_minimal_read_report(tdx_path, offline_path, duckdb_path),
        "duckdb_introspection": inspect_duckdb_assets(duckdb_path),
        "pytdx_reader_probe": probe_pytdx_reader(tdx_path),
        "selected_source_policy": {
            "symbol_master": "duckdb_first",
            "trading_calendar": "duckdb_first",
            "sector_membership": "duckdb_first",
            "daily_bars": "file_first",
        },
        "source_priority": [
            "local_tongdaxin_duckdb",
            "baostock_validation",
            "akshare_research_patch",
        ],
        "raw_asset_policy": "summaries_only",
        "formal_data_write_allowed": False,
        "raw_market_file_export_allowed": False,
        "signal_generation_allowed": False,
        "backtest_execution_allowed": False,
        "next_action": "action:review_local_data_asset_mapping"
        if not issues
        else "action:repair_local_data_paths",
    }


def _missing_path_issues(tdx_root: Path, offline_root: Path, duckdb_root: Path) -> list[str]:
    issues: list[str] = []
    if not tdx_root.exists():
        issues.append("missing_path:tdx_root")
    if not offline_root.exists():
        issues.append("missing_path:offline_root")
    if not duckdb_root.exists():
        issues.append("missing_path:duckdb_root")
    return issues


def _tdx_summary(root: Path) -> dict[str, Any]:
    return {
        "root": str(root),
        "exists": root.exists(),
        "vipdoc_exists": (root / "vipdoc").exists(),
        "pymp_mode_markers": {
            "tqcenter_py": (root / "PYPlugins" / "user" / "tqcenter.py").exists(),
            "tpyth_dll": (root / "TPyth.dll").exists(),
            "tpyth_client_dll": (root / "TPythClient.dll").exists(),
        },
        "vipdoc_markets": _child_dir_names(root / "vipdoc"),
    }


def _offline_summary(root: Path) -> dict[str, Any]:
    expected_dirs = ["stock", "stock-day", "index", "index-day", "block", "block-day", "raw"]
    return {
        "root": str(root),
        "exists": root.exists(),
        "expected_dirs": {
            name: (root / name).exists()
            for name in expected_dirs
        },
        "large_files": _file_summaries(root, patterns=["*.7z", "*.zip", "*.day", "*.txt"], limit=20),
    }


def _duckdb_summary(root: Path) -> dict[str, Any]:
    return {
        "root": str(root),
        "exists": root.exists(),
        "files": _file_summaries(root, patterns=["*.duckdb"], limit=20),
    }


def _child_dir_names(path: Path) -> list[str]:
    if not path.exists():
        return []
    return sorted(child.name for child in path.iterdir() if child.is_dir())


def _file_summaries(root: Path, patterns: list[str], limit: int) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root.rglob(pattern))
    summaries: list[dict[str, Any]] = []
    for path in sorted(set(files))[:limit]:
        summaries.append(
            {
                "path": _safe_relative_path(path, root),
                "size_bytes": path.stat().st_size,
            }
        )
    return summaries


def _safe_relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
