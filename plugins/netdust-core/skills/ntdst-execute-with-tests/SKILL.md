---
name: ntdst-execute-with-tests
description: Use when executing a written implementation plan in a Netdust project — wraps superpowers:executing-plans and superpowers:subagent-driven-development with mandatory testing-workflow gates. Triggers on "execute the plan", "implement the plan", "run subagents on this plan", "work the plan", "start building", "execute todo.md", "build out the plan", "run this plan". Required for any plan execution in WordPress, Statamic, or Bun projects under this harness.
---

<objective>
Wrap the chosen superpowers execution skill with two additions the upstream skills do not provide: (1) mandatory invocation of `netdust-core:testing-workflow` at every task close, and (2) a structured Test-evidence + STATUS block at the end of every subagent's report so the discipline is auditable from the transcript, not honor-system.

Everything else — TDD, two-stage review, dispatch shape, status handling, escalation — belongs to the upstream skill. Do not duplicate upstream content here.
</objective>

<extremely_important>
This skill is a sequencer with one job: load the right upstream skill, then add the netdust-specific addendum to every dispatch. It is NOT a place to think about execution shape, do pre-flight checks, run grep/ls, or improvise.

If you find yourself running Bash, Read, or Grep in the controller session BEFORE invoking the upstream skill in step 1 of `<process>` below, **stop**. That is the upstream skill's job, or a subagent's job, never yours. Pre-flight reasoning before the upstream invocation is the exact failure mode this skill exists to prevent. See `<red_flags>`.
</extremely_important>

<intake>
Before any other action, answer this question in your transcript (one sentence, explicit):

**Which upstream skill does this plan need?**

| Plan shape | Upstream skill |
|---|---|
| Independent tasks suitable for parallel subagents (most common) | `superpowers:subagent-driven-development` |
| Sequential tasks needing shared context, or solo execution | `superpowers:executing-plans` |

You must state your choice and one-sentence reason before proceeding. Examples:

> "Sub-phase B's 8 tasks are mostly independent (B-2/B-3/B-5/B-7 can parallelize after B-1), so I'm using subagent-driven-development."
>
> "This is a 3-task refactor where each task builds on the previous file structure, so I'm using executing-plans."

If you cannot pick, the plan is ambiguous — ask your human partner. Do not improvise.
</intake>

<process>

**Step 1 — Invoke the upstream skill.** Use the Skill tool. Follow its checklist EXACTLY. Its content is your primary instruction set from here on; this skill is only an addendum.

**Step 2 — Apply the netdust addendum to every dispatch prompt.** For each subagent dispatch the upstream skill produces (implementer, spec reviewer, code-quality reviewer), append the block below VERBATIM to the prompt body. Do not summarize, paraphrase, or selectively include.

See `<addendum_for_dispatch>` below.

**Step 3 — Gate every task close on testing-workflow.** A task is not done until:
1. The subagent's report ends with the structured Test-evidence + STATUS blocks defined in the addendum.
2. The subagent has invoked `Skill("netdust-core:testing-workflow")` in its transcript.

If either is missing, treat the task as DONE_WITH_CONCERNS or NEEDS_CONTEXT (depending on which is absent) per the upstream skill's status handling. Do not mark complete without both.

**Step 4 — Phase-close handoff.** After all tasks in a phase complete, follow the upstream skill's final-review step. Then invoke `Skill("netdust-core:shake-out")` (or stack-specific override like `netdust-statamic:shake-out-statamic`). Then `superpowers:finishing-a-development-branch`.

</process>

<addendum_for_dispatch>

Append this block VERBATIM at the bottom of every implementer dispatch prompt. It supplements (does not replace) the upstream `implementer-prompt.md` template.

```
---

## Netdust addendum — mandatory close-out

Before reporting STATUS, you MUST:

1. Invoke `Skill("netdust-core:testing-workflow")` via the Skill tool.
   Walk the task-complete checklist it produces. The invocation itself —
   not the prose summary — is what makes this gate auditable.

2. Run the affected app's full unit suite from the APP's directory
   (never from repo root). Confirm the test-count delta matches the
   plan's expectation.

3. Run static analysis on touched files. For TypeScript:
   `bun x tsc --noEmit` from the affected app's directory.

4. End your final message with these two blocks, verbatim and complete:

   ## Test evidence
   - Test file(s): <list of paths touched>
   - RED proof: <command you ran> → <1-3 line snippet showing fail>
   - GREEN proof: <command you ran> → <1-3 line snippet showing pass>
   - Suite delta: <app> was <N>, now <M>, <K> fails
   - Typecheck: <command> → <clean | errors>

   ## STATUS
   STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
   COMMIT: <sha>
   FILES TOUCHED: <list>
   DIVERGENCES FROM PLAN: <list, or "matched plan verbatim">

Missing any item in either block = task NOT done. Do not rationalize.
Do not substitute prose for the structured form. The structure is what
makes the audit possible.

---
```

