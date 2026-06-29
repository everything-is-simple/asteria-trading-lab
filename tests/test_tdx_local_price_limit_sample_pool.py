from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sources.tdx_local.price_limit_sample_pool import (
    screen_pullback_add_price_limit_candidates,
)


def _create_market_meta_db(path: Path) -> None:
    con = duckdb.connect(str(path))
    con.execute("create schema market_meta")
    con.execute(
        """
        create table market_meta.market_meta.instrument_master (
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
    con.execute(
        """
        create table market_meta.market_meta.industry_block_relation (
            symbol varchar,
            asset_type varchar,
            relation_type varchar,
            relation_code varchar,
            relation_name varchar,
            effective_from date,
            effective_to date,
            source_run_id varchar,
            schema_version varchar,
            rule_version varchar,
            source_manifest_hash varchar
        )
        """
    )
    con.executemany(
        """
        insert into market_meta.market_meta.instrument_master values
        (?, 'stock', ?, ?, ?, null, 'run-1', 'v1', 'r1', 'hash-1')
        """,
        [
            ("sz000001", "SZ", "Alpha Power", "2020-01-01"),
            ("sz300123", "SZ", "Growth Motion", "2020-01-01"),
            ("sh600200", "SH", "Energy ETF", "2020-01-01"),
            ("sh600300", "SH", "ST Skip", "2020-01-01"),
        ],
    )
    tradability_rows = []
    for symbol in ("sz000001", "sz300123", "sh600200", "sh600300"):
        for trade_dt in (
            "2026-03-20",
            "2026-03-23",
            "2026-03-24",
            "2026-03-25",
            "2026-03-26",
            "2026-03-27",
            "2026-03-30",
            "2026-03-31",
        ):
            tradability_rows.append(
                (symbol, "stock", trade_dt, "tradable", None, "unit-test", "run-1", "v1", "r1", "hash-1")
            )
    con.executemany(
        """
        insert into market_meta.market_meta.tradability_fact values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        tradability_rows,
    )
    con.executemany(
        """
        insert into market_meta.market_meta.industry_block_relation values
        (?, 'stock', 'industry', ?, ?, ?, ?, 'run-1', 'v1', 'r1', 'hash-1')
        """,
        [
            ("sz000001", "T1001", "Utilities", "2026-03-01", None),
            ("sz300123", "T2001", "Growth", "2026-04-23", None),
            ("sh600200", "T3001", "FundLike", "2026-03-01", None),
            ("sh600300", "T4001", "StLike", "2026-03-01", None),
        ],
    )
    con.close()


def _create_market_base_day_db(path: Path) -> None:
    con = duckdb.connect(str(path))
    con.execute("create schema market_base_day")
    con.execute(
        """
        create table market_base_day.market_base_day.base_bar (
            symbol varchar,
            asset_type varchar,
            timeframe varchar,
            bar_dt date,
            trade_dt date,
            open double,
            high double,
            low double,
            close double,
            volume bigint,
            amount double,
            analysis_price_line varchar,
            source_run_id varchar,
            schema_version varchar,
            rule_version varchar,
            source_manifest_hash varchar
        )
        """
    )
    rows = [
        ("sz000001", "stock", "day", "2026-03-20", "2026-03-20", 10.5, 10.6, 10.4, 10.5),
        ("sz000001", "stock", "day", "2026-03-23", "2026-03-23", 10.8, 11.1, 10.7, 11.0),
        ("sz000001", "stock", "day", "2026-03-24", "2026-03-24", 11.1, 11.9, 10.9, 11.6),
        ("sz000001", "stock", "day", "2026-03-25", "2026-03-25", 11.7, 12.0, 11.5, 11.8),
        ("sz000001", "stock", "day", "2026-03-26", "2026-03-26", 11.5, 11.5, 10.9, 11.4),
        ("sz000001", "stock", "day", "2026-03-27", "2026-03-27", 10.9, 11.0, 10.3, 10.8),
        ("sz000001", "stock", "day", "2026-03-30", "2026-03-30", 10.2, 10.1, 9.02, 9.7),
        ("sz300123", "stock", "day", "2026-03-20", "2026-03-20", 20.4, 20.6, 20.0, 20.5),
        ("sz300123", "stock", "day", "2026-03-23", "2026-03-23", 20.7, 21.8, 20.6, 21.5),
        ("sz300123", "stock", "day", "2026-03-24", "2026-03-24", 21.6, 23.2, 21.4, 22.8),
        ("sz300123", "stock", "day", "2026-03-25", "2026-03-25", 22.9, 23.5, 22.4, 23.0),
        ("sz300123", "stock", "day", "2026-03-26", "2026-03-26", 22.6, 22.8, 21.8, 22.0),
        ("sz300123", "stock", "day", "2026-03-27", "2026-03-27", 21.8, 22.0, 20.9, 21.2),
        ("sz300123", "stock", "day", "2026-03-30", "2026-03-30", 21.0, 21.1, 20.0, 20.0),
        ("sz300123", "stock", "day", "2026-03-31", "2026-03-31", 18.0, 18.5, 16.0, 16.4),
        ("sh600200", "stock", "day", "2026-03-20", "2026-03-20", 8.0, 8.4, 7.9, 8.3),
        ("sh600200", "stock", "day", "2026-03-23", "2026-03-23", 8.3, 8.6, 8.2, 8.5),
        ("sh600200", "stock", "day", "2026-03-24", "2026-03-24", 8.5, 8.9, 8.4, 8.8),
        ("sh600200", "stock", "day", "2026-03-25", "2026-03-25", 8.8, 9.0, 8.7, 8.9),
        ("sh600200", "stock", "day", "2026-03-26", "2026-03-26", 8.9, 9.1, 8.8, 9.0),
        ("sh600200", "stock", "day", "2026-03-27", "2026-03-27", 9.0, 9.2, 8.9, 9.1),
        ("sh600200", "stock", "day", "2026-03-30", "2026-03-30", 9.0, 9.1, 8.2, 8.4),
        ("sh600300", "stock", "day", "2026-03-20", "2026-03-20", 7.0, 7.4, 6.9, 7.3),
        ("sh600300", "stock", "day", "2026-03-23", "2026-03-23", 7.3, 7.7, 7.2, 7.6),
        ("sh600300", "stock", "day", "2026-03-24", "2026-03-24", 7.6, 7.9, 7.5, 7.8),
        ("sh600300", "stock", "day", "2026-03-25", "2026-03-25", 7.8, 8.0, 7.7, 7.9),
        ("sh600300", "stock", "day", "2026-03-26", "2026-03-26", 7.9, 8.1, 7.8, 8.0),
        ("sh600300", "stock", "day", "2026-03-27", "2026-03-27", 8.0, 8.2, 7.9, 8.1),
        ("sh600300", "stock", "day", "2026-03-30", "2026-03-30", 8.0, 8.1, 7.29, 7.5),
    ]
    con.executemany(
        """
        insert into market_base_day.market_base_day.base_bar values
        (?, ?, ?, ?, ?, ?, ?, ?, ?, 100000, 1000000.0, 'unit-test', 'run-1', 'v1', 'r1', 'hash-1')
        """,
        rows,
    )
    con.close()


