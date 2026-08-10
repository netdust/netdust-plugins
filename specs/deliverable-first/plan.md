# Plan — Deliverable-first harness

**Spec:** `specs/deliverable-first/spec.md` · **Class A** (multi-task, real design decisions) · inline-planned, human present.

## Technical context

- **Edit target:** this repo (`~/.claude/plugins/marketplaces/netdust-plugins`), plugin
  `plugins/netdust-agent`. Never the cache.
- **Test runner:** `python3 -m pytest plugins/netdust-agent/tests/` from the repo root.
  pytest is not currently importable on this box (`.pytest_cache` proves it ran before) —
  first task installs it (`pip3 install --user pytest` or distro package) and records the
  working invocation in its evidence. No production dependency is added.
- **Checker architecture (ground-truthed):** `bin/gate-check.py` is 1528 lines of
  `check_*(text, f: Findings)` functions called from a main that reads
  `specs/<feature>/{spec,plan,tasks}.md`, with fenced blocks stripped before parsing.
  New checks follow that exact shape.
- **Hook architecture (ground-truthed):** `hooks/subagent-stop.py` blocks an implementer
  close whose evidence suite exited non-zero, scrapes the transcript so testimony cannot
  overrule a scraped failure, and appends `suite-green` events to
  `tasks/.harness-loop.json`. That ledger is where cluster behaviour-block context will
  live (a `cluster-open` event naming the RED test; written by the controller per the
  building skill, read by the hook).

**Loop budget: ~14 iterations** (9 tasks + 3 review clusters + slack for one fix round on Cluster B).

## Stakes

**Stakes: standard** — a wrong gate or skill text ships bad guidance to every future
session on every project, visibly and recoverably (git revert of a markdown/py file); no
money, data, access, or irreversible operation anywhere in the diff.

### Per-cluster stakes

| Cluster | Stakes | Why |
|---|---|---|
| A — the checker | **standard** | a wrong check blocks or admits plans loudly; caught at first use, reverted in one commit |
| A-fix — review findings | **standard** | same surface as A; three fix cycles from the Cluster A review |
| B — the hook | **high** | `subagent-stop.py` is the enforcement boundary itself — a bug here silently un-gates every implementer close on every project; failure mode is invisible, not loud |
| C — the skill texts | **standard** | prose guidance; wrong words misroute sessions but every mechanical gate beneath them still holds |

## First working version

**Task:** T01
**Demonstrates:** the checker refuses the exact artifacts that passed on 2026-08-09 — a
human can run one command and watch the musician-events plan fail for the reason the
post-mortem named (the deliverable ordered last); T02 adds the second finding
(`fr-source`) to the same replay.
**Verify by:** `python3 plugins/netdust-agent/bin/gate-check.py <fixture copy of daan specs/musician-events>` → exit 1, findings naming `deliverable-first` (and, after T02, `fr-source`).

## Constitution check

