# Failure Taxonomy

## Locator

Symptoms: `NoSuchElementException`, empty element lists, selector works only on one viewport, element renamed or moved.

Next evidence: screenshot, HTML dump, selector search, product diff.

## Stale Element

Symptoms: `StaleElementReferenceException`, DOM rerender after locating.

Next evidence: rerender timing, framework lifecycle, page-object caching.

## Wait or Timing

Symptoms: `TimeoutException`, passes with sleep, fails under load, element present but not clickable.

Next evidence: loading indicators, network-backed result, explicit condition mismatch.

## Assertion Mismatch

Symptoms: Selenium steps succeed but expected text/state differs.

Next evidence: expected product behavior, recent app diff, test data state.

## Test Data

Symptoms: duplicate data, missing account/org/project, cleanup collision, shared environment contamination.

Next evidence: setup logs, API responses, database/test data records.

## Fixture Isolation

Symptoms: order-dependent failures, state leaks between tests, local parallelism fails while serial CI passes.

Next evidence: fixture scopes, browser/session reuse, xdist/parallel settings.

## Environment

Symptoms: browser/grid failures, driver mismatch, CI-only or local-only infrastructure issue.

Next evidence: browser version, driver version, grid logs, resource constraints.

## Product Regression

Symptoms: user-visible behavior changed and manual or lower-level tests confirm it.

Next evidence: recent app diff, manual reproduction, API response changes.

## Cascade

Symptoms: many tests fail after one setup failure or serial suite stop.

Next evidence: first failure in chronological output.
