"""Run the repository's offline tests without requiring pytest."""

import contextlib
import io
import runpy
import sys
import unittest
from pathlib import Path


TEST_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEST_DIR.parent
LIVE_PROVIDER_SCRIPTS = {"test_claude_client.py", "test_fast_confidence.py"}
sys.path.insert(0, str(PROJECT_ROOT))


class CallableTest(unittest.FunctionTestCase):
    """A no-argument pytest-style test run by unittest."""

    def __init__(self, test_func, description):
        super().__init__(self._run_test, description=description)
        self.test_func = test_func
        self.description = description

    def shortDescription(self):
        return self.description

    def _run_test(self):
        # Keep printed prompt examples out of the test report and avoid
        # terminal encoding differences on Windows.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            self.test_func()


def build_suite():
    suite = unittest.TestSuite()
    loader = unittest.defaultTestLoader
    suite.addTests(loader.discover(str(TEST_DIR), pattern="test_*.py"))

    for test_file in sorted(TEST_DIR.glob("test_*.py")):
        if test_file.name in LIVE_PROVIDER_SCRIPTS:
            continue
        namespace = runpy.run_path(str(test_file))
        for name, value in sorted(namespace.items()):
            if name.startswith("test_") and callable(value):
                suite.addTest(CallableTest(value, f"{test_file.name}::{name}"))
    return suite


if __name__ == "__main__":
    result = unittest.TextTestRunner(verbosity=2).run(build_suite())
    raise SystemExit(0 if result.wasSuccessful() else 1)
