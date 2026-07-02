from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalRuleDefinitionWriteAuditTest(TdxLocalFirstBatchSupport):
    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_passes_valid_package_and_request(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)

            report = audit_formal_institution_rule_definition_write_when_explicitly_requested(
                formal_rule_definition_persistence_package_report=package_report,
                formal_rule_definition_write_audit_request=request,
                generated_at="2026-07-02T09:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "formal_institution_rule_definition_write_audit_v0.1")
        self.assertEqual(report["formal_institution_rule_definition_write_audit_result"], "pass")
        self.assertEqual(
            report["formal_institution_rule_definition_write_audit_status"],
            "ready_for_formal_institution_rule_definition_explicit_write_confirmation_gate",
        )
        self.assertFalse(report["formal_institution_rule_definition_write_allowed"])
        self.assertFalse(report["formal_institution_rule_definition_persistence_performed"])
        self.assertEqual(report["source_package_id"], package_report["package_id"])
        self.assertEqual(report["source_package_version"], package_report["package_version"])
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertEqual(report["institution_rule_definition_scope"], "rule-definition-only")
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(
            report["next_gate"],
            "gate:formal_institution_rule_definition_explicit_write_confirmation",
        )
        self.assertEqual(report["package_staleness_policy"], "not_enforced_v0.1")
        self.assertEqual(
            report["write_audit_idempotency_policy"],
            "same_package_identity_is_idempotent_v0.1",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_blocks_missing_or_failed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)
            cases = [
                (
                    "formal_rule_definition_persistence_package_report",
                    None,
                    "formal_institution_rule_definition_write_audit_requires_p8_package_pass",
                ),
                (
                    "formal_rule_definition_persistence_package_report",
                    {"formal_institution_rule_definition_persistence_package_result": "blocked"},
                    "formal_institution_rule_definition_write_audit_requires_p8_package_pass",
                ),
                (
                    "formal_rule_definition_persistence_package_report",
                    {"report_id": None},
                    "formal_institution_rule_definition_write_audit_requires_report_id",
                ),
                (
                    "formal_rule_definition_persistence_package_report",
                    {"package_id": None},
                    "formal_institution_rule_definition_write_audit_requires_package_identity",
                ),
                (
                    "formal_rule_definition_persistence_package_report",
                    {"package_version": None},
                    "formal_institution_rule_definition_write_audit_requires_package_identity",
                ),
                (
                    "formal_rule_definition_write_audit_request",
                    None,
                    "formal_institution_rule_definition_write_audit_requires_request",
                ),
                (
                    "formal_rule_definition_write_audit_request",
                    {"real_data_root_write_confirmed": True},
                    "formal_institution_rule_definition_write_audit_rejects_early_real_data_root_confirmation",
                ),
                (
                    "formal_rule_definition_write_audit_request",
                    {"no_trading_no_signal_no_backtest_acknowledged": False},
                    "formal_institution_rule_definition_write_audit_requires_no_downstream_acknowledgement",
                ),
            ]
            reports = []
            for field, update, _issue in cases:
                payload = {
                    "formal_rule_definition_persistence_package_report": dict(package_report),
                    "formal_rule_definition_write_audit_request": dict(request),
                }
                if update is None:
                    payload[field] = None
                else:
                    payload[field].update(update)
                reports.append(
                    audit_formal_institution_rule_definition_write_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-02T09:20:00+08:00",
                    )
                )

        for report, (_field, _update, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["formal_institution_rule_definition_write_allowed"])
            self.assertFalse(report["formal_institution_rule_definition_persistence_performed"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_blocks_package_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)
            mismatched_package_request = dict(request)
            mismatched_package_request["target_package_id"] = "wrong-package"
            mismatched_version_request = dict(request)
            mismatched_version_request["target_package_version"] = "wrong-version"
            reports = [
                audit_formal_institution_rule_definition_write_when_explicitly_requested(
                    formal_rule_definition_persistence_package_report=package_report,
                    formal_rule_definition_write_audit_request=mismatched_package_request,
                    generated_at="2026-07-02T09:30:00+08:00",
                ),
                audit_formal_institution_rule_definition_write_when_explicitly_requested(
                    formal_rule_definition_persistence_package_report=package_report,
                    formal_rule_definition_write_audit_request=mismatched_version_request,
                    generated_at="2026-07-02T09:31:00+08:00",
                ),
            ]

        for report in reports:
            self.assertEqual(report["result"], "blocked")
            self.assertIn("formal_institution_rule_definition_write_audit_package_identity_mismatch", report["issues"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_blocks_write_allowed_true_or_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)
            reports = []
            for value in [True, "true"]:
                payload = dict(package_report)
                payload["formal_institution_rule_definition_write_allowed"] = value
                reports.append(
                    audit_formal_institution_rule_definition_write_when_explicitly_requested(
                        formal_rule_definition_persistence_package_report=payload,
                        formal_rule_definition_write_audit_request=request,
                        generated_at="2026-07-02T09:40:00+08:00",
                    )
                )

        for report in reports:
            self.assertEqual(report["result"], "blocked")
            self.assertIn(
                "formal_institution_rule_definition_write_audit_requires_write_not_already_allowed",
                report["issues"],
            )
            self.assertFalse(report["formal_institution_rule_definition_write_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            package_report["position_size"] = 1.0
            request = self._formal_rule_definition_write_audit_request(package_report)

            report = audit_formal_institution_rule_definition_write_when_explicitly_requested(
                formal_rule_definition_persistence_package_report=package_report,
                formal_rule_definition_write_audit_request=request,
                generated_at="2026-07-02T09:50:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn(
            "formal_institution_rule_definition_write_audit_forbidden_output_field_present",
            report["issues"],
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("position_size", payload)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_keeps_downstream_hard_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)

            report = audit_formal_institution_rule_definition_write_when_explicitly_requested(
                formal_rule_definition_persistence_package_report=package_report,
                formal_rule_definition_write_audit_request=request,
                generated_at="2026-07-02T10:00:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["formal_institution_rule_definition_write_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_write_when_explicitly_requested_is_idempotent_for_same_package_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_report = self._p8_prepared_package_report(Path(tmp))
            request = self._formal_rule_definition_write_audit_request(package_report)

            first = audit_formal_institution_rule_definition_write_when_explicitly_requested(
                formal_rule_definition_persistence_package_report=package_report,
                formal_rule_definition_write_audit_request=request,
                generated_at="2026-07-02T10:10:00+08:00",
            )
            second = audit_formal_institution_rule_definition_write_when_explicitly_requested(
                formal_rule_definition_persistence_package_report=package_report,
                formal_rule_definition_write_audit_request=request,
                generated_at="2026-07-02T10:11:00+08:00",
            )

        self.assertEqual(first["result"], "pass")
        self.assertEqual(second["result"], "pass")
        self.assertEqual(first["source_package_id"], second["source_package_id"])
        self.assertEqual(first["source_package_version"], second["source_package_version"])
        self.assertEqual(
            first["write_audit_idempotency_policy"],
            second["write_audit_idempotency_policy"],
        )
