import importlib
import unittest


_SPLIT_TEST_MODULES = (
    "tests.test_tachibana_catalogs",
    "tests.test_tachibana_runtime",
    "tests.test_tachibana_gates",
    "tests.test_tachibana_cli",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):
    suite = unittest.TestSuite()
    for module_name in _SPLIT_TEST_MODULES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(module_name)))
    return suite
