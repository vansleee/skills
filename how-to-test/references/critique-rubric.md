# Critique rubric — test code

Use this rubric to apply your assigned focus area (Reliability **or** Maintainability) to the test-suite explanation. Each section lists the questions to ask and the kinds of findings that count as real.

A finding is real only if you can name a concrete failure mode (flake, false signal, missed regression, maintenance cost, SDET trap). "I would have done it differently" is not a finding.

The hard prohibitions in `critic-prompt.md` apply throughout — never recommend sleeps, retries, skips, weakened assertions, swallowed exceptions, or rewrites.

---

## Reliability

The question this critic answers: *under what concrete conditions does this suite lie?*

### Hidden waits and race conditions

Questions:
- Is there a global `implicitly_wait` or driver-level wait that masks races?
- Are there `time.sleep()` calls in tests, page objects, or helpers? What race are they papering over?
- Are explicit waits (`WebDriverWait`, custom `wait_for_*`) used consistently, or only in some places?
- Are waits tied to the **actual readiness condition** (element clickable, request settled, network idle) or to a proxy (element visible)?
- For API tests: are there assumptions about eventual consistency without a poll?

Counts as real:
- "`conftest.py:18` sets `driver.implicitly_wait(10)` globally; explicit waits in `pages/orders.py:60` then stack on top, giving 20–30s on real races and hiding the underlying flake."
- "`time.sleep(2)` in `helpers/uploads.py:44` is the only synchronization after triggering an upload; under CI load this falls under the response time and the next assertion sees stale state."

### Test isolation

Questions:
- Is the browser session shared across tests (session-scope driver fixture)? What state leaks?
- Are users / tenants / DB rows shared between tests? Who cleans up?
- Does cleanup run on test failure, or only on success (`yield` vs. `finalizer` vs. `try/finally`)?
- Under `pytest-xdist`, do workers collide on ports, DB schemas, user accounts, or filesystem paths?
- Are autouse fixtures running in an order that breaks isolation?

Counts as real:
- "`browser` fixture in `conftest.py:30` is session-scope; cookies set by `test_a` are visible to `test_b`, and the suite passes only in the current alphabetical order."
- "Test data created in `tests/api/test_orders.py:55` is cleaned up in a post-action block that is never reached if the assertion fails — failed runs accumulate rows in the shared test tenant."

### Environment coupling

Questions:
- Are URLs, credentials, or test data IDs hardcoded?
- Does the suite assume a specific deploy state (a particular user exists, a flag is on)?
- Is there a single env-detection branch (`if env == "staging"`) that silently changes test behavior?
- Are `skip` / `xfail` markers gating tests on env in ways the explanation didn't surface?

Counts as real:
- "`pages/login.py:12` hardcodes `https://staging.example.com`; the suite cannot run against PR preview envs and tests silently pass against the wrong target if `BASE_URL` is unset."
- "`@pytest.mark.skipif(env != 'staging')` in `tests/test_billing.py:8` removes 14 tests from CI without surfacing in the summary."

### Retry / rerun behavior

Questions:
- Is `pytest-rerunfailures` (or equivalent) enabled? At what scope?
- Are there custom retry decorators on individual tests or actions?
- Do reruns mask flakes (test passes on rerun 2, ships as green) without alerting?

Counts as real:
- "`pytest.ini:8` sets `--reruns 3 --reruns-delay 2`; a test that fails on first attempt 30% of the time still reports green. This is the only flake signal disappearing."
- "Custom `@retry(times=5)` on `OrdersPage.create_order` in `pages/orders.py:120` hides the underlying race in the order-creation endpoint."

### Failure visibility

Questions:
- On failure, can on-call / SDET see: the last URL, the last action attempted, the request/response, a screenshot, browser console, server logs?
- Does the suite attach artifacts to CI (screenshots, HAR, logs) on failure only, or always?

Counts as real:
- "`conftest.py` defines no `pytest_runtest_makereport` hook; failures produce only the assertion line — no screenshot, no DOM dump, no URL. Triage requires re-running locally."

---

## Maintainability

The question this critic answers: *what will hurt the next SDET trying to add or change a test here?*

