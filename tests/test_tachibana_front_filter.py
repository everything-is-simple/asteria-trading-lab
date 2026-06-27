import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from tachibana_front_filter import (
    audit_backtest_input_gate,
    audit_candidate_table_update_gate,
    audit_cognitive_pipeline_gate,
    audit_front_filter_system,
    audit_interface_boundary_gate,
    audit_interface_boundary_catalog,
    audit_method_pm_bridge_gate,
    audit_method_pm_action_catalog,
    audit_qualification_rule_catalog,
    audit_qualification_record_consistency,
    audit_rhythm_sample_catalog,
    audit_rhythm_sample_row_gate,
    build_qualification_record_draft,
    get_interface_boundary_catalog,
    get_method_action_catalog,
    get_pm_action_catalog,
    get_qualification_rule_catalog,
    get_rhythm_sample_catalog,
    run_front_filter,
)


FORBIDDEN_OUTPUT_FIELDS = {
    "buy_signal",
    "sell_signal",
    "trade_accept",
    "target_position",
    "ashare_t1_action",
    "position_size",
    "center_position",
}


def write_snapshot(root: Path, payload: dict) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / "snapshot.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class TachibanaFrontFilterTest(unittest.TestCase):
    def test_qualification_rule_catalog_defines_filter_output_codes(self) -> None:
        catalog = get_qualification_rule_catalog()

        self.assertIn("Q-ALIVE-CLEAN", catalog)
        self.assertEqual(catalog["Q-ALIVE-CLEAN"]["rhythm_meaning"], "meaningful")
        self.assertEqual(catalog["Q-ALIVE-CLEAN"]["tachibana_applicability"], "suitable")
        self.assertEqual(catalog["Q-ALIVE-CLEAN"]["pm_complexity"], "none")
        self.assertEqual(catalog["Q-ALIVE-CLEAN"]["candidate_stage_after"], "tachibana_candidate")

        self.assertEqual(catalog["Q-SEED-AFTER-CLEAR"]["rhythm_meaning"], "limited")
        self.assertEqual(catalog["Q-PRESSURE-ADJUST"]["tachibana_applicability"], "conditional")
        self.assertEqual(catalog["Q-LOCK-WAIT"]["pm_required"], True)
        self.assertEqual(catalog["Q-CLEAR-RESET"]["pm_complexity"], "high")
        self.assertEqual(catalog["Q-SOURCE-DISRUPTED"]["rhythm_meaning"], "unknown")
        self.assertEqual(catalog["NM-NO-STRUCTURE"]["tachibana_applicability"], "unsuitable")

        with tempfile.TemporaryDirectory() as tmp:
            snapshot_paths = [
                write_snapshot(
                    Path(tmp) / "alive",
                    {
                        "malf_snapshot_ref": "SNAP-ALIVE",
                        "ts_code": "000001.SZ",
                        "window_start": "2026-01-05",
                        "window_end": "2026-01-06",
                        "malf_background": "alive_wave",
                        "snapshot_quality_status": "ready",
                        "wave_range_break_fields": {"wave_core_state": "alive"},
                    },
                ),
                write_snapshot(
                    Path(tmp) / "birth",
                    {
                        "malf_snapshot_ref": "SNAP-BIRTH",
                        "ts_code": "000001.SZ",
                        "window_start": "2026-01-05",
                        "window_end": "2026-01-06",
                        "malf_background": "break_birth",
                        "snapshot_quality_status": "ready",
                        "wave_range_break_fields": {"birth_type": "seed_after_clear"},
                    },
                ),
                write_snapshot(
                    Path(tmp) / "pullback",
                    {
                        "malf_snapshot_ref": "SNAP-PULLBACK",
                        "ts_code": "000001.SZ",
                        "window_start": "2026-01-05",
                        "window_end": "2026-01-06",
                        "malf_background": "pullback",
                        "snapshot_quality_status": "ready",
                        "wave_range_break_fields": {"pressure_adjustment": True},
                    },
                ),
                write_snapshot(
                    Path(tmp) / "range",
                    {
                        "malf_snapshot_ref": "SNAP-RANGE",
                        "ts_code": "000001.SZ",
                        "window_start": "2026-01-05",
                        "window_end": "2026-01-06",
                        "malf_background": "range",
                        "snapshot_quality_status": "ready",
                        "wave_range_break_fields": {"no_trade_wait": True},
                    },
                ),
                write_snapshot(
                    Path(tmp) / "stagnation",
                    {
                        "malf_snapshot_ref": "SNAP-STAGNATION",
                        "ts_code": "000001.SZ",
                        "window_start": "2026-01-05",
                        "window_end": "2026-01-06",
                        "malf_background": "stagnation",
                        "snapshot_quality_status": "ready",
                        "wave_range_break_fields": {"clear_reset": True},
                    },
                ),
                write_snapshot(
                    Path(tmp) / "disrupted",
                    {
                        "malf_snapshot_ref": "SNAP-DISRUPTED",
                        "ts_code": "000001.SZ",
                        "window_start": "2026-01-05",
                        "window_end": "2026-01-06",
                        "malf_background": "transition",
                        "snapshot_quality_status": "ready",
                        "wave_range_break_fields": {"source_disrupted": True},
                    },
                ),
                write_snapshot(
                    Path(tmp) / "no-structure",
                    {
                        "malf_snapshot_ref": "SNAP-NO-STRUCTURE",
                        "ts_code": "000001.SZ",
                        "window_start": "2026-01-05",
                        "window_end": "2026-01-06",
                        "malf_background": "no_structure",
                        "snapshot_quality_status": "ready",
                        "wave_range_break_fields": {"negative_type": "NM-NO-STRUCTURE"},
                    },
                ),
            ]

            for snapshot_path in snapshot_paths:
                report = run_front_filter(snapshot_path)
                rule_id = report["qualification_rule_id"]
                self.assertIn(rule_id, catalog)
                self.assertEqual(report["rhythm_meaning"], catalog[rule_id]["rhythm_meaning"])
                self.assertEqual(
                    report["tachibana_applicability"],
                    catalog[rule_id]["tachibana_applicability"],
                )
                self.assertEqual(report["pm_required"], catalog[rule_id]["pm_required"])
                self.assertEqual(
                    report["candidate_stage_after"],
                    catalog[rule_id]["candidate_stage_after"],
                )

    def test_qualification_rule_catalog_audit_passes_when_required_rules_are_defined(self) -> None:
        audit = audit_qualification_rule_catalog()

        self.assertEqual(audit["result"], "pass")
        self.assertEqual(audit["defined_rule_count"], 16)
        self.assertEqual(audit["valid_rule_count"], 16)
        self.assertEqual(audit["pending_limited_rules"], [])
        self.assertEqual(audit["pending_not_meaningful_rules"], [])
        self.assertEqual(audit["invalid_rules"], {})

    def test_qualification_rule_catalog_audit_blocks_invalid_rule_shape(self) -> None:
        catalog = get_qualification_rule_catalog()
        catalog["Q-BAD"] = {
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "conditional",
            "pm_complexity": "very_high",
            "pm_required": "yes",
            "candidate_stage_after": "tachibana_candidate",
            "rule_family": "positive",
            "boundary_warning": [],
        }

        audit = audit_qualification_rule_catalog(catalog)

        self.assertEqual(audit["result"], "blocked")
        self.assertIn("Q-BAD", audit["invalid_rules"])
        self.assertIn("rule_catalog_applicability_mismatch", audit["invalid_rules"]["Q-BAD"])
        self.assertIn("invalid_rule_pm_complexity:very_high", audit["invalid_rules"]["Q-BAD"])
        self.assertIn("invalid_rule_pm_required:yes", audit["invalid_rules"]["Q-BAD"])
        self.assertIn("rule_requires_boundary_warning", audit["invalid_rules"]["Q-BAD"])

    def test_cli_audits_qualification_rule_catalog_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-rule-catalog",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["pending_limited_rules"], [])
        self.assertEqual(report["pending_not_meaningful_rules"], [])
        self.assertEqual(report["invalid_rules"], {})

    def test_rhythm_sample_catalog_is_audited_by_row_gate(self) -> None:
        samples = get_rhythm_sample_catalog()

        self.assertIn("1975-01", samples)
        self.assertIn("1976-11-A", samples)
        self.assertIn("1976-09", samples)
        self.assertIn("NM-NO-STRUCTURE-FIXTURE", samples)
        self.assertEqual(samples["1975-01"]["rhythm_meaning"], "meaningful")
        self.assertEqual(samples["1976-11-A"]["qualification_rule_id"], "Q-EXTREME-ADDON")
        self.assertEqual(samples["1976-09"]["rhythm_meaning"], "unknown")
        self.assertEqual(samples["NM-NO-STRUCTURE-FIXTURE"]["rhythm_meaning"], "not_meaningful")

        audit = audit_rhythm_sample_catalog(samples)

        self.assertEqual(audit["result"], "pass")
        self.assertEqual(audit["sample_count"], 16)
        self.assertEqual(audit["passed_sample_count"], 16)
        self.assertEqual(audit["blocked_sample_count"], 0)
        self.assertEqual(audit["missing_rule_ids"], [])
        self.assertEqual(len(audit["covered_rule_ids"]), 16)
        self.assertEqual(audit["blocked_samples"], {})

    def test_rhythm_sample_catalog_audit_reports_blocked_rows(self) -> None:
        samples = get_rhythm_sample_catalog()
        samples["BAD-MEANINGFUL"] = {
            **samples["1975-01"],
            "sample_id": "BAD-MEANINGFUL",
            "qualification_rule_id": "Q-EXTREME-ADDON",
            "pm_complexity": "high",
        }

        audit = audit_rhythm_sample_catalog(samples)

        self.assertEqual(audit["result"], "blocked")
        self.assertEqual(audit["sample_count"], 17)
        self.assertEqual(audit["blocked_sample_count"], 1)
        self.assertIn("BAD-MEANINGFUL", audit["blocked_samples"])
        self.assertIn(
            "rule_catalog_rhythm_mismatch:Q-EXTREME-ADDON",
            audit["blocked_samples"]["BAD-MEANINGFUL"]["issues"],
        )

    def test_cli_audits_rhythm_sample_catalog_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-rhythm-samples",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["sample_count"], 16)
        self.assertEqual(report["blocked_sample_count"], 0)
        self.assertEqual(report["missing_rule_ids"], [])

    def test_method_pm_action_catalog_audit_covers_actions_and_blocks_malf_generation(self) -> None:
        method_catalog = get_method_action_catalog()
        pm_catalog = get_pm_action_catalog()

        self.assertIn("trend_probe_entry", method_catalog)
        self.assertIn("wait_no_action", method_catalog)
        self.assertIn("open_center", pm_catalog)
        self.assertIn("lock_candidate", pm_catalog)
        self.assertFalse(method_catalog["trend_probe_entry"]["malf_can_generate"])
        self.assertFalse(pm_catalog["open_center"]["malf_can_generate"])
        self.assertEqual(pm_catalog["lock_candidate"]["layer"], "pm")

        audit = audit_method_pm_action_catalog()

        self.assertEqual(audit["result"], "pass")
        self.assertEqual(audit["method_action_count"], 9)
        self.assertEqual(audit["pm_action_count"], 10)
        self.assertEqual(audit["missing_method_actions"], [])
        self.assertEqual(audit["missing_pm_actions"], [])
        self.assertEqual(audit["invalid_actions"], {})

    def test_method_pm_action_catalog_audit_blocks_malf_generated_actions(self) -> None:
        method_catalog = get_method_action_catalog()
        pm_catalog = get_pm_action_catalog()
        pm_catalog["open_center"] = {**pm_catalog["open_center"], "malf_can_generate": True}

        audit = audit_method_pm_action_catalog(method_catalog, pm_catalog)

        self.assertEqual(audit["result"], "blocked")
        self.assertIn("open_center", audit["invalid_actions"])
        self.assertIn("pm_action_must_not_be_generated_by_malf", audit["invalid_actions"]["open_center"])

    def test_cli_audits_method_pm_actions_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-method-pm-actions",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["missing_method_actions"], [])
        self.assertEqual(report["missing_pm_actions"], [])

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

    def test_candidate_table_gate_blocks_failed_record_consistency(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-BAD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {
                "result": "fail",
                "issues": ["forbidden_record_field:target_position"],
            },
        }

        gate = audit_candidate_table_update_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("record_consistency_failed", gate["issues"])
        self.assertIn("record_consistency_issue:forbidden_record_field:target_position", gate["issues"])

    def test_candidate_table_gate_blocks_missing_evidence_boundary_and_rule(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-MISSING-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": None,
            "next_action": "action:fill_candidate_table",
            "boundary_warning": [],
            "evidence_level": [],
            "record_consistency": {"result": "pass", "issues": []},
        }

        gate = audit_candidate_table_update_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("candidate_table_requires_qualification_rule_id", gate["issues"])
        self.assertIn("candidate_table_requires_boundary_warning", gate["issues"])
        self.assertIn("candidate_table_requires_e1_malf_snapshot", gate["issues"])

    def test_candidate_table_gate_blocks_forbidden_trade_fields(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-TRADE-FIELD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "trade_accept": True,
        }

        gate = audit_candidate_table_update_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("candidate_table_forbidden_field:trade_accept", gate["issues"])

    def test_method_pm_bridge_gate_allows_clean_wait_plan_without_pm_action(self) -> None:
        record = {
            "method_action": "wait_no_action",
            "method_status": "hypothesis",
            "method_reason": ["active_waiting"],
            "pm_required": False,
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "hold",
        }

        gate = audit_method_pm_bridge_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["bridge_status"], "method_pm_ready")
        self.assertEqual(gate["next_action"], "action:build_backtest_input_snapshot")
        self.assertEqual(gate["issues"], [])
        self.assertIn("method_action", gate["required_fields_checked"])
        self.assertIn("pm_required", gate["required_fields_checked"])

    def test_method_pm_bridge_gate_blocks_unknown_method_action_and_missing_pm_action(self) -> None:
        record = {
            "method_action": "buy_breakout",
            "method_status": "hypothesis",
            "method_reason": ["staged_execution"],
            "pm_required": True,
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "open",
        }

        gate = audit_method_pm_bridge_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertEqual(gate["bridge_status"], "method_pm_review_required")
        self.assertEqual(gate["next_action"], "action:method_pm_review")
        self.assertIn("method_pm_invalid_method_action:buy_breakout", gate["issues"])
        self.assertIn("method_pm_requires_pm_action_when_pm_required", gate["issues"])

    def test_method_pm_bridge_gate_blocks_malf_derived_pm_fields(self) -> None:
        record = {
            "method_action": "inventory_rebalance",
            "method_status": "hypothesis",
            "method_reason": ["inventory_awareness"],
            "pm_required": True,
            "pm_action": "rebalance",
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "rebalance",
            "center_position_from_malf": 10,
        }

        gate = audit_method_pm_bridge_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("method_pm_forbidden_field:center_position_from_malf", gate["issues"])

    def test_interface_boundary_catalog_audit_covers_layers(self) -> None:
        catalog = get_interface_boundary_catalog()

        self.assertIn("data", catalog)
        self.assertIn("signal", catalog)
        self.assertIn("backtest", catalog)
        self.assertIn("tachibana_adapter", catalog)
        self.assertFalse(catalog["data"]["may_write_structure_qualification"])
        self.assertFalse(catalog["signal"]["may_read_structure_qualification"])
        self.assertFalse(catalog["backtest"]["may_write_structure_qualification"])
        self.assertTrue(catalog["tachibana_adapter"]["may_read_structure_qualification"])

        audit = audit_interface_boundary_catalog()

        self.assertEqual(audit["result"], "pass")
        self.assertEqual(audit["layer_count"], 4)
        self.assertEqual(audit["invalid_layers"], {})
        self.assertEqual(audit["missing_layers"], [])

    def test_interface_boundary_catalog_audit_blocks_signal_reading_structure(self) -> None:
        catalog = get_interface_boundary_catalog()
        catalog["signal"] = {
            **catalog["signal"],
            "may_read_structure_qualification": True,
        }

        audit = audit_interface_boundary_catalog(catalog)

        self.assertEqual(audit["result"], "blocked")
        self.assertIn("signal", audit["invalid_layers"])
        self.assertIn("signal_must_not_read_structure_qualification", audit["invalid_layers"]["signal"])

    def test_cli_audits_interface_boundary_catalog_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-interface-boundary",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["missing_layers"], [])
        self.assertEqual(report["invalid_layers"], {})

    def test_front_filter_system_audit_aggregates_all_catalogs(self) -> None:
        audit = audit_front_filter_system()

        self.assertEqual(audit["result"], "pass")
        self.assertEqual(audit["blocked_audits"], [])
        self.assertEqual(audit["audits"]["qualification_rule_catalog"]["result"], "pass")
        self.assertEqual(audit["audits"]["rhythm_sample_catalog"]["result"], "pass")
        self.assertEqual(audit["audits"]["method_pm_action_catalog"]["result"], "pass")
        self.assertEqual(audit["audits"]["interface_boundary_catalog"]["result"], "pass")

    def test_front_filter_system_audit_reports_blocked_sub_audit(self) -> None:
        samples = get_rhythm_sample_catalog()
        samples["BROKEN"] = {
            **samples["1975-01"],
            "sample_id": "BROKEN",
            "qualification_rule_id": "Q-EXTREME-ADDON",
            "pm_complexity": "high",
        }

        audit = audit_front_filter_system(rhythm_sample_catalog=samples)

        self.assertEqual(audit["result"], "blocked")
        self.assertEqual(audit["blocked_audits"], ["rhythm_sample_catalog"])
        self.assertEqual(audit["audits"]["rhythm_sample_catalog"]["result"], "blocked")

    def test_cli_audits_front_filter_system_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-front-filter-system",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["blocked_audits"], [])

    def test_interface_boundary_gate_blocks_data_layer_structure_and_trade_fields(self) -> None:
        record = {
            "interface_layer": "data",
            "ts_code": "000001.SZ",
            "tachibana_applicability": "suitable",
            "target_position": 0.5,
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertEqual(gate["next_action"], "action:clean_interface_boundary")
        self.assertIn("data_layer_must_not_write:tachibana_applicability", gate["issues"])
        self.assertIn("data_layer_must_not_write:target_position", gate["issues"])

    def test_interface_boundary_gate_blocks_signal_layer_consuming_rhythm_or_applicability(self) -> None:
        record = {
            "interface_layer": "signal",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "signal_decision": "accept",
            "signal_decision_from_rhythm": "accept",
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("signal_layer_must_not_read:rhythm_meaning", gate["issues"])
        self.assertIn("signal_layer_must_not_read:tachibana_applicability", gate["issues"])
        self.assertIn("signal_layer_forbidden_field:signal_decision_from_rhythm", gate["issues"])

    def test_interface_boundary_gate_blocks_backtest_layer_rewriting_structure(self) -> None:
        record = {
            "interface_layer": "backtest",
            "execution_failed": True,
            "rhythm_meaning": "not_meaningful",
            "tachibana_applicability": "unsuitable",
            "structure_suitable": False,
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("backtest_layer_must_not_write:rhythm_meaning", gate["issues"])
        self.assertIn("backtest_layer_must_not_write:tachibana_applicability", gate["issues"])
        self.assertIn("backtest_layer_must_not_write:structure_suitable", gate["issues"])

    def test_interface_boundary_gate_allows_tachibana_adapter_context_fields(self) -> None:
        record = {
            "interface_layer": "tachibana_adapter",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "method_action": "wait_no_action",
            "pm_required": False,
            "execution_intent": "replay_hypothesis_plan",
        }

        gate = audit_interface_boundary_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["next_action"], "action:continue")
        self.assertEqual(gate["issues"], [])

    def test_rhythm_sample_row_gate_allows_clean_alive_wave_meaningful_row(self) -> None:
        row = {
            "sample_id": "1975-01",
            "source_scope": "historical_review",
            "snapshot_quality_status": "ready",
            "malf_background": "alive_wave",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["row_status"], "rhythm_row_ready")
        self.assertEqual(gate["next_action"], "action:fill_candidate_table")
        self.assertEqual(gate["issues"], [])

    def test_rhythm_sample_row_gate_blocks_meaningful_when_pm_complexity_is_high(self) -> None:
        row = {
            "sample_id": "1976-11",
            "source_scope": "historical_review",
            "snapshot_quality_status": "ready",
            "malf_background": "alive_wave",
            "qualification_rule_id": "Q-EXTREME-ADDON",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "high",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_treat_addon_size_as_structure_strength"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("meaningful_requires_low_pm_complexity", gate["issues"])
        self.assertIn("q_extreme_addon_requires_limited", gate["issues"])

    def test_rhythm_sample_row_gate_blocks_rule_catalog_mismatches(self) -> None:
        row = {
            "sample_id": "BAD-CATALOG",
            "source_scope": "fixture",
            "snapshot_quality_status": "ready",
            "malf_background": "pullback",
            "qualification_rule_id": "Q-PRESSURE-ADJUST",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("rule_catalog_rhythm_mismatch:Q-PRESSURE-ADJUST", gate["issues"])
        self.assertIn("rule_catalog_applicability_mismatch:Q-PRESSURE-ADJUST", gate["issues"])
        self.assertIn("rule_catalog_pm_complexity_mismatch:Q-PRESSURE-ADJUST", gate["issues"])

    def test_rhythm_sample_row_gate_blocks_unknown_qualification_rule_id(self) -> None:
        row = {
            "sample_id": "UNKNOWN-RULE",
            "source_scope": "fixture",
            "snapshot_quality_status": "ready",
            "malf_background": "pullback",
            "qualification_rule_id": "Q-NOT-IN-CATALOG",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "pm_complexity": "medium",
            "meaning_reason": ["rhythm_meaning_limited"],
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("unknown_qualification_rule_id:Q-NOT-IN-CATALOG", gate["issues"])

    def test_rhythm_sample_row_gate_allows_no_structure_not_meaningful_row(self) -> None:
        row = {
            "sample_id": "NM-FIXTURE",
            "source_scope": "synthetic_test_fixture",
            "snapshot_quality_status": "ready",
            "malf_background": "no_structure",
            "qualification_rule_id": "NM-NO-STRUCTURE",
            "rhythm_meaning": "not_meaningful",
            "tachibana_applicability": "unsuitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_not_meaningful"],
            "boundary_warning": ["do_not_convert_applicability_to_signal_accept"],
            "evidence_level": ["E1_malf_snapshot", "E2_ashare_daily_fact"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["row_status"], "rhythm_row_ready")
        self.assertEqual(gate["next_action"], "action:research_audit_only")

    def test_rhythm_sample_row_gate_blocks_not_ready_snapshot_from_meaningful(self) -> None:
        row = {
            "sample_id": "PENDING",
            "source_scope": "ashare_real_sample",
            "snapshot_quality_status": "incomplete",
            "malf_background": "alive_wave",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "pm_complexity": "none",
            "meaning_reason": ["rhythm_meaning_meaningful"],
            "boundary_warning": ["do_not_upgrade_without_malf_snapshot"],
            "evidence_level": ["source_missing"],
        }

        gate = audit_rhythm_sample_row_gate(row)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("non_ready_snapshot_requires_unknown", gate["issues"])
        self.assertIn("non_ready_snapshot_requires_unknown_applicability", gate["issues"])

    def test_cognitive_pipeline_gate_allows_institution_discussion_only_after_all_prior_gates_pass(self) -> None:
        record = {
            "ashare_sample_id": "ASHARE-READY-001",
            "contract_check_result": "pass",
            "eligible_for_malf_run": True,
            "malf_snapshot_ref": "SNAP-READY",
            "snapshot_quality_status": "ready",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "institution_constraint_need": "execution_feasibility",
            "candidate_table_gate": {"result": "pass", "issues": []},
            "rhythm_sample_row_gate": {"result": "pass", "issues": []},
            "method_pm_bridge_gate": {"result": "pass", "issues": []},
            "interface_boundary_gate": {"result": "pass", "issues": []},
            "backtest_input_gate": {"result": "pass", "mode": "hypothesis_replay", "issues": []},
            "front_filter_system_audit": {"result": "pass", "blocked_audits": []},
        }

        gate = audit_cognitive_pipeline_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertTrue(gate["institution_adaptation_allowed"])
        self.assertEqual(gate["next_action"], "action:start_institution_constraint_audit")
        self.assertEqual(gate["issues"], [])

    def test_cognitive_pipeline_gate_blocks_institution_discussion_when_contract_or_need_is_missing(self) -> None:
        record = {
            "ashare_sample_id": "ASHARE-BLOCKED-001",
            "contract_check_result": "fail",
            "eligible_for_malf_run": False,
            "malf_snapshot_ref": None,
            "snapshot_quality_status": "source_missing",
            "rhythm_meaning": "unknown",
            "tachibana_applicability": "unknown",
            "institution_constraint_need": "none",
            "candidate_table_gate": {"result": "blocked", "issues": ["candidate_table_requires_tachibana_candidate"]},
            "rhythm_sample_row_gate": {"result": "blocked", "issues": ["non_ready_snapshot_requires_unknown"]},
            "method_pm_bridge_gate": {"result": "blocked", "issues": ["method_pm_requires_execution_intent"]},
            "interface_boundary_gate": {"result": "pass", "issues": []},
            "backtest_input_gate": {"result": "blocked", "mode": "research_audit", "issues": ["backtest_input_requires_method_plan"]},
            "front_filter_system_audit": {"result": "blocked", "blocked_audits": ["rhythm_sample_catalog"]},
        }

        gate = audit_cognitive_pipeline_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertFalse(gate["institution_adaptation_allowed"])
        self.assertEqual(gate["next_action"], "action:repair_data")
        self.assertIn("pipeline_requires_contract_pass_or_warn", gate["issues"])
        self.assertIn("pipeline_requires_eligible_for_malf_run", gate["issues"])
        self.assertIn("pipeline_requires_ready_malf_snapshot", gate["issues"])
        self.assertIn("pipeline_requires_institution_constraint_need", gate["issues"])
        self.assertIn("pipeline_requires_front_filter_system_audit_pass", gate["issues"])
        self.assertIn("front_filter_system_audit_issue:rhythm_sample_catalog", gate["issues"])

    def test_cognitive_pipeline_gate_blocks_when_front_filter_system_audit_is_missing(self) -> None:
        record = {
            "ashare_sample_id": "ASHARE-NO-SYSTEM-AUDIT",
            "contract_check_result": "pass",
            "eligible_for_malf_run": True,
            "malf_snapshot_ref": "SNAP-READY",
            "snapshot_quality_status": "ready",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "institution_constraint_need": "execution_feasibility",
            "candidate_table_gate": {"result": "pass", "issues": []},
            "rhythm_sample_row_gate": {"result": "pass", "issues": []},
            "method_pm_bridge_gate": {"result": "pass", "issues": []},
            "interface_boundary_gate": {"result": "pass", "issues": []},
            "backtest_input_gate": {"result": "pass", "mode": "hypothesis_replay", "issues": []},
        }

        gate = audit_cognitive_pipeline_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("pipeline_requires_front_filter_system_audit_pass", gate["issues"])

    def test_backtest_input_gate_blocks_candidate_without_method_pm_plan(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-NO-METHOD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_infer_position_size_from_malf"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "candidate_table_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:fill_candidate_table",
            },
        }

        gate = audit_backtest_input_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertEqual(gate["mode"], "research_audit")
        self.assertEqual(gate["next_action"], "action:method_pm_review")
        self.assertIn("backtest_input_requires_method_plan", gate["issues"])
        self.assertIn("backtest_input_requires_execution_intent", gate["issues"])

    def test_backtest_input_gate_allows_hypothesis_replay_when_method_pm_bridge_is_present(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-METHOD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "limited",
            "tachibana_applicability": "conditional",
            "qualification_rule_id": "Q-LOCK-WAIT",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": [
                "do_not_infer_position_size_from_malf",
                "do_not_generate_trade_from_rhythm_meaning_only",
            ],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "candidate_table_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:fill_candidate_table",
            },
            "method_action": "wait_no_action",
            "method_status": "hypothesis",
            "method_reason": ["active_waiting"],
            "pm_required": True,
            "pm_action": "hold",
            "method_pm_bridge_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:build_backtest_input_snapshot",
            },
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "hold",
        }

        gate = audit_backtest_input_gate(record)

        self.assertEqual(gate["result"], "pass")
        self.assertEqual(gate["mode"], "hypothesis_replay")
        self.assertEqual(gate["next_action"], "action:build_backtest_input_snapshot")
        self.assertEqual(gate["issues"], [])
        self.assertIn("method_action", gate["required_fields_checked"])
        self.assertIn("candidate_table_gate", gate["required_fields_checked"])

    def test_backtest_input_gate_blocks_rhythm_only_and_forbidden_signal_fields(self) -> None:
        record = {
            "qualification_record_id": "ASHARE-QUAL-RHYTHM-ONLY-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "meaningful",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": "Q-ALIVE-CLEAN",
            "next_action": "action:fill_candidate_table",
            "boundary_warning": ["do_not_generate_trade_from_rhythm_meaning_only"],
            "evidence_level": ["E1_malf_snapshot", "E4_research_mapping"],
            "record_consistency": {"result": "pass", "issues": []},
            "candidate_table_gate": {
                "result": "pass",
                "issues": [],
                "next_action": "action:fill_candidate_table",
            },
            "method_action": "trend_probe_entry",
            "method_status": "hypothesis",
            "method_reason": ["staged_execution"],
            "pm_required": False,
            "execution_intent": "replay_hypothesis_plan",
            "execution_event_type": "open",
            "signal_decision_from_rhythm": "accept",
        }

        gate = audit_backtest_input_gate(record)

        self.assertEqual(gate["result"], "blocked")
        self.assertIn("backtest_input_forbidden_field:signal_decision_from_rhythm", gate["issues"])

    def test_record_consistency_detects_stage_meaning_and_forbidden_field_contradictions(self) -> None:
        bad_record = {
            "qualification_record_id": "ASHARE-QUAL-BAD-v0.1",
            "candidate_stage_after": "tachibana_candidate",
            "rhythm_meaning": "unknown",
            "tachibana_applicability": "suitable",
            "qualification_rule_id": None,
            "next_action": "action:fill_candidate_table",
            "record_status": "draft",
            "boundary_warning": [],
            "target_position": 0.5,
        }

        audit = audit_qualification_record_consistency(bad_record)

        self.assertEqual(audit["result"], "fail")
        self.assertIn("tachibana_candidate_requires_meaningful_or_limited", audit["issues"])
        self.assertIn("suitable_requires_meaningful", audit["issues"])
        self.assertIn("tachibana_candidate_requires_qualification_rule_id", audit["issues"])
        self.assertIn("forbidden_record_field:target_position", audit["issues"])

    def test_record_consistency_detects_not_meaningful_candidate_table_upgrade(self) -> None:
        bad_record = {
            "qualification_record_id": "ASHARE-QUAL-BAD-NM-v0.1",
            "candidate_stage_after": "rejected",
            "rhythm_meaning": "not_meaningful",
            "tachibana_applicability": "unsuitable",
            "qualification_rule_id": "NM-NO-STRUCTURE",
            "next_action": "action:fill_candidate_table",
            "record_status": "draft",
            "boundary_warning": [],
        }

        audit = audit_qualification_record_consistency(bad_record)

        self.assertEqual(audit["result"], "fail")
        self.assertIn("not_meaningful_must_research_audit_only", audit["issues"])
        self.assertIn("unsuitable_must_not_fill_candidate_table", audit["issues"])


if __name__ == "__main__":
    unittest.main()
