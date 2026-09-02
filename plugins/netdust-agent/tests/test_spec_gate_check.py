"""
test_spec_gate_check.py — verifies the harness gate checker (bin/gate-check.py).

The checker is the MECHANICAL backstop for the harness's non-test gates: it must FAIL a
spec/plan/tasks set that skips a gate, and PASS one that carries them. The load-bearing
case (ADR Phase B gate): a spec that flags a security surface but whose plan leaves the
## Threat model as N/A must FAIL — that is the proactive 1a gate the harness exists to keep.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).parent.parent / "bin" / "gate-check.py"

# ── fixtures ──────────────────────────────────────────────────────────────────

SPEC_TRIGGERED = """# Feature Specification: Webhook receiver

## Success criteria
- **SC-1:** 0 requests reach an RFC1918 target

## Security-relevant surfaces
- [x] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] None of the above

## Open questions / [NEEDS CLARIFICATION]
[List remaining ambiguities as `[NEEDS CLARIFICATION: …]`. This section must be empty.]
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

SPEC_CLEAN_NOSEC = """# Feature Specification: Rename a label

## Success criteria
- **SC-1:** 1 label changed, 0 other copy touched

## Security-relevant surfaces
- [ ] User-controlled URLs / server-side outbound requests
- [x] None of the above

## Clarifications
- Q: which label? → A: the footer copyright label
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

SPEC_WITH_UNRESOLVED = """# Feature Specification: Importer

## Success criteria
- **SC-1:** a 10 MB CSV imports in under 30 seconds

## Functional requirements
- FR-1: import a CSV [NEEDS CLARIFICATION: max file size?]

## Security-relevant surfaces
- [x] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# ── `success-criteria` fixtures (the spec-authoring artifact contract) ───────
# The gate exists so shake-out signs off against a comparison rather than a
# judgement call: every SC line must carry a number. Measurability is tested
# crudely — "the line contains a digit" — which admits `100% of users are
# happy` but catches the failure mode that actually occurs: prose success
# criteria nobody can sign off against.

SPEC_SC_MEASURABLE = """# Feature Specification: Course publishing

## Success criteria

> Feature-level, technology-agnostic, and **measurable** — every line carries a number.

- **SC-1:** an editor publishes a course module in under 3 minutes, unassisted
- **SC-2:** the module list renders in under 500 ms at 4,000 users

## Security-relevant surfaces
- [x] None of the above
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# Mixed: SC-1 carries a number, SC-2/SC-3 are prose. FAIL must name the offenders,
# not just report a count — the author needs to know WHICH line to rewrite.
SPEC_SC_VAGUE = """# Feature Specification: Course publishing

## Success criteria

- **SC-1:** an editor publishes a course module in under 3 minutes, unassisted
- **SC-2:** editors find the publishing flow intuitive
- **SC-3:** the module list feels fast

## Security-relevant surfaces
- [x] None of the above
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# The section present but never filled in — bracketed `[e.g. …]` bodies, the shape an
# agent produces when it copies guidance instead of answering it. Placeholder text is not
# a criterion, so this must FAIL rather than PASS on its own digits ("3 minutes", "500 ms").
# (This case is why there is no spec template: a skeleton's untouched state must not pass.)
SPEC_SC_TEMPLATE_UNTOUCHED = """# Feature Specification: [FEATURE NAME]

## Success criteria

> Feature-level, technology-agnostic, and **measurable** — every line carries a number.

- **SC-1:** [e.g. an editor publishes a course module in under 3 minutes, unassisted]
- **SC-2:** [e.g. the module list renders in under 500 ms at 4,000 users]

## Security-relevant surfaces
- [x] None of the above
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# A spec that predates the contract carrying this section at all. The silent WARN floor is
# gone: total absence FAILs unless the artifact states a legacy waiver out loud — the waiver
# downgrades ABSENCE ONLY to a WARN that names it, so a genuinely old spec stays green while
# staying visible.
SPEC_PRE_TEMPLATE_NO_SC = """# Feature Specification: Rename a label

<!-- gate-check: legacy-artifact — authored 2026-05, before the Success criteria contract -->

## Problem / why

The footer copyright label reads 2019.

## Security-relevant surfaces
- [x] None of the above
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# ── `security-surfaces` fixtures — the arming switch for the plan's 1a gate ───
# THE case: an auth feature whose surface boxes were all left blank. Before this check,
# spec_security_triggered() returned nothing, the plan's `N/A` threat model PASSED, and
# gate-check printed "no spec surface flagged" as reassurance. Disarmed by inaction.
SPEC_SURFACES_ALL_BLANK = """# Feature Specification: Token minting endpoint

## Success criteria
- **SC-1:** a token mints in under 200 ms
- **SC-2:** 0 tokens issued to an unauthenticated caller

## Security-relevant surfaces
- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [ ] None of the above — *(state so explicitly)*
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# No section at all — same disarmed outcome, reached by omission rather than by blankness.
SPEC_SURFACES_MISSING = """# Feature Specification: Token minting endpoint

## Success criteria
- **SC-1:** a token mints in under 200 ms
"""

# Contradictory: a real surface AND "None of the above".
SPEC_SURFACES_CONTRADICTORY = """# Feature Specification: Token minting endpoint

## Success criteria
- **SC-1:** a token mints in under 200 ms

## Security-relevant surfaces
- [x] Auth / session / token / capability surfaces
- [x] None of the above — *(state so explicitly)*
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# ── `review-gate-marker` / `review-tier` fixtures (1f / 1h) ───────────────────
# Sized clusters, tiers declared, but NO STOP marker: `building` HALTs at the marker, so
# this runs the phase flat into the un-bisectable mega-diff (calibration: teardown-cluster).
TASKS_NO_REVIEW_GATE = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier B] a  (f: a)
      Unit test: no unit test: Tier B, glue
- [ ] T02 [Tier B] b  (f: b)
      Unit test: no unit test: Tier B, glue

### Cluster C2  (1 task · provisional tier: LIGHT)
- [ ] T03 [Tier B] c  (f: c)
      Unit test: no unit test: Tier B, copy edit
"""

# Markers present, but no cluster declares a provisional tier — `building` restates the
# tier at each gate and escalates one-way FROM it; with none there is nothing to restate.
TASKS_NO_REVIEW_TIER = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier B] a  (f: a)
      Unit test: no unit test: Tier B, glue

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, `/code-review`)*

### Cluster C2
- [ ] T02 [Tier B] b  (f: b)
      Unit test: no unit test: Tier B, glue

── REVIEW GATE ──  *(STOP: commit C2, `/integration`, `/code-review`)*
"""

# ── `unit-test-contract` fixtures (1d) ───────────────────────────────────────
# Partial presence: T02 has a tier and an author but states no contract — a tier marker
# with no target is where a denial path stops being tested.
TASKS_PARTIAL_UNIT_TEST = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects RFC1918; allows a public https URL
- [ ] T02 [Tier A] parse the payload  (files: lib/parse.ts)

── REVIEW GATE ──  *(tier STANDARD)*
"""

# A Tier A task waiving its test outright — the erosion the tier system exists to stop.
TASKS_TIER_A_WAIVES_TEST = """# Tasks: x

### Cluster C1  (1 task · provisional tier: FULL)
- [ ] T01 [Tier A] rewrite the auth token store  (files: db/tokens.sql)
      Unit test: no unit test: it is mostly SQL

── REVIEW GATE ──  *(tier FULL)*
"""

# ── `requirement-coverage` fixtures — the one cross-artifact check ────────────
# Asks whether each FR-n / SC-n is visible in the task list at all. Retro-compat: a task
# list citing NO id is pre-convention and WARNs (both live specs/ dirs are that shape);
# once ANY id is cited the convention is in use, so a gap FAILs.

SPEC_WITH_REQS = """# Feature Specification: Course publishing

## Success criteria
- **SC-1:** an editor publishes a module in under 3 minutes

## Functional requirements
- **FR-1:** system MUST publish a module. Source: the human, 2026-06-01: "publish".
- **FR-2:** system MUST reject an unauthorised editor. Source: invented — approved
  2026-06-01 (review note).
- **FR-3:** system MUST log every publish. Source: the audit brief (2026-06-01).

## Security-relevant surfaces
- [x] None of the above
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

TASKS_COVERS_ALL_REQS = """# Tasks: Course publishing

### Cluster C1  (3 tasks \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier A] publish a module (FR-1, SC-1)  (files: publish.ts)
      Test-author: solo \u2014 A-lite, pure orchestration, no security-boundary category
      Unit test: publishes in one call; denial path: unauthorised editor rejected
- [ ] T02 [Tier A] authorisation guard (FR-2)  (files: guard.ts)
      Test-author: split
      Unit test: rejects a non-editor; allows an editor
- [ ] T03 [Tier B] publish audit log (FR-3)  (files: log.ts)
      Test-author: solo \u2014 Tier B
      Unit test: no unit test: Tier B, wiring over the existing logger

**Integration gate (C1):** an editor publishes end to end and the log carries the entry; a
non-editor's attempt is refused and logged.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(STOP: commit C1 \u2014 tier STANDARD)*
"""

# FR-1 cited, FR-2 / FR-3 / SC-1 traced to nothing → the convention IS in use, so FAIL.
TASKS_COVERS_SOME_REQS = """# Tasks: Course publishing

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier A] publish a module (FR-1)  (files: publish.ts)
      Unit test: publishes in one call; denial path: unauthorised editor rejected

\u2500\u2500 REVIEW GATE \u2500\u2500  *(STOP: commit C1 \u2014 tier STANDARD)*
"""

# No id cited anywhere — the live-corpus shape, now carrying the explicit waiver that
# keeps it a WARN. Without the marker, total absence FAILs like everything else (10q-b).
TASKS_CITES_NO_REQS = """# Tasks: Course publishing

<!-- gate-check: legacy-artifact — task list predates the FR-n citation convention and the 0.8.0 Test-author field -->

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier A] publish a module  (files: publish.ts)
      Unit test: publishes in one call; denial path: unauthorised editor rejected

**Integration gate (C1):** an editor publishes end to end; a non-editor is refused.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(STOP: commit C1 \u2014 tier STANDARD)*
"""

# ── `security-boundary-mode` fixtures — D1's no-self-downgrade, made visible ──
# test-author-mode accepts ANY reason text after `solo —`, so a Tier-A auth task talked down
# to "A-lite, pure transform" passes it exactly like a legitimate one. These WARN.
TASKS_TIER_A_SOLO_ON_BOUNDARY = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier A] rewrite the token store  (files: db/tokens.sql)
      Test-author: solo \u2014 A-lite, pure transform, no security-boundary category
      Unit test: replays the migration on a seeded fixture

**Integration gate (C1):** a token minted before the rewrite still authenticates after it.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# Correct mode on the same task — no warning.
TASKS_TIER_A_SPLIT_ON_BOUNDARY = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier A] rewrite the token store  (files: db/tokens.sql)
      Test-author: split
      Unit test: replays the migration on a seeded fixture

**Integration gate (C1):** a token minted before the rewrite still authenticates after it.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# Tier B on a security-boundary file with NOTHING proving it — a guard nobody checks.
# Before 0.16 this WARNed on the TIER alone; it now WARNs on the ABSENT EVIDENCE, which is
# what the finding was always reaching for.
TASKS_TIER_B_ON_BOUNDARY = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier B] tidy the session guard  (files: lib/session-guard.ts)
      Test-author: solo \u2014 Tier B
      Unit test: no unit test: Tier B, tidy-up only

**Integration gate (C1):** an expired session is still refused after the tidy-up.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# The same shape with its presence proof NAMED. This is the `contact-page-8k` fix: a direct
# call to a hardened framework primitive carries no decision of its own, so it owes a presence
# proof, not a bespoke behavioural test — and naming that proof must draw no warning, or every
# form handler in a WordPress feature gets pushed up to Tier A + split.
TASKS_TIER_B_ON_BOUNDARY_PROVEN = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier B] call the nonce check on the contact handler  (files: src/contact-nonce.php)
      Test-author: solo \u2014 Tier B
      Proven by: machine gate \u2014 the project gate asserts a nonce on every handler
      Unit test: no unit test: Tier B, direct call to a framework primitive

**Integration gate (C1):** the contact handler refuses a request with no nonce end to end.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# Tier B and `Proven by: new test` contradict each other — the tier says no bespoke test,
# the evidence line says one is being written. One of them is wrong.
TASKS_TIER_B_ON_BOUNDARY_CONTRADICTORY = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier B] tidy the session guard  (files: lib/session-guard.ts)
      Test-author: solo \u2014 Tier B
      Proven by: new test
      Unit test: no unit test: Tier B, tidy-up only

**Integration gate (C1):** an expired session is still refused after the tidy-up.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# THE EXEMPTION (F2): Tier B + an `Integration test:` contract + `Proven by: new test` is
# NOT a contradiction \u2014 it is the designed WP wiring path (`Integration test:` became
# first-class in 0.15): the "new test" IS the integration test the contract line states.
# The contradiction WARN is reserved for a waived Tier B claiming a test nobody is writing.
TASKS_TIER_B_BOUNDARY_INTEGRATION_NEW_TEST = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier B] cron wiring for the token sweep  (files: inc/token-cron.php)
      Test-author: solo \u2014 Tier B
      Proven by: new test
      Integration test: the scheduled sweep fires once and expired rows are gone; denial: live rows survive

**Integration gate (C1):** the sweep is scheduled exactly once and fires on the real cron chain.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# F1 regression: an unparseable bullet id (`T07b` \u2014 TASK_LINE requires `T\\d+\\b`) between
# two tasks is NOT a continuation of the task above it. A walker that only ends a block at a
# PARSEABLE task line / heading attributes the malformed bullet's Test-author:/Proven by:
# lines to T01 and grades T01 with another task's evidence \u2014 silently, on every
# block-based check at once. One boundary rule, shared by every block-based check: any
# column-0 bullet ends the block (the rule `check_unit_test_contract` already carried on
# main, ae65211).
TASKS_MALFORMED_BULLET_LEAK = """# Tasks: x

### Cluster C1  (2 tasks \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier B] wire the session refresh call  (files: lib/session-refresh.ts)
      Unit test: no unit test: Tier B, direct call to a framework primitive
- [ ] T07b [Tier B] malformed id \u2014 these lines belong to NO task
      Test-author: solo \u2014 Tier B
      Proven by: machine gate \u2014 the auth gate asserts refresh on every route
      Unit test: no unit test: Tier B, covered elsewhere
- [ ] T02 [Tier B] render the badge  (files: src/badge.tsx)
      Test-author: solo \u2014 Tier B
      Proven by: framework \u2014 typed lib, presence via the suite
      Unit test: no unit test: Tier B, presentational

**Integration gate (C1):** the refresh call and the badge render compose on a live route.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier STANDARD)*
"""

# The calibration cases the live corpus produced: `auth` inside test-AUTHor.md, `acl` inside
# performance-orACLe.md. Doc-editing tasks on this repo's own files must stay silent, or the
# WARN becomes noise nobody reads.
TASKS_BOUNDARY_FALSE_FRIENDS = """# Tasks: x

### Cluster C1  (2 tasks \u00b7 provisional tier: LIGHT)
- [ ] T01 [Tier B] update the agent preambles  (files: agents/test-author.md, agents/implementer.md)
      Test-author: solo \u2014 Tier B
      Unit test: no unit test: Tier B, agent-prose edit
- [ ] T02 [Tier B] retune a reviewer persona  (files: agents/performance-oracle.md)
      Test-author: solo \u2014 Tier B
      Unit test: no unit test: Tier B, agent-prose edit

**Integration gate (C1):** the reviewer personas still load and dispatch unchanged.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier LIGHT)*
"""

# ── 1g fixtures: `user-facing-surfaces` (arming switch) + `acceptance-flows` ──
# The 1g twin of the security fixtures above, and it exists for the same reason: `planning`
# requires an `## Acceptance flows` matrix for user-facing work, `building` Stage 3 /
# `/shakeout` / `shakeout-qa` / `test-author` all READ it out of the plan — and nothing
# checked it, because no spec field said "this is user-facing" for a check to key on.

SPEC_USER_FACING = """# Feature Specification: Invoice wizard

## Success criteria
- **SC-1:** an editor issues an invoice in under 2 minutes

## Security-relevant surfaces
- [x] None of the above

## User-facing surfaces
- [x] A form / wizard / multi-step flow
- [ ] A view / screen / page
- [ ] None of the above
"""

SPEC_USER_FACING_ALL_BLANK = """# Feature Specification: Invoice wizard

## Success criteria
- **SC-1:** an editor issues an invoice in under 2 minutes

## Security-relevant surfaces
- [x] None of the above

## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [ ] A CRUD surface
- [ ] An endpoint a client or agent drives
- [ ] None of the above
"""

