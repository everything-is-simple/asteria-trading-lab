from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from data_sources.tdx_local import audit_local_data_assets


class TdxLocalAuditTest(unittest.TestCase):
    def test_audit_reports_missing_paths_as_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = audit_local_data_assets(
                tdx_root=root / "missing-tdx",
                offline_root=root / "missing-offline",
                duckdb_root=root / "missing-duckdb",
            )

        self.assertEqual(report["result"], "blocked")
        self.assertIn("missing_path:tdx_root", report["issues"])
        self.assertIn("missing_path:offline_root", report["issues"])
        self.assertIn("missing_path:duckdb_root", report["issues"])
        self.assertFalse(report["formal_data_write_allowed"])
        self.assertFalse(report["raw_market_file_export_allowed"])

    def test_audit_exposes_four_primary_outputs_and_adjustment_auxiliary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "new_tdx64"
            (tdx_root / "vipdoc" / "sh").mkdir(parents=True)
            (tdx_root / "PYPlugins" / "user").mkdir(parents=True)
            (tdx_root / "PYPlugins" / "user" / "tqcenter.py").write_text("# fixture\n", encoding="utf-8")
            (tdx_root / "TPyth.dll").write_text("fixture", encoding="utf-8")
            (tdx_root / "TPythClient.dll").write_text("fixture", encoding="utf-8")

            offline_root = root / "tdx_offline_Data"
            for name in ["stock", "stock-day", "index-day", "block", "block-day"]:
                (offline_root / name).mkdir(parents=True)
            (offline_root / "stock" / "Non-Adjusted.7z").write_text("fixture", encoding="utf-8")

            duckdb_root = root / "malf-data"
            duckdb_root.mkdir()
            (duckdb_root / "market_base_day.duckdb").write_text("fixture", encoding="utf-8")
            (duckdb_root / "market_meta.duckdb").write_text("fixture", encoding="utf-8")

            report = audit_local_data_assets(tdx_root, offline_root, duckdb_root)

        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["primary_outputs"], [
            "symbol_master",
            "trading_calendar",
            "daily_bars",
            "sector_membership",
        ])
        self.assertEqual(report["auxiliary_outputs"], ["adjustment_metadata"])
        self.assertIn("symbol_master", report["field_mapping"])
        self.assertIn("trading_calendar", report["field_mapping"])
        self.assertIn("daily_bars", report["field_mapping"])
        self.assertIn("sector_membership", report["field_mapping"])
        self.assertIn("adjustment_metadata", report["field_mapping"])
        self.assertEqual(report["source_priority"], [
            "local_tongdaxin_duckdb",
            "baostock_validation",
            "akshare_research_patch",
        ])
        self.assertIn("minimal_read_capability", report)
        self.assertIn("symbol_master", report["minimal_read_capability"])
        self.assertIn("trading_calendar", report["minimal_read_capability"])
        self.assertIn("daily_bars", report["minimal_read_capability"])
        self.assertIn("sector_membership", report["minimal_read_capability"])
        self.assertIn("duckdb_introspection", report)
        self.assertIn("pytdx_reader_probe", report)
        self.assertEqual(report["selected_source_policy"], {
            "symbol_master": "duckdb_first",
            "trading_calendar": "duckdb_first",
            "sector_membership": "duckdb_first",
            "daily_bars": "file_first",
        })

    def test_audit_does_not_export_raw_market_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tdx_root = root / "new_tdx64"
            (tdx_root / "vipdoc").mkdir(parents=True)
            offline_root = root / "tdx_offline_Data"
            (offline_root / "stock").mkdir(parents=True)
            (offline_root / "stock" / "Non-Adjusted.7z").write_text("fixture", encoding="utf-8")
            duckdb_root = root / "malf-data"
            duckdb_root.mkdir()
            (duckdb_root / "raw_market.duckdb").write_text("fixture", encoding="utf-8")

            report = audit_local_data_assets(tdx_root, offline_root, duckdb_root)

        self.assertEqual(report["raw_asset_policy"], "summaries_only")
        self.assertFalse(report["raw_market_file_export_allowed"])
        for asset in report["asset_summary"]["offline"]["large_files"]:
            self.assertIn("path", asset)
            self.assertIn("size_bytes", asset)
            self.assertNotIn("content", asset)
        for asset in report["asset_summary"]["duckdb"]["files"]:
            self.assertIn("path", asset)
            self.assertIn("size_bytes", asset)
            self.assertNotIn("content", asset)


if __name__ == "__main__":
    unittest.main()
