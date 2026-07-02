import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = ("src", "scripts", "tests")
MAX_PYTHON_FILE_LINES = 1000


def iter_python_files():
    for root_name in SCAN_ROOTS:
        root = ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            yield path


class SourceFileSizeContractTest(unittest.TestCase):
    def test_python_files_stay_under_1000_lines(self):
        oversized = []
        for path in iter_python_files():
            with path.open("r", encoding="utf-8") as handle:
                line_count = sum(1 for _ in handle)
            if line_count > MAX_PYTHON_FILE_LINES:
                oversized.append((line_count, path.relative_to(ROOT).as_posix()))

        oversized.sort(reverse=True)
        self.assertEqual(
            [],
            oversized,
            "Python files exceed 1000 lines:\n"
            + "\n".join(f"{line_count:5d} {path}" for line_count, path in oversized),
        )


if __name__ == "__main__":
    unittest.main()
