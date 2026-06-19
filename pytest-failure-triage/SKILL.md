---
name: pytest-failure-triage
description: >
  Triage failed automation tests from a pytest report — JUnit XML, pytest console output,
  or pytest-html — typically produced by a Jenkins (or any CI) run: parse the failures,
  group them by owner, create or update the corresponding JIRA tickets (one per owner),
  then delegate root-cause analysis to the pytest-selenium-failure-analysis skill.
  Always use this skill when the user provides a pytest report path/URL or CI test output
  and wants tickets created, failures triaged, owners notified, or asks things like
  「幫我 triage 這份 report」、「根據 owner 開 JIRA ticket」、「分析這個 run 的失敗」、/triage-report.
---

# Pytest Failure Triage

Usage: `/triage-report <report_path_or_url>`

Accepted inputs (any one, in priority order):

1. **JUnit XML** (`--junitxml` output) — most structured, prefer this.
2. **pytest console output** (CI console log or a saved text file).
3. **pytest-html report** (`--html` output).

The input can be a local path or a URL. Download URLs with `curl -s` into `/tmp/triage/` before parsing — do not use WebFetch for intranet HTTP servers (it force-upgrades to HTTPS and fails).

## Configuration

Read `config.yaml` in the skill directory if it exists; otherwise fall back to the defaults in `config.example.yaml`. On first run, confirm any missing required settings with the user before continuing:

```yaml
jira:
  base_url: "https://jira.example.com"
  project_key: "PROJ"
  issue_type: "Bug"
  auth: "env:JIRA_API_TOKEN"   # Bearer token from env var; never ask the user to paste it in chat
  labels: ["pytest-triage", "auto-created"]
ownership:
  # test path pattern (glob) -> owner name; earlier entries win
  owner_map: {}
  # owner name -> JIRA username / accountId (if missing, leave the ticket unassigned and note it in the description)
  jira_account_map: {}
  # when owner_map has no match, infer the owner via git history (majority author of the test file)
  fallback_git_blame: true
dedupe:
  jql_template: 'project = {project_key} AND labels = pytest-triage AND summary ~ "{test_file}" AND statusCategory != Done'
```

## What to do

### Step 1 — Collect the report

- Read local paths directly; download URLs with `curl -s <url> -o /tmp/triage/report.<ext>`.
- Auto-detect the format: content starting with `<testsuite` → JUnit XML; HTML → pytest-html; anything else → console output.
- `head` the file to inspect the actual structure before writing the parser; do not assume field order.

### Step 2 — Parse failures

Write a small script to `/tmp/triage/parse_report.py` that emits JSON to `/tmp/triage/failures.json`; every later step consumes that JSON. For each failure collect at least:

| Field | Source |
|-------|--------|
| nodeid | full `file::class::test` path |
| test_file | file part of the nodeid (key for owner mapping and dedupe) |
| outcome | failed / error / skipped (error includes collection errors) |
| error_type | exception class (e.g. `TimeoutException`, `AssertionError`) |
| message | first line of the failure message |
| traceback | full traceback (fed to RCA) |
| duration | seconds, if available |

Also emit run totals (total / passed / failed / error / skipped). Flag collection errors (files with no counted tests) as WARNING.

### Step 3 — Resolve owners

For each failed/error test_file, resolve the owner in order:

1. Match `ownership.owner_map` glob patterns (first match wins).
2. If `fallback_git_blame: true` and the file is inside a git repo: `git log --format=%an -- <file>`, take the author with the most commits in the last year.
3. Otherwise owner = `unassigned`, and flag "⚠ owner mapping missing: <file>" in both the ticket and the final report.

### Step 4 — Root cause analysis (delegate)

For each failure, invoke the **`pytest-selenium-failure-analysis`** skill with the nodeid, error_type, message, and traceback (plus screenshot / browser log paths when available), and collect:

- failure classification (locator / wait-timing / assertion mismatch / test data / fixture isolation / environment / product regression / cascade / unknown)
- queue category (Autonomous / Needs owner / Ignored)
- likely root cause, confidence, and the smallest recommended next step

