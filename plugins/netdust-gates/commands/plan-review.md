---
description: Review a written plan — or every plan a spec was cut into — with a fresh subagent before Stefan reads it — premises ground-truthed against source, coverage, invented scope, the simplest design, and the cut. Writes plan-review.md naming each plan's blob.
argument-hint: <feature | topic>
allowed_tools: ["Bash", "Read", "Glob", "Write", "Agent"]
---

Review `specs/$ARGUMENTS/plan.md` — or, when `specs/$ARGUMENTS/` holds a spec and no plan,
the set of plans whose `**Spec:**` header names `specs/$ARGUMENTS/spec.md`
(`grep -lE "Spec:\**[[:space:]]*\`?specs/$ARGUMENTS/spec\.md" specs/*/plan.md`). Three steps.

## Step 1 — The blob

```bash
git hash-object specs/$ARGUMENTS/plan.md     # or each plan of the set
```

Each sha is what the review names. A plan edited after its review has a new blob — run this
command again when the change matters.

## Step 2 — Dispatch `plan-reviewer`

Dispatch the **`plan-reviewer`** agent on the most capable available model with: the plan
path (every plan path, for a set, with its sha), the spec path, the repository root, and the
blob sha from Step 1. A set is one dispatch, never one per plan — the cut is only visible whole. It is read-only and returns the report; it never edits the plan.

You are not the reviewer. If you wrote this plan in this session, that is the point — the
reviewer's context is fresh and yours is not.

## Step 3 — File the report, then act on it

Write the returned report verbatim to `specs/$ARGUMENTS/plan-review.md`. Its second line
must be `Reviewed-plan: <sha>` — one such line per plan for a set, each followed by the plan's
path — check it before writing.

- **Blocking** findings: fix the plan now (it is yours to edit at this stage), then run
  `/plan-review` again — the new blob needs its own review.
- **Should fix**: fix them the same way unless the fix needs Stefan's ruling; then leave
  them in the report for him.
- **Note**: stays in the report.

Then hand the plan and the review to Stefan together, as `superpowers:writing-plans` says:
he reviews the saved plan and chooses the execution mode. The review travels with the plan;
he reads a plan that has already been checked.