SPEC_USER_FACING_CONTRADICTORY = """# Feature Specification: Invoice wizard

## Success criteria
- **SC-1:** an editor issues an invoice in under 2 minutes

## Security-relevant surfaces
- [x] None of the above

## User-facing surfaces
- [x] A form / wizard / multi-step flow
- [x] None of the above
"""

PLAN_FLOWS_NA = """# Implementation Plan: Invoice wizard

## Constitution check
- [x] ok

## Threat model
N/A — no surface flagged.

## Acceptance flows
N/A — small feature.

## Architecture invariants touched
N/A

## Spec-premise ground-truth
N/A

## Phases & review clusters
See tasks.md.

## Stakes
Stakes: standard — fixture

## Technical context
- **Loop budget:** ~6 iterations
"""

# A matrix with a header and separator but no filled-in row — the shape produced by copying
# the table skeleton without answering it. `/shakeout` has nothing to drive, so when 1g is
# armed this must FAIL exactly as an N/A does.
PLAN_FLOWS_EMPTY_TABLE = PLAN_FLOWS_NA.replace(
    "## Acceptance flows\nN/A — small feature.",
    """## Acceptance flows

| Flow | Expected | Edges |
|---|---|---|
""",
)

# Carries the 1j `## First working version` section since the deliverable-first gate
# landed — the same fixture amendment SPEC_TRIGGERED et al. received when the 1g
# user-facing sections and the Stakes: dial became mandatory grammar (the paired case's
# assertions are unchanged and unweakened; a user-facing plan simply must now name its
# first demoable slice to be a green fixture). Names TASKS_GOOD's T01: position 1,
# non-test file (lib/url.ts).
PLAN_FLOWS_FILLED = PLAN_FLOWS_NA.replace(
    "## Acceptance flows\nN/A — small feature.",
    """## Acceptance flows

| Flow | Expected | Edges |
|---|---|---|
| issue an invoice | PDF stored, editor sees it listed | empty: no line items → blocked with a message; denied: viewer role refused; re-entry: back-then-submit does not double-issue; concurrent: double-submit issues one; boundary: 0.00 total refused; mid-flow failure: storage error rolls the record back |
| email the invoice | recipient receives it once | empty: no recipient → blocked; denied: viewer cannot send; re-entry: resend is idempotent per invoice; concurrent: two sends deliver one; boundary: 500-char subject truncated; mid-flow failure: SMTP error leaves it queued, not sent |

## First working version

**Task:** T01
**Demonstrates:** a wired validator an editor can exercise from the first cluster
**Verify by:** drive the wizard's first screen and watch an RFC1918 target refused
""",
)

# ── `files-segment` fixtures — the declared task-line grammar, and what it protects ──
# THE demonstration case: a Tier-B task doing auth + payment work, with no `(files: …)`
# segment. Before this check it drew NO security-boundary WARN at all — `auth` and `payment`
# live in FILES_SECURITY (matched against the segment), not in the deliberately narrow
# PROSE_SECURITY, so with no segment there was nothing to match them against. Omitting the
# segment was a free way to blind the no-self-downgrade detector, which is why this FAILs
# rather than shrugging.
TASKS_NO_FILES_SEGMENT = """# Tasks: Invoice wizard

### Cluster C1  (2 tasks · provisional tier: LIGHT)
- [ ] T01 [Tier B] build the invoice wizard, auth, payment capture and email
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, glue
- [ ] T02 [Tier B] wire it up
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, glue

**Integration gate (C1):** the wizard issues an invoice end to end.

── REVIEW GATE ──  *(tier LIGHT)*
"""

# A planned yield point (`planning`: "destructive-migration approval, credentials, deploy
# confirmation") touches no files by nature. It is exempt, and the exemption is reported.
TASKS_HUMAN_YIELD_NO_FILES = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: FULL)
- [ ] T01 [Tier A] write the teardown migration  (files: migrations/002.sql)
      Test-author: split
      Unit test: replays on a seeded fixture; denial path: refuses to run twice
- [ ] T02 [HUMAN] [Tier B] approve the teardown migration
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, human approval step

**Integration gate (C1):** the migration is applied only after the recorded approval.

── REVIEW GATE ──  *(tier FULL)*
"""

# A `[HUMAN]` task ALSO marked `[P]` — the contradiction `planning` names explicitly ("a
# planned yield point, never `[P]`"). `[P]` tells the controller it may dispatch this task in
# parallel with its siblings, so a `[HUMAN]` task carrying it is a yield point an armed
# `/loop` can run straight past — the exact failure the mark exists to prevent.
# `check_clusters` already refuses `[P]` on an irreversible cluster; this is that rule one
# level down, on the task.
TASKS_HUMAN_PARALLEL = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: FULL)
- [ ] T01 [Tier A] write the teardown migration  (files: migrations/002.sql)
      Test-author: split
      Unit test: replays on a seeded fixture; denial path: refuses to run twice
- [ ] T02 [HUMAN] [P] [Tier B] approve the destructive migration
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, human approval step

**Integration gate (C1):** the migration is applied only after the recorded approval.

── REVIEW GATE ──  *(tier FULL)*
"""

# ── `integration-gate` fixtures (1d) ─────────────────────────────────────────
# A cluster with a STOP marker and a tier but nothing stated to verify ACROSS its tasks:
# `building` Step 2.8 HALTs here and runs `/integration` against no contract, which is where
# the review quietly degrades to reading the diff for style.
TASKS_NO_INTEGRATION_GATE = """# Tasks: x

### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
      Unit test: rejects RFC1918; allows a public https URL

── REVIEW GATE ──  *(tier STANDARD)*
"""

# The false-positive guard for the ANCHORED regex: a task's own prose mentions an integration
# gate ("covered by the cluster integration gate") but no line DECLARES one. An unanchored
# match would let a cluster satisfy this check by talking about it — the same
# mention-is-not-an-answer failure the security-surfaces check exists to refuse.
TASKS_INTEGRATION_GATE_ONLY_IN_PROSE = """# Tasks: x

### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, wiring only — covered by the cluster integration gate

── REVIEW GATE ──  *(tier STANDARD)*
"""

# The wp-manager corpus shape: a tasks.md whose clusters were authored before the per-cluster
# `Integration gate:` line existed — NO cluster carries one, and the file says so with a
# waiver. Total absence + waiver → WARN naming it; partial absence is never waived (the
# convention is in use, so a bare cluster is a defect — same absence-only rule as the floors).
TASKS_INTEGRATION_GATE_WAIVED = """# Tasks: x

<!-- gate-check: legacy-artifact — clusters authored before the per-cluster Integration gate: line; cross-task verification ran at each review gate via /integration -->

### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
      Unit test: rejects RFC1918; allows a public https URL

── REVIEW GATE ──  *(tier STANDARD)*

### Cluster C2  (1 task · provisional tier: LIGHT)
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, wiring only

── REVIEW GATE ──  *(tier LIGHT)*
"""

# ── `loop-budget` fixtures (1d loop-auditability) ────────────────────────────
# The bold form is what BOTH live plans actually write. run-score.py's regex did not match
# it, so the budget read as absent on 100% of the corpus and every run graded
# ungraded-by-default; this fixture pins the shape both readers must accept.
PLAN_BOLD_LOOP_BUDGET = """# Implementation Plan: x

## Constitution check
- [x] ok

## Threat model
N/A — no surface flagged.

## Architecture invariants touched
N/A

## Spec-premise ground-truth
N/A

## Phases & review clusters
See tasks.md.

## Stakes
Stakes: standard — fixture

## Technical context
- **Loop budget:** ~20 iterations — 12 tasks + 5 clusters + slack
## Acceptance flows
N/A — no user-facing surface.

"""

PLAN_NO_LOOP_BUDGET = """# Implementation Plan: x

## Constitution check
- [x] ok

## Threat model
N/A — no surface flagged.

## Architecture invariants touched
N/A

## Spec-premise ground-truth
N/A

## Phases & review clusters
See tasks.md.

## Stakes
Stakes: standard — fixture
## Acceptance flows
N/A — no user-facing surface.

"""

# A plan whose ONLY budget line sits inside a fence (quoting the template) — strip_fenced
# must run before the search, so this reads as ABSENT, not as a declared ~99 ceiling.
PLAN_FENCED_LOOP_BUDGET_ONLY = PLAN_NO_LOOP_BUDGET + """
## Technical context

The budget line goes here, e.g.:

```
- **Loop budget:** ~99 iterations
```
"""

# The run-observability shape: no `Test-author:` line anywhere, and an explicit waiver saying
# why. The waiver downgrades ABSENCE to a WARN that names it — never partial presence, never
# an invalid value, and never without a stated reason.
TASKS_WAIVED_NO_TEST_AUTHOR = """# Tasks: x

<!-- gate-check: legacy-artifact — predates the 0.8.0 Test-author field -->

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects RFC1918
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Unit test: no unit test: Tier B, glue
"""


# The stakes-less base: every required heading and the loop budget, but NO `Stakes:` line.
# The stakes fixtures below append their own `## Stakes` section to this; the reference
# PLAN_GATES_FULL adds a `standard` dial so the compliant set stays compliant now that a
# missing dial FAILs unless waived.
PLAN_GATES_BASE = """# Implementation Plan: Webhook receiver

## Constitution check  [GATE]
- [x] No RULES.md non-negotiable violated.

## Threat model  [GATE]
> guidance blockquote that should be ignored by the checker
### Attacks → Mitigations
1. **SSRF via webhook URL → resolves to RFC1918** → **shared validator in lib/url.ts, called from both routes**

## Architecture invariants touched  [GATE]
N/A — no convergence point touched.

## Spec-premise ground-truth  [GATE]
N/A — no reuse premise.

## Phases & review clusters  [GATE]
See tasks.md.

## Technical context
- **Loop budget:** ~6 iterations — 3 tasks + 2 clusters + slack
## Acceptance flows
N/A — no user-facing surface.

"""

PLAN_GATES_FULL = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: standard — a failure breaks the webhook flow for real users, recoverably
"""

# ── `stakes` fixtures — the consequence dial (1i) ─────────────────────────────
# The class dial scales PLANNING ceremony; this scales VERIFICATION effort. `low` buys the
# lightest verification in the harness, so the one place it must be unreachable is work the
# SPEC ITSELF flagged as security-relevant. `standard` there is fine — that is the honest
# classification for most input-handling features, and presence-vs-decision keeps it cheap.

PLAN_STAKES_LOW = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: low \u2014 worst case is a broken-looking page
"""

PLAN_STAKES_STANDARD = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: standard \u2014 a failure breaks a working feature for real users, recoverably
"""

PLAN_STAKES_UNREADABLE = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: medium-ish \u2014 somewhere in between
"""

PLAN_STAKES_HIGH_NO_REASON = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: high
"""

# F3 — the field tolerates any human reason-punctuation. A declared level must never be
# silently demoted to the no-line WARN because its reason used parentheses or a comma
# instead of an em-dash: the WARN reads "fall back to standard", which is a silent
# downgrade of a level somebody stated.
PLAN_STAKES_HIGH_PAREN_REASON = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: high (touches billing rows that cannot be replayed)
"""

PLAN_STAKES_STANDARD_COMMA_REASON = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: standard, breaks a working feature recoverably
"""

# F3 — a fenced `Stakes:` example (a plan quoting the template) is not a declared level.
# The plan below carries ONLY the fenced sample, so the verdict must be the no-line WARN.
PLAN_STAKES_FENCED_ONLY = PLAN_GATES_BASE + """
## Stakes  [GATE]

The dial goes here, e.g.:

```
Stakes: high — money on the line
```
"""

# I8 — under-calling stakes on a money/PII spec. WARN, never FAIL: the spec's own words
# are weaker evidence than its checked security boxes (which drive the `low` FAIL), but a
# `standard` plan on a spec that talks about payments deserves one visible question.
SPEC_MONEY = """# Feature Specification: Refund flow

## Success criteria
- **SC-1:** a refund lands back on the customer's card within 5 days

## Security-relevant surfaces
- [x] Auth / session / token / capability surfaces
- [ ] None of the above

## Notes
Handles payment provider webhooks and refund amounts.
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

# S9 — a money spec with NO checked security box (so the `low` FAIL stays out of the way),
# paired below with a reason-less `Stakes: low` plan: BOTH advisory WARNs (under-call +
# missing-reason) must surface. An early return after the first WARN would suppress the
# second — two independent questions, both owed to the reviewer.
SPEC_MONEY_NO_BOX = """# Feature Specification: Refund flow

## Success criteria
- **SC-1:** a refund lands back on the customer's card within 5 days

## Security-relevant surfaces
- [x] None of the above

## Notes
Handles payment provider webhooks and refund amounts.
## User-facing surfaces
- [ ] A view / screen / page
- [ ] A form / wizard / multi-step flow
- [x] None of the above

"""

PLAN_STAKES_LOW_NO_REASON = PLAN_GATES_BASE + """
## Stakes  [GATE]
Stakes: low
"""

# ── `proven-by` fixtures — the evidence ladder (1d) ───────────────────────────
# Name what ALREADY proves the property before writing a test. Rungs 1\u20133 assert the
# evidence lives elsewhere, so they must NAME it; rung 4 need not, because the task's own
# `Unit test:` line already carries the contract.

TASKS_PROVEN_BY_COMPLETE = """# Tasks: Contact page

### Cluster C1  (2 tasks \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier B] call the nonce check on the submit handler  (files: src/submit.php)
      Test-author: solo \u2014 Tier B
      Proven by: framework \u2014 wp_verify_nonce; presence asserted by the project security gate
      Unit test: no unit test: Tier B, direct call to a framework primitive
- [ ] T02 [Tier A] enforce the 2000-character message cap  (files: src/validate.php)
      Test-author: solo \u2014 A-lite, a project threshold, no security-boundary category
      Proven by: new test
      Unit test: a 2001-character message is refused, a 2000-character one is accepted

**Integration gate (C1):** the submit handler accepts a capped message end to end and refuses an over-cap one.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier STANDARD)*
"""

TASKS_PROVEN_BY_PARTIAL = """# Tasks: x

### Cluster C1  (2 tasks \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier A] enforce the message cap  (files: src/validate.php)
      Test-author: solo \u2014 A-lite, a project threshold
      Proven by: new test
      Unit test: a 2001-character message is refused
- [ ] T02 [Tier B] render the confirmation partial  (files: src/views/thanks.php)
      Test-author: solo \u2014 Tier B
      Unit test: no unit test: Tier B, presentational

**Integration gate (C1):** the cap and the confirmation compose on a live submit.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier STANDARD)*
"""

TASKS_PROVEN_BY_BAD_RUNG = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier B] render the confirmation partial  (files: src/views/thanks.php)
      Test-author: solo \u2014 Tier B
      Proven by: the suite covers it
      Unit test: no unit test: Tier B, presentational

**Integration gate (C1):** the confirmation renders on a live submit.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier STANDARD)*
"""

TASKS_PROVEN_BY_UNNAMED = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier B] render the confirmation partial  (files: src/views/thanks.php)
      Test-author: solo \u2014 Tier B
      Proven by: machine gate
      Unit test: no unit test: Tier B, presentational

**Integration gate (C1):** the confirmation renders on a live submit.

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier STANDARD)*
"""

PLAN_THREATMODEL_NA = """# Implementation Plan: Webhook receiver

## Constitution check  [GATE]
- [x] ok

## Threat model  [GATE]
N/A — small feature.

## Architecture invariants touched  [GATE]
N/A.

## Spec-premise ground-truth  [GATE]
N/A.

## Phases & review clusters  [GATE]
See tasks.md.

## Technical context
- **Loop budget:** ~6 iterations — 3 tasks + 2 clusters + slack

## Stakes  [GATE]
Stakes: standard — a failure breaks the webhook flow for real users, recoverably
## Acceptance flows
N/A — no user-facing surface.

"""

PLAN_MISSING_HEADING = """# Implementation Plan: Webhook receiver

## Constitution check  [GATE]
- [x] ok

## Threat model  [GATE]
1. **x → y** → **z**

## Spec-premise ground-truth  [GATE]
N/A.

## Phases & review clusters  [GATE]
See tasks.md.

## Technical context
- **Loop budget:** ~6 iterations — 3 tasks + 2 clusters + slack

## Stakes  [GATE]
Stakes: standard — a failure breaks the webhook flow for real users, recoverably
## Acceptance flows
N/A — no user-facing surface.

"""

