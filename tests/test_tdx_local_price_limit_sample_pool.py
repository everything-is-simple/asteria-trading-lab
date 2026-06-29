from __future__ import annotations

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sources.tdx_local.price_limit_sample_pool import (
    screen_pullback_add_price_limit_candidates,
    screen_pullback_add_price_limit_candidates_with_intraday,
    shortlist_core_malf_snapshot_candidates,
    shortlist_formal_pressure_adjust_review_candidates,
    shortlist_pullback_add_pressure_adjust_candidates,
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

    def test_screen_pullback_add_price_limit_candidates_with_intraday_merges_review_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            _create_market_meta_db(duckdb_root / "market_meta.duckdb")
            _create_market_base_day_db(duckdb_root / "market_base_day.duckdb")

            intraday_reports = {
                ("300123.SZ", "2026-03-31"): {
                    "result": "source_review_required",
                    "selected_source": "tdx_lc5_intraday_range",
                    "trade_date": "2026-03-31",
                    "intraday_range": {
                        "ts_code": "300123.SZ",
                        "trade_date": "2026-03-31",
                        "bar_count": 48,
                        "intraday_open": 18.0,
                        "intraday_high": 18.5,
                        "intraday_low": 16.0,
                        "intraday_close": 16.4,
                        "source_ref": "fixture:sz300123.lc5",
                    },
                    "formal_data_write_allowed": False,
                },
                ("000001.SZ", "2026-03-27"): {
                    "result": "source_review_required",
                    "selected_source": "tdx_lc5_intraday_range",
                    "trade_date": "2026-03-27",
                    "intraday_range": {
                        "ts_code": "000001.SZ",
                        "trade_date": "2026-03-27",
                        "bar_count": 48,
                        "intraday_open": 10.9,
                        "intraday_high": 11.0,
                        "intraday_low": 10.3,
                        "intraday_close": 10.8,
                        "source_ref": "fixture:sz000001.lc5",
                    },
                    "formal_data_write_allowed": False,
                },
            }

            def fake_read_intraday_range(tdx_root: Path, ts_code: str, trade_date: str) -> dict[str, object]:
                return intraday_reports[(ts_code, trade_date)]

            with patch(
                "data_sources.tdx_local.price_limit_sample_pool.read_intraday_range",
                side_effect=fake_read_intraday_range,
            ):
                rows = screen_pullback_add_price_limit_candidates_with_intraday(
                    duckdb_root=duckdb_root,
                    tdx_root=root / "tdx",
                    window_start="2026-03-24",
                    window_end="2026-03-31",
                )

        by_code = {row["ts_code"]: row for row in rows}
        self.assertEqual(by_code["300123.SZ"]["intraday_review_result"], "source_review_required")
        self.assertEqual(by_code["300123.SZ"]["intraday_bar_count"], 48)
        self.assertEqual(by_code["300123.SZ"]["intraday_nearest_limit_side"], "down_limit_side")
        self.assertEqual(by_code["300123.SZ"]["intraday_nearest_limit_gap_pct"], 0.0)
        self.assertEqual(by_code["300123.SZ"]["intraday_limit_reopen_status"], "reopened_after_limit_touch")
        self.assertEqual(by_code["300123.SZ"]["intraday_close_gap_pct"], 2.5)
        self.assertEqual(by_code["000001.SZ"]["intraday_nearest_limit_side"], "down_limit_side")
        self.assertEqual(by_code["000001.SZ"]["intraday_nearest_limit_gap_pct"], 0.39)
        self.assertEqual(by_code["000001.SZ"]["intraday_limit_reopen_status"], "near_limit_without_touch")
        self.assertEqual(by_code["000001.SZ"]["intraday_close_gap_pct"], 5.26)

    def test_screen_pullback_add_price_limit_candidates_with_intraday_keeps_blocked_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()
            _create_market_meta_db(duckdb_root / "market_meta.duckdb")
            _create_market_base_day_db(duckdb_root / "market_base_day.duckdb")

            def fake_read_intraday_range(tdx_root: Path, ts_code: str, trade_date: str) -> dict[str, object]:
                if ts_code == "300123.SZ":
                    return {
                        "result": "blocked",
                        "reason": "intraday_bar_file_missing",
                        "trade_date": trade_date,
                        "intraday_range": None,
                        "formal_data_write_allowed": False,
                    }
                return {
                    "result": "source_review_required",
                    "selected_source": "tdx_lc5_intraday_range",
                    "trade_date": trade_date,
                    "intraday_range": {
                        "ts_code": ts_code,
                        "trade_date": trade_date,
                        "bar_count": 48,
                        "intraday_open": 10.9,
                        "intraday_high": 11.0,
                        "intraday_low": 10.3,
                        "intraday_close": 10.8,
                        "source_ref": "fixture:any.lc5",
                    },
                    "formal_data_write_allowed": False,
                }

            with patch(
                "data_sources.tdx_local.price_limit_sample_pool.read_intraday_range",
                side_effect=fake_read_intraday_range,
            ):
                rows = screen_pullback_add_price_limit_candidates_with_intraday(
                    duckdb_root=duckdb_root,
                    tdx_root=root / "tdx",
                    window_start="2026-03-24",
                    window_end="2026-03-31",
                )

        by_code = {row["ts_code"]: row for row in rows}
        self.assertEqual(by_code["300123.SZ"]["intraday_review_result"], "blocked")
        self.assertEqual(by_code["300123.SZ"]["intraday_review_reason"], "intraday_bar_file_missing")
        self.assertIsNone(by_code["300123.SZ"]["intraday_nearest_limit_gap_pct"])
        self.assertIsNone(by_code["300123.SZ"]["intraday_limit_reopen_status"])

    def test_shortlist_pullback_add_pressure_adjust_candidates_prefers_reopened_and_near_without_touch(self) -> None:
        rows = [
            {
                "ts_code": "A.SH",
                "close_return_pct": -3.0,
                "runup_pct": 50.0,
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "B.SH",
                "close_return_pct": -10.0,
                "runup_pct": 55.0,
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "closed_at_limit_after_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "C.SH",
                "close_return_pct": -7.0,
                "runup_pct": 30.0,
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "near_limit_without_touch",
                "intraday_nearest_limit_gap_pct": 0.05,
            },
            {
                "ts_code": "D.SH",
                "close_return_pct": -9.0,
                "runup_pct": 60.0,
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "E.SH",
                "close_return_pct": -4.0,
                "runup_pct": 20.0,
                "intraday_review_result": "blocked",
                "intraday_limit_reopen_status": None,
                "intraday_nearest_limit_gap_pct": None,
            },
        ]

        shortlist = shortlist_pullback_add_pressure_adjust_candidates(rows, limit=3, max_close_drop_pct=8.5)

        self.assertEqual([row["ts_code"] for row in shortlist], ["A.SH", "C.SH"])
        self.assertEqual(shortlist[0]["pressure_adjust_priority_rank"], 1)
        self.assertEqual(shortlist[0]["pressure_adjust_alignment"], "higher_priority")
        self.assertEqual(shortlist[1]["pressure_adjust_priority_rank"], 2)
        self.assertEqual(shortlist[1]["pressure_adjust_alignment"], "higher_priority")

    def test_shortlist_pullback_add_pressure_adjust_candidates_sorts_by_gap_then_close_drop(self) -> None:
        rows = [
            {
                "ts_code": "A.SH",
                "close_return_pct": -4.0,
                "runup_pct": 30.0,
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.03,
            },
            {
                "ts_code": "B.SH",
                "close_return_pct": -2.5,
                "runup_pct": 25.0,
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "C.SH",
                "close_return_pct": -5.0,
                "runup_pct": 60.0,
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
        ]

        shortlist = shortlist_pullback_add_pressure_adjust_candidates(rows, limit=3, max_close_drop_pct=8.5)

        self.assertEqual([row["ts_code"] for row in shortlist], ["B.SH", "C.SH", "A.SH"])

    def test_shortlist_formal_pressure_adjust_review_candidates_mixes_reopened_and_near_limit(self) -> None:
        rows = [
            {
                "ts_code": "R1.SH",
                "symbol_name": "Reopen One",
                "trade_date": "2026-03-30",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -3.0,
                "runup_pct": 40.0,
                "proximity_bucket": "at_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "R2.SH",
                "symbol_name": "Reopen Two",
                "trade_date": "2026-03-29",
                "nearest_limit_side": "up_limit_side",
                "close_return_pct": -4.0,
                "runup_pct": 50.0,
                "proximity_bucket": "at_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "R3.SH",
                "symbol_name": "Reopen Three",
                "trade_date": "2026-03-28",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -5.0,
                "runup_pct": 35.0,
                "proximity_bucket": "at_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "N1.SZ",
                "symbol_name": "Near One",
                "trade_date": "2026-04-03",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -7.0,
                "runup_pct": 20.0,
                "proximity_bucket": "near_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "near_limit_without_touch",
                "intraday_nearest_limit_gap_pct": 0.05,
            },
            {
                "ts_code": "N2.SZ",
                "symbol_name": "Near Two",
                "trade_date": "2026-04-02",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -7.5,
                "runup_pct": 25.0,
                "proximity_bucket": "near_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "near_limit_without_touch",
                "intraday_nearest_limit_gap_pct": 0.06,
            },
            {
                "ts_code": "C1.SH",
                "symbol_name": "Closed One",
                "trade_date": "2026-03-27",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -10.0,
                "runup_pct": 60.0,
                "proximity_bucket": "at_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "closed_at_limit_after_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
        ]

        shortlist = shortlist_formal_pressure_adjust_review_candidates(
            rows,
            reopened_limit=3,
            near_limit=2,
            max_close_drop_pct=8.5,
        )

        self.assertEqual([row["ts_code"] for row in shortlist], ["R1.SH", "R2.SH", "R3.SH", "N1.SZ", "N2.SZ"])
        self.assertEqual(shortlist[0]["formal_review_bucket"], "pressure_adjust_reopen")
        self.assertEqual(shortlist[3]["formal_review_bucket"], "near_limit_compare")
        self.assertEqual(shortlist[-1]["formal_review_priority_rank"], 5)

    def test_shortlist_formal_pressure_adjust_review_candidates_prefers_tighter_near_limit(self) -> None:
        rows = [
            {
                "ts_code": "R1.SH",
                "symbol_name": "Reopen One",
                "trade_date": "2026-03-30",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -3.0,
                "runup_pct": 40.0,
                "proximity_bucket": "at_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "reopened_after_limit_touch",
                "intraday_nearest_limit_gap_pct": 0.0,
            },
            {
                "ts_code": "N1.SZ",
                "symbol_name": "Near One",
                "trade_date": "2026-04-03",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -7.5,
                "runup_pct": 25.0,
                "proximity_bucket": "near_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "near_limit_without_touch",
                "intraday_nearest_limit_gap_pct": 0.06,
            },
            {
                "ts_code": "N2.SZ",
                "symbol_name": "Near Two",
                "trade_date": "2026-04-02",
                "nearest_limit_side": "down_limit_side",
                "close_return_pct": -7.0,
                "runup_pct": 20.0,
                "proximity_bucket": "near_limit_candidate",
                "intraday_review_result": "source_review_required",
                "intraday_limit_reopen_status": "near_limit_without_touch",
                "intraday_nearest_limit_gap_pct": 0.05,
            },
        ]

        shortlist = shortlist_formal_pressure_adjust_review_candidates(
            rows,
            reopened_limit=1,
            near_limit=1,
            max_close_drop_pct=8.5,
        )

        self.assertEqual([row["ts_code"] for row in shortlist], ["R1.SH", "N2.SZ"])

    def test_shortlist_core_malf_snapshot_candidates_prefers_pressure_adjust_reopen_rows(self) -> None:
        rows = [
            {
                "ts_code": "R1.SH",
                "symbol_name": "Reopen One",
                "trade_date": "2026-04-01",
                "formal_review_bucket": "pressure_adjust_reopen",
                "formal_review_priority_rank": 1,
                "nearest_limit_side": "down_limit_side",
            },
            {
                "ts_code": "R2.SH",
                "symbol_name": "Reopen Two",
                "trade_date": "2026-03-30",
                "formal_review_bucket": "pressure_adjust_reopen",
                "formal_review_priority_rank": 2,
                "nearest_limit_side": "down_limit_side",
            },
            {
                "ts_code": "R3.SH",
                "symbol_name": "Reopen Three",
                "trade_date": "2026-03-30",
                "formal_review_bucket": "pressure_adjust_reopen",
                "formal_review_priority_rank": 3,
                "nearest_limit_side": "up_limit_side",
            },
            {
                "ts_code": "R4.SH",
                "symbol_name": "Reopen Four",
                "trade_date": "2026-03-27",
                "formal_review_bucket": "pressure_adjust_reopen",
                "formal_review_priority_rank": 4,
                "nearest_limit_side": "down_limit_side",
            },
            {
                "ts_code": "N1.SZ",
                "symbol_name": "Near One",
                "trade_date": "2026-04-03",
                "formal_review_bucket": "near_limit_compare",
                "formal_review_priority_rank": 5,
                "nearest_limit_side": "down_limit_side",
            },
        ]

        shortlist = shortlist_core_malf_snapshot_candidates(rows, limit=4)

        self.assertEqual([row["ts_code"] for row in shortlist], ["R1.SH", "R2.SH", "R3.SH", "R4.SH"])
        self.assertEqual(shortlist[0]["core_review_bucket"], "malf_snapshot_priority")
        self.assertEqual(shortlist[0]["core_snapshot_focus"], "pressure_adjust_reopen_core")
        self.assertEqual(shortlist[-1]["core_review_priority_rank"], 4)

    def test_shortlist_core_malf_snapshot_candidates_can_fall_back_to_near_limit_compare(self) -> None:
        rows = [
            {
                "ts_code": "R1.SH",
                "symbol_name": "Reopen One",
                "trade_date": "2026-04-01",
                "formal_review_bucket": "pressure_adjust_reopen",
                "formal_review_priority_rank": 1,
                "nearest_limit_side": "down_limit_side",
            },
            {
                "ts_code": "R2.SH",
                "symbol_name": "Reopen Two",
                "trade_date": "2026-03-30",
                "formal_review_bucket": "pressure_adjust_reopen",
                "formal_review_priority_rank": 2,
                "nearest_limit_side": "up_limit_side",
            },
            {
                "ts_code": "N1.SZ",
                "symbol_name": "Near One",
                "trade_date": "2026-04-03",
                "formal_review_bucket": "near_limit_compare",
                "formal_review_priority_rank": 3,
                "nearest_limit_side": "down_limit_side",
            },
            {
                "ts_code": "N2.SZ",
                "symbol_name": "Near Two",
                "trade_date": "2026-03-30",
                "formal_review_bucket": "near_limit_compare",
                "formal_review_priority_rank": 4,
                "nearest_limit_side": "down_limit_side",
            },
        ]

        shortlist = shortlist_core_malf_snapshot_candidates(rows, limit=3)

        self.assertEqual([row["ts_code"] for row in shortlist], ["R1.SH", "R2.SH", "N1.SZ"])
        self.assertEqual(shortlist[2]["core_snapshot_focus"], "near_limit_compare_backup")
        self.assertEqual(shortlist[2]["core_review_priority_rank"], 3)


if __name__ == "__main__":
    unittest.main()
