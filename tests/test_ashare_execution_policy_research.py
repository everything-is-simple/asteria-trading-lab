from tests.ashare_intake_support import *


class AshareExecutionPolicyResearchTest(unittest.TestCase):
    def test_execution_policy_research_prep_creates_read_only_prep_records(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, verdict_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="executable",
            )
            review_root = tmp_path / "policy-reviews"
            write_execution_policy_review_file(
                review_root,
                sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
                ts_code="000001.SZ",
                candidate_reviews=[
                    {
                        "candidate_constraint_type": "t1",
                        "review_status": "review_required",
                        "review_reason": ["planned_event_requires_t1_policy_review"],
                        "blocked_reason": [],
                        "evidence_ref": ["ASHARE-CONSTRAINT-000001.SZ-2026-01-06-v0.1"],
                    },
                    {
                        "candidate_constraint_type": "price_limit",
                        "review_status": "review_required",
                        "review_reason": ["price_limit_event_fact_ready_for_policy_research"],
                        "blocked_reason": [],
                        "evidence_ref": ["ASHARE-CONSTRAINT-000001.SZ-2026-01-06-v0.1"],
                    },
                ],
            )

            report = audit_first_batch_execution_policy_research_prep(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_research_prep_count"], 3)
        self.assertEqual(report["execution_policy_research_prep_blocked_count"], 0)
        self.assertEqual(
            report["research_prep_status_counts"],
            {
                "review_required": 2,
                "carry_forward_required": 1,
            },
        )
        self.assertEqual(report["next_action"], "action:prepare_execution_policy_research")
        preps = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_research_preps"]
        }
        self.assertEqual(preps["t1"]["record_type"], "AShareExecutionPolicyResearchPrep")
        self.assertEqual(preps["t1"]["research_prep_source"], "execution_policy_archive")
        self.assertEqual(
            preps["t1"]["research_prep_reason"],
            ["execution_policy_candidate_ready_for_research_preparation"],
        )
        self.assertEqual(preps["t1"]["next_action"], "action:prepare_execution_policy_research")
        self.assertEqual(
            preps["price_limit"]["research_prep_reason"],
            ["execution_policy_candidate_ready_for_research_preparation"],
        )
        self.assertEqual(
            preps["price_limit"]["next_action"],
            "action:prepare_execution_policy_research",
        )
        self.assertEqual(
            preps["suspension_resume"]["research_prep_reason"],
            ["execution_policy_candidate_research_preparation_carry_forward"],
        )
        self.assertEqual(
            preps["suspension_resume"]["next_action"],
            "action:collect_additional_execution_evidence",
        )
        for prep in report["execution_policy_research_preps"]:
            for forbidden_field in [
                "buy_signal",
                "sell_signal",
                "trade_accept",
                "target_position",
                "position_size",
                "ashare_t1_action",
                "limit_up_strategy",
                "limit_down_strategy",
            ]:
                self.assertNotIn(forbidden_field, prep)

    def test_execution_policy_research_agenda_groups_prep_records_by_constraint_type(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, verdict_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="executable",
            )
            review_root = tmp_path / "policy-reviews"
            write_execution_policy_review_file(
                review_root,
                sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
                ts_code="000001.SZ",
                candidate_reviews=[
                    {
                        "candidate_constraint_type": "t1",
                        "review_status": "review_required",
                        "review_reason": ["planned_event_requires_t1_policy_review"],
                    },
                    {
                        "candidate_constraint_type": "price_limit",
                        "review_status": "review_required",
                        "review_reason": ["price_limit_event_fact_ready_for_policy_research"],
                    },
                ],
            )

            report = audit_first_batch_execution_policy_research_agenda(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_research_agenda_count"], 3)
        agendas = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_research_agendas"]
        }
        self.assertEqual(agendas["t1"]["agenda_status"], "ready_for_research")
        self.assertEqual(agendas["t1"]["sample_count"], 1)
        self.assertEqual(agendas["price_limit"]["agenda_status"], "ready_for_research")
        self.assertEqual(agendas["suspension_resume"]["agenda_status"], "carry_forward_required")
        self.assertEqual(report["next_action"], "action:prepare_execution_policy_research")

    def test_execution_policy_research_agenda_keeps_price_limit_ready_with_relation_constrained(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, verdict_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="add_on",
                method_action="pullback_add",
                pm_action="add_on",
                feasibility_status="constrained",
                verdict_reason=["manual_constraint_confirmed"],
                blocked_reason=["limit_state_unknown_on_planned_event"],
            )
            review_root = tmp_path / "policy-reviews"
            write_execution_policy_review_file(
                review_root,
                sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
                ts_code="000001.SZ",
                candidate_reviews=[
                    {
                        "candidate_constraint_type": "t1",
                        "review_status": "review_required",
                        "review_reason": ["planned_event_requires_t1_policy_review"],
                    },
                    {
                        "candidate_constraint_type": "price_limit",
                        "review_status": "review_required",
                        "review_reason": ["price_limit_event_fact_ready_for_policy_research"],
                    }
                ],
            )

            report = audit_first_batch_execution_policy_research_agenda(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        agendas = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_research_agendas"]
        }
        self.assertEqual(agendas["price_limit"]["agenda_status"], "ready_for_research")

    def test_execution_policy_research_prep_preserves_upstream_blocked_items(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, verdict_dir = write_execution_policy_case(
                tmp_path,
                execution_event_type="lock_candidate",
                method_action="wait_no_action",
                pm_action="lock_candidate",
                feasibility_status="carry_forward_required",
                verdict_reason=["manual_followup_required"],
                blocked_reason=["awaiting_execution_evidence"],
                carry_forward_required=True,
            )
            review_root = tmp_path / "policy-reviews"

            report = audit_first_batch_execution_policy_research_prep(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_research_prep_count"], 0)
        self.assertEqual(report["execution_policy_research_prep_blocked_count"], 1)
        self.assertEqual(
            report["execution_policy_research_prep_blocked_items"][0]["issues"],
            ["execution_policy_candidates_require_additional_execution_evidence"],
        )
        self.assertEqual(report["next_action"], "action:collect_additional_execution_evidence")

    def test_execution_policy_research_prep_blocks_when_archive_blocks(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan_dir, fact_root, verdict_dir = write_execution_policy_case(
                tmp_path,
                feasibility_status="executable",
            )
            review_root = tmp_path / "policy-reviews"
            write_execution_policy_review_file(
                review_root,
                sample_id="ASHARE-000001.SZ-2026-01-05-2026-01-06",
                ts_code="000001.SZ",
                candidate_reviews=[
                    {
                        "candidate_constraint_type": "price_limit",
                        "review_status": "review_required",
                        "review_reason": ["price_limit_event_fact_ready_for_policy_research"],
                    }
                ],
            )

            report = audit_first_batch_execution_policy_research_prep(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_research_prep_count"], 0)
        self.assertEqual(report["execution_policy_research_preps"], [])
        self.assertEqual(report["next_action"], "action:review_execution_policy_candidates")
        self.assertEqual(
            report["issues"],
            ["execution_policy_research_prep_requires_valid_execution_policy_archive"],
        )

    def test_execution_policy_research_prep_blocks_unknown_archive_status(self) -> None:
        archive_item = {
            "record_type": "AShareExecutionPolicyArchive",
            "ashare_institution_gate_id": "gate-1",
            "ashare_sample_id": "ASHARE-000001.SZ-2026-01-05-2026-01-06",
            "ts_code": "000001.SZ",
            "planned_event": "open_center",
            "feasibility_status": "executable",
            "candidate_constraint_type": "t1",
            "machine_candidate_status": "review_required",
            "review_status": "review_required",
            "archive_status": "unexpected_status",
            "archive_reason": ["unexpected"],
            "blocked_reason": [],
            "constraint_snapshot_ref": "constraint-ref-1",
            "evidence_ref": ["evidence-1"],
            "review_source": "manual_review",
            "archive_source": "execution_policy_review_merge",
            "boundary_warning": [],
            "institution_rule_definition_allowed": False,
            "signal_generation_allowed": False,
            "backtest_execution_allowed": False,
            "next_action": "action:prepare_execution_policy_research",
        }

        with patch(
            "ashare_execution_policy_pipeline.audit_first_batch_execution_policy_archive",
            return_value={
                "result": "pass",
                "execution_policy_archive_count": 1,
                "execution_policy_archives": [archive_item],
                "execution_policy_archive_blocked_count": 0,
                "execution_policy_archive_blocked_items": [],
                "archive_status_counts": {"unexpected_status": 1},
                "institution_rule_definition_allowed": False,
                "signal_generation_allowed": False,
                "backtest_execution_allowed": False,
                "next_action": "action:prepare_execution_policy_research",
                "issues": [],
            },
        ):
            report = audit_first_batch_execution_policy_research_prep(
                ROOT / "tests" / "fixtures" / "ashare-intake-ready",
                Path("plans"),
                Path("facts"),
                Path("reviews"),
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_research_prep_count"], 0)
        self.assertEqual(report["execution_policy_research_prep_blocked_count"], 1)
        self.assertIn(
            "execution_policy_research_prep_invalid_archive_status:unexpected_status",
            report["execution_policy_research_prep_blocked_items"][0]["issues"],
        )
        self.assertEqual(report["next_action"], "action:collect_additional_execution_evidence")

    def test_execution_policy_research_agenda_blocks_when_prep_blocks(self) -> None:
        with patch(
            "ashare_execution_policy_pipeline.audit_first_batch_execution_policy_research_prep",
            return_value={
                "result": "blocked",
                "next_action": "action:collect_additional_execution_evidence",
                "issues": ["execution_policy_research_prep_requires_valid_execution_policy_archive"],
            },
        ):
            report = audit_first_batch_execution_policy_research_agenda(
                ROOT / "tests" / "fixtures" / "ashare-intake-ready",
                Path("plans"),
                Path("facts"),
                Path("reviews"),
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(
            report["issues"],
            ["execution_policy_research_agenda_requires_valid_research_prep"],
        )
        self.assertEqual(report["next_action"], "action:collect_additional_execution_evidence")
