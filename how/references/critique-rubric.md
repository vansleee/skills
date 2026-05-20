# Critique rubric

Use this rubric to apply your assigned focus area to the explanation. Each section lists the questions a critic in that focus should ask and the kinds of findings that count as real.

A finding is real only if you can name a concrete failure mode, change scenario, or operational risk. "I would have done it differently" is not a finding.

---

## Coupling and boundaries

Questions:
- Where do modules reach across boundaries they don't own (private fields, internal helpers, cross-layer imports)?
- Which type/interface, if changed, forces edits in N unrelated places?
- Where does business logic live in the wrong layer (route handlers doing domain work, UI doing transport, models doing persistence concerns)?
- Where is shared mutable state hidden as a singleton, module-level variable, or context that callers don't see?
- Are dependencies pointing the right way (high-level → low-level, not the reverse)?

Counts as real:
- "`PaymentService` depends on `UserRepository` internals; a schema rename breaks N call sites."
- "Route handler at `routes/checkout.ts:50` instantiates the domain entity directly, bypassing the validation in `Order.create()`."
- "Module-level `cache` in `services/pricing.ts` survives between requests; test order matters."

Does not count:
- "Should use dependency injection." — without a concrete scenario.
- "Coupling is high." — without naming the coupling.

---

## Failure modes and resilience

Questions:
- What happens when each external call fails (timeout, 5xx, partial response, malformed payload)?
- Are retries idempotent? Are they bounded? Do they back off?
- Where can the system end up in a partially-applied state (DB write succeeds, downstream call fails)?
- What does the user see when each failure happens? What does on-call see?
- Are there silent failures — caught exceptions that swallow context, fallbacks that hide errors?
- Concurrency: are there read-modify-write sequences without a lock or transaction?

Counts as real:
- "`sendInvoice` writes to DB then calls Stripe; if Stripe times out, DB row says 'sent' but nothing was sent — no reconciliation."
- "Retry loop at `worker/email.ts:120` has no upper bound; a permanently failing message will retry forever."
- "`catch (e) { logger.warn(e) }` at `api/users.ts:88` — the request returns 200 with no user created."

Does not count:
- "Should add more error handling." — without a specific path.
- "Could use a circuit breaker." — without a concrete failure to break on.

---

## Extensibility and change-amplification

Questions:
- For each plausible near-term change (new payment method, new event type, new tenant, new platform), how many files would need to change?
- Where are concepts encoded as enums/switches that grow every time a new variant is added?
- Where are abstractions premature — adding indirection without a second concrete user?
- Where are abstractions missing — the same pattern duplicated across files?
- How testable is the seam where extension would happen?

Counts as real:
- "Adding a new payment provider requires edits to `enum PaymentMethod`, `paymentDispatch` switch, `validatePayment`, `serializePayment`, and 3 tests."
- "`NotificationFactory` abstracts a single concrete type — the abstraction has no second user, just adds indirection."
- "Three near-identical `format*Address` functions in `utils/`; the next address format will become a fourth."

Does not count:
- "Should be more flexible." — without naming the next change.
- "Could be more abstract." — adding abstraction without a concrete second user is the failure mode, not the fix.

---

## Performance and resource use

Questions:
- N+1 patterns: loops that query, render, or fetch per item?
- Synchronous work on a request path that could be deferred?
- Allocations or copies in a hot loop?
- Caches without invalidation, or invalidation without correctness reasoning?
- Resources (DB connections, file handles, subscriptions) that aren't released on the error path?

Counts as real:
- "`getUsersWithOrders` calls `findOrders(user)` per user in a loop — N+1 across the user list."
- "Request handler `GET /feed` reads the entire `posts` table into memory then filters in JS."
- "WebSocket connection in `client/realtime.ts:140` is opened in `useEffect` but never closed on unmount."

Does not count:
- "Could be faster." — without measurement or a specific path.
- "Should use Redis." — solution-shopping without the problem.

---

## Observability and debuggability

Questions:
- When this breaks in production, what does the on-call engineer see?
- Are errors logged with the context needed to act (request id, user id, the inputs that triggered the failure)?
- Are metrics on the right things (success rate, latency percentiles, queue depth) or just on what's easy?
- Can you reconstruct a user's session from logs?
- Is there a way to safely reproduce a production failure locally?

Counts as real:
- "All `webhook` errors log only the exception class — no request body, no source IP, no retry count. Triage requires DB queries."
- "Latency metric is mean only; p99 spikes are invisible."

Does not count:
- "Needs more logging." — without naming the missing context.

---

## How to weight findings

- **P1** — concrete bug, outage risk, security issue, or change pattern that will block a near-term roadmap item.
- **P2** — design smell that will cost meaningfully more time per change, or hide bugs in future.
- **P3** — worth knowing about, low cost to leave, low cost to fix.

A finding is at most P3 if you cannot name a concrete scenario where it bites.
