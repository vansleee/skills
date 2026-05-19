# Pytest + Selenium Guidelines

## Locators

- Prefer stable test attributes such as `data-testid`, `data-test`, or `data-qa`.
- Use semantic attributes such as accessible names, labels, stable `id`, and `name` when test attributes are unavailable.
- Use CSS selectors only when they describe stable structure.
- Treat XPath as a last resort; avoid absolute XPath and index-heavy paths.
- Page-object methods should describe user intent, not DOM mechanics.

## Waits

- Prefer `WebDriverWait` with explicit expected conditions.
- Wait for the condition the user actually needs: clickable element, visible result, URL change, text present, loading indicator gone, or persisted state visible.
- Avoid `time.sleep()` in committed test code.
- Avoid using implicit waits as the main synchronization strategy.
- Do not increase global timeouts without evidence that the product intentionally takes longer.

## Assertions

- Assert business-visible outcomes.
- Keep assertions close to the behavior under test.
- Avoid no-op assertions such as asserting a returned WebElement exists after Selenium already found it.
- Do not loosen assertions merely to make a test pass.

## Fixtures and Isolation

- Use function-scoped fixtures for mutable browser state and test data.
- Use broader-scoped fixtures only for immutable or explicitly cleaned setup.
- Make teardown idempotent and safe after partial setup failure.
- Keep login/session reuse explicit and documented.
- Avoid tests that depend on execution order.

## Failure Evidence

Capture the pytest command, failing node IDs, exception class, failure message, screenshots, browser logs, HTML dumps, CI job URL, and rerun count when available.

Classify failures as locator, stale element, timing, assertion mismatch, test data, setup/teardown, fixture isolation, environment/browser/grid, product regression, cascade, or unknown.

## Anti-Patterns

- `time.sleep`
- broad `except Exception`
- forced JavaScript clicks without a comment explaining why a real click cannot work
- blanket retries
- skipped tests without a tracker item
- selectors tied to CSS framework classes
- shared mutable state across tests
