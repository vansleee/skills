# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repo purpose

Collection of personal Claude skills — each skill is a self-contained subdirectory with its own `SKILL.md` (workflow), `README.md` (setup), `scripts/`, `tests/`, `config.example.yaml`, and `data/`.

## Install / activate skills

Symlink every skill in this repo into `~/.claude/skills/`:

```bash
./install-skills.sh             # install / refresh (idempotent — safe after git pull)
./install-skills.sh --dry-run   # preview, change nothing
./install-skills.sh --uninstall # remove only the symlinks this repo owns
```

The script auto-discovers any subdir containing a `SKILL.md`. Hand-written files at the target path are preserved (skipped, never overwritten). Open a new Claude Code session after install to pick up the new skills.

Override target with `CLAUDE_SKILLS_DIR=/some/other/path ./install-skills.sh`.

## Skills

### daily-missing-juenu

Finds Lee Ju-Eun (李珠珢) fan videos daily, composes a Slack draft digest, never auto-sends.

**Setup (first time):**
```bash
cd daily-missing-juenu
pip install pyyaml --break-system-packages
cp config.example.yaml config.yaml
cp data/fan-accounts.example.yaml data/fan-accounts.yaml
cp data/sent-log.example.yaml data/sent-log.yaml
# edit config.yaml: fill slack.sender.user_id and slack.recipient.dm_channel
```

**Run tests:**
```bash
cd daily-missing-juenu
python3 -m unittest discover -s tests -v
```

**Run one test module:**
```bash
python -m unittest tests.test_store -v
```

## Architecture — daily-missing-juenu

```
scripts/config.py   — YAML config loader; cached load(), dotted-path get(), convenience accessors
scripts/store.py    — YAML-backed data API: sent-log, fan-accounts, openers, state
scripts/tools.py    — CLI entry point (argparse); 20+ subcommands, all support --json
tests/              — stdlib unittest; safe to run anytime (temp files, no network)
```

**Data flow:**
1. `get-since` → time window for search
2. Browse fan accounts / WebSearch → candidate URLs
3. `is-sent <url>` → dedupe (exit 0 = already sent, skip)
4. `is-fresh <url> [--posted-at ISO]` → freshness gate (exit 0=keep, 1=stale, 2=unknown, 5=rejected)
5. Filter to exactly `message.video_count` freshest candidates
6. `pick-opener` → random Chinese/Korean phrase avoiding recent repeats
7. `slack_send_message_draft` to `slack.recipient.dm_channel` — **never call send directly**
8. `record-sent --url ... --handle ... --platform ... --opener ...` → writes sent-log, bumps fan account, advances `last_run_at`

**Exit code contract (tools.py):**
- `0` — success / positive result (is-sent=yes, is-fresh=yes)
- `1` — expected negative (is-sent=no, is-fresh=stale)
- `2` — unknown / missing data
- `3` — validation error
- `5` — freshness rejected by record-sent

**Data files (all gitignored except openers.yaml):**
- `data/sent-log.yaml` — dedup source; list of `{date, url, handle, platform, country, opener}`
- `data/fan-accounts.yaml` — watchlist; ranked by `hit_count` desc; auto-created on first bump
- `data/openers.yaml` — shipped in repo; list of Chinese/Korean phrase strings
- `data/state.yaml` — single key `last_run_at` (ISO datetime); advanced by `record-sent`

**Key conventions:**
- All dates: `YYYY-MM-DD` string in YAML
- TikTok freshness: derived from video ID (top 32 bits = Unix timestamp); no `--posted-at` needed
- Other platforms: must pass `--posted-at` parsed from page JSON-LD or `og:published_time`
- Handles: stored without leading `@`
- URLs are canonical dedupe keys

Full workflow details: `daily-missing-juenu/SKILL.md`

### agentic-sdet-governance

Governance rules for Agentic SDET workflows. Use as the control layer before multi-step automation-test repair work. It enforces read-before-write, one tracker item at a time, baseline/after verification, explicit checkpoints, no skipped tests, no weakened assertions, no silent failures, and human-in-loop boundaries.

### pytest-selenium-test-improvement

Human-in-loop workflow for improving pytest + Selenium automation tests. Uses tracker tasks, 3-run baseline benchmarks, minimal fixes, 3-run after benchmarks, tracker updates, and optional PR summaries.

Key resources:
- `pytest-selenium-test-improvement/SKILL.md`
- `pytest-selenium-test-improvement/references/pytest-selenium-guidelines.md`
- `pytest-selenium-test-improvement/assets/tracker-template.md`
- `pytest-selenium-test-improvement/evals/evals.json`

### pytest-selenium-failure-analysis

Diagnoses pytest + Selenium failures from pytest output, Selenium exceptions, screenshots, browser logs, CI logs, and reruns. Outputs classification, evidence, confidence, likely root cause, and next step.

### automation-test-tracker

Maintains `TEST_IMPROVEMENT_TRACKER.md` using stable task IDs, affected tests, baseline/after benchmarks, risk, and status sections.

### selenium-best-practices-review

Reviews Selenium tests, page objects, fixtures, locators, waits, retries, and isolation for reliability risks.

### pytest-benchmark-runner

Runs pytest selectors repeatedly and summarizes pass rate, durations, exit codes, and failure signatures.

Run tests:
```bash
cd pytest-benchmark-runner
python3 -m unittest discover -s tests -v
```

Run benchmark:
```bash
python3 pytest-benchmark-runner/scripts/run_pytest_benchmark.py --runs 3 -- tests/e2e/test_login.py -q
```

### automation-pr-summary

Creates structured PR descriptions for automation-test improvements using tracker entries, diffs, and before/after benchmark evidence.

### how

Explains how a subsystem, feature, or flow works in **product source code**, at the level of a senior engineer onboarding. Adapted from [poteto/how](https://github.com/poteto/how). Two modes: Explain (default — Overview / Key Concepts / How It Works / Where Things Live / Gotchas) and Critique (spawns parallel critics against an architectural rubric). Complex questions fan out into 2–4 parallel explorer subagents, then a synthesis pass.

Trigger: "how does X work", "walk me through Y", "explain the architecture of Z". Add "also critique" for the review pass.

Layout:
```
how/
├── SKILL.md
└── references/
    ├── explainer-prompt.md
    ├── explorer-prompt.md
    ├── critic-prompt.md
    └── critique-rubric.md
```

### how-to-test

Sibling of `how`, targeted at **test code** — pytest + Selenium E2E and integration / API test repos. Output emphasizes test architecture (conftests, fixtures, page objects / API clients, helpers, test data, runner config) and reliability/maintainability gotchas. Critique mode runs exactly two critics in parallel: **Reliability** (flakiness, hidden waits, isolation, retry behavior, env coupling) and **Maintainability** (page object discipline, locator strategy, fixture sprawl, naming).

Hard prohibitions in critique findings (per `agentic-sdet-governance`): never recommend `time.sleep`, broader retries, skips/xfails, weakened assertions, swallowed exceptions, or wholesale rewrites.

Trigger: "how does this test work", "walk me through the fixtures", "explain the page object layer", "how is the test data set up". Add "also critique" for the review pass.

Wires (points the user at, never invokes): `pytest-selenium-test-improvement`, `selenium-best-practices-review`, `pytest-selenium-failure-analysis`, `pytest-benchmark-runner`, `automation-test-tracker`, `automation-pr-summary`, `agentic-sdet-governance`.

Layout: same as `how/` above.
