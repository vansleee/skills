#!/usr/bin/env python3
"""Run pytest repeatedly and summarize pass rate, durations, and failures."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass


FAILURE_PATTERNS = [
    re.compile(r"^(E\s+.+)$", re.MULTILINE),
    re.compile(r"^(FAILED\s+.+)$", re.MULTILINE),
    re.compile(r"(selenium\.common\.exceptions\.[A-Za-z0-9_]+Exception:.*)"),
    re.compile(r"([A-Za-z0-9_]+Exception: .+)"),
    re.compile(r"(AssertionError:.*)"),
]


@dataclass
class RunResult:
    index: int
    exit_code: int
    duration_seconds: float
    passed: bool
    failure_signatures: list[str]


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest repeatedly and summarize benchmark results."
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of runs.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Pytest arguments after --, for example: -- tests/e2e -q",
    )
    args = parser.parse_args(argv)
    if args.runs < 1:
        parser.error("--runs must be >= 1")
    if args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]
    if not args.pytest_args:
        parser.error("pytest arguments are required after --")
    return args


def extract_failure_signatures(output: str, limit: int = 8) -> list[str]:
    signatures: list[str] = []
    for pattern in FAILURE_PATTERNS:
        for match in pattern.findall(output):
            text = " ".join(str(match).strip().split())
            if text and text not in signatures:
                signatures.append(text)
            if len(signatures) >= limit:
                return signatures
    return signatures


def run_once(pytest_args: list[str], index: int) -> RunResult:
    command = [sys.executable, "-m", "pytest", *pytest_args]
    started = time.monotonic()
    completed = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    duration = time.monotonic() - started
    return RunResult(
        index=index,
        exit_code=completed.returncode,
        duration_seconds=round(duration, 3),
        passed=completed.returncode == 0,
        failure_signatures=extract_failure_signatures(completed.stdout),
    )


def summarize(pytest_args: list[str], results: list[RunResult]) -> dict:
    passed = sum(1 for result in results if result.passed)
    signatures: list[str] = []
    for result in results:
        for signature in result.failure_signatures:
            if signature not in signatures:
                signatures.append(signature)
    return {
        "command": " ".join([sys.executable, "-m", "pytest", *pytest_args]),
        "runs": len(results),
        "passed_runs": passed,
        "pass_rate": passed / len(results),
        "total_duration_seconds": round(
            sum(result.duration_seconds for result in results), 3
        ),
        "results": [asdict(result) for result in results],
        "failure_signatures": signatures,
    }


def render_markdown(summary: dict) -> str:
    lines = [
        "# Pytest Benchmark",
        "",
        f"- Command: `{summary['command']}`",
        f"- Runs: {summary['passed_runs']}/{summary['runs']} passing",
        f"- Pass rate: {summary['pass_rate']:.0%}",
        f"- Total duration: {summary['total_duration_seconds']}s",
        "",
        "## Runs",
    ]
    for result in summary["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        lines.append(
            f"- Run {result['index']}: {status}, exit {result['exit_code']}, "
            f"{result['duration_seconds']}s"
        )
    lines.extend(["", "## Failure Signatures"])
    if summary["failure_signatures"]:
        lines.extend(f"- {signature}" for signature in summary["failure_signatures"])
    else:
        lines.append("- none")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    results = [run_once(args.pytest_args, index) for index in range(1, args.runs + 1)]
    summary = summarize(args.pytest_args, results)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_markdown(summary))
    return 0 if summary["passed_runs"] == summary["runs"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
