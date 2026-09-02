# Plan — Harness inversion

**Spec:** `specs/harness-inversion/spec.md` · **Class A** (multi-task, real design decisions: lane semantics, ladder defaults, which herdr moments earn their cost) · inline-planned, human present · **Stakes: standard**.

## Technical context

- **Edit target:** this repo (`netdust-plugins`), plugin `plugins/netdust-agent`, plus one
  read-only consumer relationship to `plugins/netdust-core/skills/herdr-orchestration`
  (cited, never edited here). Never the cache.
- **Test runner:** `bash plugins/netdust-agent/tests/run.sh` — 22 self-runner modules
  (`def run() -> list[(bool, desc)]`), no pytest dependency. Baseline on this box:
  21 pass, 1 module (`test_integration_contract`) reports its live-corpus seam as
  skipped because `~/Sites/netdust-wp-manager` is not present; that is the recorded
  environment state, not a regression, and it must read the same after every cluster.
- **Checker architecture (ground-truthed):** `bin/gate-check.py` (2013 lines) —
  `check_*(text, f)` functions over `task_blocks()` / `parse_clusters()` /
  `parse_behaviour_clusters()`, fenced blocks stripped first, `run_checks()` the single
  call order. The lane is one more attribute of a parsed cluster; every lane-aware check
  reads it from the parser, none re-parses.
- **Hook architecture (ground-truthed):** `hooks/subagent-stop.py` already tolerates the
  cluster's named RED mid-cluster via `cluster-open` / `cluster-close` ledger events
  (deliverable-first FR-8, tests in `test_subagent_stop_evidence.py`), and already
  enforces the sensitive-path floor on a solo close. The behaviour lane needs NO hook
  change: a behaviour-lane implementer close is a `solo`-class close whose only
  tolerated red is the cluster RED. That is the whole reason the lane is cheap to land.
- **Cost tool (ground-truthed):** `bin/run-cost.py` walks `~/.claude/projects/**/*.jsonl`,
  sums `message.usage` per assistant line, joins to run-log windows. Assistant lines
  carry `message.model` in the same object — the column is a read of a field already
  in hand.
- **Model contract (ground-truthed against the Claude Code docs, 2026-09-02):** subagent
  frontmatter `model:` accepts an alias (`sonnet` / `opus` / `haiku` / `fable`), a full
  model id, or `inherit`; omitted = inherit. Resolution order is dispatch-time `model`
  parameter → agent frontmatter → `CLAUDE_CODE_SUBAGENT_MODEL` → main model, so the
  controller's dispatch wins over the file. Skills and commands accept `model:` and
  `effort:` in their frontmatter too (turn-scoped). Whether a PreToolUse hook sees the
  dispatch `model` in `tool_input` is NOT documented — so v1 has no hook enforcement of
  the ladder; the enforcement is the measured `model` column in `run-cost.py` (FR-12)
  and the ladder's single home (FR-11). Docs: `code.claude.com/docs/en/sub-agents`,
  `…/skills`.
- **herdr contract:** syntax is read at run time from `herdr --skill`; this plan pins
  only the DECISIONS (which moment, which primitive, when not to). `HERDR_ENV=1`,
  `$HERDR_PANE_ID` / `$HERDR_TAB_ID` / `$HERDR_WORKSPACE_ID` are the detection surface
  the netdust-core skill already documents.

**Loop budget: ~16 iterations** (11 tasks + 4 review clusters + one fix round on Cluster A).

## Stakes

**Stakes: standard** — a wrong gate or skill text ships bad guidance to every future
session on every project, visibly and recoverably (git revert of a markdown/py file); no
money, data, access, or irreversible operation anywhere in the diff. The one enforcement
boundary in reach (the sensitive-path floor in `subagent-stop.py`) is not edited.

### Per-cluster stakes

| Cluster | Stakes | Why |
|---|---|---|
| A — the checker lane grammar | **standard** | a wrong check blocks or admits plans loudly; caught at first use, reverted in one commit; FR-3 keeps the unsafe direction a FAIL |
| B — machine layer | **standard** | run-cost is read-only telemetry; session-start appends two lines under an env flag; agent frontmatter is declarative |
| C — the spine texts | **standard** | prose routing; every mechanical gate beneath it still holds |
| D — the record | **low** | calibration, version, self-hosting re-shape |

## First working version

**Task:** T01
**Demonstrates:** a human runs one command on a fixture `tasks.md` carrying
`Lane: behaviour` and watches the checker accept it, then adds `auth/Guard.php` to one
member's files and watches it refuse, naming the task and the term — the lane is real,
and the unsafe direction is closed, before any prose changes.
**Verify by:** `python3 plugins/netdust-agent/bin/gate-check.py <fixture dir>` → exit 0,
then exit 1 with a `cluster-lane` finding.

## Constitution check

Simplicity first: no new hook, no new script, no new artifact type. The lane is one
attribute on an existing parsed structure; the behaviour block, the RED tolerance, the
sensitive-path floor, the `Artifact-diff:` comparison and the branch review all exist and
are REUSED. Two new reference files (`model-ladder.md`, `herdr-moments.md`) are the
single homes the plugin's own "one canonical statement per rule" convention demands;
every skill cites, none restates. Net effect on a behaviour-lane feature: fewer
dispatches, fewer fields, fewer panels — nothing added to the ceremony anywhere.

## Threat model [GATE]

N/A — no 1a trigger surface: parsed artifacts are repo-local files the team authors;
`run-cost.py` stays strictly read-only over local transcripts and emits counts plus a
model name; herdr commands execute in the operator's own session with the operator's
permissions and are gated on an env flag the operator's terminal sets. The sensitive-path
floor is unchanged; FR-3 and FR-7 route sensitive paths INTO the contract lane.

