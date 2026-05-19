---
name: selenium-best-practices-review
description: >-
  Review pytest + Selenium automation test code for reliability, maintainability, and flakiness risks. Use when reviewing Selenium tests, page objects, fixtures, waits, locators, retries, sleeps, browser/session isolation, test data setup, or automation-test pull requests.
---

# Selenium Best Practices Review

Review Selenium automation code with a test-reliability lens.

## Workflow

1. Inspect the relevant tests, page objects, fixtures, and helper wrappers.
2. Read `references/review-checklist.md`.
3. Prioritize findings that can cause false green, false red, flakiness, or hidden product regressions.
4. Lead with findings ordered by severity.
5. Recommend the smallest safe fix and verification command.

## Finding Priorities

- P1: can hide product regressions, create false green, or break a large suite
- P2: likely flake or repeated maintenance cost
- P3: readability or local maintainability issue

## Guardrails

- Do not request broad rewrites when a targeted fix is enough.
- Do not flag style-only issues unless they affect reliability.
- Do not suggest sleeps, skips, or broad retries as the primary fix.
- Mention when a review needs runtime evidence from `pytest-benchmark-runner`.

## Output

```markdown
## Findings
- [P1] <file:line> <issue and impact>

## Suggested Fix
<smallest safe change>

## Verification
<pytest command or benchmark recommendation>
```
