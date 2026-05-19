# Selenium Review Checklist

## Reliability

- Are waits explicit and tied to the right readiness condition?
- Can tests run independently and in any order?
- Are retries narrow and justified?
- Are failure artifacts captured?

## Locators

- Are selectors stable across layout and style changes?
- Are absolute XPath and index-based selectors avoided?
- Are page-object names user-intent oriented?

## Assertions

- Do assertions prove meaningful user-visible behavior?
- Are product regressions still observable?
- Were assertions weakened to pass?

## Fixtures and Data

- Is mutable data function-scoped or isolated?
- Is teardown idempotent?
- Does browser/session reuse leak state?

## Red Flags

- `time.sleep`
- broad `except Exception`
- global timeout increase
- unconditional skip
- forced JavaScript click without justification
- order-dependent tests
