# Calibration index — every war story, told once

**The rule:** a calibration incident has ONE full home (listed below); everywhere else
cites its slug — `(calibration: traverse-clause)` — optionally pointing here. New skill
prose never retells an indexed incident; it cites. This file is an INDEX, not a catalog:
one line of lesson per incident, the full story stays at its canonical home.

All incidents: Folio, Phases 1–3 (2026-05 → 2026-06) unless noted.

## Plan-time gate calibrations

| Slug | Date | Lesson (one line) | Full story |
|---|---|---|---|
| `traverse-clause` | 05-28 | CR-8..11: every route had a guard, no test asserted the denial — cross-tenant reads shipped green; ~80 findings, 7.7× review-to-implementation. Converge visibility into ONE helper; assert denials. | `skills/test-effectiveness/references/failure-modes.md` (mode 5); attack taxonomy in `skills/threat-modeling/SKILL.md` |
| `subphase-b-retrofit` | 05-28 | 7 tasks of BYOK/provider-URL code shipped with no threat model → 2 review rounds, ~30 security findings (SSRF IPv6-mapped bypass, baseUrl exfil). Prevention = 15 min; remediation = 15 min + the rounds. | `skills/threat-modeling/SKILL.md` (calibration data) + its `lessons.md` |
| `drop-workspace-retrofit` | 06-05 | Threat model retrofitted after review on an obviously-triggering surface: 2 rounds / 11 findings vs the proactive phases' 1 round / 3–4. The catalog wasn't the hole; applying it late was. | `skills/planning/SKILL.md` (gate 1a) |
| `class-d-gap` | 06-03 | A one-line `validatePublicUrl` SSRF-guard edit shipped without a threat model — the trigger was keyed to plan-writing only. Ad-hoc security diffs get the gate too (Class D). | `skills/planning/SKILL.md` (gate 1a) + `skills/harnessed-development/SKILL.md` (intake D) |
| `tableview-premise` | 05-30 | "Runs render through the existing TableView" survived spec + plan + handoff and was false; one grep would have falsified it. Ground-truth every reuse-X-for-Y premise (1c). | `skills/planning/SKILL.md` (gate 1c) |
| `teardown-cluster` | 06-05 | A 7-task `__system`-teardown phase behind ONE gate ran flat, merged two tasks into an uncommitted blob, and nearly reviewed irreversible drops beside refactors. Clusters ≤4; irreversible = solo (1f). | `skills/planning/SKILL.md` (task-shaping gate, 1f facet) |
| `tokens-mint-bypass` | 06-01 | The one CRITICAL in a "tight" auth audit was the single write path bypassing the `roleToScopes` convergence point — latent for months. Name the convergence point; the bypass becomes a one-line finding. | `skills/architecture-invariants/SKILL.md` (calibration data) |
| `background-planner-pivots` | 07-04 | Sofie session: plan approved 12:24, invalidated 12:34 ("Sofie has nothing to do with Hermes"), second pivot 13:09 (dev/prod split) — each correction cost a background-agent round-trip (~14 and ~7 min) plus check-on-agent wakeups, while the pre-unattended review ladder caught 4 real loop-breakers that same day (incl. a live-ACL-tested lockout) — the highest-ROI gate of the day. Resolution: presence-aware planning (D3) — plan inline while the human is steering; dispatch background + run the full ladder only before unattended execution. | `skills/planning/SKILL.md` (`<stage_persona>` + seam) |

## Execution calibrations

| Slug | Date | Lesson (one line) | Full story |
|---|---|---|---|
| `subphase-a-0of7` | 06-04 | 0/7 subagents re-invoked `testing-workflow` under a weak dispatch one-liner, yet the work was correct — the auditable gate is the structured Test-evidence + STATUS blocks, not a Skill re-invocation. | `skills/building/SKILL.md` (integration, calibration data) |
| `self-grading-split` | 07-04 | The implementer authored its own Tier-A test and self-reported the gating evidence — self-grading: the test drifts to fit the code, the denial path vanishes, a guard gets self-excused to Tier B. Fixed by the test/dev split: an independent `test-author` writes RED from the contract before the implementer greens it, two agents, two commits. | `skills/building/SKILL.md` (`<test_dev_split>` + integration) |
| `tier-conditional-split` | 07-04/05 | The unconditional split (`self-grading-split`'s fix) cost 2× dispatches + 4–6 min sequential latency per task on the run-observability run; its only incident was the test-author's own defective fixtures on T04 (~15 min + 3 extra dispatches to resolve) — not a caught coder-self-grading bug. The cluster review gates + phase-close test-effectiveness audit independently caught all 5 real reproduced defects that run, without the split's help. Resolution: the split became tier-conditional via the machine-checked `Test-author:` field (D1 rule — split iff Tier A **and** a security-boundary category); the no-self-downgrade invariant (no run-time agent may re-decide its own task's mode) keeps the split/solo boundary out of any run-time agent's hands. | `skills/building/SKILL.md` (`<test_dev_split>` + integration); `skills/testing-workflow/SKILL.md` ("Who authors vs who greens") |
| `plan-drift-4x` | 05→06 | FOUR consecutive sub-phases (A, C.2, C.3, Phase C) hit plan-vs-source drift caught only by per-task ground-truthing (Step 2.5) — signatures, an entire nonexistent provider API, renamed fields. | `skills/building/SKILL.md` (Step 2.5) |
| `one-cycle-per-bug` | 05-30 | Sub-phase F: bundling review findings I2+I3 into one debug cycle drifted the process even though outcomes were sound. One systematic-debugging invocation per bug. | `skills/building/SKILL.md` (Step 2.7) |
| `sibling-sites` | 05-30 | Sub-phase C.1: every cross-cutting fix had 1–2 sibling sites needing the same change, missed by the primary fix. Enumerate the audit surface in the plan (1e). | `skills/planning/SKILL.md` (gate 1e) |

