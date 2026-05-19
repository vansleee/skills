---
name: automation-test-tracker
description: >-
  Create, maintain, and update TEST_IMPROVEMENT_TRACKER.md for automation test improvement work. Use when adding pytest/Selenium improvement tasks, selecting the next task, recording baseline and after benchmark results, marking status, tracking risk, or summarizing progress across automation-test repairs.
---

# Automation Test Tracker

Keep automation-test improvement work auditable.

## Workflow

### 1. Find or create the tracker

Use `TEST_IMPROVEMENT_TRACKER.md` in the target project root. If it is missing and the user asked for tracker work, create it from `assets/tracker-template.md`.

### 2. Add or select tasks

Use stable IDs such as `T001`. Select by user-specified ID first, then blocking CI failure, then smallest task with clear affected tests, then highest repeated flake or maintenance pain.

### 3. Maintain required fields

Every task should have scope, affected tests, problem, acceptance criteria, baseline, after, files changed, risk, and notes.

### 4. Update status conservatively

Move a task to Done only when acceptance criteria pass. If blocked, record blocker evidence and the next action. Do not silently delete tasks.

## Rules

- Record commands exactly.
- Preserve benchmark history.
- Keep notes evidence-based.
- Mention if only affected tests were run.
- Do not mark done when the after benchmark is missing.

## Resources

- `assets/tracker-template.md` for the initial file.
- `references/status-rules.md` for status semantics.
