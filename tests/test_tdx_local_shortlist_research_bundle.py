from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalShortlistResearchBundleTest(TdxLocalFirstBatchSupport):
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


