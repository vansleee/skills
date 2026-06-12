---
name: agentic-sdet-governance
description: >-
  Governance rules for Agentic SDET workflows and Claude Skills that modify or analyze automation tests. Use this skill when an agent is about to run multi-step test improvement work, repair pytest/Selenium tests, use TEST_IMPROVEMENT_TRACKER.md, apply baseline/after benchmarks, coordinate multiple SDET skills, or needs guardrails against overengineering, silent assumptions, broad rewrites, skipped tests, weakened assertions, or unverified success.
---

# Agentic SDET Governance

Use this skill as the control layer for automation-test agents. It does not replace specialized skills such as `pytest-selenium-test-improvement`; it constrains how they are used.

## Core Rules

### 1. Think before coding

State the current goal, affected area, success criteria, and known unknowns before editing. Do not silently assume expected behavior, environment state, or test ownership.

### 2. Read before writing

Inspect the relevant tests, fixtures, page objects, helper utilities, tracker entries, and existing patterns before making changes.

### 3. Keep changes surgical

Change the smallest set of files needed for the selected tracker item. Do not bundle unrelated cleanup, style changes, or speculative abstractions.

### 4. Prefer simple fixes

Use the existing test architecture and project conventions. Add abstractions only when they remove real duplication or enforce a repeated reliability pattern.

### 5. Validate intent, not only green output

Passing tests are not enough. Verify that the test still checks the user-visible or business-relevant behavior it is supposed to protect.

### 6. Make deterministic work deterministic

Use scripts for repeated benchmark runs, parsing, tracker summaries, and other mechanical work. Do not reimplement deterministic work in freeform reasoning each time.

### 7. Checkpoint long workflows

After each major step, record what was learned: selected task, baseline result, diagnosis, change made, after result, remaining risk.

### 8. Reveal pattern conflicts

If the codebase has conflicting patterns, name the conflict and choose the pattern closest to the edited area. Do not invent a third style without explicit reason.

### 9. Fail explicitly

If a test cannot run, evidence is missing, or the environment is unavailable, say so clearly. Do not present partial work as fully verified.

### 10. Protect test integrity

Do not skip tests, weaken assertions, add broad retries, increase global timeouts, or add sleeps to create a green result.

### 11. Keep humans in the loop with tiered authorization

Treat analysis, modification, and publication as separate permissions. A grant at one tier never implies the next.

- **Analysis and diagnosis** — reading code, running tests, benchmarks, failure analysis — requires no authorization.
- **Modifying test code** requires an explicit task assignment from the user.
- **Commit/push**, **opening PRs**, **merging**, and **changing CI gates or release criteria** each require their own explicit authorization. Push permission does not imply merge permission; an assigned fix does not imply commit permission.

Without the required permission, stop at the last authorized boundary and report the exact next action and the permission it needs.

### 12. Use the specialized skill chain

- Use `automation-test-tracker` for tracker creation and updates.
- Use `pytest-benchmark-runner` for repeated pytest baseline/after runs.
- Use `pytest-selenium-failure-analysis` for unclear Selenium failures.
- Use `pytest-selenium-test-improvement` for the repair workflow.
- Use `selenium-best-practices-review` for review.
- Use `automation-pr-summary` for final PR text.

### 13. Ask decision-ready questions only

Do not bring the user an unprepared question. First finish the analysis, candidate fixes, evidence, and tradeoffs that can be done autonomously. Then converge the question into explicit options (adopt A / adopt B / abandon), each with its consequences, and include your own recommendation with concise rationale. This supplements rules #5, #9, and #11: failing explicitly is still required, but the failure report must arrive decision-ready.

## Default Agentic SDET Loop

1. Confirm the selected tracker item or choose one unfinished item.
2. Read relevant code and evidence.
3. Define affected tests and success criteria.
4. Run the baseline benchmark.
5. Diagnose and apply the smallest safe fix.
6. Run the after benchmark with the same selector.
7. Compare before/after results.
8. Update the tracker.
9. Summarize verification, risk, and follow-up.

## Resources

- `references/sdet-agent-rules.md` contains the expanded governance rules.
- `assets/checkpoint-template.md` contains a checkpoint format for long-running tasks.
- `evals/evals.json` defines expected behavior for governed SDET workflows.
