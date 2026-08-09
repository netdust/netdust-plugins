# Tasks — Deliverable-first harness

**Spec:** `specs/deliverable-first/spec.md` · **Plan:** `specs/deliverable-first/plan.md`
**Loop budget: ~14 iterations** (9 tasks + 3 review clusters + slack for one fix round on Cluster B).

**Standing line for every checker task (T01–T04):**
> New checks follow the house shape — a `check_*(text, f: Findings)` function, fixtures in
> `tests/test_spec_gate_check.py`'s existing style, fenced-block stripping inherited from the
> caller. RED-first against the real script, never against a stub. Existing cases stay
> untouched except the one named re-contract (`test_verify_budget.py`, per SC-6).

**Standing line for every skill-text task (T07–T09):**
> Text cites the mechanical check by its exact name (`check_deliverable_first`,
> `check_fr_sources`, the behaviour-block grammar, the ledger event); no skill text may
> promise an enforcement the machine doesn't perform — where enforcement is sequencer-level
> (FR-9, FR-13), the text says so, following the 1a honesty convention.

---

## Phase 1 — all three clusters

### Cluster A — the checker (4 tasks · effective stakes: standard · provisional tier: STANDARD)

Behaviour: `gate-check.py` refuses a musician-events-shaped plan and never again interrupts a run over a test ratio.
Observable: one command per claim — the fixture replay exits 1 naming `deliverable-first` + `fr-source`; this spec's own artifacts exit 0; an above-ceiling verify-budget input exits 0 printing its report line.
RED until: `tests/test_spec_gate_check.py::test_deliverable_first_missing_section_fails`

- [x] T01 [Tier A] Implement `check_deliverable_first()` per the 1j draft with the decided parameters (named task in first 3, FAIL; test-only files FAIL; N/A only for non-runnable deliverables; `legacy-artifact` → WARN; >2 preceding tasks → WARN). Step 0: bring up pytest (`pip3 install --user pytest` or distro package) and record the working invocation.  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T01 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) plan without `## First working version` + spec flagging a user-facing surface → FAIL; (b) section naming a task absent from tasks.md → FAIL; (c) named task in position 4 → FAIL; (d) named task whose `(files:)` lists only `tests/` paths → FAIL; (e) valid section, task in first 3, non-test file → pass; (f) `N/A — docs-only` justification on a spec with no user-facing surface → pass; (g) `legacy-artifact` waiver → WARN naming it; (h) 3 tasks preceding the named one → WARN.
  Notes: the two worked examples in the 1j draft (josworld-core T05-fifth; yootheme-baseline test-only T03) become fixture cases for (c) and (d).
  (FR-3, FR-4, FR-5, AC-3)

- [x] T02 [Tier A] Implement `check_fr_sources()` — every FR line in spec.md must carry a `Source:` continuation; `invented` sources must carry an approval.  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T02 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) an FR with no `Source:` line → FAIL naming the FR; (b) `Source:` quoting the request → pass; (c) `Source: invented — approved <date>` → pass; (d) `Source: invented` with no approval → FAIL; (e) spec-level `legacy-artifact` waiver → WARN; (f) a spec with no `## Functional requirements` section → existing missing-section behaviour unchanged.
  (FR-1, FR-2, AC-3)

- [x] T03 [Tier A] Implement the behaviour-block grammar in the checker: a `### Cluster` block may carry `Behaviour:` + `Observable:` + `RED until: <path::method>`; the task-contract form `covered by cluster behaviour` is accepted only inside a cluster carrying the full block whose `RED until:` test file exists or is created by a task in that cluster — its path appears in a member task's files segment.  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the T03 case block in `test_spec_gate_check.py`.
  Unit test: RED-first. (a) `covered by cluster behaviour` inside a cluster with the full block whose test file is created by a member task → pass; (b) same form in a cluster with NO behaviour block → FAIL naming task and cluster; (c) block with `Behaviour:` but no `RED until:` while a member uses the waiver → FAIL; (d) `RED until:` naming a test file neither existing nor in any member's `(files:)` → FAIL; (e) a cluster carrying the block where members keep ordinary unit-test lines → pass (opt-in, both forms legal); (f) artifacts with no behaviour blocks anywhere → zero new findings (AC-3 lock).
  Notes: observable ADMISSIBILITY (no config/array shapes) is deliberately NOT machine-judged — that is FR-9's sequencer rule, landed in T06. The machine checks presence + the named test.
  (FR-6, FR-7, FR-9, SC-2)

