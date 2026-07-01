from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalRuleDefinitionGatesTest(TdxLocalFirstBatchSupport):
    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_blocks_missing_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)
            (manifest_path.parent / "candidate-table.jsonl").unlink()

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:35:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_jsonl_missing", report["issues"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_blocks_malformed_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)
            (manifest_path.parent / "candidate-table.jsonl").write_text("{bad jsonl}\n", encoding="utf-8")

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:36:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_jsonl_invalid", report["issues"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_never_opens_downstream_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:40:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_trading_layer_read_gate_contract_when_explicitly_requested_passes_contract_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p6_contract_inputs(Path(tmp))

            report = audit_trading_layer_read_gate_contract_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T10:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "trading_layer_read_gate_contract_audit_v0.1")
        self.assertEqual(report["trading_layer_read_gate_contract_audit_result"], "pass")
        self.assertEqual(
            report["trading_layer_read_gate_contract_status"],
            "ready_for_trading_layer_read_contract_review",
        )
        self.assertEqual(report["candidate_table_trading_layer_readiness_audit_result"], "pass")
        self.assertEqual(report["method_pm_gate_result"], "pass")
        self.assertEqual(report["backtest_input_gate_result"], "pass")
        self.assertTrue(report["execution_constraint_audit_only"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_trading_layer_read_gate_contract")
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_audit_trading_layer_read_gate_contract_when_explicitly_requested_blocks_missing_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p6_contract_inputs(Path(tmp))
            cases = [
                ("p5_readiness_report", "trading_layer_read_gate_requires_p5_readiness_pass"),
                ("method_pm_gate", "trading_layer_read_gate_requires_method_pm_gate_pass"),
                ("backtest_input_gate", "trading_layer_read_gate_requires_backtest_input_gate_pass"),
                ("execution_constraint_artifact", "trading_layer_read_gate_requires_execution_constraint_audit_only"),
            ]
            reports = []
            for field, _issue in cases:
                payload = dict(inputs)
                payload[field] = None
                reports.append(
                    audit_trading_layer_read_gate_contract_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T10:20:00+08:00",
                    )
                )

        for report, (_field, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_trading_layer_read_gate_contract_when_explicitly_requested_blocks_failed_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p6_contract_inputs(Path(tmp))
            cases = [
                (
                    "p5_readiness_report",
                    {"candidate_table_trading_layer_readiness_audit_result": "blocked"},
                    "trading_layer_read_gate_requires_p5_readiness_pass",
                ),
                ("method_pm_gate", {"result": "blocked"}, "trading_layer_read_gate_requires_method_pm_gate_pass"),
                ("backtest_input_gate", {"result": "blocked"}, "trading_layer_read_gate_requires_backtest_input_gate_pass"),
                (
                    "execution_constraint_artifact",
                    {"audit_only": False},
                    "trading_layer_read_gate_requires_execution_constraint_audit_only",
                ),
            ]
            reports = []
            for field, updates, _issue in cases:
                payload = dict(inputs)
                payload[field] = dict(payload[field])
                payload[field].update(updates)
                reports.append(
                    audit_trading_layer_read_gate_contract_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T10:25:00+08:00",
                    )
                )

        for report, (_field, _updates, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_trading_layer_read_gate_contract_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p6_contract_inputs(Path(tmp))
            inputs["method_pm_gate"] = dict(inputs["method_pm_gate"])
            inputs["method_pm_gate"]["buy_signal"] = True

            report = audit_trading_layer_read_gate_contract_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T10:30:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("trading_layer_read_gate_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("buy_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_trading_layer_read_gate_contract_when_explicitly_requested_never_opens_trading_layer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p6_contract_inputs(Path(tmp))

            report = audit_trading_layer_read_gate_contract_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T10:40:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_readiness_when_explicitly_requested_passes_draft_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7_readiness_inputs(Path(tmp))

            report = audit_institution_rule_definition_readiness_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T11:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "institution_rule_definition_readiness_audit_v0.1")
        self.assertEqual(report["institution_rule_definition_readiness_audit_result"], "pass")
        self.assertEqual(
            report["institution_rule_definition_readiness_status"],
            "ready_for_institution_rule_definition_draft_review",
        )
        self.assertEqual(
            report["required_rule_draft_inputs"],
            ["t1", "price_limit", "suspension_resume"],
        )
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_institution_rule_definition_drafts")
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_audit_institution_rule_definition_readiness_when_explicitly_requested_blocks_missing_or_failed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7_readiness_inputs(Path(tmp))
            cases = [
                (
                    "p6_contract_report",
                    None,
                    "institution_rule_definition_readiness_requires_p6_contract_pass",
                ),
                (
                    "p6_contract_report",
                    {"trading_layer_read_gate_contract_audit_result": "blocked"},
                    "institution_rule_definition_readiness_requires_p6_contract_pass",
                ),
                (
                    "t1_rule_draft_input",
                    None,
                    "institution_rule_definition_readiness_requires_t1_draft_input",
                ),
                (
                    "price_limit_rule_draft_input",
                    None,
                    "institution_rule_definition_readiness_requires_price_limit_draft_input",
                ),
                (
                    "suspension_resume_rule_draft_input",
                    None,
                    "institution_rule_definition_readiness_requires_suspension_resume_draft_input",
                ),
                (
                    "t1_rule_draft_input",
                    {**inputs["t1_rule_draft_input"], "draft_input_only": False},
                    "institution_rule_definition_readiness_requires_draft_input_only",
                ),
            ]
            reports = []
            for field, replacement, _issue in cases:
                payload = dict(inputs)
                payload[field] = replacement
                reports.append(
                    audit_institution_rule_definition_readiness_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T11:20:00+08:00",
                    )
                )

        for report, (_field, _replacement, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_readiness_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7_readiness_inputs(Path(tmp))
            inputs["price_limit_rule_draft_input"] = dict(inputs["price_limit_rule_draft_input"])
            inputs["price_limit_rule_draft_input"]["rhythm_meaning_override"] = "meaningful"

            report = audit_institution_rule_definition_readiness_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T11:30:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("institution_rule_definition_readiness_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("rhythm_meaning_override", payload)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_readiness_when_explicitly_requested_keeps_hard_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7_readiness_inputs(Path(tmp))

            report = audit_institution_rule_definition_readiness_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T11:40:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_passes_review_ready_drafts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7b_draft_review_inputs(Path(tmp))

            report = audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T12:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "institution_rule_definition_draft_review_gate_audit_v0.1")
        self.assertEqual(report["institution_rule_definition_draft_review_gate_result"], "pass")
        self.assertEqual(
            report["institution_rule_definition_draft_review_status"],
            "ready_for_institution_rule_definition_contract_review",
        )
        self.assertEqual(
            report["reviewed_rule_draft_inputs"],
            ["t1", "price_limit", "suspension_resume"],
        )
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:write_p7c_institution_rule_definition_contract_review_spec")
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))

    def test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_blocks_missing_or_failed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7b_draft_review_inputs(Path(tmp))
            cases = [
                (
                    "p7a_readiness_report",
                    None,
                    "institution_rule_definition_draft_review_requires_p7a_readiness_pass",
                ),
                (
                    "p7a_readiness_report",
                    {"institution_rule_definition_readiness_audit_result": "blocked"},
                    "institution_rule_definition_draft_review_requires_p7a_readiness_pass",
                ),
                (
                    "t1_rule_draft_input",
                    None,
                    "institution_rule_definition_draft_review_requires_t1_review_ready_draft",
                ),
                (
                    "price_limit_rule_draft_input",
                    None,
                    "institution_rule_definition_draft_review_requires_price_limit_review_ready_draft",
                ),
                (
                    "suspension_resume_rule_draft_input",
                    None,
                    "institution_rule_definition_draft_review_requires_suspension_resume_review_ready_draft",
                ),
                (
                    "t1_rule_draft_input",
                    {**inputs["t1_rule_draft_input"], "draft_input_only": False},
                    "institution_rule_definition_draft_review_requires_draft_input_only",
                ),
            ]
            reports = []
            for field, replacement, _issue in cases:
                payload = dict(inputs)
                payload[field] = replacement
                reports.append(
                    audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T12:20:00+08:00",
                    )
                )

        for report, (_field, _replacement, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_blocks_incomplete_draft_quality(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7b_draft_review_inputs(Path(tmp))
            cases = [
                (
                    {"draft_quality_status": "needs_rework"},
                    "institution_rule_definition_draft_review_requires_ready_quality",
                ),
                (
                    {"field_contract_status": "incomplete"},
                    "institution_rule_definition_draft_review_requires_complete_field_contract",
                ),
                (
                    {"evidence_refs": []},
                    "institution_rule_definition_draft_review_requires_evidence_refs",
                ),
                (
                    {"boundary_review_status": "contaminated"},
                    "institution_rule_definition_draft_review_requires_clean_boundary",
                ),
            ]
            reports = []
            for updates, _issue in cases:
                payload = dict(inputs)
                payload["price_limit_rule_draft_input"] = dict(payload["price_limit_rule_draft_input"])
                payload["price_limit_rule_draft_input"].update(updates)
                reports.append(
                    audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
                        **payload,
                        generated_at="2026-07-01T12:30:00+08:00",
                    )
                )

        for report, (_updates, issue) in zip(reports, cases):
            self.assertEqual(report["result"], "blocked")
            self.assertIn(issue, report["issues"])
            self.assertFalse(report["institution_rule_definition_allowed"])
            self.assertFalse(report["trading_layer_read_allowed"])
            self.assertFalse(report["signal_generation_allowed"])
            self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_blocks_forbidden_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7b_draft_review_inputs(Path(tmp))
            inputs["suspension_resume_rule_draft_input"] = dict(inputs["suspension_resume_rule_draft_input"])
            inputs["suspension_resume_rule_draft_input"]["signal_decision"] = "accept"

            report = audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T12:40:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("institution_rule_definition_draft_review_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("signal_decision", payload)
        self.assertFalse(any(field in payload for field in P7_FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_institution_rule_definition_draft_review_gate_when_explicitly_requested_keeps_hard_gates_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inputs = self._p7b_draft_review_inputs(Path(tmp))

            report = audit_institution_rule_definition_draft_review_gate_when_explicitly_requested(
                **inputs,
                generated_at="2026-07-01T12:50:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])


