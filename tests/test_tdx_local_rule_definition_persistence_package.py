from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalRuleDefinitionPersistencePackageTest(TdxLocalFirstBatchSupport):
    def test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_passes_package_ready_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p8_formal_rule_definition_persistence_package_inputs(Path(tmp))

            report = prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T16:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "formal_institution_rule_definition_persistence_package_v0.1")
        self.assertEqual(report["report_id"], "formal_institution_rule_definition_persistence_package_report_v0.1")
        self.assertEqual(report["package_id"], "formal_institution_rule_definition_persistence_package_v0.1")
        self.assertEqual(report["package_version"], "v0.1")
        self.assertEqual(report["formal_institution_rule_definition_persistence_package_result"], "pass")
        self.assertEqual(
            report["formal_institution_rule_definition_persistence_package_status"],
            "formal_institution_rule_definition_persistence_package_prepared",
        )
        self.assertTrue(report["formal_institution_rule_definition_persistence_package_prepared"])
        self.assertFalse(report["formal_institution_rule_definition_persistence_performed"])
        self.assertEqual(report["source_formal_institution_rule_definition_result"], "pass")
        self.assertEqual(
            report["packaged_rule_definition_inputs"],
            ["t1", "price_limit", "suspension_resume"],
        )
        self.assertEqual(report["package_field_contract_status"], "complete")
        self.assertEqual(report["package_boundary_status"], "clean")
        self.assertEqual(report["package_evidence_status"], "ready")
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(
            report["next_action"],
            "action:audit_formal_institution_rule_definition_write_when_explicitly_requested",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_blocks_missing_or_failed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p8_formal_rule_definition_persistence_package_inputs(Path(tmp))
            cases = [
                (
                    "p7e_formal_rule_definition_report",
                    None,
                    "formal_institution_rule_definition_persistence_package_requires_p7e_pass",
                ),
                (
                    "p7e_formal_rule_definition_report",
                    {"formal_institution_rule_definition_result": "blocked"},
                    "formal_institution_rule_definition_persistence_package_requires_p7e_pass",
                ),
                (
                    "formal_institution_rule_definition_payload",
                    None,
                    "formal_institution_rule_definition_persistence_package_requires_definition_payload",
                ),
                (
                    "formal_institution_rule_definition_payload",
                    {"consumed_reviewed_draft_inputs": ["t1", "price_limit"]},
                    "formal_institution_rule_definition_persistence_package_requires_full_reviewed_draft_coverage",
                ),
                (
                    "formal_institution_rule_definition_payload",
                    {"field_contract_status": "incomplete"},
                    "formal_institution_rule_definition_persistence_package_requires_complete_field_contract",
                ),
            ]
            reports = []
            for field, updates, _issue in cases:
                payload = dict(inputs)
                if updates is None:
                    payload[field] = None
                else:
                    payload[field] = dict(payload[field])
                    payload[field].update(updates)
                reports.append(
                    prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T16:20:00+08:00",
                    )
                )

        for report, (_field, _updates, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["formal_institution_rule_definition_persistence_package_prepared"])
            self.assertFalse(report["formal_institution_rule_definition_persistence_performed"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p8_formal_rule_definition_persistence_package_inputs(Path(tmp))
            inputs["formal_institution_rule_definition_payload"] = dict(
                inputs["formal_institution_rule_definition_payload"]
            )
            inputs["formal_institution_rule_definition_payload"]["position_size"] = 1.0

            report = prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T16:30:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn(
            "formal_institution_rule_definition_persistence_package_forbidden_output_field_present",
            report["issues"],
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("position_size", payload)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested_keeps_downstream_hard_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p8_formal_rule_definition_persistence_package_inputs(Path(tmp))

            report = prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T16:40:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertFalse(report["formal_institution_rule_definition_persistence_performed"])


