# testing-workflow — lessons learned

Calibration notes from real harness runs. Each entry: short trigger → observation → recommendation → severity.

---

### 2026-05-28 — Drizzle `migrate()` is journal-idempotent; don't call it twice in a test

- **Source:** Folio Phase 3 Sub-phase A (Task A-3), surfaced by `/evaluate` retro at `docs/superpowers/retros/2026-05-28-phase-3-sub-phase-A-retro.md`.
- **Observation:** A migration test was written assuming `migrate(db, { migrationsFolder })` could be called once to apply all prior migrations, then again to apply a newly-added migration against seeded data. **Drizzle's migrator is idempotent at the journal level** — once a migration's tag is in `__drizzle_migrations`, the second `migrate()` call is a no-op. The seeded rows are never touched, the test fails, and the failure mode is hard to debug because the migration *file* exists and the migrator *runs* — it just runs zero new migrations.
- **Recommendation for tests that need to apply a single migration's UPDATE against pre-seeded rows:**

  ```ts
  import { readFileSync } from 'node:fs';
  import { resolve } from 'node:path';

  // Step 1: run all prior migrations to a clean DB.
  migrate(db, { migrationsFolder: MIGRATIONS_FOLDER });

  // Step 2: seed pre-migration state (rows the new migration will UPDATE).
  sqlite.run(`INSERT INTO ... VALUES (...)`);

  // Step 3: exec the new migration's SQL directly, bypassing the journal.
  const sql = readFileSync(
    resolve(MIGRATIONS_FOLDER, '0012a_flip_runner_builtins_to_enabled.sql'),
    'utf-8'
  );
  sqlite.exec(sql);

  // Step 4: assert the migration's effect on the seeded rows.
  ```

  The trick is that `sqlite.exec()` doesn't consult `__drizzle_migrations`. The migration's SQL runs against whatever state the test set up, regardless of whether the migrator thinks it has already shipped.

- **Severity:** **medium** — wastes 10-20 minutes of debugging the first time a migration test is written this way. Once internalized, costs nothing.
- **Applies to:** any Drizzle-based project (Folio, future Bun/TS projects). NOT WordPress (different test runner + migration story).

---

### 2026-05-29 — re-run timing/ordering/concurrency-sensitive test files Nx before GREEN
- Source: phase-3 sub-phase C.2 (Folio agent runner)
- Observation: a same-millisecond boundary bug (`gt` vs `gte` on a `since: started_at` cancel filter) failed ~1/25 runs. It passed two-stage per-task review AND the controller's single-run verification by scheduling luck, and was caught only by a later diff-wide `/code-review`. The fix-side then adopted a 5× determinism check reactively.
- Recommendation: the task-complete checklist should require re-running the new/changed test file ≥3× (not once) when the task touches time, ordering, concurrency, or any `Date.now()`/timestamp comparison. Single-run GREEN is not evidence of determinism for those surfaces.
- Severity: medium — a non-deterministic suite-breaking bug reached a diff-wide review gate; cheap to catch at the per-task gate (seconds), expensive to chase once it flakes in CI.
- **PROMOTED 2026-06-04:** this recommendation is now an enforced line in the SKILL.md *Task sign-off checklist* ("If this task touches time, ordering, concurrency… run the test file ≥3×").

---

