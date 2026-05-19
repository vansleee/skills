---
name: pytest-benchmark-runner
description: >-
  Run pytest selectors repeatedly and summarize pass rate, duration, exit codes, and failure signatures for baseline and after comparison. Use for pytest benchmark runs, flaky test confirmation, 3-run affected-test verification, or the benchmark step in pytest-selenium-test-improvement.
---

# Pytest Benchmark Runner

Use this skill when pytest tests must be run repeatedly with comparable output.

## Command

```bash
python3 /Users/wclee/workspace/skills/pytest-benchmark-runner/scripts/run_pytest_benchmark.py --runs 3 -- <pytest args>
```

Example:

```bash
python3 /Users/wclee/workspace/skills/pytest-benchmark-runner/scripts/run_pytest_benchmark.py --runs 3 -- tests/e2e/test_login.py -q
```

Use `--json` when another script or tracker update needs structured output.

## Rules

- Use the same selector and comparable pytest args for baseline and after runs.
- Do not add retries unless retry behavior is the subject under test.
- Keep raw output available when diagnosing failures.
- Report if the command could not run because dependencies, browsers, or environment are missing.

## Output to Record

- command
- runs passed out of total
- pass rate
- per-run duration and total duration
- exit code per run
- failure signatures
