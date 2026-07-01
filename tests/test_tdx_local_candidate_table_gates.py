from __future__ import annotations

from tests.tdx_local_first_batch_support import *


class TdxLocalCandidateTableGatesTest(TdxLocalFirstBatchSupport):
    def test_prepare_candidate_table_update_audit_when_explicitly_requested_holds_bad_or_forbidden_packages(self) -> None:
        persistence_report = {
            "result": "blocked",
            "research_only": True,
            "package_id": "formal_qualification_record_persistence_package_v0.1",
            "qualification_record_persistence_package_prepared": True,
            "qualification_record_persistence_packages": [
                {
                    "qualification_record_status": "draft_only",
                    "qualification_record_id": "ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "603687.SH",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                },
                {
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "000899.SZ",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "trade_accept": True,
                },
            ],
        }

        report = prepare_candidate_table_update_audit_when_explicitly_requested(
            persistence_report,
            generated_at="2026-06-30T19:35:00+08:00",
        )

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["candidate_table_update_audit_result"], "blocked")
        self.assertFalse(report["candidate_table_update_package_prepared"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertEqual(report["candidate_table_update_audit_candidate_count"], 0)
        self.assertEqual(report["held_candidate_table_update_audit_count"], 2)
        self.assertEqual(report["next_action"], "action:repair_candidate_table_update_audit_inputs")
        by_id = {item["qualification_record_id"]: item for item in report["held_candidate_table_update_audit_items"]}
        self.assertEqual(
            by_id["ASHARE-QUAL-603687.SH-2026-04-23-2026-06-29-v0.1"]["candidate_table_update_audit_reason"],
            "qualification_record_not_ready_for_persistence",
        )
        self.assertEqual(
            by_id["ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1"]["candidate_table_update_audit_reason"],
            "candidate_table_update_forbidden_output_field_present",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("candidate_table_update_audit_allowed", payload)
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_qualification_records_to_staging_when_explicitly_requested_writes_records_then_manifest(self) -> None:
        audit_report = {
            "result": "pass",
            "research_only": True,
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "pass",
            "candidate_table_update_package_prepared": True,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "trading_layer_read_allowed": False,
            "candidate_table_update_audit_packages": [
                {
                    "candidate_table_update_audit_result": "pass",
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
                    "ashare_sample_id": "ASHARE-ADDON-600310-20260605",
                    "ts_code": "600310.SH",
                    "symbol_name": "桂东电力",
                    "sample_window_start": "2026-04-23",
                    "sample_window_end": "2026-06-29",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "rhythm_meaning": "limited",
                    "tachibana_applicability": "conditional",
                    "source_qualification_record_persistence_performed": False,
                    "candidate_table_update_package_prepared": True,
                    "candidate_table_update_performed": False,
                    "candidate_table_update_allowed": False,
                    "trading_layer_read_allowed": False,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            staging_root = Path(tmp) / "staging"
            report = write_qualification_records_to_staging_when_explicitly_requested(
                audit_report,
                staging_root=staging_root,
                generated_at="2026-06-30T21:00:00+08:00",
            )
            manifest_path = staging_root / "qualification-records-v0.1" / "manifest.json"
            record_path = (
                staging_root
                / "qualification-records-v0.1"
                / "records"
                / "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1.json"
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = json.loads(record_path.read_text(encoding="utf-8"))
            tmp_files = list((staging_root / "qualification-records-v0.1").rglob("*.tmp"))

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["qualification_record_persistence_performed"])
        self.assertEqual(report["qualification_record_persistence_target"], "staging")
        self.assertEqual(report["qualification_record_staging_count"], 1)
        self.assertEqual(report["held_qualification_record_staging_count"], 0)
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:hold_for_candidate_table_update_staging_review")
        self.assertEqual(manifest["manifest_id"], "qualification_record_staging_manifest_v0.1")
        self.assertEqual(manifest["source_audit_id"], "candidate_table_update_audit_package_v0.1")
        self.assertEqual(manifest["qualification_record_count"], 1)
        self.assertEqual(
            manifest["record_files"],
            ["records/ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1.json"],
        )
        self.assertTrue(manifest["qualification_record_persistence_performed"])
        self.assertEqual(manifest["qualification_record_persistence_target"], "staging")
        self.assertFalse(manifest["candidate_table_update_performed"])
        self.assertFalse(manifest["candidate_table_update_allowed"])
        self.assertFalse(manifest["trading_layer_read_allowed"])
        self.assertFalse(manifest["signal_generation_allowed"])
        self.assertFalse(manifest["backtest_execution_allowed"])
        self.assertEqual(record["qualification_record_status"], "formal_record_persisted_to_staging")
        self.assertEqual(
            record["qualification_record_id"],
            "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
        )
        self.assertEqual(record["qualification_record_persisted_at"], "2026-06-30T21:00:00+08:00")
        self.assertFalse(record["candidate_table_update_performed"])
        self.assertFalse(record["candidate_table_update_allowed"])
        self.assertFalse(record["trading_layer_read_allowed"])
        self.assertFalse(tmp_files)
        payload = json.dumps({"report": report, "manifest": manifest, "record": record}, ensure_ascii=False)
        self.assertNotIn("action:update_candidate_table", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_qualification_records_to_staging_when_explicitly_requested_blocks_bad_audit_report(self) -> None:
        audit_report = {
            "result": "blocked",
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "blocked",
            "candidate_table_update_package_prepared": False,
            "candidate_table_update_performed": False,
            "candidate_table_update_audit_packages": [],
        }

        with tempfile.TemporaryDirectory() as tmp:
            staging_root = Path(tmp) / "staging"
            report = write_qualification_records_to_staging_when_explicitly_requested(
                audit_report,
                staging_root=staging_root,
                generated_at="2026-06-30T21:05:00+08:00",
            )
            self.assertFalse(staging_root.exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["qualification_record_persistence_performed"])
        self.assertIn("candidate_table_update_audit_not_pass", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_write_qualification_records_to_staging_when_explicitly_requested_blocks_forbidden_fields_without_files(self) -> None:
        audit_report = {
            "result": "pass",
            "audit_id": "candidate_table_update_audit_package_v0.1",
            "candidate_table_update_audit_result": "pass",
            "candidate_table_update_package_prepared": True,
            "candidate_table_update_performed": False,
            "candidate_table_update_allowed": False,
            "candidate_table_update_audit_packages": [
                {
                    "candidate_table_update_audit_result": "pass",
                    "qualification_record_status": "formal_record_ready_for_persistence",
                    "qualification_record_id": "ASHARE-QUAL-000899.SZ-2026-04-23-2026-06-29-v0.1",
                    "ts_code": "000899.SZ",
                    "qualification_rule_id": "Q-PRESSURE-ADJUST",
                    "candidate_table_update_package_prepared": True,
                    "candidate_table_update_performed": False,
                    "trade_accept": True,
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmp:
            staging_root = Path(tmp) / "staging"
            report = write_qualification_records_to_staging_when_explicitly_requested(
                audit_report,
                staging_root=staging_root,
                generated_at="2026-06-30T21:10:00+08:00",
            )
            self.assertFalse(staging_root.exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["qualification_record_persistence_performed"])
        self.assertEqual(report["held_qualification_record_staging_count"], 1)
        self.assertEqual(
            report["held_qualification_record_staging_items"][0]["qualification_record_persistence_reason"],
            "qualification_record_staging_forbidden_output_field_present",
        )
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("trade_accept", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_writes_jsonl_and_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_staged_qualification_record(root / "qualification-staging")
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:00:00+08:00",
            )
            table_root = candidate_staging_root / "candidate-table-v0.1"
            manifest = json.loads((table_root / "manifest.json").read_text(encoding="utf-8"))
            rows = [
                json.loads(line)
                for line in (table_root / "candidate-table-draft.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            tmp_dirs = list(candidate_staging_root.glob("candidate-table-v0.1.__tmp__"))

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["candidate_table_update_performed"])
        self.assertEqual(report["candidate_table_update_target"], "staging")
        self.assertEqual(report["candidate_table_row_count"], 1)
        self.assertEqual(report["candidate_table_deduplicated_existing_row_count"], 0)
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["institution_rule_definition_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_staged_candidate_table_before_formal_data_root_write")
        self.assertEqual(manifest["manifest_id"], "candidate_table_staging_manifest_v0.1")
        self.assertEqual(manifest["source_qualification_record_manifest_id"], "qualification_record_staging_manifest_v0.1")
        self.assertEqual(manifest["candidate_table_row_count"], 1)
        self.assertEqual(manifest["candidate_table_files"], ["candidate-table-draft.jsonl"])
        self.assertTrue(manifest["candidate_table_update_performed"])
        self.assertEqual(manifest["candidate_table_update_target"], "staging")
        self.assertFalse(manifest["candidate_table_update_allowed"])
        self.assertFalse(manifest["trading_layer_read_allowed"])
        self.assertFalse(manifest["signal_generation_allowed"])
        self.assertFalse(manifest["backtest_execution_allowed"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0]["candidate_table_row_id"],
            "CANDIDATE-TABLE-ROW::ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1",
        )
        self.assertEqual(rows[0]["candidate_table_row_status"], "staged_candidate_table_row")
        self.assertEqual(rows[0]["qualification_record_id"], "ASHARE-QUAL-600310.SH-2026-04-23-2026-06-29-v0.1")
        self.assertEqual(rows[0]["candidate_table_updated_at"], "2026-06-30T22:00:00+08:00")
        self.assertTrue(rows[0]["candidate_table_update_performed"])
        self.assertEqual(rows[0]["candidate_table_update_target"], "staging")
        self.assertFalse(rows[0]["candidate_table_update_allowed"])
        self.assertFalse(rows[0]["trading_layer_read_allowed"])
        self.assertFalse(rows[0]["signal_generation_allowed"])
        self.assertFalse(rows[0]["backtest_execution_allowed"])
        self.assertFalse(tmp_dirs)
        payload = json.dumps({"report": report, "manifest": manifest, "rows": rows}, ensure_ascii=False)
        self.assertNotIn("action:read_trading_layer", payload)
        self.assertNotIn("action:generate_signal", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_bad_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = root / "qualification-staging" / "qualification-records-v0.1" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "manifest_id": "bad_manifest",
                        "qualification_record_persistence_performed": True,
                        "qualification_record_persistence_target": "staging",
                        "candidate_table_update_performed": False,
                        "candidate_table_update_allowed": False,
                        "record_files": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:05:00+08:00",
            )

            self.assertFalse((candidate_staging_root / "candidate-table-v0.1").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertIn("qualification_record_staging_manifest_invalid", report["issues"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_forbidden_record_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qualification_root = root / "qualification-staging"
            manifest_path = self._write_single_staged_qualification_record(qualification_root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record_path = qualification_root / "qualification-records-v0.1" / manifest["record_files"][0]
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["trade_accept"] = True
            record_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:10:00+08:00",
            )

            self.assertFalse((candidate_staging_root / "candidate-table-v0.1").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertEqual(report["held_candidate_table_update_count"], 1)
        self.assertEqual(
            report["held_candidate_table_update_items"][0]["candidate_table_update_reason"],
            "candidate_table_forbidden_output_field_present",
        )
        payload = json.dumps(report, ensure_ascii=False)
        self.assertNotIn("trade_accept", payload)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_duplicate_record_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            qualification_root = root / "qualification-staging"
            manifest_path = self._write_single_staged_qualification_record(qualification_root)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            source_record = qualification_root / "qualification-records-v0.1" / manifest["record_files"][0]
            duplicate_record = qualification_root / "qualification-records-v0.1" / "records" / "duplicate.json"
            duplicate_record.write_text(source_record.read_text(encoding="utf-8"), encoding="utf-8")
            manifest["record_files"].append("records/duplicate.json")
            manifest["qualification_record_count"] = 2
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            candidate_staging_root = root / "candidate-staging"

            report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:15:00+08:00",
            )

            self.assertFalse((candidate_staging_root / "candidate-table-v0.1").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertIn("candidate_table_duplicate_qualification_record_id", report["issues"])
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_rewrites_idempotently_without_tmp_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_staged_qualification_record(root / "qualification-staging")
            candidate_staging_root = root / "candidate-staging"

            first_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:20:00+08:00",
            )
            second_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:25:00+08:00",
            )
            table_root = candidate_staging_root / "candidate-table-v0.1"
            manifest = json.loads((table_root / "manifest.json").read_text(encoding="utf-8"))
            tmp_dirs = list(candidate_staging_root.glob("candidate-table-v0.1.__tmp__"))
            table_root_exists = table_root.exists()

        self.assertEqual(first_report["result"], "pass")
        self.assertEqual(second_report["result"], "pass")
        self.assertTrue(table_root_exists)
        self.assertEqual(manifest["candidate_table_row_count"], 1)
        self.assertFalse(tmp_dirs)

    def test_update_candidate_table_from_staged_qualification_records_when_explicitly_requested_blocks_existing_row_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest_path = self._write_single_staged_qualification_record(root / "qualification-staging")
            candidate_staging_root = root / "candidate-staging"

            first_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:30:00+08:00",
            )
            table_root = candidate_staging_root / "candidate-table-v0.1"
            table_file = table_root / "candidate-table-draft.jsonl"
            rows = [json.loads(line) for line in table_file.read_text(encoding="utf-8").splitlines() if line.strip()]
            rows[0]["qualification_rule_id"] = "Q-CONFLICT"
            table_file.write_text(json.dumps(rows[0], ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

            second_report = update_candidate_table_from_staged_qualification_records_when_explicitly_requested(
                qualification_record_staging_manifest_path=manifest_path,
                candidate_table_staging_root=candidate_staging_root,
                generated_at="2026-06-30T22:35:00+08:00",
            )
            rows_after = [
                json.loads(line)
                for line in table_file.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]

        self.assertEqual(first_report["result"], "pass")
        self.assertEqual(second_report["result"], "blocked")
        self.assertFalse(second_report["candidate_table_update_performed"])
        self.assertIn("candidate_table_merge_conflict", second_report["issues"])
        self.assertEqual(rows_after[0]["qualification_rule_id"], "Q-CONFLICT")

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_writes_formal_jsonl_with_backup(self) -> None:
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
                generated_at="2026-06-30T23:10:00+08:00",
            )
            manifest = json.loads((live_root / "manifest.json").read_text(encoding="utf-8"))
            rows = [
                json.loads(line)
                for line in (live_root / "candidate-table.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            backups = list((formal_data_root / "ashare").glob("candidate-table-v0.1.backup.*"))
            backup_file_exists = bool(backups) and (backups[0] / "candidate-table.jsonl").exists()
            tmp_exists = (formal_data_root / "ashare" / "candidate-table-v0.1.__tmp__").exists()

        self.assertEqual(report["result"], "pass")
        self.assertTrue(report["candidate_table_update_performed"])
        self.assertEqual(report["candidate_table_update_target"], "formal_data_root")
        self.assertFalse(report["candidate_table_update_allowed"])
        self.assertFalse(report["trading_layer_read_allowed"])
        self.assertFalse(report["signal_generation_allowed"])
        self.assertFalse(report["backtest_execution_allowed"])
        self.assertEqual(report["next_action"], "action:review_formal_candidate_table_before_trading_layer_audit")
        self.assertEqual(manifest["manifest_id"], "candidate_table_formal_manifest_v0.1")
        self.assertEqual(manifest["candidate_table_row_count"], 1)
        self.assertEqual(manifest["candidate_table_file"], "candidate-table.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["candidate_table_update_target"], "formal_data_root")
        self.assertTrue(rows[0]["candidate_table_update_performed"])
        self.assertFalse(rows[0]["trading_layer_read_allowed"])
        self.assertEqual(len(backups), 1)
        self.assertTrue(backup_file_exists)
        self.assertFalse(tmp_exists)
        payload = json.dumps({"report": report, "manifest": manifest, "rows": rows}, ensure_ascii=False)
        self.assertFalse(any(field in payload for field in FORBIDDEN_FIELDS))

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_without_confirm_before_reading_staging(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_manifest = root / "missing" / "manifest.json"
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=missing_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=False,
                generated_at="2026-06-30T23:15:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("confirm_formal_write_required", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])
        self.assertFalse(report["trading_layer_read_allowed"])

    def test_write_candidate_table_to_formal_data_root_when_explicitly_confirmed_blocks_bad_manifest_without_backup(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            staging_manifest = root / "candidate-staging" / "candidate-table-v0.1" / "manifest.json"
            staging_manifest.parent.mkdir(parents=True)
            staging_manifest.write_text(json.dumps({"manifest_id": "bad"}, ensure_ascii=False), encoding="utf-8")
            formal_data_root = root / "formal-data"

            report = write_candidate_table_to_formal_data_root_when_explicitly_confirmed(
                candidate_table_staging_manifest_path=staging_manifest,
                formal_data_root=formal_data_root,
                confirm_formal_write=True,
                generated_at="2026-06-30T23:20:00+08:00",
            )

            self.assertFalse((formal_data_root / "ashare").exists())

        self.assertEqual(report["result"], "blocked")
        self.assertIn("candidate_table_staging_manifest_invalid", report["issues"])
        self.assertFalse(report["candidate_table_update_performed"])