Simplicity first: every fix lands in an existing file following an existing convention —
no new scripts, no new hook, no new artifact type. The one new grammar (behaviour blocks)
is opt-in per cluster and changes nothing for artifacts that don't carry it. The one
deleted behaviour (verify-budget's HALT) is replaced by strictly less machinery.

## Threat model [GATE]

N/A — no 1a trigger surface: the parsed artifacts are repo-local files authored by the
team, the hook reads a ledger the harness itself writes, and nothing touches auth,
untrusted input, credentials, tenancy, or outbound requests.

## Acceptance flows [GATE]

N/A — spec flags no user-facing surface (developer/agent tooling). The behavioural
contract is the named pytest cases per task plus the two fixture replays in Cluster A's
integration gate (musician-events must FAIL; this spec's own artifacts must pass).

## Architecture invariants touched [GATE]

This repo carries no `ARCHITECTURE-INVARIANTS.md`. The harness's own load-bearing
invariant — **no self-attestation: a gate is proven by an artifact property or a scraped
result, never by an agent's claim** — is preserved and extended by every change here:
1j and fr-source are artifact properties; the hook's RED tolerance reads the ledger and
the scraped suite result, never testimony; verify-budget's demotion removes a gate, it
does not weaken one (its HALT was already non-binding in practice — waived 3/3 times).

## Spec-premise ground-truth [GATE]

- **G1 — checker shape:** `check_*` registry confirmed at `bin/gate-check.py:135–1436`;
  fenced-block stripping confirmed; `legacy-artifact` waiver convention exists and is the
  reuse target for FR-2/FR-5.
- **G2 — hook blocks red suites and owns a ledger:** `hooks/subagent-stop.py` docstring
  lines 10–54: blocks implementer close on non-zero suite, scraped-failure-wins rule,
  appends `suite-green` (sha + cmd) to `tasks/.harness-loop.json`. The tolerance change
  (FR-8) extends this file and its ledger; no new channel is invented.
- **G3 — the 1j draft:** `skills/planning/references/gate-1j-deliverable-first.md` exists
  (148 lines), status "proposal, awaiting a human decision", its three open questions now
  answered (first-3 / FAIL / spec-side section stays in the plan per the draft's own
  mechanical-assertions design). Both its worked examples remain valid test fixtures.
- **G4 — verify-budget contract:** `bin/verify-budget.py:1–60` — exit 1 on HALT is the
  only non-zero path; `CEILINGS` dict is self-contained; `tests/test_verify_budget.py`
  (262 lines) pins the current contract and is the one test file this spec is allowed to
  re-contract (SC-6 names it).
- **G5 — test corpus:** `tests/test_spec_gate_check.py` (1846 lines) and
  `tests/test_subagent_stop*.py` (355 + 372 lines) exist and pass in CI style; new cases
  extend them, no parallel harness is built.

## The failure-chain table (SC-5)

| # | 2026-08-09 failure link | Control landed here | FR | Task |
|---|---|---|---|---|
| 1 | FR-7 invented at spec time, then served | `Source:` line per FR, machine-checked | FR-1/2 | T02 |
| 2 | Deliverable ordered last, session died first | 1j `## First working version`, first-3, FAIL | FR-3/4/5 | T01 |
| 3 | 276-line config-shape test as "proof" | behaviour blocks: one outside-observable RED per cluster, hook-tolerated | FR-6/7/9 | T03, T05 |
| 4 | Reviewers dispatched, artifact never loaded | `Artifact-load:` line required before reviewer dispatch | FR-12/13 | T07 |
| 5 | verify-budget HALT waived a third time | HALT deleted; ratio becomes telemetry | FR-10/11 | T04, T07 |
| 6 | Declarative config routed as full Class A | decision-density intake clause + red flag | FR-14/15 | T08 |

## Phases & review clusters [GATE]

Single phase, three clusters, ordered deliverable-first (the checker IS the demo), the
enforcement boundary reviewed alone at FULL, prose last at LIGHT:

- **Cluster A — the checker** (T01–T04, effective stakes standard, provisional tier
  STANDARD): pytest environment, then the three new checks and the verify-budget
  demotion, TDD'd against `test_spec_gate_check.py` / `test_verify_budget.py`.
- **Cluster B — the hook** (T05, effective stakes high, provisional tier FULL): the
  subagent-stop transition tolerance. Reviews alone; `split` test-authorship per D1.
- **Cluster C — the skill texts** (T06–T09, effective stakes standard, provisional tier
  LIGHT): planning / spec-authoring / building / harnessed-development text changes,
  the 1j reference promotion, calibration entry, version bump.

Task list, contracts, and gates: `specs/deliverable-first/tasks.md`.

## The convergence contract

Reviews of this diff verify against: the failure-chain table (6/6 rows closed), AC-3/AC-4
(zero behaviour change for artifacts/projects carrying none of the new grammar), and SC-6
(no existing assertion weakened outside the one named re-contract). Free-form hunting is
out of scope for the cluster reviews.
