# netdust-gates v0 — spec

2026-09-21 · pilot on netdust.be this week · netdust-agent 0.28 stays untouched and in use elsewhere

## Intent

Stefan, 2026-09-21: *"I started out netdust-agent as skills that would add netdust coding
standards and testing into the spec and plan so it would be followed. Superpowers =
general-purpose agent engineering loop; netdust-agent = my software-delivery policy and
verification layer, authority gates."* Outcome wanted: *"high standards code, netdust
coding concepts, framework and a test framework ensuring code works, a proven stable
project."*

netdust-gates is that idea with nothing else in it. Superpowers runs the loop in its own
plan format. netdust-gates does three things and only these:

1. **Inject** — netdust standards land in the slots superpowers already carries to every
   implementer and reviewer (`Global Constraints`, `Review Focus`).
2. **Verify** — by executables: the project's `make gate`, and the shake-out artifact gate.
3. **Authorize** — hooks for what only Stefan can grant.

## What last week's sessions showed (the evidence this design answers)

- 30 sessions, 13–21 Sept. Most `gate-check` failures were plan-grammar fitting
  (`behaviour-cluster` ×16, `test-author-mode`, `cluster-lane`, `task-tier`, `stakes`);
  the checks that caught real problems were `shakeout-manifest` ×12, `shakeout-credential`
  ×2, `threat-model` ×2.
- devops-main-flow: 1,541 implementation / 2,638 test / 1,318 spec lines, 43 commits,
  ~3.5 days, none merged — the simpler flow shipped. The main controller alone produced
  1.1M output tokens; the heaviest implementer read a ninth of what it read. Stefan:
  "this feels like endless review/testing again".
- netdust.be session: "start the home prototype now, don't wait", "still no design?".

## Three findings from the code that shape v0

- **The 0.28 Write/Edit floors have never fired in a live session.** `hooks/hooks.json`
  registers the guard with `"matcher": "Bash"`, so `check_vendor_floor` and
  `check_upstream_floor` are reachable only from the test suite. Every
  `deny reason=upstream-floor` line in `~/.claude/logs/memory-hook.log` names a `/tmp`
  fixture path. v0 registers the matcher for every tool `main()` handles and tests the
  wiring, not only the function.
- **netdust.be has no declared gate.** It carries `tests/Unit`, `tests/Integration`,
  `tests/e2e` and `make gate`, but `site.yml` has no `commands.gate`, so `make gate` exits
  1. Declaring it is the pilot's first task on the site.
- **`make ship` already runs the gate itself** (devops 0.7.0). The shipping floor exists;
  v0 adds no gate-stamp hook.

## Requirements

**R1 — One policy skill, `netdust-gates:policy`.** It invokes `superpowers:brainstorming`
and `superpowers:writing-plans` and says what netdust adds to their artifacts; it never
restates them. Spec: a `Source:` line per requirement (a quote, or `invented — approved
<date>`). Plan: `Global Constraints` filled from the stack's constraints pack;
`Review Focus` filled from the threat model and the edge-class catalog, each line pinned
to a test in the owning task; a `First working version` line; one paragraph naming the
simplest design that would meet the ask and why it was or was not chosen.
*Source: "add netdust coding standards and testing into the spec and plan so it would be followed."*

**R2 — Intake is superpowers' three paths plus one netdust rule.** Spike, bounded,
architectural stand as upstream defines them. The netdust rule: a change to a
security-boundary file owes a threat model on the diff first, whatever its size. Design
work takes the prototype-first path; nothing in the skill delays a visible first version.
*Source: session evidence ("still no design?"); calibration `class-d-gap`.*

**R3 — The execution mode is recommended by rule, chosen by Stefan at the plan handoff.**
Native by default. Subagent-driven when a task encodes a rule this project chose, touches
a security-boundary path, or the plan is long enough to outlive one context.
*Source: invented — approved 2026-09-21 (the proposal Stefan answered "go ahead").*

