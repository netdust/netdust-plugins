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
`docs/superpowers/...` defaults.

## Intake

Invoke `superpowers:brainstorming`. Its three paths (spike, bounded, architectural) stand as
defined there. Netdust adds:

- **Security boundary.** A change to a security-boundary file — auth, session, capability or
  permission checks, nonces, input parsing, outbound fetches of user-supplied URLs, stored
  credentials, tenancy — owes a threat model on the diff first, whatever its size
  (`class-d-gap`: a one-line SSRF-guard edit shipped without one). Use
  `netdust-gates:threat-modeling`.
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

- **Global Constraints** — on a WordPress project (a `site.yml` with `structure:`, or
  `roots/wordpress` in `composer.json`) copy the constraint lines of `wordpress.md`, beside
  this file, verbatim, then the spec's own. Other stacks: the spec's own until a pack exists.
- **Review Focus** — one line per mitigation in the threat model, per convergence point of an
  `ARCHITECTURE-INVARIANTS.md` the diff touches, and per class in `edge-classes.md` the feature
  can actually meet, most likely first. Each line is pinned to a test in the task that owns the
  code; a line with no test is a wish.
- **First working version** — one line under Architecture: the task that produces the first
  thing Stefan can see or run, ordered first. Tests and scaffolding for something nobody can
  yet see come after it.
- **Simplest design** — one paragraph: the simplest design that would meet the ask, and why
  the plan does or does not use it.

Nothing else is added. A plan field is not how an incident is remembered (see the plugin's
`CLAUDE.md`).

## Execution mode

Stefan chooses at the plan handoff; you recommend by rule. **Native** by default. Recommend
**subagent-driven** when a task encodes a rule this project chose, touches a security-boundary
path, or the plan is long enough to outlive one context. Give the rule that fired, in a sentence.

## Stops

Upstream's four stops stand. Netdust names the ones that occur: the plan approval and the
execution-mode choice; the shake-out screenshot yield (Close, step 2); and every devops verb
that belongs to the operator — `promote`, `unpromote`, `ship`, deploy — which Stefan runs or
confirms by typing. Everything else you decide and ledger as
`Ruling: <what> — <why> — <cost if wrong>`, and list in the final message. A shake-out exception
Stefan accepts is `Accepted-by-human:` in the manifest, never `Ruling:`; only he writes it.

## Close

1. `make gate` exits 0 — the project's own suite (`commands.gate` in `site.yml`). A project with
   no declared gate declares one as the first task of the work; that is not a reason to skip.
2. A user-facing change runs `/shakeout`: `shakeout-qa` drives the flows through the real
   browser or wire, commits them as tests and writes `specs/<feature>/shakeout.md`;
   `bin/shakeout-check.py` exits 0; Stefan sees one screenshot per surface.
3. Superpowers' single whole-branch review on the most capable model, joined by
   `security-sentinel` when the plan carries a `## Threat model` and `invariant-auditor` when
   the project carries `ARCHITECTURE-INVARIANTS.md`.
4. One fix pass, each fix RED→GREEN. No re-review — named checks and the suites close it. Then
   `superpowers:finishing-a-development-branch`.
