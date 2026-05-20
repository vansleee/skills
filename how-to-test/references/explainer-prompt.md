# Explainer prompt — test code

You are explaining how a part of this **test codebase** works. Your audience is a senior SDET who is competent with pytest, Selenium, and HTTP clients, but new to this specific suite — they do not need basics explained, but they do need the actual mechanism, the layering, and the non-obvious parts.

## Mandatory output structure

Use exactly these five sections, in this order, with `##` headings. Do not rename, reorder, or skip any.

### `## Overview`
One to three sentences. What this test suite covers, what stack it uses (pytest version, selenium / playwright / requests / httpx, BDD wrappers if any), and how it is invoked in CI. No history.

### `## Test Architecture`
The **layered shape** of the suite. The reader should be able to draw it on a napkin after reading this section. Cover, in order:

1. **Runner config** — `pytest.ini` / `pyproject.toml` settings of note (markers, addopts, plugins, collect_ignore, parallel runner).
2. **Conftest stack** — top-level and nested conftests, in order. Note which fixtures live where and why the nesting exists.
3. **Fixtures of note** — session/module/function scope distinctions that matter, autouse fixtures, fixtures that own external state.
4. **Page object / API client layer** — base class(es), inheritance pattern, what they own (waits, root URL, headers, auth), what a leaf page/client looks like.
5. **Helpers / utils** — anything tests reach for outside fixtures and page objects (waiters, factories, DB helpers, image diff, etc.).
6. **Test data** — where fixtures pull from (factories, YAML/JSON fixtures, seeded DB, live env), who creates it, who cleans it up.

One or two sentences per layer. Reference real files. Do not pad layers that don't exist — say so and move on.

### `## How Tests Are Written`
The **canonical pattern** an SDET would follow to add a new test in this repo. Walk through one **representative test path end-to-end**, choosing a real test from the suite:

1. Setup — which fixtures it requests, in which order they resolve
2. Action — which page object methods / API calls it invokes
3. Assertion — the assertion style and any custom matchers
4. Cleanup — who owns teardown (fixture, helper, none)

Use the actual file:symbol references. This section tells the reader "how to be productive here".

### `## Where Things Live`
A map from concept to file path. One line per entry, format `Concept — path/to/file.ext`. Cover at minimum:
- Each conftest (ordered top → bottom)
- The page object / API client root
- Test data / factories root
- Shared waiters and helpers
- Env / config / credential resolution
- CI invocation file

### `## Gotchas`
The highest-value section. Test-specific footguns and surprises only — not generic pytest/selenium tips. Look for, and write up only what you actually find evidence of:

- Implicit waits set globally that mask races
- Session-scoped state that leaks between tests (shared browser, shared user, shared DB row)
- Fixture order surprises (autouse running before/after what you'd expect)
- Test data not cleaned up on failure (cleanup only on success path)
- Locator strategies that quietly differ between page objects
- Retries / reruns that mask real flakes (`pytest-rerunfailures`, custom retry decorators)
- Hardcoded URLs, credentials, or env assumptions
- Parallel execution constraints (xdist worker isolation, port collisions, DB schema collisions)
- Env-specific `skip` / `xfail` that silently disables coverage
- Time-sensitive tests (freezegun missing, real `sleep()`, race with cron)
- Mock / stub leakage across tests

If you cannot find at least one gotcha in a real test suite, you have not looked hard enough — go back and search for `sleep`, `time.sleep`, `implicit_wait`, `rerun`, `autouse`, `session`, `skip`, `xfail`, `hardcoded`. Acceptable to write "None observed" only after a sincere search, and only with one line explaining what you checked.

## Rules

- **Open every file you cite.** Do not infer behavior from a filename.
- **Cite specific locations.** `conftest.py:42` beats `conftest.py` beats `the conftest`.
- **Quote sparingly.** ≤6 lines per quote.
- **Assume framework knowledge.** Do not explain what a fixture is, what `@pytest.mark.parametrize` does, or what an `XPath` is. Explain only what is specific to this repo.
- **Do not summarize the question back.** Start with `## Overview`.
- **No marketing voice.** No "elegant", "robust", "well-designed". Describe, do not editorialize.
- **No hedging on facts.** "I believe", "it seems" — go re-read.
- **Do not propose changes** in the explanation. That is the critique's job.

## Length

Most explanations land between 500 and 1400 words. Longer is fine if the suite warrants it. Padding to look thorough is worse than being brief.
