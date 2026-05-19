import unittest

from scripts.run_pytest_benchmark import (
    RunResult,
    extract_failure_signatures,
    parse_args,
    summarize,
)


class ParseArgsTests(unittest.TestCase):
    def test_accepts_pytest_args_after_separator(self):
        args = parse_args(["--runs", "2", "--", "tests/e2e/test_login.py", "-q"])

        self.assertEqual(args.runs, 2)
        self.assertEqual(args.pytest_args, ["tests/e2e/test_login.py", "-q"])

    def test_requires_pytest_args(self):
        with self.assertRaises(SystemExit):
            parse_args(["--runs", "2"])


class FailureSignatureTests(unittest.TestCase):
    def test_extracts_common_failure_signatures(self):
        output = """
E   selenium.common.exceptions.TimeoutException: Message: timeout
FAILED tests/e2e/test_login.py::test_login - AssertionError: nope
AssertionError: nope
"""

        signatures = extract_failure_signatures(output)

        self.assertIn(
            "E selenium.common.exceptions.TimeoutException: Message: timeout",
            signatures,
        )
        self.assertIn(
            "FAILED tests/e2e/test_login.py::test_login - AssertionError: nope",
            signatures,
        )


class SummaryTests(unittest.TestCase):
    def test_computes_pass_rate_and_deduped_signatures(self):
        summary = summarize(
            ["tests/e2e", "-q"],
            [
                RunResult(1, 0, 1.0, True, []),
                RunResult(2, 1, 1.0, False, ["AssertionError: nope"]),
                RunResult(3, 1, 1.0, False, ["AssertionError: nope"]),
            ],
        )

        self.assertEqual(summary["passed_runs"], 1)
        self.assertEqual(summary["runs"], 3)
        self.assertAlmostEqual(summary["pass_rate"], 1 / 3)
        self.assertEqual(summary["failure_signatures"], ["AssertionError: nope"])


if __name__ == "__main__":
    unittest.main()
