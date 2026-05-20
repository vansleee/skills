---
name: how-to-test
description: >-
  Explain how a test suite, fixture stack, page object layer, or test flow works in this **test repository**, at the level of an SDET onboarding to a new automation codebase. Trigger with "how does this test work", "walk me through the fixtures", "explain the page object layer", "how is the test data set up", "/how-to-test", or any request to understand pytest + Selenium E2E tests or integration / API tests. Add "and critique it" / "也幫我 critique" to run a reliability + maintainability review pass.
---

# how-to-test

Explain test code by exploring the repo and producing a structured, SDET-grade walkthrough of how the suite is built. Optionally critique it for reliability and maintainability.

Sibling of `how` (which targets product code). This one targets **test code** — pytest + Selenium E2E, and integration / API tests. If the question is about product code, use `how` instead.

## Modes

- **Explain** (default) — explore the test repo and produce a structured explanation focused on **test architecture**: fixtures, page objects, helpers, data setup, isolation, runner config.
- **Critique** — run Explain first, then spawn independent critics for **Reliability** and **Maintainability** against the rubric.

Critique is triggered when the user says any of: "critique", "review the test design", "also critique", "找出問題", "幫我 critique", "test design review", "is this flaky".

## Routing — simple vs. complex

**Simple** (skip fan-out, single agent end-to-end):
- One test file, one fixture, one page object, or one helper.
- A localized question about a specific waiter, locator, or assertion pattern.
- Examples: "What does `LoginPage.login()` do?", "Why does `db_session` fixture roll back?", "How does the `wait_for_table_loaded` helper work?".

**Complex** (decompose, fan out 2–4 explorer subagents in parallel, then synthesize):
- Spans multiple layers (test → page object → driver wrapper → helpers → fixtures → conftest).
- Asks about a flow that crosses concerns (E2E suite setup, parallel execution, env config, test data lifecycle).
- Examples: "How does this E2E suite get a logged-in browser?", "Walk me through what happens between `pytest` invocation and the first assertion", "How are API tests isolated from each other?".

When in doubt, treat as complex.

## Workflow

### Step 1 — Read the prompts

Read `references/explainer-prompt.md`. If complex, also read `references/explorer-prompt.md`. If critique is requested, also read `references/critic-prompt.md` and `references/critique-rubric.md`.

### Step 2 — Orient

Locate the test framework config and root before anything else:
- `pytest.ini` / `pyproject.toml [tool.pytest.ini_options]` / `setup.cfg`
- Top-level `conftest.py` (and nested conftests — order matters)
- `requirements*.txt` / `Pipfile` / `poetry.lock` — which selenium / requests / httpx / playwright versions
- CI config — how the suite is actually invoked (`.github/workflows/`, `.gitlab-ci.yml`, `Makefile`, `tox.ini`)
- Page object root (commonly `pages/`, `page_objects/`, `pom/`) — if Selenium
- API client root (commonly `api/`, `clients/`) — if API tests
- Test data (commonly `data/`, `fixtures/`, `factories/`)

If you cannot locate the test root or framework after 3 search attempts, ask the user — wrong root = wrong explanation.

### Step 3a — Simple path

Follow `references/explainer-prompt.md`. Read the entry point and its immediate collaborators (the fixture it requests, the page object it imports, the helper it calls). Produce the five-section output.

### Step 3b — Complex path (fan-out)

1. Decompose the question into 2–4 **non-overlapping exploration angles**. Examples for "how does this E2E suite get a logged-in browser":
   - Driver / browser lifecycle (fixture, session vs. function scope, parallel safety)
   - Authentication path (UI login vs. API login vs. injected cookie / token)
   - Page object initialization and base class (waits, root URL, navigation)
   - Test data prerequisites (user creation, tenant setup, cleanup ownership)

   For API tests, angles might be: HTTP client construction, auth strategy, test data setup/teardown, response assertion patterns.

   Keep angles orthogonal.

