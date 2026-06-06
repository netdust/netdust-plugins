---
name: feature-acceptance
description: "Use when planning OR shipping a user-facing feature, to prove the feature actually works the way it's meant to be used — through every intended flow with edge/error/empty/concurrent cases, driven through the real browser AND the API layer, not just unit/integration tests. AUTHORS an `## Acceptance flows` matrix in the plan at plan-time (intended-use flows + a mandatory per-flow edge enumeration), and VERIFIES that matrix at shake-out by driving each flow through the faithful layer (Playwright/Chrome for UI, real HTTP/MCP for backend) and emitting a pass/fail/not-reachable manifest. Sibling to test-effectiveness: that audits whether the CODE'S tests bite; this proves the FEATURE behaves. Covers TypeScript (Playwright/Chrome/Hono/MCP) and PHP (Codeception/WPBrowser). Opt-in via the project's CLAUDE.md — not auto-invoked."
---

<objective>
A green unit suite, a passing integration test, and a clean code review all answer "is the code correct in the small?" None of them answers the question a user actually has: **does the feature do what it's for, through every way it'll be used, including the ugly paths?** This skill closes that gap. It is the *behavioral* sibling of the *code-facing* testing skills:

- `testing-workflow` (write-time, per-task): does this task have a test, at what tier?
- `test-effectiveness` (audit-time, per-phase): would the suite go RED if a dangerous code path broke?
- `feature-acceptance` (this skill): **does the FEATURE behave correctly when driven the way it's actually used — every intended flow, every edge, through the real surface?**

