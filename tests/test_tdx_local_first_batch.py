from __future__ import annotations

import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ashare_intake_validator import (
    audit_first_batch_front_filter_run,
    audit_first_batch_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
)
from data_sources.tdx_local import (
    apply_malf_snapshot_manual_review_verdicts,
    apply_qualification_record_draft_manual_verdicts,
    audit_formal_front_filter_review_package,
    audit_add_on_price_limit_shortlist_time_alignment,
    audit_first_batch_sample_coverage,
    build_first_batch_sample_package,
    build_default_add_on_price_limit_shortlist_malf_research_prep,
    prepare_malf_snapshot_draft_review,
    prepare_candidate_table_update_audit_when_explicitly_requested,
    prepare_formal_front_filter_review_package,
    prepare_formal_qualification_record_persistence_package_when_explicitly_requested,
    prepare_formal_qualification_record_write_audit,
    prepare_qualification_record_draft_review,
    review_add_on_price_limit_post_label_daily_malf_structure,
    review_add_on_price_limit_post_label_intraday_reopen,
    materialize_default_add_on_price_limit_core_malf_research_bundle,
    rescreen_add_on_price_limit_post_industry_window,
    build_shortlist_malf_research_prep,
    build_shortlist_sample_package,
    default_add_on_price_limit_shortlist_sample_entries,
    update_candidate_table_from_staged_qualification_records_when_explicitly_requested,
    write_candidate_table_to_formal_data_root_when_explicitly_confirmed,
    write_qualification_records_to_staging_when_explicitly_requested,
)
from tachibana_front_filter import run_front_filter


FORBIDDEN_FIELDS = {
    "buy_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "limit_up_strategy",
}


