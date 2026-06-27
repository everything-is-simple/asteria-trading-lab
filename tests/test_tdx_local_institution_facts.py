from __future__ import annotations

import csv
import json
from pathlib import Path
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


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    unittest.main()
