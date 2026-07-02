from tests.tachibana_front_filter_support import *


class TachibanaRuntimeTest(unittest.TestCase):
    def test_alive_wave_snapshot_maps_to_meaningful_suitable_without_trade_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-ALIVE",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "alive_wave",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "wave_core_state": "alive",
                        "progress_state": "clean_directional_push",
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "pass")
        self.assertEqual(report["candidate_stage_after"], "tachibana_candidate")
        self.assertEqual(report["rhythm_meaning"], "meaningful")
        self.assertEqual(report["tachibana_applicability"], "suitable")
        self.assertEqual(report["qualification_rule_id"], "Q-ALIVE-CLEAN")
        self.assertEqual(report["next_action"], "action:fill_qualification_record")
        self.assertIn("matched_q_alive_clean", report["rule_match_reason"])
        self.assertIn("rhythm_meaning_meaningful", report["applicability_reason"])
        self.assertIn("do_not_infer_position_size_from_malf", report["boundary_warning"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_break_birth_snapshot_maps_to_limited_conditional_and_pm_required(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-BIRTH",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "break_birth",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "birth_type": "seed_after_clear",
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "pass")
        self.assertEqual(report["candidate_stage_after"], "tachibana_candidate")
        self.assertEqual(report["rhythm_meaning"], "limited")
        self.assertEqual(report["tachibana_applicability"], "conditional")
        self.assertEqual(report["qualification_rule_id"], "Q-SEED-AFTER-CLEAR")
        self.assertTrue(report["pm_required"])
        self.assertEqual(report["next_action"], "action:fill_qualification_record")
        self.assertIn("rhythm_meaning_limited", report["applicability_reason"])
        self.assertIn("do_not_merge_new_seed_into_old_segment", report["boundary_warning"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_pullback_pressure_adjustment_maps_to_limited_conditional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-PULLBACK",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "pullback",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "pressure_adjustment": True,
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "pass")
        self.assertEqual(report["rhythm_meaning"], "limited")
        self.assertEqual(report["tachibana_applicability"], "conditional")
        self.assertEqual(report["qualification_rule_id"], "Q-PRESSURE-ADJUST")
        self.assertTrue(report["pm_required"])
        self.assertIn("matched_q_pressure_adjust", report["rule_match_reason"])
        self.assertIn("do_not_merge_pressure_adjustment_into_clean_wave", report["boundary_warning"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_range_wait_maps_to_limited_conditional_without_inferred_trade(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-RANGE",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "range",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "range_state": "alive",
                        "no_trade_wait": True,
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "pass")
        self.assertEqual(report["rhythm_meaning"], "limited")
        self.assertEqual(report["tachibana_applicability"], "conditional")
        self.assertEqual(report["qualification_rule_id"], "Q-LOCK-WAIT")
        self.assertTrue(report["pm_required"])
        self.assertIn("matched_q_lock_wait", report["rule_match_reason"])
        self.assertIn("structure_no_trade_not_range", report["applicability_reason"])
        self.assertIn("do_not_infer_range_from_no_trade", report["boundary_warning"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_stagnation_clear_reset_maps_to_limited_conditional(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-STAGNATION",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "stagnation",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "exit_window": True,
                        "clear_reset": True,
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "pass")
        self.assertEqual(report["rhythm_meaning"], "limited")
        self.assertEqual(report["tachibana_applicability"], "conditional")
        self.assertEqual(report["qualification_rule_id"], "Q-CLEAR-RESET")
        self.assertTrue(report["pm_required"])
        self.assertIn("matched_q_clear_reset", report["rule_match_reason"])
        self.assertIn("do_not_encode_clear_reason_in_malf", report["boundary_warning"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_transition_source_disrupted_stays_unknown_and_blocks_method_pm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-DISRUPTED",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "transition",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "source_disrupted": True,
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "blocked")
        self.assertEqual(report["candidate_stage_after"], "structure_candidate")
        self.assertEqual(report["rhythm_meaning"], "unknown")
        self.assertEqual(report["tachibana_applicability"], "unknown")
        self.assertEqual(report["qualification_rule_id"], "Q-SOURCE-DISRUPTED")
        self.assertFalse(report["pm_required"])
        self.assertEqual(report["next_action"], "action:research_audit_only")
        self.assertIn("matched_q_source_disrupted", report["rule_match_reason"])
        self.assertIn("source_disrupted_keep_unknown", report["applicability_reason"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_ready_snapshot_without_structure_object_maps_to_not_meaningful_unsuitable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-NO-STRUCTURE",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "no_structure",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "negative_type": "NM-NO-STRUCTURE",
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "rejected")
        self.assertEqual(report["candidate_stage_after"], "rejected")
        self.assertEqual(report["rhythm_meaning"], "not_meaningful")
        self.assertEqual(report["tachibana_applicability"], "unsuitable")
        self.assertEqual(report["qualification_rule_id"], "NM-NO-STRUCTURE")
        self.assertFalse(report["pm_required"])
        self.assertEqual(report["next_action"], "action:research_audit_only")
        self.assertIn("negative_type_nm_no_structure", report["applicability_reason"])
        self.assertIn("rhythm_meaning_not_meaningful", report["applicability_reason"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_unknown_snapshot_stays_structure_candidate_and_does_not_enter_method_pm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-UNKNOWN",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "unknown",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {},
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "blocked")
        self.assertEqual(report["candidate_stage_after"], "structure_candidate")
        self.assertEqual(report["rhythm_meaning"], "unknown")
        self.assertEqual(report["tachibana_applicability"], "unknown")
        self.assertIsNone(report["qualification_rule_id"])
        self.assertFalse(report["pm_required"])
        self.assertEqual(report["next_action"], "action:keep_pending")
        self.assertIn("blocked_by_unknown_malf_background", report["rule_match_reason"])
        self.assertIn("rhythm_meaning_unknown", report["applicability_reason"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_not_ready_snapshot_stays_unknown_and_requests_malf_repair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-INCOMPLETE",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "alive_wave",
                    "snapshot_quality_status": "incomplete",
                    "wave_range_break_fields": {
                        "wave_core_state": "alive",
                    },
                    "evidence_ref": "unit-test",
                },
            )

            report = run_front_filter(snapshot_path)

        self.assertEqual(report["front_filter_result"], "blocked")
        self.assertEqual(report["candidate_stage_after"], "structure_candidate")
        self.assertEqual(report["rhythm_meaning"], "unknown")
        self.assertEqual(report["tachibana_applicability"], "unknown")
        self.assertIsNone(report["qualification_rule_id"])
        self.assertEqual(report["next_action"], "action:rerun_malf")
        self.assertIn("blocked_by_malf_snapshot_not_ready", report["rule_match_reason"])
        self.assertIn("no_ready_malf_snapshot", report["applicability_reason"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(report.keys()))

    def test_builds_qualification_record_draft_from_passed_front_filter_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-ALIVE",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "alive_wave",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "wave_core_state": "alive",
                    },
                    "evidence_ref": "unit-test",
                },
            )
            front_filter_report = run_front_filter(snapshot_path)

        draft = build_qualification_record_draft(
            front_filter_report,
            ashare_sample_id="ASHARE-FIXTURE-001",
            symbol_name="Ping An Bank",
            candidate_stage_before="structure_candidate",
        )

        self.assertEqual(draft["qualification_record_id"], "ASHARE-QUAL-000001.SZ-2026-01-05-2026-01-06-v0.1")
        self.assertEqual(draft["ashare_sample_id"], "ASHARE-FIXTURE-001")
        self.assertEqual(draft["record_status"], "draft")
        self.assertEqual(draft["candidate_stage_before"], "structure_candidate")
        self.assertEqual(draft["candidate_stage_after"], "tachibana_candidate")
        self.assertEqual(draft["rhythm_meaning"], "meaningful")
        self.assertEqual(draft["tachibana_applicability"], "suitable")
        self.assertEqual(draft["qualification_rule_id"], "Q-ALIVE-CLEAN")
        self.assertEqual(draft["rule_match_confidence"], "high")
        self.assertEqual(draft["next_action"], "action:fill_candidate_table")
        self.assertIn("E1_malf_snapshot", draft["evidence_level"])
        self.assertIn("E4_research_mapping", draft["evidence_level"])
        self.assertEqual(draft["record_consistency"]["result"], "pass")
        self.assertEqual(draft["record_consistency"]["issues"], [])
        self.assertEqual(draft["candidate_table_gate"]["result"], "pass")
        self.assertEqual(draft["candidate_table_gate"]["allowed_candidate_stage"], "tachibana_candidate")
        self.assertEqual(draft["candidate_table_gate"]["next_action"], "action:fill_candidate_table")
        self.assertEqual(draft["candidate_table_gate"]["issues"], [])
        self.assertEqual(draft["rhythm_sample_row_gate"]["result"], "pass")
        self.assertEqual(draft["rhythm_sample_row_gate"]["row_status"], "rhythm_row_ready")
        self.assertEqual(draft["rhythm_sample_row_gate"]["next_action"], "action:fill_candidate_table")
        self.assertEqual(draft["front_filter_system_audit"]["result"], "pass")
        self.assertEqual(draft["front_filter_system_audit"]["blocked_audits"], [])
        self.assertIn("record_consistency", draft["candidate_table_gate"]["required_fields_checked"])
        self.assertIn("rhythm_meaning", draft["candidate_table_gate"]["required_fields_checked"])
        self.assertIn("tachibana_applicability", draft["candidate_table_gate"]["required_fields_checked"])
        self.assertIn("qualification_rule_id", draft["candidate_table_gate"]["required_fields_checked"])
        self.assertIn("boundary_warning", draft["candidate_table_gate"]["required_fields_checked"])
        self.assertIn("evidence_level", draft["candidate_table_gate"]["required_fields_checked"])
        self.assertEqual(draft["backtest_input_gate"]["result"], "blocked")
        self.assertEqual(draft["method_pm_bridge_gate"]["result"], "blocked")
        self.assertEqual(draft["method_pm_bridge_gate"]["next_action"], "action:method_pm_review")
        self.assertEqual(draft["interface_boundary_gate"]["result"], "pass")
        self.assertEqual(draft["interface_boundary_gate"]["interface_layer"], "tachibana_adapter")
        self.assertEqual(draft["backtest_input_gate"]["mode"], "research_audit")
        self.assertEqual(draft["backtest_input_gate"]["next_action"], "action:method_pm_review")
        self.assertIn("backtest_input_requires_method_plan", draft["backtest_input_gate"]["issues"])
        self.assertEqual(draft["cognitive_pipeline_gate"]["result"], "blocked")
        self.assertEqual(draft["cognitive_pipeline_gate"]["institution_adaptation_allowed"], False)
        self.assertEqual(draft["cognitive_pipeline_gate"]["next_action"], "action:repair_data")
        self.assertIn("pipeline_requires_contract_pass_or_warn", draft["cognitive_pipeline_gate"]["issues"])
        self.assertIn("pipeline_requires_eligible_for_malf_run", draft["cognitive_pipeline_gate"]["issues"])
        self.assertIn("pipeline_requires_method_pm_bridge_gate_pass", draft["cognitive_pipeline_gate"]["issues"])
        self.assertIn("pipeline_requires_backtest_input_gate_pass", draft["cognitive_pipeline_gate"]["issues"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(draft.keys()))

    def test_rejected_front_filter_result_builds_research_audit_record_draft(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            snapshot_path = write_snapshot(
                Path(tmp),
                {
                    "malf_snapshot_ref": "SNAP-NO-STRUCTURE",
                    "ts_code": "000001.SZ",
                    "window_start": "2026-01-05",
                    "window_end": "2026-01-06",
                    "malf_background": "no_structure",
                    "snapshot_quality_status": "ready",
                    "wave_range_break_fields": {
                        "negative_type": "NM-NO-STRUCTURE",
                    },
                    "evidence_ref": "unit-test",
                },
            )
            front_filter_report = run_front_filter(snapshot_path)

        draft = build_qualification_record_draft(
            front_filter_report,
            ashare_sample_id="ASHARE-FIXTURE-REJECTED",
            symbol_name="Ping An Bank",
            candidate_stage_before="structure_candidate",
        )

        self.assertEqual(draft["record_status"], "blocked")
        self.assertEqual(draft["candidate_stage_after"], "rejected")
        self.assertEqual(draft["rhythm_meaning"], "not_meaningful")
        self.assertEqual(draft["tachibana_applicability"], "unsuitable")
        self.assertEqual(draft["qualification_rule_id"], "NM-NO-STRUCTURE")
        self.assertEqual(draft["rule_match_confidence"], "blocked")
        self.assertEqual(draft["next_action"], "action:research_audit_only")
        self.assertIn("negative_type_nm_no_structure", draft["meaning_reason"])
        self.assertEqual(draft["record_consistency"]["result"], "pass")
        self.assertEqual(draft["candidate_table_gate"]["result"], "blocked")
        self.assertEqual(draft["candidate_table_gate"]["allowed_candidate_stage"], "rejected")
        self.assertEqual(draft["candidate_table_gate"]["next_action"], "action:research_audit_only")
        self.assertIn("candidate_table_requires_tachibana_candidate", draft["candidate_table_gate"]["issues"])
        self.assertIn("candidate_table_requires_meaningful_or_limited", draft["candidate_table_gate"]["issues"])
        self.assertIn("candidate_table_requires_suitable_or_conditional", draft["candidate_table_gate"]["issues"])
        self.assertIn("candidate_table_blocks_rejected_or_unsuitable", draft["candidate_table_gate"]["issues"])
        self.assertTrue(FORBIDDEN_OUTPUT_FIELDS.isdisjoint(draft.keys()))