## Green-but-broken calibrations (the seven failure modes + edge classes)

Nineteen defects reached review/QA **while the unit suite was green** — all
coverage-of-the-dangerous-path escapes. Full per-mode stories:
`skills/test-effectiveness/references/failure-modes.md`.

| Slug | Date | Lesson (one line) | Full story |
|---|---|---|---|
| `stale-fixture-f11` | 05-27 | `author` slug→id changed server-side; legacy fixtures kept three broken UI surfaces green (mode 1). | failure-modes.md mode 1 |
| `migrate-at-boot` | 05-25 | Migration green in the fresh-DB harness, 500 on the long-lived dev DB (mode 2). | failure-modes.md mode 2 |
| `refetch-toggle-blank-editor` | 06-01 | React Query flipped `doc` to `undefined` mid-session; the draft buffer blanked the editor — jsdom never reproduced the toggle (mode 3; also edge class 1, empty/zero). | failure-modes.md mode 3; `skills/feature-acceptance/SKILL.md` edge 1 |
| `unmounted-guard-f1f3` | 05-27 | Scope check present on the MCP path, absent on its HTTP twin; SSE mounted under `wScope` so `requireResource` never ran (mode 4). | failure-modes.md mode 4 |
| `phase-b-seam-blockers` | 06-02 | Two feature-nullifying merge-blockers survived all seven per-task reviews because every test stopped at a seam (mode 4). | failure-modes.md mode 4 |
| `inlineedit-jsdom-race` | 05-23 | Keystroke-before-focus race broke in the real browser; RTL's `userEvent.type` selects-then-types, masking it in every jsdom test (mode 6). Drive UI in the real browser. | failure-modes.md mode 6; `skills/feature-acceptance/SKILL.md` driving layers |
| `bun-sqlite-no-rollback` | — | `db.transaction(async …)` did NOT roll back on an awaited throw at the driver+ORM seam; clients diverged until reload (mode 6; edge class 6, mid-flow failure). | failure-modes.md mode 6; `skills/feature-acceptance/SKILL.md` edge 6 |
| `setinterval-reentrancy` | — | Dispatcher + poller `setInterval` without a re-entrancy latch; passed whenever the scheduler cooperated (mode 7). | failure-modes.md mode 7 |
| `double-submit-a11y-collision` | — | Empty-state CTA and sheet submit shared an accessible name; rapid double-click submitted mid-transition. Single-click tests never reproduce it (edge class 4). | `skills/feature-acceptance/SKILL.md` edge 4 (sole home) |
| `route-vs-service-guard` | — | A route-boundary write guard saw the payload, but schema defaults ran a SECOND mutation pass at the service boundary — incomplete by construction. Drive denials through the full chain (edge class 2). | `skills/feature-acceptance/SKILL.md` edge 2 (sole home) |

## Single-home extras (indexed for citation; no dedup needed)

- `gt-gte-race` (05-29), `migrate-journal-idempotent` (05-28), `test-count-delta-13x`
  (06-02), `tier-diagnosis` (06-04) — `skills/testing-workflow/lessons.md`
- `evaluate-stamp-skip` — `commands/evaluate.md`
- `milkdown-ast-not-dom` (05-24), `narrow-key-invalidation` (05-24) —
  `skills/test-effectiveness/references/failure-modes.md`
- `state-md-bloat` (175 KB STATE.md / 100 KB preamble) — `hooks/session-start.sh`
- `mid-sentence-truncation` (06-05) — `hooks/session-stop.py`