class PriceLimitSamplePoolTest(unittest.TestCase):
    def test_screen_pullback_add_price_limit_candidates_returns_ranked_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            _create_market_meta_db(duckdb_root / "market_meta.duckdb")
            _create_market_base_day_db(duckdb_root / "market_base_day.duckdb")

            rows = screen_pullback_add_price_limit_candidates(
                duckdb_root=duckdb_root,
                window_start="2026-03-24",
                window_end="2026-03-31",
            )

        self.assertEqual([row["ts_code"] for row in rows], ["300123.SZ", "000001.SZ"])
        self.assertEqual(rows[0]["proximity_bucket"], "at_limit_candidate")
        self.assertEqual(rows[0]["nearest_limit_side"], "down_limit_side")
        self.assertEqual(rows[1]["proximity_bucket"], "near_limit_candidate")
        self.assertLess(rows[0]["nearest_limit_gap_pct"], rows[1]["nearest_limit_gap_pct"])

    def test_screen_pullback_add_price_limit_candidates_excludes_st_and_fund_like_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            _create_market_meta_db(duckdb_root / "market_meta.duckdb")
            _create_market_base_day_db(duckdb_root / "market_base_day.duckdb")

            rows = screen_pullback_add_price_limit_candidates(
                duckdb_root=duckdb_root,
                window_start="2026-03-24",
                window_end="2026-03-31",
            )

        names = {row["symbol_name"] for row in rows}
        self.assertNotIn("Energy ETF", names)
        self.assertNotIn("ST Skip", names)

    def test_screen_pullback_add_price_limit_candidates_marks_window_industry_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            _create_market_meta_db(duckdb_root / "market_meta.duckdb")
            _create_market_base_day_db(duckdb_root / "market_base_day.duckdb")

            rows = screen_pullback_add_price_limit_candidates(
                duckdb_root=duckdb_root,
                window_start="2026-03-24",
                window_end="2026-03-31",
            )

        by_code = {row["ts_code"]: row for row in rows}
        self.assertTrue(by_code["000001.SZ"]["industry_window_overlap"])
        self.assertEqual(by_code["000001.SZ"]["industry_window_status"], "overlapping")
        self.assertFalse(by_code["300123.SZ"]["industry_window_overlap"])
        self.assertEqual(by_code["300123.SZ"]["industry_window_status"], "not_overlapping")

    def test_screen_pullback_add_price_limit_candidates_can_require_window_industry_overlap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            _create_market_meta_db(duckdb_root / "market_meta.duckdb")
            _create_market_base_day_db(duckdb_root / "market_base_day.duckdb")

            rows = screen_pullback_add_price_limit_candidates(
                duckdb_root=duckdb_root,
                window_start="2026-03-24",
                window_end="2026-03-31",
                require_industry_window_overlap=True,
            )

        self.assertEqual([row["ts_code"] for row in rows], ["000001.SZ"])
        self.assertTrue(rows[0]["industry_window_overlap"])


if __name__ == "__main__":
    unittest.main()
