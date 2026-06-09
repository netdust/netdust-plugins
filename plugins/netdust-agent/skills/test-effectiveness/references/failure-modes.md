# The Seven Failure Modes — Deep Catalog

Each mode below: **definition** → **the real calibration bug** (what shipped past green) → **classification questions** (for Situation B — "which mode is this escape?") → **audit move** (Situation A — detect it in an existing suite) → **sibling sweep** (where the same mode hides nearby). The per-stack code is in `patterns-typescript.md` / `patterns-php.md`.

The modes are ordered by how silently they pass: 1–3 are "the test ran but against the wrong world," 4–5 are "the test ran but not the dangerous branch," 6–7 are "the test never ran the path at all."

---

## Mode 1 — Stale fixture

**Definition.** A test passes because its fixture encodes the OLD contract. When a server-emitted canonical form changes (an id-vs-slug, an enum value, a field name, a date format), the fixture keeps the old shape, the test round-trips green, and every real consumer breaks on the new shape that no test exercises.

**Calibration bug (Folio F11, 2026-05-27).** Comment `frontmatter.author` changed from `agent:<slug>` to `agent:<id>` server-side. Test fixtures still posted the legacy slug form, so Vitest stayed green. Three UI surfaces broke silently: `AuthorDisplay` rendered raw nanoids, `resolveIsAuthor` never matched (Edit/Delete affordances lost), `ApprovalButtons.findResolution` never resolved approvals. The first `/code-review` missed all three because no test in CI exercised the new shape; the second caught them. The fix landed *with passing tests*.

**Classification questions (is this Mode 1?).**
- Did a server-emitted canonical value (id/slug/enum/field-name/format) change?
- Were the test fixtures updated to the NEW form, or do they still carry the old one?
- If you grep the repo for the OLD form, do real consumers (not just fixtures) still match it?

**Audit move.** After any canonical-form change in the diff: `grep -rn '<old-form-pattern>'` across the WHOLE repo (app + tests). Every match is either (a) a consumer that must be updated, or (b) a test fixture that is now lying. A fixture on the old form + a green test = the trap.

**Sibling sweep.** Canonical forms are almost always read at N sites. The primary fix updates the most-visible consumer; the others (a display component, a resolver, a comparison predicate) are the siblings. Enumerate every reader of the changed field before closing.

---

## Mode 2 — Test-world ≠ real-world

**Definition.** The test runs against a fresh/clean world the harness builds from scratch (fresh-migrated DB, seeded-from-empty state, clean cache) that does not match the long-lived real world (a dev/prod DB with history, a pre-existing row, an un-migrated column). Green in the harness, broken in reality — because the harness *cannot drift*, so it cannot catch drift.

**Calibration bug (Folio Phase 1.7, 2026-05-25).** Migration `0005_..._last_touched_at.sql` was added. Backend tests passed because the harness creates a fresh DB and runs the full migration chain every run. But the developer's long-lived dev SQLite predated the migration; clicking "Log activity" gave a 500 — the column didn't exist. The test world (fresh + fully migrated) diverged from the dev world (stale). The fix was structural: run migrations at server boot, not only in the harness.

**Classification questions.**
- What does the test harness build from scratch that the real environment accumulates over time (schema, seed data, cache, sessions)?
- Could the real environment be in a state the harness never produces (a pre-migration DB, a row created before a new constraint, a half-filled column)?
- Is the failure a 500/constraint error that only appears against a *pre-existing* world?

**Audit move.** List what the harness resets per run (migrations, seeds, in-memory DB). Each reset is a place real-world drift is invisible. The fix is usually NOT another test — it's making the real environment self-heal (migrate-at-boot) or seeding the test from a realistic baseline (post-migration, has-history) instead of empty.

**Sibling sweep.** Any other state the harness builds fresh: backfill migrations (does old data get the new column populated?), enum widenings (do pre-existing rows have a valid value?), new NOT-NULL columns (do old rows violate it?).

---

## Mode 3 — Wire-mock leak

**Definition.** The test stubs the very boundary it is supposed to verify. A client test mocks the server response, so it proves "given a correct server, the client wires up" — never that the server is correct or the wire doesn't leak. Both sides are green; the un-mocked wire fails.

**Calibration bugs (Folio).**
- *React-Query refetch-toggle oscillation (2026-06-01).* A derived draft buffer re-seeded from a `doc` prop. React Query toggles `doc` to `undefined` and back on refetch; the buffer oscillated and blanked the editor. Unit tests stayed green because jsdom doesn't reproduce React Query's refetch toggling — the mocked response was stable. Only live instrumentation exposed it.
- *Narrow-key list invalidation (2026-05-24).* `useUpdateDocument` invalidated only the exact-param list key. A second surface (the wiki tree) used different list params, so its key never matched and didn't refresh. The test asserted "the list refreshes" against a single mocked list shape; the real world has multiple lists with different params.

