from tests.ashare_intake_support import *


class AshareExecutionPolicyCandidatesTest(unittest.TestCase):
    def test_execution_policy_candidates_emit_three_audit_records_for_executable_outcome(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="executable",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_candidate_count"], 3)
        self.assertEqual(report["execution_policy_candidate_blocked_count"], 0)
        self.assertEqual(report["candidate_status_counts"], {"review_required": 2, "not_triggered_in_fact_window": 1})
        self.assertEqual(report["next_action"], "action:review_execution_policy_candidates")
        candidates = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_candidates"]
        }
        self.assertEqual(candidates["t1"]["candidate_status"], "review_required")
        self.assertEqual(candidates["price_limit"]["candidate_status"], "review_required")
        self.assertEqual(candidates["price_limit"]["price_limit_event_evidence_status"], "event_fact_ready")
        self.assertEqual(
            candidates["price_limit"]["price_limit_event_evidence_reason"],
            ["planned_event_has_price_limit_bounds_without_explicit_blocking_fact"],
        )
        self.assertEqual(candidates["suspension_resume"]["candidate_status"], "not_triggered_in_fact_window")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        for candidate in report["execution_policy_candidates"]:
            self.assertEqual(candidate["record_type"], "AShareExecutionPolicyCandidateAudit")
            for forbidden_field in [
                "buy_signal",
                "sell_signal",
                "trade_accept",
                "target_position",
                "position_size",
                "ashare_t1_action",
                "limit_up_strategy",
            ]:
                self.assertNotIn(forbidden_field, candidate)

    def test_execution_policy_candidates_emit_relation_clear_for_open_center(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="executable",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        candidates = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_candidates"]
        }
        price_limit = candidates["price_limit"]
        self.assertEqual(price_limit["candidate_status"], "review_required")
        self.assertEqual(price_limit["price_limit_event_relation_status"], "relation_clear")
        self.assertEqual(
            price_limit["price_limit_event_fill_blocking_status"],
            "no_explicit_fill_blocking_fact",
        )
        self.assertEqual(
            price_limit["price_limit_event_limit_proximity"],
            "not_applicable",
        )
        self.assertEqual(
            price_limit["price_limit_event_relation_reason"],
            ["planned_event_has_no_explicit_price_limit_blocking_fact"],
        )

    def test_execution_policy_candidates_emit_relation_constrained_for_add_on(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        candidates = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_candidates"]
        }
        price_limit = candidates["price_limit"]
        self.assertEqual(price_limit["candidate_status"], "review_required")
        self.assertEqual(price_limit["price_limit_event_relation_status"], "relation_constrained")
        self.assertEqual(
            price_limit["price_limit_event_fill_blocking_status"],
            "fill_blocking_unknown",
        )
        self.assertEqual(
            price_limit["price_limit_event_limit_proximity"],
            "proximity_unknown",
        )
        self.assertEqual(
            price_limit["price_limit_event_relation_reason"],
            [
                "planned_event_limit_proximity_is_unknown",
                "planned_event_requires_higher_price_limit_resolution",
            ],
        )

    def test_execution_policy_candidates_use_reviewed_not_near_limit_relation_evidence(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )
            relation_dir = tmp_path / "price-limit-event-relations"
            write_price_limit_relation_evidence(
                relation_dir,
                sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
                ts_code="000001.SZ",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
                relation_dir,
            )

        candidates = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_candidates"]
        }
        price_limit = candidates["price_limit"]
        self.assertEqual(report["result"], "pass")
        self.assertEqual(price_limit["candidate_status"], "review_required")
        self.assertEqual(price_limit["price_limit_event_relation_status"], "relation_constrained")
        self.assertEqual(
            price_limit["price_limit_event_fill_blocking_status"],
            "fill_blocking_unknown",
        )
        self.assertEqual(
            price_limit["price_limit_event_limit_proximity"],
            "not_near_limit",
        )
        self.assertEqual(
            price_limit["price_limit_event_relation_reason"],
            [
                "planned_event_intraday_range_far_from_limit_bounds",
                "planned_event_not_near_limit_supported_by_reviewed_lc5_evidence",
            ],
        )
        self.assertIn(
            "unit-test:reviewed-lc5-evidence",
            price_limit["price_limit_event_relation_ref"],
        )

    def test_execution_policy_candidates_block_invalid_relation_evidence_enum(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )
            relation_dir = tmp_path / "price-limit-event-relations"
            write_price_limit_relation_evidence(
                relation_dir,
                sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
                ts_code="000001.SZ",
                limit_proximity="unsupported_value",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
                relation_dir,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_candidate_count"], 0)
        self.assertEqual(
            report["next_action"],
            "action:review_price_limit_event_relation_evidence",
        )
        self.assertIn("price_limit_event_relation_evidence_invalid", report["issues"])
        blocked_items = report["execution_feasibility_outcomes_report"][
            "execution_feasibility_verdict_merge"
        ]["execution_feasibility_verdict_drafts"]["execution_feasibility_gate"][
            "execution_constraint_snapshots"
        ]["execution_constraint_snapshot_blocked_items"]
        self.assertEqual(
            blocked_items[0]["issues"],
            ["invalid_price_limit_event_relation_evidence_enum:price_limit_event_limit_proximity"],
        )

    def test_reviewed_relation_evidence_keeps_trading_fields_disabled(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )
            relation_dir = tmp_path / "price-limit-event-relations"
            write_price_limit_relation_evidence(
                relation_dir,
                sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
                ts_code="000001.SZ",
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
                relation_dir,
            )

        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        for candidate in report["execution_policy_candidates"]:
            self.assertFalse(candidate["institution_rule_definition_allowed"])
            self.assertFalse(candidate["signal_generation_allowed"])
            self.assertFalse(candidate["backtest_execution_allowed"])
            for forbidden_field in [
                "trade_accept",
                "position_size",
                "limit_up_strategy",
                "limit_down_strategy",
            ]:
                self.assertNotIn(forbidden_field, candidate)

    def test_execution_policy_candidates_keep_price_limit_evidence_incomplete_when_bounds_missing(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="executable",
            )
            fact_path = fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv"
            write_csv(
                fact_path,
                INSTITUTION_FACT_HEADER,
                [[
                    "000001.SZ",
                    "2026-01-06",
                    "true",
                    "false",
                    "",
                    "",
                    "unknown",
                    "unknown",
                    "100",
                    "unit-test:exchange-calendar-and-price-limit",
                ]],
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        candidates = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_candidates"]
        }
        self.assertEqual(candidates["price_limit"]["candidate_status"], "evidence_incomplete")
        self.assertEqual(candidates["price_limit"]["price_limit_event_evidence_status"], "event_fact_missing")
        self.assertEqual(
            candidates["price_limit"]["price_limit_event_evidence_reason"],
            ["planned_event_missing_price_limit_bounds"],
        )
        self.assertEqual(candidates["price_limit"]["price_limit_event_relation_status"], "relation_unknown")
        self.assertEqual(
            candidates["price_limit"]["price_limit_event_fill_blocking_status"],
            "fill_blocking_unknown",
        )

    def test_execution_policy_candidates_emit_relation_blocked_when_suspended(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="executable",
            )
            fact_path = fact_root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv"
            write_csv(
                fact_path,
                INSTITUTION_FACT_HEADER,
                [[
                    "000001.SZ",
                    "2026-01-06",
                    "true",
                    "true",
                    "12.10",
                    "9.90",
                    "unknown",
                    "unknown",
                    "100",
                    "unit-test:suspended",
                ]],
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        candidates = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_candidates"]
        }
        price_limit = candidates["price_limit"]
        self.assertEqual(price_limit["candidate_status"], "evidence_incomplete")
        self.assertEqual(price_limit["price_limit_event_relation_status"], "relation_blocked")
        self.assertEqual(
            price_limit["price_limit_event_fill_blocking_status"],
            "explicit_fill_blocking_fact",
        )

    def test_execution_policy_candidates_emit_three_audit_records_for_constrained_outcome(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_candidate_count"], 3)
        self.assertEqual(report["candidate_status_counts"]["review_required"], 2)
        self.assertEqual(report["next_action"], "action:review_execution_policy_candidates")

    def test_execution_policy_candidates_block_items_for_carry_forward_required_outcome(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="lock_candidate",
                method_action="wait_no_action",
                pm_action="lock_candidate",
                feasibility_status="carry_forward_required",
                verdict_reason=["manual_followup_required"],
                blocked_reason=["awaiting_execution_evidence"],
                carry_forward_required=True,
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_candidate_count"], 0)
        self.assertEqual(report["execution_policy_candidate_blocked_count"], 1)
        self.assertEqual(
            report["execution_policy_candidate_blocked_items"][0]["issues"],
            ["execution_policy_candidates_require_additional_execution_evidence"],
        )
        self.assertEqual(report["next_action"], "action:collect_additional_execution_evidence")

    def test_execution_policy_candidates_return_verdict_review_when_not_evaluated(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, review_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="not_evaluated",
                verdict_reason=["manual_review_left_open"],
            )

            report = audit_first_batch_execution_policy_candidates(
                fixture_root,
                plan_dir,
                fact_root,
                review_dir,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_candidate_count"], 0)
        self.assertEqual(report["execution_policy_candidate_blocked_count"], 1)
        self.assertEqual(
            report["execution_policy_candidate_blocked_items"][0]["issues"],
            ["execution_policy_candidates_require_manual_verdict"],
        )
        self.assertEqual(report["next_action"], "action:review_execution_feasibility_verdicts")