The unit suite can be 100% green and tier-disciplined while the feature is broken in use: the empty state renders blank, the second-actor is silently allowed, the double-submit creates two rows, the wizard breaks if you go back a step, the form 500s on the boundary value, the optimistic write never rolls back when the network fails. Those are not weak assertions on tested code (that's `test-effectiveness`) — they are *intended-use paths nobody drove*. This skill makes someone (a test, a browser, a real request) drive them.
</objective>

<core_idea>
**A feature is not "done" because its code is correct. It is done when each intended-use flow — and each edge of that flow — has been driven end-to-end and behaved.**

The discipline is two artifacts, one written, one executed, with the same matrix as the through-line:

1. **At plan-time** (Situation A): derive the **`## Acceptance flows`** matrix from the spec — every intended-use flow, each with a *mandatory* edge enumeration. This is the feature's behavioral contract, written before code, exactly as `threat-modeling` writes the attack contract before code.
2. **At shake-out** (Situation B): *drive* each flow + edge through the faithful layer (real browser for UI, real HTTP/MCP for backend), and emit a `pass`/`fail`/`not-reachable`/`unverified-no-browser` manifest. Shake-out stops being free-form "what's broken?" and becomes "verify this contract."

**The teeth are in the edges, not the flows.** A happy-flow-only matrix is worthless — the bugs that ship past green suites are almost never on the happy path. So the matrix format *forces* per-flow edge enumeration, and a flow listed with no edges is a defect in the plan, not a complete entry.
</core_idea>

<when_to_use>

| Situation | Trigger |
|---|---|
| **A — Author the acceptance matrix (plan-time)** | Writing a plan/spec for any user-facing feature (a new view, a form, a wizard, a CRUD surface, an interactive flow, an API endpoint a client will drive). Fired by `harnessed-development` Stage 1d, after the threat-model/invariants gates, BEFORE task breakdown — so the behavioral contract exists before the code. |
| **B — Verify the acceptance matrix (shake-out)** | A feature's tasks are all green and you're at the spec-complete gate. Fired by `/shakeout` after the `test-effectiveness` audit, before the reviewer dispatch. Drive every flow + edge; the manifest becomes the reviewers' convergence target. |
| **C — A feature shipped that "passed everything" but broke in use** | Any time a user / QA / the developer hit a feature defect that the unit suite, integration tests, and code review all missed. Reconstruct the flow that broke, add it (and its un-driven edges) to the matrix, drive it, fix, then sweep sibling flows. |

**Do not invoke for:** non-user-facing internal refactors with no behavioral surface (that's covered by the code-facing skills); the per-task "does this need a test" decision (`testing-workflow`); pure coverage-bite auditing (`test-effectiveness`). This skill assumes the code is *correct in the small* and asks whether the *feature behaves in the large*.

</when_to_use>

<the_matrix>

The `## Acceptance flows` section embedded in the plan. One row per intended-use flow; the **Edges** column is mandatory and is where the skill earns its keep.

| Flow | Actor | Layer | Steps (intended use) | Expected | Edges to drive (MANDATORY — enumerate, don't write "n/a" without a reason) |
|------|-------|-------|----------------------|----------|----------------------------------------------------------------------------|
| Create a work item | member | browser | open list → click +New → type title → Enter | row appears optimistically, persists on reload | **empty** title submitted; **denied** actor (viewer role) gets no +New; **double-submit** (Enter twice fast) → one row not two; **boundary** 10k-char title; **mid-flow fail** (network drops on save) → optimistic row rolls back + toast |
| Assign via API | agent token | api | POST /items/:id {assignee} | 200, assignee set, event emitted | **unauthorized** token → 403; **nonexistent** id → 404; **concurrent** two assigns race → last-write-wins by updated_at; **malformed** body → 422 |

**The six edge classes every flow is checked against** (omit one only with a written reason). Each carries a real Folio incident where a green suite shipped the bug:

1. **Empty / zero state** — no data, blank input, first-run, empty list, a prop a data layer toggles to empty. *(Folio: `useDocumentDraft` seeded from `doc ?? placeholder`; React Query flipped `doc` to `undefined` on refetch mid-session → editor blanked + a stale-frontmatter 422 on agent-save. The unit test never saw the toggle.)*
2. **Denied actor** — the wrong role / second tenant / unauthorized token drives the flow and is refused. This is `test-effectiveness` mode 5 at the behavioral layer — the denial must be *driven*, not just unit-asserted. *(Folio: a write guard installed at the route boundary saw the user's payload, but schema defaults ran a SECOND mutation pass at the service boundary — the guard was incomplete by construction. Drive the denial through the full chain, not the route function.)*
3. **Wrong order / re-entry** — back-button mid-wizard, refresh mid-flow, an action before its precondition, a second mount.
4. **Concurrent / double** — double-click submit, two tabs, racing requests, a re-entrant callback. *(Folio: the `/` empty-state "Create workspace" button and the sheet's submit button shared an accessible name; a rapid double-click could hit submit mid-transition. A single-click test never reproduced it.)*
5. **Boundary value** — max length, zero, negative, the off-by-one, unicode/emoji, the huge paste.
6. **Mid-flow failure** — network drops, server 500s, the dependency is down: does the optimistic UI roll back, does the partial write clean up, does the user see a real error. *(Folio: a tx that awaited inside `db.transaction(async tx => …)` on bun-sqlite did NOT roll back on an awaited throw — the events row persisted, and two open clients diverged until reload. "Rollback cleans up" was false at the driver+ORM seam; only forcing the failure mid-flow showed it.)*

**The litmus:** for each flow, *name who drives each edge and what proves it behaved.* If an edge has no driver, it's a finding — either author the driver or record it `not-reachable` with the reason.

</the_matrix>

<driving_layers>

**Drive each flow through the layer where its behavior actually lives — and UI features get the real browser, not jsdom.** This is the lesson behind several calibration bugs: a jsdom unit test "passes" while the rendered DOM, the real wire, or the actual interaction is broken. *(Folio: InlineEdit's pre-select-to-replace hack raced the focus effect and broke in the real browser, but RTL's `userEvent.type` clears-then-types internally — masking the bug so every jsdom test stayed green.)*

| Flow kind | Faithful layer | Tool |
|-----------|----------------|------|
| UI / interaction / rendered-DOM / CSS contract | **real browser** | Playwright spec if one exists → else `superpowers-chrome` `use_browser` against the running dev server. Assert rendered DOM + behavior, not AST. |
| Backend / endpoint / data + side-effect / event | **real HTTP/MCP, real DB** | a request through the mounted app (un-mocked wire); assert response + DB state + emitted event. |
| Full user journey crossing both | browser drives UI, which hits the real backend | one browser flow, no mocked server. |

**Fallback ladder — no silent skips.** If the browser layer can't be reached (no Playwright config, dev server not up, `use_browser` unavailable):
1. Try `use_browser` against a freshly-started dev server.
2. If still unreachable, drive the flow's *backend* through the API layer AND mark each UI assertion `unverified-no-browser` in the manifest — explicitly, never silently dropped.
3. Report the `unverified-no-browser` count to the user as residual risk. A UI feature shipped with all its UI flows `unverified-no-browser` is a flagged gap, not a pass.

The per-stack driving patterns (Playwright/`use_browser`/Hono/MCP for TypeScript; Codeception/WPBrowser for PHP) live in `patterns-typescript.md` and `patterns-php.md`.

</driving_layers>

<process>

**Situation A — author the matrix (plan-time).** Before task breakdown:
1. From the spec, list every **intended-use flow** — the things a user/agent will actually do with this feature, in their words ("create and assign a task", "filter the list and save the view", "set up a provider").
2. For each flow, fill the row: actor, faithful layer, steps, expected — then **enumerate the six edge classes**, dropping one only with a written reason. A flow with an empty Edges column is an incomplete row; do not ship the plan.
3. Mark each flow's **driving layer** per `<driving_layers>`. Flag any flow whose faithful layer is the browser, so the executor knows a browser-driven check is owed at shake-out.
4. Embed the `## Acceptance flows` matrix in the plan. It is now the behavioral contract `/shakeout` verifies against — the reviewers verify flow outcomes instead of re-discovering them.

**Situation B — verify the matrix (shake-out).** After `test-effectiveness`, before reviewer dispatch:
1. Bring up the real surface (start the dev server for browser flows; have the API reachable for backend flows).
2. **Drive each flow and each edge** through its faithful layer. Prefer authoring a durable test (Playwright/Codeception) where the flow will recur; use `use_browser` / a `curl`/request for one-shot verification.
3. Record each flow+edge `pass` / `fail` / `not-reachable` / `unverified-no-browser`. A `fail` becomes a bug handed to `superpowers:systematic-debugging` (the shake-out skill's normal fix loop). *(Before promoting a `fail` to a bug, sanity-check it against `_shared/finding-verification.md` if present — don't manufacture a flow the spec deliberately excluded.)*
4. **Sweep sibling flows** for any `fail`'s class — a missing denial on one flow usually has siblings (create vs update vs delete); a double-submit bug on one form usually repeats on the next.
5. Emit the manifest. Hand it to the reviewer dispatch as the convergence target.

**Situation C — a feature broke in use despite green.** Reconstruct → add → drive → fix → sweep:
1. Reconstruct the exact flow + edge that broke (it's almost always an edge nobody drove — denial, concurrency, boundary, mid-flow fail, empty toggle).
2. Add it to the matrix; author the driver (browser or API) that reproduces it RED-first.
3. Fix, re-drive to green, sweep sibling flows for the same edge class.
4. Record a lesson naming the flow + edge class, so the next plan's matrix inherits it.

</process>

<red_flags>

These thoughts mean a feature is about to ship broken-in-use. Stop.

| Thought | Reality |
|---|---|
| "All the unit tests pass, the feature works." | Unit-green proves the code is correct in the small. It says nothing about the empty state, the denied actor, the double-submit, or the mid-flow network fail. Drive the flow. |
| "I listed the flows, the matrix is done." | A flow with no edges is half a row. The bugs live in the edges, not the happy path. Enumerate the six edge classes or write why one doesn't apply. |
| "There's a Playwright test, the UI is covered." | Covered ≠ the edges are driven. A happy-path Playwright spec that never submits empty, never races, never drops the network proves the easy path only. |
| "I tested it in jsdom, the component renders." | jsdom is not the browser. The rendered-DOM contract, the real CSS, the actual click target — drive the real browser or you've proven the unit, not the feature. |
| "The API test mocks the client, it's fine." | Then you tested the mock. Drive the un-mocked wire once — the leak shows there, never in the mock. |
| "No browser here, I'll mark these covered." | Marking an undriven UI flow `pass` is a lie in the manifest. It's `unverified-no-browser` — flag it as residual risk, don't launder it to green. |
| "This is just test-effectiveness again." | test-effectiveness asks if the *code's tests bite*. This asks if the *feature behaves when driven*. A suite can bite perfectly on every tested path and the feature still breaks on the path no test drives. Different gate. |
| "I'll write the matrix after shake-out finds things." | That inverts the gate. The matrix written at plan-time is what makes shake-out a verification pass instead of a discovery pass. Author at plan-time. |

</red_flags>

<success_criteria>

This skill has succeeded when:

1. The plan contains an `## Acceptance flows` matrix with one row per intended-use flow, each row's **Edges** column enumerating the six edge classes (or naming why one is excluded).
2. At shake-out, every flow + edge was **driven through its faithful layer** — UI flows through the real browser (or explicitly `unverified-no-browser`), backend flows through the un-mocked wire — and recorded `pass`/`fail`/`not-reachable`/`unverified-no-browser`.
3. Every `fail` was fixed (via systematic-debugging) and its edge class swept across sibling flows.
4. The manifest was handed to the reviewer dispatch, which verified flow outcomes instead of re-discovering them.
5. No UI flow was marked `pass` without a real browser driving it; `unverified-no-browser` flows were reported to the user as residual risk.

If a later QA pass or a user finds a feature defect on an intended-use path the matrix should have contained, the matrix was too shallow — add the flow + edge class and the missed edge to the next plan's enumeration. If the matrix is authored but never driven, the gate isn't wired — cite it in CLAUDE.md and `harnessed-development` Stages 1d/3.

</success_criteria>

<integration>

| Skill / gate | Relationship |
|---|---|
| `netdust-core:test-effectiveness` | **SIBLING — code-bite vs feature-behavior.** test-effectiveness audits whether the suite would go RED if a dangerous *code path* broke (coverage of the dangerous path). This drives whether the *feature behaves* when used (every intended flow + edge). They overlap on the denial path (its mode 5 = this skill's edge class 2) — test-effectiveness asserts the denial in a unit test; this *drives* the denial through the real surface. Neither replaces the other. |
| `netdust-core:harnessed-development` | **STAGE 1d (author) + STAGE 3 (verify).** Stage 1d fires this at plan-time to author the `## Acceptance flows` matrix, after threat-model/invariants, before task breakdown. Stage 3 fires it at shake-out to drive the matrix, after test-effectiveness, before reviewer dispatch. |
| `netdust-core:shake-out` | **DOWNSTREAM HOST.** Shake-out's end-to-end sweep IS where Situation B runs; the matrix turns its free-form "what's broken?" into "verify this contract." A shake-out bug on an intended-use flow the matrix lacked is a finding this skill's authoring should have caught — feed it back as a new flow. |
| `netdust-core:threat-modeling` | **UPSTREAM TWIN.** Same shape (a contract written in the plan before code, verified later) for a different axis: threat-modeling writes the *attack* contract verified at /code-review; this writes the *intended-use* contract verified at shake-out. The denied-actor edge (class 2) is where they meet — a named mitigation should also be a driven denial flow. |
| `netdust-core:testing-workflow` | **UPSTREAM.** testing-workflow decides per-task test tier; the durable Playwright/Codeception flows this skill authors at shake-out are the e2e tier testing-workflow points at for UI/journey coverage. |
| `superpowers-chrome:browsing` | **TOOL.** The `use_browser` path for driving UI flows when no Playwright spec exists. |
| `/shakeout` | **HOST COMMAND.** Runs Situation B between the test-effectiveness step and the reviewer dispatch; passes the manifest to the reviewers. |

**Calibration data behind this skill:** Folio, Phases 1–3 (2026-05 to 2026-06). The edge-class incidents above (`useDocumentDraft` empty-toggle, the route-vs-service guard gap, the double-submit accessible-name collision, the bun-sqlite no-rollback divergence, the InlineEdit jsdom-masked race) all shipped past a green unit suite AND tier discipline — each was an intended-use *edge* nobody drove through the real surface, not a weak assertion on tested code. That is precisely the gap test-effectiveness (code-bite) does not cover and this skill (feature-behavior) does.

</integration>
```