For **doc-only or tooling-only tasks** (no code-touching changes), the implementer may omit the Test evidence block but MUST still include the STATUS block.

For **reviewer subagents** (spec compliance, code quality), only the STATUS block is required — they do not run tests themselves.

</addendum_for_dispatch>

<red_flags>

These thoughts mean you are about to skip the upstream skill. Stop.

| Thought | Reality |
|---|---|
| "Let me think about execution shape before invoking the upstream skill" | The upstream skill IS how you think about execution shape. Invoke it first. |
| "I'll do a quick pre-flight grep before dispatching" | Pre-flight belongs to the controller's coordination work, AFTER the upstream skill is loaded. Not before. |
| "I already know what subagent-driven-development says" | Skills evolve. Invoke and read the current version every time. |
| "The wrapper is enough — I don't need the upstream" | The wrapper is an addendum. It only works on top of upstream content. |
| "Two-stage review feels like ceremony for a simple task" | The upstream skill's review loop catches what TDD doesn't. Do not skip it. |
| "Skipping the verbatim addendum saves a few lines" | The verbatim form is what closes the audit gap. Skipping it = reverting to honor-system, which is the failure mode this skill exists to prevent. |
| "I'll invoke testing-workflow after the commit, not before reporting" | The order is: invoke testing-workflow → walk checklist → report. The invocation is in the same transcript as the report, or the gate is bypassed. |

If you have read this far without invoking the upstream skill from `<process>` Step 1, your next action MUST be that invocation. Not "let me check one more thing."

</red_flags>

<success_criteria>

This skill has succeeded when:

1. The upstream skill (`subagent-driven-development` or `executing-plans`) was invoked via the Skill tool and its checklist was followed.
2. Every implementer subagent's dispatch prompt contained the verbatim addendum block.
3. Every implementer subagent's report ended with the structured Test-evidence + STATUS blocks.
4. Every implementer subagent's transcript shows an explicit `Skill("netdust-core:testing-workflow")` invocation.
5. Phase close handed off cleanly to `netdust-core:shake-out` and then `superpowers:finishing-a-development-branch`.

If any of (1)-(4) is missing, the wrapper failed at its specific job, even if the code shipped correctly. The wrapper exists for audit-trail durability, not for code correctness — the upstream skill is what handles code correctness.

</success_criteria>

<integration>

| Skill | Relationship |
|---|---|
| `superpowers:subagent-driven-development` | **WRAPPED — primary branch.** Invoked in `<process>` Step 1 for plans with parallel-independent tasks. |
| `superpowers:executing-plans` | **WRAPPED — secondary branch.** Invoked in `<process>` Step 1 for sequential or solo execution. |
| `superpowers:using-superpowers` | **OVERRIDDEN where they conflict** per `using-superpowers`'s own Instruction Priority — user/project rules (e.g. this skill's testing-workflow mandate) take precedence. |
| `netdust-core:testing-workflow` | **MANDATORY GATE.** Invoked by every implementer subagent at task close. The addendum forces this. |
| `netdust-core:shake-out` | **DOWNSTREAM.** Invoked at phase close after upstream's final-review. |
| `superpowers:finishing-a-development-branch` | **DOWNSTREAM.** Invoked after shake-out. |
| netdust-core `subagent-stop.py` hook | **BACKSTOP.** Detects when a subagent finished without invoking `testing-workflow` and surfaces a reminder. The reminder is a backstop, not the primary mechanism — the addendum is. |

**Calibration data behind the verbatim addendum:** Folio Phase 3 Sub-phase A (2026-05-28), 7 tasks shipped with a weaker one-liner version of the addendum. Zero of 7 subagents invoked `Skill("netdust-core:testing-workflow")` despite the prose instruction; discipline held by other means (RED→GREEN cycles, test-count deltas in commit messages, full-suite re-runs) but the audit trail was unverifiable from transcripts. The current structured addendum was hardened in response. See `~/Projects/folio/docs/superpowers/retros/2026-05-28-phase-3-sub-phase-A-retro.md` Gap #5.

</integration>
