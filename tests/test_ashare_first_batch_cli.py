from tests.ashare_intake_support import *


class AshareFirstBatchCliTest(unittest.TestCase):
    def test_cli_audits_first_batch_readiness_without_upgrading_candidates(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-readiness",
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
        self.assertTrue(report["first_batch_ready_for_front_filter"])
        self.assertEqual(report["front_filter_ready_candidate_count"], 1)
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertFalse(report["intake_contract"]["eligible_for_tachibana_candidate"])

    def test_cli_runs_first_batch_front_filter_without_upgrading_candidates(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-front-filter-run",
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
        self.assertEqual(report["front_filter_run_count"], 1)
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["front_filter_results"][0]["qualification_rule_id"], "Q-ALIVE-CLEAN")
        self.assertEqual(report["front_filter_results"][0]["next_action"], "action:fill_qualification_record")

    def test_cli_audits_first_batch_record_drafts_without_writing_tables(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-record-drafts",
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
        self.assertEqual(report["record_draft_count"], 1)
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["record_drafts"][0]["candidate_table_gate"]["result"], "pass")

    def test_cli_audits_first_batch_sample_table_trial_without_writing(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-sample-table-trial",
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
        self.assertEqual(report["trial_row_count"], 1)
        self.assertEqual(report["candidate_table_write_mode"], "manual_review_only")
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["trial_rows"][0]["candidate_table_gate_result"], "pass")

    def test_cli_audits_first_batch_method_pm_readiness_without_generating_actions(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-method-pm-readiness",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["method_pm_review_required_count"], 1)
        self.assertFalse(report["method_pm_auto_generation_allowed"])
        self.assertFalse(report["malf_action_backflow_allowed"])
        self.assertEqual(report["method_pm_review_items"][0]["next_action"], "action:method_pm_review")

    def test_cli_audits_first_batch_backtest_input_readiness_without_bypassing_method_pm(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-backtest-input-readiness",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["backtest_input_ready_count"], 0)
        self.assertEqual(report["backtest_input_blocked_count"], 1)
        self.assertFalse(report["backtest_input_snapshot_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertEqual(report["backtest_input_blocked_items"][0]["blocker"], "method_pm_not_ready")

    def test_cli_audits_first_batch_cognitive_pipeline_without_starting_institution_adaptation(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "ashare_intake_validator",
                "--root",
                str(fixture_root),
                "--audit-first-batch-cognitive-pipeline",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )

        self.assertEqual(completed.returncode, 1, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["current_blocking_layer"], "method_pm_readiness")
        self.assertEqual(report["next_action"], "action:method_pm_review")
        self.assertFalse(report["institution_adaptation_allowed"])
        self.assertFalse(report["structure_to_institution_transition_allowed"])

    def test_cli_audits_method_pm_plan_draft_contract_from_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            draft_path = Path(tmp) / "method-pm-plan.json"
            draft_path.write_text(
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
                    str(ROOT / "tests" / "fixtures" / "ashare-intake-ready"),
                    "--audit-method-pm-plan-draft",
                    str(draft_path),
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
        self.assertEqual(report["next_action"], "action:build_backtest_input_snapshot")
        self.assertFalse(report["malf_action_backflow_allowed"])

    def test_cli_merges_first_batch_method_pm_plan_directory(self) -> None:
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
                    "--audit-first-batch-method-pm-plan-merge",
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
        self.assertEqual(report["method_pm_plan_ready_count"], 1)
        self.assertTrue(report["backtest_input_snapshot_allowed"])
        self.assertFalse(report["institution_adaptation_allowed"])

    def test_cli_builds_first_batch_backtest_input_snapshot_drafts(self) -> None:
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
                    "--audit-first-batch-backtest-input-snapshots",
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
        self.assertEqual(report["backtest_input_snapshot_count"], 1)
        self.assertEqual(report["backtest_input_snapshots"][0]["backtest_input_gate_result"], "pass")
        self.assertFalse(report["institution_adaptation_allowed"])

    def test_cli_audits_first_batch_institution_constraint_gate_without_defining_rules(self) -> None:
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
                    "--audit-first-batch-institution-constraint-gate",
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
        self.assertTrue(report["institution_constraint_audit_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertEqual(report["institution_gate_items"][0]["gate_status"], "pass")
