---
description: Review a written plan with a fresh subagent before Stefan reads it — premises ground-truthed against source, coverage, invented scope, the simplest design. Writes specs/<feature>/plan-review.md naming the plan's blob; the guard refuses product code until it exists.
argument-hint: <feature>
allowed_tools: ["Bash", "Read", "Glob", "Write", "Agent"]
---

Review `specs/$ARGUMENTS/plan.md`. Three steps.

## Step 1 — The blob

```bash
git hash-object specs/$ARGUMENTS/plan.md
```

That sha is what the review names. A plan edited after its review has a new blob, and the
guard treats it as unreviewed — run this command again.

## Step 2 — Dispatch `plan-reviewer`

Dispatch the **`plan-reviewer`** agent on the most capable available model with: the plan
path, the spec path (`specs/$ARGUMENTS/spec.md`), the repository root, and the blob sha from
Step 1. It is read-only and returns the report; it never edits the plan.

You are not the reviewer. If you wrote this plan in this session, that is the point — the
reviewer's context is fresh and yours is not.

## Step 3 — File the report, then act on it

Write the returned report verbatim to `specs/$ARGUMENTS/plan-review.md`. Its second line
must be `Reviewed-plan: <sha>` — check it before writing; a report without it does not
satisfy the guard.

- **Blocking** findings: fix the plan now (it is yours to edit at this stage), then run
  `/plan-review` again — the new blob needs its own review.
- **Should fix**: fix them the same way unless the fix needs Stefan's ruling; then leave
  them in the report for him.
- **Note**: stays in the report.

Then hand the plan and the review to Stefan together, as `superpowers:writing-plans` says:
he reviews the saved plan and chooses the execution mode. The review travels with the plan;
he reads a plan that has already been checked.
