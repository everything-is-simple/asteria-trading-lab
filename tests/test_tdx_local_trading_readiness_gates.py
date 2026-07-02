from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalTradingReadinessGatesTest(TdxLocalFirstBatchSupport):
    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_forbidden_staging_row_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            table_root = staging_manifest.parent
            rows = [
                json.loads(line)
                for line in (table_root / "candidate-table-draft.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rows[0]["buy_signal"] = True
            (table_root / "candidate-table-draft.jsonl").write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:25:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("buy_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_rolls_back_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = self._write_single_staged_candidate_table(root / "staging")
            formal_data_root = root / "formal-data"
            live_root = formal_data_root / "ashare" / "candidate-table-v0.1"
            live_root.mkdir(parents=True)
            (live_root / "candidate-table.jsonl").write_text('{"old": true}\n', encoding="utf-8")
            (live_root / "manifest.json").write_text('{"manifest_id": "old"}\n', encoding="utf-8")

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:30:00+08:00",
                simulate_failure_step="after_backup",
            )
            old_payload = (live_root / "candidate-table.jsonl").read_text(encoding="utf-8")
            backups = list((formal_data_root / "ashare").glob("candidate-table-v0.1.backup.*"))
            backup_file_exists = bool(backups) and (backups[0] / "candidate-table.jsonl").exists()
            tmp_exists = (formal_data_root / "ashare" / "candidate-table-v0.1.__tmp__").exists()

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_write_failed_after_backup", report["issues"])
        self.assertEqual(old_payload, '{"old": true}\n')
        self.assertEqual(len(backups), 1)
        self.assertTrue(backup_file_exists)
        self.assertFalse(tmp_exists)
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["trading_layer_read_allowed"])

    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_passes_formal_candidate_table(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:10:00+08:00",
            )

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["audit_id"], "candidate_table_trading_layer_readiness_audit_v0.1")
        self.assertEqual(report["candidate_table_trading_layer_readiness_audit_result"], "pass")
        self.assertTrue(report["candidate_table_trading_layer_readiness_checked"])
        self.assertEqual(
            report["candidate_table_trading_layer_readiness_status"],
            "ready_for_trading_layer_read_gate_review",
        )
        self.assertEqual(report["candidate_table_row_count"], 1)
        self.assertTrue(report["candidate_table_update_performed"])
        self.assertEqual(report["candidate_table_update_target"], "formal_data_root")
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(
            report["next_action"],
            "action:write_p5_implementation_plan_for_trading_layer_readiness_audit",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_blocks_missing_manifest_without_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_manifest = root / "formal-data" / "ashare" / "candidate-table-v0.1" / "manifest.json"

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=missing_manifest,
                generated_at="2026-07-01T09:20:00+08:00",
            )

            self.assertFalse((root / "formal-data").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_formal_manifest_missing", report["issues"])
        self.assertFalse(report["candidate_table_trading_layer_readiness_checked"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested_blocks_forbidden_jsonl_field_without_echo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_formal_candidate_table(root)
            table_path = manifest_path.parent / "candidate-table.jsonl"
            rows = [
                json.loads(line)
                for line in table_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            rows[0]["buy_signal"] = True
            table_path.write_text(
                "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
                encoding="utf-8",
            )

            report = audit_trading_layer_readiness_for_candidate_table_when_explicitly_requested(
                formal_candidate_table_manifest_path=manifest_path,
                generated_at="2026-07-01T09:30:00+08:00",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_trading_readiness_forbidden_output_field_present", report["issues"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("buy_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])


