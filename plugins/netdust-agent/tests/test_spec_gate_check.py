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

## Security-relevant surfaces
- [x] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] None of the above

## Open questions / [NEEDS CLARIFICATION]
[List remaining ambiguities as `[NEEDS CLARIFICATION: …]`. This section must be empty.]
"""

SPEC_CLEAN_NOSEC = """# Feature Specification: Rename a label

## Security-relevant surfaces
- [ ] User-controlled URLs / server-side outbound requests
- [x] None of the above

## Clarifications
- Q: which label? → A: the footer copyright label
"""

SPEC_WITH_UNRESOLVED = """# Feature Specification: Importer

## Functional requirements
- FR-1: import a CSV [NEEDS CLARIFICATION: max file size?]

## Security-relevant surfaces
- [x] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
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
"""

# A spec that predates the contract carrying this section at all → WARN, never FAIL.
# Same retro-compat stance as test-author-mode's pre-0.8 WARN. The two live specs/ dirs
# are the only reason it is not "fail" — flip gate-check.py's "warn" once they carry it.
SPEC_PRE_TEMPLATE_NO_SC = """# Feature Specification: Rename a label

## Problem / why

The footer copyright label reads 2019.

## Security-relevant surfaces
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
- **FR-1:** system MUST publish a module
- **FR-2:** system MUST reject an unauthorised editor
- **FR-3:** system MUST log every publish

## Security-relevant surfaces
- [x] None of the above
"""

TASKS_COVERS_ALL_REQS = """# Tasks: Course publishing

### Cluster C1  (3 tasks \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier A] publish a module (FR-1, SC-1)  (files: publish.ts)
      Unit test: publishes in one call; denial path: unauthorised editor rejected
- [ ] T02 [Tier A] authorisation guard (FR-2)  (files: guard.ts)
      Unit test: rejects a non-editor; allows an editor
- [ ] T03 [Tier B] publish audit log (FR-3)  (files: log.ts)
      Unit test: no unit test: Tier B, wiring over the existing logger

\u2500\u2500 REVIEW GATE \u2500\u2500  *(STOP: commit C1 \u2014 tier STANDARD)*
"""

# FR-1 cited, FR-2 / FR-3 / SC-1 traced to nothing → the convention IS in use, so FAIL.
TASKS_COVERS_SOME_REQS = """# Tasks: Course publishing

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier A] publish a module (FR-1)  (files: publish.ts)
      Unit test: publishes in one call; denial path: unauthorised editor rejected

\u2500\u2500 REVIEW GATE \u2500\u2500  *(STOP: commit C1 \u2014 tier STANDARD)*
"""

# No id cited anywhere — the live-corpus shape. WARN, never FAIL.
TASKS_CITES_NO_REQS = """# Tasks: Course publishing

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier A] publish a module  (files: publish.ts)
      Unit test: publishes in one call; denial path: unauthorised editor rejected

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

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# Correct mode on the same task — no warning.
TASKS_TIER_A_SPLIT_ON_BOUNDARY = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier A] rewrite the token store  (files: db/tokens.sql)
      Test-author: split
      Unit test: replays the migration on a seeded fixture

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier FULL)*
"""

# Tier B on a security-boundary file with NOTHING proving it — a guard nobody checks.
# Before 0.15 this WARNed on the TIER alone; it now WARNs on the ABSENT EVIDENCE, which is
# what the finding was always reaching for.
TASKS_TIER_B_ON_BOUNDARY = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: FULL)
- [ ] T01 [Tier B] tidy the session guard  (files: lib/session-guard.ts)
      Test-author: solo \u2014 Tier B
      Unit test: no unit test: Tier B, tidy-up only

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

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier LIGHT)*
"""

PLAN_GATES_FULL = """# Implementation Plan: Webhook receiver

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
"""