# The reference COMPLIANT tasks.md: sized clusters, a STOP marker closing each, a
# provisional tier per cluster (1h), and a stated Unit test: contract per task (1d).
# It carries the tiers and contracts on the cluster headings / continuation lines exactly
# as the live specs/ dirs write them.
TASKS_GOOD = """# Tasks: Webhook receiver

## Phase 1 — receiver

### Cluster C1  (2 tasks · provisional tier: FULL)
- [ ] T01 [P] [Tier A] validate URL (SC-1)  (files: lib/url.ts)
      Test-author: split
      Unit test: rejects an RFC1918 target and an http:// downgrade; allows a public https URL
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, wiring only — covered by the cluster integration gate

**Integration gate (C1):** a real request reaches the handler through the wired route and an
RFC1918 target is refused end to end, not just at the validator.

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, `/code-review` — tier FULL)*

### Cluster C2 — (irreversible: drop legacy table) — solo
- [ ] T03 [Tier A] migration  (files: migrations/001.sql)
      Test-author: split
      Unit test: replays the migration on a seeded fixture; denial path: refuses to run twice

**Integration gate (C2):** the migration replays on a seeded copy and the receiver still serves
after the drop.

── REVIEW GATE ──  *(STOP: commit C2, `/integration`, `/code-review`, `/security-review` — tier FULL)*
"""

TASKS_NO_TIER = """# Tasks: x

### Cluster C1
- [ ] T01 [P] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire  (files: r.ts)
"""

TASKS_OVERSIZED = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] a  (f: a)
- [ ] T02 [Tier A] b  (f: b)
- [ ] T03 [Tier A] c  (f: c)
- [ ] T04 [Tier A] d  (f: d)
- [ ] T05 [Tier A] e  (f: e)
"""

TASKS_IRREVERSIBLE_PARALLEL = """# Tasks: x

### Cluster C1 — (irreversible: teardown) — solo
- [ ] T01 [P] [Tier A] drop table  (f: m.sql)
"""

# ── D1 `test-author-mode` fixtures (plan.md section D1 rules table) ──────────
# gate-check.py: from `plugins.netdust_agent... ` — imported directly below via
# importlib since this file already resolves CHECKER by path; check_test_author_mode
# is called DIRECTLY (unit-level) here — a deliberate choice to isolate the
# function's own branch logic from the CLI plumbing. It was authored as a RED
# sentinel shell at commit cee7b48 and wired into run_checks() at c8d5087 (see
# gate-check.py:376); the seam (subprocess) tests further down cover the CLI
# floor separately, now exercising the same wired check end-to-end.

import importlib.util as _ilu

_GATE_SPEC = _ilu.spec_from_file_location("gate_check_module", CHECKER)
_gate_check = _ilu.module_from_spec(_GATE_SPEC)
_GATE_SPEC.loader.exec_module(_gate_check)

# Row: "No task in the file carries a `Test-author:` line" → WARN, never FAIL
# (this is retro-compat: a run-observability-shaped tasks.md must never retro-fail)
TASKS_NO_TEST_AUTHOR_LINES = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire route  (files: routes.ts)
"""

# Row: "Some tasks carry it, some don't" → FAIL, naming the bare task ids
TASKS_PARTIAL_TEST_AUTHOR = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
- [ ] T02 [Tier B] wire route  (files: routes.ts)
- [ ] T03 [Tier B] docs tweak  (files: README.md)
      Test-author: solo — Tier B
"""

# Row: "Value not `split` or `solo…`" → FAIL
TASKS_INVALID_VALUE = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: maybe
"""

# Row: "[Tier A] task with `solo` and no reason text after a dash" → FAIL
TASKS_TIER_A_SOLO_NO_REASON = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: solo
"""

# Row: "[Tier B] task with `split`" → WARN (over-ceremony)
TASKS_TIER_B_SPLIT = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier B] rename a label  (files: labels.ts)
      Test-author: split
"""

# Row: "All present and coherent" → PASS
TASKS_ALL_COHERENT = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
- [ ] T03 [Tier A] pure threshold logic  (files: calc.ts)
      Test-author: solo — A-lite, pure transform, no security-boundary category
"""

# A FENCED `Test-author:` example (as a plan's own per-task format block carries) must never count —
# neither as "present" (it's documentation, not a real task's mode) nor trip the
# partial-presence FAIL. Wrapping TASKS_NO_TEST_AUTHOR_LINES's real tasks with a
# fenced per-task-format example ahead of them must still yield the WARN verdict,
# not FAIL, and the fenced line's task-like content (`T<NN>`) must not be treated
# as a real task either.
TASKS_FENCED_EXAMPLE_IGNORED = """# Tasks: x

## Per-task format

```
- [ ] T<NN> [P?] [Tier A|B] <imperative description>  (files: <paths>)
      Test-author: <split | solo — reason>  (D1 rule: split iff Tier A on a security-boundary
                  category — auth/guards, untrusted parsing, migrations, money, 1a surface)
```

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire route  (files: routes.ts)
"""

# A fenced example whose task line is REAL-SHAPED (`T99`, matches TASK_LINE)
# rather than the inert `T<NN>` placeholder above — this is what actually
# exercises the strip_fenced call inside check_test_author_mode: with
# fencing correctly stripped, T99 (and its fenced `Test-author: split` line)
# must never be counted at all, and the verdict must be driven ONLY by the
# 3 real, unfenced tasks below (all 3 carrying the field) -> PASS "all 3
# tasks". If strip_fenced were skipped, T99 would be picked up as a 4th
# real task whose Test-author: line sits at the wrong offset relative to
# the *unfenced* scan (the fence delimiters themselves would shift line
# indices), corrupting the total/verdict — see the mutation-proof below.
TASKS_FENCED_REALSHAPED_TASK_LINE = """# Tasks: x

## Per-task format

```
- [ ] T99 [Tier A] sample
      Test-author: split
```

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
- [ ] T03 [Tier A] pure threshold logic  (files: calc.ts)
      Test-author: solo — A-lite, pure transform, no security-boundary category
"""


# ── `deliverable-first` fixtures — the 1j gate (first demoable slice first) ──
# The 2026-08-03 post-mortem's gate, decided 2026-08-09 (FR-3/4/5): a plan must carry
# `## First working version` naming a task among the FIRST 3 whose `(files:)` produces at
# least one non-test file; `N/A` only when the spec flags no user-facing surface; a legacy
# plan states the `legacy-artifact` waiver and degrades ABSENCE to WARN. The two worked
# examples in the 1j draft become fixture shapes here: josworld-core's first seeable task
# fifth (position FAIL) and yootheme-baseline's test-only T03 (files FAIL).

# Five tasks, deliberately post-mortem-shaped: T01 non-test scaffold, T02 test-only,
# T03 mixed (impl + test), T04 the first admin-visible surface — too late.
TASKS_FWV = """# Tasks: Case model

### Cluster C1
- [ ] T01 [Tier B] scaffold the loader pair  (files: src/loader.php)
- [ ] T02 [Tier A] boot-order proof  (files: tests/Integration/BootOrderTest.php)
- [ ] T03 [Tier A] register the case model  (files: src/model.php, tests/model.spec.php)
- [ ] T04 [Tier A] case admin screen  (files: src/admin.php)
- [ ] T05 [Tier B] docs  (files: README.md)
"""

# Same list with a [HUMAN] yield point among the preceding tasks — it still counts toward
# position (the deliverable waits on it all the same), so T04 stays fourth.
TASKS_FWV_HUMAN_PRECEDING = TASKS_FWV.replace(
    "- [ ] T02 [Tier A] boot-order proof  (files: tests/Integration/BootOrderTest.php)",
    "- [ ] T02 [HUMAN] approve the destructive rename")

_PLAN_FWV_BASE = """# Implementation Plan: Case model

## Constitution check
- [x] ok

## Threat model
N/A — no surface flagged.

## Acceptance flows
N/A — fixture.

## Architecture invariants touched
N/A

## Spec-premise ground-truth
N/A

## Phases & review clusters
See tasks.md.

## Stakes
Stakes: standard — fixture

## Technical context
- **Loop budget:** ~6 iterations
"""

def _plan_fwv(task_id: str) -> str:
    return _PLAN_FWV_BASE + f"""
## First working version

**Task:** {task_id}
**Demonstrates:** an editor sees the case model in wp-admin
**Verify by:** open wp-admin and create one case
"""

# The section marked N/A, threat-model style — legitimate ONLY on a non-user-facing spec.
PLAN_FWV_NA = _PLAN_FWV_BASE + """
## First working version
N/A — docs-only deliverable, nothing runnable lands.
"""

# The section present ONLY inside a fenced example (the planning template's own format
# block) — must read as ABSENT, exactly as fenced task lines and Stakes: samples do.
PLAN_FWV_FENCED_ONLY = _PLAN_FWV_BASE + """
## Per-section format

```markdown
## First working version

**Task:** T01
**Demonstrates:** <what a human can SEE or RUN>
**Verify by:** <command / URL / screen>
```
"""

# The section present but naming nothing — a section that points at nothing orders nothing.
PLAN_FWV_NO_TASK_NAMED = _PLAN_FWV_BASE + """
## First working version

The checker itself is the demo; run it and watch it fail.
"""

# ── `fr-source` fixtures — source traceability (FR-1/FR-2) ────────────────────
# The post-mortem's link 1: a requirement invented at spec time reads exactly like one
# the human asked for, and the build then serves the invention. The check makes every FR
# name where it came from — a quotation, a document reference, or `invented` + an
# approval. It judges PRESENCE, not truthfulness (a fabricated quote passes the machine;
# challenging what a Source: says is review's job — the 1a honesty convention).

# Corpus-shaped: all four legal source shapes in one spec — a quotation mid-paragraph on
# the def line, `invented — approved` with the date across a line break (the live spec's
# FR-2 writes exactly that), a continuation-line `Source:`, and the approver-reference
# form. FR-1's own prose mentions a backticked `Source:` BEFORE its real source — the
# mention must read as prose, not as the source (the live spec's FR-1/FR-2 shape).
SPEC_FR_SOURCED = """# Feature Specification: Payload archive

## Functional requirements

### Traceability
- **FR-1:** Every payload carries a `Source:` tag — either a quotation or an approved
  invention. Source: the human, 2026-08-09: "every payload must say where it came from".
- **FR-2:** Rejected payloads are archived for replay. Source: invented — approved
  2026-08-09 (post-incident review; the human signed the intake).

### Retention
- **FR-3:** Archives expire after 90 days.
  Source: the retention draft (2026-07-01), adopted verbatim.
- **FR-4:** Expiry runs nightly. Source: invented — approved by Stefan (intake Q2).
"""

# One sourced, one bare — partial presence is a defect the waiver can NOT rescue
# (absence-only downgrade, the same partial-vs-absent logic as unit-test-contract).
SPEC_FR_PARTIAL = """# Feature Specification: Payload archive

<!-- gate-check: legacy-artifact — spec predates the Source: convention -->

## Functional requirements
- **FR-1:** Every payload is archived. Source: the human, 2026-08-09: "archive them".
- **FR-2:** Archives expire after 90 days.
"""

# `invented` (first word, case-insensitive) with no approval — FAILs; a quoted source
# containing a date is NOT mistaken for an invention.
SPEC_FR_INVENTED_BARE = """# Feature Specification: Payload archive

## Functional requirements
- **FR-1:** Rejected payloads are archived. Source: invented — felt necessary.
- **FR-2:** Expiry runs nightly. Source: Invented, obviously correct.
- **FR-3:** Archives expire after 90 days. Source: the human, 2026-08-09: "90 days".
"""

# FR ids defined, zero `Source:` anywhere — the musician-events shape. Bare → FAIL;
# with the file-scoped waiver → WARN naming it (absence-only downgrade).
SPEC_FR_NONE = """# Feature Specification: Payload archive

## Functional requirements
- **FR-1:** Every payload is archived.
- **FR-2:** Archives expire after 90 days.
"""

SPEC_FR_NONE_WAIVED = (
    "<!-- gate-check: legacy-artifact — spec authored before the Source: convention -->\n"
    + SPEC_FR_NONE)

# I-2 probe: a colon-less FR def (`- **FR-2** …`, colon missing) is not an FR_DEF_LINE,
# so under the old walker it CONTINUED FR-1's block and donated its `Source:` upward —
# FR-1 read sourced while FR-2 escaped the check entirely. The block must flush at any
# column-0 bullet that is not an FR def: FR-1 reads bare, the donation never happens.
SPEC_FR_COLONLESS = """# Feature Specification: Payload archive

## Functional requirements
- **FR-1:** Every payload is archived.
- **FR-2** Archives expire after 90 days. Source: the human, 2026-08-09: "90 days".
- **FR-3:** Expiry runs nightly. Source: invented — approved by Stefan (intake Q2).
"""

# S-4 rider: a `Source:` whose value carries no word character (`Source: —`) is
# contentless — it must read as unsourced, never as a source.
SPEC_FR_DASH_SOURCE = """# Feature Specification: Payload archive

## Functional requirements
- **FR-1:** Every payload is archived. Source: —
- **FR-2:** Expiry runs nightly. Source: the human, 2026-08-09: "nightly".
"""

# A fenced example carrying `Source:` never sources the FR above it — fence-stripped
# like every parser in the checker.
SPEC_FR_FENCED_SOURCE = """# Feature Specification: Payload archive

## Functional requirements
- **FR-1:** Every payload is archived.

```markdown
Source: invented — approved 2026-08-09
```
"""

# Seam fixtures: an otherwise fully-green artifact set (SPEC_CLEAN_NOSEC's shape) whose
# spec gains one FR — sourced (green floor) or bare (the check must flip the exit code).
_FR_SECTION_SOURCED = """
## Functional requirements
- **FR-1:** the footer label reads correctly. Source: the human, 2026-08-09: "rename it".
"""

_FR_SECTION_BARE = """
## Functional requirements
- **FR-1:** the footer label reads correctly.
"""

# TASKS_GOOD with the seam spec's FR-1 cited, so requirement-coverage stays green and the
# seam cases attribute their exit code to fr-source alone.
TASKS_FR_CITED = TASKS_GOOD.replace("validate URL (SC-1)", "validate URL (SC-1, FR-1)")


# ── `behaviour-cluster` fixtures — the FR-6/FR-7 grammar (T03) ────────────────
# One RED per behaviour, observable from outside: a `### Cluster` may carry
# `Behaviour:` + `Observable:` + `RED until: <path::method>`, and a member task may then
# satisfy its test-contract line with `covered by cluster behaviour` INSTEAD of its own
# unit test — accepted only inside a cluster carrying the FULL block whose `RED until:`
# test file exists on disk or is created by a member task (its path appears in a member's
# `(files:)` segment). The machine checks presence + the named test; observable
# ADMISSIBILITY (no config/array shapes) is FR-9's sequencer rule, not checked here.

_BEHAVIOUR_TASKS_HEAD = """# Tasks: Notifier

### Cluster N1 — the notifier  (2 tasks · provisional tier: STANDARD)

"""

_BEHAVIOUR_BLOCK = """Behaviour: one mail per event, never a duplicate.
Observable: `php bin/replay.php fixtures/events.json` prints `sent=1 dupes=0`.
RED until: `tests/NotifyTest.php::test_one_mail_per_event`

"""

_BEHAVIOUR_TASKS_BODY = """- [ ] T01 [Tier A] implement the notifier dedupe  (files: src/notify.php, tests/NotifyTest.php)
      Test-author: solo — standard stakes, fixture
      Proven by: new test — the cluster's behaviour RED
      Unit test: covered by cluster behaviour
- [ ] T02 [Tier B] wire the notifier into the dispatcher  (files: src/dispatch.php)
      Test-author: solo — Tier B
      Proven by: existing test — the cluster's behaviour RED reaches the wire
      Unit test: the dispatcher invokes notify exactly once per event

**Integration gate (N1):** replay fixtures/events.json end to end; exactly one mail lands.

