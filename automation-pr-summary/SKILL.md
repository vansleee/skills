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

## Owner Decision Brief

Whenever the summary mentions any ticket or PR, print its full canonical clickable URL (e.g. `https://github.com/OWNER/REPO/pull/123`, `https://jira.example.com/browse/NPLAN-1234`). Never use only a bare number such as `#123` or `NPLAN-1234`.

For every open decision the PR leaves to the reviewer or owner, include:

- what changed and who benefits, in plain language;
- why the decision is needed now;
- completed evidence: baseline/after benchmarks, reruns, CI state, live proof if applicable;
- material tradeoffs and residual risks;
- your recommendation with concise rationale;
- the explicit options available and what each one does.

## Output

Keep the result ready to paste into a PR body or commit description.
