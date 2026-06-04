---
name: test-effectiveness
description: "Use to AUDIT whether a test suite would actually catch bugs (not just whether tests exist + pass), and to AUTHOR tests that close the gap — at phase-complete, at shake-out, or whenever a green suite shipped a bug. Risk-aware sibling to testing-workflow: testing-workflow gates 'does this task need a test, at what tier?' (write-time, per-task); this gates 'would my suite go RED if the dangerous path broke?' (audit-time, per-phase). Names the seven failure modes that ship bugs past a green suite — stale fixture, test-world≠real-world, wire-mock leak, unmounted guard, happy-path-only/missing-denial, no-coverage, concurrency/timing — each with an audit move and a per-stack author pattern. Covers TypeScript (Vitest/Playwright) and PHP (PHPUnit/Codeception). Opt-in via the project's CLAUDE.md — not auto-invoked."
---

<objective>
A test that exists and passes is not the same as a test that would catch the bug. This skill closes that gap. It answers a different question than `testing-workflow`:

- `testing-workflow` (write-time, per-task): **"Does this task need a test, and at what tier?"** It gates presence + tier.
- `test-effectiveness` (audit-time, per-phase): **"Would my suite go RED if the dangerous path broke?"** It gates power.

A suite can be 100% green, 2000 tests, full tier discipline — and still ship a cross-tenant leak, a stale-fixture UI break, or a race. Every one of those passed a green per-task test and was caught one gate later (or by a customer). The reason is almost never "a test was missing on a clear acceptance line." It is that **the test exercised the safe path while the dangerous path had no assertion** — the fixture encoded the old contract, the guard's denial branch was never called, the wire was mocked so the leak couldn't show, the unit was green but never mounted, the race never raced.

This skill names the **seven failure modes** that let a bug pass a green suite, gives each a concrete **audit move** (how to detect it in an existing suite) and a per-stack **author pattern** (the test that would have caught it). It is used as an audit lens at phase-close / shake-out, and as an authoring reference when a green suite has shipped a bug.

It is **stack-agnostic**: the seven modes are universal; the patterns files give the concrete TypeScript and PHP forms.
</objective>

<core_idea>
**A bug that ships past a green suite is almost always a path the suite never exercised — not an assertion that was too weak.**

This matters for tool choice. "Weak assertion on tested code" is what mutation testing catches (break the code, see if a test goes red). But the escaped-bug history of a real project is dominated by the *other* failure: the dangerous path — the denial branch, the second tenant, the stale-fixture consumer, the refetch toggle, the concurrent re-entry — was **never run by any test**, so there was no assertion to be weak. Mutation testing reports "0 surviving mutants" on a line that has no test at all only if some test happens to execute it; on an unmounted guard it reports nothing useful.

So this skill's spine is the **seven coverage-of-the-dangerous-path failure modes**, not mutation testing. Mutation testing is one *optional* tool (see `<optional_tools>`), aimed only at high-risk surfaces where the path IS tested and you want to know if the assertion bites. Reach for the spine first; reach for mutation only when the spine says "this path is covered — is the assertion real?"
</core_idea>

<when_to_use>

Invoke this skill in three situations:

| Situation | Trigger |
|---|---|
| **A — Phase-complete / shake-out audit** | All tasks in a phase are green and you are about to sign off or merge. Run the seven-mode audit over the phase diff BEFORE `/shakeout` dispatches reviewers — it is the cheapest place to find a green-but-blind test. |
| **B — A green suite shipped a bug** | Any time a defect reached review, QA, or a user while the unit suite was green. Classify the escape into one of the seven modes, then add the test that mode prescribes — and sweep for siblings of the same mode. |
| **C — Authoring tests on a high-risk surface** | While writing tests for auth/scope predicates, multi-tenancy reads, untrusted parsing, migrations, or any wiring task — use the per-stack author patterns so the dangerous path is asserted from the start, not retrofitted after the escape. |

