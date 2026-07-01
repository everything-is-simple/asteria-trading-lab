from tests.ashare_intake_support import *


class AshareIntakeContractsTest(unittest.TestCase):
    def test_institution_fact_package_accepts_fact_fields_without_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            facts_dir = root / "ashare" / "institution-facts-v0.1"
            write_csv(
                facts_dir / "000001.SZ.csv",
                INSTITUTION_FACT_HEADER,
                [[
                    "000001.SZ",
                    "2026-01-06",
                    "true",
                    "false",
                    "11.77",
                    "9.63",
                    "none",
                    "none",
                    "100",
                    "unit-test:exchange-calendar-and-price-limit",
                ]],
            )

            report = audit_ashare_institution_fact_package(root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_fact_status"], "ready")
        self.assertEqual(report["institution_fact_count"], 1)
        self.assertEqual(report["institution_fact_files"], ["ashare/institution-facts-v0.1/000001.SZ.csv"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertEqual(report["next_action"], "action:build_execution_constraint_snapshots")
        self.assertEqual(report["failed_contract_items"], [])

    def test_institution_fact_package_blocks_rule_and_signal_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            facts_dir = root / "ashare" / "institution-facts-v0.1"
            write_csv(
                facts_dir / "000001.SZ.csv",
                [*INSTITUTION_FACT_HEADER, "limit_up_strategy", "trade_accept", "target_position"],
                [[
                    "000001.SZ",
                    "2026-01-06",
                    "true",
                    "false",
                    "11.77",
                    "9.63",
                    "none",
                    "none",
                    "100",
                    "unit-test",
                    "chase_board",
                    "true",
                    "0.5",
                ]],
            )

            report = audit_ashare_institution_fact_package(root)

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["institution_fact_status"], "invalid")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertIn("forbidden_field:000001.SZ.csv:limit_up_strategy", report["failed_contract_items"])
        self.assertIn("forbidden_field:000001.SZ.csv:trade_accept", report["failed_contract_items"])
        self.assertIn("forbidden_field:000001.SZ.csv:target_position", report["failed_contract_items"])
        self.assertEqual(report["next_action"], "action:repair_institution_fact_package")

    def test_ready_fixture_stops_at_structure_candidate_and_requires_front_filter(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = validate_intake_package(fixture_root)

        self.assertEqual(report["intake_package_status"], "ready")
        self.assertEqual(report["contract_check_result"], "pass")
        self.assertEqual(report["failed_contract_items"], [])
        self.assertFalse(report["eligible_for_tachibana_candidate"])
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")
        summary = report["candidate_stage_summary"]["000001.SZ"]
        self.assertTrue(summary["eligible_for_malf_run"])
        self.assertEqual(summary["candidate_stage_after"], "structure_candidate")
        self.assertEqual(summary["tachibana_applicability"], "unknown")
        self.assertEqual(summary["next_action"], "action:run_front_filter")
        self.assertIn("no_qualification_rule", summary["applicability_reason"])
        self.assertIn("do_not_upgrade_ready_snapshot_without_front_filter", summary["boundary_warning"])
        self.assertNotEqual(summary["candidate_stage_after"], "tachibana_candidate")

    def test_empty_data_root_reports_missing_package_and_blocks_all_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_intake_package(Path(tmp))

        self.assertEqual(report["intake_package_status"], "missing")
        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertFalse(report["eligible_for_structure_candidate"])
        self.assertFalse(report["eligible_for_tachibana_candidate"])
        self.assertIn("missing_file:ashare/candidate-universe-v0.1.csv", report["failed_contract_items"])
        self.assertIn("missing_file:ashare/sw-industry-membership-v0.1.csv", report["failed_contract_items"])
        self.assertIn("missing_dir:ashare/daily-window-v0.1", report["failed_contract_items"])
        self.assertIn("missing_dir:ashare/malf-snapshots-v0.1", report["failed_contract_items"])
        self.assertIn("missing_candidate_universe", report["failed_contract_reason_codes"])
        self.assertIn("missing_sw_industry_membership", report["failed_contract_reason_codes"])
        self.assertIn("missing_daily_window", report["failed_contract_reason_codes"])
        self.assertIn("missing_malf_snapshot", report["failed_contract_reason_codes"])
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")
        self.assertEqual(report["stage_reason_consistency"]["issues"], [])

    def test_forbidden_trading_fields_fail_the_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                [*CANDIDATE_HEADER, "buy_signal"],
                [["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test", "true"]],
            )
            write_csv(
                ashare / "sw-industry-membership-v0.1.csv",
                SW_HEADER,
                [["000001.SZ", "Bank", "Joint-stock Bank", "2025-01-01", "", "unit-test"]],
            )
            (ashare / "daily-window-v0.1").mkdir()
            (ashare / "malf-snapshots-v0.1").mkdir()

            report = validate_intake_package(root)

        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertIn("forbidden_field:buy_signal", report["failed_contract_items"])
        self.assertIn("forbidden_field_present", report["failed_contract_reason_codes"])

    def test_minimal_valid_package_passes_read_only_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                CANDIDATE_HEADER,
                [["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test"]],
            )
            write_csv(
                ashare / "sw-industry-membership-v0.1.csv",
                SW_HEADER,
                [["000001.SZ", "Bank", "Joint-stock Bank", "2025-01-01", "", "unit-test"]],
            )
            write_csv(
                ashare / "daily-window-v0.1" / "000001.SZ.csv",
                DAILY_HEADER,
                [
                    ["000001.SZ", "2026-01-05", "10.00", "10.50", "9.80", "10.20", "100000", "1020000", "qfq", "false", "false", "false"],
                    ["000001.SZ", "2026-01-06", "10.20", "10.80", "10.10", "10.70", "110000", "1177000", "qfq", "false", "false", "false"],
                ],
            )
            snapshot = {
                "malf_snapshot_ref": "MALF-SNAP-000001-202601",
                "ts_code": "000001.SZ",
                "window_start": "2026-01-05",
                "window_end": "2026-01-06",
                "source_daily_file": "daily-window-v0.1/000001.SZ.csv",
                "generated_at": "2026-06-26T00:00:00+08:00",
                "malf_version": "MALF_Definitive_v2_0",
                "malf_background": "alive_wave",
                "wave_range_break_fields": {"range_state": "up_range"},
                "evidence_ref": "unit-test",
                "snapshot_quality_status": "ready",
            }
            snapshot_dir = ashare / "malf-snapshots-v0.1"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "000001.SZ-2026-01.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            report = validate_intake_package(root)

        self.assertEqual(report["intake_package_status"], "ready")
        self.assertEqual(report["contract_check_result"], "pass")
        self.assertTrue(report["eligible_for_malf_run"])
        self.assertTrue(report["eligible_for_structure_candidate"])
        self.assertFalse(report["eligible_for_tachibana_candidate"])
        self.assertEqual(report["failed_contract_items"], [])
        self.assertEqual(
            report["candidate_stage_summary"]["000001.SZ"]["candidate_stage_after"],
            "structure_candidate",
        )
        self.assertEqual(
            report["candidate_stage_summary"]["000001.SZ"]["tachibana_applicability"],
            "unknown",
        )
        self.assertEqual(
            report["candidate_stage_summary"]["000001.SZ"]["next_action"],
            "action:run_front_filter",
        )
        self.assertIn(
            "do_not_upgrade_ready_snapshot_without_front_filter",
            report["candidate_stage_summary"]["000001.SZ"]["boundary_warning"],
        )
        self.assertIn(
            "do_not_upgrade_ready_snapshot_without_front_filter",
            report["candidate_stage_summary"]["000001.SZ"]["blocking_reasons"],
        )
        self.assertIn(
            "no_qualification_rule",
            report["candidate_stage_summary"]["000001.SZ"]["applicability_reason"],
        )
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")

    def test_cross_file_orphans_and_snapshot_window_mismatches_fail_the_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                CANDIDATE_HEADER,
                [["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test"]],
            )
            write_csv(
                ashare / "sw-industry-membership-v0.1.csv",
                SW_HEADER,
                [["000002.SZ", "Bank", "Joint-stock Bank", "2025-01-01", "", "unit-test"]],
            )
            write_csv(
                ashare / "daily-window-v0.1" / "000003.SZ.csv",
                DAILY_HEADER,
                [
                    ["000003.SZ", "2026-01-05", "10.00", "10.50", "9.80", "10.20", "100000", "1020000", "qfq", "false", "false", "false"],
                    ["000003.SZ", "2026-01-06", "10.20", "10.80", "10.10", "10.70", "110000", "1177000", "qfq", "false", "false", "false"],
                ],
            )
            snapshot = {
                "malf_snapshot_ref": "MALF-SNAP-000001-202601",
                "ts_code": "000001.SZ",
                "window_start": "2026-01-01",
                "window_end": "2026-01-10",
                "source_daily_file": "daily-window-v0.1/000001.SZ.csv",
                "generated_at": "2026-06-26T00:00:00+08:00",
                "malf_version": "MALF_Definitive_v2_0",
                "malf_background": "alive_wave",
                "wave_range_break_fields": {"range_state": "up_range"},
                "evidence_ref": "unit-test",
                "snapshot_quality_status": "ready",
            }
            snapshot_dir = ashare / "malf-snapshots-v0.1"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "000001.SZ-2026-01.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            report = validate_intake_package(root)

        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertIn("orphan_sw_ts_code:000002.SZ", report["failed_contract_items"])
        self.assertIn("orphan_daily_ts_code:000003.SZ", report["failed_contract_items"])
        self.assertIn("snapshot_source_daily_missing:000001.SZ-2026-01.json:daily-window-v0.1/000001.SZ.csv", report["failed_contract_items"])
        self.assertIn("snapshot_window_outside_daily_range:000001.SZ-2026-01.json", report["failed_contract_items"])
        self.assertIn("missing_industry_label", report["failed_contract_reason_codes"])
        self.assertIn("missing_daily_window", report["failed_contract_reason_codes"])
        self.assertIn("missing_malf_snapshot", report["failed_contract_reason_codes"])
        self.assertIn("malf_snapshot_window_mismatch", report["failed_contract_reason_codes"])

    def test_key_value_domain_and_numeric_contract_violations_fail_the_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                CANDIDATE_HEADER,
                [
                    ["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test"],
                    ["000001.SZ", "Duplicate", "invalid_board", "19910403", "maybe", "false", "bad_status", "unit-test"],
                ],
            )
            write_csv(
                ashare / "sw-industry-membership-v0.1.csv",
                SW_HEADER,
                [
                    ["000001.SZ", "Bank", "Joint-stock Bank", "2025-01-02", "2025-01-01", "unit-test"],
                    ["000001.SZ", "Bank", "Joint-stock Bank", "bad-date", "", "unit-test"],
                ],
            )
            write_csv(
                ashare / "daily-window-v0.1" / "000001.SZ.csv",
                DAILY_HEADER,
                [
                    ["000001.SZ", "2026-01-05", "-10.00", "10.50", "9.80", "10.20", "-100000", "1020000", "qfq", "maybe", "false", "false"],
                    ["000001.SZ", "bad-date", "10.20", "10.80", "10.10", "10.70", "110000", "-1177000", "qfq", "false", "false", "false"],
                ],
            )
            snapshot = {
                "malf_snapshot_ref": "MALF-SNAP-000001-202601",
                "ts_code": "000001.SZ",
                "window_start": "2026/01/05",
                "window_end": "2026-01-06",
                "source_daily_file": "daily-window-v0.1/000001.SZ.csv",
                "generated_at": "2026-06-26T00:00:00+08:00",
                "malf_version": "MALF_Definitive_v2_0",
                "malf_background": "alive_wave",
                "wave_range_break_fields": {"range_state": "up_range"},
                "evidence_ref": "unit-test",
                "snapshot_quality_status": "bad_status",
            }
            snapshot_dir = ashare / "malf-snapshots-v0.1"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "000001.SZ-2026-01.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            report = validate_intake_package(root)

        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertIn("duplicate_key:candidate-universe-v0.1.csv:ts_code:000001.SZ", report["failed_contract_items"])
        self.assertIn("invalid_enum:candidate-universe-v0.1.csv:board_type:invalid_board", report["failed_contract_items"])
        self.assertIn("invalid_date:candidate-universe-v0.1.csv:list_date:19910403", report["failed_contract_items"])
        self.assertIn("invalid_boolean:candidate-universe-v0.1.csv:is_st:maybe", report["failed_contract_items"])
        self.assertIn("invalid_enum:candidate-universe-v0.1.csv:data_quality_status:bad_status", report["failed_contract_items"])
        self.assertIn("invalid_date_order:sw-industry-membership-v0.1.csv:2025-01-02>2025-01-01", report["failed_contract_items"])
        self.assertIn("invalid_date:sw-industry-membership-v0.1.csv:valid_from:bad-date", report["failed_contract_items"])
        self.assertIn("negative_number:000001.SZ.csv:open:line_2", report["failed_contract_items"])
        self.assertIn("negative_number:000001.SZ.csv:volume:line_2", report["failed_contract_items"])
        self.assertIn("invalid_boolean:000001.SZ.csv:suspension_flag:line_2", report["failed_contract_items"])
        self.assertIn("invalid_date:000001.SZ.csv:trade_date:bad-date", report["failed_contract_items"])
        self.assertIn("negative_number:000001.SZ.csv:amount:line_3", report["failed_contract_items"])
        self.assertIn("invalid_date:000001.SZ-2026-01.json:window_start:2026/01/05", report["failed_contract_items"])
        self.assertIn("invalid_enum:000001.SZ-2026-01.json:snapshot_quality_status:bad_status", report["failed_contract_items"])
        self.assertIn("duplicate_key_present", report["failed_contract_reason_codes"])
        self.assertIn("invalid_enum_value", report["failed_contract_reason_codes"])
        self.assertIn("invalid_date_value", report["failed_contract_reason_codes"])
        self.assertIn("invalid_boolean_value", report["failed_contract_reason_codes"])
        self.assertIn("invalid_daily_ohlc", report["failed_contract_reason_codes"])
        self.assertIn("invalid_numeric_value", report["failed_contract_reason_codes"])
        self.assertIn("malf_snapshot_not_ready", report["failed_contract_reason_codes"])

    def test_stage_summary_keeps_metadata_only_candidates_below_structure_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                CANDIDATE_HEADER,
                [["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test"]],
            )
            write_csv(ashare / "sw-industry-membership-v0.1.csv", SW_HEADER, [])
            (ashare / "daily-window-v0.1").mkdir()
            (ashare / "malf-snapshots-v0.1").mkdir()

            report = validate_intake_package(root)

        summary = report["candidate_stage_summary"]["000001.SZ"]
        self.assertEqual(summary["candidate_stage_after"], "universe_candidate")
        self.assertFalse(summary["eligible_for_malf_run"])
        self.assertEqual(summary["tachibana_applicability"], "unknown")
        self.assertEqual(summary["next_action"], "action:complete_industry_and_daily_window")
        self.assertIn("missing_industry_label", summary["failed_contract_reason_codes"])
        self.assertIn("missing_daily_window", summary["blocking_reasons"])
        self.assertIn("missing_malf_snapshot", summary["failed_contract_reason_codes"])
        self.assertIn("blocked_by_missing_industry_label", summary["rule_match_reason"])
        self.assertIn("blocked_by_missing_daily_window", summary["rule_match_reason"])
        self.assertIn("blocked_by_missing_malf_snapshot", summary["rule_match_reason"])
        self.assertIn("no_industry_label", summary["applicability_reason"])
        self.assertIn("no_daily_window", summary["applicability_reason"])
        self.assertIn("no_ready_malf_snapshot", summary["applicability_reason"])
        self.assertIn("do_not_upgrade_without_malf_snapshot", summary["boundary_warning"])
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")

    def test_stage_reason_consistency_detects_internal_contradictions(self) -> None:
        audit = _audit_stage_reason_consistency(
            {
                "000001.SZ": {
                    "candidate_stage_after": "tachibana_candidate",
                    "eligible_for_malf_run": False,
                    "tachibana_applicability": "suitable",
                    "failed_contract_reason_codes": ["missing_daily_window", "missing_malf_snapshot"],
                    "rule_match_reason": [],
                    "applicability_reason": [],
                    "boundary_warning": [],
                    "next_action": "run_front_filter",
                }
            },
            ["missing_daily_window", "missing_malf_snapshot"],
        )

        self.assertEqual(audit["result"], "fail")
        self.assertIn("stage_without_malf_run:000001.SZ:tachibana_candidate", audit["issues"])
        self.assertIn("tachibana_applicability_decided_before_front_filter:000001.SZ:suitable", audit["issues"])
        self.assertIn("next_action_missing_action_prefix:000001.SZ:run_front_filter", audit["issues"])
        self.assertIn("missing_malf_snapshot_without_boundary_warning:000001.SZ", audit["issues"])
