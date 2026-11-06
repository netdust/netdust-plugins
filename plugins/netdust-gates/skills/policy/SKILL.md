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
`superpowers:brainstorming` and `superpowers:writing-plans` say overrides their `docs/superpowers/...`
defaults. Everything about a feature lives in `specs/<feature>/` and nowhere else; superpowers'
ledger (`.superpowers/sdd/`) is its own scratch, deleted at finish:

| File | Holds | Written by |
|---|---|---|
| `spec.md` | the requirements, each with its `Source:` | brainstorming |
| `plan.md` | the plan, its `**Spec:**` header naming the spec | writing-plans |
| `plan-review.md` | the plan review, `Reviewed-plan:` per plan | `/plan-review` |
| `review.md` | the feature review, committed with its fix pass | `make review` · `/review-fix` |
| `flows.md` | the approved flows of a branch with no spec | `/shakeout` |
| `shakeout.md`, `shakeout/*.png`, `shakeout/*.revert.txt` | the manifest, its screenshots and revert proofs | `/shakeout` |
| `report.md` | the feature report, generated from the artifacts above | `make report` |
| `session-review.md` | the on-demand session audit | `/session-review` |
| `shakeout-bugs.md`, `shakeout-abort.md` · `test-prune/<date>.md` in `specs/` | a stack sweep's bug list and abort note · a suite audit | stack shake-out skills · `/prune-tests` |
| `CHECKS.md` | in `specs/` itself: every surface's `@e2e` and `@smoke` checks, and the trial log | `/shakeout` · `make report` |

**The plan is the feature.** When a spec covers independent subsystems (writing-plans' Scope Check; brainstorming's
sub-project decomposition lands here too, as one spec), the spec stays at `specs/<topic>/spec.md` with no plan beside it,
and each plan is `specs/<feature>/plan.md`, its `**Spec:**` header naming the parent. `<feature>` is the branch
`feature/<feature>`: one plan, one branch, one promotable unit. No plan declares another as a dependency, and no build
order is recorded — staging's e2e run is the dependency test.

## Intake

Invoke `superpowers:brainstorming`. Its three paths (spike, bounded, architectural) stand as
defined there. Netdust adds:

- **Security boundary.** A change to a security-boundary file — auth, session, capability or permission checks, nonces,
  input parsing, outbound fetches of user-supplied URLs, stored credentials, tenancy — owes a threat model on the diff
  first, whatever its size (`class-d-gap`: a one-line SSRF-guard edit shipped without one). Use `netdust-gates:threat-modeling`.
- **Design work is prototype-first.** A page or UI request builds the visible first version,
  then decides the next thing with Stefan looking at it. Nothing here delays that.
- **A small change writes no artifact.** One file, or one declarative edit, with no open decision — would a competent
  human do it in half an hour? — takes the bounded path's chat design and the change itself: no spec file, no plan file.
  On a WordPress project it still meets the pack's constraints; it just is not planned in writing.

## The spec

Every requirement carries a `Source:` line: a quote of what Stefan said, or `invented — approved <date>`. A requirement he
has not approved is a question, not a requirement. When the spec flags a security surface, the plan owes a
`## Threat model`, written with `netdust-gates:threat-modeling` before the tasks.

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
- **Slices** — a large plan is cut into vertical slices, each ending in something Stefan can see or run (a layer is
  not a slice), labelled `### Task N · Slice M:`; per slice `make gate` · its own flows, appended to the one `shakeout.md` · `make report`.