**Classification questions.**
- Does the test mock the thing it claims to verify (the server's filter, the data layer's behavior, the wire's response)?
- Would the test still pass if the un-mocked side were broken?
- Does the real wire have variants (different params, refetch cycles, multiple consumers) the single mock doesn't represent?

**Audit move.** Grep the test for the mock of the boundary under test. A client test that hard-codes the server's already-filtered response is testing the mock. Require ≥1 assertion that crosses the boundary un-mocked — a real request through the mounted app, or a shake-out `curl`/Playwright step. For invalidation: test against the BROAD key (prefix match), not one narrow param shape.

**Sibling sweep.** Every other consumer of the same wire that uses different params; every other client surface that reads the same data through a different query key.

---

## Mode 4 — Unmounted / unwired guard

**Definition.** The unit works in isolation but is never installed in the real chain. The middleware is unit-green but not mounted on the route; the guard exists on one path but not its twin; the seam test stops at "resolution returns the object" and never drives the full chain to "act in the target." A green unit test on an unmounted guard is the most dangerous false signal there is — it works and never runs.

**Calibration bugs (Folio).**
- *F1/F3 (2026-05-27).* HTTP agent-CRUD had no `agents:write` scope check — the MCP path had it since D8, the HTTP twin didn't. SSE `/events` was mounted under `wScope` only, so `resolveProject` + `requireResource` never ran; an agent-bound token scoped to project A could receive project B events. The guards existed; they weren't mounted on these paths.
- *Phase B two merge-blockers (2026-06-02).* A library agent dispatching a tool resolved to the system workspace while its token was still bound to the home workspace; scope intersection went empty and the operator literally couldn't act in the target. Both bugs survived all seven per-task two-stage reviews because every test stopped at a seam ("resolution returns the agent," "narrowedToken.projectIds is set") and none dispatched a tool into the target and asserted success. Caught only by the whole-diff holistic review.

**Classification questions.**
- Is the only test for this guard a direct call to the guard function, with no test driving it through the mounted app?
- Does a sibling path (HTTP twin of an MCP guard, create vs update, a second route group) have the same guard mounted?
- For a capability/wiring task: does any test ACT in the target (full chain), or do they all stop at a seam?

**Audit move.** For every guard/middleware, find the test that drives it through the mounted app (real request → route → guard fires → 403). If only an isolated-call test exists, a mis-mount is invisible. For wiring tasks, find the end-to-end "act in the target" assertion; a pile of seam assertions is not it.

**Sibling sweep.** The single highest-yield sweep. Every guard has twins: HTTP↔MCP, create↔update↔patch, route-group A↔B. When you add a guard to one, audit all twins for the same mount in the same commit.

---

## Mode 5 — Happy-path-only / missing denial

**Definition.** The guard's ALLOW branch is tested; its DENY branch never runs. The test seeds the privileged actor, so the 403/empty-result path is dead code in the suite. Cross-tenant reads, scope escalation, and allow-list widening all hide here — the guard looks tested because the happy path is green.

**Calibration bug (Folio CR-8..CR-11, 2026-05-28).** Phase 3 agent-bound tokens could traverse beyond their allowed projects on `/events`, `/projects`, `/runs`, `/members`. Each route HAD a `requireResource` guard — but no test asserted the denial (`?project=<blocked>` → `FORBIDDEN_RESOURCE`). The per-route tests asserted only the in-scope 200. Review rounds 1–7 surfaced ~80 findings, the majority untested denial paths; the review-to-implementation time ratio was 7.7× (5h27m of review-fix against 42m of implementation). Also F2: MCP `create_agent` lacked the widening guard that `update_agent` had — its test asserted the happy create, never the restricted-actor-widens denial.

**Classification questions.**
- Does the guard have a test that seeds a DENIED actor (wrong role, second tenant, blocked resource) and asserts the refusal?
- Or does every test seed the privileged actor, leaving the deny branch unexecuted?
- Is there a "masking payload" — does the test seed the easy/correct actor so the broken path never runs?

**Audit move.** For every `requireScope` / `requireResource` / capability check / `if (…) return 403`, find the denial test. Search the test file for the 403/forbidden assertion and the denied-actor setup. If absent, the guard is untested no matter how green the suite. This is the audit of `testing-workflow`'s Tier-A negative path — across EVERY sibling guard, not just the one in the current task.

**Sibling sweep.** Every route of the same type (all list routes, all write routes) must have the SAME denial asserted — the traverse-clause class is exactly N sibling routes each missing the same negative test. Also: every guard's twin (Mode 4) needs the denial too.

---

## Mode 6 — No coverage at all

**Definition.** A real behavior has literally no test exercising it. The path isn't weakly tested — it's untested. Often masked: a test HELPER hides the bug (a typing helper that clears-then-types hides an append-vs-replace defect), or the contract is asserted at the wrong layer (the parsed AST is checked, the rendered DOM/CSS the user sees is not), or a failure contract (rollback on throw) is never forced to fail.

**Calibration bugs (Folio).**
- *InlineEdit placeholder-vs-draft (2026-05-23).* A default-editing input pre-filled `draft = value` and relied on `input.select()` so typing would replace "Untitled." If a keystroke arrived before the select effect, text appended → "UntitledFirst task." It didn't show in unit tests because RTL's `userEvent.type` clears via select-all internally — masking the bug. No e2e exercised typing immediately after focus.
- *Milkdown task-item CSS (2026-05-24).* GFM parsed `- [x]` into `<li data-item-type="task">` but shipped no CSS to render a checkbox. The AST test passed; the rendered DOM the user sees was never asserted.
- *bun-sqlite async rollback (F6).* `db.transaction(async tx => …)` does not roll back on an awaited throw — the row persists while the event doesn't fire. The test asserted "publish suppressed on throw," never "row rolled back on throw" (which is false on this driver). The all-or-nothing contract was never forced.

**Classification questions.**
- Is there ANY test that executes this exact path (not a neighbor)?
- Does a test helper mask the behavior (clears-then-types, auto-flushes, auto-retries)?
- Is the contract asserted at the layer the USER experiences (rendered DOM, persisted state), or only at an internal layer (AST, return value)?

**Audit move.** List the phase's user-facing behaviors and interaction/DOM contracts; map each to a test that exercises THAT layer. Gaps are findings. Be suspicious of green tests on input/timing/render paths — check whether the helper is doing work that hides the defect.

**Sibling sweep.** Other behaviors of the same component family with no DOM/interaction test; other uses of the same risky primitive (every `db.transaction(async …)` for the rollback contract).

---

## Mode 7 — Concurrency / timing

**Definition.** A single green run passes by scheduling luck. The race only manifests under an adverse interleaving — callback A slow while B re-enters, a high-frequency tick, a data layer that toggles a value on a schedule the test exits before seeing. One green run proves nothing about determinism.

**Calibration bug (Folio Phase 3 F shake-out).** The agent-run dispatcher and event-bus poller both registered `setInterval` callbacks without a re-entrancy latch. A slow first callback let the second fire mid-transaction → status transitions out of sync, events out of order. Unit tests of each in isolation passed; the suite never ran long enough for them to collide. (Also the React-Query oscillation in Mode 3 is timing-flavored: the harness exits before the refetch cycle toggles.)

**Classification questions.**
- Does the path involve `setInterval`/`setTimeout`/a poller/a queue/`Date.now()`/a refetch-toggle/concurrent transactions?
- Does the test force the adverse interleaving (slow first callback, high-frequency tick, concurrent runs), or does it run once and hope?
- Would the test still pass if the scheduler ordered events the other way?

**Audit move.** For each timer/poller/refetch/concurrent path, find the test that FORCES the bad interleaving — injects a slow dependency, drives the timer manually, launches concurrent operations. If the test runs once and asserts, it's scheduling luck. Require the new/changed test to run ≥3× green (this is `testing-workflow`'s determinism box — audit it was actually done).

**Sibling sweep.** Every other shared timer/interval (do they all have the latch?); every other derived-state-from-toggled-source (Mode 3 overlap); every other concurrent writer to the same row/transaction.

---

## Using this catalog

- **Situation A (audit):** walk the diff, apply each mode's audit move to the dangerous paths it touches, record `covered`/`blind`/`fixed`.
- **Situation B (an escape happened):** answer the classification questions to find the mode, write the RED-first reproducing test, then run the sibling sweep — the escape is rarely alone.
- **Situation C (authoring):** open the patterns file and use the mode's author pattern so the dangerous path is asserted first.

When a new escape doesn't fit any of the seven, that's signal: add it here as mode 8+ with its own calibration bug, audit move, and sweep — the catalog grows from real escapes, never from speculation.
