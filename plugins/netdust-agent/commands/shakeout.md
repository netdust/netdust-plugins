---
description: Spec-complete gate. Run when all task groups in a spec are done — before merging the branch. Stack-agnostic. Runs the test-effectiveness audit and feature-acceptance verification first, re-runs the /integration checks, then Playwright if a config exists, then invokes the shake-out skill, then auto-dispatches four (or five for WP) reviewer agents in parallel on the full branch diff.
allowed_tools: ["Bash", "Read", "Glob", "Skill", "Agent"]
---

Run the **spec-complete gate**. This fires when an entire spec is done, before merging the branch. It's heavier than `/integration` — full QA sweep + e2e + multi-perspective review.

## What this gate is, in one line

> Before merging, prove the artifact actually works end-to-end and survives review from multiple angles (simplicity, security, performance, architecture drift).

## Pre-flight

Verify you're on a feature branch, not `main` / `master` / `staging`:

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
case "$BRANCH" in
  main|master|staging)
    echo "Refusing to run /shakeout on $BRANCH. Switch to a feature branch first."
    exit 1
    ;;
esac
```

## Step 0 — Test-effectiveness audit (the suite *bites*, not just passes)

Before anything else, audit whether the test suite would actually go RED if a dangerous path broke — a green suite that never exercises the denial branch, the second tenant, the un-mocked wire, or the unmounted guard ships bugs past every later gate. This is the cheapest place to catch a green-but-blind test, and its `covered`/`blind`/`fixed` manifest becomes the convergence target the Step 4 reviewers verify against (so they verify gaps instead of re-discovering them).

> Note: if you reached `/shakeout` via `harnessed-development`, its Stage 3 already ran this audit — you may skip Step 0. Running `/shakeout` standalone, this is the only place the audit fires, so do not skip it.

Use the Skill tool, pointed at the branch diff (Situation A — phase/spec-complete audit):

```
Skill("test-effectiveness")
```

Hand it the diff range (`$(git merge-base HEAD main)..HEAD`) as the audit target. It will walk the seven failure modes (stale fixture, test-world≠real-world, wire-mock leak, unmounted guard, happy-path-only/missing-denial, no-coverage, concurrency) over every guard, fixture, wire, mount, and timer the diff introduced, and for each either name the test that goes RED or record it `blind` and author the test that closes it.

**Wait for the audit manifest before continuing.** If it surfaced `blind` paths, those tests are authored now (RED-first) and the unit suite below must include them. If the audit aborts or the suite can't be made to bite, stop and report — don't proceed to a review pass that would just re-discover the gap.

## Step 0b — Feature-acceptance verification (does the FEATURE behave, not just the code)

If this branch added or changed a **user-facing feature** (a view, form, wizard, interactive flow, CRUD surface, or an endpoint a client/agent drives), verify it behaves the way it's meant to be used — every intended flow, every edge — driven through the real surface. test-effectiveness (Step 0) proved the tests *bite*; this proves the *feature behaves*. These two gates are siblings: one audits code coverage, the other drives behavior.

> Note: if you reached `/shakeout` via `harnessed-development`, Stage 1g authored an `## Acceptance flows` matrix in the plan and Stage 3 may have already driven it — point this step at that matrix rather than re-deriving. Running `/shakeout` standalone with no matrix, derive the intended-use flows from the spec/diff now.

Use the Skill tool (Situation B — verify the matrix):

```
Skill("feature-acceptance")
```

It will drive each flow + edge through its faithful layer — **UI flows through the real browser** (a Playwright spec if one exists → else `superpowers-chrome` `use_browser` against the running dev server), **backend flows through the un-mocked wire** (a real request through the mounted app, asserting response + DB state + emitted event) — checking the six edge classes per flow (empty/zero state, denied actor, wrong-order/re-entry, concurrent/double, boundary value, mid-flow failure).

**Bring up the real surface first** (start the dev server for browser flows; have the API reachable for backend flows). The skill emits a `pass`/`fail`/`not-reachable`/`unverified-no-browser` manifest. A `fail` is a bug fixed here (via `superpowers:systematic-debugging`) before proceeding. **No UI flow is marked `pass` without a real browser driving it** — if the browser can't be reached, those flows are `unverified-no-browser` and reported to the user as residual risk, never laundered to green.

**Wait for the manifest before continuing.** Like Step 0's, it becomes a convergence target the Step 4 reviewers verify against.

## Step 1 — Re-run /integration's checks

The spec gate is a superset. If the group-level gates don't pass, there's no point shaking out.

Detect the stack the same way `/integration` does. Run:

1. Type-check (Bun/TS only — see `/integration` for the command).
2. Unit + integration tests (full suite, not delta).

If any fail: stop. Report. Don't proceed. The user fixes and re-runs.

## Step 2 — Playwright e2e (if configured)

```bash
PW=$(find . -maxdepth 4 -name 'playwright.config.*' -not -path './node_modules/*' | head -1)
if [[ -n "$PW" ]]; then
  echo "→ Running Playwright from $(dirname "$PW")"
  (cd "$(dirname "$PW")" && bunx playwright test) || exit 1
else
  echo "→ No playwright.config — skipping e2e. (Add one to gate this.)"
fi
```

Same for `cypress.config.*`, `vitest.workspace.*` with e2e suites — best-effort, don't be clever.

