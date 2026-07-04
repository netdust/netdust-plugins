---
name: building
description: The BUILD spine of the Netdust harness — execute → test → standards → review clusters → shake-out → finish. PRECONDITION-FIRST — for plan-driven work (Class A/B) it REFUSES to start unless an approved `tasks.md` exists and `spec-kit/gate-check.py` is GREEN; the seam artifact from `planning` is the entry ticket, and a missing or red gate-check routes the work BACK to `planning`, never forward. Also the home of the plan-less classes — a bug-fix bundle from review findings is one TDD cycle per finding (Class C), an ad-hoc security-boundary edit runs after its diff threat model (Class D), a small self-contained tweak is one straight TDD cycle (Class E). Owns the Stage-2 armed loop (`/loop` + loop-gate). Normally entered via `harnessed-development` intake; also triggers directly on "execute the plan", "work the plan", "execute todo.md", "execute tasks.md", "start building", "implement the plan", "run the tasks", "fix the code-review findings", "address the review feedback". NOT for writing or reshaping a plan — that is `planning`; if you find yourself re-deciding plan content here, you are in the wrong spine. Stack-agnostic; defers to the loaded stack sub-plugin for stack-specific skills, reviewers, and test runners. Replaces the deleted `ntdst-execute-with-tests` skill (its "execute the plan" / "work the plan" triggers resolve here).
---

<precondition>
**Check this BEFORE anything else — before loading an execution skill, before reading the plan, before touching a file.** Entry is by class (stated at `harnessed-development` intake; restate it here in one sentence):

