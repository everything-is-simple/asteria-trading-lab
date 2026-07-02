from __future__ import annotations

import importlib
import unittest


SPLIT_TEST_MODULES = [
    "tests.test_tdx_local_shortlist_reviews",
    "tests.test_tdx_local_front_filter_reviews",
    "tests.test_tdx_local_candidate_table_gates",
    "tests.test_tdx_local_trading_readiness_gates",
    "tests.test_tdx_local_rule_definition_gates",
    "tests.test_tdx_local_shortlist_materialization",
    "tests.test_tdx_local_first_batch_sample_packages",
    "tests.test_tdx_local_rule_definition_write_audit",
]


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for module_name in SPLIT_TEST_MODULES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(module_name)))
    return suite