## Acceptance flows [GATE]

N/A — the spec flags no user-facing surface. The behavioural contract is the named test
cases per task plus the self-hosting gate-check run (SC-3).

## Architecture invariants touched [GATE]

This repo carries no `ARCHITECTURE-INVARIANTS.md`. The harness's own load-bearing invariant
— **no self-attestation: a gate is proven by an artifact property or a scraped result,
never by an agent's claim** — is preserved: the lane is an artifact property checked by
the machine; the unsafe direction (a boundary file under `Lane: behaviour`) is a FAIL the
planner cannot talk past; a behaviour-lane close is still a scraped suite run through the
existing hook. The invariant the plugin's CLAUDE.md states for prose — "a netdust skill
that restates superpowers is a defect" — is extended to the two new single homes (SC-4,
SC-6 grep at the Cluster C/D gates).

## Spec-premise ground-truth [GATE]

- **G1 — cluster parsing:** `parse_clusters()` (`gate-check.py:668`) yields one dict per
  `### Cluster` heading with `tier` read from the heading label or the marker line;
  `parse_behaviour_clusters()` (`:1426`) reads the block lines between the heading and
  the first task. The lane line follows the same "between heading and first task"
  placement so both parsers can read it with one regex.
- **G2 — the four per-task checks** `check_task_tiers` / `check_test_author_mode` /
  `check_proven_by` / `check_unit_test_contract` each walk `task_blocks()` independently
  and know nothing about clusters; lane-awareness means passing them the set of
  behaviour-lane member ids (the `behaviour_covered_task_ids()` pattern, `:1532`) and
  skipping those — no restructuring.
- **G3 — the detectors** `FILES_SECURITY` / `PROSE_SECURITY` / `_boundary_hit()`
  (`:884–904`) exist and are calibrated against the corpus; FR-3 reuses `_boundary_hit`
  verbatim, so a lane FAIL and a `security-boundary-mode` WARN can never disagree about
  what a boundary is.
- **G4 — review markers:** `check_review_gates` / `check_review_tiers` (`:715–756`) read
  `parse_clusters()`; FR-5 filters that list by lane and adds one file-level marker check.
- **G5 — the hook needs nothing:** `subagent-stop.py` docstring lines 10–60 + the FR-8
  transition tests confirm mid-cluster tolerance of exactly the ledger-named RED and the
  sensitive-path floor on solo closes. A behaviour-lane dispatch declares itself
  `role=implementer`; the floor applies as-is.
- **G6 — model contract:** see Technical context; dispatch parameter wins, hook visibility
  undocumented. Consequence taken: no PreToolUse ladder check in this spec.
- **G7 — herdr decisions already written:** `netdust-core/skills/herdr-orchestration/SKILL.md`
  carries the channel split, topology-per-checkout, `bat` tab recipe, watcher script,
  session-review role and the dispatch-brief recipe. `herdr-moments.md` cites those by
  section and adds ONLY the mapping to harness stages. The building lesson of 2026-08-09
  (parallel dispatch in one checkout) names the exact failure FR-15 prevents.
- **G9 — herdr vs dev-stack disagree on the base branch:**
  `herdr-orchestration/SKILL.md` ("Decision — topology follows the checkout") shows
  `herdr worktree create … --base master --branch fix/<name>`; `dev-stack/SKILL.md`
  ("Git branch strategy") says features branch from `development`, hotfixes from `main`,
  `make feature` / `make hotfix` do it correctly, and branching elsewhere "ships every
  unfinished change sitting there". The herdr line is an example for a framework fix on a
  master-default repo, not a rule; FR-21 makes dev-stack the authority and reads the base
  from `site.yml`.
- **G8 — run-cost fields:** `bin/run-cost.py` reads `message.usage` from assistant lines;
  the sibling key `message.model` is present on the same records in this box's own
  transcripts (checked on the current session's jsonl).

## Phases & review clusters [GATE]

Single phase, four clusters, ordered so the checker (the demo) lands first, the machine
layer second, the prose that cites both third, the record last:

- **Cluster A — the checker lane grammar** (T01–T03, standard, provisional tier
  STANDARD): lane parsing + FR-3/FR-4 verdicts; lane-aware skipping of the four per-task
  checks; lane-aware review markers + `── BRANCH REVIEW ──`.
- **Cluster B — machine layer** (T04–T06, standard, STANDARD): `run-cost.py` model
  column; `session-start.sh` herdr lines; agent frontmatter `model:` + `model-ladder.md`
  with its frontmatter test.
- **Cluster C — the spine texts** (T07–T10, standard, LIGHT): building (lane execution,
  ladder citations, herdr moments); implementer/test-author/reviewer bodies; planning
  seam + intake + testing-workflow; `herdr-moments.md` + `/loop` doorbell + compounding
  Pass B + `/shakeout` FR-8.
- **Cluster D — the record** (T11, low, LIGHT): calibration entry, eval cases, version
  bump, and the self-hosting re-shape of this feature's own `tasks.md` to the lane
  grammar.

Task list, contracts and gates: `specs/harness-inversion/tasks.md`.

## The convergence contract

Reviews of this diff verify against: AC-2 (zero new findings on the existing corpus —
no lane lines means today's checker), FR-3 (the unsafe direction is a FAIL, never a
WARN), SC-4/SC-6 (single homes, no restatement), and the standing rule that no skill
text promises an enforcement the machine does not perform (the ladder is measured, not
hook-enforced — the text must say so). Free-form hunting is out of scope.
