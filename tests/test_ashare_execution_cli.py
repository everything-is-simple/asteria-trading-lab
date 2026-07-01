from tests.ashare_intake_support import *


class AshareExecutionCliTest(unittest.TestCase):
    def test_cli_builds_first_batch_institution_feasibility_records_without_rules(self) -> None:
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-institution-feasibility-records",
                    str(plan_dir),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_feasibility_record_count"], 1)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertEqual(report["institution_feasibility_records"][0]["executable_status"], "pending_constraint_evidence")

    def test_cli_audits_institution_fact_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_csv(
                root / "ashare" / "institution-facts-v0.1" / "000001.SZ.csv",
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(root),
                    "--audit-institution-fact-package",
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_fact_count"], 1)
        self.assertFalse(report["institution_rule_definition_allowed"])

    def test_cli_builds_execution_constraint_snapshots_without_rules(self) -> None:
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-constraint-snapshots",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_constraint_snapshot_count"], 1)
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertEqual(report["execution_constraint_snapshots"][0]["executable_status"], "not_evaluated")

    def test_cli_runs_execution_feasibility_gate_without_trade_decision(self) -> None:
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-feasibility-gate",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_gate_items"][0]["executable_status"], "evidence_ready")
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_runs_execution_feasibility_verdicts_without_trade_decision(self) -> None:
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-feasibility-verdicts",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_verdicts"][0]["feasibility_status"], "not_evaluated")
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_merges_execution_feasibility_verdict_directory(self) -> None:
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-feasibility-verdict-merge",
                    str(review_dir),
                    "--method-pm-plan-dir",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_verdicts"][0]["feasibility_status"], "executable")
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_runs_execution_feasibility_outcomes(self) -> None:
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
                    }
                ),
                encoding="utf-8",
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-feasibility-outcomes",
                    str(review_dir),
                    "--method-pm-plan-dir",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_feasibility_outcomes"][0]["feasibility_status"], "constrained")
        self.assertEqual(report["execution_feasibility_outcomes"][0]["next_action"], "action:review_execution_policy_candidates")
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_runs_execution_policy_candidates(self) -> None:
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-policy-candidates",
                    str(review_dir),
                    "--method-pm-plan-dir",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_candidate_count"], 3)
        self.assertEqual(report["candidate_status_counts"]["review_required"], 2)
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_runs_execution_policy_review_merge(self) -> None:
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
                        "review_status": "evidence_incomplete",
                        "review_reason": ["price_limit_state_still_unknown_on_planned_event"],
                    },
                ],
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-policy-review-merge",
                    str(review_root),
                    "--method-pm-plan-dir",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_review_count"], 3)
        self.assertEqual(report["review_status_counts"]["carry_forward_required"], 1)
        self.assertEqual(report["next_action"], "action:review_execution_policy_archive")
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_runs_execution_policy_archive(self) -> None:
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

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-policy-archive",
                    str(review_root),
                    "--method-pm-plan-dir",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_archive_count"], 3)
        self.assertEqual(report["archive_status_counts"]["carry_forward_required"], 1)
        self.assertEqual(report["next_action"], "action:prepare_execution_policy_research")
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_runs_execution_policy_research_prep(self) -> None:
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
                        "review_status": "evidence_incomplete",
                        "review_reason": ["price_limit_state_still_unknown_on_planned_event"],
                    },
                ],
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-policy-research-prep",
                    str(review_root),
                    "--method-pm-plan-dir",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_research_prep_count"], 3)
        self.assertEqual(report["research_prep_status_counts"]["carry_forward_required"], 1)
        self.assertEqual(report["next_action"], "action:prepare_execution_policy_research")
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_cli_runs_execution_policy_research_agenda(self) -> None:
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
                        "review_status": "evidence_incomplete",
                        "review_reason": ["price_limit_state_still_unknown_on_planned_event"],
                    }
                ],
            )

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ashare_intake_validator",
                    "--root",
                    str(fixture_root),
                    "--audit-first-batch-execution-policy-research-agenda",
                    str(review_root),
                    "--method-pm-plan-dir",
                    str(plan_dir),
                    "--institution-fact-root",
                    str(fact_root),
                ],
                cwd=ROOT,
                env={"PYTHONPATH": str(ROOT / "src")},
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["execution_policy_research_agenda_count"], 3)
