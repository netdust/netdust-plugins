---
description: Review the work of a build session on demand — task reports, rulings, plan and diff checked against the real source on six dimensions, core fit included; security-sentinel when the review says so. Reports only. Nothing is fixed until Stefan approves.
argument-hint: <feature>
allowed_tools: ["Bash", "Read", "Glob", "Write", "Agent"]
---

Review the work done for `specs/$ARGUMENTS/`. You coordinate; you do not review it yourself,
and you change no code in this command.

## Step 1 — Gather the paths

- The feature directory `specs/$ARGUMENTS/` (spec, plan, plan-review, shakeout manifest).
- The task-report workspace: `.superpowers/sdd/<plan-basename>/`. Superpowers deletes it once
  a branch is finished — if it is gone, say so; the review works from the plan and the diff.
- The range: `git merge-base <production branch> HEAD`..`HEAD`, the production branch read
  from `site.yml` (`environments.production.branch`), else `main`.

Run it before `superpowers:finishing-a-development-branch` when you can: the task reports are
the best evidence the review gets.

## Step 2 — Dispatch `session-reviewer`

On the most capable available model, with the four paths above and the repository root. It
is read-only and returns the report. Then read its `Security review:` line: on `required`,
dispatch `security-sentinel` on the same range with the reviewer's security findings and the
plan's `## Threat model` if there is one.

## Step 3 — File and present, then stop

Write the report (and the sentinel's, appended under `## Security`) verbatim to
`specs/$ARGUMENTS/session-review.md`. Show Stefan the Critical and Important findings and the
core-fit classes, and give the path.

**Stop there.** Stefan approves which findings are acted on. Nothing is edited, fixed,
parked or committed on the review's say-so. On his approval: each approved behaviour finding
is one fix, RED→GREEN; a `CORE_GAP` or `WRONG_LAYER` finding is not fixed in the feature
branch — it changes the framework, so it goes to `memory/STATE.md` with its evidence unless
he says otherwise.
