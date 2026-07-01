from tests.ashare_intake_support import *


class AshareExecutionFeasibilityPipelineTest(unittest.TestCase):
    def test_execution_feasibility_gate_marks_evidence_ready_without_trade_decision(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            plan_dir = Path(tmp) / "plans"
            plan_dir.mkdir()
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
            fact_root = Path(tmp) / "facts"
            write_csv(
                fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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

            report = audit_first_batch_execution_feasibility_gate(fixture_root, plan_dir, fact_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_gate_count"], 1)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:manual_review_execution_feasibility")

        item = report["execution_feasibility_gate_items"][0]
        self.assertEqual(item["record_type"], "AShareExecutionFeasibilityAudit")
        self.assertEqual(item["ashare_sample_id"], "ASHARE-000001.SZ-2026-01-05-2026-01-06")
        self.assertEqual(item["planned_event"], "hold")
        self.assertEqual(item["constraint_snapshot_ref"], "ASHARE-CONSTRAINT-000001.SZ-2026-01-06-v0.1")
        self.assertEqual(item["executable_status"], "evidence_ready")
        self.assertEqual(item["blocked_reason"], [])
        self.assertFalse(item["carry_forward_required"])
        self.assertIn("do_not_convert_evidence_ready_to_trade_accept", item["boundary_warning"])
        for forbidden_field in ["trade_accept", "signal_decision", "target_position", "position_size"]:
            self.assertNotIn(forbidden_field, item)

    def test_execution_feasibility_gate_blocks_without_constraint_snapshot(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            plan_dir = Path(tmp) / "plans"
            plan_dir.mkdir()
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

            report = audit_first_batch_execution_feasibility_gate(fixture_root, plan_dir, Path(tmp) / "missing-facts")

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_feasibility_gate_count"], 0)
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:repair_institution_fact_package")

    def test_execution_feasibility_verdicts_emit_audit_only_verdicts(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            plan_dir = Path(tmp) / "plans"
            plan_dir.mkdir()
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
            fact_root = Path(tmp) / "facts"
            write_csv(
                fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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

            report = audit_first_batch_execution_feasibility_verdicts(fixture_root, plan_dir, fact_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_verdict_count"], 1)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_execution_feasibility_verdicts")

        verdict = report["execution_feasibility_verdicts"][0]
        self.assertEqual(verdict["record_type"], "AShareExecutionFeasibilityVerdict")
        self.assertEqual(verdict["ashare_sample_id"], "ASHARE-000001.SZ-2026-01-05-2026-01-06")
        self.assertEqual(verdict["planned_event"], "hold")
        self.assertEqual(verdict["constraint_snapshot_ref"], "ASHARE-CONSTRAINT-000001.SZ-2026-01-06-v0.1")
        self.assertEqual(verdict["evidence_status"], "evidence_ready")
        self.assertEqual(verdict["feasibility_status"], "not_evaluated")
        self.assertEqual(verdict["allowed_feasibility_statuses"], [
            "not_evaluated",
            "evidence_ready",
            "executable",
            "constrained",
            "blocked",
            "carry_forward_required",
            "blocked_by_fact_review",
        ])
        self.assertEqual(verdict["verdict_source"], "manual_review_required")
        self.assertIn("manual_verdict_must_not_be_trade_accept", verdict["boundary_warning"])
        for forbidden_field in [
            "buy_signal",
            "sell_signal",
            "trade_accept",
            "target_position",
            "position_size",
            "ashare_t1_action",
            "limit_up_strategy",
        ]:
            self.assertNotIn(forbidden_field, verdict)

    def test_execution_feasibility_verdicts_block_before_evidence_ready(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            plan_dir = Path(tmp) / "plans"
            plan_dir.mkdir()
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

            report = audit_first_batch_execution_feasibility_verdicts(fixture_root, plan_dir, Path(tmp) / "missing-facts")

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_feasibility_verdict_count"], 0)
        self.assertEqual(report["execution_feasibility_verdicts"], [])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:repair_institution_fact_package")

    def test_execution_feasibility_verdict_merge_applies_manual_review_status_without_trade_fields(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir = tmp_path / "plans"
            plan_dir.mkdir()
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
            fact_root = tmp_path / "facts"
            write_csv(
                fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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
            review_dir = tmp_path / "execution-verdicts"
            review_dir.mkdir()
            (review_dir / "000001-execution-feasibility-verdict.json").write_text(
                json.dumps(
                    {
                        "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                        "ts_code": "000001.SZ",
                        "feasibility_status": "constrained",
                        "verdict_reason": ["manual_constraint_confirmed"],
                        "blocked_reason": ["board_lot_needs_rounding_review"],
                        "evidence_ref": ["manual:execution-verdict-001"],
                    }
                ),
                encoding="utf-8",
            )

            report = audit_first_batch_execution_feasibility_verdict_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_verdict_ready_count"], 1)
        self.assertEqual(report["execution_feasibility_verdict_blocked_count"], 0)
        self.assertEqual(report["unmatched_review_count"], 0)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_execution_feasibility_outcome")
        verdict = report["execution_feasibility_verdicts"][0]
        self.assertEqual(verdict["feasibility_status"], "constrained")
        self.assertEqual(verdict["verdict_source"], "manual_review")
        self.assertEqual(verdict["verdict_reason"], ["manual_constraint_confirmed"])
        self.assertEqual(verdict["blocked_reason"], ["board_lot_needs_rounding_review"])
        self.assertIn("manual:execution-verdict-001", verdict["evidence_ref"])
        for forbidden_field in [
            "buy_signal",
            "sell_signal",
            "trade_accept",
            "target_position",
            "position_size",
            "ashare_t1_action",
            "limit_up_strategy",
        ]:
            self.assertNotIn(forbidden_field, verdict)

    def test_execution_feasibility_verdict_merge_blocks_invalid_manual_status(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir = tmp_path / "plans"
            plan_dir.mkdir()
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
            fact_root = tmp_path / "facts"
            write_csv(
                fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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
            review_dir = tmp_path / "execution-verdicts"
            review_dir.mkdir()
            (review_dir / "000001-execution-feasibility-verdict.json").write_text(
                json.dumps(
                    {
                        "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                        "ts_code": "000001.SZ",
                        "feasibility_status": "evidence_ready",
                        "verdict_reason": ["manual_status_must_not_reuse_system_state"],
                    }
                ),
                encoding="utf-8",
            )

            report = audit_first_batch_execution_feasibility_verdict_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_feasibility_verdict_ready_count"], 0)
        self.assertEqual(report["execution_feasibility_verdict_blocked_count"], 1)
        self.assertEqual(report["unmatched_review_count"], 0)
        self.assertEqual(report["next_action"], "action:review_execution_feasibility_verdicts")
        self.assertIn(
            "execution_feasibility_verdict_invalid_status:evidence_ready",
            report["execution_feasibility_verdict_blocked_items"][0]["issues"],
        )

    def test_execution_feasibility_outcomes_emit_read_only_outcome_records(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir = tmp_path / "plans"
            plan_dir.mkdir()
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
            fact_root = tmp_path / "facts"
            write_csv(
                fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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
            review_dir = tmp_path / "execution-verdicts"
            review_dir.mkdir()
            (review_dir / "000001-execution-feasibility-verdict.json").write_text(
                json.dumps(
                    {
                        "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                        "ts_code": "000001.SZ",
                        "feasibility_status": "executable",
                        "verdict_reason": ["manual_execution_path_is_clear"],
                    }
                ),
                encoding="utf-8",
            )

            report = audit_first_batch_execution_feasibility_outcomes(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_outcome_count"], 1)
        self.assertEqual(report["outcome_status_counts"], {"executable": 1})
        self.assertEqual(report["next_action"], "action:review_execution_policy_candidates")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        outcome = report["execution_feasibility_outcomes"][0]
        self.assertEqual(outcome["record_type"], "AShareExecutionFeasibilityOutcome")
        self.assertEqual(outcome["feasibility_status"], "executable")
        self.assertEqual(outcome["outcome_source"], "execution_feasibility_verdict_merge")
        self.assertEqual(outcome["next_action"], "action:review_execution_policy_candidates")
        self.assertEqual(outcome["outcome_note"], "execution_fact_outcome_ready_for_policy_candidate_review")
        for forbidden_field in [
            "buy_signal",
            "sell_signal",
            "trade_accept",
            "target_position",
            "position_size",
            "ashare_t1_action",
            "limit_up_strategy",
        ]:
            self.assertNotIn(forbidden_field, outcome)

    def test_execution_feasibility_outcomes_map_carry_forward_action(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir = tmp_path / "plans"
            plan_dir.mkdir()
            (plan_dir / "000001.SZ-method-pm-plan.json").write_text(
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
            fact_root = tmp_path / "facts"
            write_csv(
                fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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
            review_dir = tmp_path / "execution-verdicts"
            review_dir.mkdir()
            (review_dir / "000001-execution-feasibility-verdict.json").write_text(
                json.dumps(
                    {
                        "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                        "ts_code": "000001.SZ",
                        "feasibility_status": "carry_forward_required",
                        "verdict_reason": ["manual_followup_required"],
                    }
                ),
                encoding="utf-8",
            )

            report = audit_first_batch_execution_feasibility_outcomes(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(
            report["execution_feasibility_outcomes"][0]["next_action"],
            "action:collect_additional_execution_evidence",
        )
        self.assertTrue(report["execution_feasibility_outcomes"][0]["carry_forward_required"])

    def test_execution_feasibility_outcomes_map_not_evaluated_back_to_verdict_review(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir = tmp_path / "plans"
            plan_dir.mkdir()
            (plan_dir / "000001.SZ-method-pm-plan.json").write_text(
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
            fact_root = tmp_path / "facts"
            write_csv(
                fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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
            review_dir = tmp_path / "execution-verdicts"
            review_dir.mkdir()
            (review_dir / "000001-execution-feasibility-verdict.json").write_text(
                json.dumps(
                    {
                        "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
                        "ts_code": "000001.SZ",
                        "feasibility_status": "not_evaluated",
                        "verdict_reason": ["manual_review_left_open"],
                    }
                ),
                encoding="utf-8",
            )

            report = audit_first_batch_execution_feasibility_outcomes(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(
            report["execution_feasibility_outcomes"][0]["next_action"],
            "action:review_execution_feasibility_verdicts",
        )
        self.assertFalse(report["execution_feasibility_outcomes"][0]["carry_forward_required"])

    def test_execution_feasibility_outcomes_block_when_verdict_merge_blocks(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir = tmp_path / "plans"
            plan_dir.mkdir()
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

            report = audit_first_batch_execution_feasibility_outcomes(
                fixture_root,
                plan_dir,
                Path(tmp) / "missing-facts",
                Path(tmp) / "missing-reviews",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_feasibility_outcome_count"], 0)
        self.assertEqual(report["execution_feasibility_outcomes"], [])
        self.assertEqual(report["next_action"], "action:repair_institution_fact_package")