For WordPress/Statamic projects: if `tests/acceptance/` exists with Codeception specs, run `vendor/bin/codecept run acceptance` (prefix `ddev exec ` if `.ddev/` exists).

## Step 3 — Invoke the shake-out skill

The `shake-out` skill is the QA sweep itself (Sweep → Manifest → Fix). This command does NOT replicate it — it invokes it.

Use the Skill tool:

```
Skill("shake-out")
```

Hand off to the skill. It will:
- Read the plan (point it at `tasks/todo.md` or the spec under `docs/superpowers/specs/` if present)
- Sweep the artifact end-to-end
- Compile a bug manifest
- Fix systematically via `superpowers:systematic-debugging` per bug
- Re-sweep after fixes

**Wait for the skill to complete and the manifest to be either empty or fully resolved before continuing.** This is the QA gate proper.

## Step 4 — Auto-dispatch the multi-reviewer pass

Once shake-out reports green, dispatch the reviewer agents **in parallel**. This means a single assistant turn containing multiple `Agent` tool calls in one message — not sequential calls. If Step 0 produced a `covered`/`blind`/`fixed` manifest (and/or Step 0b a `pass`/`fail`/`unverified-no-browser` acceptance manifest), include them in each agent's briefing as the convergence targets — reviewers verify the `blind→fixed` transitions, the driven flow outcomes, and flag any path still `blind` or any UI flow still `unverified-no-browser`, rather than re-discovering coverage/behavior gaps free-form.

Compute the diff range:

```bash
BASE=$(git merge-base HEAD main)
RANGE="${BASE}..HEAD"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
SPEC=$(ls docs/superpowers/specs/*.md 2>/dev/null | tail -1)  # most recent spec, if any
```

Detect WordPress: if `composer.json` exists AND grep finds `wordpress` / `wpackagist` / `wp-config.php`, the project is WP — include reviewer #5.

Then dispatch the agents in a single message (parallel block). Each agent gets the same briefing core, varying only by lens:

| # | subagent_type | Always or WP-only |
|---|---|---|
| 1 | `code-simplicity-reviewer` | always |
| 2 | `security-sentinel` | always |
| 3 | `performance-oracle` | always |
| 4 | `invariant-auditor` | always |
| 5 | `netdust-wp:ntdst-drift-reviewer` | WP only |

Briefing template (use verbatim per agent, substituting the lens):

```
Review the diff <RANGE> on branch <BRANCH>.

Spec (if present): <SPEC, or "no spec file under docs/superpowers/specs/">

Your lens: <one-line lens, e.g. "code simplicity / YAGNI / dead code">

Constraints:
- Read git diff <RANGE> first; this is the changeset.
- Read the spec file if one exists; it's the intent.
- Findings only — do not propose patches longer than a few lines.
- Severity for each finding: BLOCKER / SHOULD-FIX / NICE-TO-HAVE.
- Brevity wins. No filler. No restating the diff.
- Report format:
    ## <Lens>
    ### BLOCKER (n)
    - <file:line> — <issue>
    ### SHOULD-FIX (n)
    - ...
    ### NICE-TO-HAVE (n)
    - ...

If your lens finds nothing, say so in one line.
```

**Important:** the four (or five) `Agent` calls MUST go in a single assistant message so they run concurrently. Sequential calls defeat the point.

After all reports return, present the consolidated triage to the user:

```
✅ /shakeout: unit + integration + type + e2e + shake-out all green
✅ Four (or five) reviewer agents reported.

Consolidated findings:

  BLOCKERS (must fix before merge):     <count>
  SHOULD-FIX (recommended):              <count>
  NICE-TO-HAVE (optional):               <count>

Top findings by lens:
  - simplicity:    <one-line summary>
  - security:      <one-line summary>
  - performance:   <one-line summary>
  - architecture:  <one-line summary>
  - drift (WP):    <one-line summary>  ← only if WP

[Full per-agent reports follow below.]

Next steps:
  1. Triage BLOCKERS now — fix here, then re-run /shakeout.
  2. SHOULD-FIX → triage with user; either fix or record in memory/STATE.md.
  3. NICE-TO-HAVE → ignore or open issues.
  4. When BLOCKERS == 0:
       /code-review --base=main --effort=high --comment
     for one final inline pass.
  5. Then invoke superpowers:finishing-a-development-branch.
```

If any reviewer agent fails to return (timeout, error): print which one failed and stop. The user re-runs `/shakeout` after fixing the agent or skipping it manually.

## Failure modes

- **Stack mismatch (mixed mono-repo)**: run each detected stack's gate. Report each separately.
- **Skill invocation fails**: print the error and stop. Don't fall through to the announcement.
- **shake-out aborts and re-plans**: that's the skill's normal escape hatch. Respect it — do not announce success.
- **No spec file**: the shake-out skill will ask. If the user has only `tasks/todo.md`, point it there.

## What this command does NOT do

- Does not auto-invoke `/code-review` — it has its own UX (`--fix`, `--comment`) and pairs better with the user looking at findings on screen.
- Does not merge or push.
- Does not update `.last-integration` (that's a group-level marker).
- Does not auto-fix reviewer findings — those need human triage.

The principle: **`/shakeout` proves the artifact works, runs the deep review automatically, and hands the user a triaged list.** The user pulls the final triggers (fixing blockers, `/code-review`, merge).