── REVIEW GATE ──  *(tier STANDARD)*
"""

# (a)+(e): full block, RED-until file created by member T01, T02 keeps an ordinary line —
# opt-in grammar, both forms legal inside one cluster.
TASKS_BEHAVIOUR_VALID = _BEHAVIOUR_TASKS_HEAD + _BEHAVIOUR_BLOCK + _BEHAVIOUR_TASKS_BODY

# (b): the same waiver-using member with NO block at all above it.
TASKS_BEHAVIOUR_NO_BLOCK = _BEHAVIOUR_TASKS_HEAD + _BEHAVIOUR_TASKS_BODY

# (c): `Behaviour:`/`Observable:` present but no `RED until:` — a block that names no RED
# cannot cover anyone.
TASKS_BEHAVIOUR_PARTIAL = (_BEHAVIOUR_TASKS_HEAD
                           + "Behaviour: one mail per event, never a duplicate.\n"
                           + "Observable: `php bin/replay.php fixtures/events.json` prints `sent=1`.\n\n"
                           + _BEHAVIOUR_TASKS_BODY)

# (d): full block whose RED-until test is neither on disk nor in any member's files —
# the replace targets the `::`-qualified RED value only; T01's files still name
# tests/NotifyTest.php, which must NOT satisfy a RED pointing at GhostTest.
TASKS_BEHAVIOUR_DANGLING = TASKS_BEHAVIOUR_VALID.replace(
    "tests/NotifyTest.php::test_one_mail_per_event",
    "tests/GhostTest.php::test_missing")

# Disk rung: the RED-until file is NOT in any member's `(files:)` segment, so validity can
# come only from the file existing on disk under the given repo root.
TASKS_BEHAVIOUR_ON_DISK = (_BEHAVIOUR_TASKS_HEAD
                           + "Behaviour: one mail per event, never a duplicate.\n"
                           + "Observable: `php bin/replay.php fixtures/events.json` prints `sent=1`.\n"
                           + "RED until: tests/OnDiskTest.php::test_one_mail\n\n"
                           + _BEHAVIOUR_TASKS_BODY.replace(
                               "(files: src/notify.php, tests/NotifyTest.php)",
                               "(files: src/notify.php)"))

# I-1 probe (disk rung): the RED-until path names a DIRECTORY that exists under the
# repo root. A directory is not a test — the block must read dangling, not valid. The
# member files drop the tests/ entry so validity could only come from the disk rung.
TASKS_BEHAVIOUR_DIR_ONLY = (_BEHAVIOUR_TASKS_HEAD
                            + "Behaviour: one mail per event, never a duplicate.\n"
                            + "Observable: `php bin/replay.php fixtures/events.json` prints `sent=1`.\n"
                            + "RED until: tests/::test_one_mail\n\n"
                            + _BEHAVIOUR_TASKS_BODY.replace(
                                "(files: src/notify.php, tests/NotifyTest.php)",
                                "(files: src/notify.php)"))

# I-1 probe (files rung): the RED-until path is a SUBSTRING of a member file
# (`src` inside `src/notify.php`) — the files rung must require an exact match against
# the comma-split member paths, never a substring hit.
TASKS_BEHAVIOUR_SUBSTRING = (_BEHAVIOUR_TASKS_HEAD
                             + "Behaviour: one mail per event, never a duplicate.\n"
                             + "Observable: `php bin/replay.php fixtures/events.json` prints `sent=1`.\n"
                             + "RED until: src::test_one_mail\n\n"
                             + _BEHAVIOUR_TASKS_BODY.replace(
                                 "(files: src/notify.php, tests/NotifyTest.php)",
                                 "(files: src/notify.php)"))

# I-A probes (disk-rung confinement): the rung must accept ONLY a test-shaped path
# resolving to a file STRICTLY UNDER the repo root. `.is_file()` alone accepts three
# escapes — an absolute path (`repo_root / "/etc/hostname"` discards the left operand),
# a `../` traversal (os.stat resolves it right past the root), and any in-repo non-test
# file (README.md) — each of which vacuously validates the block and unlocks the Tier-A
# `covered by cluster behaviour` waiver. The member files drop the tests/ entry so
# validity could only come from the disk rung.
def _bhv_disk_tasks(red_path: str) -> str:
    return (_BEHAVIOUR_TASKS_HEAD
            + "Behaviour: one mail per event, never a duplicate.\n"
            + "Observable: `php bin/replay.php fixtures/events.json` prints `sent=1`.\n"
            + f"RED until: {red_path}::test_one_mail\n\n"
            + _BEHAVIOUR_TASKS_BODY.replace(
                "(files: src/notify.php, tests/NotifyTest.php)",
                "(files: src/notify.php)"))


# I-A (e): the files rung is SHAPE-BLIND by design — a member-declared RED-until path
# of any shape (spec/checks.php: not test-shaped, not on disk) stays valid, because the
# member task is creating it.
TASKS_BEHAVIOUR_FILES_NONTEST = (_BEHAVIOUR_TASKS_HEAD
                                 + "Behaviour: one mail per event, never a duplicate.\n"
                                 + "Observable: `php bin/replay.php fixtures/events.json` prints `sent=1`.\n"
                                 + "RED until: spec/checks.php::test_one_mail\n\n"
                                 + _BEHAVIOUR_TASKS_BODY.replace(
                                     "(files: src/notify.php, tests/NotifyTest.php)",
                                     "(files: src/notify.php, spec/checks.php)"))

# S-2 rider: backtick quoting on the PATH half alone (`path`::method) must resolve
# exactly like the fully-quoted form — no false dangle from a trailing backtick
# surviving the `::` split.
TASKS_BEHAVIOUR_BACKTICK_PATH = TASKS_BEHAVIOUR_VALID.replace(
    "RED until: `tests/NotifyTest.php::test_one_mail_per_event`",
    "RED until: `tests/NotifyTest.php`::test_one_mail_per_event")

# strip_fenced inheritance: a fenced block SAMPLE between the heading and the first task
# must be invisible — the cluster reads block-less (the "carries no behaviour block" FAIL),
# NOT as a full block with a dangling RED (which a fence leak would produce, since
# tests/SampleTest.php resolves to nothing).
TASKS_BEHAVIOUR_FENCED = (_BEHAVIOUR_TASKS_HEAD
                          + "```\n"
                          + "Behaviour: <one sentence>\n"
                          + "Observable: <command + expected output>\n"
                          + "RED until: tests/SampleTest.php::test_sample\n"
                          + "```\n\n"
                          + _BEHAVIOUR_TASKS_BODY)

# The waiver form on a task under no `### Cluster` heading at all.
TASKS_BEHAVIOUR_OUTSIDE = """# Tasks: x

## Phase 1
- [ ] T01 [Tier A] implement the notifier dedupe  (files: src/notify.php)
      Test-author: solo — standard stakes, fixture
      Unit test: covered by cluster behaviour
"""


# ── suffixed task ids (T03b, T07b, T09b) ─────────────────────────────────────
# Found live on todai-client 2026-08-20: `(T\d+)\b` cannot match `T07b`, because
# `T\d+` stops at the digit and `\b` then demands a boundary between two word
# characters. Every b-suffixed task was therefore INVISIBLE — skipped by the tier,
# files, test-author, proven-by and unit-test checks, and uncounted by the <=4
# cluster-size rule. A FULL-tier security spec had three such tasks and still
# read GATE: PASS. That is INV-4's own failure mode: green while a named check
# never ran.
TASKS_SUFFIXED_ID_NO_TIER = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier B] a  (files: a.php)
      Test-author: solo — Tier B
      Proven by: machine gate — gate exit 0
      Unit test: no unit test: Tier B, glue
- [ ] T01b the suffixed task that carries NO tier  (files: b.php)
      Test-author: solo — Tier B
      Proven by: machine gate — gate exit 0
      Unit test: no unit test: Tier B, glue

Integration gate: gate exit 0

── REVIEW GATE ── STANDARD
"""

TASKS_SUFFIXED_ID_OVERSIZED = """# Tasks: x

### Cluster C1  (5 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier B] a  (files: a.php)
      Test-author: solo — Tier B
      Proven by: machine gate — gate exit 0
      Unit test: no unit test: Tier B, glue
- [ ] T01b [Tier B] b  (files: b.php)
      Test-author: solo — Tier B
      Proven by: machine gate — gate exit 0
      Unit test: no unit test: Tier B, glue
- [ ] T02 [Tier B] c  (files: c.php)
      Test-author: solo — Tier B
      Proven by: machine gate — gate exit 0
      Unit test: no unit test: Tier B, glue
- [ ] T02b [Tier B] d  (files: d.php)
      Test-author: solo — Tier B
      Proven by: machine gate — gate exit 0
      Unit test: no unit test: Tier B, glue
- [ ] T03 [Tier B] e  (files: e.php)
      Test-author: solo — Tier B
      Proven by: machine gate — gate exit 0
      Unit test: no unit test: Tier B, glue

Integration gate: gate exit 0

── REVIEW GATE ── STANDARD
"""

# ── lanes (harness-inversion FR-1..FR-5) ──────────────────────────────────────
#
# A `### Cluster` declares `Lane: behaviour` or `Lane: contract` (heading label or a line
# between the heading and the first task). Behaviour-lane members carry ONLY a files
# segment; the cluster's full behaviour block is the proof and the file ends at one
# `── BRANCH REVIEW ──` marker. Contract lane is today's grammar untouched.

_LANE_BLOCK = """Behaviour: the case model is registered and its admin screen answers.
Observable: `wp post-type list --field=name` contains `case`; `/wp-admin/edit.php?post_type=case` → 200.
RED until: `tests/CaseModelTest.php::test_case_registered`

"""

_LANE_BEHAVIOUR_MEMBERS = """- [ ] T01 declare the case model  (files: src/models/case.php, tests/CaseModelTest.php)
- [ ] T02 the field map  (files: src/models/case-fields.php)
- [ ] T03 the admin tab layout  (files: src/admin/case-tabs.php)
- [ ] T04 the archive template  (files: templates/archive-case.php)

**Integration gate (L1):** `composer gate` exits 0 and the observable above holds.
"""

_BRANCH_REVIEW = """
── BRANCH REVIEW ──  *(tier LIGHT)*
"""

TASKS_LANE_BEHAVIOUR_BARE = ("# Tasks: Case model\n\n### Cluster L1 — the case model  (4 tasks)\n\n"
                             "Lane: behaviour\n" + _LANE_BLOCK + _LANE_BEHAVIOUR_MEMBERS
                             + _BRANCH_REVIEW)

# the lane on the heading label instead of its own line — both placements count
TASKS_LANE_IN_LABEL = ("# Tasks: Case model\n\n### Cluster L1 — the case model  (4 tasks · lane: behaviour)\n\n"
                       + _LANE_BLOCK + _LANE_BEHAVIOUR_MEMBERS + _BRANCH_REVIEW)

_CONTRACT_CLUSTER = """
### Cluster L2 — the access rule  (1 task · provisional tier: FULL)

Lane: contract — encodes the grant-access window this project chose

- [ ] T05 [Tier A] private events honour grantaccess  (files: src/access/grant.php, tests/GrantTest.php)
      Test-author: solo — standard stakes, an ownership predicate with a fixture
      Proven by: new test — the denial path in GrantTest
      Unit test: a viewer without a grant gets 403; with one, 200

**Integration gate (L2):** the denial path holds through the real request.

── REVIEW GATE ──  *(tier FULL)*
"""

TASKS_LANE_MIXED = ("# Tasks: Case model\n\n### Cluster L1 — the case model  (4 tasks)\n\n"
                    "Lane: behaviour\n" + _LANE_BLOCK + _LANE_BEHAVIOUR_MEMBERS
                    + _CONTRACT_CLUSTER + _BRANCH_REVIEW)

# (b): a sibling cluster with NO lane once one is declared
TASKS_LANE_SIBLING_BARE = TASKS_LANE_MIXED.replace(
    "Lane: contract — encodes the grant-access window this project chose\n\n", "")

# (c): a behaviour-lane member whose files hit the boundary detector
TASKS_LANE_BOUNDARY = TASKS_LANE_BEHAVIOUR_BARE.replace(
    "(files: src/admin/case-tabs.php)", "(files: src/admin/case-tabs.php, auth/Guard.php)")

# (e)/(f): contract lane with no boundary hit, with and without a reason
TASKS_LANE_CONTRACT_NO_REASON = TASKS_LANE_MIXED.replace(
    "Lane: contract — encodes the grant-access window this project chose",
    "Lane: contract").replace("src/access/grant.php", "src/rules/window.php")
TASKS_LANE_CONTRACT_REASON = TASKS_LANE_MIXED.replace("src/access/grant.php", "src/rules/window.php")

# invalid value
TASKS_LANE_INVALID = TASKS_LANE_BEHAVIOUR_BARE.replace("Lane: behaviour", "Lane: fast")

# T02 (b): a behaviour-lane member carrying per-task paperwork anyway
TASKS_LANE_DRIFT = TASKS_LANE_BEHAVIOUR_BARE.replace(
    "- [ ] T02 the field map  (files: src/models/case-fields.php)\n",
    "- [ ] T02 [Tier B] the field map  (files: src/models/case-fields.php)\n"
    "      Test-author: solo — Tier B\n")

# T02 (c): behaviour lane with a partial block
TASKS_LANE_PARTIAL_BLOCK = TASKS_LANE_BEHAVIOUR_BARE.replace(
    "RED until: `tests/CaseModelTest.php::test_case_registered`\n", "")

# T02 (d): behaviour lane with no integration gate
TASKS_LANE_NO_INTEGRATION = TASKS_LANE_BEHAVIOUR_BARE.replace(
    "**Integration gate (L1):** `composer gate` exits 0 and the observable above holds.\n", "")

# T02 (e): the contract cluster in a mixed file still gets every per-task check
TASKS_LANE_CONTRACT_MISSING_TIER = TASKS_LANE_MIXED.replace(
    "- [ ] T05 [Tier A] private events", "- [ ] T05 private events")

# T03 (b)/(c)/(d): branch-review marker absent, tier-less, or a review gate on a behaviour cluster
TASKS_LANE_NO_BRANCH_REVIEW = TASKS_LANE_BEHAVIOUR_BARE.replace(_BRANCH_REVIEW, "\n")
TASKS_LANE_BRANCH_REVIEW_NO_TIER = TASKS_LANE_BEHAVIOUR_BARE.replace(
    "── BRANCH REVIEW ──  *(tier LIGHT)*", "── BRANCH REVIEW ──")
TASKS_LANE_BEHAVIOUR_WITH_REVIEW_GATE = TASKS_LANE_BEHAVIOUR_BARE.replace(
    _BRANCH_REVIEW, "\n── REVIEW GATE ──  *(tier LIGHT)*\n" + _BRANCH_REVIEW)

PLAN_CLUSTER_STAKES_HIGH = PLAN_GATES_FULL + """
### Per-cluster stakes

| Cluster | Stakes | Why |
|---|---|---|
| L1 — the case model | high | the model stores payment references |
"""
PLAN_STAKES_HIGH_LINE = PLAN_GATES_FULL.replace("Stakes: standard", "Stakes: high")


def test_lane_behaviour_bare_members_pass() -> tuple[bool, str]:
    """The cluster RED named in specs/harness-inversion: a behaviour-lane cluster whose
    members carry only `(files:)` passes the gate, exit 0, with the lane reported."""
    rc, out = _run({"tasks.md": TASKS_LANE_BEHAVIOUR_BARE})
    return (rc == 0 and "✓ [cluster-lane]" in out and "behaviour" in out,
            "lane (a): behaviour-lane cluster with 4 bare members exits 0 with the ✓ line")