- [x] T04 [Tier A] Demote `verify-budget.py` to telemetry: exit 0 on every input, print the one-line ratio report (`ratio=<r> ceiling=<c> stakes=<s>` shape), delete the HALT path; re-contract `test_verify_budget.py` accordingly — the one permitted existing-test edit (SC-6).  (files: plugins/netdust-agent/bin/verify-budget.py, plugins/netdust-agent/tests/test_verify_budget.py)
  Test-author: solo — standard stakes, reporting-only change, not a security-boundary category.
  Proven by: new test — the re-contracted exit-code cases in `test_verify_budget.py`.
  Unit test: RED-first. (a) above-ceiling ratio → exit 0 AND report line printed; (b) under-ceiling → exit 0, same report shape; (c) `--json` output keeps its fields so any consumer parsing it is unbroken; (d) the string `HALT` absent from the script's stdout in both cases.
  (FR-10, AC-6, SC-3)

**Integration gate (Cluster A):** three commands, run together after T01–T04: (1) new
`gate-check.py` against a fixture copy of daan `specs/musician-events` → exit 1, findings
include `deliverable-first` and `fr-source` (AC-1, SC-1); (2) against
`specs/deliverable-first` itself → exit 0 (AC-2 — this spec self-hosts its own grammar);
(3) full plugin pytest suite → 0 failures with ≥ 14 new cases counted (SC-2), and zero new
findings on any existing-corpus fixture (AC-3).

── REVIEW GATE ── (tier: STANDARD — checker logic, no 1a surface. Escalates one-way to FULL if any finding touches the waiver/bypass paths.)

---

### Cluster A-fix — review findings (3 tasks · effective stakes: standard · provisional tier: STANDARD)

*Triage record (2026-08-09, generalist + simplicity reviews, both independent): 0 Critical.
I-1/I-2/I-3 → fix now (below). Parked: S-1, S-3, S-5 + 9 simplicity items — see
`specs/deliverable-first/review-A.md`. Escalation: I-1 touched the waiver path, so Cluster A
is promoted one-way to FULL — `security-sentinel` runs on the post-fix cluster diff.*

- [ ] T10 [Tier A] fix I-1: behaviour-block validity is vacuously satisfiable — `RED until:` accepts a directory (`.exists()`) and a substring files-segment match — closes when the two named dangling tests go green  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the two dangling cases in case block 25.
  Unit test: RED-first. (a) `RED until: tests/::x` where `tests/` is a directory → dangling FAIL; (b) `RED until: src::x` beside a member whose files list `src/notify.php` → dangling FAIL (exact comma-split path match required). Rider S-2: backticked path half no longer false-dangles. Rider S-5b: one comment in the checker noting the deliberate FAIL+WARN dual-fire (test 23h).
  (FR-6, FR-7)

- [ ] T11 [Tier A] fix I-2: `check_fr_sources` block boundary — a colon-less FR def escapes the check and donates its `Source:` to the previous FR — closes when the leak test goes green  (files: plugins/netdust-agent/bin/gate-check.py, plugins/netdust-agent/tests/test_spec_gate_check.py)
  Test-author: solo — standard stakes, checker validation logic, not a security-boundary category.
  Proven by: new test — the leak case in case block 24.
  Unit test: RED-first. A spec whose colon-less FR def carries the only `Source:` must FAIL naming the sourced-in-appearance FR as bare (block flushes at any column-0 bullet that is not an FR def). Rider S-4: a `Source:` must contain at least one word character.
  (FR-1, FR-2)

