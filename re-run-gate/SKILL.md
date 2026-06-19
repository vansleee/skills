---
name: re-run-gate
description: >
  Verify that a test fix actually held by reading pytest-benchmark-runner output from a
  real (CI / staging) environment and deciding PASS, FAIL_RETRY, or ESCALATED. Closes
  the SDET loop: pytest-failure-triage → pytest-selenium-failure-analysis →
  agentic-sdet-governance → pytest-selenium-test-improvement → re-run-gate. Always use
  when the user has applied a fix and wants to verify it under a real re-run, or when a
  previous re-run-gate FAIL needs re-evaluation after another improvement attempt.
  Triggers include 「驗證修復是否成立」「跑 re-run-gate」「這個 fix 撐得住嗎」/check-gate.
---

# Re-Run Gate

The terminal gate of the SDET loop. Reads benchmark output from a real environment,
decides whether the loop closes, recycles, or escalates.

## What it never does

- **Never runs pytest.** Reads `pytest-benchmark-runner --json` output only. Execution
  and scoring are separated; this skill scores, the benchmark runner executes.
- **Never resets retry_count.** Only increments. Resetting is the only way to enter an
  infinite loop, so this skill refuses to do it.
- **Never closes a JIRA ticket without explicit user confirmation.** Closing is the
  only destructive action this skill takes; it always asks first.
- **Never re-evaluates a previously recorded result.** Reads `data/rerun-state.yaml`
  first and short-circuits if `(task_id, run_label)` already has a recorded decision.

## Inputs

- `--benchmark <path>` — JSON output from `pytest-benchmark-runner` (required)
- `--task-id <T###>` — tracker task identifier (required)
- `--ticket <JIRA-KEY>` — JIRA ticket to update (optional; JIRA steps skipped if absent)
- `--run-label <name>` — CI run name/number, defaults to ISO timestamp

## Workflow

### Step 1 — Validate inputs

Open `--benchmark` and verify it conforms to the `pytest-benchmark-runner` output
shape (at minimum: a `runs` array, each with `passed: bool` and `duration: number`).
If the file is malformed or empty, fail explicitly with the exact missing field.
Do not infer or invent fields.

If the benchmark file path matches any `gate.local_path_warn_patterns` entry from
config, print a warning: "Benchmark looks local — Live Proof Gate prefers CI / staging.
Proceeding anyway." Do not block. The user is responsible for the source they chose.

### Step 2 — Read state

Load `data/rerun-state.yaml`. Find the entry for `(task_id, run_label)`.

- **Entry exists with `last_result` for this `run_label`** → duplicate call. Print the
  previously recorded decision and exit. Do not call JIRA, do not touch
  retry_count, do not append to the audit log.
- **Entry exists, no result for this `run_label`** → proceed to Step 3 using the
  existing `retry_count`.
- **No entry exists** → create one with `retry_count: 0` and proceed.

### Step 3 — Score the benchmark

Count green runs. Apply `config.gate` thresholds:

| Decision | Condition |
|---|---|
| **PASS** | `green_runs >= pass_threshold` |
| **FAIL_RETRY** | `green_runs < pass_threshold` AND `retry_count < max_retries` |
| **ESCALATED** | `green_runs < pass_threshold` AND `retry_count >= max_retries` |

Defaults: `pass_threshold: 2`, `max_retries: 3` (i.e. 2-of-3 green required to pass;
up to 3 retry cycles before escalation).

### Step 4 — Act on the decision

**PASS:**

1. Print the decision and the evidence: per-run pass/fail and durations, total green
   count, and the source of the benchmark (path + any local-warning).
2. Ask the user to confirm closing the JIRA ticket and marking the tracker task done.
3. On user confirmation:
   - Post a closing comment on the JIRA ticket linking the benchmark path.
   - Transition the ticket via `config.jira.close_transition` (default "Done").
   - Invoke `automation-test-tracker` to set the tracker task status to
     `config.tracker.done_status` (default "done").

**FAIL_RETRY:**

1. Print the decision and the missing-green-run count.
2. Post a JIRA comment summarizing the failed runs and the benchmark path (comments
   are non-destructive — no confirmation required).
3. Increment `retry_count` in `data/rerun-state.yaml`. This is the only field the
   skill mutates other than `last_result`.
4. Emit a hand-off marker in the output: `recommended_next_skill: pytest-selenium-test-improvement`.
   The user (or the orchestrating workflow) invokes that skill — re-run-gate never
   calls it directly.

**ESCALATED:**

1. Print the decision and the final retry count.
2. Post a JIRA comment: `escalated: max retries reached (<retry_count>/<max_retries>).
   Leaving ticket open for human review.` Do not transition the ticket.
3. Invoke `automation-test-tracker` to set the tracker task status to
   `config.tracker.blocked_status` (default "blocked") with
   `Blocked reason: re-run-gate ESCALATED after <max_retries> retries`.
4. Append to the triage report file under `config.triage_report.dir` the line:
   `- <task_id>: escalated: max retries reached`.

### Step 5 — Record and audit

Append a single entry to `data/gate-log.yaml` with at minimum:
`{timestamp, task_id, run_label, retry_count, decision, evidence_summary,
ticket_key, benchmark_path}`. The log is **append-only** — never delete entries,
never edit a prior entry. If the file grows large, summarize older entries into a
separate `gate-log.archive.yaml` but preserve originals.

Update `data/rerun-state.yaml` for `(task_id, run_label)` with `last_result: <decision>`
and the new `retry_count`. This is what makes Step 2 short-circuit on duplicate calls.

## Rules

- **One decision per `(task_id, run_label)`.** Idempotency is enforced by Step 2.
- **JIRA close is the only destructive action.** Always confirm with the user. JIRA
  comments are not destructive; they may be posted without confirmation.
- **Comments must include the benchmark path.** Anyone reading the ticket later must
  be able to trace which file drove the decision.
- **The benchmark must come from a real environment.** If the path looks local
  (matched by `config.gate.local_path_warn_patterns`), warn but proceed. Do not
  silently fail — surface the risk.
- **Tracker updates go through `automation-test-tracker`.** This skill does not edit
  `TEST_IMPROVEMENT_TRACKER.md` directly.
- **Read `agentic-sdet-governance` first** if you are unsure whether the current
  authorization tier permits ticket closure.

## Resources

- `config.example.yaml` — gate thresholds, JIRA settings, file paths.
- `data/rerun-state.yaml` — per-task mutable state (gitignored).
- `data/gate-log.yaml` — append-only audit log (gitignored).
- Upstream input: `pytest-benchmark-runner` JSON output.
- Downstream on FAIL_RETRY: `pytest-selenium-test-improvement` (via hand-off marker).
- Downstream on ESCALATED: human review + `automation-test-tracker` update.
- Governing skill: `agentic-sdet-governance`.

## See also

- `pytest-failure-triage` — entry point of the SDET loop.
- `pytest-selenium-failure-analysis` — RCA before any action.
- `pytest-selenium-test-improvement` — applies the actual fix.
- `automation-test-tracker` — tracker state machine and writes.
- `pytest-benchmark-runner` — produces the benchmark JSON this skill consumes.
