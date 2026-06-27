from __future__ import annotations

import argparse
import configparser
import json
from pathlib import Path
from typing import Any


BLOCKED_PATTERNS = ["*.day", "*.txt", "*.duckdb", "*.7z"]
BLOCKED_LOCATIONS = ["Z:\\new_tdx64", "Z:\\tdx_offline_Data", "Z:\\malf-data"]
SOURCE_PRIORITY = ["local_tdx_pymp", "offline_tdx_files", "legacy_duckdb"]


def audit_local_data_assets(
    tdx_root: str | Path,
    offline_root: str | Path,
    duckdb_root: str | Path,
) -> dict[str, Any]:
    tdx_path = Path(tdx_root)
    offline_path = Path(offline_root)
    duckdb_path = Path(duckdb_root)

    issues: list[str] = []

    required_files = {
        "TdxW.exe": (tdx_path / "TdxW.exe").exists(),
        "PYPlugins/user/tqcenter.py": (tdx_path / "PYPlugins" / "user" / "tqcenter.py").exists(),
        "PYPlugins/TPyth.dll": (tdx_path / "PYPlugins" / "TPyth.dll").exists(),
        "PYPlugins/TPythClient.dll": (tdx_path / "PYPlugins" / "TPythClient.dll").exists(),
    }

    tdx_ready = tdx_path.exists() and all(required_files.values())
    if not tdx_path.exists():
        issues.append("missing_tdx_root")
    else:
        if not required_files["TdxW.exe"]:
            issues.append("missing_tdxw_exe")
        if not required_files["PYPlugins/user/tqcenter.py"]:
            issues.append("missing_tqcenter_py")
        if not required_files["PYPlugins/TPyth.dll"]:
            issues.append("missing_tpyth_dll")
        if not required_files["PYPlugins/TPythClient.dll"]:
            issues.append("missing_tpyth_client_dll")

    offline_ready = offline_path.exists()
    if not offline_ready:
        issues.append("missing_offline_root")

    duckdb_ready = duckdb_path.exists()
    if not duckdb_ready:
        issues.append("missing_duckdb_root")

    port = _read_pymp_port(tdx_path / "TMTconfig.ini") if tdx_path.exists() else None
    offline_extension_totals = _count_extensions(offline_path) if offline_ready else {}
    duckdb_file_count = _count_duckdb_files(duckdb_path) if duckdb_ready else 0

    result = "pass" if not issues else "blocked"
    return {
        "result": result,
        "next_action": "action:continue_local_audit" if result == "pass" else "action:repair_local_data_assets",
        "issues": issues,
        "tdx": {
            "ready": tdx_ready,
            "status": "ready" if tdx_ready else "missing",
            "mode": "local_python_pymp" if tdx_ready else "unavailable",
            "root": str(tdx_path),
            "port": port,
            "required_files": required_files,
        },
        "offline": {
            "ready": offline_ready,
            "root": str(offline_path),
            "extension_totals": offline_extension_totals,
        },
        "duckdb": {
            "ready": duckdb_ready,
            "root": str(duckdb_path),
            "duckdb_file_count": duckdb_file_count,
        },
        "upload_boundary": {
            "never_copy_to_repo": True,
            "blocked_locations": BLOCKED_LOCATIONS,
            "blocked_patterns": BLOCKED_PATTERNS,
        },
        "source_priority": SOURCE_PRIORITY,
        "field_mapping": {
            "symbol_master": {
                "source_files": ["stock/<ts_code>.txt", "stock/summary.txt"],
                "target_fields": ["ts_code", "symbol_name", "board_type", "list_date", "source_ref"],
            },
            "trading_calendar": {
                "source_files": ["stock-day/<ts_code>.day", "raw/calendar.txt"],
                "target_fields": ["trade_date", "is_trading_day", "source_ref"],
            },
            "daily_bars": {
                "source_files": ["stock-day/<ts_code>.day", "stock/<ts_code>.txt"],
                "target_fields": ["ts_code", "trade_date", "open", "high", "low", "close", "volume", "amount"],
            },
            "adjustment_metadata": {
                "source_files": ["raw/*.txt", "market_meta.duckdb"],
                "target_fields": ["adj_ref", "corporate_action_flag", "source_ref"],
            },
            "sector_membership": {
                "source_files": ["stock/*.txt", "block/*.txt", "index/*.txt"],
                "target_fields": ["ts_code", "sw_l1_name", "sw_l2_name", "valid_from", "valid_to", "source_ref"],
            },
        },
    }


def _read_pymp_port(path: Path) -> int | None:
    if not path.exists():
        return None
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    if "PYMP" not in parser:
        return None
    try:
        return parser.getint("PYMP", "Port")
    except (ValueError, configparser.Error):
        return None


def _count_extensions(root: Path) -> dict[str, int]:
    totals: dict[str, int] = {}
    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        suffix = file_path.suffix.lower() or "<no_suffix>"
        totals[suffix] = totals.get(suffix, 0) + 1
    return dict(sorted(totals.items()))


def _count_duckdb_files(root: Path) -> int:
    return sum(1 for file_path in root.rglob("*.duckdb") if file_path.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit local Tongdaxin, offline data, and legacy DuckDB assets.")
    parser.add_argument("--tdx-root", required=True)
    parser.add_argument("--offline-root", required=True)
    parser.add_argument("--duckdb-root", required=True)
    args = parser.parse_args(argv)

    report = audit_local_data_assets(args.tdx_root, args.offline_root, args.duckdb_root)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
