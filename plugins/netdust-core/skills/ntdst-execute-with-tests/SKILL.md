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

**For parallel subagents:** include this instruction in the dispatch prompt verbatim:

> Before reporting this task complete, you MUST invoke `Skill("testing-workflow")` via the Skill tool and complete its task-complete checklist. A task without unit tests is not done. Do not report success without invoking the skill.

The SubagentStop hook (netdust-core) detects when a subagent finishes without having invoked `testing-workflow` and will surface a reminder. That reminder is a backstop, not the primary mechanism — the dispatch prompt is.

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
