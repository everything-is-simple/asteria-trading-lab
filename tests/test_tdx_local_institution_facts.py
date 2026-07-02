from __future__ import annotations

import csv
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sources.tdx_local import build_minimal_institution_fact_package


FORBIDDEN_FIELDS = {
    "buy_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "limit_up_strategy",
}


def _write_day_file(path: Path, records: list[tuple[int, int, int, int, int, float, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"".join(
            struct.pack("<IIIIIfII", trade_date, open_i, high_i, low_i, close_i, amount, volume, 0)
            for trade_date, open_i, high_i, low_i, close_i, amount, volume in records
        )
    )


class TdxLocalInstitutionFactsTest(unittest.TestCase):
    def test_build_minimal_institution_fact_package_exports_tradability_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            data_root = root / "data"
            duckdb_root.mkdir()

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute("create schema market_meta")
            con.execute(
                """
                create table market_meta.market_meta.tradability_fact (
                    symbol varchar,
                    asset_type varchar,
                    trade_dt date,
                    tradability_status varchar,
                    blocked_reason varchar,
                    source_role varchar,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.executemany(
                """
                insert into market_meta.market_meta.tradability_fact values
                (?, 'stock', ?, ?, ?, 'tdx_direct', 'run-1', 'v1', 'r1', ?)
                """,
                [
                    ("sz000001", "2026-03-24", "tradable", None, "hash-1"),
                    ("sz000001", "2026-03-25", "blocked", "suspended", "hash-2"),
                    ("sz300750", "2026-03-24", "tradable", None, "hash-3"),
                ],
            )
            con.close()

            report = build_minimal_institution_fact_package(
                duckdb_root=duckdb_root,
                data_root=data_root,
                ts_codes=["000001.SZ", "300750.SZ"],
                window_start="2026-03-24",
                window_end="2026-03-25",
            )

            first_rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv")
            second_rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "300750.SZ.csv")

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_fact_count"], 3)
        self.assertEqual(
            report["institution_fact_files"],
            [
                "ashare/institution-facts-v0.1/000001.SZ.csv",
                "ashare/institution-facts-v0.1/300750.SZ.csv",
            ],
        )
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(first_rows[0]["ts_code"], "000001.SZ")
        self.assertEqual(first_rows[0]["trade_date"], "2026-03-24")
        self.assertEqual(first_rows[0]["is_trading_day"], "true")
        self.assertEqual(first_rows[0]["is_suspended"], "false")
        self.assertEqual(first_rows[0]["limit_up_price"], "")
        self.assertEqual(first_rows[0]["limit_down_price"], "")
        self.assertEqual(first_rows[0]["close_limit_status"], "unknown")
        self.assertEqual(first_rows[0]["touched_limit_status"], "unknown")
        self.assertEqual(first_rows[0]["board_lot_size"], "100")
        self.assertEqual(
            first_rows[0]["source_ref"],
            "market_meta.duckdb:market_meta.tradability_fact:sz000001:2026-03-24:hash-1",
        )
        self.assertEqual(first_rows[1]["is_suspended"], "true")
        self.assertEqual(second_rows[0]["ts_code"], "300750.SZ")
        for row in [*first_rows, *second_rows]:
            self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(row))

    def test_cli_builds_minimal_institution_fact_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            data_root = root / "data"
            duckdb_root.mkdir()

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table tradability_fact (
                    symbol varchar,
                    asset_type varchar,
                    trade_dt date,
                    tradability_status varchar,
                    blocked_reason varchar,
                    source_role varchar,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into tradability_fact values
                ('sz000001', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "data_sources.tdx_local.institution_facts",
                    "--duckdb-root",
                    str(duckdb_root),
                    "--data-root",
                    str(data_root),
                    "--ts-code",
                    "000001.SZ",
                    "--window-start",
                    "2026-03-24",
                    "--window-end",
                    "2026-03-24",
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_fact_count"], 1)

    def test_build_minimal_institution_fact_package_derives_price_bounds_for_known_board(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            data_root = root / "data"
            offline_root = root / "offline"
            duckdb_root.mkdir()

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table tradability_fact (
                    symbol varchar,
                    asset_type varchar,
                    trade_dt date,
                    tradability_status varchar,
                    blocked_reason varchar,
                    source_role varchar,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                create table instrument_master (
                    symbol varchar,
                    asset_type varchar,
                    exchange varchar,
                    name varchar,
                    list_dt date,
                    delist_dt date,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into tradability_fact values
                ('sz300750', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-3')
                """
            )
            con.execute(
                """
                insert into instrument_master values
                ('sz300750', 'stock', 'SZ', 'CATL', '2018-06-11', null, 'run-1', 'v1', 'r1', 'hash-im-1')
                """
            )
            con.close()

            _write_day_file(
                offline_root / "raw" / "sz" / "lday" / "sz300750.day",
                [
                    (20260321, 19800, 19900, 19700, 19800, 1000.0, 100000),
                    (20260324, 20000, 21000, 19500, 20500, 1200.0, 120000),
                ],
            )

            report = build_minimal_institution_fact_package(
                duckdb_root=duckdb_root,
                data_root=data_root,
                ts_codes=["300750.SZ"],
                window_start="2026-03-24",
                window_end="2026-03-24",
                offline_root=offline_root,
            )

            rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "300750.SZ.csv")

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["limit_price_policy"], "derived_bounds_explicit_status_only")
        self.assertEqual(rows[0]["limit_up_price"], "237.60")
        self.assertEqual(rows[0]["limit_down_price"], "158.40")
        self.assertEqual(rows[0]["close_limit_status"], "unknown")
        self.assertEqual(rows[0]["touched_limit_status"], "unknown")

    def test_build_minimal_institution_fact_package_keeps_bounds_empty_for_new_stock_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            data_root = root / "data"
            offline_root = root / "offline"
            duckdb_root.mkdir()

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table tradability_fact (
                    symbol varchar,
                    asset_type varchar,
                    trade_dt date,
                    tradability_status varchar,
                    blocked_reason varchar,
                    source_role varchar,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                create table instrument_master (
                    symbol varchar,
                    asset_type varchar,
                    exchange varchar,
                    name varchar,
                    list_dt date,
                    delist_dt date,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into tradability_fact values
                ('sz301001', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-9')
                """
            )
            con.execute(
                """
                insert into instrument_master values
                ('sz301001', 'stock', 'SZ', 'New Listing', '2026-01-10', null, 'run-1', 'v1', 'r1', 'hash-im-2')
                """
            )
            con.close()

            _write_day_file(
                offline_root / "raw" / "sz" / "lday" / "sz301001.day",
                [
                    (20260321, 1000, 1100, 900, 1000, 100.0, 10000),
                    (20260324, 1010, 1200, 1000, 1150, 120.0, 12000),
                ],
            )

            report = build_minimal_institution_fact_package(
                duckdb_root=duckdb_root,
                data_root=data_root,
                ts_codes=["301001.SZ"],
                window_start="2026-03-24",
                window_end="2026-03-24",
                offline_root=offline_root,
            )

            rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "301001.SZ.csv")

        self.assertEqual(report["result"], "pass")
        self.assertEqual(rows[0]["limit_up_price"], "")
        self.assertEqual(rows[0]["limit_down_price"], "")
        self.assertEqual(rows[0]["close_limit_status"], "unknown")
        self.assertEqual(rows[0]["touched_limit_status"], "unknown")

    def test_build_minimal_institution_fact_package_keeps_bounds_empty_without_prev_close(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            data_root = root / "data"
            offline_root = root / "offline"
            duckdb_root.mkdir()

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table tradability_fact (
                    symbol varchar,
                    asset_type varchar,
                    trade_dt date,
                    tradability_status varchar,
                    blocked_reason varchar,
                    source_role varchar,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                create table instrument_master (
                    symbol varchar,
                    asset_type varchar,
                    exchange varchar,
                    name varchar,
                    list_dt date,
                    delist_dt date,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into tradability_fact values
                ('sh600000', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-6')
                """
            )
            con.execute(
                """
                insert into instrument_master values
                ('sh600000', 'stock', 'SH', 'PF Bank', '1999-11-10', null, 'run-1', 'v1', 'r1', 'hash-im-3')
                """
            )
            con.close()

            _write_day_file(
                offline_root / "raw" / "sh" / "lday" / "sh600000.day",
                [
                    (20260324, 1000, 1020, 990, 1010, 100.0, 10000),
                ],
            )

            report = build_minimal_institution_fact_package(
                duckdb_root=duckdb_root,
                data_root=data_root,
                ts_codes=["600000.SH"],
                window_start="2026-03-24",
                window_end="2026-03-24",
                offline_root=offline_root,
            )

            rows = _read_csv(data_root / "ashare" / "institution-facts-v0.1" / "600000.SH.csv")

        self.assertEqual(report["result"], "pass")
        self.assertEqual(rows[0]["limit_up_price"], "")
        self.assertEqual(rows[0]["limit_down_price"], "")

    def test_cli_builds_minimal_institution_fact_package_with_derived_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            data_root = root / "data"
            offline_root = root / "offline"
            duckdb_root.mkdir()

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table tradability_fact (
                    symbol varchar,
                    asset_type varchar,
                    trade_dt date,
                    tradability_status varchar,
                    blocked_reason varchar,
                    source_role varchar,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                create table instrument_master (
                    symbol varchar,
                    asset_type varchar,
                    exchange varchar,
                    name varchar,
                    list_dt date,
                    delist_dt date,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into tradability_fact values
                ('sz300750', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-3')
                """
            )
            con.execute(
                """
                insert into instrument_master values
                ('sz300750', 'stock', 'SZ', 'CATL', '2018-06-11', null, 'run-1', 'v1', 'r1', 'hash-im-4')
                """
            )
            con.close()

            _write_day_file(
                offline_root / "raw" / "sz" / "lday" / "sz300750.day",
                [
                    (20260321, 19800, 19900, 19700, 19800, 1000.0, 100000),
                    (20260324, 20000, 21000, 19500, 20500, 1200.0, 120000),
                ],
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "data_sources.tdx_local.institution_facts",
                    "--duckdb-root",
                    str(duckdb_root),
                    "--data-root",
                    str(data_root),
                    "--offline-root",
                    str(offline_root),
                    "--ts-code",
                    "300750.SZ",
                    "--window-start",
                    "2026-03-24",
                    "--window-end",
                    "2026-03-24",
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["limit_price_policy"], "derived_bounds_explicit_status_only")

    def test_blocked_run_clears_requested_stale_files_when_a_ts_code_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            data_root = root / "data"
            duckdb_root.mkdir()

            stale_path = data_root / "ashare" / "institution-facts-v0.1" / "300750.SZ.csv"
            stale_path.parent.mkdir(parents=True, exist_ok=True)
            stale_path.write_text(
                "ts_code,trade_date,is_trading_day,is_suspended,limit_up_price,limit_down_price,close_limit_status,touched_limit_status,board_lot_size,source_ref\n"
                "300750.SZ,2026-03-24,true,false,,,unknown,unknown,100,stale\n",
                encoding="utf-8",
            )

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute(
                """
                create table tradability_fact (
                    symbol varchar,
                    asset_type varchar,
                    trade_dt date,
                    tradability_status varchar,
                    blocked_reason varchar,
                    source_role varchar,
                    source_run_id varchar,
                    schema_version varchar,
                    rule_version varchar,
                    source_manifest_hash varchar
                )
                """
            )
            con.execute(
                """
                insert into tradability_fact values
                ('sz000001', 'stock', '2026-03-24', 'tradable', null, 'tdx_direct', 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            report = build_minimal_institution_fact_package(
                duckdb_root=duckdb_root,
                data_root=data_root,
                ts_codes=["000001.SZ", "300750.SZ"],
                window_start="2026-03-24",
                window_end="2026-03-24",
            )

            stale_exists_after = stale_path.exists()

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["missing_ts_codes"], ["300750.SZ"])
        self.assertFalse(stale_exists_after)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
