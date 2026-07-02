from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalShortlistMaterializationTest(TdxLocalFirstBatchSupport):
    def test_audit_institution_rule_definition_contract_review_when_explicitly_requested_passes_contract_ready_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7c_contract_review_inputs(Path(tmp))

            report = audit_institution_rule_definition_contract_review_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T13:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "institution_rule_definition_contract_review_audit_v0.1")
        self.assertEqual(report["institution_rule_definition_contract_review_result"], "pass")
        self.assertEqual(
            report["institution_rule_definition_contract_review_status"],
            "ready_for_explicit_institution_rule_definition_open_gate_review",
        )
        self.assertEqual(
            report["contract_reviewed_rule_draft_inputs"],
            ["t1", "price_limit", "suspension_resume"],
        )
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_explicit_institution_rule_definition_open_gate")
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_audit_institution_rule_definition_contract_review_when_explicitly_requested_blocks_missing_or_failed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7c_contract_review_inputs(Path(tmp))
            cases = [
                (
                    "p7b_draft_review_gate_report",
                    None,
                    "institution_rule_definition_contract_review_requires_p7b_draft_review_gate_pass",
                ),
                (
                    "p7b_draft_review_gate_report",
                    {"institution_rule_definition_draft_review_gate_result": "blocked"},
                    "institution_rule_definition_contract_review_requires_p7b_draft_review_gate_pass",
                ),
                (
                    "t1_rule_draft_input",
                    None,
                    "institution_rule_definition_contract_review_requires_t1_contract_ready_draft",
                ),
                (
                    "price_limit_rule_draft_input",
                    None,
                    "institution_rule_definition_contract_review_requires_price_limit_contract_ready_draft",
                ),
                (
                    "suspension_resume_rule_draft_input",
                    None,
                    "institution_rule_definition_contract_review_requires_suspension_resume_contract_ready_draft",
                ),
                (
                    "t1_rule_draft_input",
                    {**inputs["t1_rule_draft_input"], "draft_input_only": False},
                    "institution_rule_definition_contract_review_requires_draft_input_only",
                ),
            ]
            reports = []
            for field, replacement, _issue in cases:
                payload = dict(inputs)
                payload[field] = replacement
                reports.append(
                    audit_institution_rule_definition_contract_review_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T13:20:00+08:00",
                    )
                )

        for report, (_field, _replacement, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_contract_review_when_explicitly_requested_blocks_incomplete_contract_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7c_contract_review_inputs(Path(tmp))
            cases = [
                (
                    {"contract_review_status": "needs_rework"},
                    "institution_rule_definition_contract_review_requires_ready_contract_review",
                ),
                (
                    {"definition_contract_fields": []},
                    "institution_rule_definition_contract_review_requires_definition_contract_fields",
                ),
                (
                    {"consumer_entrypoint": "trading_layer"},
                    "institution_rule_definition_contract_review_requires_definition_consumer_entrypoint",
                ),
                (
                    {"field_contract_status": "incomplete"},
                    "institution_rule_definition_contract_review_requires_complete_field_contract",
                ),
            ]
            reports = []
            for updates, _issue in cases:
                payload = dict(inputs)
                payload["price_limit_rule_draft_input"] = dict(payload["price_limit_rule_draft_input"])
                payload["price_limit_rule_draft_input"].update(updates)
                reports.append(
                    audit_institution_rule_definition_contract_review_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T13:30:00+08:00",
                    )
                )

        for report, (_updates, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_contract_review_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7c_contract_review_inputs(Path(tmp))
            inputs["t1_rule_draft_input"] = dict(inputs["t1_rule_draft_input"])
            inputs["t1_rule_draft_input"]["target_position"] = 0.2

            report = audit_institution_rule_definition_contract_review_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T13:40:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("institution_rule_definition_contract_review_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("target_position", payload)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_contract_review_when_explicitly_requested_keeps_hard_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7c_contract_review_inputs(Path(tmp))

            report = audit_institution_rule_definition_contract_review_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T13:50:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_passes_explicit_rule_definition_only_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7d_open_gate_inputs(Path(tmp))

            report = audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T14:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "explicit_institution_rule_definition_open_gate_audit_v0.1")
        self.assertEqual(report["explicit_institution_rule_definition_open_gate_result"], "pass")
        self.assertEqual(
            report["explicit_institution_rule_definition_open_gate_status"],
            "institution_rule_definition_opened_for_rule_definition_only",
        )
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:define_formal_institution_rules_only")
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_blocks_missing_or_failed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7d_open_gate_inputs(Path(tmp))
            cases = [
                (
                    "p7c_contract_review_report",
                    None,
                    "explicit_institution_rule_definition_open_gate_requires_p7c_contract_review_pass",
                ),
                (
                    "p7c_contract_review_report",
                    {"institution_rule_definition_contract_review_result": "blocked"},
                    "explicit_institution_rule_definition_open_gate_requires_p7c_contract_review_pass",
                ),
                (
                    "t1_rule_draft_input",
                    None,
                    "explicit_institution_rule_definition_open_gate_requires_t1_contract_ready_draft",
                ),
                (
                    "price_limit_rule_draft_input",
                    None,
                    "explicit_institution_rule_definition_open_gate_requires_price_limit_contract_ready_draft",
                ),
                (
                    "suspension_resume_rule_draft_input",
                    None,
                    "explicit_institution_rule_definition_open_gate_requires_suspension_resume_contract_ready_draft",
                ),
                (
                    "t1_rule_draft_input",
                    {**inputs["t1_rule_draft_input"], "draft_input_only": False},
                    "explicit_institution_rule_definition_open_gate_requires_draft_input_only",
                ),
            ]
            reports = []
            for field, replacement, _issue in cases:
                payload = dict(inputs)
                payload[field] = replacement
                reports.append(
                    audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T14:20:00+08:00",
                    )
                )

        for report, (_field, _replacement, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_blocks_bad_open_gate_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7d_open_gate_inputs(Path(tmp))
            cases = [
                (
                    None,
                    "explicit_institution_rule_definition_open_gate_requires_explicit_open_gate_decision",
                ),
                (
                    {**inputs["explicit_open_gate_decision"], "gate_decision": "approve_trading"},
                    "explicit_institution_rule_definition_open_gate_requires_rule_definition_only_decision",
                ),
                (
                    {**inputs["explicit_open_gate_decision"], "gate_scope": "trading_layer"},
                    "explicit_institution_rule_definition_open_gate_requires_rule_definition_only_scope",
                ),
                (
                    {**inputs["explicit_open_gate_decision"], "approved_by": ""},
                    "explicit_institution_rule_definition_open_gate_requires_approval_identity",
                ),
                (
                    {**inputs["explicit_open_gate_decision"], "approval_evidence_refs": []},
                    "explicit_institution_rule_definition_open_gate_requires_approval_evidence_refs",
                ),
                (
                    {**inputs["explicit_open_gate_decision"], "acknowledged_no_signal_generation": False},
                    "explicit_institution_rule_definition_open_gate_requires_no_downstream_acknowledgement",
                ),
            ]
            reports = []
            for replacement, _issue in cases:
                payload = dict(inputs)
                payload["explicit_open_gate_decision"] = replacement
                reports.append(
                    audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T14:30:00+08:00",
                    )
                )

        for report, (_replacement, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7d_open_gate_inputs(Path(tmp))
            inputs["explicit_open_gate_decision"] = dict(inputs["explicit_open_gate_decision"])
            inputs["explicit_open_gate_decision"]["signal_decision"] = "accept"

            report = audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T14:40:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("explicit_institution_rule_definition_open_gate_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("signal_decision", payload)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested_opens_only_rule_definition_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7d_open_gate_inputs(Path(tmp))

            report = audit_explicit_institution_rule_definition_open_gate_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T14:50:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_when_explicitly_requested_passes_rule_definition_only_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7e_formal_rule_definition_inputs(Path(tmp))

            report = audit_formal_institution_rule_definition_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T15:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "formal_institution_rule_definition_audit_v0.1")
        self.assertEqual(report["formal_institution_rule_definition_result"], "pass")
        self.assertEqual(
            report["formal_institution_rule_definition_status"],
            "formal_institution_rule_definition_audited_for_rule_definition_only",
        )
        self.assertEqual(report["p7d_open_gate_result"], "pass")
        self.assertEqual(
            report["consumed_reviewed_draft_inputs"],
            ["t1", "price_limit", "suspension_resume"],
        )
        self.assertEqual(report["formal_institution_rule_definition_field_contract_status"], "complete")
        self.assertEqual(report["formal_institution_rule_definition_boundary_status"], "clean")
        self.assertEqual(report["formal_institution_rule_definition_evidence_status"], "ready")
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(
            report["next_action"],
            "action:prepare_formal_institution_rule_definition_persistence_package_when_explicitly_requested",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_audit_formal_institution_rule_definition_when_explicitly_requested_blocks_missing_or_failed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7e_formal_rule_definition_inputs(Path(tmp))
            cases = [
                ("p7d_open_gate_report", None, "formal_institution_rule_definition_requires_p7d_open_gate_pass"),
                (
                    "p7d_open_gate_report",
                    {"explicit_institution_rule_definition_open_gate_result": "blocked"},
                    "formal_institution_rule_definition_requires_p7d_open_gate_pass",
                ),
                (
                    "t1_rule_draft_input",
                    None,
                    "formal_institution_rule_definition_requires_t1_contract_ready_draft",
                ),
                (
                    "price_limit_rule_draft_input",
                    None,
                    "formal_institution_rule_definition_requires_price_limit_contract_ready_draft",
                ),
                (
                    "suspension_resume_rule_draft_input",
                    None,
                    "formal_institution_rule_definition_requires_suspension_resume_contract_ready_draft",
                ),
                (
                    "formal_institution_rule_definition_input",
                    None,
                    "formal_institution_rule_definition_requires_definition_input",
                ),
                (
                    "formal_institution_rule_definition_input",
                    {"consumed_reviewed_draft_inputs": ["t1", "price_limit"]},
                    "formal_institution_rule_definition_requires_full_reviewed_draft_coverage",
                ),
                (
                    "formal_institution_rule_definition_input",
                    {"field_contract_status": "incomplete"},
                    "formal_institution_rule_definition_requires_complete_field_contract",
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
                    audit_formal_institution_rule_definition_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T15:20:00+08:00",
                    )
                )

        for report, (_field, _updates, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7e_formal_rule_definition_inputs(Path(tmp))
            inputs["formal_institution_rule_definition_input"] = dict(inputs["formal_institution_rule_definition_input"])
            inputs["formal_institution_rule_definition_input"]["signal_decision"] = "buy"

            report = audit_formal_institution_rule_definition_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T15:30:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("formal_institution_rule_definition_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("signal_decision", payload)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_formal_institution_rule_definition_when_explicitly_requested_keeps_downstream_hard_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7e_formal_rule_definition_inputs(Path(tmp))

            report = audit_formal_institution_rule_definition_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T15:40:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])


