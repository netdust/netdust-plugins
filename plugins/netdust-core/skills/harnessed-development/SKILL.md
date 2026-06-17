---
name: harnessed-development
description: The single entry point for any non-trivial work in a Netdust project — sequences the FULL harness end to end so no session can skip a gate. Brainstorm → write-plan (with threat-modeling + architecture-invariants when triggered) → execute (subagent/TDD + mandatory testing-workflow at every task close) → shake-out → finish-branch. Triggers on "build a feature", "start a feature", "implement X", "work the plan", "execute the plan", "execute todo.md", "run subagents on this plan", "start building", "do this properly", "the whole harness", "ship X". Also the entry point for ad-hoc security-boundary edits (auth/token/URL-allow-list/crypto) even with no plan. NOT for read-only questions, trivial one-file edits, formatting, dependency bumps, prose, or research — those need no harness. Required for any non-trivial work under this harness, on any stack (WordPress, Statamic, Bun/React, …) — it is stack-agnostic and defers to the loaded stack sub-plugin for stack-specific skills, reviewers, and test runners. Replaces the deleted `ntdst-execute-with-tests` skill (its "execute the plan" / "work the plan" triggers resolve here).
---

<objective>
Make one truth hold: **if this skill was invoked, the whole disciplined pipeline was engaged.** Nothing — threat modeling, invariants, per-task tests, two-stage review, shake-out — is left to "remember to do it." Each gate fires because the skill sequences it, not because a prose instruction in CLAUDE.md was honored.

This skill enforces two gates the upstream superpowers skills do not:

1. **The planning gates fire from the spine, not from prose.** `netdust-core:threat-modeling` and `netdust-core:architecture-invariants` are sequenced here, so they engage whenever their triggers match — instead of relying on a CLAUDE.md reminder a session can skip. (A security-boundary edit once shipped without a threat model because that reminder was keyed only to "writing a plan." This skill makes the gate structural — see Class D.)

2. **Every task close is gated on tests, auditably.** `netdust-core:testing-workflow` is mandatory at each task close, and every implementer report ends with the structured Test-evidence + STATUS block — so the discipline is visible in the transcript, not honor-system.

Everything in between — brainstorming, plan structure, TDD red→green, dispatch shape, two-stage review, status handling, escalation — belongs to the upstream superpowers skills. This skill is a **sequencer**: at each stage it loads the right upstream skill and adds the netdust-specific gate around it. Do NOT duplicate upstream content.

This skill is **stack-agnostic by design** — it names only generic, cross-stack skills. See `<stack_overrides>` for how stack-specific skills replace the generics.
</objective>

<stack_overrides>
**Standing rule — this skill names only generic skills; a loaded stack sub-plugin replaces them.**

This skill lives in `netdust-core` and is stack-agnostic. The stages below reference generic, cross-stack skills (`superpowers:*`, `netdust-core:*`). When a stack sub-plugin is installed for the project at hand (e.g. `netdust-wp`, `netdust-statamic`, or any future `netdust-<stack>`), and it offers a more specific skill, reviewer, or test runner for a stage, **use the stack-specific one in place of the generic** — same stage, same gate, sharper tool.

How to apply it, at each stage:
- **Brainstorm / plan / domain conventions** — if the stack sub-plugin provides a domain skill for the artifact you're designing (a framework-architecture, data-layer, or patterns skill), invoke it alongside or instead of the generic.
- **Testing** — `netdust-core:testing-workflow` already auto-detects the stack and picks the right unit/integration runner. Nothing to override manually; it does the right thing per project.
- **Shake-out / review** — if the stack sub-plugin provides a stack-specific shake-out skill or reviewer agents (PHP/WP, Statamic, etc.), the spec-close gate (Stage 3) dispatches *those* in addition to the generic reviewers. `/shakeout` already does this auto-dispatch per detected stack.

Do not hardcode any stack's skill names in this file. The rule is "prefer the stack-specific skill when one is loaded for this project" — that way new sub-plugins are picked up without editing this skill.
</stack_overrides>

<extremely_important>
This skill is a sequencer with one job: at each stage, load the right upstream skill, then add the netdust-specific gate. It is NOT a place to think about execution shape, do pre-flight checks, run grep/ls, or improvise.