**Do not invoke for:** the per-task "does this need a test, at what tier" decision — that is `testing-workflow`. This skill assumes tests exist and asks whether they bite. Nor for pure test-tooling setup (a missing runner is `testing-workflow`'s "No Test Framework? Set It Up").

If you are unsure whether a green suite is trustworthy on a security-rich or cross-cutting phase, default to running the Situation-A audit — it is ~20 minutes and it is the gate that has historically caught what per-task tests missed.

</when_to_use>

<the_seven_failure_modes>

Each mode is: **the escape** (how a bug passes green) → **the audit move** (how to detect it in an existing suite) → **the author fix** (the test that catches it). The deep catalog with the real calibration bug behind each lives in `references/failure-modes.md`; the per-stack code is in `patterns-typescript.md` / `patterns-php.md`. This table is the always-loaded summary.

| # | Mode | The escape (green-but-blind) | Audit move | Author fix |
|---|------|------------------------------|------------|------------|
| **1** | **Stale fixture** | The fixture encodes the OLD contract. Server changed a canonical shape; the test fixture still uses the old shape, so the test round-trips green while every real consumer breaks on the new shape. | After any change to a server-emitted canonical form (an id-vs-slug, an enum value, a field name), grep the whole repo for the OLD form. Every match is a consumer; every test fixture using the old form is now lying. | Update fixtures to the NEW shape in the SAME commit as the contract change, so CI exercises post-change reality. Add one consumer test that asserts the new shape renders/resolves. |
| **2** | **Test-world ≠ real-world** | The test runs against a fresh/clean world (fresh-migrated DB, seeded-from-scratch state) that does not match the long-lived real world (a dev/prod DB with history, a pre-existing row). Green in the harness, 500 in reality. | Ask: "what does the test harness build from scratch that the real environment accumulates?" Migrations applied fresh every run, seed data, a clean cache. If the harness can't drift, it can't catch drift. | The fix is usually structural, not a test: apply migrations at boot, not just in the harness. Where a test IS the right place, seed the test from a realistic (post-migration, has-history) baseline, not an empty one. |
| **3** | **Wire-mock leak** | The test stubs the boundary it should cross — mocks the server response, so the client test proves "given a correct server, the client wires up," never that the server is correct or the wire doesn't leak. Both sides green; the un-mocked wire leaks. | Grep the test for where it mocks the thing it is supposed to verify. A client test that hard-codes the server's filtered response is testing the mock. A list-invalidation test that mocks one list shape doesn't cover the other list shapes the real wire feeds. | Add ≥1 assertion that crosses the REAL boundary un-mocked: a real request through the mounted app, or a shake-out `curl`/Playwright step against the live wire. Test against the broad invalidation key, not a single mocked param shape. |
| **4** | **Unmounted / unwired guard** | The unit works in isolation but is never installed in the real chain — the middleware is unit-green but not mounted on the route, the guard exists on one path (MCP) but not its twin (HTTP), the seam test stops at "resolution returns the object" and never drives the full chain. | For every guard/middleware, find the test that drives it THROUGH the mounted app, not the one that calls it directly. If the only test calls the guard function in isolation, a mis-mount is invisible. For a capability/wiring task, find the test that ACTS in the target, not the one that asserts the seam. | At the wiring task: ≥1 assertion through the un-mocked real chain (real request → mounted route → guard fires) AND ≥1 end-to-end "act in the target" for capability features. Audit every sibling path (HTTP twin of an MCP guard, create vs update) for the same mount. |
| **5** | **Happy-path-only / missing denial** | The guard's allow branch is tested; its DENY branch never runs. The test seeds the privileged actor, so the 403 path is dead code in the suite. Cross-tenant, scope-escalation, and widening bugs hide here. | For every `requireScope` / `requireResource` / capability check / `if (role === …) return 403`, find the test that asserts the DENIAL (a denied actor, a second tenant, a `?project=blocked`). If only the 200 path is asserted, the guard is untested. | Add the RED-first denial test: the denied actor / second tenant / masking-payload alternative gets the 403/empty result. This is the Tier-A negative-path test `testing-workflow` mandates — this skill is where you AUDIT that it actually exists across all sibling guards. |
| **6** | **No coverage at all** | A real behavior has literally no test exercising it — a timing-dependent input path masked by the test helper, a rendered-DOM/CSS contract asserted only at the AST level, a transactional-rollback contract the test never forces to fail. | List the phase's user-facing behaviors and DOM/interaction contracts; map each to a test. The gaps are the bugs. Watch for helpers that mask the bug (`userEvent.type` clears-then-types, hiding an append-vs-replace defect). | Author the missing test at the layer where the behavior lives: an e2e for a keystroke-after-focus race, a rendered-DOM assertion (not AST) for a CSS/interaction contract, a forced-throw test for a rollback contract. |
| **7** | **Concurrency / timing** | A single green run passes by scheduling luck. The race only manifests when callback A is slow and B re-enters, or when a data layer toggles a value on a schedule the test exits before seeing. One run ≠ determinism. | For any `setInterval`/`setTimeout`/poller/queue/`Date.now()`/refetch-toggle, find the test that forces the adverse interleaving — a slow first callback, a high-frequency tick, a refetch cycle. If the test runs once and asserts, it proves nothing about the race. | Re-run the new/changed test ≥3× and require green every run. Force the interleaving (inject a slow dependency, drive the timer) rather than hoping for it. This is `testing-workflow`'s "≥3× determinism" box — audit that it was actually done. |

**The one-line litmus for an audit:** for each guard, fixture, wire, mount, and timer the phase touched — *name the test that would go RED if the dangerous path broke.* If you can't name it, that's the finding.

</the_seven_failure_modes>

<process>

**Situation A — phase-complete / shake-out audit.** Run this over the phase diff after the unit suite is green, before `/shakeout`:

1. **Enumerate the dangerous paths the diff introduced.** From the diff, list every: guard/scope check, canonical-form change, client↔server wire, route mount, timer/poller/refetch, migration, and rendered-DOM/interaction contract. This is the surface; the seven modes are the lenses.
2. **For each, apply the litmus:** name the test that goes RED if that path breaks. Use the audit-move column. Record each path as `covered` (named a real RED-able test), `blind` (no such test — a finding), or `n/a`.
3. **Sweep siblings.** Every `blind` finding on a cross-cutting concern (a guard with twins, a canonical form with many consumers, a predicate at N sites) gets a sibling-site sweep — modes 1, 4, and 5 almost always have ≥1 sibling the primary fix missed. *(Before promoting a `blind` to a real gap, verify it via `_shared/finding-verification.md` — rule 2 (test-only/dead code) and rule 16 (a ratified deferral) refute most false blinds, so you don't manufacture a test for a path that's intentionally untested.)*
4. **Author the missing tests** at the right layer (per the author-fix column + the patterns file), RED-first where the mode is a guard/parse/transform (Tier A per `testing-workflow`).
5. **Report** the audit as a short manifest: per dangerous path, `covered`/`blind`/`fixed`, and the residual risk handed to `/shakeout` + `/code-review`. This manifest is the convergence target for the reviewers — they verify the `blind→fixed` transitions instead of re-discovering them.

**Situation B — a green suite shipped a bug.** Classify → fix → sweep:

1. **Classify** the escape into one of the seven modes (the `references/failure-modes.md` catalog has the decision questions). The mode tells you the author fix AND where to sweep.
2. **Write the RED-first test** that reproduces the escape (you must watch it fail against the shipped code), then fix, then green.
3. **Sweep for siblings of the same mode** — the escape is rarely unique. A stale-fixture break has other consumers; a missing-denial has sibling guards; an unmounted guard has twin paths.
4. **Record a lesson** (project `lessons.md`) naming the mode, so the audit (Situation A) inherits it next phase.

**Situation C — authoring on a high-risk surface.** Before writing the test, open the patterns file for your stack and use the mode-specific pattern (denial-first for guards, un-mocked-wire for client↔server, forced-interleaving for timers). Author the dangerous-path assertion FIRST; the happy path is the easy add.

</process>

<optional_tools>

**Targeted mutation testing — one tool, not the spine.** Mutation testing (break the code, see if a test goes RED; a surviving mutant = a test that doesn't bite) answers mode-adjacent question: "this path IS tested — is the assertion real?" It does NOT find any of modes 1–7's escapes, because those are *untested* paths, not weak assertions. Use it ONLY when:

- the spine audit says a high-risk surface (auth predicate, scope-narrowing, parser, migration) IS covered, and
- you want to confirm the covering test would actually fail if the guard inverted.

Run it **targeted, not whole-suite** — point it at the handful of high-risk files, never the whole codebase (whole-suite mutation is slow and its signal drowns in low-value mutants on glue). Per stack: Stryker (`@stryker-mutator/core`) for TypeScript; Infection for PHP. If the project has no mutation tooling and no surviving-mutant bug in its history, **do not add it** — the spine is where the bugs are. (Folio: 0 mutation infra, 0 mutant-survival bugs in 19 escaped-green-test defects — all seven-mode escapes. Adding mutation there would be tooling fitted to theory, not evidence.)

</optional_tools>

<red_flags>

These thoughts mean a green suite is lying to you. Stop.

| Thought | Reality |
|---|---|
| "All 2000 tests pass, the phase is verified." | Green proves the tested paths work. It says nothing about the dangerous paths no test exercises. Run the litmus: name the test that goes RED if the guard's deny branch breaks. |
| "There's a test for this route, it's covered." | Covered ≠ the denial is asserted. A route test that only seeds the privileged actor never runs the 403 path (mode 5). Find the denied-actor test or it's blind. |
| "The client test passes, the integration works." | If the test mocks the server response, it proves the client wires up given a correct server — not that the server is correct or the wire doesn't leak (mode 3). Cross the un-mocked wire once. |
| "The unit test for the middleware is green." | A green unit test on an unmounted middleware is the single most dangerous false signal — the guard works and never runs (mode 4). Drive it through the mounted app. |
| "The fixture round-trips fine." | After a canonical-form change, a green round-trip on a STALE fixture means CI is testing the old contract while every consumer broke on the new one (mode 1). Update the fixture in the same commit. |
| "It passed, so the race is fine." | One green run of a concurrency path passes by scheduling luck (mode 7). Force the interleaving and run ≥3×, or you've proven nothing. |
| "Let me add mutation testing to catch these." | Mutation testing catches weak assertions on TESTED code. Your escapes are UNTESTED dangerous paths — mutation finds ~none of them. Fix coverage of the dangerous path first; mutation is a later, narrower tool. |
| "I'll write the effectiveness audit after shake-out finds things." | That inverts the gate. The audit is cheaper than the shake-out fix loop and is the convergence target that makes shake-out a verification pass, not a discovery pass. Audit BEFORE dispatch. |

</red_flags>

<success_criteria>

This skill has succeeded when:

1. For each dangerous path the phase touched (guard, fixture, wire, mount, timer, migration, DOM contract), a specific test was NAMED that would go RED if that path broke — or the gap was recorded as a finding and fixed.
2. Every guard added in the phase has an asserted DENIAL path (mode 5), and every guard with a twin/sibling was swept for the same mount + denial (modes 4, 5).
3. Every canonical-form change updated its fixtures in the same commit and added a consumer test (mode 1).
4. Every client↔server wire the phase introduced has ≥1 un-mocked crossing (mode 3); every wiring task has ≥1 act-in-the-target assertion (mode 4).
5. Every timer/race/refetch path the phase introduced was forced and run ≥3× (mode 7).
6. The audit produced a short manifest (`covered`/`blind`/`fixed` per path) that `/shakeout` + `/code-review` verify against, instead of re-discovering the same gaps.

If a later `/shakeout` or `/code-review` finds a green-but-blind test the audit should have caught, the audit was too shallow — extend the seven-mode sweep, and add the missed mode's audit move to `references/failure-modes.md`. If the audit is never run and shake-out keeps finding green-but-shipped bugs, the gate isn't wired — cite it in the project CLAUDE.md and `harnessed-development` Stage 3.

</success_criteria>

<integration>

| Skill / gate | Relationship |
|---|---|
| `netdust-core:testing-workflow` | **SIBLING — the seam is altitude.** testing-workflow is write-time + per-task: "does this task need a test, at what tier (A/B), is the RED-first/denial path written?" This skill is audit-time + per-phase: "across the whole phase diff, would the suite go RED if any dangerous path broke?" testing-workflow writes the denial test; this skill AUDITS that it exists across every sibling guard and crosses every un-mocked wire. They share the Tier-A negative-path contract; neither replaces the other. |
| `netdust-core:harnessed-development` | **STAGE 3 GATE (new).** harnessed-development fires this skill at phase-complete — after the `testing-workflow` integration gate, before `netdust-core:shake-out` — as the Situation-A audit over the phase diff. Its manifest becomes the convergence target the shake-out reviewers verify against. Also fired ad-hoc in Situation B (a green suite shipped a bug). |
| `netdust-core:shake-out` | **DOWNSTREAM CONSUMER.** Shake-out exercises the built artifact end-to-end; this skill's pre-shake-out audit narrows what shake-out must discover from scratch to what it must verify (`blind→fixed`). A shake-out bug that was a green-but-blind test is a finding this skill's audit should have caught — feed it back as a new audit move. |
| `netdust-core:threat-modeling` | **UPSTREAM.** The threat model's named mitigations ARE the denial-path contracts mode 5 audits — each mitigation should have a test that asserts the attack is refused. This skill checks that the mitigations became tests, not just prose. |
| `netdust-core:architecture-invariants` | **UPSTREAM.** Each invariant names a convergence point + the bypass that's a bug; mode 4 (unmounted/unwired) and mode 5 (missing denial) are how those bypasses slip past a green suite. An invariant's bypass should have a test that goes RED when a path skips the convergence point. |
| `/code-review` | **CONSUMER.** Reviews verify the audit manifest's `blind→fixed` transitions and flag any dangerous path still marked `blind`, instead of re-discovering coverage gaps free-form. |
| `superpowers:test-driven-development` | **GOVERNS THE CYCLE.** TDD's RED→GREEN governs writing each missing test this skill's audit surfaces; this skill governs WHICH tests are missing and at WHAT layer. |

**Calibration data behind this skill:** Folio, Phases 1–3 (2026-05 to 2026-06). Nineteen distinct defects reached `/code-review`, QA, or the developer **while the unit suite was green** — every one a coverage-of-the-dangerous-path escape, none a weak-assertion-on-tested-code escape. They distribute across all seven modes: stale fixture (F11 — comment `author` slug→id stayed green on legacy fixtures while three UI surfaces broke); test-world≠real-world (Phase 1.7 — migration green in the fresh-DB harness, 500 on the long-lived dev DB); wire-mock leak (the React-Query refetch-toggle oscillation jsdom never reproduced; the narrow-key list-invalidation that mocked one list shape); unmounted/unwired (F1/F3 — agent-CRUD scope check present on MCP, absent on the HTTP twin; SSE mounted under `wScope` so `requireResource` never ran; Phase B's two feature-nullifying merge-blockers that survived all seven per-task two-stage reviews because every test stopped at a seam); happy-path-only (CR-8..CR-11 — traverse-clause denials never asserted; ~80% of one sub-phase's review findings were untested denial paths, costing a 7.7× review-to-implementation time ratio); no-coverage (InlineEdit's keystroke-before-focus race masked by `userEvent.type`; Milkdown task-item CSS asserted at the AST not the DOM); concurrency/timing (the dispatcher+poller `setInterval` re-entrancy that passed when the scheduler cooperated). The lesson that made this a skill: **count-and-tier discipline was already near-100%, yet bugs shipped — because the gate checked that tests existed, never that they bit.** This skill is the missing audit. Mutation testing is deliberately demoted: it would have caught ~0 of the nineteen.

See each project's `lessons.md` for the per-bug entries (Folio: F11 canonical-form, Phase 1.7 migration-at-boot, the React-Query toggle, F1/F2/F3 cross-route guards, CR-8..11 traverse-clause, InlineEdit placeholder-vs-draft, the setInterval latch).

</integration>
