from tests.ashare_intake_support import *


class AshareExecutionPolicyReviewArchiveTest(unittest.TestCase):
    def test_execution_policy_review_merge_creates_manual_and_auto_review_records(self) -> None:
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

            report = audit_first_batch_execution_policy_review_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_review_count"], 3)
        self.assertEqual(report["execution_policy_review_blocked_count"], 0)
        self.assertEqual(report["execution_policy_review_unmatched_count"], 0)
        self.assertEqual(
            report["review_status_counts"],
            {
                "review_required": 2,
                "carry_forward_required": 1,
            },
        )
        self.assertEqual(report["next_action"], "action:review_execution_policy_archive")
        reviews = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_reviews"]
        }
        self.assertEqual(reviews["t1"]["review_source"], "manual_review")
        self.assertEqual(reviews["price_limit"]["review_source"], "manual_review")
        self.assertEqual(reviews["suspension_resume"]["review_source"], "auto_carry_forward_from_not_triggered_fact_window")
        self.assertEqual(reviews["suspension_resume"]["review_status"], "carry_forward_required")
        for review in report["execution_policy_reviews"]:
            self.assertEqual(review["record_type"], "AShareExecutionPolicyCandidateReview")
            for forbidden_field in [
                "buy_signal",
                "sell_signal",
                "trade_accept",
                "target_position",
                "position_size",
                "ashare_t1_action",
                "limit_up_strategy",
            ]:
                self.assertNotIn(forbidden_field, review)

    def test_execution_policy_review_merge_blocks_when_required_manual_review_missing(self) -> None:
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
                        "review_status": "evidence_incomplete",
                        "review_reason": ["price_limit_state_still_unknown_on_planned_event"],
                    }
                ],
            )

            report = audit_first_batch_execution_policy_review_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_review_count"], 0)
        self.assertEqual(report["execution_policy_review_unmatched_count"], 1)
        self.assertIn(
            "execution_policy_review_missing_required_candidate_review:t1",
            report["execution_policy_review_unmatched_items"][0]["issues"],
        )
        self.assertEqual(report["next_action"], "action:review_execution_policy_candidates")

    def test_execution_policy_review_merge_blocks_invalid_candidate_constraint_type(self) -> None:
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
                        "candidate_constraint_type": "board_lot",
                        "review_status": "review_required",
                        "review_reason": ["unsupported_candidate_type"],
                    },
                    {
                        "candidate_constraint_type": "price_limit",
                        "review_status": "review_required",
                        "review_reason": ["price_limit_event_fact_ready_for_policy_research"],
                    },
                ],
            )

            report = audit_first_batch_execution_policy_review_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_review_blocked_count"], 1)
        self.assertIn(
            "execution_policy_review_invalid_candidate_constraint_type:board_lot",
            report["execution_policy_review_blocked_items"][0]["issues"],
        )

    def test_execution_policy_review_merge_blocks_invalid_review_status(self) -> None:
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
                        "review_status": "not_triggered_in_fact_window",
                        "review_reason": ["invalid_manual_status"],
                    },
                    {
                        "candidate_constraint_type": "price_limit",
                        "review_status": "review_required",
                        "review_reason": ["price_limit_event_fact_ready_for_policy_research"],
                    },
                ],
            )

            report = audit_first_batch_execution_policy_review_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_review_blocked_count"], 1)
        self.assertIn(
            "execution_policy_review_invalid_review_status:not_triggered_in_fact_window",
            report["execution_policy_review_blocked_items"][0]["issues"],
        )

    def test_execution_policy_review_merge_blocks_on_ts_code_mismatch(self) -> None:
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
                ts_code="300750.SZ",
                candidate_reviews=[
                    {
                        "candidate_constraint_type": "t1",
                        "review_status": "review_required",
                        "review_reason": ["planned_event_requires_t1_policy_review"],
                    },
                    {
                        "candidate_constraint_type": "price_limit",
                        "review_status": "evidence_incomplete",
                        "review_reason": ["price_limit_state_still_unknown_on_planned_event"],
                    },
                ],
            )

            report = audit_first_batch_execution_policy_review_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_review_blocked_count"], 1)
        self.assertIn(
            "execution_policy_review_ts_code_mismatch",
            report["execution_policy_review_blocked_items"][0]["issues"],
        )

    def test_execution_policy_review_merge_preserves_blocked_outcome_items_without_review_records(self) -> None:
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

            report = audit_first_batch_execution_policy_review_merge(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_review_count"], 0)
        self.assertEqual(report["execution_policy_review_blocked_count"], 1)
        self.assertEqual(
            report["execution_policy_review_blocked_items"][0]["issues"],
            ["execution_policy_candidates_require_additional_execution_evidence"],
        )
        self.assertEqual(report["next_action"], "action:collect_additional_execution_evidence")

    def test_execution_policy_archive_creates_read_only_archive_records(self) -> None:
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

            report = audit_first_batch_execution_policy_archive(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_archive_count"], 3)
        self.assertEqual(report["execution_policy_archive_blocked_count"], 0)
        self.assertEqual(
            report["archive_status_counts"],
            {
                "review_required": 2,
                "carry_forward_required": 1,
            },
        )
        self.assertEqual(report["next_action"], "action:prepare_execution_policy_research")
        archives = {
            item["candidate_constraint_type"]: item
            for item in report["execution_policy_archives"]
        }
        self.assertEqual(archives["t1"]["record_type"], "AShareExecutionPolicyArchive")
        self.assertEqual(archives["t1"]["archive_source"], "execution_policy_review_merge")
        self.assertEqual(
            archives["t1"]["archive_reason"],
            ["execution_policy_candidate_archived_for_policy_research"],
        )
        self.assertEqual(archives["t1"]["next_action"], "action:prepare_execution_policy_research")
        self.assertEqual(
            archives["price_limit"]["archive_reason"],
            ["execution_policy_candidate_archived_for_policy_research"],
        )
        self.assertEqual(
            archives["price_limit"]["next_action"],
            "action:prepare_execution_policy_research",
        )
        self.assertEqual(
            archives["suspension_resume"]["archive_reason"],
            ["execution_policy_candidate_archived_for_carry_forward"],
        )
        self.assertEqual(
            archives["suspension_resume"]["next_action"],
            "action:collect_additional_execution_evidence",
        )
        for archive in report["execution_policy_archives"]:
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
                self.assertNotIn(forbidden_field, archive)

    def test_execution_policy_archive_preserves_upstream_blocked_items(self) -> None:
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

            report = audit_first_batch_execution_policy_archive(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_archive_count"], 0)
        self.assertEqual(report["execution_policy_archive_blocked_count"], 1)
        self.assertEqual(
            report["execution_policy_archive_blocked_items"][0]["issues"],
            ["execution_policy_candidates_require_additional_execution_evidence"],
        )
        self.assertEqual(report["next_action"], "action:collect_additional_execution_evidence")

    def test_execution_policy_archive_blocks_when_review_merge_blocks(self) -> None:
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
                        "review_status": "evidence_incomplete",
                        "review_reason": ["price_limit_state_still_unknown_on_planned_event"],
                    }
                ],
            )

            report = audit_first_batch_execution_policy_archive(
                fixture_root,
                plan_dir,
                fact_root,
                review_root,
            )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["execution_policy_archive_count"], 0)
        self.assertEqual(report["execution_policy_archives"], [])
        self.assertEqual(report["next_action"], "action:review_execution_policy_candidates")
        self.assertEqual(
            report["issues"],
            ["execution_policy_archive_requires_valid_execution_policy_reviews"],
        )
