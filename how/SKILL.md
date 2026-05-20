---
name: how
description: >-
  Explain how a subsystem, feature, or flow works in this codebase, at the level of a senior engineer onboarding to a new area. Trigger with "how does X work", "walk me through Y", "explain the architecture of Z", "/how", or any time the user asks for a structured explanation of product code. Add "and critique it" / "也幫我 critique" to run an architectural review pass after the explanation.
---

# how

Explain product code by exploring the repo and producing a structured, senior-engineer-grade walkthrough. Optionally critique the architecture.

Adapted from [poteto/how](https://github.com/poteto/how) for Claude Code / Cowork. Targets **product source code**. For test code, use `how-to-test` instead.

## Modes

Two modes, picked automatically from the question:

- **Explain** (default) — explore the codebase and produce a structured explanation with five sections: Overview, Key Concepts, How It Works, Where Things Live, Gotchas.
- **Critique** — run Explain first, then spawn independent critics to surface architectural problems against the rubric.

Critique is triggered when the user says any of: "critique", "review the design", "also critique", "找出問題", "幫我 critique", "design review", "what's wrong with this design".

## Routing — simple vs. complex

Before exploring, decide simple or complex.

**Simple** (skip fan-out, single agent end-to-end):
- Localized to one file or one tight cluster of files.
- Asks about a single function, class, hook, middleware, or small flow.
- Examples: "How does the auth middleware check permissions?", "What does `useChannelPresence` do?", "Where is the rate limiter implemented?".

**Complex** (decompose, fan out 2–4 explorer subagents in parallel, then synthesize):
- Spans multiple files, services, layers, or boundaries.
- Asks about a flow that crosses concerns (frontend ↔ backend, request lifecycle, data pipeline, multi-step process).
- Examples: "How does message virtualization work?", "Walk me through what happens when a user sends a message", "How is the billing service structured?".

When in doubt, treat as complex. Fan-out adds latency but rarely produces worse output.

## Workflow

### Step 1 — Read the prompts

Read `references/explainer-prompt.md`. If the question is complex, also read `references/explorer-prompt.md`. If critique is requested, also read `references/critic-prompt.md` and `references/critique-rubric.md`.

### Step 2 — Locate the entry point

Use `Glob` / `Grep` / `Read` to find the entry point named in the question (file, symbol, route, component). If the question names something that does not exist verbatim, search semantically (e.g., "message virtualization" → look for `virtuali`, `windowing`, `IntersectionObserver`, list components).

If you cannot find any entry point after 3 search attempts, ask the user for a hint instead of guessing — wrong entry point = wrong explanation.

### Step 3a — Simple path

Follow `references/explainer-prompt.md`. Read the entry point and its immediate collaborators. Produce the five-section output. Done.

### Step 3b — Complex path (fan-out)

1. Decompose the question into 2–4 **non-overlapping exploration angles**. Examples for "how does message sending work":
   - Client-side input → optimistic update → request dispatch
   - Server-side request handling → persistence → fan-out to subscribers
   - Real-time delivery (websocket / pubsub) → client receive → reconciliation
   - Failure paths (retry, dedupe, offline queue)

   Keep angles **orthogonal**. If two angles would read the same files, merge them.

2. For each angle, spawn one explorer subagent in parallel using the `Agent` tool (subagent_type `Explore` or `general-purpose`). Pass it `references/explorer-prompt.md` and the specific angle. Send all spawns in **a single message with multiple tool calls** so they run concurrently.

3. After all explorers return, act as the synthesis agent: reconcile their findings, resolve contradictions by re-reading the relevant files yourself, and produce the five-section output. Do not concatenate the subagent reports verbatim — synthesize.

### Step 4 — Critique pass (only if requested)

After the explanation is complete, spawn 2–3 critics in parallel via `Agent`. Each critic receives:
- The explanation produced in step 3
- `references/critic-prompt.md`
- `references/critique-rubric.md`
- One assigned focus area (e.g., "coupling and boundaries", "failure modes and resilience", "extensibility and change-amplification")

Use **different models** where possible (e.g., `model: "opus"` for one, default for another) — independent perspectives are the point. Send all spawns in one message.

After critics return, deduplicate findings and present them as a Critique section appended to the explanation, ordered by severity.

## Output format

Always exactly these five sections, in this order, with `##` headings:

```
## Overview
1–3 sentences. What this subsystem does and why it exists.

## Key Concepts
The vocabulary a reader needs before the rest makes sense. Define each in one line.

## How It Works
The actual mechanism. Walk through the flow. Reference real file paths and symbols.
Use a numbered list for sequential steps. Use prose for the rest.

## Where Things Live
Map concept → file path. One line per entry. Skip the obvious.

## Gotchas
Non-obvious behaviors, footguns, historical reasons, places the abstraction leaks.
This section is the highest-value one — do not skip it.
```

If critique was run, append:

```
## Critique
Findings ordered by severity (P1 → P3), deduplicated across critics.
Each finding: one-line claim, brief evidence (file:line), suggested direction.
```

## Guardrails

- **Never invent files, symbols, or behavior.** If you have not opened the file, do not claim what it does. Re-read before asserting.
- **Cite real paths.** Every claim in "Where Things Live" and "How It Works" must reference a real `path/to/file.ext` from this repo.
- **Prefer evidence over restatement.** "The middleware extracts the token at `auth/middleware.ts:42`" beats "the middleware extracts the token".
- **Do not paste large code blocks.** Quote the smallest revealing snippet (≤6 lines). The reader can open the file.
- **Do not fan out for simple questions.** Latency and noise without payoff.
- **Critique is opt-in.** Do not critique unless the user asked.

## When not to use this skill

- The user wants to **write or change** code → use the appropriate engineering skill.
- The user wants to explain **test code** → use `how-to-test` instead.
- The user wants a one-line answer to a factual code question → just answer.
