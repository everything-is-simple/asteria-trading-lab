from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalShortlistReviewsTest(TdxLocalFirstBatchSupport):
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