# ── `stakes` fixtures — the consequence dial (1i) ─────────────────────────────
# The class dial scales PLANNING ceremony; this scales VERIFICATION effort. `low` buys the
# lightest verification in the harness, so the one place it must be unreachable is work the
# SPEC ITSELF flagged as security-relevant. `standard` there is fine — that is the honest
# classification for most input-handling features, and presence-vs-decision keeps it cheap.

PLAN_STAKES_LOW = PLAN_GATES_FULL + """
## Stakes  [GATE]
Stakes: low \u2014 worst case is a broken-looking page
"""

PLAN_STAKES_STANDARD = PLAN_GATES_FULL + """
## Stakes  [GATE]
Stakes: standard \u2014 a failure breaks a working feature for real users, recoverably
"""

PLAN_STAKES_UNREADABLE = PLAN_GATES_FULL + """
## Stakes  [GATE]
Stakes: medium-ish \u2014 somewhere in between
"""

PLAN_STAKES_HIGH_NO_REASON = PLAN_GATES_FULL + """
## Stakes  [GATE]
Stakes: high
"""

# F3 — the field tolerates any human reason-punctuation. A declared level must never be
# silently demoted to the no-line WARN because its reason used parentheses or a comma
# instead of an em-dash: the WARN reads "fall back to standard", which is a silent
# downgrade of a level somebody stated.
PLAN_STAKES_HIGH_PAREN_REASON = PLAN_GATES_FULL + """
## Stakes  [GATE]
Stakes: high (touches billing rows that cannot be replayed)
"""

PLAN_STAKES_STANDARD_COMMA_REASON = PLAN_GATES_FULL + """
## Stakes  [GATE]
Stakes: standard, breaks a working feature recoverably
"""

# F3 — a fenced `Stakes:` example (a plan quoting the template) is not a declared level.
# The plan below carries ONLY the fenced sample, so the verdict must be the no-line WARN.
PLAN_STAKES_FENCED_ONLY = PLAN_GATES_FULL + """
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

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier STANDARD)*
"""

TASKS_PROVEN_BY_BAD_RUNG = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier B] render the confirmation partial  (files: src/views/thanks.php)
      Test-author: solo \u2014 Tier B
      Proven by: the suite covers it
      Unit test: no unit test: Tier B, presentational

\u2500\u2500 REVIEW GATE \u2500\u2500  *(tier STANDARD)*
"""

TASKS_PROVEN_BY_UNNAMED = """# Tasks: x

### Cluster C1  (1 task \u00b7 provisional tier: STANDARD)
- [ ] T01 [Tier B] render the confirmation partial  (files: src/views/thanks.php)
      Test-author: solo \u2014 Tier B
      Proven by: machine gate
      Unit test: no unit test: Tier B, presentational

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
"""

# The reference COMPLIANT tasks.md: sized clusters, a STOP marker closing each, a
# provisional tier per cluster (1h), and a stated Unit test: contract per task (1d).
# It carries the tiers and contracts on the cluster headings / continuation lines exactly
# as the live specs/ dirs write them.
TASKS_GOOD = """# Tasks: Webhook receiver

## Phase 1 — receiver

### Cluster C1  (2 tasks · provisional tier: FULL)
- [ ] T01 [P] [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects an RFC1918 target and an http:// downgrade; allows a public https URL
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Unit test: no unit test: Tier B, wiring only — covered by the cluster integration gate

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, `/code-review` — tier FULL)*

