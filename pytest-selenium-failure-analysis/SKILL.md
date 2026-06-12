---
name: pytest-selenium-failure-analysis
description: >-
  Analyze pytest + Selenium failures from pytest output, stack traces, Selenium exceptions, screenshots, browser logs, CI logs, reruns, or flaky-test evidence. Use when a user asks why Selenium tests failed, whether a failure is flaky, what root cause is likely, or what evidence-backed next step should happen before fixing automation tests.
---

# Pytest Selenium Failure Analysis

Diagnose failures before changing tests.

## Workflow

### 1. Collect evidence

Gather the pytest command, failing node IDs, full failure output, Selenium exception type and message, screenshot/video/HTML dump paths, browser console logs, CI logs, and recent diff if available.

### 2. Find the first real failure

Separate the first real failure from cascade failures, especially in serial or order-dependent suites.

### 3. Classify

Read `references/failure-taxonomy.md`, then classify the failure as locator, stale element, wait/timing, assertion mismatch, test data, setup/teardown, fixture isolation, environment/browser/grid, product regression, cascade, or unknown.

### 4. Assign a queue category

After classifying the failure mode, place the item in exactly one queue:

- **Autonomous** — reproducible, bounded, fixable within test code with a usable verification path; proceed via `pytest-selenium-test-improvement`.
- **Needs owner** — requires a product judgment, missing permissions/credentials, or an environment that cannot be obtained.
- **Ignored** — only when the user explicitly named this item as out of scope. Ordinary difficult, stale, or flaky items must never be self-assigned to Ignored.

Every report must list all Ignored items together with the explicit user instruction that justified each one.

### 5. Recommend the next step

State the likely root cause, confidence, missing evidence, and the smallest next action. If a code change is appropriate, hand off to `pytest-selenium-test-improvement`.

## Output

Use `assets/failure-analysis-template.md`. Keep the output evidence-based and concise.

## Guardrails

- Do not recommend skipping tests as the primary fix.
- Do not assume CI is correct just because it is green.
- Do not assume local is wrong without environment evidence.
- Do not claim product regression without behavior evidence.
