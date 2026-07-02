from tests.tachibana_front_filter_support import *


class TachibanaCliTest(unittest.TestCase):
    def test_cli_audits_qualification_rule_catalog_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-rule-catalog",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["pending_limited_rules"], [])
        self.assertEqual(report["pending_not_meaningful_rules"], [])
        self.assertEqual(report["invalid_rules"], {})

    def test_cli_audits_rhythm_sample_catalog_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-rhythm-samples",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["sample_count"], 18)
        self.assertEqual(report["blocked_sample_count"], 0)
        self.assertEqual(report["missing_rule_ids"], [])
        self.assertEqual(report["missing_rhythm_meanings"], [])
        self.assertEqual(report["undercovered_rhythm_meanings"], {})

    def test_cli_audits_method_pm_actions_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-method-pm-actions",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["missing_method_actions"], [])
        self.assertEqual(report["missing_pm_actions"], [])

    def test_cli_audits_interface_boundary_catalog_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-interface-boundary",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["missing_layers"], [])
        self.assertEqual(report["invalid_layers"], {})

    def test_cli_audits_front_filter_system_without_snapshot(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "tachibana_front_filter",
                "--audit-front-filter-system",
            ],
            cwd=ROOT,
            env={"PYTHONPATH": str(ROOT / "src")},
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["result"], "pass")
        self.assertEqual(report["blocked_audits"], [])
