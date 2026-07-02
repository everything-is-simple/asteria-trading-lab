from tests.tachibana_front_filter_support import *


class TachibanaCatalogsTest(unittest.TestCase):
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
        self.assertEqual(audit["sample_count"], 18)
        self.assertEqual(audit["passed_sample_count"], 18)
        self.assertEqual(audit["blocked_sample_count"], 0)
        self.assertEqual(audit["missing_rule_ids"], [])
        self.assertEqual(audit["covered_rhythm_meanings"], [
            "limited",
            "meaningful",
            "not_meaningful",
            "unknown",
        ])
        self.assertEqual(audit["missing_rhythm_meanings"], [])
        self.assertEqual(audit["sample_count_by_rhythm_meaning"]["meaningful"], 2)
        self.assertEqual(audit["sample_count_by_rhythm_meaning"]["limited"], 10)
        self.assertEqual(audit["sample_count_by_rhythm_meaning"]["unknown"], 2)
        self.assertEqual(audit["sample_count_by_rhythm_meaning"]["not_meaningful"], 4)
        self.assertEqual(audit["minimum_sample_count_by_rhythm_meaning"], {
            "limited": 2,
            "meaningful": 2,
            "not_meaningful": 2,
            "unknown": 2,
        })
        self.assertEqual(audit["undercovered_rhythm_meanings"], {})
        self.assertEqual(len(audit["covered_rule_ids"]), 16)
        self.assertEqual(audit["blocked_samples"], {})

    def test_rhythm_sample_catalog_audit_blocks_undercovered_rhythm_meanings(self) -> None:
        samples = get_rhythm_sample_catalog()
        samples = {
            sample_id: row
            for sample_id, row in samples.items()
            if row["rhythm_meaning"] != "unknown" or sample_id == "1976-09"
        }

        audit = audit_rhythm_sample_catalog(samples)

        self.assertEqual(audit["result"], "blocked")
        self.assertEqual(audit["sample_count_by_rhythm_meaning"]["unknown"], 1)
        self.assertEqual(audit["undercovered_rhythm_meanings"], {
            "unknown": {"actual": 1, "minimum": 2},
        })
        self.assertIn("unknown", audit["covered_rhythm_meanings"])
        self.assertEqual(audit["missing_rhythm_meanings"], [])

    def test_rhythm_sample_catalog_audit_blocks_future_industry_label_on_dated_samples(self) -> None:
        samples = get_rhythm_sample_catalog()
        samples["FUTURE-INDUSTRY-LABEL"] = {
            **samples["1975-01"],
            "sample_id": "FUTURE-INDUSTRY-LABEL",
            "sample_window_start": "2026-04-25",
            "sample_window_end": "2026-06-30",
            "current_industry_valid_from": "2026-07-01",
            "current_industry_valid_to": "",
        }

        audit = audit_rhythm_sample_catalog(samples)

        self.assertEqual(audit["result"], "blocked")
        self.assertEqual(audit["passed_sample_count"], 18)
        self.assertEqual(audit["blocked_sample_count"], 1)
        self.assertEqual(audit["industry_time_alignment_result"], "blocked")
        self.assertEqual(audit["industry_time_alignment_blocked_count"], 1)
        self.assertIn("FUTURE-INDUSTRY-LABEL", audit["industry_time_alignment_blocked_samples"])
        self.assertIn(
            "future_industry_label_valid_from_after_sample_window_end",
            audit["industry_time_alignment_blocked_samples"]["FUTURE-INDUSTRY-LABEL"]["issues"],
        )
        self.assertIn(
            "future_industry_label_valid_from_after_sample_window_end",
            audit["blocked_samples"]["FUTURE-INDUSTRY-LABEL"]["issues"],
        )

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
        self.assertEqual(audit["sample_count"], 19)
        self.assertEqual(audit["blocked_sample_count"], 1)
        self.assertIn("BAD-MEANINGFUL", audit["blocked_samples"])
        self.assertIn(
            "rule_catalog_rhythm_mismatch:Q-EXTREME-ADDON",
            audit["blocked_samples"]["BAD-MEANINGFUL"]["issues"],
        )

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
