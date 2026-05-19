---
name: automation-pr-summary
description: >-
  Create structured PR descriptions, commit summaries, or change notes for pytest + Selenium automation test improvements using tracker entries, git diff, and before/after benchmark results. Use after human-reviewed automation test fixes, especially with pytest-selenium-test-improvement.
---

# Automation PR Summary

Create concise, evidence-backed PR text for automation test changes.

## Workflow

1. Read the tracker task, changed files, and before/after benchmark evidence.
2. Use `assets/pr-summary-template.md`.
3. Mention affected tests and whether only a subset was run.
4. Call out reliability improvements such as locator, wait, fixture, isolation, or cleanup changes.
5. State risk and rollback plainly.

## Rules

- Do not overclaim stability beyond the evidence.
- Do not imply product behavior changed when only tests changed.
- Do not say a commit or PR exists unless it actually exists.
- Mention missing verification honestly.

## Output

Keep the result ready to paste into a PR body or commit description.