### 2026-06-02 — the test-count-delta line (`N -> M`) belongs in every code commit's body
- Source: operator-agent phase-op-2 (Folio token-scoped config write surface)
- Observation: across 13 implementer commits, ZERO carried the `Test count: <before> -> <after>` convention. Discipline actually held (9/9 code commits shipped a paired `.test.ts`, the CRITICAL auth fix was TDD'd RED→GREEN), but `/evaluate` Step 2.4 reads the count-delta line to verify test GROWTH from git alone — its absence forced the retro to infer coverage from test-file pairing instead. The signal the retrospective depends on was missing even though the underlying discipline was sound.
- Recommendation: the implementer-prompt / task-complete checklist should require the `Test count: <before> -> <after> <suite> (+N)` line in the commit body for any code-touching commit. Cheap, mechanical, and it is the machine-readable handle `/evaluate` consumes. Pairing a test FILE is necessary but not sufficient — the count delta is the auditable number.
- Severity: low — no defect shipped; this is observability debt that degrades the retro's ability to verify discipline from git artifacts.
- **REFINED 2026-06-04:** the count-delta line stays (observability), but SKILL.md now states explicitly that **count growth is NOT a quality signal** — a Tier-B task may legitimately add 0 tests, and one sharp RED-first denial test outranks four happy-path mirrors. `/evaluate` should flag HIGH-risk (Tier-A) tasks that shipped without a denial-path test, not low count per se.

---

### 2026-06-04 — per-task unit tests are a CONTRACT gate, not an integration gate — risk-tier the demand
- **Source:** whole-project diagnosis of how this skill behaved across ~9 substantive Folio sessions (raw transcripts + 12 sub-phase retros + the live test suite). Stefan's report: the skill "adds unit tests after each task, slowing things down, but not always adding better quality." Two independent evidence sweeps agreed; baseline pressure-tests reproduced the failure modes verbatim.
- **Observation:** the unconditional "a task without unit tests is not done" gate fired identically for a one-line `clsx` wrapper and a multi-tenancy auth guard, producing two failure modes:
  1. **Manufactured ceremony** — `cn.test.ts` re-asserts tailwind-merge's own behavior; `pill.test.tsx` asserts Tailwind classnames. The skill's own "What NOT to unit test: third-party library behavior" forbade these, but the mandate overrode the advice (the two halves were structurally unsatisfiable together — a baseline agent confirmed "the checklist gate wins… resolves the deadlock in favor of writing a test its own line says is worthless").
  2. **False confidence** — every CRITICAL/HIGH defect in the corpus PASSED a green per-task unit test and was caught one gate later (holistic review, `/shakeout`, `/code-review`, invariant-auditor): the `requireResource` middleware unit-tested 11/11 green but never mounted → cross-tenant 200; wire-mocked UI green against a leaking server; the `gt`/`gte` race that passed by scheduling luck; the empty-prompt throw that became an instance-wide reactor DoS. The per-task unit test is structurally blind to anything that only manifests across a seam, against the un-mocked dependency, under concurrency, under adversarial input, or for an actor the happy path didn't seed. Per-task tests caught real bugs almost exclusively on **migrations and pure functions**.
- **Recommendation (SHIPPED in this edit):** make the demand **risk-tiered** — Tier A (logic / transforms / state machines / security-auth-scope predicates / untrusted parsing / migrations) requires a behavioral RED-first test incl. the **denial path**; Tier B (glue / wiring / pass-through wrappers / presentational UI / config-enum-seed) requires **no bespoke test** (suite-green + seam reach, record `no unit test: Tier B, <reason>`). Add a **seam test at the wiring task** (≥1 un-mocked-chain assertion + ≥1 negative case) — the single highest-leverage change, since every CRITICAL was a seam/wiring/wire-mock/masking-payload bug. Add a **value-gate question** ("if I delete this test, what real bug ships? name it") and a mandatory **named-deferral line** routing the uncatchable classes to the gate that owns them. Reconcile "What NOT to test" into a **hard exclusion**. Close the **RED-first `OR covers the new behavior` escape** for Tier A.
- **Erosion guard:** security/auth/scope guards, untrusted-input parsers, and state machines are ALWAYS Tier A regardless of line count — a one-line guard is not glue. An adversarial pressure-test (late-night, last task, "this looks exactly like wiring") could find NO wording that lets a security guard into Tier B; it could only find a reader-ordering by which a skimmer might miss the rule — closed by inline cross-links from the Tier-B litmus + pass-through bullet back to the erosion guard.
- **Severity:** **high** — this is the skill's central calibration. The old gate spent effort uniformly while every severe defect escaped to a later, more expensive gate. Verified RED→GREEN→REFACTOR with subagent pressure scenarios before shipping.

---

### 2026-07-31 — a contact page bought an auth subsystem's verification (`contact-page-8k`)

- **Source:** Stefan's report the following morning: *"a session with netdust-agent yesterday went totally wrong. what is nothing more as a simple contact page took hours and hours of coding and testing. 8000 lines of tests."* This is the same complaint as the 2026-06-04 entry below, one level up: that one was per-unit ceremony, this one is per-FEATURE ceremony, and the earlier fix could not reach it.
- **Observation — four gates, each doing exactly what it was told:**
  1. **The class dial scales planning, not verification.** `harnessed-development` says it "scales the ceremony to the work", but its only lever is which spine runs. A contact page is a legitimate Class A (new feature, several tasks), so it drew the entire Stage-3 ladder — integration gate, seven-mode `test-effectiveness` audit, full `feature-acceptance` matrix drive, shake-out panel — at the same weight a billing engine draws.
  2. **By the harness's own detectors, a contact form is indistinguishable from an auth subsystem.** `gate-check.py`'s `FILES_SECURITY` matches `nonce|sanitiz|capabilit|permission|role|upload|pars|…`; a contact form hits five of them. Every task classified Tier A, D1 then made each `split` (two dispatches per task), and `security-boundary-mode` WARNed on any attempt to say otherwise. The machinery could push a classification UP and had no path DOWN.
  3. **The erosion guard had no framework-primitive exit.** "Security/auth/scope guards are ALWAYS Tier A no matter how few lines" is right about guards that decide something and wrong about `if (!wp_verify_nonce(...)) wp_die()`. That primitive is upstream-hardened and upstream-tested; the project's risk is the call being *absent*, which a RED-first denial test is the one thing that cannot check.
  4. **Nothing counted the cost.** `run-cost.py` is report-only by design; "count is not quality" was prose. Every gate asked "is this verified?" and none asked "is this verification worth what it cost?" — so 8000 lines accumulated with every individual gate satisfied, and the human was the only thing in the loop able to notice, hours later.
- **The distinction that fixes it — presence vs decision.** A guard carries two obligations the old rule collapsed into one. **Presence** (is it there, on every path, reachable?) is best proven by a machine gate over the whole diff, is never waived at any stakes level, and costs nothing at the point of use. **Decision** (does this predicate encode a rule THIS PROJECT chose — a role, a window, an ownership test, a threshold?) is Tier A at every stakes level. The litmus: *name the rule this predicate encodes; if the only answer is "the framework's rule", it is presence.*
- **Recommendation (SHIPPED in this edit), four levers:**
  1. **The stakes dial** — `Stakes: high | standard | low` stated at intake, recorded by `planning` gate 1i, machine-checked by `gate-check.py`, READ by every verification gate and re-decided by none. Independent of the class dial: class asks how big, stakes asks what breaks. `Stakes: low` on a spec that flagged a security surface is a FAIL — the spec's own checkboxes outrank plan prose.
  2. **The evidence ladder** — machine gate > framework guarantee > existing test > new test, recorded per task as `Proven by:`, with rungs 1–3 required to NAME their evidence. Evidence that is cheap, broad and permanent outranks evidence that is expensive, narrow and one-off.
  3. **Presence vs decision** on the erosion guard, above — and `security-boundary-mode` re-keyed from the TIER to the ABSENCE OF EVIDENCE, so Tier B on a boundary surface passes when it names a presence proof and warns when it names nothing.
  4. **`bin/verify-budget.py`** — added-test-lines vs added-implementation-lines against a stakes-scaled ceiling, run at every cluster gate and over the whole branch. A HALT is a stop-and-report to the human naming three causes, with "the stakes line was too low, raise it" listed FIRST and deleting tests explicitly forbidden.
- **What deliberately did NOT change:** the erosion guard still makes every project-authored decision Tier A regardless of line count; presence is never waived at any stakes level; D1 still forces `split` on Tier-A security-boundary work; the no-self-downgrade invariant now covers the stakes field too. The relaxation is strictly on re-proving what the framework and the project's own machine gates already prove.
- **Severity:** **high** — the harness's second central calibration on this axis. The first (2026-06-04) stopped it manufacturing tests on units that had no logic; this one stops it manufacturing tests on properties something cheaper already proves, and gives it the first sense it has ever had of what its own verification costs.
- **Open follow-up:** the numbers above are Stefan's from the session ("hours and hours", "8000 lines") — the run's `run-cost.py` transcript would sharpen the per-dispatch half of the story if it is still on disk. The tripwire's ceilings (4.0 / 2.5 / 1.0) are first estimates chosen to catch runaways rather than tune taste; they should be revisited once a few real runs have passed under them.