| Class | Entry ticket — verify, then proceed |
|---|---|
| **A / B — plan-driven work** | The seam artifact, all three parts: **(1)** `tasks.md` exists for the feature; **(2)** `python3 <plugin>/spec-kit/gate-check.py specs/<feature>` exits **0** — run it NOW, do not trust a transcript assertion (yours or `planning`'s); **(3)** your human partner has approved the plan. **Any part missing → REFUSE to start.** Name the missing part and route the work to `planning` (Class B additionally gets `planning`'s freshness review when the plan is stale or externally authored). On a project without the spec-kit graft, the equivalent ticket is `planning`'s manual 1a–1g checklist explicitly confirmed in the plan + human approval — ask for it if it isn't stated. |
| **C — bug-fix bundle from `/code-review` or `/security-review`** | No plan needed. Each finding is one TDD cycle (Step 2.7); Stage 3 verifies. If any finding touches a security boundary, the 1a diff threat model (from `planning`) must exist first. |
| **D — ad-hoc edit to a named security-boundary file** (auth/session/token, URL-allow-list, crypto) | The thin plan gate: a `## Threat model` **on the diff** (produced by `threat-modeling` via `planning`'s 1a) must exist BEFORE implementation. Even for a one-liner. Then: implement with TDD → verify. (Slug: `class-d-gap`.) |
| **E — small self-contained change, no plan warranted** | Straight to one TDD cycle (Step 2.0, third row). No plan, no spec, no shake-out. The per-task testing gate STILL applies — tier it, record the Test-evidence block; the `subagent-stop` hook still backstops it. Verify with the suite + `/integration` on the diff. |

This precondition is the whole point of the plan/build split: the gates `planning` sequences are only durable because THIS skill will not run without their machine-checked output. Talking yourself past a red or missing gate-check re-fuses what the split separated.
</precondition>

<objective>
Make one truth hold: **every task that ships crossed its gates — per-task test evidence, standards, review-cluster HALTs, phase-close audits — and none was left to "remember to do it."** The plan (or the class's single TDD cycle) says what to build; this spine proves, auditably in reports and commit bodies, that it was built gated.

This skill enforces what the upstream superpowers skills do not:

1. **Entry is gated at the seam** (`<precondition>`) — the plan-time gates cannot be skipped upstream and slip through, because their machine-checked output is the entry ticket.
2. **Every task close is gated on tests, auditably.** `testing-workflow` discipline is mandatory at each task close, and every implementer report ends with the structured Test-evidence + STATUS blocks — visible in the transcript, not honor-system.

Everything in between — TDD red→green, dispatch shape, two-stage review, status handling, escalation — belongs to the upstream superpowers skills. This skill is a **sequencer**: at each stage it loads the right upstream skill and adds the netdust-specific gate around it. Do NOT duplicate upstream content. Stack-agnostic by design — see `<stack_overrides>`.
</objective>

<how_each_gate_is_actually_enforced>
Be honest about enforcement strength — the gates are NOT equally hard:

- **The seam precondition is MACHINE-CHECKED.** `gate-check.py` exits non-zero; you run it and read the exit code. It cannot be talked out of a finding.
- **The per-task testing + standards gates are HOOK-ENFORCED.** `subagent-stop.py` (a real SubagentStop hook) blocks a subagent that edited code from stopping without the testing-workflow evidence, and blocks a close that skipped a configured linter. Even so, the *auditable* evidence is the structured Test-evidence + STATUS blocks in the report/commit — the hook is the backstop.
- **The review-cluster HALTs (Step 2.8) and Stage-3 sequence are SEQUENCER-ENFORCED.** No hook stops you from running past a `── REVIEW GATE ──` marker. Treat the marker as non-negotiable as a failing test, precisely because nothing will hard-stop you.
</how_each_gate_is_actually_enforced>

<extremely_important>
This skill is a sequencer. Do not think about execution shape, do pre-flight greps, or improvise in the controller session BEFORE invoking the stage's upstream skill — that reasoning belongs to the upstream skill or to a subagent. The one exception is Step 2.5 (plan-freshness ground-truthing), which is explicitly a *post-upstream-load, per-task* controller obligation.

And the mirror of `planning`'s boundary: **this skill never re-plans.** If execution reveals the plan's shape is wrong (not just a signature drifted — Step 2.5 handles drift), stop and take it back across the seam: a plan-correction with your human partner, not an improvised re-design mid-dispatch.
</extremely_important>

<stack_overrides>
**Standing rule — this skill names only generic skills; a loaded stack sub-plugin replaces them.**

- **Testing** — `testing-workflow` auto-detects the stack and picks the right unit/integration runner. Nothing to override manually.
- **Execute / UI craft** — if the sub-plugin provides stack-specific build or frontend skills, prefer them at Stage 2 for matching tasks.
- **Shake-out / review** — if the sub-plugin provides a stack-specific shake-out skill or reviewer agents (PHP/WP, Statamic, …), the spec-close gate (Stage 3) dispatches *those* in addition to the generic reviewers. `/shakeout` already does this auto-dispatch per detected stack.

Do not hardcode any stack's skill names in this file.
</stack_overrides>

<craft_routing>
GATES decide *whether/when*; CRAFT skills are the *how-to* loaded to do that step's work well. Craft layers on its superpowers base, never replaces it.

| Stage / step | Gate (when/whether) | Craft skill to load (how-to) |
|---|---|---|
| Stage 2 — execute, any task | `testing-workflow` (per-task tier gate, Step 2.6) | `writing-tests` (Tier-A RED→GREEN on top of `superpowers:test-driven-development`) |
| Stage 2 — execute, UI task | `feature-acceptance` (1g matrix, authored by `planning`) | `building-frontend` (component/state/a11y/responsive; build the empty/error/loading edge states the matrix drives) |
| Stage 2 — execute, any commit | — | `versioning-with-git` (atomic commit-per-task; STATUS / Test-evidence in the commit body) |
| Stage 2 — ground-truth (Step 2.5) | — | `sourcing-from-docs` (external dep) + `engineering-context` (sibling code from the 3-layer memory) |
| Any stage — browser drive / inspect | `feature-acceptance` / `superpowers:systematic-debugging` | `driving-the-browser` (HOW to operate Chrome; feature-acceptance owns WHAT to drive) |
| Stage 3 — review | `/code-review` + reviewer agents | `simplifying-code` (reduce complexity, behavior preserved — suite green before and after) |
| Stage 3 — finish / deploy | `superpowers:finishing-a-development-branch` | `deploying` (route to `/deploy` + dev-stack; never prod without explicit confirmation) |
| Stage 3 — spec-close (after finish) | `compounding` | `compounding` (harvest into CODE-MAP + scoped skill-audit; spec-close only) |
| Session start / task switch | — | `engineering-context` (pack the right context from the existing 3-layer memory model) |

If a stack sub-plugin offers a sharper craft skill for a stage, prefer it — same rule as `<stack_overrides>`.
</craft_routing>

<stage_personas>
Each stage has an agent PERSONA you can dispatch to own it — the *who* that LOADS the stage's gates + craft skills. Dispatch the persona, or run the stage inline; the gates fire the same either way:

| Stage | Persona | What it loads / owns |
|---|---|---|
| Stage 2 — one task to done, test-gated | `implementer` (one per task, often parallel) | testing-workflow/writing-tests, building-frontend, versioning-with-git; closes with the Test-evidence + STATUS blocks |
| Stage 3 — whole-diff review | `reviewer` (generalist, five-pillar) + the specialist reviewers | reviews the diff against the threat model, invariants, and test-effectiveness manifest |
| Stage 3 — exercise the artifact | `shakeout-qa` | drives the acceptance matrix through the real browser / un-mocked wire; compiles the bug manifest |

At Stage 3 the `/shakeout` command auto-dispatches `reviewer` + the specialists in parallel, after `shakeout-qa` (or the inline sweep) has exercised the artifact.
</stage_personas>

<process>

## Stage 2 — Execute

**Handoff seam (spec-kit graft).** When the plan came through spec-kit, execution starts from `tasks.md` — it feeds THIS stage. **NEVER run `/speckit.implement`:** it executes tasks flat with none of the Stage-2 gates below (no threat-model verify, no per-task tiers, no review-cluster HALT, no `subagent-stop.py` backstop). spec-kit owns spec→plan→tasks; this spine owns execute→verify→finish. Nothing downstream of `tasks.md` runs under spec-kit.

**Armed loop (optional, `/loop`).** When `tasks/.harness-loop.json` exists, the `loop-gate.py` Stop hook drives this stage: the session cannot stop while unchecked non-`[HUMAN]` tasks remain — the gate blocks the stop and names the next unit (`spec-kit/loop-check.py` is the ledger; FINISHED is derived from `tasks.md`, never asserted). Two obligations while armed: (1) stay a THIN SCHEDULER — rebuild your working state from `tasks.md` + the plan on every re-entry, never from scrollback (compaction must not kill the loop); (2) the loop changes NOTHING below — review-gate HALTs, tiers, and the subagent-stop backstop apply exactly as written. The loop ends at Stage 2 complete; Stage 3 runs attended.

**Step 2.0 — Pick and invoke the execution upstream skill.** State your choice and one-sentence reason first.

| Plan shape | Upstream skill |
|---|---|
| Independent tasks suitable for parallel subagents (most common) | `superpowers:subagent-driven-development` |
| Sequential tasks needing shared context, or solo execution | `superpowers:executing-plans` |
| **No plan — a single small change (Class E)** | None. Do the one TDD cycle directly: `superpowers:test-driven-development` (red→green), record the Test-evidence block, done. No dispatch machinery, no addendum. |

Invoke it via the Skill tool. Its content is your primary instruction set for execution from here on; this skill only adds the netdust gates below.

**Step 2.1 — Append the netdust addendum to every dispatch prompt.** For each subagent dispatch (implementer, spec reviewer, code-quality reviewer), append the block in `<addendum_for_dispatch>` VERBATIM. Do not summarize, paraphrase, or selectively include — the verbatim form is what closes the audit gap, because it demands the structured **Test-evidence + STATUS blocks** (tier, RED-first/Tier-B, seam, deferral) in the report. (Calibration: `subphase-a-0of7` — the blocks are verifiable in the report + commit; a Skill-tool call in a subagent transcript is not. Full story under `<integration>` below.)

**Step 2.5 — Ground-truth the dependency surface before each dispatch (plan-freshness gate).** A written plan is a *hypothesis* about the code it integrates against; the source is truth. When the plan is more than a few days old, OR it integrates against another sub-phase's / module's code (calls its functions, names its enums, scopes, env vars, table columns, event payloads), the controller MUST — for the specific task about to be dispatched, AFTER the upstream skill is loaded (never as pre-flight before Step 2.0) — Read the actual exported signatures + types + enums of that task's named dependencies and reconcile them against the plan's code samples. Bake the verified-true signatures into the dispatch prompt and flag any drift inline so the implementer builds to reality, not the stale sample. Per-task, not whole-plan up front. If reconciliation surfaces drift big enough to change the task's shape, correct the plan (a plan-correction commit) before dispatching.

  Calibration (why this is a hard rule, not advice): FOUR consecutive Folio sub-phases hit plan-vs-source drift this catch resolved — A (Zod house-style + migration columns), C.2 (an entire provider API that didn't exist), C.3 (`recoverOrphanRuns` signature + a contaminated `db:generate` migration), Phase C (triggers carry `fm.agent`, not the plan's `target_agent_id`). Every drift was caught at controller ground-truthing and corrected before/at dispatch. Skipping it ships the drift into the subagent, which builds the wrong thing confidently. (Slug: `plan-drift-4x`.)

**Step 2.6 — Gate every task close on testing-workflow's OUTPUT, not its re-invocation.** A task is not done until the subagent's report ends with the structured Test-evidence + STATUS blocks (see addendum), AND those blocks carry the testing-workflow discipline made auditable: the **tier classification** (A/B + one-sentence justification), a Tier-A **RED-first** proof (or the `no unit test: Tier B, <reason>` line), and the **deferral line** naming the risk class handed downstream.

  Those blocks — visible in the report and the commit body — ARE the gate. Do **not** require the subagent to literally re-invoke `Skill("testing-workflow")` once per task: the gate skill itself states that *"Re-invoking the Skill tool once per task is **not** the discipline."* The subagent reads testing-workflow **once per session** to internalize it; per-task re-invocation is the ghost ritual `subphase-a-0of7` retired.

If any required block or line is missing, treat the task as DONE_WITH_CONCERNS or NEEDS_CONTEXT per the upstream skill's status handling. Do not mark complete without them. The `subagent-stop.py` hook is a backstop, not the primary mechanism — the structured blocks are.

**Step 2.6b — Standards gate at every code-task close.** Alongside the testing gate, invoke `netdust-agent:standards-gate`: run the project's configured linter/formatter (eslint/prettier/biome, or phpcs/php-cs-fixer) on the touched files and record a `Standards: clean | <N fixed> | n/a — no linter` line in the Test-evidence block. The same `subagent-stop.py` hook backstops it: it blocks a code-editing subagent's close when a linter is configured for the project but was never run. If no linter is configured, the gate (and the backstop) no-op — do not impose a style of your own.

**Step 2.7 — Bug-fix bundles (Class C) get one TDD cycle per finding.** Each `/code-review` or `/security-review` finding is a behavior change → the Iron Law applies. Invoke `superpowers:systematic-debugging` once per bug via the Skill tool, fix one bug per cycle, re-sweep between. "I already see the fix, the phases are obvious here" is the exact rationalization the debugging skill's red-flags table names. (2026-05-30, Sub-phase F: bundling I2+I3 into one cycle drifted the process even though outcomes were sound. Slug: `one-cycle-per-bug`.)

**Step 2.8 — HALT at every review-gate marker (the cluster boundary is a hard stop).** When you reach a `── REVIEW GATE ──` / STOP marker in the plan (placed by `planning`'s task-shaping gate), OR the end of a phase's task group, you STOP. Commit the cluster's tasks, run `/integration` on that cluster's diff, then review — and do NOT begin the next task until that review is clear. The diff a reviewer holds must be one cluster (~3–4 tasks), never a whole long phase run flat. **The pull to "just keep going to the next task, I'll review at the end" is the exact failure the cluster rule exists to prevent** — it produces an un-bisectable mega-diff and lets the agent grade a large body of its own work in one pass. Treat the marker as non-negotiable as a failing test. If the plan you're executing is a long phase with NO such markers, that is a planning defect — add the markers (a plan-correction commit) before running past ~4 tasks. (Slug: `teardown-cluster`.)

  **State the review tier at the gate, same as the work-class statement at intake.** Before dispatching the cluster review, declare in the transcript: `Review tier: <FULL | STANDARD | LIGHT> — <one-line justification keyed to the 1a trigger surface>` (the plan carries a provisional tier per cluster from `planning`; restate it, and override with justification if the cluster's diff turned out to touch a different surface than planned). The fan-out you dispatch is **read from the stated tier**, not fixed:
  - **FULL** (diff touches any 1a trigger surface, a named architecture invariant, or the data layer/migrations) → all finder angles in parallel + `security-sentinel` mandatory; `/code-review --effort=high`; `/security-review` if the threat-modeling gate fired at plan time.
  - **STANDARD** (multi-file behavior changes outside those surfaces) → 2 finder angles (line-by-line + cross-file tracer) + `code-simplicity-reviewer` + the feature-acceptance browser pass. No `security-sentinel`, no `performance-oracle` unless the diff touches a hot path named in `CODE-MAP.md`. `/code-review --effort=medium`.
  - **LIGHT** (doc/copy/config/skill-body only) → a single generalist `reviewer` pass. No fan-out.

  **Escalation is one-way.** If ANY finder/reviewer surfaces a finding on a 1a surface, the cluster is immediately promoted to **FULL** — dispatch the FULL-tier reviewers you skipped, on this same cluster, before proceeding. Never de-escalate mid-review. And regardless of tier, `/security-review` still fires if a plan-time `## Threat model` exists for this work — tier governs finder/persona fan-out; it never cancels the security-review obligation.

## Stage 3 — Phase close, shake-out, finish

After all tasks in a phase complete and the upstream skill's final-review step is done:

1. **Phase-complete integration gate** — `testing-workflow` phase-complete (integration + acceptance), or run `/integration`.
2. **Test-effectiveness audit** — invoke `test-effectiveness` (Situation A) over the phase diff. The integration gate proved the tests *pass*; this proves they would *bite*. Walk the seven failure modes over every dangerous path the diff introduced — for each guard, fixture, wire, mount, and timer, name the test that goes RED if it breaks, or record it `blind` and fix it. The resulting `covered`/`blind`/`fixed` manifest is the convergence target for the next step's reviewers. (Especially load-bearing on security-rich / multi-tenancy phases — see `traverse-clause`.)
3. **Feature-acceptance verification** — if the phase added/changed a user-facing feature, invoke `feature-acceptance` (Situation B) to *drive* the `## Acceptance flows` matrix `planning` authored at 1g. Drive each flow + edge through its faithful layer — UI flows through the real browser (Playwright spec → else `superpowers-chrome` `use_browser` against the running dev server), backend flows through the un-mocked wire — and emit a `pass`/`fail`/`not-reachable`/`unverified-no-browser` manifest. (`/shakeout` runs this for you.) No UI flow is `pass` without a browser driving it.
4. **Shake-out** — invoke `shake-out`, or its stack-specific replacement (see `<stack_overrides>`); or run `/shakeout` at spec close. This is the spec-complete / pre-merge gate: re-runs integration, runs E2E, and dispatches the reviewer agents against the full branch diff. **The spec-close panel composition is set by the branch diff's review tier:** FULL → the 5-persona panel (`reviewer` + `code-simplicity-reviewer` + `security-sentinel` + `performance-oracle` + `invariant-auditor`; +`ntdst-drift-reviewer` on WP); STANDARD → `reviewer` + `invariant-auditor` only; LIGHT → a single `reviewer` pass. State the branch tier before dispatch; one-way escalation still applies. `/shakeout` reads the tier and dispatches accordingly.
5. **Finish** — `superpowers:finishing-a-development-branch`. (`shake-out`'s own completion step has already invoked `superpowers:verification-before-completion` — don't re-run it here.)
6. **Compound** (spec-close only) — invoke `compounding`. After the branch is finished, harvest what the spec taught into PROPOSALS: a patch to `docs/architecture/CODE-MAP.md` + a `/skill-audit` scoped to the skills touched this spec. Report-only — the user approves what's written, nothing auto-edits. **Cadence: spec-close / `/shakeout`-level only — NOT every sub-phase.**

</process>

<addendum_for_dispatch>

Append this block VERBATIM at the bottom of every implementer dispatch prompt. It supplements (does not replace) the upstream `implementer-prompt.md` template.

```
---

## Netdust addendum — mandatory close-out

Before reporting STATUS, you MUST:

1. Apply the `testing-workflow` discipline (read it once per
   session to internalize it — you need NOT re-invoke the Skill tool per
   task): classify the task's risk tier (A/B), verify at the tier
   (Tier A → a RED-first behavioral test incl. the denial path; Tier B →
   suite-green + seam reach, with a `no unit test: Tier B, <reason>` line),
   and record the tier + deferral line. The structured blocks below — not a
   Skill-tool re-invocation — are what makes this gate auditable.

2. Run the affected app's full unit suite from the APP's directory
   (never from repo root). Confirm the test-count delta matches the
   plan's expectation.

3. Run static analysis on touched files. For TypeScript:
   `bun x tsc --noEmit` from the affected app's directory.

3b. Run the project's linter/formatter on the touched files if one is
   configured — `netdust-agent:standards-gate` (eslint + `prettier --check`
   for TS/JS, `phpcs` for PHP/WP, biome, etc.). Fix violations or justify
   them narrowly inline. If no linter is configured, this is n/a. The
   subagent-stop hook blocks your close if a linter exists and you skip it.

4. End your final message with these two blocks, verbatim and complete:

   ## Test evidence
   - Tier: <A | B> — <one-sentence justification>
   - Test file(s): <list of paths touched, or "none — Tier B">
   - RED proof: <command you ran> → <1-3 line snippet showing fail>
     (Tier B: replace with `no unit test: Tier B, <reason>`)
   - GREEN proof: <command you ran> → <1-3 line snippet showing pass>
   - Seam test (if this task WIRES a piece into the real chain):
     <1 un-mocked-chain assertion + 1 negative/adversarial case, or "n/a — not a wiring task">
   - Suite delta: <app> was <N>, now <M>, <K> fails
   - Typecheck: <command> → <clean | errors>
   - Standards: <clean | N fixed | n/a — no linter> (cmd: <what you ran>)
   - Deferral: Risk this does NOT cover: <concurrency | adversarial-input |
     cross-actor | multi-component | un-mocked-seam | none> → <integration-gate | /code-review | invariant-auditor | /shakeout>

   ## STATUS
   STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
   COMMIT: <sha>
   FILES TOUCHED: <list>
   DIVERGENCES FROM PLAN: <list, or "matched plan verbatim">

Missing any item in either block = task NOT done. Do not rationalize.
Do not substitute prose for the structured form. The structure is what
makes the audit possible.

---
```

For **doc-only or tooling-only tasks** (no code-touching changes), the implementer may omit the Test evidence block but MUST still include the STATUS block.

For **reviewer subagents** (spec compliance, code quality), only the STATUS block is required — they do not run tests themselves.

</addendum_for_dispatch>

<red_flags>

These thoughts mean you are about to skip a gate. Stop.

| Thought | Reality |
|---|---|
| "The plan looks solid, I'll skip re-running gate-check and start dispatching" | The seam is machine-checked BY YOU, at entry, every time. An assertion in a transcript (even `planning`'s) is not an exit code. Run it. |
| "gate-check is red on a formality — I'll proceed and fix the plan later" | A red checker means a gate the work warranted did not fire. Route back to `planning`; do not carry a defect across the seam. |
| "It's just a one-line edit to the URL allow-list, no plan needed" | Correct — but it IS Class D: the threat model runs on the *diff* before you implement. This is the exact 2026-06-03 gap (`class-d-gap`). |
| "The plan was written this week, it's fresh enough" | Conventions and signatures drift within a single sub-phase. Step 2.5 is per-task and mandatory when the task integrates against other code (`plan-drift-4x`). |
| "Execution shows the plan's approach is wrong — I'll redesign as I go" | Signature drift is Step 2.5; a wrong *shape* goes back across the seam as a plan-correction with your human partner. This spine never re-plans. |
| "Let me grep the codebase to understand the task before invoking the upstream skill" | The upstream skill IS how you understand the task. Invoke it first. (Step 2.5 ground-truthing is the one allowed post-load read.) |
| "I already know what subagent-driven-development says" | Skills evolve. Invoke and read the current version every time. |
| "Skipping the verbatim addendum saves a few lines" | The verbatim form is what closes the audit gap. Skipping it reverts to honor-system (`subphase-a-0of7`). |
| "I see the fix for all three review findings, I'll bundle them" | One TDD cycle per finding, one systematic-debugging invocation per bug (`one-cycle-per-bug`). |
| "Two-stage review is ceremony for a simple task" | The review loop catches what TDD doesn't. Do not skip it. |
| "I'll just finish the rest of the phase's tasks, then review the whole thing at the end" | That's the un-bisectable mega-diff (`teardown-cluster` / Step 2.8). HALT at the review-gate marker. A reviewer must hold one cluster, not a 7-task phase. |
| "I'll classify the tier and record the deferral line after the commit, not before reporting" | Order is: verify-at-tier → full suite + static analysis → report with the tier + RED-first/Tier-B + deferral blocks. The blocks must be in the report. |
| "This cluster only touches auth lightly — I'll run STANDARD to save time" | Touching a 1a surface AT ALL = TIER FULL. The trigger is binary on the surface, not a severity judgment — and under-calling FULL is the dangerous direction. |
| "A finder flagged something on the token path but this is a STANDARD cluster, I'll note it and move on" | Escalation is one-way: a finding on a 1a surface promotes the unit to FULL NOW — dispatch the skipped reviewers on this same unit before proceeding. |
| "The plan-time threat model means I can skip /security-review since the panel was STANDARD" | Backwards. `/security-review` is independent of tier — if a `## Threat model` was authored at plan time, it fires regardless. |
| "I'll just run `/speckit.implement` to execute the tasks" | That bypasses every Stage-2 gate — threat-model verify, per-task tiers, review-cluster HALT, the `subagent-stop` backstop. The handoff is `tasks.md`; this spine executes it. NEVER `/speckit.implement`. |
| "Tests are green, the task is done" | Tests are half the close. Run `standards-gate` too (Step 2.6b) and record the `Standards:` line — or the `subagent-stop` hook blocks the close when a linter is configured. |

</red_flags>

<success_criteria>

This skill has succeeded when:

1. The seam precondition was verified at entry — `gate-check.py` run fresh (exit 0) + human approval confirmed for Class A/B; the class-specific ticket for C/D/E.
2. The execution upstream skill was invoked via the Skill tool and its checklist followed.
3. Every implementer dispatch contained the verbatim addendum; every implementer report ended with the structured Test-evidence + STATUS blocks carrying the tier classification, the Tier-A RED-first proof (or the `no unit test: Tier B` line), and the deferral line.
4. Step 2.5 ground-truthing was performed per-task for every task integrating against other code.
5. Execution HALTed at every `── REVIEW GATE ──` marker, with the review tier stated and the matching fan-out dispatched; escalation, when triggered, was one-way to FULL.
6. Every code-task close recorded a `Standards:` line; the `subagent-stop` backstop did not have to fire.
7. Phase close ran the full Stage-3 ladder: integration → test-effectiveness → feature-acceptance drive → shake-out → finish → (spec-close) compounding.
8. `/speckit.implement` was never run; no re-planning happened inside this spine.

If any gate that *should* have fired did not, the skill failed at its specific job — even if the code shipped correctly. This spine exists for *gate-coverage durability*; the upstream skills handle code correctness.

</success_criteria>

<integration>

| Skill | Relationship |
|---|---|
| `harnessed-development` | **ROUTER / UPSTREAM.** Classifies the work (A–E); every class's execution lands here. |
| `planning` | **UPSTREAM — the other spine.** Produces the seam artifact this skill's precondition demands (approved `tasks.md` + gate-check GREEN). A red/missing ticket routes work back there; so does a mid-execution discovery that the plan's shape is wrong. |
| stack sub-plugins | **OVERRIDE LAYER.** Stack-specific execute/shake-out skills, reviewers, and test runners replace the generics — see `<stack_overrides>`. |
| `superpowers:subagent-driven-development` | **STAGE 2 — primary branch.** Parallel-independent tasks. |
| `superpowers:executing-plans` | **STAGE 2 — secondary branch.** Sequential / solo execution. |
| `superpowers:test-driven-development` | **STAGE 2 — Class E branch.** The single red→green cycle, no dispatch machinery. |
| `superpowers:systematic-debugging` | **STAGE 2 (Class C).** One invocation per bug. |
| `testing-workflow` | **STAGE 2 MANDATORY GATE.** Per-task close (the addendum's structured blocks ARE the auditable gate) + phase-complete. |
| `standards-gate` | **STAGE 2 GATE (Step 2.6b).** Project linter on touched files at each code-task close; backstopped by `subagent-stop.py`. |
| `test-effectiveness` | **STAGE 3 GATE.** Phase-close audit: green tests proved to *bite*; its manifest is the reviewers' convergence target. |
| `feature-acceptance` | **STAGE 3 (drive).** Drives the `## Acceptance flows` matrix `planning` authored at 1g — real browser / un-mocked wire. |
| `shake-out` | **STAGE 3.** Spec-close, after upstream final-review; panel composition read from the branch tier. |
| `superpowers:finishing-a-development-branch` | **STAGE 3.** After shake-out. |
| `compounding` | **STAGE 3 closer (step 6, spec-close only).** Harvests spec knowledge into PROPOSALS; report-only. |
| `/loop` + `loop-gate.py` + `spec-kit/loop-check.py` | **STAGE 2 DRIVER (optional).** The armed loop that runs execution unattended through `tasks.md`; drives *through* the gates, never around them. This spine owns the loop protocol. |
| `subagent-stop.py` hook | **BACKSTOP.** Blocks a code-editing subagent's close without testing evidence or with a skipped configured linter. Backstop, not primary — the structured blocks are. |
| `ntdst-execute-with-tests` (historical) | **DELETED (2026-06-05) — absorbed into the god-skill, whose execution half is now THIS spine.** Its triggers ("execute the plan", "work the plan") resolve here. |

**Calibration data behind these rules** (index: `skills/_shared/calibrations.md`):
- *Verbatim addendum (`subphase-a-0of7`):* Sub-phase A — 0/7 subagents re-invoked the testing-workflow skill under a weaker one-liner, yet the work was correct. The lesson (2026-06-04): the audit trail must rest on the **structured Test-evidence + STATUS blocks** the addendum demands, not on a per-task Skill-tool re-invocation — which is unverifiable from git and which the testing-workflow gate skill has itself retired.
- *Step 2.5 (`plan-drift-4x`), Step 2.7 (`one-cycle-per-bug`), Step 2.8 (`teardown-cluster`):* told in full at their steps above.

</integration>