- [ ] T12 [Tier B] fix I-3 (code half): retire the HALT consumer branch in `hooks/loop-gate.py` and re-contract its stub-pinned test — the branch is unreachable with the shipped verify-budget (dead code; fails toward the new behaviour), so this is a non-behavioural removal closing on the suite green  (files: plugins/netdust-agent/hooks/loop-gate.py, plugins/netdust-agent/tests/test_loop_gate.py)
  Test-author: solo — Tier B.
  Proven by: existing test — the loop-gate module in `bash plugins/netdust-agent/tests/run.sh`, green over the removal; the stub re-contract is declared (the stub printed a contract no real input can produce — green-but-blind).
  Unit test: no unit test: Tier B, dead-branch removal; the re-contracted loop-gate test asserts the gate no longer reads budget output at all.
  (FR-10, FR-11)

**Integration gate (Cluster A-fix):** the two probe inputs from the review (dir-only and
substring `RED until:`, colon-less FR def) now FAIL through the live CLI; full suite green;
self-host and daan replays unchanged from the Cluster A gate.

── REVIEW GATE ── (tier: FULL — the escalation landed here: `security-sentinel` on the whole Cluster A + A-fix diff; verify-only for the three named closing checks, no new general hunting round.)

---

### Cluster B — the enforcement boundary (1 task · effective stakes: high · provisional tier: FULL)

- [ ] T05 [Tier A] Teach `hooks/subagent-stop.py` the behaviour-cluster transition tolerance  (files: plugins/netdust-agent/hooks/subagent-stop.py, plugins/netdust-agent/tests/test_subagent_stop_evidence.py)
  Contract: when the run ledger (`tasks/.harness-loop.json`) carries an open
  `cluster-open` event naming a RED test, an implementer close whose ONLY suite failure
  is exactly that named test is admitted (and the admission recorded); any other failure
  blocks as today; a `cluster-close` event while the named test still fails blocks with a
  reason naming the test. No `cluster-open` in the ledger → behaviour bit-for-bit
  unchanged.
  Test-author: split — Tier A guard at effective-high stakes (D1 hard rule: the hook is the harness's own enforcement boundary; a silent bug here un-gates every project).
  Proven by: new test — the transition cases in `test_subagent_stop_evidence.py`.
  Unit test: RED-first, denial paths mandatory. (a) ledger names `FooTest::test_bar`, scraped suite failure is exactly that → close admitted; (b) failure is a DIFFERENT test → blocked, reason names the unexpected failure; (c) named test red PLUS another red → blocked (tolerance is exact, not prefix); (d) `cluster-close` while named test red → blocked; (e) no `cluster-open` event → all existing fixture cases pass unmodified (AC-4 lock); (f) scraped-failure-wins rule intact: a claimed exit=0 with a scraped failure of the named test is still treated as that failure (admitted under (a)), and with any other scraped failure is blocked.
  (FR-8, AC-4, AC-5, SC-4)

**Integration gate (Cluster B):** run the FULL plugin pytest suite (not just the hook file)
— the hook change must leave every non-behaviour-block fixture green (SC-6: no existing
assertion weakened; the test diff outside `test_verify_budget.py` is additive-only).

── REVIEW GATE ── (tier: FULL — the harness's own guard; reviews alone.)

---

### Cluster C — the skill texts (4 tasks · effective stakes: standard · provisional tier: LIGHT)

- [ ] T06 [Tier B] Planning + spec-authoring texts — 1j, Source:, behaviour-block shaping  (files: plugins/netdust-agent/skills/planning/SKILL.md, plugins/netdust-agent/skills/spec-authoring/SKILL.md)
  Contract: promote gate 1j into `planning` SKILL.md Stage 1 (section requirement + the
  decided parameters, citing `check_deliverable_first`); add the `Source:` rule to
  `spec-authoring`'s `<artifact_contract>` (invented-unapproved = a
  `[NEEDS CLARIFICATION]`-grade HALT) and to planning's Stage 0.5 summary; add
  behaviour-block shaping to gate 1d, including the FR-9 observable-admissibility rule
  (outside-observable only; config/array shapes inadmissible — sequencer-enforced,
  stated honestly).
  Test-author: solo — Tier B.
  Proven by: machine gate — Cluster A's checker tests enforce the behaviour; this task's
  text must cite those checks by name (standing line), verified at the cluster gate grep.
  Unit test: no unit test: Tier B, skill prose whose mechanical halves landed in T01–T03.
  (FR-1, FR-3, FR-9)

- [ ] T07 [Tier B] Building text — Artifact-load rule, ledger events, verify-budget telemetry  (files: plugins/netdust-agent/skills/building/SKILL.md, plugins/netdust-agent/commands/integration.md, plugins/netdust-agent/commands/shakeout.md, plugins/netdust-agent/bin/README.md)
  Contract: add the `Artifact-load:` requirement to the review-gate step — before
  reviewer dispatch on a cluster whose diff touches a user-facing surface, the controller
  loads the artifact once and records `Artifact-load: <cmd/URL> → <observed>` in the
  cluster evidence; reviewer dispatch refuses to proceed without it (sequencer-enforced,
  red-flag row added). Define the `cluster-open` / `cluster-close` ledger events the T05
  hook reads, and who writes them (the controller, at the behaviour cluster's
  boundaries). Replace verify-budget's HALT step with the telemetry line (record and
  continue; the human is never asked). I-3 extension: retire the HALT contract wherever
  the plugin still states it outside skills/ — `commands/integration.md`,
  `commands/shakeout.md`, `bin/README.md` (the doc half; the loop-gate code half is T12).
  Test-author: solo — Tier B.
  Proven by: machine gate — T04's exit-0 contract and T05's ledger tests; the text cites
  both; SC-3's grep at the cluster gate proves no HALT semantics remain.
  Unit test: no unit test: Tier B, skill prose over mechanics landed in T04/T05.
  (FR-11, FR-12, FR-13, SC-3)

