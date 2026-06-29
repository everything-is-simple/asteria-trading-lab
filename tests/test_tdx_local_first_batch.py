from __future__ import annotations

from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ashare_intake_validator import (
    audit_first_batch_front_filter_run,
    audit_first_batch_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
)
from data_sources.tdx_local import (
    audit_first_batch_sample_coverage,
    build_first_batch_sample_package,
    build_shortlist_sample_package,
)


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
