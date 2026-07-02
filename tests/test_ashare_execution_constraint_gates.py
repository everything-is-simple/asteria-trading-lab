from tests.ashare_intake_support import *


class AshareExecutionConstraintGatesTest(unittest.TestCase):
    def test_first_batch_institution_constraint_gate_allows_audit_scope_only_after_backtest_input(self) -> None:
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

            report = audit_first_batch_institution_constraint_gate(fixture_root, plan_dir)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_gate_count"], 1)
        self.assertTrue(report["institution_constraint_audit_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertEqual(report["next_action"], "action:start_institution_constraint_audit")

        gate_item = report["institution_gate_items"][0]
        self.assertEqual(gate_item["ashare_sample_id"], "ASHARE-000001.SZ-2026-01-05-2026-01-06")
        self.assertEqual(gate_item["gate_status"], "pass")
        self.assertEqual(gate_item["allowed_constraint_scope"], ["execution_feasibility_audit"])
        self.assertEqual(gate_item["backtest_input_gate_result"], "pass")
        self.assertEqual(gate_item["institution_constraint_need"], "execution_feasibility")
        self.assertIn("do_not_define_t1_or_limit_rules_in_gate", gate_item["boundary_warning"])
        self.assertIn("do_not_rewrite_structure_from_institution_constraint", gate_item["boundary_warning"])
        for forbidden_field in ["ashare_t1_action", "limit_up_strategy", "trade_accept", "signal_decision"]:
            self.assertNotIn(forbidden_field, gate_item)

    def test_institution_constraint_gate_blocks_if_snapshot_already_contains_institution_rules(self) -> None:
        snapshot = {
            "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
            "ts_code": "000001.SZ",
            "malf_snapshot_ref": "FIXTURE-MALF-SNAP-000001-202601",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "method_pm_bridge_gate": {"result": "pass"},
            "backtest_input_gate": {"result": "pass"},
            "backtest_input_gate_result": "pass",
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "hold",
            "ashare_t1_action": "sell_next_day",
        }

        report = audit_first_batch_institution_constraint_gate(
            ROOT / "tests" / "fixtures" / "ashare-intake-ready",
            None,
            backtest_input_snapshots=[snapshot],
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["institution_gate_blocked_count"], 1)
        self.assertFalse(report["institution_constraint_audit_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertIn("institution_gate_forbidden_field:ashare_t1_action", report["institution_gate_blocked_items"][0]["issues"])
        self.assertEqual(report["next_action"], "action:clean_backtest_input_snapshot")

    def test_first_batch_institution_feasibility_records_are_pending_evidence_only(self) -> None:
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

            report = audit_first_batch_institution_feasibility_records(fixture_root, plan_dir)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_feasibility_record_count"], 1)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:collect_institution_constraint_evidence")

        record = report["institution_feasibility_records"][0]
        self.assertEqual(record["record_type"], "AShareExecutionFeasibilityAudit")
        self.assertEqual(record["ashare_sample_id"], "ASHARE-000001.SZ-2026-01-05-2026-01-06")
        self.assertEqual(record["planned_event"], "hold")
        self.assertEqual(record["executable_status"], "pending_constraint_evidence")
        self.assertEqual(record["blocked_reason"], ["institution_constraint_evidence_not_loaded"])
        self.assertTrue(record["carry_forward_required"])
        self.assertEqual(record["constraint_snapshot_ref"], None)
        self.assertEqual(record["allowed_constraint_scope"], ["execution_feasibility_audit"])
        self.assertIn("do_not_convert_pending_evidence_to_rule", record["boundary_warning"])
        for forbidden_field in ["signal_decision", "trade_accept", "target_position", "structure_suitable", "rhythm_meaning"]:
            self.assertNotIn(forbidden_field, record)

    def test_institution_feasibility_records_block_before_institution_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = audit_first_batch_institution_feasibility_records(Path(tmp), Path(tmp))

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["institution_feasibility_record_count"], 0)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertEqual(report["next_action"], "action:repair_intake_package")

    def test_execution_constraint_snapshots_link_fact_rows_to_planned_events_without_rules(self) -> None:
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

            report = audit_first_batch_execution_constraint_snapshots(fixture_root, plan_dir, fact_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_constraint_snapshot_count"], 1)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_execution_constraint_snapshots")

        snapshot = report["execution_constraint_snapshots"][0]
        self.assertEqual(snapshot["record_type"], "AShareExecutionConstraintSnapshot")
        self.assertEqual(snapshot["constraint_ref"], "ASHARE-CONSTRAINT-000001.SZ-2026-01-06-v0.1")
        self.assertEqual(snapshot["ts_code"], "000001.SZ")
        self.assertEqual(snapshot["trade_date"], "2026-01-06")
        self.assertEqual(snapshot["constraint_type"], ["trading_calendar", "price_limit", "board_lot"])
        self.assertEqual(snapshot["affected_execution_event"], "hold")
        self.assertEqual(snapshot["evidence_ref"], ["unit-test:exchange-calendar-and-price-limit"])
        self.assertEqual(snapshot["executable_status"], "not_evaluated")
        self.assertIn("do_not_infer_executability_from_constraint_snapshot", snapshot["boundary_warning"])
        for forbidden_field in ["trade_accept", "signal_decision", "target_position", "ashare_t1_action", "limit_up_strategy"]:
            self.assertNotIn(forbidden_field, snapshot)

    def test_execution_constraint_snapshots_block_without_fact_package(self) -> None:
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

            report = audit_first_batch_execution_constraint_snapshots(fixture_root, plan_dir, Path(tmp) / "missing-facts")

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_constraint_snapshot_count"], 0)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertEqual(report["next_action"], "action:repair_institution_fact_package")