### Page object / API client discipline

Questions:
- Is there a base class with a clear contract (waits, root URL, navigation, auth)? Do leaves follow it?
- Do page objects expose **actions and assertions**, or do they leak raw `WebElement` / `Response` objects to tests?
- Are tests doing waits or finds directly (bypassing the layer)?
- For API clients: are tests assembling URLs / headers themselves, or going through the client?

Counts as real:
- "`pages/base.py:1` defines `BasePage` with `wait_for_loaded`; `pages/billing.py:1` does not inherit and re-implements waits inline — adding a new page requires copying the inline pattern."
- "`tests/test_billing.py:42` does `driver.find_element(By.CSS, '.cell')` directly, bypassing `BillingPage`. Half the tests do this; the page object is fictional."

### Locator strategy

Questions:
- Are locators consistent across page objects (data-testid? CSS? XPath?) or a mix?
- Are locators defined as class constants / in a locator module, or scattered inline?
- Are XPaths brittle (position-based: `//div[3]/span`)?
- Do the same UI elements have different locators in different page objects?

Counts as real:
- "`pages/orders.py:88` and `pages/billing.py:42` both target the table row — one with `By.XPATH '//tr[2]'`, the other with `By.CSS 'tr[data-testid=row]'`. A component refactor will silently break only one."
- "Locators are inlined throughout `pages/`; renaming a `data-testid` requires grep + manual review across 14 files."

### Fixture sprawl and duplication

Questions:
- Are there N near-identical fixtures (`logged_in_user`, `logged_in_admin`, `logged_in_billing_user`) that could be parameterized?
- Are conftests at the wrong nesting level (overly broad, polluting unrelated tests)?
- Are autouse fixtures doing work the test doesn't need?

Counts as real:
- "`conftest.py` defines `user_a`, `user_b`, `user_c` that differ only in role — adding a fourth role requires a fourth fixture plus updates in 3 places."
- "Autouse `reset_state` in top-level `conftest.py:55` runs before every API test even though only UI tests need it, adding ~800ms per test."

### Helpers and shared utilities

Questions:
- Are helpers single-purpose and discoverable (one module per concern), or a junk drawer (`utils.py` with 40 functions)?
- Are helpers tested? (Test code that other test code depends on, untested, is high-risk.)
- Are there parallel implementations of the same idea in different helper files?

Counts as real:
- "`helpers/utils.py` is 600 lines with 38 unrelated functions; adding a new helper requires reading the whole file to avoid duplication."
- "`helpers/dates.py:format_iso` and `helpers/api.py:format_timestamp` produce the same string; tests use one or the other unpredictably."

### Test naming and structure

Questions:
- Do test names describe the behavior under test (`test_creating_invoice_with_no_lines_returns_400`) or just the function under test (`test_create_invoice`)?
- Is Arrange-Act-Assert structure visible, or are tests a wall of mixed setup and assertions?
- Are tests parametrized where they should be, or copy-pasted N times with one value changed?

Counts as real:
- "`tests/test_billing.py` has 6 tests named `test_billing_1`..`test_billing_6` — failure messages give no signal about what broke."
- "`test_create_user_valid_email`, `test_create_user_invalid_email`, `test_create_user_empty_email` are three copies of the same test body with different inputs; should be parametrized."

### Documentation and discoverability

Questions:
- Is there a top-level README that tells a new SDET how to run the suite, where things live, how to add a test?
- Are non-obvious fixtures documented at their definition?
- Are skip / xfail markers commented with the reason and ticket?

Counts as real:
- "`@pytest.mark.skip` at `tests/test_billing.py:8` has no comment — no one knows whether to re-enable it."
- "No README in `tests/`; a new SDET cannot find the page object root or the test data factory without grep."

---

## How to weight findings

- **P1** — concrete flake or false-signal risk that affects merge safety, or a maintenance trap that blocks near-term work
- **P2** — design smell that will produce flakes under specific conditions, or cost meaningfully more time per test added
- **P3** — worth knowing about, low cost to leave, low cost to fix

A finding is at most P3 if you cannot name a concrete scenario where it bites.
