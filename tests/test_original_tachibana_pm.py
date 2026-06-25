import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from original_tachibana.performance import run_performance
from original_tachibana.major_trades import build_major_trades
from original_tachibana.quant_report import build_quant_report
from original_tachibana.audit_source_data import audit_files
from original_tachibana.pm_state import parse_inventory, run_backtest
from original_tachibana.single_trade_runner import run_single_trade


DATA_DIR = ROOT / "data" / "pioneer-1975-1976" / "json"
SOURCE_DIR = ROOT / "data" / "pioneer-1975-1976" / "source-images"


class ParseInventoryTest(unittest.TestCase):
    def test_single_and_dual_inventory_formats(self) -> None:
        self.assertEqual(parse_inventory("40 —").gross_short, 40)
        self.assertEqual(parse_inventory("—26").gross_long, 26)
        self.assertEqual(parse_inventory("— 10").gross_long, 10)
        dual = parse_inventory("2 — 20")
        self.assertEqual((dual.gross_short, dual.gross_long), (2, 20))
        flat = parse_inventory("0")
        self.assertEqual((flat.gross_long, flat.gross_short), (0, 0))


class MinimalBacktestTest(unittest.TestCase):
    def test_strong_samples_generate_required_pm_events(self) -> None:
        files = [
            DATA_DIR / "1976-03.json",
            DATA_DIR / "1976-04.json",
            DATA_DIR / "1976-05.json",
            DATA_DIR / "1976-10.json",
            DATA_DIR / "1976-11.json",
            DATA_DIR / "1976-12.json",
        ]
        daily_rows, summary = run_backtest(files)
        by_date = {row["date_key"]: row for row in daily_rows}

        self.assertTrue(by_date["1976-03-24"]["reset_after_clear"])
        self.assertEqual(by_date["1976-04-05"]["pm_action"], "lock_candidate")
        self.assertEqual(by_date["1976-05-10"]["pm_action"], "unlock")
        self.assertEqual(by_date["1976-11-09"]["decision_basis_date"], "1976-11-08")
        self.assertEqual(by_date["1976-11-09"]["execution_timing"], "pre_open_market_order")
        self.assertFalse(by_date["1976-11-09"]["same_day_close_available_at_order"])
        self.assertEqual(by_date["1976-11-13"]["pm_action"], "clear")
        self.assertTrue(by_date["1976-11-13"]["reset_after_clear"])
        self.assertTrue(by_date["1976-11-09"]["scale_alert"])
        self.assertTrue(by_date["1976-12-13"]["scale_alert"])
        self.assertEqual(by_date["1976-12-24"]["pm_action"], "clear")

        event_actions = [event["pm_action"] for event in summary["pm_event_log"]]
        self.assertIn("add_on", event_actions)
        self.assertIn("lock_candidate", event_actions)
        self.assertIn("unlock", event_actions)
        self.assertIn("clear", event_actions)

        strong_samples = summary["strong_sample_report"]
        self.assertTrue(all(sample["passed"] for sample in strong_samples))
        flip_sample = next(
            sample for sample in strong_samples if sample["sample"] == "1976-11 probe_clear_probe_flip_candidate"
        )
        self.assertIn("reversal_flip_final_confirmation", flip_sample["manual_review_required"])

    def test_performance_metrics_are_reproducible_for_full_sample(self) -> None:
        files = sorted(DATA_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json"))
        equity_rows, metrics = run_performance(files)

        self.assertEqual(len(equity_rows), 729)
        self.assertEqual(metrics["coverage"]["segments"], 15)
        self.assertAlmostEqual(metrics["performance"]["total_pnl"], 80187.0)
        self.assertAlmostEqual(metrics["performance"]["sharpe"], 1.06669959543025)
        self.assertAlmostEqual(metrics["trade_statistics"]["win_rate"], 2 / 3)
        self.assertAlmostEqual(metrics["trade_statistics"]["expectancy_per_trade"], 5345.8)
        self.assertEqual(metrics["trade_statistics"]["best_trade"]["segment_id"], "S013")
        self.assertAlmostEqual(metrics["trade_statistics"]["best_trade"]["pnl"], 41140.0)
        self.assertIn("1976-09-21", metrics["assumptions"]["shares_per_hand_note"])

    def test_major_trade_report_keeps_1976_11_trade_direction_correct(self) -> None:
        files = sorted(DATA_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json"))
        equity_rows, metrics = run_performance(files)
        report = build_major_trades(equity_rows, metrics)
        by_id = {row["major_trade_id"]: row for row in report["major_trades"]}
        november_trade = by_id["S013"]

        self.assertEqual(len(report["coverage"]["source_months"]), 24)
        self.assertEqual(report["coverage"]["daily_rows"], 729)
        self.assertEqual(report["coverage"]["trade_rows"], 159)
        self.assertEqual(report["coverage"]["missing_trade_price_on_trade_rows"], 0)
        self.assertEqual(report["coverage"]["missing_position_on_trade_rows"], 0)
        self.assertEqual(report["summary"]["major_trade_count"], 15)
        self.assertEqual(november_trade["direction"], "long")
        self.assertEqual(november_trade["max_gross_long"], 200)
        self.assertEqual(november_trade["max_gross_short"], 0)
        self.assertIn("—102", november_trade["entry_trade_sequence"])
        self.assertEqual(november_trade["exit_trade_sequence"], "200 —")
        self.assertAlmostEqual(november_trade["pnl"], 41140.0)
        self.assertEqual(report["summary"]["best_major_trade"]["major_trade_id"], "S013")
        self.assertEqual(november_trade["trade_ledger"][0]["trade_price"], 2250)
        self.assertEqual(november_trade["trade_ledger"][0]["operations"][0]["operation"], "buy_long")
        self.assertEqual(november_trade["trade_ledger"][0]["operations"][0]["quantity"], 10)
        self.assertEqual(november_trade["trade_ledger"][-2]["trade_raw"], "—102")
        self.assertEqual(november_trade["trade_ledger"][-2]["operations"][0]["quantity"], 102)
        self.assertEqual(november_trade["trade_ledger"][-1]["trade_raw"], "200 —")
        self.assertEqual(november_trade["trade_ledger"][-1]["operations"][0]["operation"], "sell_long")
        self.assertEqual(november_trade["trade_ledger"][-1]["operations"][0]["quantity"], 200)
        self.assertAlmostEqual(november_trade["trade_ledger"][-1]["cumulative_realized_pnl"], 41140.0)

    def test_quant_report_metrics_are_reproducible_for_major_trades(self) -> None:
        files = sorted(DATA_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].json"))
        equity_rows, metrics = run_performance(files)
        report = build_quant_report(equity_rows, metrics)
        stats = report["trade_statistics"]

        self.assertEqual(report["coverage"]["major_trade_count"], 15)
        self.assertEqual(stats["winning_trades"], 10)
        self.assertEqual(stats["losing_trades"], 5)
        self.assertAlmostEqual(stats["win_rate"], 2 / 3)
        self.assertAlmostEqual(stats["total_pnl"], 80187.0)
        self.assertAlmostEqual(stats["gross_profit"], 85737.0)
        self.assertAlmostEqual(stats["gross_loss"], -5550.0)
        self.assertAlmostEqual(stats["payoff_ratio"], 7.724054054054055)
        self.assertAlmostEqual(stats["profit_factor"], 15.448108108108108)
        self.assertAlmostEqual(stats["expectancy_per_trade"], 5345.8)
        self.assertEqual(stats["best_trade"]["major_trade_id"], "S013")
        self.assertEqual(stats["worst_trade"]["major_trade_id"], "S015")
        self.assertAlmostEqual(report["account_performance"]["sharpe"], 1.06669959543025)

    def test_source_data_audit_covers_json_and_images(self) -> None:
        report = audit_files(DATA_DIR, SOURCE_DIR)

        self.assertEqual(report["summary"]["json_months"], 24)
        self.assertEqual(report["summary"]["source_images"], 24)
        self.assertEqual(report["summary"]["daily_rows"], 729)
        self.assertEqual(report["summary"]["trade_rows"], 159)
        self.assertEqual(report["summary"]["error_count"], 0)
        self.assertEqual(report["summary"]["warning_count"], 0)
        self.assertEqual(report["issues"], [])

    def test_single_trade_entrypoints_exist_and_replay_s013(self) -> None:
        entry_dir = ROOT / "src" / "original_tachibana" / "single_trades"
        entrypoints = sorted(entry_dir.glob("trade_s[0-9][0-9][0-9].py"))

        self.assertEqual(len(entrypoints), 15)
        self.assertTrue((entry_dir / "trade_s001.py").exists())
        self.assertTrue((entry_dir / "trade_s015.py").exists())

        out_dir = ROOT / "data" / "pioneer-1975-1976" / "backtest-v0.1" / "test-single-trades"
        report_dir = ROOT / "docs" / "backtest-spec" / "test-single-trades"
        trade = run_single_trade("S013", DATA_DIR, out_dir, report_dir)

        self.assertEqual(trade["major_trade_id"], "S013")
        self.assertEqual(trade["trade_ledger"][-1]["trade_raw"], "200 —")
        self.assertAlmostEqual(trade["trade_ledger"][-1]["cumulative_realized_pnl"], 41140.0)
        self.assertTrue((report_dir / "S013.md").exists())

    def test_part4_annotations_capture_lock_purpose_and_unit_policy(self) -> None:
        path = ROOT / "data" / "pioneer-1975-1976" / "annotations" / "part4-pm-annotations-v0.1.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        by_id = {item["major_trade_id"]: item for item in payload["major_trade_annotations"]}

        self.assertTrue(payload["unit_policy"]["date_dependent_share_multiplier"])
        self.assertEqual(payload["unit_policy"]["events"][0]["date"], "1976-09-21")
        self.assertIn("mother_position_protection", by_id["S001"]["lock_purpose"])
        self.assertIn("reverse_probe", by_id["S008"]["lock_purpose"])
        self.assertEqual(by_id["S013"]["unit_context"], "post_1976_09_21_100_share_unit_experiment")
        self.assertIn("over_frequent_averaging", by_id["S015"]["risk_tags"])


if __name__ == "__main__":
    unittest.main()
