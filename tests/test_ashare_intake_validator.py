import importlib
import unittest


_SPLIT_TEST_MODULES = (
    "tests.test_ashare_first_batch_pipeline",
    "tests.test_ashare_intake_cli",
    "tests.test_ashare_intake_contracts",
    "tests.test_ashare_execution_constraint_gates",
    "tests.test_ashare_execution_feasibility_pipeline",
    "tests.test_ashare_execution_policy_candidates",
    "tests.test_ashare_execution_policy_review_archive",
    "tests.test_ashare_execution_policy_research",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):
    suite = unittest.TestSuite()
    for module_name in _SPLIT_TEST_MODULES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(module_name)))
    return suite