def _run(files: dict) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as d:
        for name, content in files.items():
            (Path(d) / name).write_text(content)
        proc = subprocess.run([sys.executable, str(CHECKER), d],
                               capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout + proc.stderr


def run():
    results = []

    # 1. THE load-bearing case: triggered surface + N/A threat model → FAIL
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_THREATMODEL_NA, "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "threat-model" in out,
                    "triggered surface + N/A threat model FAILS the gate"))

    # 2. triggered surface WITH a substantive threat model → PASS
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_GATES_FULL, "tasks.md": TASKS_GOOD})
    results.append((rc == 0, "triggered surface + substantive threat model PASSES"))

    # 3. no security surface + N/A threat model → PASS (legitimate)
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC, "plan.md": PLAN_THREATMODEL_NA, "tasks.md": TASKS_GOOD})
    results.append((rc == 0, "no security surface + N/A threat model PASSES"))

    # 4. unresolved [NEEDS CLARIFICATION] in spec → FAIL (Stage 0.5 HALT)
    rc, out = _run({"spec.md": SPEC_WITH_UNRESOLVED})
    results.append((rc == 1 and "clarify-halt" in out,
                    "unresolved [NEEDS CLARIFICATION] HALTS (spec-only stage)"))

    # 5. clean spec (template guidance present but no real marker) → PASS clarify
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC})
    results.append((rc == 0, "template guidance is not mistaken for an unresolved marker"))

    # 6. missing a required [GATE] heading (invariants) → FAIL
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC, "plan.md": PLAN_MISSING_HEADING, "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "Architecture invariants" in out,
                    "missing required [GATE] heading FAILS"))

    # 7. a task without a test tier → FAIL
    rc, out = _run({"tasks.md": TASKS_NO_TIER})
    results.append((rc == 1 and "task-tier" in out, "task missing a test tier FAILS"))

    # 8. oversized cluster (>4 tasks) → FAIL
    rc, out = _run({"tasks.md": TASKS_OVERSIZED})
    results.append((rc == 1 and "review-cluster" in out, "cluster with >4 tasks FAILS"))

    # 9. irreversible cluster with a [P] task → FAIL
    rc, out = _run({"tasks.md": TASKS_IRREVERSIBLE_PARALLEL})
    results.append((rc == 1 and "review-cluster" in out, "irreversible cluster marked [P] FAILS"))

    # 10. fully good set → PASS
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_GATES_FULL, "tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "GATE: PASS" in out, "complete, gate-bearing set PASSES"))

    # ── `success-criteria` — the spec-stage half of the Stage-0.5 gate ────────
    # Run through the CLI (_run) rather than unit-level, because the WARN-vs-FAIL
    # distinction is only load-bearing via the exit code: a pre-template spec must
    # stay green while a filled-in-but-unmeasurable one must not.

    # 10a. every SC line carries a number → PASS
    rc, out = _run({"spec.md": SPEC_SC_MEASURABLE})
    results.append((rc == 0 and "✓ [success-criteria]" in out,
                    "measurable ## Success criteria PASSES"))

    # 10b. prose SC lines → FAIL, naming the offending ids (not just a count)
    rc, out = _run({"spec.md": SPEC_SC_VAGUE})
    results.append((rc == 1 and "success-criteria" in out
                     and "SC-2" in out and "SC-3" in out and "SC-1" not in out,
                    "SC line with no number FAILs and names SC-2/SC-3 only"))

    # 10c. section present but only bracketed `[e.g. …]` placeholder text → FAIL
    # (the placeholder's own digits must not be mistaken for a measurement)
    rc, out = _run({"spec.md": SPEC_SC_TEMPLATE_UNTOUCHED})
    results.append((rc == 1 and "success-criteria" in out and "placeholder" in out,
                    "bracketed placeholder body FAILs, digits in the example ignored"))

    # 10d. a spec with no ## Success criteria but an explicit legacy waiver → WARN that
    # NAMES the waiver, gate stays PASS. The silent retro-compat floor is gone.
    rc, out = _run({"spec.md": SPEC_PRE_TEMPLATE_NO_SC})
    results.append((rc == 0 and "! [success-criteria]" in out
                     and "legacy waiver exercised" in out,
                    "no ## Success criteria + a stated legacy waiver WARNs, naming the waiver"))

    # 10d-b. the same spec with NO waiver → FAIL, and the finding tells the author the
    # waiver form exists (an old artifact says so out loud; a new one adds the section).
    rc, out = _run({"spec.md": SPEC_PRE_TEMPLATE_NO_SC.replace(
        "<!-- gate-check: legacy-artifact — authored 2026-05, before the Success criteria contract -->\n\n", "")})
    results.append((rc == 1 and "success-criteria" in out and "legacy-artifact" in out,
                    "no ## Success criteria and no waiver FAILs, naming the waiver form"))

    # 10d-c. a waiver marker with NO reason is not a waiver — same rule as a bare Tier-A solo.
    rc, out = _run({"spec.md": SPEC_PRE_TEMPLATE_NO_SC.replace(
        "authored 2026-05, before the Success criteria contract", "")})
    results.append((rc == 1 and "success-criteria" in out,
                    "a reason-less success-criteria waiver marker does not waive anything"))

    # ── `security-surfaces` — the arming switch (spec side) ───────────────────
    # These four are the highest-value cases in this file: each one is a spec that
    # previously reached execution with the 1a threat-model gate silently disarmed.

    # 10e. every surface box blank on an auth feature → FAIL (was: green + reassurance)
    rc, out = _run({"spec.md": SPEC_SURFACES_ALL_BLANK, "plan.md": PLAN_THREATMODEL_NA,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "security-surfaces" in out and "0 of 6" in out,
                    "all surface boxes blank FAILs — blank is not 'none', it disarms 1a"))

    # 10f. no ## Security-relevant surfaces section at all → FAIL (same hole, by omission)
    rc, out = _run({"spec.md": SPEC_SURFACES_MISSING})
    results.append((rc == 1 and "security-surfaces" in out,
                    "missing ## Security-relevant surfaces section FAILs"))

    # 10g. a real surface AND "None of the above" → FAIL as contradictory
    rc, out = _run({"spec.md": SPEC_SURFACES_CONTRADICTORY})
    results.append((rc == 1 and "security-surfaces" in out and "contradictory" in out,
                    "a real surface plus 'None of the above' FAILs as contradictory"))

    # 10h. answered honestly → PASS, and the finding says whether 1a is armed
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_GATES_FULL, "tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "1a threat model is REQUIRED" in out,
                    "a flagged surface PASSES and states that the plan's 1a model is required"))

    # ── 1g: `user-facing-surfaces` (arming) + `acceptance-flows` ──────────────
    # These mirror the 1a cases above one-for-one. THE load-bearing one is 10ad: before the
    # arming switch existed, a wizard reached execution with no matrix and the gate said
    # GREEN, because nothing in the spec could tell a checker the work was user-facing.

    # 10ad. flagged user-facing surface + N/A acceptance flows → FAIL
    rc, out = _run({"spec.md": SPEC_USER_FACING, "plan.md": PLAN_FLOWS_NA,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "acceptance-flows" in out,
                    "flagged user-facing surface + N/A ## Acceptance flows FAILS the gate"))

    # 10ae. flagged surface + a filled-in matrix → PASS, echoing the row count
    rc, out = _run({"spec.md": SPEC_USER_FACING, "plan.md": PLAN_FLOWS_FILLED,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "2 filled-in flow row(s)" in out,
                    "flagged user-facing surface + a filled matrix PASSES"))

    # 10af. a header+separator skeleton with no filled row is not a matrix → FAIL when armed
    rc, out = _run({"spec.md": SPEC_USER_FACING, "plan.md": PLAN_FLOWS_EMPTY_TABLE,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "acceptance-flows" in out,
                    "an empty table skeleton does not satisfy 1g — nothing to drive"))

    # 10ag. no user-facing surface flagged + N/A flows → PASS (legitimate; the corpus shape)
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC, "plan.md": PLAN_FLOWS_NA,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "✓ [acceptance-flows]" in out,
                    "no user-facing surface + N/A acceptance flows PASSES"))

    # 10ah. every user-facing box blank → FAIL (disarm by inaction, same as 1a's blank case)
    rc, out = _run({"spec.md": SPEC_USER_FACING_ALL_BLANK, "plan.md": PLAN_FLOWS_NA,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "user-facing-surfaces" in out and "0 of 5" in out,
                    "all user-facing boxes blank FAILs — blank is not 'none', it disarms 1g"))

    # 10ai. a real surface AND "None of the above" → FAIL as contradictory
    rc, out = _run({"spec.md": SPEC_USER_FACING_CONTRADICTORY, "plan.md": PLAN_FLOWS_NA,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "user-facing-surfaces" in out and "contradictory" in out,
                    "a user-facing surface plus 'None of the above' FAILs as contradictory"))

    # 10aj. no ## User-facing surfaces section at all → FAIL (the hole by omission)
    rc, out = _run({"spec.md": SPEC_SURFACES_MISSING})
    results.append((rc == 1 and "user-facing-surfaces" in out,
                    "missing ## User-facing surfaces section FAILs"))

    # 10ak. `## Acceptance flows` is a required plan heading like the other five
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC,
                    "plan.md": PLAN_FLOWS_NA.replace(
                        "## Acceptance flows\nN/A — small feature.\n", ""),
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "Acceptance flows" in out,
                    "a plan missing ## Acceptance flows FAILs on the heading check"))

    # ── `review-gate-marker` / `review-tier` — the cluster boundary (1f / 1h) ──

    # 10i. sized clusters with tiers but no STOP marker → FAIL (nothing HALTs execution)
    rc, out = _run({"tasks.md": TASKS_NO_REVIEW_GATE})
    results.append((rc == 1 and "review-gate-marker" in out and "2/2" in out,
                    "clusters with no `── REVIEW GATE ──` marker FAIL, naming them"))

    # 10j. markers present but no provisional tier declared → FAIL (nothing to restate)
    rc, out = _run({"tasks.md": TASKS_NO_REVIEW_TIER})
    results.append((rc == 1 and "review-tier" in out,
                    "clusters with no provisional review tier FAIL"))

    # 10k. the compliant reference file → both PASS, tiers reported back
    rc, out = _run({"tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "review-gate-marker" in out and "FULL" in out,
                    "a compliant tasks.md PASSES marker + tier checks, echoing the tiers"))

    # ── `unit-test-contract` (1d) ─────────────────────────────────────────────

    # 10l. partial presence → FAIL naming the task with no stated contract
    rc, out = _run({"tasks.md": TASKS_PARTIAL_UNIT_TEST})
    results.append((rc == 1 and "unit-test-contract" in out and "T02" in out,
                    "a task with a tier but no `Unit test:` contract FAILs, naming it (T02)"))

    # 10m. a Tier A task waiving its test → FAIL (the tier-erosion case)
    rc, out = _run({"tasks.md": TASKS_TIER_A_WAIVES_TEST})
    results.append((rc == 1 and "unit-test-contract" in out and "Tier A may not waive" in out,
                    "a Tier A task waiving its test with `no unit test:` FAILs"))

    # 10n. zero test-contract lines anywhere and NO waiver → FAIL, naming every bare task.
    # This previously WARNed on pre-convention retro-compat grounds; that floor was
    # unreachable on the live corpus and an all-or-nothing floor rewards writing ZERO
    # contracts over writing some — the exact shape a hollow tasks.md walks through.
    rc, out = _run({"tasks.md": TASKS_NO_TEST_AUTHOR_LINES})
    results.append((rc == 1 and "unit-test-contract" in out
                     and "T01" in out and "T02" in out,
                    "zero test-contract lines FAILs (no silent floor), naming T01 and T02"))

    # 10n-b. the same file with an explicit legacy waiver → WARN naming the waiver.
    rc, out = _run({"tasks.md": "<!-- gate-check: legacy-artifact — predates the Unit test: contract line -->\n"
                    + TASKS_NO_TEST_AUTHOR_LINES})
    results.append(("! [unit-test-contract]" in out and "legacy waiver exercised" in out,
                    "zero test-contract lines + a stated waiver WARNs, naming the waiver"))

    # ── `security-boundary-mode` — the free-form `solo` reason, made visible ───

    # 10s. Tier A + solo on a token/migration file → WARN (gate still PASSes: heuristic)
    rc, out = _run({"tasks.md": TASKS_TIER_A_SOLO_ON_BOUNDARY})
    results.append((rc == 0 and "! [security-boundary-mode]" in out
                     and "T01" in out and "split at effective-`high` stakes" in out,
                    "Tier A + solo on a security-boundary file WARNs, never FAILs"))

    # 10t. same task, correct `split` mode → silent
    rc, out = _run({"tasks.md": TASKS_TIER_A_SPLIT_ON_BOUNDARY})
    results.append((rc == 0 and "security-boundary-mode" not in out,
                    "the same task with `split` produces no boundary warning"))

    # 10u. Tier B on a security-boundary file with NO evidence named → WARN.
    # The finding moved from the tier to the missing proof; the warning must still fire, and
    # must still never FAIL (a keyword is not knowledge).
    rc, out = _run({"tasks.md": TASKS_TIER_B_ON_BOUNDARY})
    results.append((rc == 0 and "! [security-boundary-mode]" in out and "NOTHING proving it" in out,
                    "Tier B on a security-boundary file with no evidence WARNs"))

    # 10u-b. THE REGRESSION THAT MATTERS (`contact-page-8k`). The same boundary surface, with a
    # presence proof named, must be SILENT. If this ever warns again, every framework-primitive
    # call in a WP feature gets pushed to Tier A + split and the contact page repeats itself.
    rc, out = _run({"tasks.md": TASKS_TIER_B_ON_BOUNDARY_PROVEN})
    results.append((rc == 0 and "security-boundary-mode" not in out,
                    "Tier B on a boundary surface WITH a named presence proof draws no warning"))

    # 10u-c. Tier B + `Proven by: new test` contradict each other → WARN naming the conflict.
    rc, out = _run({"tasks.md": TASKS_TIER_B_ON_BOUNDARY_CONTRADICTORY})
    results.append((rc == 0 and "! [security-boundary-mode]" in out and "one of them is wrong" in out,
                    "Tier B claiming `Proven by: new test` WARNs as self-contradictory"))

    # 10u-d. F2 — the SAME shape WITH an `Integration test:` contract is the designed WP
    # wiring path (the "new test" is the integration test the contract states) → SILENT.
    rc, out = _run({"tasks.md": TASKS_TIER_B_BOUNDARY_INTEGRATION_NEW_TEST})
    results.append((rc == 0 and "security-boundary-mode" not in out,
                    "Tier B + Integration contract + `Proven by: new test` draws no warning"))

    # 10u-e. F1 — a malformed bullet's lines must not be attributed to the task above, on
    # ANY block-based check. Three checks, one boundary rule:
    rc, out = _run({"tasks.md": TASKS_MALFORMED_BULLET_LEAK})
    results.append((rc == 1 and "test-author-mode" in out and "T01" in out,
                    "F1: T01 is reported as missing its Test-author line — the malformed "
                    "bullet's mode line is not attributed to T01"))
    results.append(("! [security-boundary-mode]" in out and "NOTHING proving it" in out
                    and "T01 (session" in out,
                    "F1: T01 (Tier B, boundary file) WARNs as unproven — the malformed "
                    "bullet's `Proven by: machine gate` does not shield it"))
    results.append(("[proven-by]" in out and "missing a `Proven by:` line: T01" in out,
                    "F1: proven-by FAILs naming T01 — the malformed bullet's rung line "
                    "does not leak upward"))

    # 10v. CALIBRATION: test-AUTHor.md / performance-orACLe.md must not match. The first
    # cut of this check flagged three live doc tasks on exactly these substrings, which is
    # the noise that trains people to ignore WARNs.
    rc, out = _run({"tasks.md": TASKS_BOUNDARY_FALSE_FRIENDS})
    results.append((rc == 0 and "security-boundary-mode" not in out,
                    "`auth` in test-author.md and `acl` in performance-oracle.md do not match"))

    # ── `files-segment` — declared grammar, and the detector it keeps alive ────

    # 10w. tasks with no `(files: …)` segment → FAIL, naming them
    rc, out = _run({"tasks.md": TASKS_NO_FILES_SEGMENT})
    results.append((rc == 1 and "files-segment" in out and "T01" in out and "T02" in out,
                    "task lines with no `(files: …)` segment FAIL, naming T01 and T02"))

    # 10x. THE reason it FAILs: the same auth/payment task draws no security-boundary WARN
    # without a segment to match FILES_SECURITY against. This pins the calibration — the
    # files-segment check is what stops that silence being reachable.
    results.append(("security-boundary-mode" not in out,
                    "no files segment ⇒ the auth/payment task draws no boundary WARN "
                    "(why files-segment FAILs rather than shrugs)"))

    # 10y. the short `(f: …)` form counts — FILES_SEGMENT is the single reader of this grammar
    rc, out = _run({"tasks.md": TASKS_NO_REVIEW_TIER})
    results.append(("files-segment" in out and "✓ [files-segment]" in out,
                    "the short `(f: …)` form satisfies files-segment"))

    # 10ya. a `[HUMAN]` yield point needs no files segment — it is an approval, not a file
    # edit, and demanding paths would invite inventing one. The exemption is REPORTED, not
    # silent, so a planner cannot hide a code task behind a [HUMAN] marker unnoticed.
    rc, out = _run({"tasks.md": TASKS_HUMAN_YIELD_NO_FILES})
    results.append(("✓ [files-segment]" in out and "1 [HUMAN] yield point(s) exempt" in out,
                    "a [HUMAN] task is exempt from files-segment, and the exemption is named"))

    # ── `human-yield` (1d loop-auditability) — a yield point is never parallel ──

    # 10yb. `[HUMAN]` + `[P]` on the same task → FAIL, naming it. `planning` states the rule
    # outright ("a planned yield point, never `[P]`") and nothing enforced it: the mark
    # exists so an armed /loop STOPS, and `[P]` tells the controller it may dispatch
    # alongside its siblings. A task carrying both is a yield point the loop can run past.
    rc, out = _run({"tasks.md": TASKS_HUMAN_PARALLEL})
    results.append((rc == 1 and "human-yield" in out and "T02" in out,
                    "a [HUMAN] task also marked [P] FAILs, naming it (T02)"))

    # 10yc. the same yield point without `[P]` → clean
    rc, out = _run({"tasks.md": TASKS_HUMAN_PARALLEL.replace("[HUMAN] [P]", "[HUMAN]")})
    results.append((rc == 0 and "✓ [human-yield]" in out,
                    "a [HUMAN] task that is not [P] PASSES"))

    # 10yd. a plan with no [HUMAN] task at all is silent — most features have none, so there
    # is nothing to require here, only a contradiction to refuse.
    rc, out = _run({"tasks.md": TASKS_GOOD})
    results.append(("human-yield" not in out,
                    "a tasks.md with no [HUMAN] task says nothing about human-yield"))

    # ── `integration-gate` (1d) — what the Step 2.8 HALT verifies against ─────

    # 10z. a cluster with a marker and a tier but no integration gate → FAIL
    rc, out = _run({"tasks.md": TASKS_NO_INTEGRATION_GATE})
    results.append((rc == 1 and "integration-gate" in out,
                    "a cluster stating no `Integration gate:` FAILs"))

    # 10aa. mention ≠ declaration: the ANCHORED regex must not accept a task's own prose
    rc, out = _run({"tasks.md": TASKS_INTEGRATION_GATE_ONLY_IN_PROSE})
    results.append((rc == 1 and "integration-gate" in out,
                    "a task mentioning 'the cluster integration gate' in prose does not "
                    "satisfy the check — it must be DECLARED at line start"))

    # 10aa-b. the wp-manager corpus shape: NO cluster carries the line and the file states a
    # waiver → WARN naming the waiver (absence only, kept visible).
    rc, out = _run({"tasks.md": TASKS_INTEGRATION_GATE_WAIVED})
    results.append((rc == 0 and "! [integration-gate]" in out
                     and "legacy waiver exercised" in out,
                    "total integration-gate absence + a stated waiver WARNs, naming it"))

    # 10aa-c. the waiver never excuses PARTIAL absence: give C1 a gate line, keep the
    # waiver, and the bare C2 still FAILs — the convention is in use.
    rc, out = _run({"tasks.md": TASKS_INTEGRATION_GATE_WAIVED.replace(
        "── REVIEW GATE ──  *(tier STANDARD)*",
        "**Integration gate (C1):** the validator refuses RFC1918 end to end.\n\n"
        "── REVIEW GATE ──  *(tier STANDARD)*")})
    results.append((rc == 1 and "integration-gate" in out,
                    "the waiver does not excuse a bare cluster once any cluster states a "
                    "gate — absence only"))

    # ── `loop-budget` (1d loop-auditability) ─────────────────────────────────

    # 10ab. the bold corpus form is accepted, and the number is echoed back
    rc, out = _run({"plan.md": PLAN_BOLD_LOOP_BUDGET})
    results.append((rc == 0 and "loop-budget" in out and "~20" in out,
                    "the live corpus's `- **Loop budget:** ~20 iterations` form PASSES"))

    # 10ac. no budget line at all → FAIL (an armed /loop has no ceiling; run-score cannot
    # grade the run against one)
    rc, out = _run({"plan.md": PLAN_NO_LOOP_BUDGET})
    results.append((rc == 1 and "loop-budget" in out,
                    "a plan with no `Loop budget:` line FAILs"))

    # 10ac-b. a fenced budget sample never counts — strip_fenced runs before the search, so
    # the plan reads as absent (and must not read as a declared ~99 ceiling).
    rc, out = _run({"plan.md": PLAN_FENCED_LOOP_BUDGET_ONLY})
    results.append((rc == 1 and "loop-budget" in out and "~99" not in out,
                    "a fenced `Loop budget:` sample is ignored — the plan reads as absent"))

    # ── `requirement-coverage` — spec ids traced into the task list ───────────

    # 10o. every FR/SC cited by a task → PASS
    rc, out = _run({"spec.md": SPEC_WITH_REQS, "tasks.md": TASKS_COVERS_ALL_REQS})
    results.append((rc == 0 and "requirement-coverage" in out and "all 4 requirement" in out,
                    "every FR-n/SC-n cited in tasks.md PASSES"))

    # 10p. convention in use but gaps remain → FAIL naming the untraced ids only
    rc, out = _run({"spec.md": SPEC_WITH_REQS, "tasks.md": TASKS_COVERS_SOME_REQS})
    results.append((rc == 1 and "requirement-coverage" in out
                     and "FR-2" in out and "FR-3" in out and "SC-1" in out,
                    "partial requirement coverage FAILs, naming only the untraced ids"))

    # 10q. the live-corpus shape WITH its waiver stated: no id cited at all → WARN that
    # names the waiver, gate stays PASS.
    rc, out = _run({"spec.md": SPEC_WITH_REQS, "tasks.md": TASKS_CITES_NO_REQS})
    results.append((rc == 0 and "! [requirement-coverage]" in out
                     and "legacy waiver exercised" in out,
                    "a task list citing no requirement id + a waiver WARNs, naming the waiver"))

    # 10q-b. the same task list with the waiver stripped → FAIL (absence is no longer
    # silently pre-convention; the finding names the waiver form for a genuinely old list).
    rc, out = _run({"spec.md": SPEC_WITH_REQS, "tasks.md": TASKS_CITES_NO_REQS.replace(
        "<!-- gate-check: legacy-artifact — task list predates the FR-n citation convention and the 0.8.0 Test-author field -->\n\n", "")})
    results.append((rc == 1 and "requirement-coverage" in out and "legacy-artifact" in out,
                    "a task list citing no requirement id with NO waiver FAILs"))

    # 10r. a spec with no numbered requirements at all → WARN (nothing is traceable).
    # Reachable only on a legacy-waived spec now: any `## Success criteria` section declares
    # SC-n by construction, so an id-less spec is one with no criteria section at all.
    rc, out = _run({"spec.md": SPEC_PRE_TEMPLATE_NO_SC, "tasks.md": TASKS_CITES_NO_REQS})
    results.append(("! [requirement-coverage]" in out and "no FR-n" in out,
                    "a spec declaring no FR-n/SC-n ids WARNs — nothing is traceable"))

    # ── D1 `test-author-mode` — one fixture per plan.md D1 rules-table row ────
    # check_test_author_mode() is called DIRECTLY (unit level), independent of
    # run_checks()/the CLI, to pin down the function's own branch logic. These
    # assertions were the BEHAVIORAL contract authored RED at commit cee7b48;
    # the function is now wired into run_checks() (c8d5087, gate-check.py:376)
    # and these still hold as the unit-level half of the coverage.

    # 11. zero Test-author: lines with NO waiver → FAIL. D1's mode is a plan-time decision
    # the controller only reads; total absence used to WARN on retro-compat grounds, which
    # made a brand-new task list indistinguishable from a 2026-07 one.
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_NO_TEST_AUTHOR_LINES, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"] and f.failed,
                    "zero Test-author: lines FAILs when no legacy waiver is stated"))

    # 11b. the same shape with an explicit waiver → WARN naming the waiver, gate stays PASS.
    # This is the run-observability shape, and the WARN keeps it VISIBLE rather than silent.
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_WAIVED_NO_TEST_AUTHOR, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["warn"] and not f.failed
                     and any("legacy waiver exercised" in d for d in details),
                    "an explicit legacy waiver downgrades it to a WARN that names the waiver"))

    # 11c. a waiver marker with no stated reason is not a waiver — same rule as a bare
    # Tier-A `solo`. An empty escape hatch would be the whole mechanism defeated.
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(
        TASKS_WAIVED_NO_TEST_AUTHOR.replace(
            "<!-- gate-check: legacy-artifact — predates the 0.8.0 Test-author field -->",
            "<!-- gate-check: legacy-artifact — -->"), f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"],
                    "a waiver marker with no stated reason does not waive anything"))

    # 11d. the waiver covers ABSENCE ONLY — it never excuses partial presence.
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(
        TASKS_PARTIAL_TEST_AUTHOR.replace(
            "# Tasks: x",
            "# Tasks: x\n\n<!-- gate-check: legacy-artifact — old list -->"), f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"],
                    "the waiver does not excuse PARTIAL Test-author: presence — absence only"))

    # 12. partial presence → FAIL, naming the bare task ids (T02 here)
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_PARTIAL_TEST_AUTHOR, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"] and any("T02" in d for d in details),
                    "partial Test-author: presence FAILs and names the bare task id (T02)"))

    # 13. invalid value (not split/solo) → FAIL
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_INVALID_VALUE, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"],
                    "Test-author: value other than split/solo FAILs"))

    # 14. [Tier A] + solo with no reason after a dash → FAIL
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_TIER_A_SOLO_NO_REASON, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"],
                    "[Tier A] task with solo and no stated reason FAILs"))

    # 15. [Tier B] + split → WARN (over-ceremony), gate does not fail on this alone
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_TIER_B_SPLIT, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["warn"] and not f.failed,
                    "[Tier B] task with split WARNs as over-ceremony, does not FAIL"))

    # 16. all present and coherent → PASS
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_ALL_COHERENT, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["pass"]
                     and any(re.search(r"\ball\s+3\s+tasks\b", d) for d in details),
                    "all tasks carrying a coherent Test-author: mode PASSes"))

    # 17. a FENCED Test-author: example must never count — the same real tasks as #11
    # (no real Test-author: lines outside the fence, no waiver) now FAIL on total absence,
    # and the count proves the fenced line was credited to neither task: exactly the 2 real
    # tasks are reported. If the fence leaked, the verdict would be partial-presence naming
    # one task instead.
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_FENCED_EXAMPLE_IGNORED, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"] and any("(2 tasks)" in d for d in details),
                    "a fenced Test-author: example is stripped — exactly the 2 real tasks "
                    "count, and the fenced line is credited to neither"))

    # 17b. a REAL-SHAPED fenced task line (T99, matches TASK_LINE, carrying its
    # own fenced Test-author: line) alongside 3 real unfenced tasks (all 3
    # carrying the field) -> PASS counting the 3 unfenced tasks ONLY. T99
    # must neither count toward "present" nor be reported as "missing"/
    # partial — it must be invisible to the check entirely, proving
    # strip_fenced is actually exercised (the pre-existing fixture's
    # `T<NN>` placeholder never matched TASK_LINE, so this path went
    # unexercised even though the fixture existed).
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_FENCED_REALSHAPED_TASK_LINE, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["pass"]
                     and any(re.search(r"\ball\s+3\s+tasks\b", d) for d in details),
                    "a real-shaped fenced task line (T99) neither counts nor "
                    "FAILs-as-partial; verdict PASSes on the 3 unfenced tasks only"))

    # ── Seam tests: real (un-mocked) subprocess run of gate-check.py ──────────
    # check_test_author_mode is wired into run_checks() (c8d5087, gate-check.py:376)
    # beside check_task_tiers, so these seam tests exercise the live CLI path.
    # #18/#19 assert the retro-compat floor holds unchanged on real spec dirs.
    # #20 is the true seam case: a tasks.md that violates D1 (partial presence)
    # now exits 1 through the live, wired gate — this was the RED seam case
    # authored at cee7b48 and flipped GREEN by the c8d5087 wiring.

    # 18. real script against specs/run-observability (zero Test-author: lines) → exit 0
    # (the live-corpus cases run only where the source repo's specs/ exists — an
    # installed cache copy carries the code but not the corpus)
    repo_root = Path(__file__).parent.parent.parent.parent
    if not (repo_root / "specs").is_dir():
        return results
    ro_dir = repo_root / "specs" / "run-observability"
    proc = subprocess.run([sys.executable, str(CHECKER), str(ro_dir)],
                           capture_output=True, text=True, timeout=15)
    results.append((proc.returncode == 0,
                    "seam: gate-check.py on specs/run-observability still exits 0 (retro-compat live)"))

    # 19. real script against specs/harness-efficiency (dogfoods the field) → exit 0
    he_dir = repo_root / "specs" / "harness-efficiency"
    proc = subprocess.run([sys.executable, str(CHECKER), str(he_dir)],
                           capture_output=True, text=True, timeout=15)
    results.append((proc.returncode == 0,
                    "seam: gate-check.py on specs/harness-efficiency (dogfood) exits 0"))

    # 20. TRUE seam case: a tmp fixture dir violating D1 (partial presence)
    # exits 1 now that test-author-mode is wired into run_checks() (c8d5087,
    # gate-check.py:376, beside check_task_tiers). This was the RED case at
    # cee7b48 before the wiring landed; it now asserts the wired GREEN floor.
    rc, out = _run({"tasks.md": TASKS_PARTIAL_TEST_AUTHOR})
    results.append((rc == 1 and "test-author-mode" in out,
                    "seam: a tmp fixture dir violating D1 (partial presence) exits 1 "
                    "once test-author-mode is wired into run_checks()"))

    # ── 21. `stakes` — the consequence dial (1i) ──────────────────────────────
    # The erosion control: `low` is not reachable on a spec that flagged a security surface.
    # This is the ONE stakes finding that is not a judgment call, because the spec's own
    # checkboxes are the evidence and no plan prose overrides them.
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_STAKES_LOW})
    results.append((rc == 1 and "[stakes]" in out and "not reachable here" in out,
                    "`Stakes: low` on a security-flagged spec FAILS the gate"))

    # The same spec at `standard` passes — over-classifying every input-handling feature to
    # `high` is the failure this whole dial exists to end, so `standard` must be comfortable.
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_STAKES_STANDARD})
    results.append((rc == 0 and "\u2713 [stakes]" in out,
                    "`Stakes: standard` on a security-flagged spec PASSES"))

    # A level no downstream gate can read is worse than no level: each would pick its own
    # default and they would silently diverge.
    rc, out = _run({"plan.md": PLAN_STAKES_UNREADABLE})
    results.append((rc == 1 and "unreadable stakes level" in out,
                    "an unrecognised stakes level FAILS"))

    # The pre-0.16 floor joined the waiver regime: no `Stakes:` line and no waiver → FAIL.
    # A silent fallback-to-standard made a brand-new plan indistinguishable from a pre-dial
    # one — consistency with the other flipped floors beats a fourth silent floor.
    rc, out = _run({"plan.md": PLAN_GATES_BASE})
    results.append((rc == 1 and "[stakes]" in out and "legacy-artifact" in out,
                    "a plan with no `Stakes:` line and no waiver FAILs, naming the waiver form"))

    # The same plan with an explicit waiver → WARN naming it; downstream gates still fall
    # back to `standard`, but the exercise stays visible instead of silent.
    rc, out = _run({"plan.md": PLAN_GATES_BASE
                    + "\n<!-- gate-check: legacy-artifact — plan authored before the 0.16 stakes dial -->\n"})
    results.append((rc == 0 and "! [stakes]" in out and "legacy waiver exercised" in out,
                    "a stakes-less plan with a stated waiver WARNs, naming the waiver"))

    # `high` and `low` are departures from the default and owe a reason — but a stated level
    # with a thin reason still beats no level, so this WARNs rather than FAILs.
    rc, out = _run({"plan.md": PLAN_STAKES_HIGH_NO_REASON})
    results.append((rc == 0 and "! [stakes]" in out and "states no reason" in out,
                    "`Stakes: high` with no reason WARNs, never FAILs"))

    # F3 — punctuated reasons parse to the DECLARED level. A parenthesised or comma'd
    # reason must never demote a stated level to the no-line fallback: that WARN reads
    # "fall back to standard", which silently downgrades `high`.
    rc, out = _run({"plan.md": PLAN_STAKES_HIGH_PAREN_REASON})
    results.append((rc == 0 and "✓ [stakes]" in out and "Stakes: high" in out
                    and "pre-0.16" not in out,
                    "`Stakes: high (reason)` parses to level `high` with its reason read"))

    rc, out = _run({"plan.md": PLAN_STAKES_STANDARD_COMMA_REASON})
    results.append((rc == 0 and "✓ [stakes]" in out and "Stakes: standard" in out,
                    "`Stakes: standard, reason` parses to level `standard`"))

    # F3 — a fenced `Stakes:` example never counts as a declared level: the plan reads as
    # ABSENT, which (with no waiver) is now the loud FAIL, not a quiet fallback.
    rc, out = _run({"plan.md": PLAN_STAKES_FENCED_ONLY})
    results.append((rc == 1 and "[stakes]" in out and "high" not in out.split("[stakes]")[1][:120],
                    "a fenced `Stakes:` sample is ignored — the plan reads as absent and FAILs"))

    # I8 — under-calling on a money/PII spec: `standard` while the spec talks payments →
    # WARN (visible question), never FAIL (the spec's words are weaker evidence than its
    # checked boxes, which drive the `low` FAIL above).
    rc, out = _run({"spec.md": SPEC_MONEY, "plan.md": PLAN_STAKES_STANDARD})
    results.append((rc == 0 and "! [stakes]" in out and "money/PII" in out,
                    "`Stakes: standard` on a spec mentioning payments WARNs as an under-call"))

    # S9 — the two advisory WARNs are independent questions and BOTH must surface: a
    # reason-less `Stakes: low` on a money spec (no checked security box) is an under-call
    # question AND a missing-reason question. Early-returning after the first suppressed
    # the second.
    rc, out = _run({"spec.md": SPEC_MONEY_NO_BOX, "plan.md": PLAN_STAKES_LOW_NO_REASON})
    results.append((rc == 0 and "money/PII" in out and "states no reason" in out
                    and "✓ [stakes]" not in out,
                    "S9: under-call + missing-reason WARNs both surface (no early-return "
                    "suppression), and no pass line rides along"))

    # ── 22. `proven-by` — the evidence ladder (1d) ────────────────────────────
    rc, out = _run({"tasks.md": TASKS_PROVEN_BY_COMPLETE})
    results.append((rc == 0 and "\u2713 [proven-by]" in out,
                    "every task naming an evidence rung PASSES"))

    # Half-adopted is worse than absent: a reader cannot tell "nothing proves this" from
    # "nobody filled it in".
    rc, out = _run({"tasks.md": TASKS_PROVEN_BY_PARTIAL})
    results.append((rc == 1 and "proven-by" in out and "T02" in out,
                    "a partially-adopted `Proven by:` field FAILS, naming the gap"))

    rc, out = _run({"tasks.md": TASKS_PROVEN_BY_BAD_RUNG})
    results.append((rc == 1 and "unrecognised evidence rung" in out,
                    "free-text evidence ('the suite covers it') FAILS \u2014 the ladder is the point"))

    # Rungs 1\u20133 claim the evidence lives elsewhere; an unnamed claim is the assertion this
    # harness refuses to trust.
    rc, out = _run({"tasks.md": TASKS_PROVEN_BY_UNNAMED})
    results.append((rc == 1 and "does not NAME it" in out,
                    "`Proven by: machine gate` with nothing named FAILS"))

    # Retro-compat: a task list where NO task carries the line is a pre-0.16 artifact.
    rc, out = _run({"tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "! [proven-by]" in out and "pre-0.16" in out,
                    "zero `Proven by:` lines WARNs as a pre-0.16 tasks.md, never FAILs"))

    # ── 23. `deliverable-first` — the 1j gate (FR-3/4/5) ──────────────────────
    # Unit-level direct calls first (the function's own branch logic, D1-test style),
    # then the seam cases through the live CLI proving the check is wired into
    # run_checks(). Letters (a)–(h) are T01's contract in tasks.md.

    def _fwv(plan, spec, tasks):
        f = _gate_check.Findings()
        _gate_check.check_deliverable_first(plan, spec, tasks, f)
        verdicts = [s for s, c, d in f.items if c == "deliverable-first"]
        details = [d for s, c, d in f.items if c == "deliverable-first"]
        return verdicts, details

    # 23a. plan WITHOUT the section + spec flagging a user-facing surface → FAIL
    verdicts, details = _fwv(_PLAN_FWV_BASE, SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["fail"]
                     and any("First working version" in d for d in details),
                    "no ## First working version on a user-facing spec FAILs (1j)"))

    # 23b. section naming a task absent from tasks.md → FAIL naming it
    verdicts, details = _fwv(_plan_fwv("T99"), SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["fail"] and any("T99" in d for d in details),
                    "## First working version naming a nonexistent task FAILs"))

    # 23c. named task in position 4 → FAIL (not among the first 3; the josworld shape)
    verdicts, details = _fwv(_plan_fwv("T04"), SPEC_USER_FACING, TASKS_FWV)
    results.append(("fail" in verdicts
                     and any("position 4" in d for d in details),
                    "first-working-version task at position 4 FAILs — not among the first 3"))

    # 23h. the same shape carries the >2-preceding WARN — 3 tasks precede T04. The WARN
    # is belt+braces beside the FAIL: it survives even if a human later relaxes the
    # first-3 threshold (the 1j draft's open question 1).
    results.append(("warn" in verdicts
                     and any("3 task(s) precede" in d for d in details),
                    "3 tasks preceding the named one WARNs (independent of the FAIL)"))

    # 23d. named task whose `(files:)` lists ONLY tests/ paths → FAIL (the yootheme shape)
    verdicts, details = _fwv(_plan_fwv("T02"), SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["fail"]
                     and any("only test paths" in d for d in details),
                    "first-working-version task with test-only files FAILs"))

    # 23e. valid section, task in first 3, non-test file → pass
    verdicts, details = _fwv(_plan_fwv("T01"), SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["pass"],
                    "named task first with a non-test file PASSes"))

    # 23e-b. boundary: position 3 is INSIDE "among the first 3" (inclusive), and mixed
    # impl+test files are not "only tests/" — pass with no WARN riding along.
    verdicts, details = _fwv(_plan_fwv("T03"), SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["pass"],
                    "position 3 (inclusive boundary) with mixed files PASSes, no WARN"))

    # 23f. `N/A — docs-only` on a spec with NO user-facing surface → pass (threat-model
    # N/A convention: legitimate only for a genuinely non-runnable deliverable)
    verdicts, details = _fwv(PLAN_FWV_NA, SPEC_CLEAN_NOSEC, TASKS_FWV)
    results.append((verdicts == ["pass"],
                    "N/A first-working-version on a non-user-facing spec PASSes"))

    # 23f-b. the same N/A on a spec that DOES flag a user-facing surface → FAIL
    verdicts, details = _fwv(PLAN_FWV_NA, SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["fail"] and any("N/A" in d for d in details),
                    "N/A first-working-version on a user-facing spec FAILs"))

    # 23g. absence + a stated `legacy-artifact` waiver → WARN naming the waiver (FR-5:
    # never a silent pass), gate does not fail
    verdicts, details = _fwv(
        "<!-- gate-check: legacy-artifact — plan authored before the 1j gate -->\n"
        + _PLAN_FWV_BASE, SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["warn"]
                     and any("legacy waiver exercised" in d for d in details),
                    "absent section + legacy waiver WARNs, naming the waiver"))

    # 23i. a fenced `## First working version` example never counts — the plan reads as
    # ABSENT and FAILs, exactly as fenced Stakes:/task-line samples are stripped
    verdicts, details = _fwv(PLAN_FWV_FENCED_ONLY, SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["fail"]
                     and any("First working version" in d for d in details),
                    "a fenced-only ## First working version reads as absent and FAILs"))

    # 23j. a [HUMAN] yield point preceding the named task still counts toward position —
    # T04 stays fourth even when T02 is a [HUMAN] approval step
    verdicts, details = _fwv(_plan_fwv("T04"), SPEC_USER_FACING, TASKS_FWV_HUMAN_PRECEDING)
    results.append(("fail" in verdicts and any("position 4" in d for d in details),
                    "a [HUMAN] task preceding the named one still counts toward position"))

    # 23k. the section present but naming NO task → FAIL (points at nothing, orders nothing)
    verdicts, details = _fwv(PLAN_FWV_NO_TASK_NAMED, SPEC_USER_FACING, TASKS_FWV)
    results.append((verdicts == ["fail"] and any("names no task" in d for d in details),
                    "a ## First working version naming no task FAILs"))

    # 23L. seam: the check is WIRED into run_checks() — an armed user-facing spec whose
    # plan lacks the section exits 1 through the live CLI naming `deliverable-first`
    rc, out = _run({"spec.md": SPEC_USER_FACING, "plan.md": PLAN_FLOWS_NA,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "deliverable-first" in out,
                    "seam: armed spec + section-less plan exits 1 naming deliverable-first"))

    # 23m. seam GREEN floor: the same armed spec with a compliant plan (section naming
    # TASKS_GOOD's T01, non-test files, position 1) exits 0 with the pass finding — this
    # is also existing case 10ae's shape kept green under the new grammar
    rc, out = _run({"spec.md": SPEC_USER_FACING, "plan.md": PLAN_FLOWS_FILLED,
                    "tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "✓ [deliverable-first]" in out,
                    "seam: armed spec + compliant first-working-version plan exits 0"))

    # ── 24. `fr-source` — source traceability (FR-1/FR-2) ─────────────────────
    # Letters (a)–(f) are T02's contract in tasks.md. Unit-level direct calls first
    # (the function's own branch logic, D1-test style), then the seam through the
    # live CLI proving the check is wired into run_checks().

    def _frs(spec):
        f = _gate_check.Findings()
        _gate_check.check_fr_sources(spec, f)
        verdicts = [s for s, c, d in f.items if c == "fr-source"]
        details = [d for s, c, d in f.items if c == "fr-source"]
        return verdicts, details

    # 24b/c. all four corpus source shapes pass in one spec: quotation mid-paragraph,
    # `invented — approved` with its date across a line break, continuation-line Source:,
    # approved-by reference — and FR-1's backticked `Source:` mention reads as prose.
    verdicts, details = _frs(SPEC_FR_SOURCED)
    results.append((verdicts == ["pass"] and any("all 4" in d for d in details),
                    "all four corpus source shapes pass (quote, invented+date across a "
                    "line break, continuation line, approved-by)"))

    # 24a. an FR with no Source: → FAIL naming exactly the bare FR — and the waiver in
    # the same file does NOT rescue partial absence (never-waivable, like its siblings)
    verdicts, details = _frs(SPEC_FR_PARTIAL)
    results.append((verdicts == ["fail"]
                     and any("FR-2" in d for d in details)
                     and not any("FR-1" in d for d in details),
                    "a bare FR beside a sourced one FAILs naming only the bare FR, "
                    "waiver notwithstanding"))

    # 24d. `Source: invented` with no approval → FAIL naming the FRs (first word,
    # case-insensitive); a quoted source carrying a date is not an invention
    verdicts, details = _frs(SPEC_FR_INVENTED_BARE)
    results.append((verdicts == ["fail"]
                     and any("FR-1" in d and "FR-2" in d for d in details)
                     and not any("FR-3" in d for d in details),
                    "invented sources with no approval FAIL naming FR-1/FR-2, not the "
                    "quoted FR-3"))

    # 24e. zero sources across all FRs + the spec-level waiver → WARN naming the waiver
    verdicts, details = _frs(SPEC_FR_NONE_WAIVED)
    results.append((verdicts == ["warn"]
                     and any("legacy waiver exercised" in d for d in details),
                    "FRs with zero sources + a stated waiver WARNs, naming the waiver"))

    # 24e-b. the same spec with NO waiver → FAIL, and the finding tells the author the
    # waiver form exists (same convention as every flipped floor)
    verdicts, details = _frs(SPEC_FR_NONE)
    results.append((verdicts == ["fail"]
                     and any("legacy-artifact" in d for d in details),
                    "FRs with zero sources and no waiver FAILs, naming the waiver form"))

    # 24g. I-2: a colon-less FR def carrying the only `Source:` — the block flushes at
    # the column-0 bullet, so the apparently-sourced FR-1 FAILs as bare instead of
    # absorbing the donated source (never a vacuous all-sourced pass).
    verdicts, details = _frs(SPEC_FR_COLONLESS)
    results.append((verdicts == ["fail"]
                     and any("FR-1" in x for x in details)
                     and not any("FR-3" in x for x in details),
                    "(I-2) a colon-less FR def's Source: no longer donates upward — "
                    "the apparently-sourced FR-1 FAILs as bare"))

    # 24h. S-4: `Source: —` carries no word character — contentless, reads as bare.
    verdicts, details = _frs(SPEC_FR_DASH_SOURCE)
    results.append((verdicts == ["fail"]
                     and any("FR-1" in x for x in details)
                     and not any("FR-2" in x for x in details),
                    "(S-4) a Source: with no word character (`—`) FAILs as bare"))

    # 24-fence. a fenced `Source:` example never sources the FR above it
    verdicts, details = _frs(SPEC_FR_FENCED_SOURCE)
    results.append((verdicts == ["fail"],
                    "a fenced Source: example is stripped — the FR reads as bare"))

    # 24f. a spec defining no FR ids yields NO fr-source findings (nothing to source),
    # and the missing-section behaviour of the other checks is untouched via the CLI
    verdicts, details = _frs(SPEC_CLEAN_NOSEC)
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC})
    results.append((verdicts == [] and rc == 0 and "fr-source" not in out,
                    "a spec with no FR definitions produces no fr-source findings and "
                    "existing behaviour is unchanged"))

    # 24f-b. an FR id cited in prose (`(FR-7 …)`) is a mention, not a definition
    verdicts, details = _frs('# S\n\nThe post-mortem (FR-7 "multi-day") tells the story.\n')
    results.append((verdicts == [],
                    "an FR id cited in prose is not an FR definition"))

    # 24-seam. RED: a bare FR flips an otherwise-green artifact set to exit 1 naming
    # fr-source; GREEN floor: the same set with the FR sourced exits 0 with the pass line
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC + _FR_SECTION_BARE,
                    "plan.md": PLAN_THREATMODEL_NA, "tasks.md": TASKS_FR_CITED})
    results.append((rc == 1 and "fr-source" in out,
                    "seam: one bare FR exits 1 through the live CLI naming fr-source"))
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC + _FR_SECTION_SOURCED,
                    "plan.md": PLAN_THREATMODEL_NA, "tasks.md": TASKS_FR_CITED})
    results.append((rc == 0 and "✓ [fr-source]" in out,
                    "seam: the same set with the FR sourced exits 0 with the pass line"))

    # ── 25. `behaviour-cluster` — the FR-6/FR-7 grammar (T03) ─────────────────
    # Letters (a)–(f) are T03's contract in tasks.md. Unit-level direct calls first
    # (the function's own branch logic, D1-test style), then the interplay with
    # check_unit_test_contract (the waiver form is a Unit-test-line value), then the
    # seam through the live CLI, then the self-hosting corpus (this repo's own
    # specs/deliverable-first Cluster A carries the block).

    def _bhv(tasks, repo_root=None):
        f = _gate_check.Findings()
        _gate_check.check_behaviour_clusters(tasks, f, repo_root=repo_root)
        verdicts = [s for s, c, d in f.items if c == "behaviour-cluster"]
        details = [d for s, c, d in f.items if c == "behaviour-cluster"]
        return verdicts, details

    # 25a. (a) full block + RED-until file created by a member task → the waiver passes,
    # and the ✓ line names the cluster. Also (e) rides here: T02's ordinary `Unit test:`
    # line coexists with the block, and no finding rides along the single pass verdict.
    verdicts, details = _bhv(TASKS_BEHAVIOUR_VALID)
    results.append((verdicts == ["pass"] and any("N1" in d for d in details),
                    "(a/e) covered-by-cluster inside a full block whose test a member "
                    "creates PASSes, ✓ naming the cluster; the sibling's ordinary "
                    "unit-test line draws no finding"))

    # 25a-b. (a) unit-test-contract accepts the valid waiver as a stated contract — the
    # Tier A task is neither bare nor waived (the cluster's RED is the behavioural proof).
    f = _gate_check.Findings()
    _gate_check.check_unit_test_contract(TASKS_BEHAVIOUR_VALID, f)
    verdicts = [s for s, c, d in f.items if c == "unit-test-contract"]
    results.append((verdicts == ["pass"],
                    "(a) a VALID covered-by-cluster satisfies unit-test-contract — Tier A "
                    "accepted, per-task RED moved up to the behaviour level"))

    # 25b. (b) the same form in a cluster with NO behaviour block → FAIL naming both the
    # task id and the cluster heading text.
    verdicts, details = _bhv(TASKS_BEHAVIOUR_NO_BLOCK)
    results.append((verdicts == ["fail"]
                     and any("T01" in d and "N1" in d for d in details),
                    "(b) the waiver form in a cluster with NO behaviour block FAILs, "
                    "naming task and cluster"))

    # 25b-b. (b) …and the existing Tier-A-waiver FAIL fires in unit-test-contract —
    # never a silent pass for a Tier A leaning on a block that isn't there.
    f = _gate_check.Findings()
    _gate_check.check_unit_test_contract(TASKS_BEHAVIOUR_NO_BLOCK, f)
    fails = [d for s, c, d in f.items if c == "unit-test-contract" and s == "fail"]
    results.append((any("Tier A may not waive" in d and "T01" in d for d in fails),
                    "(b) a Tier A task using an INVALID covered-by-cluster trips the "
                    "Tier-A-waiver FAIL in unit-test-contract"))

    # 25c. (c) `Behaviour:` without `RED until:` while a member uses the waiver → FAIL
    # naming task, cluster, and the missing line.
    verdicts, details = _bhv(TASKS_BEHAVIOUR_PARTIAL)
    results.append((verdicts == ["fail"]
                     and any("T01" in d and "N1" in d and "RED until" in d for d in details),
                    "(c) a partial block (no `RED until:`) with a waiver-using member "
                    "FAILs, naming the missing line"))

    # 25d. (d) `RED until:` naming a test neither on disk nor in any member's files →
    # FAIL naming the dangling path; no ✓ line rides along.
    verdicts, details = _bhv(TASKS_BEHAVIOUR_DANGLING)
    results.append(("fail" in verdicts and "pass" not in verdicts
                     and any("tests/GhostTest.php" in d for d in details),
                    "(d) a RED-until test that resolves to nothing FAILs, naming the path"))

    # 25d-b. the disk rung: the SAME cluster shape whose RED-until file is not in any
    # member's files validates ONLY when the file exists under the repo root.
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "tests").mkdir()
        (Path(d) / "tests" / "OnDiskTest.php").write_text("<?php // fixture")
        verdicts, details = _bhv(TASKS_BEHAVIOUR_ON_DISK, repo_root=Path(d))
    results.append((verdicts == ["pass"],
                    "(d-inverse) a RED-until file existing on disk validates the block "
                    "even when no member's files name it"))
    verdicts, details = _bhv(TASKS_BEHAVIOUR_ON_DISK)
    results.append((verdicts == ["fail"],
                    "(d) the same cluster with no repo root to find the file on FAILs"))

    # 25g. I-1 (disk rung): `RED until: tests/::x` where `tests/` is a DIRECTORY under
    # the repo root → dangling FAIL — a directory satisfies `.exists()` but is not a
    # test file; only `.is_file()` may validate the disk rung.
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "tests").mkdir()
        verdicts, details = _bhv(TASKS_BEHAVIOUR_DIR_ONLY, repo_root=Path(d))
    results.append((verdicts == ["fail"] and any("tests/" in x for x in details),
                    "(I-1) a RED-until path naming an existing DIRECTORY FAILs as "
                    "dangling — only a real file satisfies the disk rung"))

    # 25h. I-1 (files rung): `RED until: src::x` beside a member whose files list
    # `src/notify.php` → dangling FAIL — exact comma-split path match required,
    # never a substring.
    verdicts, details = _bhv(TASKS_BEHAVIOUR_SUBSTRING)
    results.append((verdicts == ["fail"] and any("`src`" in x for x in details),
                    "(I-1) a RED-until path that is only a SUBSTRING of a member file "
                    "FAILs as dangling — exact match against comma-split paths"))

    # 25j. I-A (disk-rung confinement): the docstring claims "a FILE on disk under the
    # repo root"; the code must enforce it. Repo root is `outer/repo`; the escapes live
    # in `outer` (the root's parent). Four probes, each dangling:
    #   (a)  `/etc/hostname` — absolute, not test-shaped (both rungs reject);
    #   (a2) an absolute path to a REAL test-shaped file — only resolution can reject;
    #   (b)  `../tests/test_escape.py` — test-shaped `../` traversal to a real file in
    #        the root's parent — only the under-root resolution can reject;
    #   (c)  `README.md` — real file under the root but not test-shaped — only the
    #        shape rung can reject.
    # Then (d) the legitimate shape (`tests/test_x.py` under the root) still validates,
    # and (e) the shape-blind files rung still validates a member-declared non-test
    # path even when the disk rung rejects it.
    with tempfile.TemporaryDirectory() as d:
        outer = Path(d)
        ia_root = outer / "repo"
        (ia_root / "tests").mkdir(parents=True)
        (ia_root / "README.md").write_text("# not a test")
        (ia_root / "tests" / "test_x.py").write_text("# legitimate")
        (outer / "tests").mkdir()
        (outer / "tests" / "test_escape.py").write_text("# outside the root")
        ia = {label: _bhv(_bhv_disk_tasks(red), repo_root=ia_root)[0]
              for red, label in [
                  ("/etc/hostname", "absolute"),
                  (str(outer / "tests" / "test_escape.py"), "absolute-test-shaped"),
                  ("../tests/test_escape.py", "traversal"),
                  ("README.md", "in-repo-non-test")]}
        v_legit, _ = _bhv(_bhv_disk_tasks("tests/test_x.py"), repo_root=ia_root)
        v_files, _ = _bhv(TASKS_BEHAVIOUR_FILES_NONTEST, repo_root=ia_root)
    results.append((ia["absolute"] == ["fail"] and ia["absolute-test-shaped"] == ["fail"],
                    "(I-A a) an absolute RED-until path reads dangling — plain "
                    "(/etc/hostname) and test-shaped alike; pathlib's discarded left "
                    "operand no longer validates the block"))
    results.append((ia["traversal"] == ["fail"],
                    "(I-A b) a test-shaped ../ traversal to a real file in the root's "
                    "parent reads dangling — the resolved path must sit strictly under "
                    "the resolved repo root"))
    results.append((ia["in-repo-non-test"] == ["fail"],
                    "(I-A c) an in-repo non-test file (README.md) reads dangling — the "
                    "disk rung confines to test-shaped paths (FWV_TEST_PATH, the one "
                    "dialect)"))
    results.append((v_legit == ["pass"],
                    "(I-A d) the legitimate shape — tests/test_x.py existing under the "
                    "root — still validates the disk rung (no regression)"))
    results.append((v_files == ["pass"],
                    "(I-A e) the files rung stays shape-blind — a member-declared "
                    "non-test path (spec/checks.php) validates even though the disk "
                    "rung rejects it"))

    # 25i. S-2: backticks on the path half alone (`path`::method) must not false-dangle
    # — the path resolves exactly like the fully-quoted corpus form.
    verdicts, details = _bhv(TASKS_BEHAVIOUR_BACKTICK_PATH)
    results.append((verdicts == ["pass"],
                    "(S-2) a backticked path half (`path`::method) resolves like the "
                    "fully-quoted form — no false dangle"))

    # 25-fence. strip_fenced inheritance: a fenced block sample is invisible — the
    # cluster reads BLOCK-LESS (not full-with-dangling-RED, which a fence leak would
    # produce since tests/SampleTest.php resolves to nothing).
    verdicts, details = _bhv(TASKS_BEHAVIOUR_FENCED)
    results.append((verdicts == ["fail"]
                     and any("carries no behaviour block" in d for d in details)
                     and not any("SampleTest" in d for d in details),
                    "a fenced block sample is stripped — the cluster reads block-less"))

    # 25-outside. the waiver form on a task under no `### Cluster` heading → FAIL.
    verdicts, details = _bhv(TASKS_BEHAVIOUR_OUTSIDE)
    results.append((verdicts == ["fail"] and any("T01" in d for d in details),
                    "the waiver form outside any cluster FAILs, naming the task"))

    # 25f. (f) AC-3 back-compat lock: artifacts with no behaviour blocks anywhere yield
    # ZERO behaviour-cluster findings — unit level and through the live CLI.
    verdicts, details = _bhv(TASKS_GOOD)
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_GATES_FULL,
                    "tasks.md": TASKS_GOOD})
    results.append((verdicts == [] and rc == 0 and "behaviour-cluster" not in out,
                    "(f) no behaviour blocks anywhere → zero behaviour-cluster findings, "
                    "existing corpus output unchanged"))

    # 25-seam. the check is WIRED into run_checks(): a valid block exits 0 with the ✓
    # line; a block-less waiver exits 1 carrying BOTH the behaviour-cluster FAIL and the
    # Tier-A-waiver FAIL.
    rc, out = _run({"tasks.md": TASKS_BEHAVIOUR_VALID})
    results.append((rc == 0 and "✓ [behaviour-cluster]" in out and "N1" in out,
                    "seam: a valid behaviour-block tasks.md exits 0 with the ✓ line"))
    rc, out = _run({"tasks.md": TASKS_BEHAVIOUR_NO_BLOCK})
    results.append((rc == 1 and "behaviour-cluster" in out
                     and "Tier A may not waive" in out,
                    "seam: a block-less waiver exits 1 — behaviour-cluster FAIL plus the "
                    "Tier-A-waiver FAIL together"))

    # 25-self. the self-hosting corpus: this repo's specs/deliverable-first Cluster A
    # carries the full block (RED-until file created by member tasks) while its members
    # keep ordinary unit-test lines — exit 0 with the ✓ naming Cluster A (AC-2 shape).
    df_dir = repo_root / "specs" / "deliverable-first"
    proc = subprocess.run([sys.executable, str(CHECKER), str(df_dir)],
                           capture_output=True, text=True, timeout=15)
    results.append((proc.returncode == 0
                     and "✓ [behaviour-cluster]" in proc.stdout
                     and "Cluster A" in proc.stdout,
                    "seam: specs/deliverable-first self-hosts the grammar — exit 0, "
                    "✓ naming Cluster A"))

    # 26. suffixed task ids are VISIBLE to every per-task check. Regression for the
    # live todai-client miss: b-suffixed tasks were skipped wholesale, so a spec could
    # omit a tier on one and still read GATE: PASS, and a 6-task cluster counted as 4.
    rc, out = _run({"tasks.md": TASKS_SUFFIXED_ID_NO_TIER})
    results.append((rc == 1 and "task-tier" in out and "T01b" in out,
                    "a b-suffixed task missing its test tier FAILS and is named"))
    rc, out = _run({"tasks.md": TASKS_SUFFIXED_ID_OVERSIZED})
    results.append((rc == 1 and "review-cluster" in out,
                    "b-suffixed tasks count toward the <=4 cluster-size rule"))

    # ── 27. lanes — FR-1/FR-3/FR-4 (T01) ─────────────────────────────────────
    results.append(test_lane_behaviour_bare_members_pass())

    rc, out = _run({"tasks.md": TASKS_LANE_IN_LABEL})
    results.append((rc == 0 and "✓ [cluster-lane]" in out,
                    "lane: `lane: behaviour` on the heading label counts too"))

    rc, out = _run({"tasks.md": TASKS_LANE_MIXED})
    results.append((rc == 0 and "1 behaviour" in out and "1 contract" in out,
                    "lane: a mixed file (behaviour + reasoned contract) exits 0 naming both counts"))

    rc, out = _run({"tasks.md": TASKS_LANE_SIBLING_BARE})
    results.append((rc == 1 and "cluster-lane" in out and "L2" in out,
                    "lane (b): one cluster lane-declared, sibling bare → FAIL naming the sibling"))

    rc, out = _run({"tasks.md": TASKS_LANE_BOUNDARY})
    results.append((rc == 1 and "cluster-lane" in out and "T03" in out and "auth" in out,
                    "lane (c): behaviour-lane member touching auth/ → FAIL naming task and term"))

    rc, out = _run({"plan.md": PLAN_CLUSTER_STAKES_HIGH, "tasks.md": TASKS_LANE_BEHAVIOUR_BARE})
    results.append((rc == 1 and "cluster-lane" in out and "high" in out,
                    "lane (d): behaviour lane under a per-cluster `high` row → FAIL"))
    rc, out = _run({"plan.md": PLAN_STAKES_HIGH_LINE, "tasks.md": TASKS_LANE_BEHAVIOUR_BARE})
    results.append((rc == 1 and "cluster-lane" in out and "high" in out,
                    "lane (d'): behaviour lane under a spec-level `Stakes: high` → FAIL"))

    rc, out = _run({"tasks.md": TASKS_LANE_CONTRACT_NO_REASON})
    results.append((rc == 0 and "! [cluster-lane]" in out and "L2" in out,
                    "lane (e): contract lane, no boundary hit, no reason → WARN naming the cluster"))
    rc, out = _run({"tasks.md": TASKS_LANE_CONTRACT_REASON})
    results.append((rc == 0 and "! [cluster-lane]" not in out,
                    "lane (f): the same with a dash-reason → silent"))

    rc, out = _run({"tasks.md": TASKS_LANE_INVALID})
    results.append((rc == 1 and "cluster-lane" in out and "fast" in out,
                    "lane: an unknown lane value FAILs naming it"))

    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_GATES_FULL, "tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "cluster-lane" not in out,
                    "lane (g): no `Lane:` anywhere → zero cluster-lane findings (AC-2 lock)"))

    # ── 28. lane-aware per-task checks — FR-2 (T02) ──────────────────────────
    rc, out = _run({"tasks.md": TASKS_LANE_BEHAVIOUR_BARE})
    results.append((rc == 0 and "✓ [task-tier]" in out and "✓ [test-author-mode]" in out
                     and "✓ [proven-by]" in out and "✓ [unit-test-contract]" in out
                     and "exempt" in out,
                    "lane (T02 a): the four per-task checks pass over bare members and say how many are exempt"))

    rc, out = _run({"tasks.md": TASKS_LANE_DRIFT})
    results.append((rc == 0 and "! [lane-drift]" in out and "T02" in out,
                    "lane (T02 b): a behaviour-lane member carrying Tier/Test-author lines → lane-drift WARN"))

    rc, out = _run({"tasks.md": TASKS_LANE_PARTIAL_BLOCK})
    results.append((rc == 1 and "cluster-lane" in out and "RED until" in out,
                    "lane (T02 c): behaviour lane with a partial block → FAIL naming the missing line"))

    rc, out = _run({"tasks.md": TASKS_LANE_NO_INTEGRATION})
    results.append((rc == 1 and "integration-gate" in out,
                    "lane (T02 d): behaviour lane with no Integration gate: → FAIL"))

    rc, out = _run({"tasks.md": TASKS_LANE_CONTRACT_MISSING_TIER})
    results.append((rc == 1 and "task-tier" in out and "T05" in out,
                    "lane (T02 e): the contract cluster beside it still gets every per-task check"))

    # ── 29. lane-aware review markers — FR-5 (T03) ───────────────────────────
    rc, out = _run({"tasks.md": TASKS_LANE_BEHAVIOUR_BARE})
    results.append((rc == 0 and "✓ [review-gate-marker]" in out and "BRANCH REVIEW" in out,
                    "lane (T03 a): behaviour clusters without review markers + one tiered branch marker → pass"))
    rc, out = _run({"tasks.md": TASKS_LANE_NO_BRANCH_REVIEW})
    results.append((rc == 1 and "review-gate-marker" in out and "BRANCH REVIEW" in out,
                    "lane (T03 b): no `── BRANCH REVIEW ──` marker → FAIL"))
    rc, out = _run({"tasks.md": TASKS_LANE_BRANCH_REVIEW_NO_TIER})
    results.append((rc == 1 and "review-tier" in out and "BRANCH REVIEW" in out,
                    "lane (T03 c): a branch marker without a tier → FAIL"))
    rc, out = _run({"tasks.md": TASKS_LANE_BEHAVIOUR_WITH_REVIEW_GATE})
    results.append((rc == 0 and "! [review-gate-marker]" in out and "L1" in out,
                    "lane (T03 d): a behaviour-lane cluster carrying a review marker → WARN"))
    rc, out = _run({"tasks.md": TASKS_NO_REVIEW_GATE})
    results.append((rc == 1 and "review-gate-marker" in out and "BRANCH REVIEW" not in out,
                    "lane (T03 e): a lane-less file keeps today's marker findings, no branch-marker demand"))

    # ── 30. two checker bugs the self-hosting run found (harness-inversion T11) ──
    # (i) a behaviour-lane RED-until that resolves ONLY on disk under the repo root is
    # valid for the lane check exactly as it is for the behaviour-cluster check.
    tasks_disk = TASKS_LANE_BEHAVIOUR_BARE.replace(
        "RED until: `tests/CaseModelTest.php::test_case_registered`",
        "RED until: `tests/OnDiskCaseTest.php::test_case_registered`")
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "tests").mkdir()
        (Path(d) / "tests" / "OnDiskCaseTest.php").write_text("<?php // fixture")
        f = _gate_check.Findings()
        _gate_check.check_cluster_lanes(tasks_disk, None, f, repo_root=Path(d))
        on_disk = [st for st, c, _ in f.items if c == "cluster-lane"]
        f2 = _gate_check.Findings()
        _gate_check.check_cluster_lanes(tasks_disk, None, f2, repo_root=None)
        no_root = [st for st, c, _ in f2.items if c == "cluster-lane"]
    results.append((on_disk == ["pass"] and no_root == ["fail"],
                    "lane: a RED-until file on disk under the repo root validates the lane's block; "
                    "without a root it is dangling — same rungs as behaviour-cluster"))
    # (ii) a task that MENTIONS `── BRANCH REVIEW ──` in prose is not a second marker.
    tasks_mention = TASKS_LANE_BEHAVIOUR_BARE.replace(
        "- [ ] T04 the archive template  (files: templates/archive-case.php)",
        "- [ ] T04 the archive template; the file ends at one `── BRANCH REVIEW ──` marker  (files: templates/archive-case.php)")
    rc, out = _run({"tasks.md": tasks_mention})
    results.append((rc == 0 and "✓ [review-gate-marker]" in out,
                    "lane: a prose mention of the branch marker inside a task is not counted as one"))

    # (iii) heading label and Lane: line disagree → WARN, the heading wins (review S-1)
    tasks_conflict = TASKS_LANE_IN_LABEL.replace(
        "(4 tasks · lane: behaviour)\n\n", "(4 tasks · lane: contract)\n\nLane: behaviour\n")
    rc, out = _run({"tasks.md": tasks_conflict})
    results.append(("! [cluster-lane]" in out and "disagree" in out and "heading wins" in out,
                    "lane: heading `lane: contract` beside a `Lane: behaviour` line → WARN naming both, heading wins"))

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
