---
name: ntdst-execute-with-tests
description: Use when executing a written implementation plan in a Netdust project — wraps superpowers:executing-plans and superpowers:subagent-driven-development with mandatory testing-workflow gates. Triggers on "execute the plan", "implement the plan", "run subagents on this plan", "work the plan", "start building", "execute todo.md", "build out the plan", "run this plan". Required for any plan execution in WordPress, Statamic, or Bun projects under this harness.
---

# Execute With Tests — Netdust plan execution wrapper

Plain `superpowers:executing-plans` and `superpowers:subagent-driven-development` do not enforce `testing-workflow`. In this harness, that's a regression — `testing-workflow` exists precisely to gate task/phase sign-off with real tests, but upstream skills never reference it. This skill is the front door that wires them together.

## When to use

- Any time you're about to invoke `superpowers:executing-plans` or `superpowers:subagent-driven-development` in a Netdust project (WordPress, Statamic, Bun, plain HTML).
- After `superpowers:writing-plans` produces a plan file and you're ready to build.
- Trigger phrases: "execute the plan", "implement the plan", "run subagents on this plan", "work the plan", "start building", "execute todo.md", "build out the plan".

**Do not use when:**
- No plan exists yet → use `superpowers:brainstorming` then `superpowers:writing-plans`.
- One-off bug fix with no plan → use `superpowers:systematic-debugging` + `testing-workflow` directly.
- Already mid-build inside `superpowers:executing-plans` → invoke `testing-workflow` directly at the next task boundary.

## What this skill does

It's a sequencer with three mandatory steps and no shortcuts.

### Step 1 — Load the upstream execution skill

Pick one based on the plan shape:

| Plan shape | Skill to invoke |
|---|---|
| Independent tasks suitable for parallel subagents | `superpowers:subagent-driven-development` |
| Sequential tasks needing shared context, or single agent | `superpowers:executing-plans` |

Invoke it via the Skill tool. Follow its checklist exactly. Do not deviate from upstream discipline.

### Step 2 — Gate every task with testing-workflow

```
NON-NEGOTIABLE:
Every task is considered "in progress" until testing-workflow has been invoked
for it and reports green. Not "I ran the tests" — invoked via the Skill tool.
```

The pattern per task:

1. Subagent (or you, if single-agent) implements the task.
2. Before marking the task done, invoke `Skill("testing-workflow")` with the task description as context.
3. `testing-workflow` produces the task-complete checklist. Walk it.
4. Only after all boxes are checked does the task get marked complete.

**For parallel subagents:** append the **ready-to-paste dispatch-prompt template** below to every Agent-tool prompt. Copy verbatim — do not summarize or paraphrase. This is the load-bearing language that makes the discipline auditable.

```
---

## Mandatory close-out for this task

Before reporting STATUS, you MUST:

1. Invoke `Skill("netdust-core:testing-workflow")` via the Skill tool. Walk
   the task-complete checklist it produces, in your transcript.
2. Run the affected app's full unit suite from the app's directory (NOT from
   the repo root). Confirm test count delta matches the plan's expectation.
3. Run static analysis on the touched files. For TS: `bun x tsc --noEmit`
   from the affected app's directory.
4. End your final message with this block, verbatim and complete:

   ## Test evidence
   - Test file(s): <list of paths touched>
   - RED proof: <command you ran> → <1-3 line snippet showing the test failed>
   - GREEN proof: <command you ran> → <1-3 line snippet showing the test passed>
   - Suite delta: <app> was <N>, now <M>, <K> fails
   - Typecheck: <command> → <clean | errors>

   ## STATUS
   STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
   COMMIT: <sha>
   FILES TOUCHED: <list>
   DIVERGENCES FROM PLAN: <list, or "matched plan verbatim">

Missing any item in either block = task NOT done. Do not rationalize. Do not
substitute prose for the structured form. The structure is what makes the
audit possible.

---
```

The block above MUST appear at the bottom of every subagent dispatch prompt for any code-touching task. Doc-only and tooling-only tasks may omit the test evidence block but MUST still include the STATUS block.

