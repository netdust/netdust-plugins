---
name: policy
description: Use FIRST on any code-changing request in a Netdust project — build, fix, tweak, refactor. Wraps superpowers' brainstorm → plan → execute → review loop with Netdust's three additions: standards injected into the spec and plan, verification by executables (`make gate`, the shake-out check), and the stops only the human grants. Not for read-only questions, prose or research.
---

# netdust-gates:policy

Superpowers runs the loop and owns its rules; this skill never restates them. It adds three
things — **inject** (Netdust standards into the artifacts superpowers already carries to every
implementer and reviewer), **verify** (executables, not testimony), **authorize** (what only
Stefan grants). Anything not written here is upstream's rule.

## Where artifacts live

Spec `specs/<feature>/spec.md`, plan `specs/<feature>/plan.md` — the location preference that
`superpowers:brainstorming` and `superpowers:writing-plans` say overrides their
`docs/superpowers/...` defaults. Everything about a feature lives in `specs/<feature>/`:

| File | Holds | Written by |
|---|---|---|
| `spec.md` | the requirements, each with its `Source:` | brainstorming |
| `plan.md` | the plan, its `**Spec:**` header naming the spec | writing-plans |
| `plan-review.md` | the plan review, `Reviewed-plan:` per plan | `/plan-review` |
| `review.md` | the feature review, committed with its fix pass | `make review` · `/review-fix` |
| `flows.md` | the approved flows of a branch with no spec | `/shakeout` |
| `shakeout.md`, `shakeout/*.png` | the shake-out manifest and screenshots | `/shakeout` |
| `session-review.md` | the on-demand session audit | `/session-review` |
| `shakeout-bugs.md`, `shakeout-abort.md` | a stack sweep's bug list and abort note | stack shake-out skills |
| `CHECKS.md` | in `specs/` itself: every surface's `@e2e` and `@smoke` checks | `/shakeout` |
| `test-prune/<date>.md` | in `specs/` itself: a suite audit | `/prune-tests` |

Nothing goes elsewhere; superpowers' ledger (`.superpowers/sdd/`) is its own scratch, deleted at finish.

**The plan is the feature.** When a spec covers independent subsystems
(writing-plans' Scope Check; brainstorming's sub-project decomposition lands here too, as one spec), the spec stays at
`specs/<topic>/spec.md` with no plan beside it, and each plan is `specs/<feature>/plan.md`, its
`**Spec:**` header naming the parent. `<feature>` is the branch `feature/<feature>`: one plan,
one branch, one promotable unit. No plan declares another as a dependency, and no build order is
recorded — staging's e2e run is the dependency test.

## Intake

Invoke `superpowers:brainstorming`. Its three paths (spike, bounded, architectural) stand as
defined there. Netdust adds:

- **Security boundary.** A change to a security-boundary file — auth, session, capability or
  permission checks, nonces, input parsing, outbound fetches of user-supplied URLs, stored
  credentials, tenancy — owes a threat model on the diff first, whatever its size (`class-d-gap`: a
  one-line SSRF-guard edit shipped without one). Use `netdust-gates:threat-modeling`.
- **Design work is prototype-first.** A page or UI request builds the visible first version,
  then decides the next thing with Stefan looking at it. Nothing here delays that.
- **A small change writes no artifact.** One file, or one declarative edit, with no open
  decision — would a competent human do it in half an hour? — takes the bounded path's chat
  design and the change itself: no spec file, no plan file. On a WordPress project it still
  meets the pack's constraints; it just is not planned in writing.

## The spec

Every requirement carries a `Source:` line: a quote of what Stefan said, or
`invented — approved <date>`. A requirement he has not approved is a question, not a
requirement. When the spec flags a security surface, the plan owes a `## Threat model`, written
with `netdust-gates:threat-modeling` before the tasks.

## The plan

Invoke `superpowers:writing-plans`; it owns the format. Netdust fills its slots:

- **Global Constraints** — on a WordPress project (a `site.yml` with `structure:`, `roots/wordpress` in `composer.json`,
  or a `composer.json` of type `wordpress-muplugin`) copy the Global Constraints of `wordpress.md`, beside this file,
  verbatim — lines and red flags — then the spec's own. Other stacks: the spec's own until a pack exists.
- **Test map** — invoke `netdust-gates:test-mapping`, after the threat model and before the
  tasks: one row per unit (seam · tier · file · command · e2e flows); a task is one row.
- **Review Focus** — one line per mitigation in the threat model, per convergence point of an
  `ARCHITECTURE-INVARIANTS.md` the diff touches, and per class in `edge-classes.md` the feature
  can actually meet, most likely first. Each line points at a Test map row; an absence or a count
  ("never", "only", "exactly one") points at an `ARCHITECTURE-INVARIANTS.md` check instead, which
  `invariant-auditor` runs at review — never a test that reads source (`source-scan-ratchets`).
- **First working version** — one line under Architecture: the task that produces the first thing Stefan
  can see or run, ordered first. Tests and scaffolding for something nobody can yet see come after it.
- **Simplest design** — one paragraph: the simplest design that would meet the ask, and why
  the plan does or does not use it.