If you find yourself running Bash, Read, or Grep in the controller session to "understand the task" BEFORE invoking the stage's upstream skill, **stop**. That reasoning belongs to the upstream skill, or to a subagent — never to the controller before the upstream invocation. Pre-flight reasoning ahead of the upstream skill is the exact failure mode this skill exists to prevent.

The one exception is Step 2.5 (plan-freshness ground-truthing), which is explicitly a *post-upstream-load, per-task* controller obligation. That is not pre-flight; it happens after the execution upstream skill is loaded and before each dispatch.
</extremely_important>

<intake>
Before any other action, classify the work in one sentence in your transcript. The class determines which stages fire.

| Work class | Stages that fire |
|---|---|
| **A — New feature / multi-task change** (most common) | Stage 0 (brainstorm if intent unclear) → **Stage 0.5 (spec-authoring → `spec.md` + clarify HALT, if the spec-kit graft is installed)** → Stage 1 (plan + gates) → **Stage 1.5 (spec-analysis gate)** → Stage 2 (execute) → Stage 3 (shake-out + finish) |
| **B — Executing an existing written plan** | Stage 1 freshness review → **Stage 1.5 (spec-analysis gate, if spec-kit artifacts exist)** → Stage 2 (execute) → Stage 3 |
| **C — Bug-fix bundle from /code-review or /security-review** | Each finding is one TDD cycle in Stage 2; Stage 3 verifies. Threat-model the diff (Stage 1 security gate) if any finding touches a security boundary |
| **D — Ad-hoc edit to a named security-boundary file** (auth/session/token, URL-allow-list, crypto) — even a one-liner, even with no plan | Stage 1 **security gate only** (threat-modeling on the diff) → implement with TDD → verify. This closes the 2026-06-03 gap. |

State your class and one-sentence reason before proceeding. If you cannot classify, the request is ambiguous — ask your human partner. Do not improvise.
</intake>

<process>

## Stage 0 — Brainstorm (Class A only, when intent is not yet concrete)

If the feature's intent, scope, or shape is not already pinned down, invoke `superpowers:brainstorming` **before** any plan exists (if a stack sub-plugin offers a brainstorming skill for this stack, prefer it — see `<stack_overrides>`). Skip only when the work is a well-specified change with no open design questions.

## Stage 0.5 — Author the spec (Class A, when the spec-kit graft is installed)

If the project has the spec-kit graft (`/spec-kit-setup` was run — `specs/` + `.specify/templates/overrides/` exist), invoke `netdust-core:spec-authoring` **before** writing the plan. It wraps `/speckit.specify` + `/speckit.clarify` to produce `specs/<feature>/spec.md` (what/why, user stories, acceptance criteria — no tech stack) and HALTS on any unresolved `[NEEDS CLARIFICATION]` (enforced mechanically by `spec-kit/gate-check.py`). The plan in Stage 1 is then written against a clarified spec, and the spec's Security-relevant-surfaces flags pre-arm the 1a threat-model gate.

Skip this stage only when the graft is not installed (fall back to brainstorm → plan directly) or for Class B/C/D.

## Stage 1 — Write the plan, with the plan-time gates baked in

Invoke `superpowers:writing-plans`. Follow its checklist. **If the spec-kit graft is installed, the plan is written from the override `plan-template.md` (the 1a/1b/1c/1f gate sections are pre-structured as `[GATE]` headings) against the Stage-0.5 `spec.md`** — `writing-plans` fills it in. Then layer these netdust gates **before task breakdown is finalized** — they are not optional add-ons, they change what tasks the plan contains:

**1a. Threat-modeling gate.** Invoke `netdust-core:threat-modeling` and embed its `## Threat model` section inline in the plan IF the feature touches any of: user-controlled URLs (webhooks, BYOK provider URLs, OAuth redirects, embed/CMS endpoints), auth/session/token surfaces, untrusted parsing (frontmatter from external sources, AI tool-call args, webhook payloads, file uploads), BYOK credentials, multi-tenancy / workspace boundaries, or any path where the server makes outbound requests to user-supplied addresses. Named assets → named attacks → named mitigations → explicit deferrals, BEFORE task breakdown. The threat model then becomes the `/code-review` convergence target (reviews verify against named mitigations instead of free-form hunting — converges in one round instead of probabilistically over many).

  - This gate ALSO fires in Class D (ad-hoc security edit). There is no plan to embed it in; run the threat model on the *diff* before committing. (2026-06-03: a `validatePublicUrl` SSRF-guard edit shipped without this because the CLAUDE.md trigger was plan-only. The guard held by luck, not by a gate. Never again.)

  - **BLOCKING — proactive, not retrospective.** The `## Threat model` must exist **BEFORE the first task is dispatched**, not be back-filled once `/code-review` surfaces findings. A threat model written *for the fix* is documentation of pain already taken, not prevention — and it does NOT earn the one-round convergence this gate exists to buy. Do not dispatch any task on a triggering surface until the section names assets → attacks → mitigations → deferrals. (Calibration: phases whose threat model was written proactively converged `/code-review` in a single round, 3–4 findings each; the one phase whose threat model was retrofitted after review — `drop-workspace-tenancy`, even though the surface plainly triggered the gate — took two rounds and 11 findings, including cross-tenant leaks the catalog *already named*. The catalog wasn't the hole; **applying it late was**.)

**1b. Architecture-invariants gate.** If the plan touches a convergence point named in the project's `ARCHITECTURE-INVARIANTS.md` (authorization, data access, live updates, error handling, entity modeling), invoke `netdust-core:architecture-invariants` and cite the touched invariants in the plan.

  - **If the doc doesn't exist yet, author it via `/architecture-invariants audit` NOW, at plan-time — not after `/code-review` finds the bypass.** The doc's whole value is letting reviews *mechanically* check "does this path skip the convergence point?" instead of re-discovering it; that value is only available if the convergence point is named *before* the code that would bypass it ships. An invariant authored after the leak is an autopsy.

  - **Front-load it for tenancy / multi-actor surfaces.** When the work touches multi-tenancy, scope-narrowing checks, cross-actor visibility, or a live-update/broadcast path that fans data out to differently-scoped consumers, author or refresh `ARCHITECTURE-INVARIANTS.md` at plan-time and name the *one* place "what may this actor see" is decided — in the stack's own idiom (a shared query/policy helper, a WP capability check, a Statamic blueprint permission; see the authorization convergence point in `netdust-core:architecture-invariants`). This is the structural twin of threat-modeling's **traverse-clause bypass** attack class: the bug is a serve/broadcast surface that skips that visibility decision. Naming the convergence point in the plan turns the next bypass into a one-line review finding instead of a multi-round leak hunt. *(Worked example — Folio: CR-8..11 were exactly this class; the fix converged the per-user visibility decision into a single helper, authored reactively after the leak when an up-front invariant would have made it a mechanical check.)*

**1c. Spec-level premise ground-truth (the cheapest catch there is).** Before the plan ships, if its core approach is "reuse existing infrastructure X (a component, endpoint, table, helper) for new data-type/use Y," READ X's source and confirm X actually accepts Y. This is the spec-level extension of Step 2.5 — it catches a *wrong architectural premise* two documents earlier than task-dispatch, where it is far cheaper. (2026-05-30, Sub-phase E: "the runs table renders through the existing TableView" survived spec + plan-expansion + handoff and was false — `agent_run` rows are walled off from `/documents`; one grep falsified it. Caught only at dispatch, forcing a mid-execution re-plan.)

**1d. Per-task and per-phase test expectations.** Per `testing-workflow`: every task gets a "Unit test: [what to verify]" line; every phase gets an "Integration gate: [what to verify across tasks]" line. A plan without these is not ready to execute.

**1e. Sibling-site audit blocks.** For any task touching a cross-cutting concern (a TS union/enum/discriminator, a SQL predicate on a JSON-extract→column field, an event scope, a cross-route guard, a closed-enum literal), add a `## Sibling-site audit` block enumerating the surface to check. (Sub-phase C.1: every cross-cutting fix had 1–2 sibling sites that needed the same change and were missed by the primary fix.)

**1f. Review-group sizing (cap the diff a reviewer must hold).** A plan groups tasks into phases, each with a per-phase integration gate (1d). But a *gate* is only a review boundary if the agent stops there — and a phase that bundles too many tasks behind ONE gate produces a diff too large for `/code-review` (human or agent) to hold, so bugs hide and review can't converge. Rule: **a single review group is ~3–4 tasks max.** When a phase exceeds that, OR contains an irreversible / security-boundary step (a schema drop, a teardown migration, an auth/token rewrite), split it into sub-group **review clusters** and declare each as an explicit STOP-AND-REVIEW marker in the plan (`── REVIEW GATE ──`), not just one gate at phase close. The executing agent (Stage 2/3) HALTS at each marker for `/integration` + `/code-review` on that cluster's diff and does not begin the next cluster until review is clear; an irreversible-migration cluster also gets `/security-review`. Without this, execution runs a long phase flat — task→task→task with no checkpoint — and the first review is an un-bisectable mega-diff. (2026-06-05, Folio drop-workspace-tenancy Phase 4: a 7-task `__system`-teardown phase had one end-of-phase gate; execution ran tasks straight through, merged two tasks into one uncommitted blob, and would have reviewed the irreversible `memberships`/`__system` drops in the same pass as refactors. Fixed by splitting into three review clusters — the contract-migration cluster got its own review. The traverse-clause disaster, CR-8..11 / 7.7× review-to-implementation time, was the same shape: too much shipped before review.)

If you are executing a plan someone else wrote (Class B), do Stage 1 as a **critical freshness review**: read the plan, run 1a–1c against it, **confirm its review-group sizing (1f) — if a phase is >~4 tasks or contains an irreversible/security step with no sub-group review marker, add the markers before starting** — and raise concerns with your human partner before starting. A plan is a snapshot of conventions at authoring time; the codebase has moved since.

## Stage 1.5 — Spec-analysis gate (pre-execution barrier)

Before dispatching ANY task, invoke `netdust-core:spec-analysis`. Two parts:

1. **Semantic consistency** — `/speckit.analyze` cross-checks spec ↔ plan ↔ tasks (every requirement covered, no orphan tasks, no contradiction). (Skip part 1 if the spec-kit graft is not installed.)
2. **Mechanical gate-presence — BLOCKING.** Run `spec-kit/gate-check.py specs/<feature>`. It FAILS (and you do NOT proceed) on: a missing `[GATE]` heading; **a security surface flagged in `spec.md` but the plan's `## Threat model` left N/A** (the proactive 1a gate unsatisfied); a task with no `[Tier A|B]` marker; a review cluster >4 tasks or an irreversible step that isn't a solo non-`[P]` task.

This is the step that turns the previously skill-honored gates (1a/1b/1d/1f) into a machine-checked barrier — it cannot be talked out of a finding. On FAIL, route each finding to its remediation (`threat-modeling` / `architecture-invariants` / `testing-workflow` / re-split clusters), fix the artifacts, re-run until green. **A green gate-check is the Stage-2 entry condition.** Even without the graft, apply 1a–1f as a manual checklist before proceeding.

## Stage 2 — Execute

**Handoff seam (spec-kit graft).** When the plan came through spec-kit, execution starts from `tasks.md` — it feeds THIS stage. **NEVER run `/speckit.implement`:** it executes tasks flat with none of the Stage-2 gates below (no threat-model verify, no per-task tiers, no review-cluster HALT, no `subagent-stop.py` backstop). spec-kit owns spec→plan→tasks; the netdust spine owns execute→verify→finish. The handoff is `tasks.md`, and nothing downstream of it runs under spec-kit.

**Step 2.0 — Pick and invoke the execution upstream skill.** State your choice and one-sentence reason first.

| Plan shape | Upstream skill |
|---|---|
| Independent tasks suitable for parallel subagents (most common) | `superpowers:subagent-driven-development` |
| Sequential tasks needing shared context, or solo execution | `superpowers:executing-plans` |

Invoke it via the Skill tool. Its content is your primary instruction set for execution from here on; this skill only adds the netdust gates below.

**Step 2.1 — Append the netdust addendum to every dispatch prompt.** For each subagent dispatch (implementer, spec reviewer, code-quality reviewer), append the block in `<addendum_for_dispatch>` VERBATIM. Do not summarize, paraphrase, or selectively include — the verbatim form is what closes the audit gap, because it demands the structured **Test-evidence + STATUS blocks** (tier, RED-first/Tier-B, seam, deferral) in the report. (Sub-phase A: a weaker one-liner produced 0/7 subagents re-invoking the testing-workflow skill — which is *why the audit must rest on the structured blocks, not on the invocation*. The blocks are verifiable in the report + commit; a Skill-tool call in a subagent transcript is not.)

**Step 2.5 — Ground-truth the dependency surface before each dispatch (plan-freshness gate).** A written plan is a *hypothesis* about the code it integrates against; the source is truth. When the plan is more than a few days old, OR it integrates against another sub-phase's / module's code (calls its functions, names its enums, scopes, env vars, table columns, event payloads), the controller MUST — for the specific task about to be dispatched, AFTER the upstream skill is loaded (never as pre-flight before Step 2.0) — Read the actual exported signatures + types + enums of that task's named dependencies and reconcile them against the plan's code samples. Bake the verified-true signatures into the dispatch prompt and flag any drift inline so the implementer builds to reality, not the stale sample. Per-task, not whole-plan up front — verify each task's surface as you reach it. If reconciliation surfaces drift big enough to change the task's shape, correct the plan (a plan-correction commit) before dispatching.

  Calibration (why this is a hard rule, not advice): FOUR consecutive Folio sub-phases hit plan-vs-source drift this catch resolved — A (Zod house-style + migration columns), C.2 (an entire provider API that didn't exist), C.3 (`recoverOrphanRuns` signature + a contaminated `db:generate` migration), Phase C (triggers carry `fm.agent`, not the plan's `target_agent_id`). Every drift was caught at controller ground-truthing and corrected before/at dispatch. Skipping it ships the drift into the subagent, which builds the wrong thing confidently.

**Step 2.6 — Gate every task close on testing-workflow's OUTPUT, not its re-invocation.** A task is not done until the subagent's report ends with the structured Test-evidence + STATUS blocks (see addendum), AND those blocks carry the testing-workflow discipline made auditable: the **tier classification** (A/B + one-sentence justification), a Tier-A **RED-first** proof (or the `no unit test: Tier B, <reason>` line), and the **deferral line** naming the risk class handed downstream.

  Those blocks — visible in the report and the commit body — ARE the gate. Do **not** require the subagent to literally re-invoke `Skill("netdust-core:testing-workflow")` once per task: the gate skill itself now states (`testing-workflow` "What the discipline actually is") that *"Re-invoking the Skill tool once per task is **not** the discipline."* The discipline is classify-at-tier → verify-at-tier → full-suite + static-analysis → record the tier/deferral lines. (The subagent reads testing-workflow **once per session** to internalize it; re-invoking it per task is the ghost ritual Sub-phase A proved was bypassable — 0/7 subagents re-invoked it and the work was still correct *because the structured blocks, not the invocation, were the real evidence*.)

If any required block or line is missing, treat the task as DONE_WITH_CONCERNS or NEEDS_CONTEXT per the upstream skill's status handling. Do not mark complete without them. The `subagent-stop.py` hook is a backstop, not the primary mechanism — the structured blocks are.

**Step 2.6b — Standards gate at every code-task close.** Alongside the testing gate, invoke `netdust-core:standards-gate`: run the project's configured linter/formatter (eslint/prettier/biome, or phpcs/php-cs-fixer) on the touched files and record a `Standards: clean | <N fixed> | n/a — no linter` line in the Test-evidence block. This closes goal #2 — coding standards become enforced, not advisory. The same `subagent-stop.py` hook backstops it: it blocks a code-editing subagent's close when a linter is configured for the project but was never run. If no linter is configured, the gate (and the backstop) no-op — do not impose a style of your own.

**Step 2.7 — Bug-fix bundles (Class C) get one TDD cycle per finding.** Each `/code-review` or `/security-review` finding is a behavior change → the Iron Law applies. Invoke `superpowers:systematic-debugging` once per bug via the Skill tool, fix one bug per cycle, re-sweep between. "I already see the fix, the phases are obvious here" is the exact rationalization the debugging skill's red-flags table names. (2026-05-30, Sub-phase F: bundling I2+I3 into one cycle drifted the process even though outcomes were sound.)

**Step 2.8 — HALT at every review-gate marker (the cluster boundary is a hard stop).** When you reach a `── REVIEW GATE ──` / STOP marker in the plan (placed per 1f), OR the end of a phase's task group, you STOP. Commit the cluster's tasks, run `/integration` on that cluster's diff, then hand back to your human partner to run `/code-review` (and `/security-review` for an irreversible/security cluster) — and do NOT begin the next task until that review is clear. The diff a reviewer holds must be one cluster (~3–4 tasks), never a whole long phase run flat. **The pull to "just keep going to the next task, I'll review at the end" is the exact failure 1f exists to prevent** — it produces an un-bisectable mega-diff and lets the agent grade a large body of its own work in one pass. Treat the marker as non-negotiable as a failing test. If the plan you're executing is a long phase with NO such markers, that is a 1f planning defect — add the markers (a plan-correction commit) before running past ~4 tasks.

## Stage 3 — Phase close, shake-out, finish

After all tasks in a phase complete and the upstream skill's final-review step is done:

1. **Phase-complete integration gate** — `testing-workflow` phase-complete (integration + acceptance), or run `/integration`.
2. **Test-effectiveness audit** — invoke `netdust-core:test-effectiveness` (Situation A) over the phase diff. The integration gate proved the tests *pass*; this proves they would *bite*. Walk the seven failure modes (stale fixture, test-world≠real-world, wire-mock leak, unmounted guard, happy-path-only/missing-denial, no-coverage, concurrency) over every dangerous path the diff introduced — for each guard, fixture, wire, mount, and timer, name the test that goes RED if it breaks, or record it `blind` and fix it. The resulting `covered`/`blind`/`fixed` manifest is the convergence target for the next step's reviewers — so shake-out verifies the gaps instead of re-discovering them. (Especially load-bearing on security-rich / multi-tenancy phases, where green-but-blind denial tests are the dominant escape — see the traverse-clause calibration.)
3. **Shake-out** — invoke `netdust-core:shake-out`, or its stack-specific replacement if the loaded sub-plugin provides one (see `<stack_overrides>`); or run `/shakeout` at spec close. This is the spec-complete / pre-merge gate: re-runs integration, runs E2E, and dispatches the reviewer agents (incl. `invariant-auditor`, plus any stack-specific reviewers the sub-plugin registers) against the full branch diff.
4. **Finish** — `superpowers:finishing-a-development-branch`.

</process>

<addendum_for_dispatch>

Append this block VERBATIM at the bottom of every implementer dispatch prompt. It supplements (does not replace) the upstream `implementer-prompt.md` template.

```
---

## Netdust addendum — mandatory close-out

Before reporting STATUS, you MUST:

1. Apply the `netdust-core:testing-workflow` discipline (read it once per
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
   configured — `netdust-core:standards-gate` (eslint + `prettier --check`
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
| "This feature doesn't really touch security, I'll skip the threat-model check" | Run the 1a trigger list literally. "BYOK + encrypted" is a property statement, not a threat model. The trigger list decides, not your gut. |
| "I'll dispatch now and write the threat model / invariant when `/code-review` flags something" | That is the retrospective failure mode (1a BLOCKING). A threat model written for the fix doesn't prevent the bug or buy one-round convergence — it documents pain already taken. The flagship `drop-workspace-tenancy` branch did exactly this and paid two review rounds for leaks the catalog already named. Write the section BEFORE the first dispatch. |
| "It's just a one-line edit to the URL allow-list, no plan needed" | That is Class D. The security gate fires on the *diff*. This is the exact 2026-06-03 gap this skill exists to close. |
| "The plan was written this week, it's fresh enough" | Conventions and signatures drift within a single sub-phase. Step 2.5 is per-task and mandatory when the task integrates against other code. |
| "We'll reuse the existing X for this, obviously it fits" | Read X's source NOW (Stage 1c). The TableView-for-runs premise survived three documents and was false. |
| "Let me grep the codebase to understand the task before invoking the upstream skill" | The upstream skill IS how you understand the task. Invoke it first. (Step 2.5 ground-truthing is the one allowed post-load read.) |
| "I already know what subagent-driven-development says" | Skills evolve. Invoke and read the current version every time. |
| "Skipping the verbatim addendum saves a few lines" | The verbatim form is what closes the audit gap. Skipping it reverts to honor-system. |
| "I see the fix for all three review findings, I'll bundle them" | One TDD cycle per finding, one systematic-debugging invocation per bug. Bundling drifts the process. |
| "Two-stage review is ceremony for a simple task" | The review loop catches what TDD doesn't. Do not skip it. |
| "I'll just finish the rest of the phase's tasks, then review the whole thing at the end" | That's the un-bisectable mega-diff (1f / Step 2.8). HALT at the review-gate marker. A reviewer must hold one cluster (~3–4 tasks), not a 7-task phase. Irreversible-migration clusters review alone. |
| "I'll classify the tier and record the deferral line after the commit, not before reporting" | Order is: verify-at-tier → run full suite + static analysis → report with the tier + RED-first/Tier-B + deferral blocks. The blocks must be in the report; a commit with no tier/deferral evidence bypasses the gate. (Re-invoking the testing-workflow Skill tool per task is NOT required — the structured blocks are the evidence.) |
| "I'll just run `/speckit.implement` to execute the tasks" | That bypasses every Stage-2 gate — threat-model verify, per-task tiers, review-cluster HALT, the `subagent-stop` backstop. The handoff is `tasks.md`; Stage 2 executes it under the netdust spine. NEVER `/speckit.implement`. |
| "`/speckit.analyze` passed, I'll start dispatching" | analyze is only half of Stage 1.5. Run `gate-check.py` (the mechanical part) — it is what catches a skipped threat model, an un-tiered task, or an oversized cluster. A green checker is the Stage-2 entry condition. |
| "Tests are green, the task is done" | Tests are half the close. Run `standards-gate` too (Step 2.6b) and record the `Standards:` line — or the `subagent-stop` hook blocks your close when a linter is configured. |

</red_flags>

<success_criteria>

This skill has succeeded when:

1. The work was classified (A/B/C/D) in the transcript before any action.
2. For any feature touching the 1a trigger surface, a `## Threat model` exists (in the plan, or run on the diff for Class D) BEFORE implementation.
3. For any feature touching a named convergence point, the relevant invariants were cited.
4. Any "reuse X for Y" premise was ground-truthed against X's source before the plan shipped.
5. The execution upstream skill was invoked via the Skill tool and its checklist followed.
6. Every implementer dispatch contained the verbatim addendum; every implementer report ended with the structured Test-evidence + STATUS blocks carrying the tier classification, the Tier-A RED-first proof (or the `no unit test: Tier B` line), and the deferral line. (The auditable evidence is those blocks + the commit body — NOT a per-task `Skill("netdust-core:testing-workflow")` re-invocation, which the gate skill itself has retired.)
7. Step 2.5 ground-truthing was performed per-task for every task integrating against other code.
8. Phase close handed off to `netdust-core:shake-out` and then `superpowers:finishing-a-development-branch`.
9. When the spec-kit graft is installed: a clarified `spec.md` existed before the plan (Stage 0.5), and `spec-analysis`'s `gate-check.py` was GREEN before any task dispatch (Stage 1.5). `/speckit.implement` was never run.
10. Every code-task close recorded a `Standards:` line (`clean | N fixed | n/a — no linter`); the `subagent-stop` standards backstop did not have to fire.

If any gate that *should* have fired (per the class + trigger lists) did not, the skill failed at its specific job — even if the code shipped correctly. This skill exists for *gate-coverage durability*; the upstream skills handle code correctness.

</success_criteria>

<integration>

| Skill | Relationship |
|---|---|
| `superpowers:brainstorming` | **STAGE 0.** Front-loaded when intent is unclear. A stack sub-plugin's brainstorming skill replaces it when loaded (see `<stack_overrides>`). |
| stack sub-plugins (`netdust-wp`, `netdust-statamic`, future `netdust-<stack>`) | **OVERRIDE LAYER.** When loaded for the project, their stage-specific skills / reviewers / test runners replace the generics named above. This skill never hardcodes their names — see `<stack_overrides>`. |
| `superpowers:writing-plans` | **STAGE 1.** The plan this skill wraps the gates around. With the spec-kit graft, written from the override `plan-template.md` so the gates are pre-structured. |
| `netdust-core:spec-authoring` | **STAGE 0.5.** Wraps `/speckit.specify` + `/speckit.clarify`; HALTs on unresolved `[NEEDS CLARIFICATION]`. Produces the `spec.md` Stage 1 plans against. |
| `netdust-core:spec-analysis` | **STAGE 1.5.** Wraps `/speckit.analyze` + the mechanical `spec-kit/gate-check.py` — the pre-execution barrier that makes the 1a/1b/1d/1f gates machine-checked, not skill-honored. |
| `netdust-core:standards-gate` | **STAGE 2 GATE (Step 2.6b).** Runs the project linter on touched files at each code-task close; records the `Standards:` line; backstopped by `subagent-stop.py`. Closes goal #2 (enforced coding standards). |
| `netdust-core:constitution-bridge` | **SETUP.** Generates the spec-kit constitution as a view over RULES/SOUL/invariants; declares the standard `standards-gate` enforces. No governance fork. |
| spec-kit graft (`spec-kit/` + `/spec-kit-setup`) | **GRAFT MECHANISM.** Override templates bake the gates into spec-kit's spec/plan/tasks; `gate-check.py` verifies them. Keystone invariant: handoff is `tasks.md`, `/speckit.implement` is never run. |
| `netdust-core:threat-modeling` | **STAGE 1 GATE (1a).** Fired by trigger list, at plan-time OR on an ad-hoc security diff (Class D). Becomes the /code-review convergence target. |
| `netdust-core:architecture-invariants` | **STAGE 1 GATE (1b).** Fired when a convergence point is touched. |
| `superpowers:subagent-driven-development` | **STAGE 2 — primary branch.** Parallel-independent tasks. |
| `superpowers:executing-plans` | **STAGE 2 — secondary branch.** Sequential / solo execution. |
| `netdust-core:testing-workflow` | **STAGE 2 MANDATORY GATE.** Per-task close (the addendum's structured tier + RED-first/Tier-B + deferral blocks ARE the auditable gate — not a per-task Skill re-invocation) + phase-complete. |
| `netdust-core:test-effectiveness` | **STAGE 3 GATE.** Phase-close audit (Situation A), after the integration gate and before shake-out: the integration gate proved tests *pass*; this proves they would *bite*. Walks the seven green-but-blind failure modes over the phase diff; its `covered`/`blind`/`fixed` manifest is the shake-out + `/code-review` convergence target. Sibling to testing-workflow (write-time/per-task) at audit-time/per-phase altitude. |
| `superpowers:systematic-debugging` | **STAGE 2 (Class C).** One invocation per bug. |
| `netdust-core:shake-out` | **STAGE 3.** Spec-close, after upstream final-review. |
| `superpowers:finishing-a-development-branch` | **STAGE 3.** After shake-out. |
| `netdust-core:ntdst-execute-with-tests` | **DELETED — fully absorbed here.** The old execution-only skill is gone (2026-06-05). Its triggers ("execute the plan", "work the plan") now resolve to THIS skill, which does everything it did plus the planning gates. Older handoff docs that name it need no change — the trigger phrases route here. |
| netdust-core `subagent-stop.py` hook | **BACKSTOP.** Surfaces a reminder when a subagent finishes without the testing-workflow evidence. Backstop, not primary mechanism — the structured Test-evidence + STATUS blocks (tier / RED-first / deferral) the addendum demands are. |

**Calibration data behind these rules** (all from Folio Phase 3):
- *Verbatim addendum:* Sub-phase A — 0/7 subagents re-invoked the testing-workflow skill under a weaker one-liner, yet the work was correct. The lesson the harness took from this (2026-06-04): the audit trail must rest on the **structured Test-evidence + STATUS blocks** the addendum demands, not on a per-task Skill-tool re-invocation — which is unverifiable from git and which the testing-workflow gate skill has itself retired.
- *Step 2.5 plan-freshness:* caught plan-vs-source drift 4 consecutive sub-phases (A, C.2, C.3, Phase C).
- *Stage 1c spec-premise:* Sub-phase E — a false "reuse TableView" premise survived spec + plan + handoff.
- *Stage 1a on ad-hoc diffs (Class D):* 2026-06-03 — a security-guard edit shipped without threat-modeling because the trigger was plan-only.

</integration>