- [ ] T08 [Tier B] Intake text — the decision-density clause in `harnessed-development`  (files: plugins/netdust-agent/skills/harnessed-development/SKILL.md)
  Contract: class is priced by open decisions, not files touched; declarative multi-file
  configuration with no design questions routes Class E; add the intake question "would a
  competent human do this inside half an hour?" and a red-flag row ("multi-file but
  declarative → I'll run it as Class A" → reality: route E).
  Test-author: solo — Tier B.
  Proven by: framework — intake is prose routing by design (no machine gate exists at
  intake); the red-flag table is the harness's own convention for exactly this.
  Unit test: no unit test: Tier B, intake prose.
  (FR-14, FR-15)

- [ ] T09 [Tier B] Close the record — 1j promotion, calibration entry, version bump  (files: plugins/netdust-agent/skills/planning/references/gate-1j-deliverable-first.md, plugins/netdust-agent/skills/_shared/calibrations.md, plugins/netdust-agent/.claude-plugin/plugin.json)
  Contract: update the 1j reference file from PROPOSAL to IMPLEMENTED (decisions + date +
  check name); add the `musician-events-ceremony` calibration to
  `skills/_shared/calibrations.md` (third `deliverable-last` instance: 4 asks → 2
  cheapest built, FR-7 invented-then-served, artifact never loaded, tripwire waived 3/3);
  verify the plan's failure-chain table is closed 6/6 (SC-5) and the test diff satisfies
  SC-6; bump the plugin version so the cache picks the changes up.
  Test-author: solo — Tier B.
  Proven by: machine gate — Clusters A+B green suites are what "implemented" means; this
  task records it where future sessions read it.
  Unit test: no unit test: Tier B, documentation and version metadata.
  (FR-5, SC-5, SC-6)

**Integration gate (Cluster C):** coherence grep across `plugins/netdust-agent/**`
(calibration history and this spec's own record excepted): 0 verify-budget HALT semantics
remain anywhere in the plugin (SC-3, widened per review finding I-3); every new skill
claim cites its mechanical check by exact name (standing line); `gate-check.py` re-run on
`specs/deliverable-first` still exits 0 after all text edits (self-hosting survives).

── REVIEW GATE ── (tier: LIGHT — skill-body/doc only. Escalates one-way if any finding shows a text promising enforcement the machine doesn't perform.)