**R4 — The WordPress constraints pack.** One file the skill reads on a WP project. It
names, by reference to the `netdust-wp` skills that own them: ntdst-core as the base and
its layering rules, the golden-path slice and named deviations, the four security pillars
per data flow, and the runners (`make gate`; Brain Monkey unit, wp-phpunit integration
through DDEV, Playwright e2e). It lives in netdust-gates for the pilot and moves to
netdust-wp if the pilot holds.
*Source: "netdust coding concepts, framework and a test framework ensuring code works."*

**R5 — Which stops survive superpowers' "only four things stop you".** Stated once in the
skill: the plan approval, the shake-out screenshot yield, and every devops verb that
belongs to the operator (`promote`, `ship`). Everything else is a ledgered ruling, listed
in the final message. The human's accepted exception in a shake-out manifest is spelled
`Accepted-by-human:`, never `Ruling:`.
*Source: invented — approved 2026-09-21 (report item 1–2, "go ahead").*

**R6 — Close.** `make gate` exits 0. On a user-facing change, `/shakeout`: `shakeout-qa`
drives the flows through the real browser or wire, commits them as tests, writes the
manifest; `bin/shakeout-check.py` exits 0; Stefan sees one screenshot per surface. Then
superpowers' single whole-branch review, joined by `security-sentinel` when the plan
carries a threat model and `invariant-auditor` when the project carries
`ARCHITECTURE-INVARIANTS.md`. One fix pass, each fix RED→GREEN; no re-review.
*Source: "a test framework ensuring code works, a proven stable project"; memory `no-reviewer-redispatch-after-fix-rounds`.*

**R7 — Authority hooks.** Carried from 0.28 with their tests: the flow floor, the
vendored-package floor, the destructive-command ask tier, SessionStart memory injection,
Stop-hook tag capture. Registered for `Bash|Write|Edit|NotebookEdit`, with a test that
fails when `hooks.json` does not cover a tool the guard handles. Not carried:
`subagent-stop.py`, `loop-gate.py`, the upstream-invocation floor.
*Source: "authority gates"; finding 1 above.*

**R8 — `bin/shakeout-check.py`.** The shake-out manifest checks extracted from
`gate-check.py` (browser evidence needs a URL and a real PNG; whole-file credential scan
with no override; the accepted-exception token per R5), with the tests that cover them.
No other part of `gate-check.py` comes along.
*Source: session evidence — the one check family that caught real problems.*

**R9 — The growth rule, written into the plugin's CLAUDE.md.** An incident lands as a
gate tier in the project, a line in a constraints pack or the edge-class catalog, or an
eval case. Never as a new plan field or a new check on plan grammar.
*Source: invented — approved 2026-09-21; 0.18 → 0.28 regrew in six weeks.*

**R10 — Evals.** Three behavioural cases ship with v0: a WP feature request yields a plan
whose `Global Constraints` carries the pack's lines; a request with a security surface
yields `Review Focus` lines naming the threat model's mitigations; a small tweak yields
no spec and no plan file.
*Source: global CLAUDE.md, "every skill ships with evals."*

## Not in v0

`gate-check.py`, lanes, tiers, clusters, placement, the model ladder, `/loop`, the loop
ledger, `implementer` / `test-author` / `reviewer` agents, `compounding`, `convergence`,
`run-score`, `run-trace`, `verify-budget`. `run-cost.py` is used from the 0.28 source tree
for the comparison; it needs no enabled plugin. The VAD scenario suite is the second
pilot. The 0.28 matcher bug is reported, not fixed here.

## Pilot setup on netdust.be (site repo, after the plugin builds)

`.claude/settings.json` disables `netdust-agent` and enables `netdust-gates` — never both,
their hooks would both fire. The site's `CLAUDE.md` overrides global §1 for this project:
the first action on code-changing work is `netdust-gates:policy`. `site.yml` gains
`commands.gate`. The running `specs/netdust-daan-fork` is left as it is; the pilot starts
at the next piece of work.

## Success, judged Friday 2026-09-25

Against last week's netdust.be session (9.3 h, 61 messages from Stefan, 17 gate-check
runs): the site's `make gate` is green and a shake-out manifest with screenshots exists
for what was built; Stefan's corrective messages about pace or ceremony are fewer; the
plans written carry the WP constraints without being asked. If it is not clearly better,
netdust.be flips back to 0.28 with one setting and nothing else changes.
