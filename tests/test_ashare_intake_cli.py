import importlib
import unittest


_SPLIT_TEST_MODULES = (
    "tests.test_ashare_first_batch_cli",
    "tests.test_ashare_execution_cli",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str | None):
    suite = unittest.TestSuite()
    for module_name in _SPLIT_TEST_MODULES:
        suite.addTests(loader.loadTestsFromModule(importlib.import_module(module_name)))
    return suite
