from __future__ import annotations

import importlib
import unittest


SPLIT_TEST_MODULES = [
    "tests.test_tdx_local_rule_definition_persistence_package",
    "tests.test_tdx_local_shortlist_research_bundle",
    "tests.test_tdx_local_first_batch_sample_package_builders",
]


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for module_name in SPLIT_TEST_MODULES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(module_name)))
    return suite
