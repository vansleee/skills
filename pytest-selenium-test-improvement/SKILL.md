---
name: pytest-selenium-test-improvement
description: >-
  Improve pytest + Selenium automation tests with a measured, human-in-the-loop workflow inspired by pw-test-improvement. Use this skill when fixing flaky, failing, brittle, slow, or hard-to-maintain Selenium tests; when a user mentions pytest baseline runs, affected tests, TEST_IMPROVEMENT_TRACKER.md, before/after benchmarks, Selenium locator or wait problems, or wants an agent to repair automation tests without skipping failures or weakening assertions.
---

# Pytest Selenium Test Improvement

Improve one automation-test task at a time with evidence before and after the change.

## Workflow

### 1. Identify the task

Find `TEST_IMPROVEMENT_TRACKER.md`. If it does not exist, use `assets/tracker-template.md` as the starting structure and ask before creating it unless the user already asked you to implement tracker work.

Choose exactly one unfinished item unless the user names a task. Identify the affected pytest selectors before editing.

### 2. Run the baseline

Run the affected tests 3 times before changing code.

Prefer:

```bash
python3 /Users/wclee/workspace/skills/pytest-benchmark-runner/scripts/run_pytest_benchmark.py --runs 3 -- <pytest args>
```

Record the command, pass rate, duration, exit codes, and failure signatures in the tracker.

### 3. Diagnose before fixing

If the failure mode is unclear, use `pytest-selenium-failure-analysis`. Read `references/pytest-selenium-guidelines.md` before making Selenium-specific changes.

### 4. Apply the smallest safe fix

Fix the test architecture or test code with the narrowest change that addresses the evidence. Prefer stable locators, explicit waits, reliable fixtures, and meaningful assertions.

Do not modify product code, CI pipelines, release gates, or commit history unless the user explicitly asks.

### 5. Re-run the same tests

Run the same affected tests 3 times after the change with the same selector and comparable pytest arguments.

If failures remain, classify them as same failure, new regression, environmental issue, or unrelated cascade.

### 6. Compare results

Summarize before/after pass rate, duration, failure signatures, and files changed. Mention tradeoffs such as increased wait specificity or slightly longer duration.

### 7. Update tracker and summary

Update `TEST_IMPROVEMENT_TRACKER.md` with baseline, after results, changed files, status, risk, and notes. Mark done only when the acceptance criteria pass.

If asked for PR text, use `assets/pr-summary-template.md` or the `automation-pr-summary` skill. Do not commit unless the user explicitly asks.

## Guardrails

- Do not skip tests to create a green result.
- Do not weaken assertions or replace them with smoke checks.
- Do not hide timing failures with broad sleeps or global timeout increases.
- Do not add broad retries as the first fix.
- Preserve isolation; avoid shared mutable browser state between tests.
- Keep raw evidence available when failures are ambiguous.

## Resources

- `references/pytest-selenium-guidelines.md` for locator, wait, fixture, and assertion guidance.
- `assets/tracker-template.md` for tracker structure.
- `assets/pr-summary-template.md` for final PR descriptions.
- `evals/evals.json` for what good usage of this skill should satisfy.