Nothing else is added. A plan field is not how an incident is remembered (see the plugin's `CLAUDE.md`).

**Then `/plan-review`, before Stefan reads it.** A fresh `plan-reviewer` subagent ground-truths
every premise against the source, checks coverage and invention, and judges the simplest design and
the slices; its report is filed as `specs/<feature>/plan-review.md` naming the plan's blob
(`Reviewed-plan: <sha>`) — a file, never a claim. Blocking findings go back into the plan and the
review runs again, within the Close's plan-review cap. A spec cut into several plans is reviewed as
one set, `/plan-review <topic>`, so the cut is judged too. Plan and review reach Stefan together;
nothing blocks code on a plan's state — an old or half plan never holds up the work (Stefan, 2026-09-23).

## Execution mode

A planned feature runs as two sessions; a change with no plan file stays in one. After the plan approval this session
turns reviewer and a coder executes in the project's checkout on `feature/<feature>`, cut from production's branch with
spec, plan and plan review as its first commits; only the coder writes that tree — a worktree is for urgent parallel work
only (`netdust-devops:parallel-work`). Inside hc (`HC_TERMINAL_ID` set) the pair recipe in `netdust-core:hc-orchestration`
starts it with `hc run`, the pair in auto mode; outside hc, one background subagent there, over SendMessage. The brief opens
`Role: coder`, the plan path and `netdust-gates:policy`: the coder skips Intake and the plan, never starts a coder, sends a
pre-flight scan for rulings before Task 1, runs every step that writes the tree (`/shakeout`, the push), ledgers each exchange
so a restart reads branch, plan and ledger, and mirrors every stop into Studio (`netdust-core:worktable`) where the box has
it. The reviewer reads only the first working version, a block and the Close: there it runs `make review name=<feature>` on
the pushed branch and brings Stefan the report yield and `make promote`; a finding is one fix request, closed by its test.
Mode: **Native** by default, **subagent-driven** only for a security-boundary unit or a plan outliving one context; name the rule.

## Stops

Upstream's four stops stand, and Netdust's: the plan approval; the report yield (Close, step 8); a spec-less
branch's flow list; every operator verb (`unpromote`, `ship`, deploy, pushing a package's `main`), his to run or confirm
by typing — `promote` and `land` ask nothing, and `unpromote`, `deploy env=staging`, `e2e`, `smoke`, `review` run under his standing OK
(`NETDUST_AGENT_OK=1`); `ship` and production stay his; a review finding about intent; the coder's permission prompts, his
alone to answer. A coder asks its reviewer, never Stefan; the reviewer rules technical ones, sparring with a fresh agent,
and takes intent and upstream's four stops to Stefan. A shake-out exception he accepts is `Accepted-by-human:`, never
`Ruling:`; only he writes it. Everything else you decide, ledger as `Ruling: <what> — <why> — <cost if wrong>` and list in
the final message, a coder's with its deferred minors via its reviewer's hand-over.

## Close

Every step is a `make` verb or names one, so a human by hand and a coder run the same commands in this order:
1. `make gate` exits 0 — the project's own suite (`commands.gate`, else the `gate` script the session-start `Box:` line
   names; none declared: declaring one is the work's first task). A box that cannot run it pushes and says so.
2. `make review name=<feature>` (`/feature-review <feature>` without devops), plan or no plan — superpowers'
   whole-branch review (`superpowers:requesting-code-review`, a fresh reviewer; the author never reviews its own diff) on
   the most capable model, joined by `security-sentinel` when the plan carries a `## Threat model` or the diff touches a
   security-boundary path, and `invariant-auditor` when the project carries `ARCHITECTURE-INVARIANTS.md`.
3. One fix pass on every Blocking and Should fix finding (a finding that is a decision goes to Stefan), each fix RED→GREEN
   through the seam where the finding showed — the request, route or render — never reflection on the private method; the
   review, copied from `make review`'s saved report to `specs/<feature>/review.md`, is committed with it. No re-review — named checks and the suites close it.
4. A user-facing change runs `/shakeout`, once, on the fixed code: `shakeout-qa` drives the flows through the real browser
   or wire, commits them as tests, proves each new test on the base (`revert-run`) and writes `specs/<feature>/shakeout.md`;
   it registers them in `specs/CHECKS.md` as `@e2e` (`make e2e env=staging`, the proof after a deploy or a plugin update)
   beside a read-only `@smoke` check (`make smoke`, production too). Then `make shakeout name=<feature>` (`bin/shakeout-check.py`) exits 0.
5. One fix round for a failed shake-out row, then its stop.
6. `make report name=<feature>` — `report.md`, generated from the artifacts, committed with `specs/CHECKS.md` (its trial line).
7. `make gate` once more, on that tip: the green run stamps what `promote` requires.
8. STOP — the report yield: Stefan reads `report.md`: its screenshots, one per surface; every `Accepted-by-human:` row (an
   agent-written one is reverted and its row re-driven); the hunt's tally and its `not ours:` / `rejected:` lines, each his
   to overrule (it gets its repro and a `fail` row, back to step 5) or to schedule.
9. Every change: `superpowers:finishing-a-development-branch` — on a project with `site.yml`, in place of its menu: the branch
   pushed, then `make promote name=<feature>` (before launch, production without a path: `make land name=<feature>`), run by
   the agent once the review and gate are green; never a merge into production by hand. `make e2e env=staging` re-runs every
   registered check on the composition, and `ship` waits for it.

Per slice of a sliced plan: `make gate`, the slice's own flows (appended to the one `shakeout.md`), `make report`; the
review, the fix pass, the hunt, the final gate and the stop run once, at the feature's end. Caps, stated here only:
plan review 2 rounds; coder 3 attempts per task, then its reviewer; fix pass 1; shake-out fix round 1; a cap hit is a
`Ruling:` with its cost and a stop for Stefan. Every other prompt that loops defers here, never restating a number.

On demand: `/session-review <feature>` (the work, six dimensions, core fit on WordPress — before finishing, while the task
reports exist), `/session-learn` (a transcript's lessons) and `/prune-tests` (a suite against the behavioural bar) report, and
Stefan approves what follows; `/review-fix <feature>` turns a saved review into follow-up commits — only what he picks.