Failures sharing the same error signature may be analyzed once as a group to avoid duplicate work. Feed the RCA results into the ticket descriptions in Step 5.

### Step 5 — Create or update JIRA tickets

Group failures by owner; all failures for one owner go into **a single ticket** (one ticket per owner) to avoid flooding the project.

**Validate RCA input.** Before constructing any ticket description, validate the RCA payload from Step 4 against `pytest-selenium-failure-analysis/schemas/rca_result.json`. Required fields per the schema: `schema_version`, `nodeid`, `classification`, `confidence`, `queue`, `root_cause`, `next_step`. If any required field is missing for a given failure, surface the violation in the final report's WARNING section and skip that failure from ticket creation — do not fabricate fields.

**Dedupe before creating.** For each owner group:

1. Search for an existing open ticket using `dedupe.jql_template`:
   ```
   curl -s -H "Authorization: Bearer $JIRA_API_TOKEN" \
     "<jira_base>/rest/api/2/search?jql=<urlencoded_jql>&fields=key,summary,status"
   ```
2. **Existing ticket found → update it**: add a comment with this run's failure list and RCA (never overwrite the original description). Before commenting, check whether this run has already been commented (idempotency).
3. **No match → create a new ticket**:
   ```
   curl -s -X POST -H "Authorization: Bearer $JIRA_API_TOKEN" -H "Content-Type: application/json" \
     "<jira_base>/rest/api/2/issue" -d @/tmp/triage/issue_<owner>.json
   ```

Ticket content template:

- **Summary**: `[Triage][<run_label>] <N> failed tests — <owner>` (run_label = CI build name/number, or the date if unavailable)
- **Description** (JIRA wiki markup):
  ```
  h3. Source
  * Report: <report path/URL>
  * Run: <CI run URL, if the user provided one>

  h3. Failed Tests
  || Test || Outcome || Error || Classification || Queue ||
  | <nodeid> | failed | <error_type>: <message> | <RCA classification> | Autonomous/Needs owner |

  h3. RCA
  <root cause, confidence, and recommended next step from pytest-selenium-failure-analysis>
  ```
- **Assignee**: `jira_account_map[<owner>]` (omit the assignee field when unmapped)
- **Labels**: apply `jira.labels`

Creating tickets and commenting are **external side effects**: list the planned tickets (owner, summary, failed tests) to the user for confirmation, and call the JIRA API only after approval.

### Step 6 — Final report

Output a triage summary in the conversation (print the full clickable URL for every ticket; never just the ticket key):

| Owner | JIRA Ticket (full URL) | Action (created/updated) | Failed Tests | RCA Classification | Queue |
|-------|------------------------|--------------------------|---------------|--------------------|-------|

Plus:

- ⚠ owners / files that could not be mapped
- ⚠ files with collection errors
- multiple failures in the same run sharing one error signature (e.g. the same timeout / connection error) → flag a possible environment or stack-wide event and suggest a single infra ticket instead of assigning to individual owners
- items queued as **Autonomous** → hand off to `pytest-selenium-test-improvement` for repair (subject to `agentic-sdet-governance` authorization tiers; never start without authorization), then to `re-run-gate` after the improvement finishes (max retries: 3). On escalation, leave the JIRA ticket open and append "escalated: max retries reached" to the triage report

Save the report to `<project-root>/triage-reports/<YYYY-MM-DD>_<run_label>_triage.md` (create the directory if missing).

## Notes

- passed + failed + error + skipped should equal total; flag a WARNING in the report when they differ.
- Always read the JIRA token from the environment variable; if unset, ask the user to set it and rerun — never ask them to paste a token in chat.
- Rerunning the same report must be idempotent: the dedupe logic prevents duplicate tickets, and duplicate comments are checked before posting.
- Division of labor: this skill only triages and files tickets; analysis belongs to `pytest-selenium-failure-analysis`, repair belongs to `pytest-selenium-test-improvement`, and everything is governed by `agentic-sdet-governance`.
