---
description: Phase-boundary gate. Run after finishing a group of related tasks (sub-phase / task cluster) before starting the next group. Stack-agnostic — detects project type and runs unit + integration + type-check, then announces the code-review the user should run on the group's diff.
allowed_tools: ["Bash", "Read", "Glob"]
---

Run the **phase-boundary gate**. This fires when a task group is done (sub-phase A before B starts) — not when the whole spec is done. For spec-complete, use `/shakeout`.

## What this gate is, in one line

> Prove the group composes before starting the next one. Catch cross-task regressions while the diff is still small.

## Step 1 — Detect the stack

Glob from repo root, in order:

| Marker | Stack | Test command | Type-check |
|---|---|---|---|
| `package.json` AND `bun.lockb` | Bun/TS | `bun test` (root, hits all workspaces if monorepo) | `bun --filter '*' run typecheck` if a `typecheck` script exists, else `bun x tsc --noEmit -p <each tsconfig.json>` |
| `package.json` AND `pnpm-lock.yaml` | Node/pnpm | `pnpm test` | `pnpm exec tsc --noEmit` |
| `package.json` AND no Bun/pnpm | Node/npm | `npm test` | `npx tsc --noEmit` |
| `composer.json` AND `codeception.yml` | PHP/WP/Codeception | `vendor/bin/codecept run unit` + `vendor/bin/codecept run integration` if suite exists. If `.ddev/` exists, prefix with `ddev exec`. | (skip — PHP) |
| `composer.json` AND `phpunit.xml*` | PHP/PHPUnit | `vendor/bin/phpunit` (or `ddev exec`) | (skip) |
| `composer.json` AND `artisan` | Laravel/Statamic | `php artisan test` (or `ddev exec`) | (skip) |

Cache the detection result in this run; don't re-detect.

If none match, stop and tell the user: "Couldn't detect project type. Run tests manually then continue."

## Step 2 — Determine the group diff range

The user runs `/integration` at the end of each task group. The "group" is `<last-integration-sha>..HEAD`.

1. Read `.claude/.last-integration` from the repo root. It contains a single SHA (the HEAD after the previous `/integration`).
2. If missing → group range = `$(git merge-base HEAD main)..HEAD` (since the branch diverged from main).
3. Capture `git rev-parse HEAD` into `NEW_SHA`. Save this for Step 4.
4. Compute the range string: `RANGE="${LAST}..HEAD"` (or the merge-base form).
5. Show the user: "Group diff: `<RANGE>` (N commits, M files changed)" via `git log --oneline RANGE` + `git diff --stat RANGE`.

## Step 3 — Run the gate

Execute, in order, halting on first failure and reporting the failure to the user:

1. **Type-check first** (if applicable). It's cheap and catches structural breaks fast. For Bun monorepos, run it per workspace:
   ```bash
   for ts in $(find . -name tsconfig.json -not -path './node_modules/*' -not -path '*/dist/*'); do
     echo "→ typecheck $ts"
     (cd "$(dirname "$ts")" && bunx tsc --noEmit) || exit 1
   done
   ```
2. **Unit + integration tests** using the command from Step 1. Run from repo root, not per workspace, unless the runner doesn't support that.
3. **Smoke** (cheap): nothing automatic here — listed as a manual checkbox in the announcement. The point of `/integration` is to catch what unit tests don't: cross-file wiring. Boot-smoke belongs at `/shakeout`.

If anything fails: print the failing output, **do not** update `.last-integration`, and stop. The user fixes and re-runs.

## Step 4 — On green, write the marker and announce

1. Write `NEW_SHA` (from Step 2) to `.claude/.last-integration`. Create the directory if needed. Do NOT commit this file — it's a per-machine state marker; add `.claude/.last-integration` to `.gitignore` if it isn't already (best-effort, don't fail the command if `.gitignore` is missing).
2. Print the announcement:

```
✅ /integration green

  Stack:    <stack>
  Range:    <RANGE>
  Commits:  <N>
  Tests:    <count passed / total>
  Type:     <pass>

This group composes. Before starting the next group:

  1. Run `/code-review` (medium effort) on the group diff:
       /code-review --base=<LAST-SHA>

     This reviews this group's diff specifically — not the whole branch.
     Use --comment to post findings inline on the PR.

  2. (optional) Skim the diff yourself for things the review skill won't catch:
     intent, naming, whether what was built matches what the spec asked for.

  3. When this group's work is in good shape, start the next group.

When the whole spec is done, run /shakeout — it picks up where this gate left off.
```

## Failure modes

- **Tests fail**: report, halt, don't update marker. User fixes, re-runs.
- **Type-check fails**: same.
- **Repo not a git repo**: skip Step 2 entirely, run tests only, print announcement without diff range.
- **`.last-integration` exists but the SHA is unreachable** (rebase, force-push): warn the user, fall back to `merge-base HEAD main`.
- **Monorepo with selective workspaces**: don't try to be smart — run the root test command. Workspace-aware runs are the user's call.

## What this command does NOT do

- Does not auto-invoke `code-review` (it's a different skill with its own UI).
- Does not run Playwright / e2e — that's `/shakeout`.
- Does not invoke `shake-out`, the QA skill — also `/shakeout`.
- Does not commit anything.
- Does not enforce that tests existed (the SubagentStop hook does that per task).

The principle: **`/integration` is the "I just finished a group, prove the parts compose" check.** It's intentionally cheap so you'll actually run it.