2. For each angle, spawn one explorer in parallel via the `Agent` tool (subagent_type `Explore` or `general-purpose`). Pass `references/explorer-prompt.md` and the assigned angle. **Single message, multiple tool calls** so they run concurrently.

3. After all explorers return, act as synthesis agent: reconcile, resolve contradictions by re-reading files yourself, and produce the five-section output. Do not concatenate subagent reports verbatim.

### Step 4 — Critique pass (only if requested)

Spawn exactly 2 critics in parallel via `Agent`:
- **Reliability critic** — assigned focus: flakiness sources, hidden waits, shared state, cleanup gaps, isolation breaks, environment coupling, retry / rerun behavior.
- **Maintainability critic** — assigned focus: page object discipline, locator strategy consistency, fixture duplication, helper sprawl, naming consistency, abstraction leaks between layers.

Each critic receives:
- The explanation produced in step 3
- `references/critic-prompt.md`
- `references/critique-rubric.md`
- Its assigned focus

Use different models where possible (e.g., one `model: "opus"`, one default). Send both spawns in one message.

Append findings as a Critique section, severity-ordered, deduplicated.

## Output format

Always exactly these five sections, in this order, with `##` headings:

```
## Overview
1–3 sentences. What this test suite covers, what stack it uses, and how it's invoked in CI.

## Test Architecture
The layered shape of the suite. Tests → page objects (or API clients) → driver/HTTP wrapper → fixtures → conftest → runner config.
For each layer, one or two sentences on what it owns and how it's wired to the next.

## How Tests Are Written
The canonical pattern an SDET would follow to add a new test here.
Walk through one representative test path end-to-end: setup (fixtures requested), action (page object methods or API calls), assertion style, cleanup (who owns it).
Reference real file paths and symbols.

## Where Things Live
Map concept → file path. One line per entry. Cover: conftests (ordered top→bottom), fixtures of note,
page object root, API client root, test data / factories, helpers, env config, CI invocation.

## Gotchas
Non-obvious behaviors specific to **test reliability and maintenance**. This is the highest-value section.
Examples: implicit waits hiding races, shared browser/session state across tests, fixture order surprises,
test data leaks, env-specific skips, hardcoded URLs, locator strategies that quietly differ, retries masking real flakes,
parallel execution constraints, cleanup that fires only on success.
Do not skip this section.
```

If critique was run, append:

```
## Critique

### Reliability
Findings ordered by severity (P1 → P3) from the Reliability critic. Each finding: claim, evidence (file:line), failure mode, suggested direction.

### Maintainability
Same shape, from the Maintainability critic.
```

## Guardrails

- **Never invent files, fixtures, page objects, or helpers.** If you have not opened the file, do not claim what it does.
- **Cite real paths.** Every claim references a real `path/to/file.ext` in this test repo.
- **Quote sparingly.** ≤6 lines per quote.
- **Do not fan out for simple questions.**
- **Critique is opt-in.** Do not critique unless asked.
- **Do not propose rewrites in the explanation.** That is the critique's job.
- **Do not suggest sleeps, broad retries, or test skips** as fixes for anything you find — those are anti-patterns this repo's other skills explicitly reject.

## Wires to other skills in this repo

When the user follows up after an explanation, suggest the right next skill:
- "Improve / fix the test" → `pytest-selenium-test-improvement` (uses tracker + baseline/after benchmarks)
- "Review the code" → `selenium-best-practices-review`
- "Diagnose a failure" → `pytest-selenium-failure-analysis`
- "Benchmark stability" → `pytest-benchmark-runner`
- "Write a PR summary for the change" → `automation-pr-summary`
- "Track the work" → `automation-test-tracker`
- "Governance / rules of engagement" → `agentic-sdet-governance`

Do not invoke those skills inside this one — just point.

## When not to use this skill

- The user wants to explain **product code** → use `how` instead.
- The user wants to **change** a test → use `pytest-selenium-test-improvement`.
- The user wants to **diagnose a failing test run** → use `pytest-selenium-failure-analysis`.
- The user wants a one-line answer to a factual test-code question → just answer.
