# Test Improvement Tracker

## Backlog

- [ ] T001: Replace brittle login locator
  - Scope: login flow
  - Affected tests: `tests/e2e/test_login.py`
  - Problem: intermittent `NoSuchElementException` on CSS class selector
  - Acceptance criteria: affected tests pass 3/3 locally; locator uses stable attribute
  - Baseline:
    - Command: `pytest tests/e2e/test_login.py -q`
    - Runs: n/a
    - Duration: n/a
    - Failure signatures: n/a
  - After:
    - Command: `pytest tests/e2e/test_login.py -q`
    - Runs: n/a
    - Duration: n/a
    - Failure signatures: n/a
  - Files changed: n/a
  - Risk: low
  - Notes: sample task; replace with real work

## In Progress

## Blocked

## Done
