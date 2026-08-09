# Spec — Deliverable-first harness

**Repo:** `netdust-plugins` (marketplace source — never the cache) · **Plugin:** `netdust-agent`
**Provenance:** the 2026-08-09 daan `musician-events` session post-mortem (full transcript
`ca1d4703…jsonl`), the human's four intake decisions of the same day, and the dormant 1j
proposal (`plugins/netdust-agent/skills/planning/references/gate-1j-deliverable-first.md`,
drafted 2026-08-03 from calibration `deliverable-last` — today was that failure's THIRD
recorded instance).

## Problem / why

A 3-hour session asked for four things ("write a service for events, make sure we can
filter passed events, … arrange the metabox fields in good ux. some events are private,
some use grantaccess") and delivered the two cheapest — a field list and a tab layout —
while both risky asks went unbuilt. The harness followed faithfully. Six links in the
failure chain, each currently uncontrolled:

1. **A requirement was invented at spec time** (FR-7 "multi-day counts as upcoming until
   it ends") and then served — a derived field, a save hook, a five-clause test, and an
   open bug descend from a sentence nobody asked for. Nothing checks an FR against the ask.
2. **Tasks were ordered by build dependency, not by ask**: scaffold → fields → tabs →
   (never reached) filtering → private. The session ran out of hours holding the half the
   human could have eyeballed. This is `deliverable-last`, instance three.
3. **Per-task RED tests rewarded shape assertions**: a 276-line test proved a config array's
   arrangement — inadmissible as proof of behaviour, expensive, and blind to the one live
   Critical (`/events/` 404) that loading the page finds in ten seconds.
4. **Reviewers were dispatched before anyone loaded the artifact**: three agents reasoned
   about markup; zero looked at it.
5. **verify-budget HALTed and was talked past — for the third time.** A gate that summons
   the human to arbitrate a test-to-code ratio is a nag, not a control ("what is this halt?
   that system doesn't work" — the human, 2026-08-09).
6. **The class dial reads shape, not decision-density**: multi-file declarative config
   routed as full Class A ceremony.

## User stories, prioritized

### P1 — A session's output is the thing that was asked for
As the human partner, when I approve a plan and come back hours later, the work that
exists is the deliverable I named — running, loadable — not infrastructure around it.
The plan is refused mechanically when its first working version is missing, mis-ordered,
or made only of tests; and every requirement in the spec traces to words I actually said
or to an invention I explicitly approved.

### P2 — Tests prove behaviour, in proportion
As the human partner, a cluster of work carries ONE failing behavioural test whose
assertion is observable from outside the file (a URL and status, a command and its
output, a query count, a screen state) — config shapes are inadmissible. Tasks below the
behaviour boundary don't manufacture their own proofs; they must not break the proof
already running. The suite gate tolerates exactly that named RED mid-cluster and refuses
to close the cluster while it still fails. Nothing ever interrupts the run to ask me
whether there are too many tests.

### P3 — Ceremony is priced by decisions, and eyes precede reviewers
As the human partner, declarative work with no design questions routes light regardless
of file count, and no reviewer is dispatched on a user-facing diff before the artifact
has been loaded once and what was seen recorded.

## Functional requirements

### Source traceability (kills link 1)
- **FR-1:** Every functional requirement in a spec carries a `Source:` line — either a
  quotation from the request/conversation, or `invented — approved <date>` naming the
  human approval. Source: invented — approved 2026-08-09 ("All six fixes", intake Q4;
  mechanism follows from the post-mortem's "I invented FR-7 and then served it").
- **FR-2:** `gate-check.py` FAILs a spec containing any FR without a `Source:` line, and
  FAILs an `invented` source carrying no approval; a pre-convention spec states the
  existing `legacy-artifact` waiver and degrades to WARN. Source: invented — approved
  2026-08-09 (same decision; reuses the waiver convention already in the checker).

### Deliverable-first ordering (kills link 2 — the 1j draft, parameters now decided)
- **FR-3:** A plan must carry a `## First working version` section naming a task,
  what a human can see or run once it lands, and the command/URL/screen that shows it.
  `N/A` only for genuinely non-runnable deliverables, justified like a threat-model N/A.
  Source: the 1j draft (2026-08-03), adopted verbatim; enforcement approved 2026-08-09.
- **FR-4:** `gate-check.py` FAILs when the section is absent (unless the spec's user-facing
  surfaces are `None of the above`), when the named task does not exist, when it is not
  among the first 3 tasks, or when its `(files:)` segment lists only test paths. It WARNs
  when more than 2 tasks precede the named one. Source: human decision 2026-08-09, intake
  Q3: "Among first 3, FAIL".
- **FR-5:** Legacy plans authored before the gate state the `legacy-artifact` waiver →
  WARN, never silent pass. Source: the 1j draft, open question 2, resolved by the same Q3
  answer (its FAIL-from-day-one option).

### Behaviour-level RED with transition gating (kills links 3 and 5's root cause)
- **FR-6:** A task cluster may declare a behaviour block: `Behaviour:` (one sentence),
  `Observable:` (how it is verified from OUTSIDE the file — URL + expected status,
  command + expected output, query result count, screen state), and `RED until:` naming
  one test (path::method). Source: the human's own proposal, 2026-08-09: "It moves up one
  level. The failing test belongs to the behaviour, not to the task… gating on transition
  rather than existence… an array shape isn't observable from outside the file."
- **FR-7:** Inside a cluster carrying a behaviour block, a member task may satisfy its
  test-contract line with `covered by cluster behaviour` instead of its own unit test;
  `gate-check.py` accepts that form only when the enclosing cluster carries the block and
  its `RED until:` names a test file that exists or is created by a task in the cluster.
  Source: same proposal ("Tasks below a behaviour boundary don't need their own proof,
  they need to not break the proof that's already running").
- **FR-8:** The subagent-stop hook tolerates, mid-cluster, a suite failure consisting of
  exactly the cluster's named RED test (read from the run ledger), blocks any other
  failure as it does today, and blocks cluster close while the named test still fails.
  With no behaviour block in play, behaviour is bit-for-bit today's. Source: human
  decision 2026-08-09, intake Q2: "Full: grammar + checker + hook".
- **FR-9:** The observable-admissibility rule (config/array shapes inadmissible as a
  cluster observable) is stated as an authoring rule in the planning skill, enforced at
  the sequencer level like gate 1a — the machine checks presence and the named test;
  admissibility judgment stays with the author. Source: invented — approved 2026-08-09
  (Q2; honest-enforcement split follows the harness's existing 1a convention).

### verify-budget stands down (link 5)
- **FR-10:** `verify-budget.py` never exits non-zero and never HALTs a run: it prints its
  ratio as a one-line report, recorded in cluster evidence as telemetry. Source: the
  human, 2026-08-09: "what is this halt? that system doesn't work. am i supposed to say
  stop coding? the whole idea here is to write code and have it tested, shoud not be
  difficult."
- **FR-11:** No skill text retains HALT semantics for verify-budget; the building spine
  records the line and moves on — the human is never summoned to arbitrate a ratio.
  Source: same statement.

### Eyes before reviewers (link 4)
- **FR-12:** Before any reviewer is dispatched on a cluster whose diff touches a
  user-facing surface, the controller loads the artifact once (page, screen, command) and
  records an `Artifact-load:` evidence line — what was run/opened and what was observed.
  Source: post-mortem, approved 2026-08-09: "We had four agents reasoning about markup and
  zero looking at it… A browser pass before any reviewer dispatch would have found C1
  instantly."
- **FR-13:** The rule lives in the building skill's review-gate step with a red-flag row;
  sequencer-enforced (the reviewer-dispatch step refuses to proceed without the line in
  evidence). Source: invented — approved 2026-08-09 (Q4 "All six fixes").

### Decision-density class dial (link 6)
- **FR-14:** The intake table's class question is decision-density, not file count: work
  that is declarative configuration with no open design questions routes Class E even
  when it spans several files. Source: post-mortem, approved 2026-08-09: "The class dial
  sorts by shape, not size… There's no dial for 'this is a 30-line config file'."
- **FR-15:** Intake gains the explicit question "would a competent human do this inside
  half an hour?" and a red-flag row for routing declarative work heavy. Source: post-mortem
  ("'Would a human do this in 5 minutes?' as an explicit intake question"), approved
  2026-08-09.

## Acceptance criteria

- **AC-1:** Running the new `gate-check.py` against a fixture copy of daan's
  `specs/musician-events` artifacts FAILs, naming at least the deliverable-first and
  fr-source findings — the artifacts that passed on 2026-08-09 no longer do.
- **AC-2:** Running it against THIS feature's own artifacts is GREEN (self-hosting).
- **AC-3:** All pre-existing checker behaviours are unchanged for artifacts that carry
  none of the new grammar (no new FAIL on the existing green corpus).
- **AC-4:** The hook change is invisible to any project with no behaviour block in its
  ledger — existing fixture tests pass unmodified.
- **AC-5:** A mid-cluster implementer close whose only suite failure is the cluster's
  named RED test is admitted; any other red is blocked; cluster close is blocked while
  the named test is red.
- **AC-6:** verify-budget above-ceiling input exits 0 and prints the report line.

## Success criteria

- **SC-1:** The musician-events fixture replay produces exit 1 with ≥ 2 findings the
  2026-08-09 checker did not emit, in 1 command.
- **SC-2:** The plugin's full pytest suite passes with 0 failures, including ≥ 14 new
  cases across the four changed surfaces (1j, fr-source, behaviour grammar, hook).
- **SC-3:** 0 occurrences of verify-budget HALT semantics remain across
  `plugins/netdust-agent/skills/**` and `bin/verify-budget.py` (grep for `HALT` in those
  scopes returns 0 verify-budget-related hits), and `verify-budget.py` exits 0 on 100% of
  its test inputs.
- **SC-4:** All 3 hook transition cases (named-RED admitted, other-red blocked,
  close-while-red blocked) are covered by tests that fail against the pre-change hook —
  3 of 3 demonstrated RED-first.
- **SC-5:** The plan's failure-chain table maps all 6 links of the 2026-08-09 session to
  a named control landed by this spec — 6 of 6, each citing the FR and the task.
- **SC-6:** 0 existing test assertions weakened: the diff to `tests/` deletes or edits
  existing assertions only where a changed contract is named in the plan (verify-budget's
  exit code), verified by review of the test diff.

## Security-relevant surfaces

- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [x] None of the above

The artifacts parsed are repo-local files authored by the team; the hook reads a ledger
the harness itself writes. No untrusted input, no auth surface, no outbound requests.

## User-facing surfaces

- [ ] A new or changed public page / view / listing
- [ ] A new or changed admin screen or editing surface
- [ ] An endpoint a client or agent will drive
- [x] None of the above

Developer/agent tooling; its behavioural contract lives in the pytest cases each task
names, not in an acceptance-flow matrix.

## Assumptions

- The marketplace source repo is the single edit target; the cache
  (`~/.claude/plugins/cache/…`) is never edited and picks changes up on version bump.
- `tests/test_spec_gate_check.py` (1846 lines) is the checker's contract corpus; new
  checks follow its fixture style. pytest may need installing on this machine
  (`python3 -m pytest` currently absent) — an environment step, not a design question.
- The `legacy-artifact` waiver convention is reused as-is for both new spec-side checks.

## Out of scope

- Porting daan's `musician-events` artifacts to the new grammar (that happens when that
  feature resumes at T13; its plan will state the legacy waiver or be re-shaped).
- Any change to netdust-wp / netdust-statamic stack skills.
- Retiring per-task RED for clusters that carry NO behaviour block — the old contract
  remains valid; the new grammar is opt-in per cluster.
- run-cost.py / run-score.py changes (verify-budget's telemetry line lands in evidence
  text; scoring integration is a later spec if wanted).