def write_day_records(path: Path, records: list[tuple[int, int, int, int, int, float, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = b"".join(
        struct.pack("<IIIIIfII", trade_date, open_i, high_i, low_i, close_i, amount, volume, 0)
        for trade_date, open_i, high_i, low_i, close_i, amount, volume in records
    )
    path.write_bytes(payload)


class TdxLocalFirstBatchTest(unittest.TestCase):
    def _write_single_staged_qualification_record(self, staging_root: Path) -> Path:
        audit_report = {
            "result": "pass",
            "research_only": True,
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "pass",
            "candidate_table_update_package_prepared": True,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "candidate_table_update_audit_packages": [
                {
                    "candidate_table_update_audit_result": "pass",
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "source_qualification_record_persistence_performed": False,
                    "candidate_table_update_package_prepared": True,
                    "candidate_table_update_performed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }
        write_qualification_records_to_staging_when_explicitly_requested(
            audit_report,
            staging_root=staging_root,
            generated_at="2026-06-30T21:00:00+08:00",
        )
        return staging_root / "qualification-records-v0.1" / "manifest.json"

    def _write_single_staged_candidate_table(self, root: Path) -> Path:
        qualification_manifest = self._write_single_staged_qualification_record(root / "qualification-staging")
        report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
            qualification_record_staging_manifest_path=qualification_manifest,
            candidate_table_staging_root=root / "candidate-staging",
            generated_at="2026-06-30T23:00:00+08:00",
        )
        self.assertEqual(report["result"], "pass")
        return root / "candidate-staging" / "candidate-table-v0.1" / "manifest.json"

    def test_default_add_on_price_limit_shortlist_sample_entries_keeps_core_four_and_backup_two_split(self) -> None:
        entries = default_add_on_price_limit_shortlist_sample_entries()

        self.assertEqual(len(entries), 6)
        self.assertEqual(
            [item["ts_code"] for item in entries],
            [
                "603538.SH",
                "603008.SH",
                "600310.SH",
                "603687.SH",
                "002663.SZ",
                "000899.SZ",
            ],
        )
        self.assertEqual(
            [item["research_priority_group"] for item in entries],
            ["core", "core", "core", "core", "backup", "backup"],
        )
        self.assertEqual(
            [item["formal_review_bucket"] for item in entries],
            [
                "pressure_adjust_reopen",
                "pressure_adjust_reopen",
                "pressure_adjust_reopen",
                "pressure_adjust_reopen",
                "near_limit_compare",
                "near_limit_compare",
            ],
        )

    def test_audit_add_on_price_limit_shortlist_time_alignment_distinguishes_original_blocker_from_updated_daily_availability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            tdx_root = root / "tdx"
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()

            write_day_records(offline_root / "raw" / "sh" / "lday" / "sh600310.day", [
                (20260324, 500, 560, 490, 550, 1000000.0, 100000),
                (20260330, 699, 726, 618, 632, 1400000.0, 140000),
                (20260403, 632, 640, 600, 615, 1500000.0, 150000),
            ])
            write_day_records(tdx_root / "vipdoc" / "sh" / "lday" / "sh600310.day", [
                (20260324, 500, 560, 490, 550, 1000000.0, 100000),
                (20260403, 632, 640, 600, 615, 1500000.0, 150000),
                (20260423, 615, 620, 590, 600, 1600000.0, 160000),
                (20260424, 600, 630, 595, 625, 1700000.0, 170000),
            ])

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
            con.execute("create schema market_meta")
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
            con.execute(
                """
                insert into market_meta.market_meta.industry_block_relation values
                ('sh600310', 'stock', 'industry', 'T010201', 'Hydropower', '2026-04-23', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            report = audit_add_on_price_limit_shortlist_time_alignment(
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=[
                    {
                        "ts_code": "600310.SH",
                        "trade_date": "2026-03-30",
                        "sample_window_start": "2026-03-24",
                        "sample_window_end": "2026-04-03",
                        "research_priority_group": "core",
                    }
                ],
                generated_at="2026-06-30T01:00:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["original_window_blocked_count"], 1)
        self.assertEqual(report["post_label_daily_available_count"], 1)
        item = report["samples"][0]
        self.assertEqual(item["ts_code"], "600310.SH")
        self.assertEqual(item["original_industry_window_status"], "not_overlapping")
        self.assertEqual(item["original_formal_front_filter_issue"], "industry_membership_window_not_overlapping:600310.SH")
        self.assertEqual(item["current_industry_valid_from"], "2026-04-23")
        self.assertEqual(item["updated_daily_source_root"], "tdx_root")
        self.assertEqual(item["updated_daily_last_trade_date"], "2026-04-24")
        self.assertEqual(item["post_label_first_trade_date"], "2026-04-23")
        self.assertEqual(item["time_alignment_next_action"], "action:rescreen_post_industry_effective_window")
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_rescreen_add_on_price_limit_post_industry_window_returns_time_aligned_research_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "tdx"
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()

            write_day_records(tdx_root / "vipdoc" / "sh" / "lday" / "sh600310.day", [
                (20260415, 1000, 1030, 990, 1000, 1000000.0, 100000),
                (20260416, 1000, 1050, 995, 1040, 1100000.0, 110000),
                (20260417, 1040, 1120, 990, 1100, 1200000.0, 120000),
                (20260420, 1100, 1200, 1050, 1180, 1300000.0, 130000),
                (20260421, 1180, 1250, 1120, 1230, 1400000.0, 140000),
                (20260422, 1230, 1280, 1160, 1260, 1500000.0, 150000),
                (20260423, 1240, 1265, 1134, 1160, 1600000.0, 160000),
                (20260424, 1160, 1170, 1120, 1140, 1700000.0, 170000),
            ])

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
            con.execute(
                """
                insert into market_meta.market_meta.instrument_master values
                ('sh600310', 'stock', 'SH', 'Guangxi Energy', '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.execute(
                """
                insert into market_meta.market_meta.industry_block_relation values
                ('sh600310', 'stock', 'industry', 'T010201', 'Hydropower', '2026-04-23', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            report = rescreen_add_on_price_limit_post_industry_window(
                tdx_root=tdx_root,
                duckdb_root=duckdb_root,
                window_start="2026-04-23",
                window_end="2026-04-24",
                ts_codes=["600310.SH"],
                generated_at="2026-06-30T02:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["rescreen_id"], "add_on_price_limit_post_industry_rescreen_v0.1")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["next_action"], "action:review_intraday_price_limit_reopen")

        candidate = report["candidates"][0]
        self.assertEqual(candidate["ts_code"], "600310.SH")
        self.assertEqual(candidate["trade_date"], "2026-04-23")
        self.assertEqual(candidate["industry_window_status"], "overlapping")
        self.assertEqual(candidate["current_industry_valid_from"], "2026-04-23")
        self.assertEqual(candidate["formal_front_filter_status"], "snapshot_pending")
        self.assertEqual(candidate["formal_front_filter_issue"], "pipeline_requires_ready_malf_snapshot")
        self.assertEqual(candidate["snapshot_stub"]["snapshot_quality_status"], "source_missing")
        self.assertIn("post_label_rescreen_is_not_formal_front_filter_ready", candidate["research_boundary_warning"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_rescreen_add_on_price_limit_post_industry_window_uses_duckdb_fast_screen_when_universe_is_unspecified(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "tdx-without-day-files"
            duckdb_root = root / "duckdb"
            duckdb_root.mkdir()

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
            con.execute(
                """
                insert into market_meta.market_meta.instrument_master values
                ('sh600310', 'stock', 'SH', 'Guangxi Energy', '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.execute(
                """
                insert into market_meta.market_meta.industry_block_relation values
                ('sh600310', 'stock', 'industry', 'T010201', 'Hydropower', '2026-04-23', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.executemany(
                """
                insert into market_meta.market_meta.tradability_fact values
                ('sh600310', 'stock', ?, 'tradable', null, 'unit-test', 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("2026-04-15",),
                    ("2026-04-16",),
                    ("2026-04-17",),
                    ("2026-04-20",),
                    ("2026-04-21",),
                    ("2026-04-22",),
                    ("2026-04-23",),
                ],
            )
            con.close()

            con = duckdb.connect(str(duckdb_root / "market_base_day.duckdb"))
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
            con.executemany(
                """
                insert into market_base_day.market_base_day.base_bar values
                ('sh600310', 'stock', 'day', ?, ?, ?, ?, ?, ?, 100000, 1000000.0, 'unit-test', 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("2026-04-15", "2026-04-15", 10.0, 10.3, 9.9, 10.0),
                    ("2026-04-16", "2026-04-16", 10.0, 10.5, 9.95, 10.4),
                    ("2026-04-17", "2026-04-17", 10.4, 11.2, 9.9, 11.0),
                    ("2026-04-20", "2026-04-20", 11.0, 12.0, 10.5, 11.8),
                    ("2026-04-21", "2026-04-21", 11.8, 12.5, 11.2, 12.3),
                    ("2026-04-22", "2026-04-22", 12.3, 12.8, 11.6, 12.6),
                    ("2026-04-23", "2026-04-23", 12.4, 12.65, 11.34, 11.6),
                ],
            )
            con.close()

            report = rescreen_add_on_price_limit_post_industry_window(
                tdx_root=tdx_root,
                duckdb_root=duckdb_root,
                window_start="2026-04-23",
                window_end="2026-06-26",
                generated_at="2026-06-30T02:30:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["source_daily_root"], "duckdb_market_base_day")
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["candidates"][0]["ts_code"], "600310.SH")
        self.assertEqual(report["candidates"][0]["trade_date"], "2026-04-23")
        self.assertEqual(report["candidates"][0]["industry_window_status"], "overlapping")
        self.assertEqual(report["formal_front_filter_ready_count"], 0)

    def test_review_add_on_price_limit_post_label_intraday_reopen_keeps_research_only_gate(self) -> None:
        rescreen_report = {
            "result": "pass",
            "research_only": True,
            "rescreen_id": "add_on_price_limit_post_industry_rescreen_v0.1",
            "window_start": "2026-04-23",
            "window_end": "2026-06-26",
            "candidate_count": 2,
            "candidates": [
                {
                    "ts_code": "603538.SH",
                    "symbol_name": "Meinuohua",
                    "trade_date": "2026-05-11",
                    "limit_up_price": 70.07,
                    "limit_down_price": 57.33,
                    "close_return_pct": -10.0,
                    "runup_pct": 27.03,
                    "nearest_limit_gap_pct": 0.0,
                    "formal_front_filter_status": "snapshot_pending",
                    "snapshot_stub": {"snapshot_quality_status": "source_missing"},
                },
                {
                    "ts_code": "000899.SZ",
                    "symbol_name": "Ganneng",
                    "trade_date": "2026-06-18",
                    "limit_up_price": 12.969,
                    "limit_down_price": 10.611,
                    "close_return_pct": -8.48,
                    "runup_pct": 14.4,
                    "nearest_limit_gap_pct": 0.46,
                    "formal_front_filter_status": "snapshot_pending",
                    "snapshot_stub": {"snapshot_quality_status": "source_missing"},
                },
            ],
        }

        def fake_read_intraday_range(tdx_root: Path, ts_code: str, trade_date: str) -> dict[str, object]:
            if ts_code == "603538.SH":
                return {
                    "result": "source_review_required",
                    "trade_date": trade_date,
                    "intraday_range": {
                        "ts_code": ts_code,
                        "trade_date": trade_date,
                        "bar_count": 48,
                        "intraday_open": 62.0,
                        "intraday_high": 63.5,
                        "intraday_low": 57.33,
                        "intraday_close": 58.2,
                        "source_ref": "fixture:603538.lc5",
                    },
                    "formal_data_write_allowed": False,
                }
            return {
                "result": "source_review_required",
                "trade_date": trade_date,
                "intraday_range": {
                    "ts_code": ts_code,
                    "trade_date": trade_date,
                    "bar_count": 48,
                    "intraday_open": 11.75,
                    "intraday_high": 11.76,
                    "intraday_low": 10.66,
                    "intraday_close": 10.79,
                    "source_ref": "fixture:000899.lc5",
                },
                "formal_data_write_allowed": False,
            }

        with patch("data_sources.tdx_local.first_batch.read_intraday_range", side_effect=fake_read_intraday_range):
            report = review_add_on_price_limit_post_label_intraday_reopen(
                tdx_root=Path("tdx"),
                rescreen_report=rescreen_report,
                generated_at="2026-06-30T03:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["review_id"], "add_on_price_limit_post_label_intraday_reopen_review_v0.1")
        self.assertEqual(report["reviewed_candidate_count"], 2)
        self.assertEqual(report["reopened_after_limit_touch_count"], 1)
        self.assertEqual(report["near_limit_without_touch_count"], 1)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["next_action"], "action:review_malf_structure_evidence")

        by_code = {item["ts_code"]: item for item in report["candidates"]}
        self.assertEqual(by_code["603538.SH"]["intraday_limit_reopen_status"], "reopened_after_limit_touch")
        self.assertEqual(by_code["603538.SH"]["intraday_nearest_limit_gap_pct"], 0.0)
        self.assertEqual(by_code["603538.SH"]["formal_front_filter_status"], "snapshot_pending")
        self.assertEqual(by_code["603538.SH"]["snapshot_stub"]["snapshot_quality_status"], "source_missing")
        self.assertEqual(by_code["000899.SZ"]["intraday_limit_reopen_status"], "near_limit_without_touch")
        self.assertIn("intraday_review_is_not_formal_front_filter_ready", by_code["603538.SH"]["research_boundary_warning"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_review_add_on_price_limit_post_label_intraday_missing_keeps_daily_malf_path_open(self) -> None:
        rescreen_report = {
            "result": "pass",
            "research_only": True,
            "rescreen_id": "add_on_price_limit_post_industry_rescreen_v0.1",
            "window_start": "2026-04-23",
            "window_end": "2026-06-29",
            "candidate_count": 1,
            "candidates": [
                {
                    "ts_code": "600310.SH",
                    "symbol_name": "Guangxi Energy",
                    "trade_date": "2026-06-05",
                    "limit_up_price": 7.92,
                    "limit_down_price": 6.48,
                    "close_return_pct": -9.72,
                    "runup_pct": 19.8,
                    "nearest_limit_gap_pct": 0.02,
                    "formal_front_filter_status": "snapshot_pending",
                    "snapshot_stub": {"snapshot_quality_status": "source_missing"},
                    "research_boundary_warning": [
                        "post_label_rescreen_is_not_formal_front_filter_ready",
                    ],
                }
            ],
        }

        def fake_read_intraday_range(tdx_root: Path, ts_code: str, trade_date: str) -> dict[str, object]:
            return {
                "result": "blocked",
                "reason": "intraday_trade_date_missing",
                "trade_date": trade_date,
                "intraday_range": None,
                "formal_data_write_allowed": False,
            }

        with patch("data_sources.tdx_local.first_batch.read_intraday_range", side_effect=fake_read_intraday_range):
            report = review_add_on_price_limit_post_label_intraday_reopen(
                tdx_root=Path("tdx"),
                rescreen_report=rescreen_report,
                generated_at="2026-06-30T09:30:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["review_scope"], "daily_level_malf_structure_with_optional_intraday_enhancement")
        self.assertEqual(report["reviewed_candidate_count"], 1)
        self.assertEqual(report["blocked_intraday_review_count"], 1)
        self.assertEqual(report["daily_level_malf_review_pending_count"], 1)
        self.assertEqual(report["next_action"], "action:review_daily_level_malf_structure")
        self.assertEqual(report["formal_front_filter_ready_count"], 0)

        candidate = report["candidates"][0]
        self.assertEqual(candidate["intraday_review_result"], "blocked")
        self.assertEqual(candidate["intraday_review_reason"], "intraday_trade_date_missing")
        self.assertEqual(candidate["intraday_limit_reopen_status"], "intraday_optional_evidence_missing")
        self.assertEqual(candidate["daily_level_malf_review_status"], "pending")
        self.assertEqual(candidate["next_action"], "action:review_daily_level_malf_structure")
        self.assertIn("intraday_missing_is_optional_enhancement_only", candidate["research_boundary_warning"])
        self.assertIn("daily_level_malf_structure_review_remains_open", candidate["research_boundary_warning"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_review_add_on_price_limit_post_label_daily_malf_structure_passes_pressure_adjust_candidate(self) -> None:
        intraday_review_report = {
            "result": "pass",
            "research_only": True,
            "review_id": "add_on_price_limit_post_label_intraday_reopen_review_v0.1",
            "review_scope": "daily_level_malf_structure_with_optional_intraday_enhancement",
            "window_start": "2026-04-23",
            "window_end": "2026-06-29",
            "candidates": [
                {
                    "ts_code": "600310.SH",
                    "symbol_name": "Guangxi Energy",
                    "trade_date": "2026-06-05",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "runup_pct": 19.8,
                    "close_return_pct": -9.72,
                    "nearest_limit_gap_pct": 0.02,
                    "proximity_bucket": "at_limit_candidate",
                    "intraday_limit_reopen_status": "intraday_optional_evidence_missing",
                    "daily_level_malf_review_status": "pending",
                    "formal_front_filter_status": "snapshot_pending",
                    "snapshot_stub": {"snapshot_quality_status": "source_missing"},
                    "research_boundary_warning": [
                        "intraday_missing_is_optional_enhancement_only",
                    ],
                }
            ],
        }

        report = review_add_on_price_limit_post_label_daily_malf_structure(
            intraday_review_report,
            generated_at="2026-06-30T10:00:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["review_id"], "add_on_price_limit_post_label_daily_malf_structure_review_v0.1")
        self.assertEqual(report["source_review_id"], "add_on_price_limit_post_label_intraday_reopen_review_v0.1")
        self.assertEqual(report["reviewed_candidate_count"], 1)
        self.assertEqual(report["daily_level_malf_review_pass_count"], 1)
        self.assertEqual(report["daily_level_malf_manual_review_required_count"], 0)
        self.assertEqual(report["daily_level_malf_blocked_count"], 0)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["next_action"], "action:prepare_malf_snapshot_draft_review")

        candidate = report["candidates"][0]
        self.assertEqual(candidate["daily_level_malf_review_status"], "pass")
        self.assertEqual(candidate["daily_level_malf_structure_hint"], "pullback_pressure_adjustment")
        self.assertEqual(candidate["next_action"], "action:prepare_malf_snapshot_draft_review")
        self.assertIn("daily_level_review_is_not_formal_front_filter_ready", candidate["research_boundary_warning"])
        self.assertIn("do_not_generate_trade_from_daily_level_review", candidate["research_boundary_warning"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_review_add_on_price_limit_post_label_daily_malf_structure_requires_manual_review_for_missing_metrics(self) -> None:
        report = review_add_on_price_limit_post_label_daily_malf_structure(
            {
                "result": "pass",
                "research_only": True,
                "review_id": "add_on_price_limit_post_label_intraday_reopen_review_v0.1",
                "window_start": "2026-04-23",
                "window_end": "2026-06-29",
                "candidates": [
                    {
                        "ts_code": "603687.SH",
                        "trade_date": "2026-04-24",
                        "runup_pct": 14.2,
                        "nearest_limit_gap_pct": 0.02,
                        "intraday_limit_reopen_status": "intraday_optional_evidence_missing",
                    },
                    {
                        "ts_code": "002663.SZ",
                        "trade_date": "2026-04-24",
                        "runup_pct": 5.0,
                        "close_return_pct": -0.5,
                        "nearest_limit_gap_pct": 4.5,
                    },
                ],
            },
            generated_at="2026-06-30T10:05:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["daily_level_malf_review_pass_count"], 0)
        self.assertEqual(report["daily_level_malf_manual_review_required_count"], 1)
        self.assertEqual(report["daily_level_malf_blocked_count"], 1)
        self.assertEqual(report["next_action"], "action:hold_for_daily_level_malf_evidence")

        by_code = {item["ts_code"]: item for item in report["candidates"]}
        self.assertEqual(by_code["603687.SH"]["daily_level_malf_review_status"], "manual_review_required")
        self.assertEqual(by_code["603687.SH"]["daily_level_malf_structure_hint"], "structure_unclear")
        self.assertEqual(by_code["002663.SZ"]["daily_level_malf_review_status"], "blocked")
        self.assertEqual(by_code["002663.SZ"]["daily_level_malf_structure_hint"], "not_applicable")
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_prepare_malf_snapshot_draft_review_builds_research_only_package_for_daily_passes(self) -> None:
        daily_review_report = {
            "result": "pass",
            "research_only": True,
            "review_id": "add_on_price_limit_post_label_daily_malf_structure_review_v0.1",
            "window_start": "2026-04-23",
            "window_end": "2026-06-29",
            "candidates": [
                {
                    "ts_code": "600310.SH",
                    "trade_date": "2026-06-05",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "daily_level_malf_review_status": "pass",
                    "daily_level_malf_structure_hint": "pullback_pressure_adjustment",
                    "snapshot_stub": {
                        "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                        "ts_code": "600310.SH",
                        "window_start": "2026-04-23",
                        "window_end": "2026-06-29",
                        "snapshot_quality_status": "source_missing",
                        "evidence_ref": "post_industry_effective_window_rescreen_v0.1",
                    },
                }
            ],
        }

        report = prepare_malf_snapshot_draft_review(
            daily_review_report,
            generated_at="2026-06-30T10:45:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["review_id"], "malf_snapshot_draft_review_prep_v0.1")
        self.assertEqual(report["source_review_id"], "add_on_price_limit_post_label_daily_malf_structure_review_v0.1")
        self.assertEqual(report["draft_review_candidate_count"], 1)
        self.assertEqual(report["draft_review_ready_count"], 1)
        self.assertEqual(report["draft_review_hold_count"], 0)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["next_action"], "action:manual_review_malf_snapshot_drafts")

        candidate = report["candidates"][0]
        self.assertEqual(candidate["snapshot_draft_review_status"], "ready_for_manual_review")
        self.assertEqual(candidate["suggested_snapshot_draft"]["snapshot_quality_status"], "incomplete")
        self.assertEqual(candidate["suggested_snapshot_draft"]["research_prep_status"], "draft_pending_manual_evidence_review")
        self.assertEqual(candidate["suggested_snapshot_draft"]["malf_background"], "pullback")
        self.assertEqual(candidate["suggested_snapshot_draft"]["wave_range_break_fields"], {"pressure_adjustment": True})
        self.assertEqual(candidate["suggested_snapshot_draft"]["draft_front_filter_expected_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertIn("snapshot_quality_status_must_remain_incomplete_until_reviewed", candidate["suggested_snapshot_draft"]["draft_boundary_warning"])
        self.assertEqual(candidate["next_action"], "action:manual_review_malf_snapshot_draft")
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_prepare_malf_snapshot_draft_review_holds_non_pass_or_missing_stub_candidates(self) -> None:
        report = prepare_malf_snapshot_draft_review(
            {
                "result": "blocked",
                "research_only": True,
                "review_id": "add_on_price_limit_post_label_daily_malf_structure_review_v0.1",
                "candidates": [
                    {
                        "ts_code": "603687.SH",
                        "trade_date": "2026-04-24",
                        "daily_level_malf_review_status": "manual_review_required",
                        "daily_level_malf_structure_hint": "structure_unclear",
                    },
                    {
                        "ts_code": "002663.SZ",
                        "trade_date": "2026-04-24",
                        "daily_level_malf_review_status": "pass",
                        "daily_level_malf_structure_hint": "pullback_pressure_adjustment",
                    },
                ],
            },
            generated_at="2026-06-30T10:50:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["draft_review_ready_count"], 0)
        self.assertEqual(report["draft_review_hold_count"], 2)
        self.assertEqual(report["next_action"], "action:hold_for_malf_snapshot_draft_inputs")
        by_code = {item["ts_code"]: item for item in report["candidates"]}
        self.assertEqual(by_code["603687.SH"]["snapshot_draft_review_status"], "hold")
        self.assertEqual(by_code["603687.SH"]["snapshot_draft_review_reason"], "daily_level_malf_review_not_pass")
        self.assertEqual(by_code["002663.SZ"]["snapshot_draft_review_reason"], "snapshot_stub_missing")
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_apply_malf_snapshot_manual_review_verdicts_keeps_approved_drafts_research_only(self) -> None:
        draft_review_report = {
            "result": "pass",
            "research_only": True,
            "review_id": "malf_snapshot_draft_review_prep_v0.1",
            "candidates": [
                {
                    "ts_code": "600310.SH",
                    "trade_date": "2026-06-05",
                    "snapshot_draft_review_status": "ready_for_manual_review",
                    "suggested_snapshot_draft": {
                        "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                        "ts_code": "600310.SH",
                        "window_start": "2026-04-23",
                        "window_end": "2026-06-29",
                        "snapshot_quality_status": "incomplete",
                        "research_prep_status": "draft_pending_manual_evidence_review",
                        "malf_background": "pullback",
                        "wave_range_break_fields": {"pressure_adjustment": True},
                        "draft_front_filter_expected_rule_id": "Q-PRESSURE-ADJUST",
                    },
                }
            ],
        }

        report = apply_malf_snapshot_manual_review_verdicts(
            draft_review_report,
            manual_verdicts={
                "600310.SH": {
                    "manual_review_verdict": "approved_for_formal_front_filter_review",
                    "reviewer_note": "Daily pullback pressure adjustment evidence is coherent.",
                }
            },
            generated_at="2026-06-30T11:30:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["review_id"], "malf_snapshot_manual_review_verdicts_v0.1")
        self.assertEqual(report["manual_reviewed_candidate_count"], 1)
        self.assertEqual(report["manual_review_approved_count"], 1)
        self.assertEqual(report["manual_review_hold_count"], 0)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["next_action"], "action:prepare_formal_front_filter_review_package")

        candidate = report["candidates"][0]
        self.assertEqual(candidate["manual_review_status"], "reviewed_ready_candidate")
        self.assertEqual(candidate["reviewed_snapshot_candidate"]["snapshot_quality_status"], "reviewed_ready_candidate")
        self.assertEqual(candidate["reviewed_snapshot_candidate"]["malf_background"], "pullback")
        self.assertEqual(candidate["reviewed_snapshot_candidate"]["wave_range_break_fields"], {"pressure_adjustment": True})
        self.assertIn("reviewed_candidate_is_not_formal_front_filter_ready", candidate["research_boundary_warning"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_apply_malf_snapshot_manual_review_verdicts_holds_rejected_or_missing_verdicts(self) -> None:
        draft_review_report = {
            "result": "pass",
            "research_only": True,
            "review_id": "malf_snapshot_draft_review_prep_v0.1",
            "candidates": [
                {
                    "ts_code": "603687.SH",
                    "trade_date": "2026-04-24",
                    "snapshot_draft_review_status": "ready_for_manual_review",
                    "suggested_snapshot_draft": {"ts_code": "603687.SH", "snapshot_quality_status": "incomplete"},
                },
                {
                    "ts_code": "000899.SZ",
                    "trade_date": "2026-06-18",
                    "snapshot_draft_review_status": "ready_for_manual_review",
                    "suggested_snapshot_draft": {"ts_code": "000899.SZ", "snapshot_quality_status": "incomplete"},
                },
            ],
        }

        report = apply_malf_snapshot_manual_review_verdicts(
            draft_review_report,
            manual_verdicts={
                "603687.SH": {
                    "manual_review_verdict": "rejected",
                    "reviewer_note": "Structure evidence remains ambiguous.",
                }
            },
            generated_at="2026-06-30T11:35:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["manual_review_approved_count"], 0)
        self.assertEqual(report["manual_review_hold_count"], 2)
        self.assertEqual(report["next_action"], "action:hold_for_manual_malf_snapshot_review")
        by_code = {item["ts_code"]: item for item in report["candidates"]}
        self.assertEqual(by_code["603687.SH"]["manual_review_status"], "rejected")
        self.assertEqual(by_code["603687.SH"]["manual_review_reason"], "manual_review_rejected")
        self.assertEqual(by_code["000899.SZ"]["manual_review_status"], "needs_manual_review")
        self.assertEqual(by_code["000899.SZ"]["manual_review_reason"], "manual_review_verdict_missing")
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_prepare_formal_front_filter_review_package_collects_reviewed_candidates_without_running_filter(self) -> None:
        manual_report = {
            "result": "pass",
            "research_only": True,
            "review_id": "malf_snapshot_manual_review_verdicts_v0.1",
            "candidates": [
                {
                    "ts_code": "600310.SH",
                    "trade_date": "2026-06-05",
                    "manual_review_status": "reviewed_ready_candidate",
                    "reviewed_snapshot_candidate": {
                        "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                        "ts_code": "600310.SH",
                        "window_start": "2026-04-23",
                        "window_end": "2026-06-29",
                        "snapshot_quality_status": "reviewed_ready_candidate",
                        "malf_background": "pullback",
                        "wave_range_break_fields": {"pressure_adjustment": True},
                        "draft_front_filter_expected_rule_id": "Q-PRESSURE-ADJUST",
                    },
                }
            ],
        }

        report = prepare_formal_front_filter_review_package(
            manual_report,
            generated_at="2026-06-30T12:40:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["package_id"], "formal_front_filter_review_package_v0.1")
        self.assertEqual(report["source_review_id"], "malf_snapshot_manual_review_verdicts_v0.1")
        self.assertEqual(report["front_filter_review_input_count"], 1)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["front_filter_execution_allowed"], False)
        self.assertEqual(report["next_action"], "action:run_formal_front_filter_audit_when_explicitly_requested")

        item = report["front_filter_review_inputs"][0]
        self.assertEqual(item["ts_code"], "600310.SH")
        self.assertEqual(item["expected_front_filter_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertEqual(item["snapshot_quality_status"], "reviewed_ready_candidate")
        self.assertIn("python -m tachibana_front_filter --snapshot", item["review_command_preview"])
        self.assertIn("front_filter_review_package_is_not_execution", item["boundary_warning"])
        self.assertNotIn("front_filter_result", item)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_prepare_formal_front_filter_review_package_blocks_when_no_reviewed_candidates(self) -> None:
        report = prepare_formal_front_filter_review_package(
            {
                "result": "blocked",
                "research_only": True,
                "review_id": "malf_snapshot_manual_review_verdicts_v0.1",
                "candidates": [
                    {
                        "ts_code": "603687.SH",
                        "trade_date": "2026-04-24",
                        "manual_review_status": "rejected",
                        "reviewed_snapshot_candidate": None,
                    }
                ],
            },
            generated_at="2026-06-30T12:45:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["front_filter_review_input_count"], 0)
        self.assertEqual(report["front_filter_review_hold_count"], 1)
        self.assertEqual(report["next_action"], "action:hold_for_reviewed_malf_snapshot_candidates")
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_audit_formal_front_filter_review_package_runs_filter_as_audit_only(self) -> None:
        review_package = {
            "result": "pass",
            "research_only": True,
            "package_id": "formal_front_filter_review_package_v0.1",
            "front_filter_review_inputs": [
                {
                    "ts_code": "600310.SH",
                    "trade_date": "2026-06-05",
                    "window_start": "2026-04-23",
                    "window_end": "2026-06-29",
                    "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                    "snapshot_quality_status": "reviewed_ready_candidate",
                    "malf_background": "pullback",
                    "wave_range_break_fields": {"pressure_adjustment": True},
                    "expected_front_filter_rule_id": "Q-PRESSURE-ADJUST",
                    "reviewed_snapshot_candidate": {
                        "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                        "ts_code": "600310.SH",
                        "window_start": "2026-04-23",
                        "window_end": "2026-06-29",
                        "snapshot_quality_status": "reviewed_ready_candidate",
                        "malf_background": "pullback",
                        "wave_range_break_fields": {"pressure_adjustment": True},
                    },
                }
            ],
        }

        report = audit_formal_front_filter_review_package(
            review_package,
            generated_at="2026-06-30T13:20:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["audit_id"], "formal_front_filter_review_audit_v0.1")
        self.assertEqual(report["audited_front_filter_input_count"], 1)
        self.assertEqual(report["formal_front_filter_audit_pass_count"], 1)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["front_filter_execution_allowed"], False)
        self.assertEqual(report["next_action"], "action:prepare_qualification_record_draft_review_when_explicitly_requested")

        item = report["front_filter_audit_results"][0]
        self.assertEqual(item["ts_code"], "600310.SH")
        self.assertEqual(item["formal_front_filter_audit_status"], "pass")
        self.assertEqual(item["qualification_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertEqual(item["expected_front_filter_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertEqual(item["front_filter_result"], "pass")
        self.assertEqual(item["audit_snapshot_quality_status"], "ready")
        self.assertEqual(item["source_snapshot_quality_status"], "reviewed_ready_candidate")
        self.assertIn("temporary_ready_snapshot_used_for_audit_only", item["boundary_warning"])
        self.assertIn("formal_front_filter_audit_is_not_trade_signal", item["boundary_warning"])
        self.assertNotIn("candidate_stage_after", item)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_audit_formal_front_filter_review_package_blocks_missing_review_inputs(self) -> None:
        report = audit_formal_front_filter_review_package(
            {
                "result": "blocked",
                "research_only": True,
                "package_id": "formal_front_filter_review_package_v0.1",
                "front_filter_review_inputs": [],
            },
            generated_at="2026-06-30T13:25:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["audited_front_filter_input_count"], 0)
        self.assertEqual(report["formal_front_filter_audit_pass_count"], 0)
        self.assertEqual(report["next_action"], "action:hold_for_formal_front_filter_review_inputs")
        self.assertIn("front_filter_review_inputs_missing", report["issues"])
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_audit_formal_front_filter_review_package_requires_rule_match(self) -> None:
        review_package = {
            "result": "pass",
            "research_only": True,
            "package_id": "formal_front_filter_review_package_v0.1",
            "front_filter_review_inputs": [
                {
                    "ts_code": "600310.SH",
                    "trade_date": "2026-06-05",
                    "window_start": "2026-04-23",
                    "window_end": "2026-06-29",
                    "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                    "snapshot_quality_status": "reviewed_ready_candidate",
                    "malf_background": "pullback",
                    "wave_range_break_fields": {"pressure_adjustment": True},
                    "expected_front_filter_rule_id": "Q-ALIVE-CLEAN",
                    "reviewed_snapshot_candidate": {
                        "ts_code": "600310.SH",
                        "window_start": "2026-04-23",
                        "window_end": "2026-06-29",
                        "snapshot_quality_status": "reviewed_ready_candidate",
                        "malf_background": "pullback",
                        "wave_range_break_fields": {"pressure_adjustment": True},
                    },
                }
            ],
        }

        report = audit_formal_front_filter_review_package(
            review_package,
            generated_at="2026-06-30T13:30:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["formal_front_filter_audit_pass_count"], 0)
        self.assertEqual(report["formal_front_filter_audit_blocked_count"], 1)
        self.assertEqual(report["next_action"], "action:repair_formal_front_filter_review_inputs")
        item = report["front_filter_audit_results"][0]
        self.assertEqual(item["formal_front_filter_audit_status"], "blocked")
        self.assertEqual(item["qualification_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertIn("front_filter_rule_mismatch:expected=Q-ALIVE-CLEAN:actual=Q-PRESSURE-ADJUST", item["audit_issues"])
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertFalse(any(field in json.dumps(report) for field in FORBIDDEN_FIELDS))

    def test_prepare_qualification_record_draft_review_builds_review_only_package_from_audit_passes(self) -> None:
        review_package = {
            "result": "pass",
            "research_only": True,
            "package_id": "formal_front_filter_review_package_v0.1",
            "front_filter_review_inputs": [
                {
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "ashare_sample_id_suggestion": "ASHARE-ADDON-600310-20260605",
                    "trade_date": "2026-06-05",
                    "window_start": "2026-04-23",
                    "window_end": "2026-06-29",
                    "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                    "snapshot_quality_status": "reviewed_ready_candidate",
                    "malf_background": "pullback",
                    "wave_range_break_fields": {"pressure_adjustment": True},
                    "expected_front_filter_rule_id": "Q-PRESSURE-ADJUST",
                    "reviewed_snapshot_candidate": {
                        "malf_snapshot_ref": "MALF-SNAP-600310.SH-2026-04-23-2026-06-29-RESEARCH-PREP-v0.1",
                        "ts_code": "600310.SH",
                        "window_start": "2026-04-23",
                        "window_end": "2026-06-29",
                        "snapshot_quality_status": "reviewed_ready_candidate",
                        "malf_background": "pullback",
                        "wave_range_break_fields": {"pressure_adjustment": True},
                    },
                }
            ],
        }
        audit_report = audit_formal_front_filter_review_package(
            review_package,
            generated_at="2026-06-30T13:45:00+08:00",
        )

        report = prepare_qualification_record_draft_review(
            audit_report,
            generated_at="2026-06-30T14:00:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["package_id"], "qualification_record_draft_review_package_v0.1")
        self.assertEqual(report["source_audit_id"], "formal_front_filter_review_audit_v0.1")
        self.assertEqual(report["qualification_record_draft_review_input_count"], 1)
        self.assertEqual(report["qualification_record_draft_review_hold_count"], 0)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertEqual(report["next_action"], "action:manual_review_qualification_record_drafts")

        item = report["qualification_record_draft_review_inputs"][0]
        self.assertEqual(item["qualification_record_draft_review_status"], "ready_for_manual_review")
        self.assertEqual(item["ts_code"], "600310.SH")
        self.assertEqual(item["symbol_name"], "桂东电力")
        self.assertEqual(item["ashare_sample_id"], "ASHARE-ADDON-600310-20260605")
        self.assertEqual(item["qualification_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertEqual(item["rhythm_meaning"], "limited")
        self.assertEqual(item["tachibana_applicability"], "conditional")
        self.assertEqual(item["source_front_filter_audit_status"], "pass")
        self.assertEqual(item["source_front_filter_result"], "pass")
        self.assertEqual(item["source_record_status"], "draft")
        self.assertFalse(item["qualification_record_write_allowed"])
        self.assertFalse(item["candidate_table_update_allowed"])
        self.assertFalse(item["trading_layer_read_allowed"])
        self.assertIn("qualification_record_draft_review_is_not_formal_record", item["boundary_warning"])
        self.assertIn("do_not_open_trade_or_backtest_from_qualification_draft", item["boundary_warning"])
        self.assertEqual(item["next_action"], "action:manual_review_qualification_record_draft")
        self.assertNotIn("action:fill_candidate_table", json.dumps(report, ensure_ascii=False))
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report, ensure_ascii=False) for field in FORBIDDEN_FIELDS))

    def test_prepare_qualification_record_draft_review_holds_blocked_or_missing_audit_results(self) -> None:
        report = prepare_qualification_record_draft_review(
            {
                "result": "blocked",
                "research_only": True,
                "audit_id": "formal_front_filter_review_audit_v0.1",
                "front_filter_audit_results": [
                    {
                        "ts_code": "600310.SH",
                        "formal_front_filter_audit_status": "blocked",
                        "front_filter_result": "pass",
                        "qualification_rule_id": "Q-PRESSURE-ADJUST",
                        "audit_issues": ["front_filter_rule_mismatch:expected=Q-ALIVE-CLEAN:actual=Q-PRESSURE-ADJUST"],
                    }
                ],
            },
            generated_at="2026-06-30T14:05:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["qualification_record_draft_review_input_count"], 0)
        self.assertEqual(report["qualification_record_draft_review_hold_count"], 1)
        self.assertEqual(report["next_action"], "action:hold_for_formal_front_filter_audit_passes")
        self.assertEqual(
            report["held_audit_results"][0]["qualification_record_draft_review_reason"],
            "formal_front_filter_audit_not_pass",
        )
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in json.dumps(report, ensure_ascii=False) for field in FORBIDDEN_FIELDS))

    def test_apply_qualification_record_draft_manual_verdicts_records_approved_review_without_writing_record(self) -> None:
        draft_review_report = {
            "result": "pass",
            "research_only": True,
            "package_id": "qualification_record_draft_review_package_v0.1",
            "qualification_record_draft_review_inputs": [
                {
                    "qualification_record_draft_review_status": "ready_for_manual_review",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "qualification_record_write_allowed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }

        report = apply_qualification_record_draft_manual_verdicts(
            draft_review_report,
            manual_verdicts={
                "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1": {
                    "manual_review_verdict": "approved_for_formal_record_write_audit",
                    "reviewer_note": "Qualification draft evidence is coherent for write-audit preparation.",
                }
            },
            generated_at="2026-06-30T14:30:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["review_id"], "qualification_record_draft_manual_verdicts_v0.1")
        self.assertEqual(report["manual_reviewed_draft_count"], 1)
        self.assertEqual(report["manual_review_approved_count"], 1)
        self.assertEqual(report["manual_review_hold_count"], 0)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertEqual(report["next_action"], "action:prepare_formal_qualification_record_write_audit_when_explicitly_requested")

        item = report["qualification_record_draft_manual_verdicts"][0]
        self.assertEqual(item["qualification_record_manual_review_status"], "approved_for_formal_record_write_audit_candidate")
        self.assertEqual(item["manual_review_verdict"], "approved_for_formal_record_write_audit")
        self.assertEqual(item["qualification_record_id"], "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1")
        self.assertEqual(item["qualification_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertFalse(item["qualification_record_write_allowed"])
        self.assertFalse(item["candidate_table_update_allowed"])
        self.assertFalse(item["trading_layer_read_allowed"])
        self.assertIn("manual_verdict_is_not_qualification_record_write", item["boundary_warning"])
        self.assertIn("formal_write_audit_required_before_record_write", item["boundary_warning"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("action:write_qualification_record", payload)
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_apply_qualification_record_draft_manual_verdicts_holds_missing_or_rejected_reviews(self) -> None:
        draft_review_report = {
            "result": "pass",
            "research_only": True,
            "package_id": "qualification_record_draft_review_package_v0.1",
            "qualification_record_draft_review_inputs": [
                {
                    "qualification_record_draft_review_status": "ready_for_manual_review",
                    "qualification_record_id": "ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "603687.SH",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
                {
                    "qualification_record_draft_review_status": "ready_for_manual_review",
                    "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "000899.SZ",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
            ],
        }

        report = apply_qualification_record_draft_manual_verdicts(
            draft_review_report,
            manual_verdicts={
                "ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1": {
                    "manual_review_verdict": "needs_revision",
                    "reviewer_note": "Record draft needs more explicit evidence notes.",
                }
            },
            generated_at="2026-06-30T14:35:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["manual_review_approved_count"], 0)
        self.assertEqual(report["manual_review_hold_count"], 2)
        self.assertEqual(report["next_action"], "action:hold_for_manual_qualification_record_draft_review")
        by_id = {item["qualification_record_id"]: item for item in report["qualification_record_draft_manual_verdicts"]}
        self.assertEqual(
            by_id["ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1"]["qualification_record_manual_review_status"],
            "needs_revision",
        )
        self.assertEqual(
            by_id["ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1"]["qualification_record_manual_review_reason"],
            "manual_review_verdict_missing",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("action:write_qualification_record", payload)
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_prepare_formal_qualification_record_write_audit_collects_approved_candidates_without_writing_record(self) -> None:
        manual_review_report = {
            "result": "pass",
            "research_only": True,
            "review_id": "qualification_record_draft_manual_verdicts_v0.1",
            "qualification_record_draft_manual_verdicts": [
                {
                    "qualification_record_manual_review_status": "approved_for_formal_record_write_audit_candidate",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "manual_review_verdict": "approved_for_formal_record_write_audit",
                    "manual_review_note": "Qualification draft evidence is coherent for write-audit preparation.",
                    "qualification_record_write_allowed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }

        report = prepare_formal_qualification_record_write_audit(
            manual_review_report,
            generated_at="2026-06-30T15:30:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["audit_id"], "formal_qualification_record_write_audit_v0.1")
        self.assertEqual(report["source_review_id"], "qualification_record_draft_manual_verdicts_v0.1")
        self.assertEqual(report["formal_record_write_audit_candidate_count"], 1)
        self.assertEqual(report["formal_record_write_audit_hold_count"], 0)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertEqual(
            report["next_action"],
            "action:prepare_formal_qualification_record_persistence_package_when_explicitly_requested",
        )

        item = report["formal_record_write_audit_candidates"][0]
        self.assertEqual(item["formal_record_write_audit_status"], "pass")
        self.assertEqual(item["qualification_record_id"], "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1")
        self.assertEqual(item["qualification_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertEqual(item["source_manual_review_status"], "approved_for_formal_record_write_audit_candidate")
        self.assertFalse(item["qualification_record_write_allowed"])
        self.assertFalse(item["candidate_table_update_allowed"])
        self.assertFalse(item["trading_layer_read_allowed"])
        self.assertIn("write_audit_is_not_record_write", item["boundary_warning"])
        self.assertIn("explicit_commit_layer_required_before_formal_record_write", item["boundary_warning"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("action:write_qualification_record", payload)
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_prepare_formal_qualification_record_write_audit_holds_unapproved_or_missing_candidates(self) -> None:
        manual_review_report = {
            "result": "blocked",
            "research_only": True,
            "review_id": "qualification_record_draft_manual_verdicts_v0.1",
            "qualification_record_draft_manual_verdicts": [
                {
                    "qualification_record_manual_review_status": "needs_revision",
                    "qualification_record_id": "ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "603687.SH",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
                {
                    "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "000899.SZ",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
            ],
        }

        report = prepare_formal_qualification_record_write_audit(
            manual_review_report,
            generated_at="2026-06-30T15:35:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["formal_record_write_audit_candidate_count"], 0)
        self.assertEqual(report["formal_record_write_audit_hold_count"], 2)
        self.assertEqual(report["next_action"], "action:hold_for_formal_qualification_record_write_audit_candidates")
        by_id = {item["qualification_record_id"]: item for item in report["held_manual_review_results"]}
        self.assertEqual(
            by_id["ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1"]["formal_record_write_audit_reason"],
            "manual_review_not_approved_for_formal_record_write_audit",
        )
        self.assertEqual(
            by_id["ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1"]["formal_record_write_audit_reason"],
            "manual_review_not_approved_for_formal_record_write_audit",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertNotIn("action:write_qualification_record", payload)
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_prepare_formal_qualification_record_persistence_package_when_explicitly_requested_prepares_package_without_writing_record(self) -> None:
        write_audit_report = {
            "result": "pass",
            "research_only": True,
            "audit_id": "formal_qualification_record_write_audit_v0.1",
            "formal_record_write_audit_candidates": [
                {
                    "formal_record_write_audit_status": "pass",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "manual_review_verdict": "approved_for_formal_record_write_audit",
                    "formal_record_write_audit_reason": "manual_review_approved_and_boundary_gates_closed",
                    "qualification_record_write_allowed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }

        report = prepare_formal_qualification_record_persistence_package_when_explicitly_requested(
            write_audit_report,
            generated_at="2026-06-30T16:55:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["package_id"], "formal_qualification_record_persistence_package_v0.1")
        self.assertEqual(report["source_audit_id"], "formal_qualification_record_write_audit_v0.1")
        self.assertEqual(report["qualification_record_persistence_package_count"], 1)
        self.assertEqual(report["held_qualification_record_persistence_count"], 0)
        self.assertEqual(report["next_action"], "action:prepare_candidate_table_update_audit_when_explicitly_requested")
        self.assertTrue(report["qualification_record_persistence_package_prepared"])
        self.assertFalse(report["qualification_record_persistence_performed"])
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_front_filter_ready_count"])

        record = report["qualification_record_persistence_packages"][0]
        self.assertEqual(record["qualification_record_status"], "formal_record_ready_for_persistence")
        self.assertEqual(record["qualification_record_id"], "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1")
        self.assertEqual(record["qualification_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertEqual(record["source_formal_record_write_audit_status"], "pass")
        self.assertEqual(record["persistence_package_prepared_at"], "2026-06-30T16:55:00+08:00")
        self.assertFalse(record["qualification_record_persistence_performed"])
        self.assertFalse(record["qualification_record_write_allowed"])
        self.assertFalse(record["candidate_table_update_allowed"])
        self.assertFalse(record["trading_layer_read_allowed"])
        self.assertIn("persistence_package_is_not_record_write", record["boundary_warning"])
        self.assertIn("explicit_persistence_writer_required_before_record_write", record["boundary_warning"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("formal_record_committed", payload)
        self.assertNotIn("committed_qualification_records", payload)
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertNotIn("trade_accept", payload)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_prepare_formal_qualification_record_persistence_package_when_explicitly_requested_holds_missing_or_blocked_audit_candidates(self) -> None:
        write_audit_report = {
            "result": "blocked",
            "research_only": True,
            "audit_id": "formal_qualification_record_write_audit_v0.1",
            "formal_record_write_audit_candidates": [
                {
                    "formal_record_write_audit_status": "hold",
                    "qualification_record_id": "ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "603687.SH",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
                {
                    "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "000899.SZ",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
            ],
        }

        report = prepare_formal_qualification_record_persistence_package_when_explicitly_requested(
            write_audit_report,
            generated_at="2026-06-30T17:00:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["qualification_record_persistence_package_prepared"])
        self.assertFalse(report["qualification_record_persistence_performed"])
        self.assertEqual(report["qualification_record_persistence_package_count"], 0)
        self.assertEqual(report["held_qualification_record_persistence_count"], 2)
        self.assertEqual(report["next_action"], "action:hold_for_formal_qualification_record_write_audit_passes")
        by_id = {item["qualification_record_id"]: item for item in report["held_qualification_record_persistence_items"]}
        self.assertEqual(
            by_id["ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1"]["qualification_record_persistence_reason"],
            "formal_record_write_audit_not_pass",
        )
        self.assertEqual(
            by_id["ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1"]["qualification_record_persistence_reason"],
            "formal_record_write_audit_not_pass",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("formal_record_committed", payload)
        self.assertNotIn("committed_qualification_records", payload)
        self.assertFalse(report["qualification_record_write_allowed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_prepare_candidate_table_update_audit_when_explicitly_requested_prepares_audit_package_without_updating_table(self) -> None:
        persistence_report = {
            "result": "pass",
            "research_only": True,
            "package_id": "formal_qualification_record_persistence_package_v0.1",
            "qualification_record_persistence_package_prepared": True,
            "qualification_record_persistence_performed": False,
            "qualification_record_persistence_packages": [
                {
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "qualification_record_persistence_performed": False,
                    "qualification_record_write_allowed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }

        report = prepare_candidate_table_update_audit_when_explicitly_requested(
            persistence_report,
            generated_at="2026-06-30T19:30:00+08:00",
        )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["audit_id"], "candidate_table_update_audit_package_v0.1")
        self.assertEqual(report["source_package_id"], "formal_qualification_record_persistence_package_v0.1")
        self.assertEqual(report["candidate_table_update_audit_result"], "pass")
        self.assertTrue(report["candidate_table_update_package_prepared"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["candidate_table_update_audit_candidate_count"], 1)
        self.assertEqual(report["held_candidate_table_update_audit_count"], 0)
        self.assertEqual(report["next_action"], "action:hold_for_explicit_candidate_table_update_writer")

        item = report["candidate_table_update_audit_packages"][0]
        self.assertEqual(item["candidate_table_update_audit_result"], "pass")
        self.assertEqual(item["qualification_record_status"], "formal_record_ready_for_persistence")
        self.assertEqual(item["candidate_table_update_audited_at"], "2026-06-30T19:30:00+08:00")
        self.assertTrue(item["candidate_table_update_package_prepared"])
        self.assertFalse(item["candidate_table_update_performed"])
        self.assertFalse(item["candidate_table_update_allowed"])
        self.assertFalse(item["trading_layer_read_allowed"])
        self.assertIn("candidate_table_update_audit_is_not_table_write", item["boundary_warning"])
        self.assertIn("candidate_table_update_writer_requires_separate_explicit_call", item["boundary_warning"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("candidate_table_update_audit_allowed", payload)
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_prepare_candidate_table_update_audit_when_explicitly_requested_holds_bad_or_forbidden_packages(self) -> None:
        persistence_report = {
            "result": "blocked",
            "research_only": True,
            "package_id": "formal_qualification_record_persistence_package_v0.1",
            "qualification_record_persistence_package_prepared": True,
            "qualification_record_persistence_packages": [
                {
                    "qualification_record_status": "draft_only",
                    "qualification_record_id": "ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "603687.SH",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
                {
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "000899.SZ",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "trade_accept": True,
                },
            ],
        }

        report = prepare_candidate_table_update_audit_when_explicitly_requested(
            persistence_report,
            generated_at="2026-06-30T19:35:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["candidate_table_update_audit_result"], "blocked")
        self.assertFalse(report["candidate_table_update_package_prepared"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertEqual(report["candidate_table_update_audit_candidate_count"], 0)
        self.assertEqual(report["held_candidate_table_update_audit_count"], 2)
        self.assertEqual(report["next_action"], "action:repair_candidate_table_update_audit_inputs")
        by_id = {item["qualification_record_id"]: item for item in report["held_candidate_table_update_audit_items"]}
        self.assertEqual(
            by_id["ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1"]["candidate_table_update_audit_reason"],
            "qualification_record_not_ready_for_persistence",
        )
        self.assertEqual(
            by_id["ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1"]["candidate_table_update_audit_reason"],
            "candidate_table_update_forbidden_output_field_present",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("candidate_table_update_audit_allowed", payload)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_qualification_records_to_staging_when_explicitly_requested_writes_records_then_manifest(self) -> None:
        audit_report = {
            "result": "pass",
            "research_only": True,
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "pass",
            "candidate_table_update_package_prepared": True,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "candidate_table_update_audit_packages": [
                {
                    "candidate_table_update_audit_result": "pass",
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "source_qualification_record_persistence_performed": False,
                    "candidate_table_update_package_prepared": True,
                    "candidate_table_update_performed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            staging_root = Path(tmp) / "staging"
            report = write_qualification_records_to_staging_when_explicitly_requested(
                audit_report,
                staging_root=staging_root,
                generated_at="2026-06-30T21:00:00+08:00",
            )
            manifest_path = staging_root / "qualification-records-v0.1" / "manifest.json"
            record_path = (
                staging_root
                / "qualification-records-v0.1"
                / "records"
                / "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            tmp_files = list((staging_root / "qualification-records-v0.1").rglob("*.tmp"))

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["qualification_record_persistence_performed"])
        self.assertEqual(report["qualification_record_persistence_target"], "staging")
        self.assertEqual(report["qualification_record_staging_count"], 1)
        self.assertEqual(report["held_qualification_record_staging_count"], 0)
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:hold_for_candidate_table_update_staging_review")
        self.assertEqual(manifest["manifest_id"], "qualification_record_staging_manifest_v0.1")
        self.assertEqual(manifest["source_audit_id"], "candidate_table_update_audit_package_v0.1")
        self.assertEqual(manifest["qualification_record_count"], 1)
        self.assertEqual(
            manifest["record_files"],
            ["records/ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1.json"],
        )
        self.assertTrue(manifest["qualification_record_persistence_performed"])
        self.assertEqual(manifest["qualification_record_persistence_target"], "staging")
        self.assertFalse(manifest["candidate_table_update_performed"])
        self.assertFalse(manifest["candidate_table_update_allowed"])
        self.assertFalse(manifest["trading_layer_read_allowed"])
        self.assertFalse(manifest["signal_generation_allowed"])
        self.assertFalse(manifest["backtest_execution_allowed"])
        self.assertEqual(record["qualification_record_status"], "formal_record_persisted_to_staging")
        self.assertEqual(
            record["qualification_record_id"],
            "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
        )
        self.assertEqual(record["qualification_record_persisted_at"], "2026-06-30T21:00:00+08:00")
        self.assertFalse(record["candidate_table_update_performed"])
        self.assertFalse(record["candidate_table_update_allowed"])
        self.assertFalse(record["trading_layer_read_allowed"])
        self.assertFalse(tmp_files)
        payload = json.dumps({"report": report, "manifest": manifest, "record": record}, ensure_ascii=False)
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_qualification_records_to_staging_when_explicitly_requested_blocks_bad_audit_report(self) -> None:
        audit_report = {
            "result": "blocked",
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "blocked",
            "candidate_table_update_package_prepared": False,
            "candidate_table_update_performed": False,
            "candidate_table_update_audit_packages": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            staging_root = Path(tmp) / "staging"
            report = write_qualification_records_to_staging_when_explicitly_requested(
                audit_report,
                staging_root=staging_root,
                generated_at="2026-06-30T21:05:00+08:00",
            )
            self.assertFalse(staging_root.exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["qualification_record_persistence_performed"])
        self.assertIn("candidate_table_update_audit_not_pass", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_write_qualification_records_to_staging_when_explicitly_requested_blocks_forbidden_fields_without_files(self) -> None:
        audit_report = {
            "result": "pass",
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "pass",
            "candidate_table_update_package_prepared": True,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "candidate_table_update_audit_packages": [
                {
                    "candidate_table_update_audit_result": "pass",
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "000899.SZ",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "candidate_table_update_package_prepared": True,
                    "candidate_table_update_performed": False,
                    "trade_accept": True,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            staging_root = Path(tmp) / "staging"
            report = write_qualification_records_to_staging_when_explicitly_requested(
                audit_report,
                staging_root=staging_root,
                generated_at="2026-06-30T21:10:00+08:00",
            )
            self.assertFalse(staging_root.exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["qualification_record_persistence_performed"])
        self.assertEqual(report["held_qualification_record_staging_count"], 1)
        self.assertEqual(
            report["held_qualification_record_staging_items"][0]["qualification_record_persistence_reason"],
            "qualification_record_staging_forbidden_output_field_present",
        )
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("trade_accept", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_writes_jsonl_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_staged_qualification_record(root / "qualification-staging")
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:00:00+08:00",
            )
            table_root = candidate_staging_root / "candidate-table-v0.1"
            manifest = json.loads((table_root / "manifest.json").read_text(encoding="utf-8"))
            rows = [
                json.loads(line)
                for line in (table_root / "candidate-table-draft.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            tmp_dirs = list(candidate_staging_root.glob("candidate-table-v0.1.__tmp__"))

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["candidate_table_update_performed"])
        self.assertEqual(report["candidate_table_update_target"], "staging")
        self.assertEqual(report["candidate_table_row_count"], 1)
        self.assertEqual(report["candidate_table_deduplicated_existing_row_count"], 0)
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_staged_candidate_table_before_formal_data_root_write")
        self.assertEqual(manifest["manifest_id"], "candidate_table_staging_manifest_v0.1")
        self.assertEqual(manifest["source_qualification_record_manifest_id"], "qualification_record_staging_manifest_v0.1")
        self.assertEqual(manifest["candidate_table_row_count"], 1)
        self.assertEqual(manifest["candidate_table_files"], ["candidate-table-draft.jsonl"])
        self.assertTrue(manifest["candidate_table_update_performed"])
        self.assertEqual(manifest["candidate_table_update_target"], "staging")
        self.assertFalse(manifest["candidate_table_update_allowed"])
        self.assertFalse(manifest["trading_layer_read_allowed"])
        self.assertFalse(manifest["signal_generation_allowed"])
        self.assertFalse(manifest["backtest_execution_allowed"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["candidate_table_row_id"],
            "CANDIDATE-TABLE-ROW::ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
        )
        self.assertEqual(rows[0]["candidate_table_row_status"], "staged_candidate_table_row")
        self.assertEqual(rows[0]["qualification_record_id"], "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1")
        self.assertEqual(rows[0]["candidate_table_updated_at"], "2026-06-30T22:00:00+08:00")
        self.assertTrue(rows[0]["candidate_table_update_performed"])
        self.assertEqual(rows[0]["candidate_table_update_target"], "staging")
        self.assertFalse(rows[0]["candidate_table_update_allowed"])
        self.assertFalse(rows[0]["trading_layer_read_allowed"])
        self.assertFalse(rows[0]["signal_generation_allowed"])
        self.assertFalse(rows[0]["backtest_execution_allowed"])
        self.assertFalse(tmp_dirs)
        payload = json.dumps({"report": report, "manifest": manifest, "rows": rows}, ensure_ascii=False)
        self.assertNotIn("action:read_trading_layer", payload)
        self.assertNotIn("action:generate_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_bad_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "qualification-staging" / "qualification-records-v0.1" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "manifest_id": "bad_manifest",
                        "qualification_record_persistence_performed": True,
                        "qualification_record_persistence_target": "staging",
                        "candidate_table_update_performed": False,
                        "candidate_table_update_allowed": False,
                        "record_files": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:05:00+08:00",
            )

            self.assertFalse((candidate_staging_root / "candidate-table-v0.1").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertIn("qualification_record_staging_manifest_invalid", report["issues"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_forbidden_record_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qualification_root = root / "qualification-staging"
            manifest_path = self._write_single_staged_qualification_record(qualification_root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record_path = qualification_root / "qualification-records-v0.1" / manifest["record_files"][0]
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["trade_accept"] = True
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:10:00+08:00",
            )

            self.assertFalse((candidate_staging_root / "candidate-table-v0.1").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertEqual(report["held_candidate_table_update_count"], 1)
        self.assertEqual(
            report["held_candidate_table_update_items"][0]["candidate_table_update_reason"],
            "candidate_table_forbidden_output_field_present",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("trade_accept", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_duplicate_record_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qualification_root = root / "qualification-staging"
            manifest_path = self._write_single_staged_qualification_record(qualification_root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            source_record = qualification_root / "qualification-records-v0.1" / manifest["record_files"][0]
            duplicate_record = qualification_root / "qualification-records-v0.1" / "records" / "duplicate.json"
            duplicate_record.write_text(source_record.read_text(encoding="utf-8"), encoding="utf-8")
            manifest["record_files"].append("records/duplicate.json")
            manifest["qualification_record_count"] = 2
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:15:00+08:00",
            )

            self.assertFalse((candidate_staging_root / "candidate-table-v0.1").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertIn("candidate_table_duplicate_qualification_record_id", report["issues"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_rewrites_idempotently_without_tmp_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_staged_qualification_record(root / "qualification-staging")
            candidate_staging_root = root / "candidate-staging"

            first_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:20:00+08:00",
            )
            second_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:25:00+08:00",
            )
            table_root = candidate_staging_root / "candidate-table-v0.1"
            manifest = json.loads((table_root / "manifest.json").read_text(encoding="utf-8"))
            tmp_dirs = list(candidate_staging_root.glob("candidate-table-v0.1.__tmp__"))
            table_root_exists = table_root.exists()

        self.assertEqual(first_report["result"], "pass")
        self.assertEqual(second_report["result"], "pass")
        self.assertTrue(table_root_exists)
        self.assertEqual(manifest["candidate_table_row_count"], 1)
        self.assertFalse(tmp_dirs)

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_existing_row_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_staged_qualification_record(root / "qualification-staging")
            candidate_staging_root = root / "candidate-staging"

            first_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:30:00+08:00",
            )
            table_root = candidate_staging_root / "candidate-table-v0.1"
            table_file = table_root / "candidate-table-draft.jsonl"
            rows = [json.loads(line) for line in table_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            rows[0]["qualification_rule_id"] = "Q-CONFLICT"
            table_file.write_text(json.dumps(rows[0], ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            second_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:35:00+08:00",
            )
            rows_after = [
                json.loads(line)
                for line in table_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(first_report["result"], "pass")
        self.assertEqual(second_report["result"], "blocked")
        self.assertFalse(second_report["candidate_table_update_performed"])
        self.assertIn("candidate_table_merge_conflict", second_report["issues"])
        self.assertEqual(rows_after[0]["qualification_rule_id"], "Q-CONFLICT")

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_writes_formal_jsonl_with_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            formal_data_root = root / "formal-data"
            live_root = formal_data_root / "ashare" / "candidate-table-v0.1"
            live_root.mkdir(parents=True)
            (live_root / "candidate-table.jsonl").write_text('{"old": true}\n', encoding="utf-8")
            (live_root / "manifest.json").write_text('{"manifest_id": "old"}\n', encoding="utf-8")

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:10:00+08:00",
            )
            manifest = json.loads((live_root / "manifest.json").read_text(encoding="utf-8"))
            rows = [
                json.loads(line)
                for line in (live_root / "candidate-table.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            backups = list((formal_data_root / "ashare").glob("candidate-table-v0.1.backup.*"))
            backup_file_exists = bool(backups) and (backups[0] / "candidate-table.jsonl").exists()
            tmp_exists = (formal_data_root / "ashare" / "candidate-table-v0.1.__tmp__").exists()

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["candidate_table_update_performed"])
        self.assertEqual(report["candidate_table_update_target"], "formal_data_root")
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_formal_candidate_table_before_trading_layer_audit")
        self.assertEqual(manifest["manifest_id"], "candidate_table_formal_manifest_v0.1")
        self.assertEqual(manifest["candidate_table_row_count"], 1)
        self.assertEqual(manifest["candidate_table_file"], "candidate-table.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidate_table_update_target"], "formal_data_root")
        self.assertTrue(rows[0]["candidate_table_update_performed"])
        self.assertFalse(rows[0]["trading_layer_read_allowed"])
        self.assertEqual(len(backups), 1)
        self.assertTrue(backup_file_exists)
        self.assertFalse(tmp_exists)
        payload = json.dumps({"report": report, "manifest": manifest, "rows": rows}, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_without_confirm_before_reading_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_manifest = root / "missing" / "manifest.json"
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=missing_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=False,
                generated_at="2026-06-30T23:15:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("confirm_formal_write_required", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["trading_layer_read_allowed"])

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_bad_manifest_without_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = root / "candidate-staging" / "candidate-table-v0.1" / "manifest.json"
            staging_manifest.parent.mkdir(parents=True)
            staging_manifest.write_text(json.dumps({"manifest_id": "bad"}, ensure_ascii=False), encoding="utf-8")
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:20:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_staging_manifest_invalid", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_forbidden_staging_row_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            table_root = staging_manifest.parent
            rows = [
                json.loads(line)
                for line in (table_root / "candidate-table-draft.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rows[0]["buy_signal"] = True
            (table_root / "candidate-table-draft.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:25:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("buy_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_rolls_back_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            formal_data_root = root / "formal-data"
            live_root = formal_data_root / "ashare" / "candidate-table-v0.1"
            live_root.mkdir(parents=True)
            (live_root / "candidate-table.jsonl").write_text('{"old": true}\n', encoding="utf-8")
            (live_root / "manifest.json").write_text('{"manifest_id": "old"}\n', encoding="utf-8")

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:30:00+08:00",
                simulate_failure_step="after_backup",
            )
            old_payload = (live_root / "candidate-table.jsonl").read_text(encoding="utf-8")
            backups = list((formal_data_root / "ashare").glob("candidate-table-v0.1.backup.*"))
            backup_file_exists = bool(backups) and (backups[0] / "candidate-table.jsonl").exists()
            tmp_exists = (formal_data_root / "ashare" / "candidate-table-v0.1.__tmp__").exists()

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_write_failed_after_backup", report["issues"])
        self.assertEqual(old_payload, '{"old": true}\n')
        self.assertEqual(len(backups), 1)
        self.assertTrue(backup_file_exists)
        self.assertFalse(tmp_exists)
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["trading_layer_read_allowed"])

    def test_build_default_add_on_price_limit_shortlist_malf_research_prep_materializes_canonical_shortlist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            candidate_windows = {
                ("sh", "603538"): [
                    (20260324, 4000, 4050, 3980, 4030, 1000000.0, 100000),
                    (20260325, 4030, 4100, 4020, 4080, 1100000.0, 110000),
                    (20260326, 4080, 4180, 4060, 4160, 1200000.0, 120000),
                    (20260330, 4160, 4210, 4050, 4070, 1300000.0, 130000),
                    (20260401, 4070, 4172, 3681, 3985, 1400000.0, 140000),
                    (20260403, 3985, 4020, 3900, 3950, 1500000.0, 150000),
                ],
                ("sh", "603008"): [
                    (20260324, 1600, 1620, 1580, 1590, 1000000.0, 100000),
                    (20260325, 1590, 1610, 1560, 1570, 1100000.0, 110000),
                    (20260326, 1570, 1590, 1540, 1540, 1200000.0, 120000),
                    (20260327, 1540, 1560, 1490, 1510, 1300000.0, 130000),
                    (20260330, 1510, 1577, 1467, 1518, 1400000.0, 140000),
                    (20260403, 1518, 1530, 1490, 1500, 1500000.0, 150000),
                ],
                ("sh", "600310"): [
                    (20260324, 500, 560, 490, 550, 1000000.0, 100000),
                    (20260325, 550, 610, 540, 600, 1100000.0, 110000),
                    (20260326, 600, 650, 590, 640, 1200000.0, 120000),
                    (20260327, 640, 660, 620, 660, 1300000.0, 130000),
                    (20260330, 699, 726, 618, 632, 1400000.0, 140000),
                    (20260403, 632, 640, 600, 615, 1500000.0, 150000),
                ],
                ("sh", "603687"): [
                    (20260324, 1700, 1710, 1660, 1670, 1000000.0, 100000),
                    (20260325, 1670, 1680, 1610, 1620, 1100000.0, 110000),
                    (20260326, 1620, 1635, 1560, 1590, 1200000.0, 120000),
                    (20260327, 1590, 1647, 1485, 1563, 1300000.0, 130000),
                    (20260330, 1563, 1575, 1520, 1540, 1400000.0, 140000),
                    (20260403, 1540, 1555, 1500, 1510, 1500000.0, 150000),
                ],
                ("sz", "002663"): [
                    (20260330, 220, 225, 218, 224, 1000000.0, 100000),
                    (20260331, 224, 232, 223, 230, 1100000.0, 110000),
                    (20260401, 230, 244, 228, 238, 1200000.0, 120000),
                    (20260402, 238, 240, 219, 219, 1300000.0, 130000),
                    (20260403, 218, 220, 197, 201, 1400000.0, 140000),
                ],
                ("sz", "000899"): [
                    (20260324, 1500, 1510, 1480, 1490, 1000000.0, 100000),
                    (20260325, 1490, 1500, 1450, 1460, 1100000.0, 110000),
                    (20260326, 1460, 1470, 1425, 1440, 1200000.0, 120000),
                    (20260327, 1440, 1450, 1400, 1420, 1300000.0, 130000),
                    (20260330, 1429, 1429, 1313, 1342, 1400000.0, 140000),
                    (20260403, 1342, 1360, 1320, 1330, 1500000.0, 150000),
                ],
            }
            for (market, code), rows in candidate_windows.items():
                write_day_records(offline_root / "raw" / market / "lday" / f"{market}{code}.day", rows)

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
                insert into market_meta.market_meta.instrument_master values (?, 'stock', ?, ?, '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh603538", "SH", "Meinuohua"),
                    ("sh603008", "SH", "Xilinmen"),
                    ("sh600310", "SH", "Guangxi Energy"),
                    ("sh603687", "SH", "Dashengda"),
                    ("sz002663", "SZ", "Pubang Shares"),
                    ("sz000899", "SZ", "Ganneng"),
                ],
            )
            con.executemany(
                """
                insert into market_meta.market_meta.industry_block_relation values (?, 'stock', 'industry', ?, ?, '2026-04-23', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh603538", "T0101", "Pharma"),
                    ("sh603008", "T0201", "Home"),
                    ("sh600310", "T010201", "Hydropower"),
                    ("sh603687", "T1102", "Packaging"),
                    ("sz002663", "T110101", "Construction"),
                    ("sz000899", "T010202", "Thermal Power"),
                ],
            )
            con.close()

            report = build_default_add_on_price_limit_shortlist_malf_research_prep(
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                generated_at="2026-06-29T23:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["research_shortlist_id"], "add_on_price_limit_shortlist_v0.1")
        self.assertEqual(report["research_shortlist_scope"], "add_on_pullback_add_price_limit")
        self.assertTrue(report["research_only"])
        self.assertEqual(report["sample_count"], 6)
        self.assertEqual(report["core_sample_count"], 4)
        self.assertEqual(report["backup_sample_count"], 2)
        self.assertEqual(report["blocked_formal_front_filter_count"], 6)
        self.assertEqual(report["snapshot_pending_formal_front_filter_count"], 0)

        by_code = {item["ts_code"]: item for item in report["samples"]}
        self.assertEqual(by_code["600310.SH"]["research_priority_group"], "core")
        self.assertEqual(by_code["002663.SZ"]["research_priority_group"], "backup")
        self.assertEqual(by_code["600310.SH"]["formal_review_bucket"], "pressure_adjust_reopen")
        self.assertEqual(by_code["000899.SZ"]["formal_review_bucket"], "near_limit_compare")
        self.assertEqual(by_code["603687.SH"]["trade_date"], "2026-03-27")
        self.assertEqual(by_code["603538.SH"]["industry_window_status"], "not_overlapping")
        self.assertEqual(by_code["000899.SZ"]["next_action"], "action:hold_for_industry_time_alignment")

    def test_materialize_default_add_on_price_limit_core_malf_research_bundle_writes_core_four_prep_and_backup_compare(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            data_root = root / "data-root"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            candidate_windows = {
                ("sh", "603538"): [
                    (20260324, 4000, 4050, 3980, 4030, 1000000.0, 100000),
                    (20260325, 4030, 4100, 4020, 4080, 1100000.0, 110000),
                    (20260326, 4080, 4180, 4060, 4160, 1200000.0, 120000),
                    (20260330, 4160, 4210, 4050, 4070, 1300000.0, 130000),
                    (20260401, 4070, 4172, 3681, 3985, 1400000.0, 140000),
                    (20260403, 3985, 4020, 3900, 3950, 1500000.0, 150000),
                ],
                ("sh", "603008"): [
                    (20260324, 1600, 1620, 1580, 1590, 1000000.0, 100000),
                    (20260325, 1590, 1610, 1560, 1570, 1100000.0, 110000),
                    (20260326, 1570, 1590, 1540, 1540, 1200000.0, 120000),
                    (20260327, 1540, 1560, 1490, 1510, 1300000.0, 130000),
                    (20260330, 1510, 1577, 1467, 1518, 1400000.0, 140000),
                    (20260403, 1518, 1530, 1490, 1500, 1500000.0, 150000),
                ],
                ("sh", "600310"): [
                    (20260324, 500, 560, 490, 550, 1000000.0, 100000),
                    (20260325, 550, 610, 540, 600, 1100000.0, 110000),
                    (20260326, 600, 650, 590, 640, 1200000.0, 120000),
                    (20260327, 640, 660, 620, 660, 1300000.0, 130000),
                    (20260330, 699, 726, 618, 632, 1400000.0, 140000),
                    (20260403, 632, 640, 600, 615, 1500000.0, 150000),
                ],
                ("sh", "603687"): [
                    (20260324, 1700, 1710, 1660, 1670, 1000000.0, 100000),
                    (20260325, 1670, 1680, 1610, 1620, 1100000.0, 110000),
                    (20260326, 1620, 1635, 1560, 1590, 1200000.0, 120000),
                    (20260327, 1590, 1647, 1485, 1563, 1300000.0, 130000),
                    (20260330, 1563, 1575, 1520, 1540, 1400000.0, 140000),
                    (20260403, 1540, 1555, 1500, 1510, 1500000.0, 150000),
                ],
                ("sz", "002663"): [
                    (20260330, 220, 225, 218, 224, 1000000.0, 100000),
                    (20260331, 224, 232, 223, 230, 1100000.0, 110000),
                    (20260401, 230, 244, 228, 238, 1200000.0, 120000),
                    (20260402, 238, 240, 219, 219, 1300000.0, 130000),
                    (20260403, 218, 220, 197, 201, 1400000.0, 140000),
                ],
                ("sz", "000899"): [
                    (20260324, 1500, 1510, 1480, 1490, 1000000.0, 100000),
                    (20260325, 1490, 1500, 1450, 1460, 1100000.0, 110000),
                    (20260326, 1460, 1470, 1425, 1440, 1200000.0, 120000),
                    (20260327, 1440, 1450, 1400, 1420, 1300000.0, 130000),
                    (20260330, 1429, 1429, 1313, 1342, 1400000.0, 140000),
                    (20260403, 1342, 1360, 1320, 1330, 1500000.0, 150000),
                ],
            }
            for (market, code), rows in candidate_windows.items():
                write_day_records(offline_root / "raw" / market / "lday" / f"{market}{code}.day", rows)

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
                insert into market_meta.market_meta.instrument_master values (?, 'stock', ?, ?, '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh603538", "SH", "Meinuohua"),
                    ("sh603008", "SH", "Xilinmen"),
                    ("sh600310", "SH", "Guangxi Energy"),
                    ("sh603687", "SH", "Dashengda"),
                    ("sz002663", "SZ", "Pubang Shares"),
                    ("sz000899", "SZ", "Ganneng"),
                ],
            )
            con.executemany(
                """
                insert into market_meta.market_meta.industry_block_relation values (?, 'stock', 'industry', ?, ?, '2026-04-23', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh603538", "T0101", "Pharma"),
                    ("sh603008", "T0201", "Home"),
                    ("sh600310", "T010201", "Hydropower"),
                    ("sh603687", "T1102", "Packaging"),
                    ("sz002663", "T110101", "Construction"),
                    ("sz000899", "T010202", "Thermal Power"),
                ],
            )
            con.close()

            report = materialize_default_add_on_price_limit_core_malf_research_bundle(
                data_root=data_root,
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                generated_at="2026-06-29T23:30:00+08:00",
            )

            bundle_root = data_root / "research" / "add_on-price-limit-shortlist-v0.1"
            core_manifest_path = bundle_root / "core-malf-snapshot-prep-manifest-v0.1.json"
            backup_manifest_path = bundle_root / "near-limit-compare-manifest-v0.1.json"
            front_filter_prep_path = bundle_root / "front-filter-research-prep-v0.1.json"
            core_daily_path = bundle_root / "daily-window-v0.1" / "603538.SH.csv"
            core_stub_path = bundle_root / "malf-snapshot-stubs-v0.1" / "603538.SH-2026-03.json"
            core_draft_path = bundle_root / "malf-snapshot-drafts-v0.1" / "603538.SH-2026-03.json"
            backup_stub_path = bundle_root / "malf-snapshot-stubs-v0.1" / "002663.SZ-2026-03.json"
            backup_draft_path = bundle_root / "malf-snapshot-drafts-v0.1" / "002663.SZ-2026-03.json"

            self.assertEqual(report["result"], "pass")
            self.assertTrue(report["research_only"])
            self.assertEqual(report["core_sample_count"], 4)
            self.assertEqual(report["backup_sample_count"], 2)
            self.assertEqual(report["core_daily_window_count"], 4)
            self.assertEqual(report["core_snapshot_stub_count"], 4)
            self.assertEqual(report["core_snapshot_draft_count"], 4)
            self.assertEqual(report["research_bundle_root"], "research/add_on-price-limit-shortlist-v0.1")
            self.assertEqual(report["next_action"], "action:fill_core_malf_snapshot_stubs")

            self.assertTrue(core_manifest_path.exists())
            self.assertTrue(backup_manifest_path.exists())
            self.assertTrue(front_filter_prep_path.exists())
            self.assertTrue(core_daily_path.exists())
            self.assertTrue(core_stub_path.exists())
            self.assertTrue(core_draft_path.exists())
            self.assertFalse(backup_stub_path.exists())
            self.assertFalse(backup_draft_path.exists())

            core_manifest = json.loads(core_manifest_path.read_text(encoding="utf-8"))
            backup_manifest = json.loads(backup_manifest_path.read_text(encoding="utf-8"))
            front_filter_prep = json.loads(front_filter_prep_path.read_text(encoding="utf-8"))
            core_stub = json.loads(core_stub_path.read_text(encoding="utf-8"))
            core_draft = json.loads(core_draft_path.read_text(encoding="utf-8"))

            self.assertEqual(core_manifest["sample_count"], 4)
            self.assertEqual(
                [item["ts_code"] for item in core_manifest["samples"]],
                ["603538.SH", "603008.SH", "600310.SH", "603687.SH"],
            )
            self.assertEqual(backup_manifest["sample_count"], 2)
            self.assertEqual(
                [item["ts_code"] for item in backup_manifest["samples"]],
                ["002663.SZ", "000899.SZ"],
            )
            self.assertEqual(front_filter_prep["core_sample_count"], 4)
            self.assertEqual(front_filter_prep["backup_sample_count"], 2)
            self.assertEqual(front_filter_prep["blocked_formal_front_filter_count"], 4)
            self.assertEqual(core_stub["snapshot_quality_status"], "source_missing")
            self.assertEqual(core_stub["source_daily_file"], "daily-window-v0.1/603538.SH.csv")
            self.assertEqual(core_stub["research_prep_status"], "stub_pending_manual_malf_fill")
            self.assertEqual(core_stub["intended_front_filter_rule_id"], "Q-PRESSURE-ADJUST")
            self.assertEqual(core_stub["intended_malf_background"], "pullback")
            self.assertEqual(
                core_stub["manual_malf_fill_required_fields"],
                [
                    "snapshot_quality_status=ready",
                    "malf_background=pullback",
                    "wave_range_break_fields.pressure_adjustment=true",
                ],
            )
            self.assertEqual(
                core_stub["research_boundary_warning"],
                [
                    "stub_is_not_formal_front_filter_ready",
                    "manual_malf_fill_required_before_front_filter",
                    "do_not_mark_ready_until_structure_evidence_is_reviewed",
                    "do_not_generate_trade_from_research_prep",
                ],
            )
            self.assertNotIn("trade_accept", core_stub)
            self.assertNotIn("target_position", core_stub)
            self.assertEqual(core_draft["snapshot_quality_status"], "incomplete")
            self.assertEqual(core_draft["research_prep_status"], "draft_pending_manual_evidence_review")
            self.assertEqual(core_draft["malf_background"], "pullback")
            self.assertEqual(core_draft["wave_range_break_fields"], {"pressure_adjustment": True})
            self.assertEqual(core_draft["draft_front_filter_expected_rule_id"], "Q-PRESSURE-ADJUST")
            self.assertEqual(
                core_draft["draft_boundary_warning"],
                [
                    "draft_is_not_formal_front_filter_ready",
                    "snapshot_quality_status_must_remain_incomplete_until_reviewed",
                    "do_not_generate_trade_from_research_draft",
                ],
            )
            draft_front_filter_report = run_front_filter(core_draft_path)
            self.assertEqual(draft_front_filter_report["front_filter_result"], "blocked")
            self.assertEqual(draft_front_filter_report["qualification_rule_id"], None)
            self.assertIn("blocked_by_malf_snapshot_not_ready", draft_front_filter_report["rule_match_reason"])
            self.assertEqual(
                core_manifest["samples"][0]["materialized_snapshot_stub_file"],
                "research/add_on-price-limit-shortlist-v0.1/malf-snapshot-stubs-v0.1/603538.SH-2026-03.json",
            )
            self.assertEqual(
                core_manifest["samples"][0]["materialized_snapshot_draft_file"],
                "research/add_on-price-limit-shortlist-v0.1/malf-snapshot-drafts-v0.1/603538.SH-2026-03.json",
            )
            self.assertIn("malf-snapshot-stubs-v0.1\\603538.SH-2026-03.json", core_manifest["samples"][0]["materialized_front_filter_command"])
            self.assertEqual(backup_manifest["samples"][0]["compare_role"], "near_limit_backup_control")

    def test_build_shortlist_malf_research_prep_keeps_non_overlapping_samples_in_research_only_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            candidate_windows = {
                ("sh", "603538"): [
                    (20260324, 4000, 4050, 3980, 4030, 1000000.0, 100000),
                    (20260325, 4030, 4100, 4020, 4080, 1100000.0, 110000),
                    (20260326, 4080, 4180, 4060, 4160, 1200000.0, 120000),
                    (20260330, 4160, 4210, 4050, 4070, 1300000.0, 130000),
                    (20260401, 4070, 4172, 3681, 3985, 1400000.0, 140000),
                    (20260403, 3985, 4020, 3900, 3950, 1500000.0, 150000),
                ],
                ("sz", "002663"): [
                    (20260330, 220, 225, 218, 224, 1000000.0, 100000),
                    (20260331, 224, 232, 223, 230, 1100000.0, 110000),
                    (20260401, 230, 244, 228, 238, 1200000.0, 120000),
                    (20260402, 238, 240, 219, 219, 1300000.0, 130000),
                    (20260403, 218, 220, 197, 201, 1400000.0, 140000),
                ],
            }
            for (market, code), rows in candidate_windows.items():
                write_day_records(offline_root / "raw" / market / "lday" / f"{market}{code}.day", rows)

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
                insert into market_meta.market_meta.instrument_master values (?, 'stock', ?, ?, '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh603538", "SH", "Meinuohua"),
                    ("sz002663", "SZ", "Pubang Shares"),
                ],
            )
            con.executemany(
                """
                insert into market_meta.market_meta.industry_block_relation values (?, 'stock', 'industry', ?, ?, '2026-04-23', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh603538", "T0101", "Pharma"),
                    ("sz002663", "T0202", "Construction"),
                ],
            )
            con.close()

            sample_entries = [
                {
                    "ts_code": "603538.SH",
                    "trade_date": "2026-04-01",
                    "sample_window_start": "2026-03-24",
                    "sample_window_end": "2026-04-03",
                    "research_priority_group": "core",
                    "formal_review_bucket": "pressure_adjust_reopen",
                    "core_snapshot_focus": "pressure_adjust_reopen_core",
                    "selection_reason": "core reopened-touch candidate",
                    "evidence_ref": "unit-test:603538-core-research-prep",
                },
                {
                    "ts_code": "002663.SZ",
                    "trade_date": "2026-04-03",
                    "sample_window_start": "2026-03-24",
                    "sample_window_end": "2026-04-03",
                    "research_priority_group": "backup",
                    "formal_review_bucket": "near_limit_compare",
                    "core_snapshot_focus": "near_limit_compare_backup",
                    "selection_reason": "backup near-limit compare candidate",
                    "evidence_ref": "unit-test:002663-backup-research-prep",
                },
            ]

            report = build_shortlist_malf_research_prep(
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=sample_entries,
                generated_at="2026-06-29T22:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["research_only"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["sample_count"], 2)
        self.assertEqual(report["core_sample_count"], 1)
        self.assertEqual(report["backup_sample_count"], 1)
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["blocked_formal_front_filter_count"], 2)

        by_code = {item["ts_code"]: item for item in report["samples"]}
        self.assertEqual(by_code["603538.SH"]["research_priority_group"], "core")
        self.assertEqual(by_code["002663.SZ"]["research_priority_group"], "backup")
        self.assertEqual(by_code["603538.SH"]["industry_window_status"], "not_overlapping")
        self.assertEqual(by_code["603538.SH"]["formal_front_filter_status"], "blocked")
        self.assertEqual(
            by_code["603538.SH"]["formal_front_filter_issue"],
            "industry_membership_window_not_overlapping:603538.SH",
        )
        self.assertEqual(by_code["603538.SH"]["current_industry_name"], "Pharma")
        self.assertEqual(by_code["603538.SH"]["snapshot_stub"]["snapshot_quality_status"], "source_missing")
        self.assertTrue(by_code["603538.SH"]["event_trade_date_in_window"])
        self.assertIn("<data_root>", by_code["603538.SH"]["suggested_front_filter_command"])
        self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(report.keys()))
        self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(by_code["603538.SH"].keys()))

    def test_build_shortlist_malf_research_prep_distinguishes_snapshot_pending_when_industry_window_overlaps(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            write_day_records(
                offline_root / "raw" / "sh" / "lday" / "sh600310.day",
                [
                    (20260324, 500, 560, 490, 550, 1000000.0, 100000),
                    (20260325, 550, 610, 540, 600, 1100000.0, 110000),
                    (20260326, 600, 650, 590, 640, 1200000.0, 120000),
                    (20260327, 640, 660, 620, 660, 1300000.0, 130000),
                    (20260330, 699, 726, 618, 632, 1400000.0, 140000),
                ],
            )

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
            con.execute(
                """
                insert into market_meta.market_meta.instrument_master values
                ('sh600310', 'stock', 'SH', 'Guangxi Energy', '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.execute(
                """
                insert into market_meta.market_meta.industry_block_relation values
                ('sh600310', 'stock', 'industry', 'T0101', 'Utilities', '2026-03-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            report = build_shortlist_malf_research_prep(
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=[
                    {
                        "ts_code": "600310.SH",
                        "trade_date": "2026-03-30",
                        "sample_window_start": "2026-03-24",
                        "sample_window_end": "2026-03-30",
                        "research_priority_group": "core",
                        "formal_review_bucket": "pressure_adjust_reopen",
                        "core_snapshot_focus": "pressure_adjust_reopen_core",
                        "selection_reason": "up-limit-side core candidate",
                        "evidence_ref": "unit-test:600310-overlap-research-prep",
                    }
                ],
                generated_at="2026-06-29T22:05:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["formal_front_filter_ready_count"], 0)
        self.assertEqual(report["blocked_formal_front_filter_count"], 0)
        self.assertEqual(report["snapshot_pending_formal_front_filter_count"], 1)
        sample = report["samples"][0]
        self.assertEqual(sample["industry_window_status"], "overlapping")
        self.assertEqual(sample["formal_front_filter_status"], "snapshot_pending")
        self.assertEqual(sample["formal_front_filter_issue"], "pipeline_requires_ready_malf_snapshot")
        self.assertEqual(sample["current_industry_name"], "Utilities")
        self.assertEqual(sample["snapshot_stub"]["ts_code"], "600310.SH")
        self.assertEqual(sample["snapshot_stub"]["window_start"], "2026-03-24")
        self.assertEqual(sample["snapshot_stub"]["window_end"], "2026-03-30")

    def test_build_shortlist_malf_research_prep_blocks_missing_daily_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
            con.execute(
                """
                insert into market_meta.market_meta.instrument_master values
                ('sz000899', 'stock', 'SZ', 'Ganneng', '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            report = build_shortlist_malf_research_prep(
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=[
                    {
                        "ts_code": "000899.SZ",
                        "trade_date": "2026-03-30",
                        "sample_window_start": "2026-03-24",
                        "sample_window_end": "2026-04-03",
                        "research_priority_group": "backup",
                        "formal_review_bucket": "near_limit_compare",
                        "core_snapshot_focus": "near_limit_compare_backup",
                        "selection_reason": "missing daily bars should block prep",
                        "evidence_ref": "unit-test:000899-missing-daily",
                    }
                ],
                generated_at="2026-06-29T22:10:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("missing_daily_window:000899.SZ", report["issues"])
        self.assertEqual(report["sample_count"], 0)

    def test_build_shortlist_sample_package_materializes_pullback_pressure_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            data_root = root / "data-root"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            candidate_windows = {
                ("sh", "600310"): [
                    (20260324, 500, 560, 490, 550, 1000000.0, 100000),
                    (20260325, 550, 610, 540, 600, 1100000.0, 110000),
                    (20260326, 600, 650, 590, 640, 1200000.0, 120000),
                    (20260327, 640, 660, 620, 660, 1300000.0, 130000),
                    (20260330, 699, 726, 618, 632, 1400000.0, 140000),
                ],
                ("sz", "002663"): [
                    (20260330, 220, 225, 218, 224, 1000000.0, 100000),
                    (20260331, 224, 232, 223, 230, 1100000.0, 110000),
                    (20260401, 230, 244, 228, 238, 1200000.0, 120000),
                    (20260402, 238, 240, 219, 219, 1300000.0, 130000),
                    (20260403, 218, 220, 197, 201, 1400000.0, 140000),
                ],
            }
            for (market, code), rows in candidate_windows.items():
                write_day_records(offline_root / "raw" / market / "lday" / f"{market}{code}.day", rows)

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
                insert into market_meta.market_meta.instrument_master values (?, 'stock', ?, ?, '2020-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh600310", "SH", "Guangxi Energy"),
                    ("sz002663", "SZ", "Pubang Shares"),
                ],
            )
            con.executemany(
                """
                insert into market_meta.market_meta.industry_block_relation values (?, 'stock', 'industry', ?, ?, '2026-03-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sh600310", "T0101", "Utilities"),
                    ("sz002663", "T0202", "Construction"),
                ],
            )
            con.close()

            sample_entries = [
                {
                    "ts_code": "600310.SH",
                    "sample_window_start": "2026-03-24",
                    "sample_window_end": "2026-03-30",
                    "expected_structure_target": "limited",
                    "snapshot_preset": "pullback_pressure",
                    "selection_reason": "upper-limit-side shortlist candidate",
                    "evidence_ref": "unit-test:600310-shortlist",
                },
                {
                    "ts_code": "002663.SZ",
                    "sample_window_start": "2026-03-30",
                    "sample_window_end": "2026-04-03",
                    "expected_structure_target": "limited",
                    "snapshot_preset": "pullback_pressure",
                    "selection_reason": "near-limit shortlist candidate",
                    "evidence_ref": "unit-test:002663-shortlist",
                },
            ]

            report = build_shortlist_sample_package(
                data_root=data_root,
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=sample_entries,
                generated_at="2026-06-29T21:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["generated_sample_count"], 2)
        self.assertEqual(report["front_filter_report"]["result"], "pass")
        self.assertEqual(report["front_filter_report"]["front_filter_run_count"], 2)
        self.assertEqual(
            {item["qualification_rule_id"] for item in report["front_filter_report"]["front_filter_results"]},
            {"Q-PRESSURE-ADJUST"},
        )
        self.assertEqual(
            {item["rhythm_meaning"] for item in report["front_filter_report"]["front_filter_results"]},
            {"limited"},
        )
        for result in report["front_filter_report"]["front_filter_results"]:
            self.assertEqual(result["tachibana_applicability"], "conditional")
            self.assertEqual(result["next_action"], "action:fill_qualification_record")

    def test_build_first_batch_sample_package_materializes_ready_intake_and_audit_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            data_root = root / "data-root"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            day_records = [
                (20260330, 1000, 1010, 990, 1005, 1005000.0, 100000),
                (20260331, 1005, 1020, 1000, 1015, 1015000.0, 110000),
                (20260401, 1015, 1030, 1010, 1025, 1025000.0, 120000),
                (20260402, 1025, 1040, 1020, 1035, 1035000.0, 130000),
                (20260403, 1035, 1050, 1030, 1045, 1045000.0, 140000),
            ]
            for market, code in [("sz", "000001"), ("sh", "600000"), ("sh", "601127"), ("sz", "002714")]:
                write_day_records(offline_root / "raw" / market / "lday" / f"{market}{code}.day", day_records)

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
                insert into market_meta.market_meta.instrument_master values (?, 'stock', ?, ?, '2000-01-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sz000001", "SZ", "Ping An Bank"),
                    ("sh600000", "SH", "Shanghai Pudong Bank"),
                    ("sh601127", "SH", "Seres"),
                    ("sz002714", "SZ", "Muyuan Foods"),
                ],
            )
            con.executemany(
                """
                insert into market_meta.market_meta.industry_block_relation values (?, 'stock', 'industry', ?, ?, '2026-03-01', null, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sz000001", "T1001", "Bank"),
                    ("sh600000", "T1001", "Bank"),
                    ("sh601127", "T040201", "Auto"),
                    ("sz002714", "T030206", "Agriculture"),
                ],
            )
            con.close()

            sample_entries = [
                {
                    "ts_code": "000001.SZ",
                    "sample_window_start": "2026-03-30",
                    "sample_window_end": "2026-04-03",
                    "expected_structure_target": "meaningful",
                    "selection_reason": "steady directional window",
                    "evidence_ref": "unit-test:meaningful",
                },
                {
                    "ts_code": "600000.SH",
                    "sample_window_start": "2026-03-30",
                    "sample_window_end": "2026-04-03",
                    "expected_structure_target": "limited",
                    "selection_reason": "range wait window",
                    "snapshot_preset": "range_wait",
                    "evidence_ref": "unit-test:limited",
                },
                {
                    "ts_code": "601127.SH",
                    "sample_window_start": "2026-03-30",
                    "sample_window_end": "2026-04-03",
                    "expected_structure_target": "unknown",
                    "selection_reason": "research pending structure",
                    "evidence_ref": "unit-test:unknown",
                },
                {
                    "ts_code": "002714.SZ",
                    "sample_window_start": "2026-03-30",
                    "sample_window_end": "2026-04-03",
                    "expected_structure_target": "not_meaningful",
                    "selection_reason": "noise dominated window",
                    "evidence_ref": "unit-test:not-meaningful",
                },
            ]

            build_report = build_first_batch_sample_package(
                data_root=data_root,
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=sample_entries,
                generated_at="2026-06-27T09:00:00+08:00",
            )
            readiness = audit_first_batch_readiness(data_root)
            front_filter = audit_first_batch_front_filter_run(data_root)
            record_drafts = audit_first_batch_record_drafts(data_root)
            trial = audit_first_batch_sample_table_trial(data_root)
            coverage = audit_first_batch_sample_coverage(data_root)

        self.assertEqual(build_report["result"], "pass")
        self.assertEqual(build_report["generated_sample_count"], 4)
        self.assertEqual(readiness["result"], "pass")
        self.assertEqual(readiness["front_filter_ready_candidate_count"], 4)
        self.assertEqual(front_filter["result"], "pass")
        self.assertEqual(front_filter["front_filter_run_count"], 4)
        self.assertEqual(
            {item["rhythm_meaning"] for item in front_filter["front_filter_results"]},
            {"meaningful", "limited", "unknown", "not_meaningful"},
        )
        self.assertEqual(record_drafts["result"], "pass")
        self.assertEqual(record_drafts["record_draft_count"], 2)
        self.assertEqual(trial["result"], "pass")
        self.assertGreaterEqual(trial["trial_row_count"], 1)
        self.assertEqual(coverage["result"], "pass")
        self.assertEqual(set(coverage["covered_structure_targets"]), {"meaningful", "limited", "unknown", "not_meaningful"})
        self.assertEqual(coverage["missing_structure_targets"], [])

        for report in [build_report, readiness, front_filter, record_drafts, trial, coverage]:
            self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(report.keys()))

    def test_build_first_batch_sample_package_blocks_when_industry_labels_do_not_overlap_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            data_root = root / "data-root"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            day_rows = [
                (20260324, 1000, 1010, 990, 1005, 1005000.0, 100000),
                (20260325, 1005, 1020, 1000, 1015, 1015000.0, 110000),
            ]
            write_day_records_file = offline_root / "raw" / "sz" / "lday" / "sz000001.day"
            write_day_records(write_day_records_file, day_rows)

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
            con.execute(
                """
                insert into market_meta.market_meta.instrument_master values
                ('sz000001', 'stock', 'SZ', 'Ping An Bank', '1991-04-03', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.execute(
                """
                insert into market_meta.market_meta.industry_block_relation values
                ('sz000001', 'stock', 'industry', 'T1001', 'Bank', '2026-04-23', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.close()

            sample_entries = [
                {
                    "ts_code": "000001.SZ",
                    "sample_window_start": "2026-03-24",
                    "sample_window_end": "2026-03-25",
                    "expected_structure_target": "meaningful",
                    "selection_reason": "window must not borrow future industry labels",
                    "evidence_ref": "unit-test:future-only-industry",
                }
            ]

            report = build_first_batch_sample_package(
                data_root=data_root,
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=sample_entries,
                generated_at="2026-06-27T09:00:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("industry_membership_window_not_overlapping:000001.SZ", report["issues"])
        self.assertEqual(report["generated_sample_count"], 0)
        self.assertTrue(FORBIDDEN_FIELDS.isdisjoint(report))

    def test_build_first_batch_sample_package_selects_overlapping_industry_label(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            offline_root = root / "offline"
            duckdb_root = root / "duckdb"
            tdx_root = root / "tdx"
            data_root = root / "data-root"
            duckdb_root.mkdir()
            (tdx_root / "vipdoc").mkdir(parents=True)

            write_day_records(offline_root / "raw" / "sz" / "lday" / "sz000001.day", [
                (20260324, 1000, 1010, 990, 1005, 1005000.0, 100000),
                (20260325, 1005, 1020, 1000, 1015, 1015000.0, 110000),
            ])

            import duckdb

            con = duckdb.connect(str(duckdb_root / "market_meta.duckdb"))
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
            con.execute(
                """
                insert into market_meta.market_meta.instrument_master values
                ('sz000001', 'stock', 'SZ', 'Ping An Bank', '1991-04-03', null, 'run-1', 'v1', 'r1', 'hash-1')
                """
            )
            con.executemany(
                """
                insert into market_meta.market_meta.industry_block_relation values
                (?, 'stock', 'industry', ?, ?, ?, ?, 'run-1', 'v1', 'r1', 'hash-1')
                """,
                [
                    ("sz000001", "T0001", "OldBank", "2025-01-01", "2026-03-23"),
                    ("sz000001", "T1001", "Bank", "2026-03-24", None),
                    ("sz000001", "T9999", "FutureBank", "2026-04-23", None),
                ],
            )
            con.close()

            sample_entries = [
                {
                    "ts_code": "000001.SZ",
                    "sample_window_start": "2026-03-24",
                    "sample_window_end": "2026-03-25",
                    "expected_structure_target": "meaningful",
                    "selection_reason": "window should align to overlapping industry label",
                    "evidence_ref": "unit-test:aligned-industry",
                }
            ]

            report = build_first_batch_sample_package(
                data_root=data_root,
                tdx_root=tdx_root,
                offline_root=offline_root,
                duckdb_root=duckdb_root,
                sample_entries=sample_entries,
                generated_at="2026-06-27T09:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["sw_file"], "ashare/sw-industry-membership-v0.1.csv")
        self.assertEqual(report["generated_sample_count"], 1)


if __name__ == "__main__":
    unittest.main()