### Cluster C2 — (irreversible: drop legacy table) — solo
- [ ] T03 [Tier A] migration  (files: migrations/001.sql)
      Unit test: replays the migration on a seeded fixture; denial path: refuses to run twice

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

    # 10d. retro-compat: no ## Success criteria section at all → WARN, gate stays PASS
    rc, out = _run({"spec.md": SPEC_PRE_TEMPLATE_NO_SC})
    results.append((rc == 0 and "! [success-criteria]" in out,
                    "spec predating the contract, no ## Success criteria: WARNs, never FAILs"))

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

    # 10n. retro-compat: zero `Unit test:` lines anywhere → WARN, never FAIL
    rc, out = _run({"tasks.md": TASKS_NO_TEST_AUTHOR_LINES})
    results.append(("! [unit-test-contract]" in out,
                    "zero `Unit test:` lines WARNs as a pre-contract tasks.md, never FAILs"))

    # ── `security-boundary-mode` — the free-form `solo` reason, made visible ───

    # 10s. Tier A + solo on a token/migration file → WARN (gate still PASSes: heuristic)
    rc, out = _run({"tasks.md": TASKS_TIER_A_SOLO_ON_BOUNDARY})
    results.append((rc == 0 and "! [security-boundary-mode]" in out
                     and "T01" in out and "ALWAYS split" in out,
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

    # 10q. retro-compat (the live-corpus shape): no id cited at all → WARN, gate stays PASS
    rc, out = _run({"spec.md": SPEC_WITH_REQS, "tasks.md": TASKS_CITES_NO_REQS})
    results.append((rc == 0 and "! [requirement-coverage]" in out,
                    "a task list citing no requirement id WARNs as pre-convention, never FAILs"))

    # 10r. a spec with no numbered requirements at all → WARN (nothing is traceable)
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC, "tasks.md": TASKS_CITES_NO_REQS})
    results.append(("! [requirement-coverage]" in out and "no FR-n" in out,
                    "a spec declaring no FR-n/SC-n ids WARNs — nothing is traceable"))

    # ── D1 `test-author-mode` — one fixture per plan.md D1 rules-table row ────
    # check_test_author_mode() is called DIRECTLY (unit level), independent of
    # run_checks()/the CLI, to pin down the function's own branch logic. These
    # assertions were the BEHAVIORAL contract authored RED at commit cee7b48;
    # the function is now wired into run_checks() (c8d5087, gate-check.py:376)
    # and these still hold as the unit-level half of the coverage.

    # 11. retro-compat: zero Test-author: lines anywhere → WARN, GATE stays PASS
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_NO_TEST_AUTHOR_LINES, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["warn"] and not f.failed,
                    "zero Test-author: lines (run-observability-shaped) WARNs, never FAILs"))

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

    # 17. a FENCED Test-author: example must never count — same real tasks as #11
    # (no real Test-author: lines outside the fence) must still WARN, not FAIL,
    # and the fenced example's own line must not be double-counted as "present".
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_FENCED_EXAMPLE_IGNORED, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["warn"] and not f.failed,
                    "a fenced Test-author: example is stripped and never counted"))

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
    repo_root = Path(__file__).parent.parent.parent.parent
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

    # Retro-compat, same stance as test-author-mode: pre-0.16 plans predate the dial.
    rc, out = _run({"plan.md": PLAN_GATES_FULL})
    results.append((rc == 0 and "! [stakes]" in out and "pre-0.16 plan" in out,
                    "a plan with no `Stakes:` line WARNs and falls back to standard"))

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

    # F3 — a fenced `Stakes:` example never counts as a declared level.
    rc, out = _run({"plan.md": PLAN_STAKES_FENCED_ONLY})
    results.append((rc == 0 and "! [stakes]" in out and "pre-0.16" in out,
                    "a fenced `Stakes:` sample is ignored — the plan reads as no-line WARN"))

    # I8 — under-calling on a money/PII spec: `standard` while the spec talks payments →
    # WARN (visible question), never FAIL (the spec's words are weaker evidence than its
    # checked boxes, which drive the `low` FAIL above).
    rc, out = _run({"spec.md": SPEC_MONEY, "plan.md": PLAN_STAKES_STANDARD})
    results.append((rc == 0 and "! [stakes]" in out and "money/PII" in out,
                    "`Stakes: standard` on a spec mentioning payments WARNs as an under-call"))

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

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
