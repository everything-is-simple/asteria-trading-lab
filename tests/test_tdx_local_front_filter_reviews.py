from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalFrontFilterReviewsTest(TdxLocalFirstBatchSupport):
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


