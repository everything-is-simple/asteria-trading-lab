import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ashare_intake_validator import (
    _audit_stage_reason_consistency,
    audit_ashare_institution_fact_package,
    audit_first_batch_execution_feasibility_gate,
    audit_first_batch_execution_feasibility_verdicts,
    audit_first_batch_execution_constraint_snapshots,
    audit_first_batch_backtest_input_readiness,
    audit_first_batch_backtest_input_snapshot_drafts,
    audit_first_batch_cognitive_pipeline,
    audit_first_batch_institution_constraint_gate,
    audit_first_batch_institution_feasibility_records,
    audit_first_batch_method_pm_plan_merge,
    audit_first_batch_method_pm_readiness,
    audit_first_batch_record_drafts,
    audit_first_batch_sample_table_trial,
    audit_first_batch_front_filter_run,
    audit_first_batch_readiness,
    audit_method_pm_plan_draft_contract,
    validate_intake_package,
)


CANDIDATE_HEADER = [
    "ts_code",
    "symbol_name",
    "board_type",
    "list_date",
    "is_st",
    "is_new_stock_window",
    "data_quality_status",
    "source_ref",
]

SW_HEADER = [
    "ts_code",
    "sw_l1_name",
    "sw_l2_name",
    "valid_from",
    "valid_to",
    "source_ref",
]

DAILY_HEADER = [
    "ts_code",
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "amount",
    "adj_ref",
    "suspension_flag",
    "corporate_action_flag",
    "missing_bar_flag",
]