Nothing else is added. A plan field is not how an incident is remembered (see the plugin's `CLAUDE.md`).

**Then `/plan-review`, before Stefan reads it.** A fresh `plan-reviewer` subagent ground-truths
every premise against the source, checks coverage and invention, and judges the simplest
design; its report is filed as `specs/<feature>/plan-review.md` naming the plan's blob
(`Reviewed-plan: <sha>`). Blocking findings go back into the plan and the review runs again.
A spec cut into several plans is reviewed as one set, `/plan-review <topic>`, so the cut is
judged too. The review is a file, never a claim. The plan and its review reach Stefan together. Nothing
blocks code on a plan's state — an old or half plan never holds up the work (Stefan, 2026-09-23).

## Execution mode

A planned feature runs as two sessions; a change with no plan file stays in one. After the plan
approval this session turns reviewer and a coder executes in its own worktree, cut from production's
branch with spec, plan and plan review as the first commits of `feature/<feature>` (on DDEV its own
project, `netdust-devops:parallel-work`); only the coder writes that tree. Inside herdr
(`HERDR_ENV=1`) the pair recipe in `netdust-core:herdr-orchestration` starts it with
`herdr agent start`; outside it, one background subagent there, over SendMessage; both in one
permission mode. The brief opens `Role: coder`, the plan path and `netdust-gates:policy`: a coder
skips Intake and the plan, never starts a coder, sends its pre-flight scan for rulings before
Task 1, runs every step that writes the tree, `/shakeout` and the push included, and ledgers each
exchange, so a restart of either reads branch, plan and ledger. The reviewer reads only the first
working version, a block and the Close, where it runs `make review name=<feature>` from its own
checkout and brings Stefan the screenshot yield and `make promote`; a finding is one fix request,
closed by its test. The mode is no longer a stop: **Native** by default, **subagent-driven** only
for a security-boundary unit or a plan that outlives one context. Name the rule that fired.

## Stops

Upstream's four stops stand, and Netdust's: the plan approval; the shake-out screenshot yield (Close, step 4); a spec-less
branch's flow list; every operator verb (`promote`, `unpromote`, `ship`, deploy, pushing a package's `main`), his to run or
confirm by typing — bar `promote`, `unpromote`, `deploy env=staging`, `e2e`, `smoke` and `review` under his standing OK
(`NETDUST_AGENT_OK=1`); `ship` and production stay his; a review finding about intent; the coder's permission prompts, his
alone to answer. A coder asks its reviewer, never Stefan; the reviewer rules technical ones, sparring with a fresh agent,
and takes intent and upstream's four stops to Stefan. A shake-out exception he accepts is `Accepted-by-human:`, never
`Ruling:`; only he writes it. Everything else you decide, ledger as `Ruling: <what> — <why> — <cost if wrong>` and list in
the final message, a coder's with its deferred minors via its reviewer's hand-over.

## Close

1. `make gate` exits 0 — the project's own suite (`commands.gate` in `site.yml`). A project with
   no declared gate declares one as the first task of the work; that is not a reason to skip.
2. The feature review, plan or no plan: `make review name=<feature>` (`/feature-review <feature>`
   without devops) — superpowers' whole-branch review (`superpowers:requesting-code-review`, a fresh
   reviewer; the author never reviews its own diff) on the most capable model, joined by
   `security-sentinel` when the plan carries a `## Threat model` or the diff touches a security-boundary
   path, and `invariant-auditor` when the project carries `ARCHITECTURE-INVARIANTS.md`.
3. One fix pass on every Blocking and Should fix finding (a finding that is a decision goes to
   Stefan), each fix RED→GREEN through the seam where the finding showed — the request, route or
   render — not reflection on the private method the fix touched; the review is kept as
   `specs/<feature>/review.md` (copied from `make review`'s saved report, or the
   `/feature-review` summary without devops) and committed with it. No re-review — named checks and the suites close it.
4. A user-facing change runs `/shakeout`, once, on the fixed code: `shakeout-qa` drives the flows
   through the real browser or wire, commits them as tests and writes `specs/<feature>/shakeout.md`; it
   registers them in `specs/CHECKS.md` as `@e2e` (`make e2e env=staging`, the proof after a deploy or a
   plugin update) beside a read-only `@smoke` check (`make smoke`, production too);
   `bin/shakeout-check.py` exits 0; Stefan sees one screenshot per surface. This shake-out writes the
   checks; `make e2e env=staging` re-runs all of them on the composition, and `ship` waits for it.
5. Every change: `superpowers:finishing-a-development-branch` — on a project with `site.yml`, in place of its menu: the
   branch pushed and `make promote name=<feature>` handed to Stefan, or run under his standing OK (it finds the saved
   review and skips it); a feature never merges into production by hand.

On demand, whenever Stefan asks: `/session-review <feature>` audits the work (six dimensions,
core fit on WordPress — run it before finishing, while the task reports exist), and
`/session-learn` reads a transcript for lessons, `/prune-tests` audits a suite against the
behavioural bar. Those three report; he approves what follows. `/review-fix <feature>` turns a
saved review into follow-up commits on the branch — it changes only what Stefan picks.
