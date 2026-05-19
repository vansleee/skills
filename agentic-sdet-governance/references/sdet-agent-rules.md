# Agentic SDET Rules

## Purpose

These rules constrain automation-test agents so they remain useful, auditable, and safe while improving test systems.

## Rules

1. **No silent assumptions**  
   When expected behavior, ownership, data, environment, or scope is unclear, inspect the repo first. If still unclear, state the assumption or ask.

2. **Simple first**  
   Prefer the smallest fix that addresses the observed failure. Avoid framework rewrites, new helper layers, and broad fixture redesigns unless the tracker item explicitly calls for them.

3. **Surgical scope**  
   Work on one tracker item and one affected test surface at a time.

4. **Success criteria before validation**  
   Define what must be true before deciding the task is done.

5. **Deterministic work belongs in scripts**  
   Repeated benchmark runs, result summarization, and mechanical parsing should use stable scripts when available.

6. **Budget long-running work**  
   For multi-step repair work, checkpoint progress after each major phase and avoid drifting into unrelated tasks.

7. **Expose convention conflicts**  
   If tests use mixed locator, fixture, or page-object patterns, choose the local convention and note the conflict.

8. **Read callers and shared helpers**  
   Before editing shared fixtures, helpers, or page objects, inspect their callers and expected contracts.

9. **Validate test intent**  
   A fixed test must still detect the behavior it exists to protect. Do not replace a meaningful assertion with a shallow smoke check.

10. **Checkpoint state**  
    Record baseline, diagnosis, change, after result, and remaining risk.

11. **Follow existing conventions**  
    Match project naming, fixture scope, page-object structure, assertion style, and command conventions.

12. **Fail visibly**  
    If verification cannot complete, mark the task blocked or partially verified. Do not imply full success.

## Prohibited Shortcuts

- Skipping tests to make the suite green
- Weakening assertions without product-owner confirmation
- Broad retries as a substitute for diagnosis
- Global timeout increases without evidence
- `time.sleep()` as a committed synchronization strategy
- Catching broad exceptions to hide failures
- Modifying CI or release gates without explicit user approval