INSTITUTION_FACT_HEADER = [
    "ts_code",
    "trade_date",
    "is_trading_day",
    "is_suspended",
    "limit_up_price",
    "limit_down_price",
    "close_limit_status",
    "touched_limit_status",
    "board_lot_size",
    "source_ref",
]


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header), *[",".join(row) for row in rows]]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class AShareIntakeValidatorTest(unittest.TestCase):
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

    def test_institution_fact_package_accepts_fact_fields_without_rules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            facts_dir = root / "ashare" / "institution-facts-v0.1"
            write_csv(
                facts_dir / "000001.SZ.csv",
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

            report = audit_ashare_institution_fact_package(root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["institution_fact_status"], "ready")
        self.assertEqual(report["institution_fact_count"], 1)
        self.assertEqual(report["institution_fact_files"], ["ashare/institution-facts-v0.1/000001.SZ.csv"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertEqual(report["next_action"], "action:build_execution_constraint_snapshots")
        self.assertEqual(report["failed_contract_items"], [])

    def test_institution_fact_package_blocks_rule_and_signal_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            facts_dir = root / "ashare" / "institution-facts-v0.1"
            write_csv(
                facts_dir / "000001.SZ.csv",
                [*INSTITUTION_FACT_HEADER, "limit_up_strategy", "trade_accept", "target_position"],
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
                    "unit-test",
                    "chase_board",
                    "true",
                    "0.5",
                ]],
            )

            report = audit_ashare_institution_fact_package(root)

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["institution_fact_status"], "invalid")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertIn("forbidden_field:000001.SZ.csv:limit_up_strategy", report["failed_contract_items"])
        self.assertIn("forbidden_field:000001.SZ.csv:trade_accept", report["failed_contract_items"])
        self.assertIn("forbidden_field:000001.SZ.csv:target_position", report["failed_contract_items"])
        self.assertEqual(report["next_action"], "action:repair_institution_fact_package")

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

    def test_ready_fixture_stops_at_structure_candidate_and_requires_front_filter(self) -> None:
        fixture_root = ROOT / "tests" / "fixtures" / "ashare-intake-ready"

        report = validate_intake_package(fixture_root)

        self.assertEqual(report["intake_package_status"], "ready")
        self.assertEqual(report["contract_check_result"], "pass")
        self.assertEqual(report["failed_contract_items"], [])
        self.assertFalse(report["eligible_for_tachibana_candidate"])
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")
        summary = report["candidate_stage_summary"]["000001.SZ"]
        self.assertTrue(summary["eligible_for_malf_run"])
        self.assertEqual(summary["candidate_stage_after"], "structure_candidate")
        self.assertEqual(summary["tachibana_applicability"], "unknown")
        self.assertEqual(summary["next_action"], "action:run_front_filter")
        self.assertIn("no_qualification_rule", summary["applicability_reason"])
        self.assertIn("do_not_upgrade_ready_snapshot_without_front_filter", summary["boundary_warning"])
        self.assertNotEqual(summary["candidate_stage_after"], "tachibana_candidate")

    def test_empty_data_root_reports_missing_package_and_blocks_all_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report = validate_intake_package(Path(tmp))

        self.assertEqual(report["intake_package_status"], "missing")
        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertFalse(report["eligible_for_structure_candidate"])
        self.assertFalse(report["eligible_for_tachibana_candidate"])
        self.assertIn("missing_file:ashare/candidate-universe-v0.1.csv", report["failed_contract_items"])
        self.assertIn("missing_file:ashare/sw-industry-membership-v0.1.csv", report["failed_contract_items"])
        self.assertIn("missing_dir:ashare/daily-window-v0.1", report["failed_contract_items"])
        self.assertIn("missing_dir:ashare/malf-snapshots-v0.1", report["failed_contract_items"])
        self.assertIn("missing_candidate_universe", report["failed_contract_reason_codes"])
        self.assertIn("missing_sw_industry_membership", report["failed_contract_reason_codes"])
        self.assertIn("missing_daily_window", report["failed_contract_reason_codes"])
        self.assertIn("missing_malf_snapshot", report["failed_contract_reason_codes"])
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")
        self.assertEqual(report["stage_reason_consistency"]["issues"], [])

    def test_forbidden_trading_fields_fail_the_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                [*CANDIDATE_HEADER, "buy_signal"],
                [["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test", "true"]],
            )
            write_csv(
                ashare / "sw-industry-membership-v0.1.csv",
                SW_HEADER,
                [["000001.SZ", "Bank", "Joint-stock Bank", "2025-01-01", "", "unit-test"]],
            )
            (ashare / "daily-window-v0.1").mkdir()
            (ashare / "malf-snapshots-v0.1").mkdir()

            report = validate_intake_package(root)

        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertIn("forbidden_field:buy_signal", report["failed_contract_items"])
        self.assertIn("forbidden_field_present", report["failed_contract_reason_codes"])

    def test_minimal_valid_package_passes_read_only_gates(self) -> None:
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
            snapshot = {
                "malf_snapshot_ref": "MALF-SNAP-000001-202601",
                "ts_code": "000001.SZ",
                "window_start": "2026-01-05",
                "window_end": "2026-01-06",
                "source_daily_file": "daily-window-v0.1/000001.SZ.csv",
                "generated_at": "2026-06-26T00:00:00+08:00",
                "malf_version": "MALF_Definitive_v2_0",
                "malf_background": "alive_wave",
                "wave_range_break_fields": {"range_state": "up_range"},
                "evidence_ref": "unit-test",
                "snapshot_quality_status": "ready",
            }
            snapshot_dir = ashare / "malf-snapshots-v0.1"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "000001.SZ-2026-01.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            report = validate_intake_package(root)

        self.assertEqual(report["intake_package_status"], "ready")
        self.assertEqual(report["contract_check_result"], "pass")
        self.assertTrue(report["eligible_for_malf_run"])
        self.assertTrue(report["eligible_for_structure_candidate"])
        self.assertFalse(report["eligible_for_tachibana_candidate"])
        self.assertEqual(report["failed_contract_items"], [])
        self.assertEqual(
            report["candidate_stage_summary"]["000001.SZ"]["candidate_stage_after"],
            "structure_candidate",
        )
        self.assertEqual(
            report["candidate_stage_summary"]["000001.SZ"]["tachibana_applicability"],
            "unknown",
        )
        self.assertEqual(
            report["candidate_stage_summary"]["000001.SZ"]["next_action"],
            "action:run_front_filter",
        )
        self.assertIn(
            "do_not_upgrade_ready_snapshot_without_front_filter",
            report["candidate_stage_summary"]["000001.SZ"]["boundary_warning"],
        )
        self.assertIn(
            "do_not_upgrade_ready_snapshot_without_front_filter",
            report["candidate_stage_summary"]["000001.SZ"]["blocking_reasons"],
        )
        self.assertIn(
            "no_qualification_rule",
            report["candidate_stage_summary"]["000001.SZ"]["applicability_reason"],
        )
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")

    def test_cross_file_orphans_and_snapshot_window_mismatches_fail_the_contract(self) -> None:
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
                [["000002.SZ", "Bank", "Joint-stock Bank", "2025-01-01", "", "unit-test"]],
            )
            write_csv(
                ashare / "daily-window-v0.1" / "000003.SZ.csv",
                DAILY_HEADER,
                [
                    ["000003.SZ", "2026-01-05", "10.00", "10.50", "9.80", "10.20", "100000", "1020000", "qfq", "false", "false", "false"],
                    ["000003.SZ", "2026-01-06", "10.20", "10.80", "10.10", "10.70", "110000", "1177000", "qfq", "false", "false", "false"],
                ],
            )
            snapshot = {
                "malf_snapshot_ref": "MALF-SNAP-000001-202601",
                "ts_code": "000001.SZ",
                "window_start": "2026-01-01",
                "window_end": "2026-01-10",
                "source_daily_file": "daily-window-v0.1/000001.SZ.csv",
                "generated_at": "2026-06-26T00:00:00+08:00",
                "malf_version": "MALF_Definitive_v2_0",
                "malf_background": "alive_wave",
                "wave_range_break_fields": {"range_state": "up_range"},
                "evidence_ref": "unit-test",
                "snapshot_quality_status": "ready",
            }
            snapshot_dir = ashare / "malf-snapshots-v0.1"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "000001.SZ-2026-01.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            report = validate_intake_package(root)

        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertIn("orphan_sw_ts_code:000002.SZ", report["failed_contract_items"])
        self.assertIn("orphan_daily_ts_code:000003.SZ", report["failed_contract_items"])
        self.assertIn("snapshot_source_daily_missing:000001.SZ-2026-01.json:daily-window-v0.1/000001.SZ.csv", report["failed_contract_items"])
        self.assertIn("snapshot_window_outside_daily_range:000001.SZ-2026-01.json", report["failed_contract_items"])
        self.assertIn("missing_industry_label", report["failed_contract_reason_codes"])
        self.assertIn("missing_daily_window", report["failed_contract_reason_codes"])
        self.assertIn("missing_malf_snapshot", report["failed_contract_reason_codes"])
        self.assertIn("malf_snapshot_window_mismatch", report["failed_contract_reason_codes"])

    def test_key_value_domain_and_numeric_contract_violations_fail_the_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                CANDIDATE_HEADER,
                [
                    ["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test"],
                    ["000001.SZ", "Duplicate", "invalid_board", "19910403", "maybe", "false", "bad_status", "unit-test"],
                ],
            )
            write_csv(
                ashare / "sw-industry-membership-v0.1.csv",
                SW_HEADER,
                [
                    ["000001.SZ", "Bank", "Joint-stock Bank", "2025-01-02", "2025-01-01", "unit-test"],
                    ["000001.SZ", "Bank", "Joint-stock Bank", "bad-date", "", "unit-test"],
                ],
            )
            write_csv(
                ashare / "daily-window-v0.1" / "000001.SZ.csv",
                DAILY_HEADER,
                [
                    ["000001.SZ", "2026-01-05", "-10.00", "10.50", "9.80", "10.20", "-100000", "1020000", "qfq", "maybe", "false", "false"],
                    ["000001.SZ", "bad-date", "10.20", "10.80", "10.10", "10.70", "110000", "-1177000", "qfq", "false", "false", "false"],
                ],
            )
            snapshot = {
                "malf_snapshot_ref": "MALF-SNAP-000001-202601",
                "ts_code": "000001.SZ",
                "window_start": "2026/01/05",
                "window_end": "2026-01-06",
                "source_daily_file": "daily-window-v0.1/000001.SZ.csv",
                "generated_at": "2026-06-26T00:00:00+08:00",
                "malf_version": "MALF_Definitive_v2_0",
                "malf_background": "alive_wave",
                "wave_range_break_fields": {"range_state": "up_range"},
                "evidence_ref": "unit-test",
                "snapshot_quality_status": "bad_status",
            }
            snapshot_dir = ashare / "malf-snapshots-v0.1"
            snapshot_dir.mkdir(parents=True)
            (snapshot_dir / "000001.SZ-2026-01.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            report = validate_intake_package(root)

        self.assertEqual(report["contract_check_result"], "fail")
        self.assertFalse(report["eligible_for_malf_run"])
        self.assertIn("duplicate_key:candidate-universe-v0.1.csv:ts_code:000001.SZ", report["failed_contract_items"])
        self.assertIn("invalid_enum:candidate-universe-v0.1.csv:board_type:invalid_board", report["failed_contract_items"])
        self.assertIn("invalid_date:candidate-universe-v0.1.csv:list_date:19910403", report["failed_contract_items"])
        self.assertIn("invalid_boolean:candidate-universe-v0.1.csv:is_st:maybe", report["failed_contract_items"])
        self.assertIn("invalid_enum:candidate-universe-v0.1.csv:data_quality_status:bad_status", report["failed_contract_items"])
        self.assertIn("invalid_date_order:sw-industry-membership-v0.1.csv:2025-01-02>2025-01-01", report["failed_contract_items"])
        self.assertIn("invalid_date:sw-industry-membership-v0.1.csv:valid_from:bad-date", report["failed_contract_items"])
        self.assertIn("negative_number:000001.SZ.csv:open:line_2", report["failed_contract_items"])
        self.assertIn("negative_number:000001.SZ.csv:volume:line_2", report["failed_contract_items"])
        self.assertIn("invalid_boolean:000001.SZ.csv:suspension_flag:line_2", report["failed_contract_items"])
        self.assertIn("invalid_date:000001.SZ.csv:trade_date:bad-date", report["failed_contract_items"])
        self.assertIn("negative_number:000001.SZ.csv:amount:line_3", report["failed_contract_items"])
        self.assertIn("invalid_date:000001.SZ-2026-01.json:window_start:2026/01/05", report["failed_contract_items"])
        self.assertIn("invalid_enum:000001.SZ-2026-01.json:snapshot_quality_status:bad_status", report["failed_contract_items"])
        self.assertIn("duplicate_key_present", report["failed_contract_reason_codes"])
        self.assertIn("invalid_enum_value", report["failed_contract_reason_codes"])
        self.assertIn("invalid_date_value", report["failed_contract_reason_codes"])
        self.assertIn("invalid_boolean_value", report["failed_contract_reason_codes"])
        self.assertIn("invalid_daily_ohlc", report["failed_contract_reason_codes"])
        self.assertIn("invalid_numeric_value", report["failed_contract_reason_codes"])
        self.assertIn("malf_snapshot_not_ready", report["failed_contract_reason_codes"])

    def test_stage_summary_keeps_metadata_only_candidates_below_structure_stage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ashare = root / "ashare"
            write_csv(
                ashare / "candidate-universe-v0.1.csv",
                CANDIDATE_HEADER,
                [["000001.SZ", "Ping An Bank", "main", "1991-04-03", "false", "false", "ready", "unit-test"]],
            )
            write_csv(ashare / "sw-industry-membership-v0.1.csv", SW_HEADER, [])
            (ashare / "daily-window-v0.1").mkdir()
            (ashare / "malf-snapshots-v0.1").mkdir()

            report = validate_intake_package(root)

        summary = report["candidate_stage_summary"]["000001.SZ"]
        self.assertEqual(summary["candidate_stage_after"], "universe_candidate")
        self.assertFalse(summary["eligible_for_malf_run"])
        self.assertEqual(summary["tachibana_applicability"], "unknown")
        self.assertEqual(summary["next_action"], "action:complete_industry_and_daily_window")
        self.assertIn("missing_industry_label", summary["failed_contract_reason_codes"])
        self.assertIn("missing_daily_window", summary["blocking_reasons"])
        self.assertIn("missing_malf_snapshot", summary["failed_contract_reason_codes"])
        self.assertIn("blocked_by_missing_industry_label", summary["rule_match_reason"])
        self.assertIn("blocked_by_missing_daily_window", summary["rule_match_reason"])
        self.assertIn("blocked_by_missing_malf_snapshot", summary["rule_match_reason"])
        self.assertIn("no_industry_label", summary["applicability_reason"])
        self.assertIn("no_daily_window", summary["applicability_reason"])
        self.assertIn("no_ready_malf_snapshot", summary["applicability_reason"])
        self.assertIn("do_not_upgrade_without_malf_snapshot", summary["boundary_warning"])
        self.assertEqual(report["stage_reason_consistency"]["result"], "pass")

    def test_stage_reason_consistency_detects_internal_contradictions(self) -> None:
        audit = _audit_stage_reason_consistency(
            {
                "000001.SZ": {
                    "candidate_stage_after": "tachibana_candidate",
                    "eligible_for_malf_run": False,
                    "tachibana_applicability": "suitable",
                    "failed_contract_reason_codes": ["missing_daily_window", "missing_malf_snapshot"],
                    "rule_match_reason": [],
                    "applicability_reason": [],
                    "boundary_warning": [],
                    "next_action": "run_front_filter",
                }
            },
            ["missing_daily_window", "missing_malf_snapshot"],
        )

        self.assertEqual(audit["result"], "fail")
        self.assertIn("stage_without_malf_run:000001.SZ:tachibana_candidate", audit["issues"])
        self.assertIn("tachibana_applicability_decided_before_front_filter:000001.SZ:suitable", audit["issues"])
        self.assertIn("next_action_missing_action_prefix:000001.SZ:run_front_filter", audit["issues"])
        self.assertIn("missing_malf_snapshot_without_boundary_warning:000001.SZ", audit["issues"])


if __name__ == "__main__":
    unittest.main()