The SubagentStop hook (netdust-core) detects when a subagent finishes without having invoked `testing-workflow` and will surface a reminder. That reminder is a backstop, not the primary mechanism — **the dispatch prompt is**. Skipping the verbatim block above breaks the discipline at the source; the hook only catches what the prompt failed to enforce.

### Calibration data behind this template

The verbatim template was hardened by retros from real harness runs:

- **Folio Phase 3 Sub-phase A** (2026-05-28): 7 tasks shipped with the earlier weaker version of this template ("you MUST invoke Skill..." as a one-liner). Result: across all 7 task dispatches, ZERO subagents actually invoked `Skill("netdust-core:testing-workflow")` — they internalized the TDD discipline via the dispatch-prompt prose but bypassed the invocation gate. The discipline held by other means (RED→GREEN cycles + test-count deltas) but the audit trail was unverifiable. The `/evaluate` retro flagged this as Gap #5: "skill-invocation contract bypassed."
- The fix: make the invocation a literal structured demand with a structured response shape (the Test evidence + STATUS blocks above). A subagent that returns the structured form has, in producing it, also done the invocation. A subagent that returns prose has skipped both.

If the structured form starts to feel like "ceremony," that's a sign it's working — subagents that find it onerous to produce it are subagents that would otherwise skip it.

### Step 3 — Gate every phase with testing-workflow

After all tasks in a phase complete:

1. Invoke `Skill("testing-workflow")` again, this time with the phase description.
2. Walk the phase-complete checklist (integration + acceptance tests).
3. Only after phase sign-off proceed to the next phase, or to `shake-out`.

### Step 4 — Hand off

When the plan is complete:

1. Invoke `Skill("netdust-core:shake-out")` (or the stack-specific override, e.g. `netdust-statamic:shake-out-statamic`). This is the QA phase that catches what unit/integration tests don't.
2. After shake-out: invoke `superpowers:finishing-a-development-branch`.

## Boundary with testing-workflow

`testing-workflow` is a discipline skill — it tells you what to test and how. This skill is a sequencer — it tells you **when** to invoke testing-workflow. Keep them separate:

- This skill: orchestration, ordering, handoff between upstream skills.
- testing-workflow: the actual test discipline (unit / integration / acceptance, fix loop, anti-patterns).

If you find yourself copying testing-workflow content into this skill, stop. Invoke testing-workflow instead.

## Boundary with shake-out

| Phase | Owner |
|---|---|
| Build loop (per task + per phase) | This skill + testing-workflow |
| Post-build QA in real environment | shake-out |
| Branch close-out | superpowers:finishing-a-development-branch |

testing-workflow has already proven the contracts known at plan time. shake-out finds what plan time missed. Do not re-run the full test suite during shake-out's Phase 1 sweep — assume it's green from the phase-complete gate.

## Red flags

Stop immediately if you catch yourself:

- "I'll skip testing-workflow for this task, it's trivial" — trivial tasks still need a unit test.
- "The subagent already ran the tests, no need to invoke the skill" — invocation is what makes it auditable. The hook checks for it.
- "We'll add integration tests at the end" — phase gate exists so this doesn't happen.
- Marking a task complete without the task-complete checklist visible in the transcript.

## Integration

| Skill | Relationship |
|---|---|
| `superpowers:executing-plans` | **WRAPPED.** Invoked in Step 1 for sequential plans. |
| `superpowers:subagent-driven-development` | **WRAPPED.** Invoked in Step 1 for parallel plans. |
| `testing-workflow` (netdust-core) | **MANDATORY GATE.** Invoked per task and per phase. |
| `shake-out` (netdust-core) | **DOWNSTREAM.** Invoked after the plan completes. |
| `superpowers:finishing-a-development-branch` | **DOWNSTREAM.** Invoked after shake-out. |
| netdust-core `subagent-stop.py` hook | **BACKSTOP.** Detects missing testing-workflow invocations. |
