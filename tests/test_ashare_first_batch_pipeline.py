from tests.ashare_intake_support import *


class AshareFirstBatchPipelineTest(unittest.TestCase):
    def test_first_batch_readiness_blocks_missing_intake_even_when_front_filter_system_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_first_batch_readiness(Path(tmp))

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["next_action"], "action:repair_intake_package")
        self.assertEqual(report["front_filter_system_audit"]["result"], "pass")
        self.assertEqual(report["intake_contract"]["contract_check_result"], "fail")
        self.assertFalse(report["first_batch_ready_for_front_filter"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertIn("first_batch_requires_intake_contract_pass_or_warn", report["issues"])
        self.assertIn("missing_candidate_universe", report["intake_contract"]["failed_contract_reason_codes"])

    def test_first_batch_readiness_allows_front_filter_only_after_ready_intake(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = audit_first_batch_readiness(fixture_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["next_action"], "action:run_front_filter")
        self.assertEqual(report["front_filter_system_audit"]["result"], "pass")
        self.assertEqual(report["intake_contract"]["contract_check_result"], "pass")
        self.assertTrue(report["first_batch_ready_for_front_filter"])
        self.assertEqual(report["front_filter_ready_candidate_count"], 1)
        self.assertEqual(
            report["front_filter_ready_candidates"],
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol_name": "Ping An Bank",
                    "candidate_stage_after": "structure_candidate",
                    "next_action": "action:run_front_filter",
                    "malf_snapshot_ref": "FIXTURE-MALF-SNAP-000001-202601",
                    "malf_snapshot_file": "ashare/malf-snapshots-v0.1/000001.SZ-2026-01.json",
                    "ashare_sample_id_suggestion": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                    "front_filter_command": "$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot <data_root>\\ashare\\malf-snapshots-v0.1\\000001.SZ-2026-01.json",
                    "record_draft_command": "$env:PYTHONPATH='src'; python -m tachibana_front_filter --snapshot <data_root>\\ashare\\malf-snapshots-v0.1\\000001.SZ-2026-01.json --record-draft --ashare-sample-id ASHARE-000001.SZ-2026-01-05-2026-01-06 --symbol-name \"Ping An Bank\"",
                }
            ],
        )
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertIn("front_filter_system_audit", report["required_audits"])
        self.assertIn("intake_contract", report["required_audits"])

    def test_first_batch_readiness_requires_a_ready_malf_snapshot(self) -> None:
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
            snapshot_dir = ashare / "malf-snapshots-v0.1"
            snapshot_dir.mkdir(parents=True)

            report = audit_first_batch_readiness(root)

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["first_batch_ready_for_front_filter"])
        self.assertEqual(report["front_filter_ready_candidate_count"], 0)
        self.assertEqual(report["front_filter_ready_candidates"], [])
        self.assertEqual(report["next_action"], "action:prepare_ready_malf_snapshot")
        self.assertIn("first_batch_requires_ready_malf_snapshot", report["issues"])
        self.assertEqual(report["intake_contract"]["contract_check_result"], "fail")

    def test_first_batch_front_filter_run_is_read_only_and_reports_structure_results(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = audit_first_batch_front_filter_run(fixture_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["front_filter_run_count"], 1)
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:review_record_drafts")
        self.assertEqual(
            report["front_filter_results"],
            [
                {
                    "ts_code": "000001.SZ",
                    "symbol_name": "Ping An Bank",
                    "ashare_sample_id_suggestion": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                    "malf_snapshot_ref": "FIXTURE-MALF-SNAP-000001-202601",
                    "malf_snapshot_file": "ashare/malf-snapshots-v0.1/000001.SZ-2026-01.json",
                    "front_filter_result": "pass",
                    "candidate_stage_after": "tachibana_candidate",
                    "rhythm_meaning": "meaningful",
                    "tachibana_applicability": "suitable",
                    "qualification_rule_id": "Q-ALIVE-CLEAN",
                    "next_action": "action:fill_qualification_record",
                    "candidate_table_update_allowed": False,
                }
            ],
        )

    def test_first_batch_record_drafts_are_read_only_and_gate_checked(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = audit_first_batch_record_drafts(fixture_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["record_draft_count"], 1)
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:manual_review_record_drafts")
        self.assertEqual(len(report["record_drafts"]), 1)
        draft = report["record_drafts"][0]
        self.assertEqual(draft["ashare_sample_id"], "ASHARE-000001.SZ-2026-01-05-2026-01-06")
        self.assertEqual(draft["ts_code"], "000001.SZ")
        self.assertEqual(draft["symbol_name"], "Ping An Bank")
        self.assertEqual(draft["front_filter_result"], "pass")
        self.assertEqual(draft["candidate_stage_after"], "tachibana_candidate")
        self.assertEqual(draft["qualification_rule_id"], "Q-ALIVE-CLEAN")
        self.assertEqual(draft["candidate_table_gate"]["result"], "pass")
        self.assertEqual(draft["record_consistency"]["result"], "pass")
        self.assertEqual(draft["cognitive_pipeline_gate"]["result"], "blocked")
        self.assertFalse(draft["cognitive_pipeline_gate"]["institution_adaptation_allowed"])
        self.assertNotIn("buy_signal", draft)
        self.assertNotIn("target_position", draft)

    def test_first_batch_sample_table_trial_maps_gate_passed_drafts_without_writing(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = audit_first_batch_sample_table_trial(fixture_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["trial_row_count"], 1)
        self.assertEqual(report["candidate_table_write_mode"], "manual_review_only")
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:manual_trial_fill_candidate_table")
        self.assertEqual(
            report["trial_rows"],
            [
                {
                    "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                    "ts_code": "000001.SZ",
                    "symbol_name": "Ping An Bank",
                    "sample_window_start": "2026-01-05",
                    "sample_window_end": "2026-01-06",
                    "candidate_stage": "tachibana_candidate",
                    "malf_snapshot_ref": "FIXTURE-MALF-SNAP-000001-202601",
                    "malf_background": "alive_wave",
                    "rhythm_meaning": "meaningful",
                    "tachibana_applicability": "suitable",
                    "qualification_rule_id": "Q-ALIVE-CLEAN",
                    "boundary_warning": [
                        "do_not_infer_position_size_from_malf",
                        "do_not_convert_rhythm_meaning_to_signal_accept",
                        "do_not_generate_trade_from_rhythm_meaning_only",
                    ],
                    "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
                    "next_action": "action:fill_candidate_table",
                    "candidate_table_gate_result": "pass",
                    "record_consistency_result": "pass",
                }
            ],
        )
        row = report["trial_rows"][0]
        self.assertNotIn("buy_signal", row)
        self.assertNotIn("trade_accept", row)
        self.assertNotIn("target_position", row)
        self.assertNotIn("ashare_t1_action", row)

    def test_first_batch_method_pm_readiness_requires_independent_method_review(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = audit_first_batch_method_pm_readiness(fixture_root)

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["method_pm_ready_count"], 0)
        self.assertEqual(report["method_pm_review_required_count"], 1)
        self.assertFalse(report["method_pm_auto_generation_allowed"])
        self.assertFalse(report["malf_action_backflow_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:method_pm_review")
        self.assertEqual(
            report["method_pm_review_items"],
            [
                {
                    "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                    "ts_code": "000001.SZ",
                    "symbol_name": "Ping An Bank",
                    "candidate_stage": "tachibana_candidate",
                    "rhythm_meaning": "meaningful",
                    "tachibana_applicability": "suitable",
                    "qualification_rule_id": "Q-ALIVE-CLEAN",
                    "pm_required_from_structure": False,
                    "method_pm_bridge_result": "blocked",
                    "missing_method_pm_fields": [
                        "method_action",
                        "method_status",
                        "method_reason",
                        "execution_intent",
                    ],
                    "blocked_reason_codes": [
                        "method_pm_invalid_method_action:None",
                        "method_pm_invalid_method_status:None",
                        "method_pm_requires_method_reason",
                        "method_pm_requires_execution_intent",
                    ],
                    "next_action": "action:method_pm_review",
                    "boundary_warning": [
                        "method_pm_must_be_independent_from_malf",
                        "do_not_generate_method_action_from_malf",
                        "do_not_generate_pm_action_from_malf",
                    ],
                }
            ],
        )
        self.assertEqual(report["method_pm_ready_items"], [])

    def test_first_batch_backtest_input_readiness_blocks_until_method_pm_is_ready(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = audit_first_batch_backtest_input_readiness(fixture_root)

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["backtest_input_ready_count"], 0)
        self.assertEqual(report["backtest_input_blocked_count"], 1)
        self.assertFalse(report["backtest_input_snapshot_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:method_pm_review")
        self.assertEqual(
            report["backtest_input_blocked_items"],
            [
                {
                    "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                    "ts_code": "000001.SZ",
                    "symbol_name": "Ping An Bank",
                    "candidate_stage": "tachibana_candidate",
                    "qualification_rule_id": "Q-ALIVE-CLEAN",
                    "blocker": "method_pm_not_ready",
                    "method_pm_bridge_result": "blocked",
                    "next_action": "action:method_pm_review",
                    "boundary_warning": [
                        "backtest_input_requires_independent_method_pm_plan",
                        "do_not_build_backtest_input_from_structure_only",
                        "do_not_start_institution_adaptation_before_backtest_input",
                    ],
                }
            ],
        )
        self.assertEqual(report["backtest_input_ready_items"], [])

    def test_first_batch_cognitive_pipeline_summarizes_current_blocking_layer(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = audit_first_batch_cognitive_pipeline(fixture_root)

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["current_blocking_layer"], "method_pm_readiness")
        self.assertEqual(report["next_action"], "action:method_pm_review")
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertFalse(report["structure_to_institution_transition_allowed"])
        self.assertEqual(report["pipeline_summary"]["readiness"], "pass")
        self.assertEqual(report["pipeline_summary"]["front_filter_run"], "pass")
        self.assertEqual(report["pipeline_summary"]["record_drafts"], "pass")
        self.assertEqual(report["pipeline_summary"]["sample_table_trial"], "pass")
        self.assertEqual(report["pipeline_summary"]["method_pm_readiness"], "blocked")
        self.assertEqual(report["pipeline_summary"]["backtest_input_readiness"], "blocked")
        self.assertEqual(
            report["blocking_evidence"],
            {
                "method_pm_review_required_count": 1,
                "backtest_input_blocked_count": 1,
                "backtest_input_snapshot_allowed": False,
                "method_pm_auto_generation_allowed": False,
                "malf_action_backflow_allowed": False,
            },
        )
        self.assertIn("pipeline_stops_before_institution_adaptation", report["issues"])

    def test_first_batch_cognitive_pipeline_blocks_at_readiness_for_missing_intake(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_first_batch_cognitive_pipeline(Path(tmp))

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["current_blocking_layer"], "readiness")
        self.assertEqual(report["next_action"], "action:repair_intake_package")
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertFalse(report["structure_to_institution_transition_allowed"])
        self.assertEqual(report["pipeline_summary"]["readiness"], "blocked")
        self.assertEqual(report["pipeline_summary"]["front_filter_run"], "blocked")
        self.assertEqual(report["pipeline_summary"]["backtest_input_readiness"], "blocked")
        self.assertEqual(report["blocking_evidence"]["method_pm_review_required_count"], 0)
        self.assertEqual(report["blocking_evidence"]["backtest_input_blocked_count"], 0)

    def test_method_pm_plan_draft_contract_accepts_independent_wait_plan(self) -> None:
        draft = {
            "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
            "ts_code": "000001.SZ",
            "method_action": "wait_no_action",
            "method_status": "hypothesis",
            "method_reason": ["structure_suitable_but_no_action_yet"],
            "pm_required": False,
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "hold",
            "method_evidence_ref": ["manual:method-review-001"],
        }

        report = audit_method_pm_plan_draft_contract(draft)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["method_pm_bridge_gate"]["result"], "pass")
        self.assertEqual(report["next_action"], "action:build_backtest_input_snapshot")
        self.assertFalse(report["malf_action_backflow_allowed"])
        self.assertFalse(report["method_pm_auto_generation_allowed"])
        self.assertEqual(report["required_fields_checked"], [
            "ashare_sample_id",
            "ts_code",
            "method_action",
            "method_status",
            "method_reason",
            "pm_required",
            "pm_action",
            "execution_intent",
            "execution_event_type",
            "method_evidence_ref",
        ])
        self.assertEqual(report["issues"], [])

    def test_method_pm_plan_draft_contract_blocks_malf_backflow_and_missing_evidence(self) -> None:
        draft = {
            "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
            "ts_code": "000001.SZ",
            "method_action": "inventory_rebalance",
            "method_status": "hypothesis",
            "method_reason": ["pm_review"],
            "pm_required": True,
            "pm_action": "rebalance",
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "rebalance",
            "center_position_from_malf": 10,
        }

        report = audit_method_pm_plan_draft_contract(draft)

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["next_action"], "action:method_pm_review")
        self.assertFalse(report["malf_action_backflow_allowed"])
        self.assertIn("method_pm_forbidden_field:center_position_from_malf", report["issues"])
        self.assertIn("method_pm_plan_requires_method_evidence_ref", report["issues"])
        self.assertEqual(report["method_pm_bridge_gate"]["result"], "blocked")

    def test_first_batch_method_pm_plan_merge_promotes_matching_manual_plan_to_backtest_input_ready(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            plan_dir = Path(tmp)
            (plan_dir / "000001-method-pm-plan.json").write_text(
                json.dumps(
                    {
                        "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                        "ts_code": "000001.SZ",
                        "method_action": "wait_no_action",
                        "method_status": "hypothesis",
                        "method_reason": ["structure_suitable_but_no_action_yet"],
                        "pm_required": False,
                        "execution_intent": "replay_hypothesis_plan",
                        "execution_event_type": "hold",
                        "method_evidence_ref": ["manual:method-review-001"],
                    }
                ),
                encoding="utf-8",
            )

            report = audit_first_batch_method_pm_plan_merge(fixture_root, plan_dir)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["method_pm_plan_ready_count"], 1)
        self.assertEqual(report["method_pm_plan_blocked_count"], 0)
        self.assertEqual(report["unmatched_review_count"], 0)
        self.assertEqual(report["backtest_input_ready_count"], 1)
        self.assertTrue(report["backtest_input_snapshot_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:build_backtest_input_snapshot")
        self.assertEqual(
            report["method_pm_plan_ready_items"],
            [
                {
                    "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                    "ts_code": "000001.SZ",
                    "method_action": "wait_no_action",
                    "pm_required": False,
                    "pm_action": None,
                    "execution_intent": "replay_hypothesis_plan",
                    "next_action": "action:build_backtest_input_snapshot",
                }
            ],
        )
        self.assertEqual(report["backtest_input_ready_items"][0]["next_action"], "action:build_backtest_input_snapshot")

    def test_first_batch_method_pm_plan_merge_blocks_unmatched_review_items(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_first_batch_method_pm_plan_merge(fixture_root, Path(tmp))

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["method_pm_plan_ready_count"], 0)
        self.assertEqual(report["method_pm_plan_blocked_count"], 0)
        self.assertEqual(report["unmatched_review_count"], 1)
        self.assertFalse(report["backtest_input_snapshot_allowed"])
        self.assertEqual(report["next_action"], "action:method_pm_review")

    def test_first_batch_backtest_input_snapshot_drafts_are_clean_read_only_adapter_records(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            plan_dir = Path(tmp)
            (plan_dir / "000001-method-pm-plan.json").write_text(
                json.dumps(
                    {
                        "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                        "ts_code": "000001.SZ",
                        "method_action": "wait_no_action",
                        "method_status": "hypothesis",
                        "method_reason": ["structure_suitable_but_no_action_yet"],
                        "pm_required": False,
                        "execution_intent": "replay_hypothesis_plan",
                        "execution_event_type": "hold",
                        "method_evidence_ref": ["manual:method-review-001"],
                    }
                ),
                encoding="utf-8",
            )

            report = audit_first_batch_backtest_input_snapshot_drafts(fixture_root, plan_dir)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["backtest_input_snapshot_count"], 1)
        self.assertTrue(report["backtest_input_snapshot_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:institution_constraint_gate_review")

        snapshot = report["backtest_input_snapshots"][0]
        self.assertEqual(snapshot["adapter_version"], "tachibana_backtest_input_v0.1")
        self.assertEqual(snapshot["snapshot_granularity"], "event_row")
        self.assertEqual(snapshot["mode"], "hypothesis_replay")
        self.assertEqual(snapshot["ashare_sample_id"], "ASHARE-000001.SZ-2026-01-05-2026-01-06")
        self.assertEqual(snapshot["sample_id"], "ASHARE-000001.SZ-2026-01-05-2026-01-06")
        self.assertEqual(snapshot["ts_code"], "000001.SZ")
        self.assertEqual(snapshot["symbol"], "000001.SZ")
        self.assertEqual(snapshot["symbol_name"], "Ping An Bank")
        self.assertEqual(snapshot["candidate_stage"], "tachibana_candidate")
        self.assertEqual(snapshot["malf_snapshot_ref"], "FIXTURE-MALF-SNAP-000001-202601")
        self.assertEqual(snapshot["malf_background"], "alive_wave")
        self.assertEqual(snapshot["rhythm_meaning"], "meaningful")
        self.assertEqual(snapshot["tachibana_applicability"], "suitable")
        self.assertEqual(snapshot["qualification_rule_id"], "Q-ALIVE-CLEAN")
        self.assertEqual(snapshot["method_action"], "wait_no_action")
        self.assertEqual(snapshot["method_status"], "hypothesis")
        self.assertEqual(snapshot["method_reason"], ["structure_suitable_but_no_action_yet"])
        self.assertFalse(snapshot["pm_required"])
        self.assertIsNone(snapshot["pm_action"])
        self.assertEqual(snapshot["execution_intent"], "replay_hypothesis_plan")
        self.assertEqual(snapshot["execution_event_type"], "hold")
        self.assertEqual(snapshot["method_evidence_ref"], ["manual:method-review-001"])
        self.assertEqual(snapshot["backtest_input_gate_result"], "pass")
        self.assertEqual(snapshot["backtest_input_gate"]["mode"], "hypothesis_replay")
        self.assertIn("do_not_treat_backtest_input_as_signal", snapshot["boundary_warning"])
        self.assertIn("do_not_start_institution_adaptation_from_snapshot", snapshot["boundary_warning"])
        for forbidden_field in ["signal_decision", "trade_accept", "target_position", "ashare_t1_action"]:
            self.assertNotIn(forbidden_field, snapshot)

    def test_first_batch_backtest_input_snapshot_drafts_block_without_matching_method_pm_plan(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_first_batch_backtest_input_snapshot_drafts(fixture_root, Path(tmp))

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["backtest_input_snapshot_count"], 0)
        self.assertEqual(report["backtest_input_snapshots"], [])
        self.assertFalse(report["backtest_input_snapshot_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["next_action"], "action:method_pm_review")
        self.assertIn("first_batch_requires_matching_valid_method_pm_plan", report["issues"])
