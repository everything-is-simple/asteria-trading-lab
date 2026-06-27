import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sources.tdx_local.audit import audit_local_data_assets
from data_sources.tdx_local.manifest import BLOCKED_LOCATIONS, BLOCKED_PATTERNS, FIELD_MAPPING, SUPPORTING_FACTS


class TdxLocalAuditTest(unittest.TestCase):
    def test_audit_reports_read_only_local_assets_and_no_upload_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "new_tdx64"
            offline_root = root / "tdx_offline_Data"
            duckdb_root = root / "malf-data"

            (tdx_root / "PYPlugins" / "user").mkdir(parents=True)
            (tdx_root / "PYPlugins").mkdir(exist_ok=True)
            (tdx_root / "TdxW.exe").write_text("", encoding="utf-8")
            (tdx_root / "PYPlugins" / "user" / "tqcenter.py").write_text("# tqcenter", encoding="utf-8")
            (tdx_root / "PYPlugins" / "TPyth.dll").write_text("", encoding="utf-8")
            (tdx_root / "PYPlugins" / "TPythClient.dll").write_text("", encoding="utf-8")
            (tdx_root / "TMTconfig.ini").write_text("[PYMP]\nPort=14571\n", encoding="utf-8")

            (offline_root / "stock").mkdir(parents=True)
            (offline_root / "stock-day").mkdir(parents=True)
            (offline_root / "raw").mkdir(parents=True)
            (offline_root / "stock" / "sample.txt").write_text("symbol_name,board_type\n000001.SZ,main\n", encoding="utf-8")
            (offline_root / "stock-day" / "000001.day").write_text("day", encoding="utf-8")
            (offline_root / "raw" / "notes.txt").write_text("raw data note", encoding="utf-8")

            duckdb_root.mkdir(parents=True)
            (duckdb_root / "market_base_day.duckdb").write_bytes(b"duckdb")

            report = audit_local_data_assets(tdx_root, offline_root, duckdb_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["tdx"]["status"], "ready")
        self.assertEqual(report["tdx"]["mode"], "local_python_pymp")
        self.assertTrue(report["tdx"]["required_files"]["TdxW.exe"])
        self.assertTrue(report["tdx"]["required_files"]["PYPlugins/user/tqcenter.py"])
        self.assertEqual(report["offline"]["extension_totals"][".txt"], 2)
        self.assertEqual(report["offline"]["extension_totals"][".day"], 1)
        self.assertEqual(report["duckdb"]["duckdb_file_count"], 1)
        self.assertTrue(report["upload_boundary"]["never_copy_to_repo"])
        self.assertIn("*.day", report["upload_boundary"]["blocked_patterns"])
        self.assertIn("*.txt", report["upload_boundary"]["blocked_patterns"])
        self.assertIn("*.duckdb", report["upload_boundary"]["blocked_patterns"])
        self.assertIn("*.7z", report["upload_boundary"]["blocked_patterns"])
        self.assertEqual(report["source_priority"], ["local_tdx_pymp", "offline_tdx_files", "legacy_duckdb"])
        self.assertEqual(
            list(report["field_mapping"].keys()),
            ["symbol_master", "trading_calendar", "daily_bars", "sector_membership"],
        )
        self.assertEqual(report["field_mapping"], FIELD_MAPPING)
        self.assertEqual(
            report["supporting_facts"],
            {
                "adjustment_metadata": {
                    "source_files": ["raw/*.txt", "market_meta.duckdb"],
                    "target_fields": ["adj_ref", "corporate_action_flag", "source_ref"],
                }
            },
        )
        self.assertEqual(report["supporting_facts"], SUPPORTING_FACTS)
        self.assertEqual(
            report["field_mapping"]["daily_bars"]["source_files"],
            ["stock-day/<ts_code>.day", "stock/<ts_code>.txt"],
        )

    def test_audit_blocks_missing_assets_with_explained_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = audit_local_data_assets(root / "missing-tdx", root / "missing-offline", root / "missing-duckdb")

        self.assertEqual(report["result"], "blocked")
        self.assertEqual(report["next_action"], "action:repair_local_data_assets")
        self.assertIn("missing_tdx_root", report["issues"])
        self.assertIn("missing_offline_root", report["issues"])
        self.assertIn("missing_duckdb_root", report["issues"])
        self.assertFalse(report["tdx"]["ready"])
        self.assertEqual(report["upload_boundary"]["blocked_locations"], BLOCKED_LOCATIONS)
        self.assertEqual(report["upload_boundary"]["blocked_patterns"], BLOCKED_PATTERNS)

    def test_cli_emits_json_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "new_tdx64"
            offline_root = root / "tdx_offline_Data"
            duckdb_root = root / "malf-data"

            (tdx_root / "PYPlugins" / "user").mkdir(parents=True)
            (tdx_root / "TdxW.exe").write_text("", encoding="utf-8")
            (tdx_root / "PYPlugins" / "user" / "tqcenter.py").write_text("# tqcenter", encoding="utf-8")
            (tdx_root / "PYPlugins" / "TPyth.dll").write_text("", encoding="utf-8")
            (tdx_root / "PYPlugins" / "TPythClient.dll").write_text("", encoding="utf-8")
            (tdx_root / "TMTconfig.ini").write_text("[PYMP]\nPort=14571\n", encoding="utf-8")
            (offline_root / "stock-day").mkdir(parents=True)
            (duckdb_root).mkdir(parents=True)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "data_sources.tdx_local.audit",
                    "--tdx-root",
                    str(tdx_root),
                    "--offline-root",
                    str(offline_root),
                    "--duckdb-root",
                    str(duckdb_root),
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
        self.assertEqual(report["tdx"]["port"], 14571)
        self.assertEqual(report["upload_boundary"]["blocked_locations"][0], "Z:\\new_tdx64")


if __name__ == "__main__":
    unittest.main()
