---
name: harnessed-development
description: The single entry point for any code-changing work in a Netdust project — it scales the ceremony to the work via a class dial at intake, it does NOT impose the full sequence on everything. A big feature gets brainstorm → write-plan (with threat-modeling + architecture-invariants when triggered) → execute (subagent/TDD + mandatory testing-workflow at every task close) → shake-out → finish-branch (Class A); a small self-contained change goes STRAIGHT to one TDD cycle — red/green only, no plan, no shake-out — while still recording the per-task test evidence (Class E); a review-finding bundle is one TDD cycle per finding (Class C); a security-boundary one-liner adds just the threat-model gate (Class D). Triggers on "build a feature", "start a feature", "implement X", "work the plan", "execute the plan", "execute todo.md", "start building", "do this properly", "the whole harness", "ship X", "fix the code-review findings", "address the review feedback" — AND on smaller asks that still change code: "tweak X", "fix this bug", "small change to X", "refactor this function", "add a helper for X", "just change X". Use it for the tweak too — it will route the tweak to the light path (Class E), not drag it through a plan. The intake class table is the first thing it does; that is the dial. NOT for read-only questions, pure formatting/whitespace, dependency bumps, prose, or research — those change no behavior and need no harness. Stack-agnostic; defers to the loaded stack sub-plugin for stack-specific skills, reviewers, and test runners. Replaces the deleted `ntdst-execute-with-tests` skill (its "execute the plan" / "work the plan" triggers resolve here).
---

<objective>
Make one truth hold: **if this skill was invoked, every gate the work's class warrants fired — and none was left to "remember to do it."** The skill scales ceremony to the work via the intake class dial (a tweak is Class E: red/green only; a feature is Class A: the full sequence) — but within the chosen class, each warranted gate fires because the skill sequences it, not because a prose instruction in CLAUDE.md was honored. The win is not "always run everything"; it is "never silently skip a gate the class called for." Threat modeling, invariants, per-task tests, two-stage review, shake-out: each fires when its class + triggers call for it, structurally.

This skill enforces two gates the upstream superpowers skills do not:

1. **The planning gates fire from the spine, not from prose.** `threat-modeling` and `architecture-invariants` are sequenced here, so they engage whenever their triggers match — instead of relying on a CLAUDE.md reminder a session can skip. (A security-boundary edit once shipped without a threat model because that reminder was keyed only to "writing a plan." This skill makes the gate structural — see Class D.)

2. **Every task close is gated on an INDEPENDENTLY-authored test, auditably.** `testing-workflow` is mandatory at each task close — and the test that gates the task is written by a separate `test-author` agent BEFORE the implementer touches the code, so no agent grades its own homework. The test-author reports the RED contract; the implementer reports the GREEN on that same, unweakened test. Both structured blocks are visible in the transcript and the two are separate commits, so the discipline — and its independence — is verifiable from git, not honor-system. (See `<test_dev_split>` for why the implementer authoring its own test was the flaw this closes.)

Everything in between — brainstorming, plan structure, TDD red→green, dispatch shape, two-stage review, status handling, escalation — belongs to the upstream superpowers skills. This skill is a **sequencer**: at each stage it loads the right upstream skill and adds the netdust-specific gate around it. Do NOT duplicate upstream content.

This skill is **stack-agnostic by design** — it names only generic, cross-stack skills. See `<stack_overrides>` for how stack-specific skills replace the generics.
</objective>

<how_each_gate_is_actually_enforced>
Be honest about enforcement strength — the gates are NOT equally hard, and assuming they are is itself a failure mode:

- **The per-task testing gate is HOOK-ENFORCED.** `subagent-stop.py` (a real SubagentStop hook) blocks a subagent that edited code from stopping without a test command having actually run. This is the one gate backed by code, not just prose — it is why it reliably fires. It backstops BOTH halves of the split: the `test-author` must have run its RED test, and the `implementer` must have run the suite. (Even so, the *auditable* evidence is the structured blocks in the reports/commits, not the hook — the hook is the backstop.)
- **The test/dev split (authorship independence) is SEQUENCER-ENFORCED, not hook-enforced.** The hook can confirm a test *ran*; it cannot confirm the implementer didn't *write* the test it ran — a single SubagentStop invocation sees one subagent's transcript, not the pair. What guarantees independence is the DISPATCH ORDER this skill mandates: the controller dispatches the `test-author` first, receives the RED_READY handoff, and only then dispatches the `implementer` with that test already committed to the tree. The two separate commits (test predates code, different authors) are the audit trail. Do not collapse them into one dispatch to save a round-trip — that silently reverts to self-grading, and nothing will hard-stop you.
- **The plan-time gates (threat-modeling 1a, architecture-invariants 1b, feature-acceptance 1g) are SEQUENCER-ENFORCED, not hook-enforced.** There is no hook that blocks a plan lacking its `## Threat model`. They fire because THIS skill sequences them and the BLOCKING prose demands them before the first dispatch, and they are caught-if-missed at `/code-review` + `/shakeout` (the threat model / acceptance matrix are the review convergence targets). That is layered defense — sequencer fires it, review verifies it — but it is honor-system at the point of authoring. Do not assume a hook will stop you; the discipline is yours to apply, and a skipped plan-time gate only surfaces one stage later (more expensive). This is a known gap, deliberately not over-built (a plan has no single mechanical "close" moment to hook).

The practical upshot: treat the test/dev split and the plan-time gates with the same seriousness as the hook-backed testing gate, precisely BECAUSE nothing will hard-stop you if you skip them.
</how_each_gate_is_actually_enforced>

<test_dev_split>
**The flaw this closes.** The original harness had ONE agent — the implementer — write the code AND its own Tier-A test AND self-report the Test-evidence that gated the task. RED-first softened it, but the same agent still authored both sides: the test drifts to fit the code it was written against, the denial path quietly goes missing, and a risky guard gets self-classified "just wiring, Tier B" to dodge a test — and the agent that benefits from the skip is the one who judged it. Grading your own homework.

**The fix — a per-task test/dev split.** Test authorship and execution are owned by a separate `test-author` agent, dispatched BEFORE the implementer for the same task:

1. `test-author` classifies the tier (from the acceptance criteria + threat model, NOT the code — which for a new symbol doesn't exist yet), and for Tier A writes the RED-first behavioral test including the denial path. For a brand-new symbol it creates only the minimal **signature shell** (declaration + sentinel body) so the RED is behavioral, not "module not found" — never the logic. It proves RED, commits the test + shell as its own commit, and hands over a `## Test contract` block with `STATUS: RED_READY`.
2. `implementer` receives that failing, contract-derived test as an **immutable input**. It drives the test to GREEN — filling the shell / modifying the symbol — WITHOUT editing, weakening, deleting, or skipping the contract test. It may ADD edge tests. If it thinks the test is wrong, it escalates `NEEDS_CONTEXT`; it does not rewrite the test to pass.

The gate is now the PAIR: the test-author's RED authorship + the implementer's GREEN on the same unweakened test, in two separate commits. This holds at every class that writes code, including **Class E** — a small tweak is still `test-author → implementer` (one cycle, no plan, no shake-out), because self-grading is just as easy on a one-line change. The ONE narrow exception: a genuinely trivial inline Class E where dispatching two agents is disproportionate — there the CONTROLLER acts as the independent test-author (writes + RED-proves the test) and dispatches only the implementer to green it; the independence still holds because the coder still isn't the grader. Record that as `Contract test author: self — Class E inline split, controller authored RED`.
</test_dev_split>

<stack_overrides>
**Standing rule — this skill names only generic skills; a loaded stack sub-plugin replaces them.**

This skill lives in `netdust-agent` and is stack-agnostic. The stages below reference generic, cross-stack skills (`superpowers:*` bases plus the local netdust-agent harness/craft skills). When a stack sub-plugin is installed for the project at hand (e.g. `netdust-wp`, `netdust-statamic`, or any future `netdust-<stack>`), and it offers a more specific skill, reviewer, or test runner for a stage, **use the stack-specific one in place of the generic** — same stage, same gate, sharper tool.

How to apply it, at each stage:
- **Brainstorm / plan / domain conventions** — if the stack sub-plugin provides a domain skill for the artifact you're designing (a framework-architecture, data-layer, or patterns skill), invoke it alongside or instead of the generic.
- **Plan requirements** — if the stack sub-plugin provides a *plan-requirements* skill (one that injects mandatory stack-specific requirement sections into the plan, the way `threat-modeling` injects `## Threat model`), fire it at Stage 1 alongside threat-modeling/invariants so its sections are baked in **before task breakdown**. This moves stack-specific security/pattern enforcement upstream into the plan, so review verifies against named items instead of hunting. (On WordPress that skill injects WP-security four-pillar + ntdst-core layering requirements; the core skill never names it — the override rule picks it up.)
- **Testing** — `testing-workflow` already auto-detects the stack and picks the right unit/integration runner. Nothing to override manually; it does the right thing per project.
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
| **E — Small self-contained change, no plan warranted** (a logic tweak, a small helper, a localized refactor, a single bug not from a review) — touches **one area**, no design questions, NOT a security-boundary file (that's D) | **Go straight to Stage 2 as one TDD cycle — but keep the test/dev split.** No brainstorm, no plan, no spec, no shake-out. The per-task testing gate STILL applies AND stays independent: an agent OTHER than the coder authors the RED test — either dispatch `test-author → implementer`, or (for a genuinely trivial inline change) the controller authors + RED-proves the test itself and dispatches only the implementer to green it. Classify the tier (logic/parsing/branching → Tier A RED-first; pure glue/rename/formatting → Tier B/no-op) and record the evidence blocks. The `subagent-stop` hook still backstops it. Verify with the suite + `/integration` on the diff. |

State your class and one-sentence reason before proceeding. If you cannot classify, the request is ambiguous — ask your human partner. Do not improvise.

**The dial, in one line:** E = red/green only · C = TDD-cycle-per-finding · D = + security gate · B = + freshness review · A = the full sequence. Match the class to the *actual* work — a tweak is Class E, not a small Class A. Over-calling the class wastes ceremony; under-calling A/D (skipping a plan or a security gate that was warranted) is the dangerous direction. When the change is genuinely small and self-contained, **E is not cutting a corner — it is the correct class.** The one rule that never relaxes with class: anything touching a named security-boundary file is D (never E), and any non-trivial logic still gets its Tier-A RED test.
</intake>

<process>

<craft_routing>
This skill sequences GATES (when/whether). At each stage it also reaches for a CRAFT skill (the how-to). The craft skill layers the harness contract on top of its superpowers base — load it when you reach that step.

**The principle:** GATES decide *whether / when* a step fires; CRAFT skills are the *how-to* you load to implement that step's work WELL. Craft **layers on** its superpowers base, never replaces it — a craft skill takes the upstream process skill as its spine and adds the netdust-agent contract on top. Running the gate without loading the craft skill clears the checkpoint but does the work blind; loading the craft without the gate does the work well but unguarded. You need both at each step.

| Stage / step | Gate (when/whether) | Craft skill to load (how-to) |
|---|---|---|
| Stage 0 — brainstorm | `superpowers:brainstorming` | `refining-ideas` (sharpen a vague idea: divergent→convergent) |
| Stage 1 — write the plan | `superpowers:writing-plans` | `sourcing-from-docs` (when a plan premise rests on external lib/API behavior — verify via context7 before asserting; pairs with Stage 1c) |
| Stage 1 — API / boundary design | `architecture-invariants` (1b) | `designing-apis` (contract-first; name the convergence points the invariant doc will check) |
| Stage 2 — author the test (test-author, BEFORE the implementer) | `testing-workflow` (per-task tier gate, Step 2.6) | `writing-tests` (Tier-A RED-first on top of `superpowers:test-driven-development`) |
| Stage 2 — green the test (implementer) | `testing-workflow` (recognize the tier; do not re-author) | `superpowers:test-driven-development` (green the handed-over RED without weakening it) |
| Stage 2 — execute, UI task | `feature-acceptance` (1g matrix) | `building-frontend` (component/state/a11y/responsive; build the empty/error/loading edge states the matrix drives) |
| Stage 2 — execute, any commit | — | `versioning-with-git` (atomic commit-per-task; STATUS / Test-evidence in the commit body) |
| Stage 2 — ground-truth (Step 2.5 / Stage 1c) | — | `sourcing-from-docs` (external dep) + `engineering-context` (sibling code from the 3-layer memory) |
| Stage 1→2 boundary — a big decision | — | `doubting-decisions` (adversarial fresh-context attack on the plan's key decision before committing work) |
| Any stage — browser drive / inspect | `feature-acceptance` / `superpowers:systematic-debugging` | `driving-the-browser` (HOW to operate Chrome; feature-acceptance owns WHAT to drive) |
| Stage 3 — review | `/code-review` + reviewer agents | `simplifying-code` (reduce complexity, behavior preserved — suite green before and after) |
| Stage 3 — finish / deploy | `superpowers:finishing-a-development-branch` | `deploying` (route to `/deploy` + dev-stack; never prod without explicit confirmation) |
| Stage 3 — spec-close (after finish) | `compounding` | `compounding` (harvest what the spec taught into CODE-MAP + a scoped skill-audit; spec-close only, NOT per sub-phase) |
| Session start / task switch | — | `engineering-context` (pack the right context from the existing 3-layer memory model) |

If a stack sub-plugin offers a sharper craft skill for a stage (a stack-specific frontend, data, or deploy how-to), prefer it — same rule as `<stack_overrides>`.
</craft_routing>

<stage_personas>
Each stage has an agent PERSONA you can dispatch to own it. A persona is the *who* (role + judgment + dispatch context) that LOADS the stage's gates + craft skills — it does not duplicate them. Dispatch the persona for the stage, or run the stage inline yourself; the gates fire the same either way. The personas are not optional decoration — they ARE how the stage's work is dispatched when you fan out:

| Stage | Persona to dispatch | What it loads / owns |
|---|---|---|
| Stage 0→1 — request → gated plan | `planner` | brainstorming/refining-ideas → writing-plans → the plan-time gates (1a–1g) |
| Stage 2 — author the test (per task, FIRST) | `test-author` (one per task, before the implementer) | testing-workflow/writing-tests; owns the tier decision + the RED-first behavioral test (+ signature shell); closes with the `## Test contract` block + `RED_READY` |
| Stage 2 — green the test (per task, SECOND) | `implementer` (one per task, often parallel across independent tasks) | test-driven-development, building-frontend, versioning-with-git; greens the test-author's RED without weakening it; closes with the Test-evidence + STATUS blocks |
| Stage 3 — whole-diff review | `reviewer` (generalist, five-pillar) + the specialist reviewers | reviews the diff against the threat model, invariants, and test-effectiveness manifest |
| Stage 3 — exercise the artifact | `shakeout-qa` | drives the acceptance matrix through the real browser / un-mocked wire; compiles the bug manifest |

The Stage-2 pair is a hard ordering: `test-author` (RED) → `implementer` (GREEN), per task, two separate commits. Never dispatch the implementer for a task whose RED test doesn't exist yet, and never let one agent do both — that is the self-grading loop `<test_dev_split>` removes.

At Stage 3 the `/shakeout` command auto-dispatches `reviewer` + the four specialists in parallel, after `shakeout-qa` (or the inline shake-out sweep) has exercised the artifact. See `/shakeout`.
</stage_personas>

## Stage 0 — Brainstorm (Class A only, when intent is not yet concrete)

If the feature's intent, scope, or shape is not already pinned down, invoke `superpowers:brainstorming` **before** any plan exists (if a stack sub-plugin offers a brainstorming skill for this stack, prefer it — see `<stack_overrides>`). Skip only when the work is a well-specified change with no open design questions.

## Stage 0.5 — Author the spec (Class A, when the spec-kit graft is installed)

If the project has the spec-kit graft (`/spec-kit-setup` was run — `specs/` + `.specify/templates/overrides/` exist), invoke `netdust-agent:spec-authoring` **before** writing the plan. It wraps `/speckit.specify` + `/speckit.clarify` to produce `specs/<feature>/spec.md` (what/why, user stories, acceptance criteria — no tech stack) and HALTS on any unresolved `[NEEDS CLARIFICATION]` (enforced mechanically by `spec-kit/gate-check.py`). The plan in Stage 1 is then written against a clarified spec, and the spec's Security-relevant-surfaces flags pre-arm the 1a threat-model gate.

Skip this stage only when the graft is not installed (fall back to brainstorm → plan directly) or for Class B/C/D.

## Stage 1 — Write the plan, with the plan-time gates baked in

Invoke `superpowers:writing-plans`. Follow its checklist. **If the spec-kit graft is installed, the plan is written from the override `plan-template.md` (the 1a/1b/1c/1f gate sections are pre-structured as `[GATE]` headings) against the Stage-0.5 `spec.md`** — `writing-plans` fills it in. Then layer these netdust gates **before task breakdown is finalized** — they are not optional add-ons, they change what tasks the plan contains:

**Stack plan-requirements (override layer).** If a stack sub-plugin is loaded and provides a plan-requirements skill (see `<stack_overrides>`), invoke it HERE, alongside 1a/1b — it injects the stack's mandatory requirement sections (e.g. on WordPress: WP-security four pillars per data-flow + ntdst-core layering per new class) into the plan before task breakdown, so those become per-task acceptance criteria and the `/code-review` + drift-reviewer convergence target. Core never names the skill; the override rule resolves it per project.

**1a. Threat-modeling gate.** Invoke `threat-modeling` and embed its `## Threat model` section inline in the plan IF the feature touches any of: user-controlled URLs (webhooks, BYOK provider URLs, OAuth redirects, embed/CMS endpoints), auth/session/token surfaces, untrusted parsing (frontmatter from external sources, AI tool-call args, webhook payloads, file uploads), BYOK credentials, multi-tenancy / workspace boundaries, or any path where the server makes outbound requests to user-supplied addresses. Named assets → named attacks → named mitigations → explicit deferrals, BEFORE task breakdown. The threat model then becomes the `/code-review` convergence target (reviews verify against named mitigations instead of free-form hunting — converges in one round instead of probabilistically over many).

  - This gate ALSO fires in Class D (ad-hoc security edit). There is no plan to embed it in; run the threat model on the *diff* before committing. (2026-06-03: a `validatePublicUrl` SSRF-guard edit shipped without this because the CLAUDE.md trigger was plan-only. The guard held by luck, not by a gate. Never again.)

  - **BLOCKING — proactive, not retrospective.** The `## Threat model` must exist **BEFORE the first task is dispatched**, not be back-filled once `/code-review` surfaces findings. A threat model written *for the fix* is documentation of pain already taken, not prevention — and it does NOT earn the one-round convergence this gate exists to buy. Do not dispatch any task on a triggering surface until the section names assets → attacks → mitigations → deferrals. (Calibration: phases whose threat model was written proactively converged `/code-review` in a single round, 3–4 findings each; the one phase whose threat model was retrofitted after review — `drop-workspace-tenancy`, even though the surface plainly triggered the gate — took two rounds and 11 findings, including cross-tenant leaks the catalog *already named*. The catalog wasn't the hole; **applying it late was**.)

**1b. Architecture-invariants gate.** If the plan touches a convergence point named in the project's `ARCHITECTURE-INVARIANTS.md` (authorization, data access, live updates, error handling, entity modeling), invoke `architecture-invariants` and cite the touched invariants in the plan.

  - **If the doc doesn't exist yet, author it via `/architecture-invariants audit` NOW, at plan-time — not after `/code-review` finds the bypass.** The doc's whole value is letting reviews *mechanically* check "does this path skip the convergence point?" instead of re-discovering it; that value is only available if the convergence point is named *before* the code that would bypass it ships. An invariant authored after the leak is an autopsy.

  - **Front-load it for tenancy / multi-actor surfaces.** When the work touches multi-tenancy, scope-narrowing checks, cross-actor visibility, or a live-update/broadcast path that fans data out to differently-scoped consumers, author or refresh `ARCHITECTURE-INVARIANTS.md` at plan-time and name the *one* place "what may this actor see" is decided — in the stack's own idiom (a shared query/policy helper, a WP capability check, a Statamic blueprint permission; see the authorization convergence point in `architecture-invariants`). This is the structural twin of threat-modeling's **traverse-clause bypass** attack class: the bug is a serve/broadcast surface that skips that visibility decision. Naming the convergence point in the plan turns the next bypass into a one-line review finding instead of a multi-round leak hunt. *(Worked example — Folio: CR-8..11 were exactly this class; the fix converged the per-user visibility decision into a single helper, authored reactively after the leak when an up-front invariant would have made it a mechanical check.)*

**1c. Spec-level premise ground-truth (the cheapest catch there is).** Before the plan ships, if its core approach is "reuse existing infrastructure X (a component, endpoint, table, helper) for new data-type/use Y," READ X's source and confirm X actually accepts Y. This is the spec-level extension of Step 2.5 — it catches a *wrong architectural premise* two documents earlier than task-dispatch, where it is far cheaper. (2026-05-30, Sub-phase E: "the runs table renders through the existing TableView" survived spec + plan-expansion + handoff and was false — `agent_run` rows are walled off from `/documents`; one grep falsified it. Caught only at dispatch, forcing a mid-execution re-plan.)

**1d. Per-task and per-phase test expectations.** Per `testing-workflow`: every task gets a "Unit test: [what to verify]" line; every phase gets an "Integration gate: [what to verify across tasks]" line. A plan without these is not ready to execute.

**1e. Sibling-site audit blocks.** For any task touching a cross-cutting concern (a TS union/enum/discriminator, a SQL predicate on a JSON-extract→column field, an event scope, a cross-route guard, a closed-enum literal), add a `## Sibling-site audit` block enumerating the surface to check. (Sub-phase C.1: every cross-cutting fix had 1–2 sibling sites that needed the same change and were missed by the primary fix.)

**1g. Acceptance-flow matrix (does the FEATURE behave, not just the code).** A plan-time content gate alongside 1a/1b — invoke `feature-acceptance` (Situation A) and embed an `## Acceptance flows` matrix in the plan IF the work adds or changes a **user-facing feature** (a view, a form, a wizard, an interactive flow, a CRUD surface, an endpoint a client/agent will drive). One row per intended-use flow; each row's **Edges** column MANDATORY — enumerate the six edge classes (empty/zero state, denied actor, wrong-order/re-entry, concurrent/double, boundary value, mid-flow failure) or name why one is excluded. A flow with no edges is an incomplete row. This is the behavioral twin of the threat model: it's written before code and becomes the contract `/shakeout` *drives* (Stage 3 / Step after test-effectiveness) — UI flows through the real browser, backend flows through the un-mocked wire — instead of shake-out re-discovering broken flows free-form. (Calibration: Folio's empty-state-toggle blank-editor, the route-vs-service guard gap, the double-submit collision, the no-rollback client divergence, and the jsdom-masked InlineEdit race ALL shipped past a green, tier-disciplined suite — each an intended-use edge nobody drove through the real surface.)

**1f. Review-group sizing (cap the diff a reviewer must hold).** A plan groups tasks into phases, each with a per-phase integration gate (1d). But a *gate* is only a review boundary if the agent stops there — and a phase that bundles too many tasks behind ONE gate produces a diff too large for `/code-review` (human or agent) to hold, so bugs hide and review can't converge. Rule: **a single review group is ~3–4 tasks max.** When a phase exceeds that, OR contains an irreversible / security-boundary step (a schema drop, a teardown migration, an auth/token rewrite), split it into sub-group **review clusters** and declare each as an explicit STOP-AND-REVIEW marker in the plan (`── REVIEW GATE ──`), not just one gate at phase close. The executing agent (Stage 2/3) HALTS at each marker for `/integration` + `/code-review` on that cluster's diff and does not begin the next cluster until review is clear; an irreversible-migration cluster also gets `/security-review`. Without this, execution runs a long phase flat — task→task→task with no checkpoint — and the first review is an un-bisectable mega-diff. (2026-06-05, Folio drop-workspace-tenancy Phase 4: a 7-task `__system`-teardown phase had one end-of-phase gate; execution ran tasks straight through, merged two tasks into one uncommitted blob, and would have reviewed the irreversible `memberships`/`__system` drops in the same pass as refactors. Fixed by splitting into three review clusters — the contract-migration cluster got its own review. The traverse-clause disaster, CR-8..11 / 7.7× review-to-implementation time, was the same shape: too much shipped before review.)

**1h. Review-tier intensity (match the artillery to the risk).** 1f decides *where* the review boundaries are (cluster size); this decides *how heavy* the review at each boundary is. A review unit is **one cluster** (at a `── REVIEW GATE ──`) or **the whole branch diff** (at spec-close). Tier is decided per review unit from the **same surface triggers the threat-modeling gate (1a) already names** — do not invent a second trigger list. The planner assigns a **provisional tier per cluster** at plan-time (it goes in the plan beside the `── REVIEW GATE ──` marker); the controller restates and may override it at the gate with justification.

| Tier | When (per review unit) | Review intensity |
|---|---|---|
| **FULL** | The diff touches **any 1a trigger surface** (auth/session/token, URL allow-lists, crypto, untrusted parsing, tenancy/workspace boundaries, outbound requests to user-supplied addresses), OR a named **architecture invariant**, OR the **data layer / migrations**. | Current behavior — the full panel. At a cluster gate: all finder angles in parallel + `security-sentinel` mandatory. At spec-close: the full 5-persona panel (`reviewer` + `code-simplicity-reviewer` + `security-sentinel` + `performance-oracle` + `invariant-auditor`; +`ntdst-drift-reviewer` on WP). |
| **STANDARD** | Multi-file **behavior changes outside** those surfaces — typical UI features, route changes, component work. | 2 finder angles (line-by-line + cross-file tracer) + `code-simplicity-reviewer`, plus the **feature-acceptance browser pass**. **No `security-sentinel`. No `performance-oracle`** unless the diff touches a hot path named in `CODE-MAP.md`. Spec-close panel = `reviewer` + `invariant-auditor` only. |
| **LIGHT** | Doc-only, copy, config, skill-body edits. | A single generalist pass (`reviewer`). No fan-out. |

**One-way escalation only.** Any finder or reviewer that surfaces a finding on a 1a surface **immediately promotes the unit to TIER FULL** (re-dispatch the missing FULL-tier reviewers on that unit). Never de-escalate mid-review — a unit's tier only ratchets up.

**`/security-review` is independent of tier.** The existing rule stands: `/security-review` is mandatory whenever the **threat-modeling gate fired at plan time** (a `## Threat model` exists for this work), regardless of the review unit's tier. Tier governs the *finder/persona fan-out*; it never cancels the security-review obligation a plan-time threat model created.

If you are executing a plan someone else wrote (Class B), do Stage 1 as a **critical freshness review**: read the plan, run 1a–1c + 1g against it, **confirm its review-group sizing (1f) — if a phase is >~4 tasks or contains an irreversible/security step with no sub-group review marker, add the markers before starting — and confirm each cluster's provisional review tier (1h), adding one where missing** — and raise concerns with your human partner before starting. A plan is a snapshot of conventions at authoring time; the codebase has moved since.

## Stage 1.5 — Spec-analysis gate (pre-execution barrier)

Before dispatching ANY task, invoke `netdust-agent:spec-analysis`. Two parts:

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
| **No plan — a single small change (Class E)** | None. Do the one cycle directly, but KEEP THE SPLIT: `test-author → implementer` (or controller-authored RED → implementer for a trivial inline change). `superpowers:test-driven-development` is the base; record both the `## Test contract` and the Test-evidence blocks. |

Invoke it via the Skill tool. Its content is your primary instruction set for execution from here on; this skill only adds the netdust gates below.

**Every task in this stage is a PAIR of dispatches** (`<test_dev_split>`): first `test-author` (writes the RED test), then `implementer` (greens it). Independent tasks parallelize as pairs — dispatch several test-authors, then their implementers — but within one task the order never inverts and the two are never fused into one agent. The natural shape is a per-task pipeline: `test-author` stage → `implementer` stage, per task.

**Step 2.1 — Append the right netdust addendum to every dispatch prompt.** There are now TWO Stage-2 dispatch addenda in `<addendum_for_dispatch>`: the **test-author addendum** (for the RED-authoring dispatch) and the **implementer addendum** (for the GREEN dispatch). Append the matching one VERBATIM to each dispatch; append the implementer addendum to reviewer dispatches' STATUS-only variant as before. Do not summarize, paraphrase, or selectively include — the verbatim form is what closes the audit gap, because it demands the structured blocks (the `## Test contract` from the test-author; the Test-evidence + STATUS from the implementer). (Sub-phase A: a weaker one-liner produced 0/7 subagents re-invoking the testing-workflow skill — which is *why the audit must rest on the structured blocks, not on the invocation*. The blocks are verifiable in the report + commit; a Skill-tool call in a subagent transcript is not.)

**Step 2.1b — Dispatch the test-author FIRST, receive `RED_READY`, only then dispatch the implementer.** For each task: dispatch the `test-author` with the acceptance criteria + the plan's `## Threat model` / `## Acceptance flows` rows for this task. It returns a `## Test contract` block with `STATUS: RED_READY` (or `BLOCKED`/`NEEDS_CONTEXT`). Do NOT dispatch the implementer for a task whose test-author has not returned `RED_READY` — a missing RED test means the implementer would author its own, collapsing the split. Pass the test-author's contract block (test path, RED proof, tier, any signature shell, the "immutable — do not weaken" instruction) into the implementer's dispatch prompt.

**Step 2.5 — Ground-truth the dependency surface before each dispatch (plan-freshness gate).** A written plan is a *hypothesis* about the code it integrates against; the source is truth. When the plan is more than a few days old, OR it integrates against another sub-phase's / module's code (calls its functions, names its enums, scopes, env vars, table columns, event payloads), the controller MUST — for the specific task about to be dispatched, AFTER the upstream skill is loaded (never as pre-flight before Step 2.0) — Read the actual exported signatures + types + enums of that task's named dependencies and reconcile them against the plan's code samples. Bake the verified-true signatures into the dispatch prompt and flag any drift inline so the implementer builds to reality, not the stale sample. Per-task, not whole-plan up front — verify each task's surface as you reach it. If reconciliation surfaces drift big enough to change the task's shape, correct the plan (a plan-correction commit) before dispatching.

  Calibration (why this is a hard rule, not advice): FOUR consecutive Folio sub-phases hit plan-vs-source drift this catch resolved — A (Zod house-style + migration columns), C.2 (an entire provider API that didn't exist), C.3 (`recoverOrphanRuns` signature + a contaminated `db:generate` migration), Phase C (triggers carry `fm.agent`, not the plan's `target_agent_id`). Every drift was caught at controller ground-truthing and corrected before/at dispatch. Skipping it ships the drift into the subagent, which builds the wrong thing confidently.

**Step 2.6 — Gate every task close on the PAIR's output — an independent RED plus a GREEN that didn't weaken it.** A task is not done until you hold BOTH structured blocks (see addenda), and they reconcile:
  - From the `test-author`: the `## Test contract` block with the **tier classification** (A/B + one-sentence justification, owned by the author, not the coder), the **RED-first behavioral proof** (or the `no unit test: Tier B, <reason>` line), and the denial/seam obligations.
  - From the `implementer`: the Test-evidence + STATUS blocks showing the **same** contract test now GREEN, the `Weakened? NO` line (or `ESCALATED`), and the **deferral line** naming the risk handed downstream.

  Reconcile the two: the implementer's `RED proof (author's)` must match the test-author's, its `Contract test author` must name the independent author (not "self", except the Class E inline exception), and `Weakened?` must be `NO`. A GREEN with no matching independent RED, or a `Weakened?` that isn't `NO`, means the split was bypassed — treat the task as NOT done regardless of a green suite. Those two blocks — visible in the reports and the two commit bodies — ARE the gate.

  Do **not** require either subagent to literally re-invoke `Skill("testing-workflow")` once per task: the gate skill itself states (`testing-workflow` "What the discipline actually is") that *"Re-invoking the Skill tool once per task is **not** the discipline."* The discipline is classify-at-tier (author) → RED-first (author) → green-without-weakening (implementer) → full-suite + static-analysis → record the tier/deferral lines. (Each subagent reads testing-workflow **once per session** to internalize it; re-invoking it per task is the ghost ritual Sub-phase A proved was bypassable — the structured blocks, not the invocation, are the evidence.)

If any required block or line is missing, or the two don't reconcile, treat the task as DONE_WITH_CONCERNS or NEEDS_CONTEXT. Do not mark complete without them. The `subagent-stop.py` hook (tests actually ran) is a backstop on each half, not the primary mechanism — the reconciled blocks are.

**Step 2.6b — Standards gate at every code-task close.** Alongside the testing gate, invoke `netdust-agent:standards-gate`: run the project's configured linter/formatter (eslint/prettier/biome, or phpcs/php-cs-fixer) on the touched files and record a `Standards: clean | <N fixed> | n/a — no linter` line in the Test-evidence block. This closes goal #2 — coding standards become enforced, not advisory. The same `subagent-stop.py` hook backstops it: it blocks a code-editing subagent's close when a linter is configured for the project but was never run. If no linter is configured, the gate (and the backstop) no-op — do not impose a style of your own.

**Step 2.7 — Bug-fix bundles (Class C) get one split TDD cycle per finding.** Each `/code-review` or `/security-review` finding is a behavior change → the Iron Law applies, and so does the split: the `test-author` writes the RED test that **reproduces** the bug (the failing case from the finding), then the `implementer` loads `superpowers:systematic-debugging` and fixes to green on that reproducing test without weakening it — one bug per cycle, re-sweep between. Authoring the reproduction independently is what proves the fix addresses the reported defect and not a convenient near-miss. "I already see the fix, the phases are obvious here" is the exact rationalization the debugging skill's red-flags table names. (2026-05-30, Sub-phase F: bundling I2+I3 into one cycle drifted the process even though outcomes were sound.)

**Step 2.8 — HALT at every review-gate marker (the cluster boundary is a hard stop).** When you reach a `── REVIEW GATE ──` / STOP marker in the plan (placed per 1f), OR the end of a phase's task group, you STOP. Commit the cluster's tasks, run `/integration` on that cluster's diff, then review — and do NOT begin the next task until that review is clear. The diff a reviewer holds must be one cluster (~3–4 tasks), never a whole long phase run flat. **The pull to "just keep going to the next task, I'll review at the end" is the exact failure 1f exists to prevent** — it produces an un-bisectable mega-diff and lets the agent grade a large body of its own work in one pass. Treat the marker as non-negotiable as a failing test. If the plan you're executing is a long phase with NO such markers, that is a 1f planning defect — add the markers (a plan-correction commit) before running past ~4 tasks.

  **State the review tier at the gate (1h), same as the work-class statement at intake.** Before dispatching the cluster review, declare in the transcript: `Review tier: <FULL | STANDARD | LIGHT> — <one-line justification keyed to the 1a trigger surface>` (the plan carries a provisional tier per cluster; restate it, and override with justification if the cluster's diff turned out to touch a different surface than planned). The fan-out you dispatch is **read from the stated tier**, not fixed:
  - **FULL** → all finder angles in parallel + `security-sentinel` mandatory; `/code-review --effort=high`; `/security-review` if the threat-modeling gate fired at plan time.
  - **STANDARD** → 2 finder angles (line-by-line + cross-file tracer) + `code-simplicity-reviewer` + the feature-acceptance browser pass. No `security-sentinel`, no `performance-oracle` unless the diff touches a hot path named in `CODE-MAP.md`. `/code-review --effort=medium`.
  - **LIGHT** → a single generalist `reviewer` pass. No fan-out.

  **Escalation is one-way (1h).** If ANY finder/reviewer surfaces a finding on a 1a surface, the cluster is immediately promoted to **FULL** — dispatch the FULL-tier reviewers you skipped, on this same cluster, before proceeding. Never the reverse. And regardless of tier, `/security-review` still fires if a plan-time `## Threat model` exists for this work.

## Stage 3 — Phase close, shake-out, finish

After all tasks in a phase complete and the upstream skill's final-review step is done:

1. **Phase-complete integration gate** — `testing-workflow` phase-complete (integration + acceptance), or run `/integration`.
2. **Test-effectiveness audit** — invoke `test-effectiveness` (Situation A) over the phase diff. The integration gate proved the tests *pass*; this proves they would *bite*. Walk the seven failure modes (stale fixture, test-world≠real-world, wire-mock leak, unmounted guard, happy-path-only/missing-denial, no-coverage, concurrency) over every dangerous path the diff introduced — for each guard, fixture, wire, mount, and timer, name the test that goes RED if it breaks, or record it `blind` and fix it. The resulting `covered`/`blind`/`fixed` manifest is the convergence target for the next step's reviewers — so shake-out verifies the gaps instead of re-discovering them. (Especially load-bearing on security-rich / multi-tenancy phases, where green-but-blind denial tests are the dominant escape — see the traverse-clause calibration.)
3. **Feature-acceptance verification** — if the phase added/changed a user-facing feature, invoke `feature-acceptance` (Situation B) to *drive* the `## Acceptance flows` matrix authored at 1g. test-effectiveness proved the tests *bite*; this proves the *feature behaves* when used. Drive each flow + edge through its faithful layer — UI flows through the real browser (Playwright spec → else `superpowers-chrome` `use_browser` against the running dev server), backend flows through the un-mocked wire — and emit a `pass`/`fail`/`not-reachable`/`unverified-no-browser` manifest. (`/shakeout` runs this for you, between Step 0 test-effectiveness and the reviewer dispatch.) The manifest is the reviewers' convergence target alongside test-effectiveness's. No UI flow is `pass` without a browser driving it.
4. **Shake-out** — invoke `shake-out`, or its stack-specific replacement if the loaded sub-plugin provides one (see `<stack_overrides>`); or run `/shakeout` at spec close. This is the spec-complete / pre-merge gate: re-runs integration, runs E2E, and dispatches the reviewer agents against the full branch diff. **The spec-close panel composition is set by the branch diff's review tier (1h):** FULL → the 5-persona panel (`reviewer` + `code-simplicity-reviewer` + `security-sentinel` + `performance-oracle` + `invariant-auditor`; +`ntdst-drift-reviewer` on WP); STANDARD → `reviewer` + `invariant-auditor` only; LIGHT → a single `reviewer` pass. State the branch tier before dispatch; one-way escalation still applies (a finding on a 1a surface promotes the whole branch to FULL and re-dispatches the missing personas). `/shakeout` reads the tier and dispatches accordingly.
5. **Finish** — `superpowers:finishing-a-development-branch`.
6. **Compound** (spec-close only) — invoke `compounding`. After the branch is finished, harvest what the spec taught into PROPOSALS: a patch to `docs/architecture/CODE-MAP.md` (codebase structure — new modules, convergence points, data flows; cross-refs `architecture-invariants`) + a `/skill-audit` scoped to the skills touched this spec (tool edge-cases + `SKILL-EDGE:` deltas → `lessons.md`). Report-only — emits a proposed-deltas manifest; the user approves what's written, nothing auto-edits. Closes the knowledge loop the same way the Stop hook's `LESSON:`/`DECISION:` tag capture closes the decision loop. **Cadence: spec-close / `/shakeout`-level only — NOT every sub-phase.**

</process>

<addendum_for_dispatch>

Stage 2 dispatches in PAIRS: the `test-author` (RED) then the `implementer` (GREEN). Each half has its own verbatim addendum. Append the matching one at the bottom of the dispatch prompt; it supplements (does not replace) the upstream template.

**A — test-author dispatch addendum** (append to the RED-authoring dispatch):

```
---

## Netdust addendum — test-author close-out (RED)

You author the test; you do NOT implement the logic. Before reporting STATUS:

1. Apply the `testing-workflow` discipline (read it once per session):
   classify the task's risk tier (A/B) from the ACCEPTANCE CRITERIA + threat
   model — not from any implementation. Apply the erosion guard literally
   (guard/parser/state-machine = Tier A regardless of line count).

2. Derive the contract from the criteria / threat-model mitigation, never
   from code. For Tier A, write the RED-first BEHAVIORAL test incl. the
   denial path. For a brand-new symbol, create ONLY the minimal signature
   shell (declaration + sentinel body) so the failure is behavioral, not
   "module not found" — never write the logic. For a wiring task, write the
   seam test (1 un-mocked-chain assertion + 1 negative case).

3. Run the test; capture the failing (RED) snippet. Commit the test (+ shell)
   as its OWN commit so authorship predates the implementation in git.

4. End your final message with this block, verbatim and complete:

   ## Test contract
   - Tier: <A | B> — <one-sentence justification (erosion guard applied)>
   - Contract source: <acceptance criterion / threat-model mitigation / flow row>
   - Test file(s): <paths, or "none — Tier B">
   - Signature shell (new symbol only): <path + sentinel body, or "n/a">
   - RED proof: <command> → <1-3 line snippet showing BEHAVIORAL fail>
     (Tier B: replace with `no unit test: Tier B, <reason>`)
   - Denial/negative path asserted: <refused actor / malformed input, or "n/a">
   - Seam assertion (wiring task): <the un-mocked-chain + negative case, or "n/a">
   - Determinism note: <"run ≥3×" if time/ordering/concurrency, else "n/a">
   - Handoff: this test is IMMUTABLE to the implementer — green without weakening.

   ## STATUS
   STATUS: RED_READY | BLOCKED | NEEDS_CONTEXT
   COMMIT: <sha of the test/shell commit>
   FILES TOUCHED: <list>

Do NOT report RED_READY without a failing proof (or the Tier-B line). Do not
implement the logic — that is the implementer's dispatch.

---
```

**B — implementer dispatch addendum** (append to the GREEN dispatch; include the test-author's `## Test contract` block above it as the handoff):

```
---

## Netdust addendum — implementer close-out (GREEN)

An independent test-author already wrote your failing test (the `## Test
contract` block above). You green it; you do NOT re-author it. Before
reporting STATUS, you MUST:

1. Treat the author's contract test as IMMUTABLE. Make it pass with real
   logic — fill the signature shell / modify the symbol. You may ADD edge
   tests (additive only); you may NOT edit, weaken, delete, or skip the
   author's test. If you believe it is wrong, report NEEDS_CONTEXT with why —
   do not rewrite it to pass. (Read `testing-workflow` once this session to
   recognize the tier; do not re-open the tier decision.)

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
   - Tier: <A | B> — <as classified by the test-author; flag if you dispute it>
   - Contract test author: test-author (independent) — <author's test path(s)>
   - Test file(s): <author's contract test + any edge tests YOU added, or "none — Tier B">
   - RED proof (author's): <the test-author's command + 1-3 line fail snippet>
     (Tier B: replace with `no unit test: Tier B, <reason>` as recorded by the author)
   - Weakened? <NO — author's test unchanged | ESCALATED via NEEDS_CONTEXT> (never "yes")
   - GREEN proof: <command you ran> → <1-3 line snippet showing the author's test now passes>
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

Missing any item in either block, or a `Weakened?` that isn't NO = task NOT
done. Do not rationalize. Do not substitute prose for the structured form.

---
```

For **doc-only or tooling-only tasks** (no code-touching changes) there is no test to author — dispatch only the implementer, which may omit the Test-evidence block but MUST still include the STATUS block.

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
| "This cluster only touches auth lightly — I'll run STANDARD to save time" | Touching a 1a surface AT ALL = TIER FULL (1h). The tier trigger is binary on the surface, not a severity judgment. "Lightly touches auth" is exactly the 23/49-dispatch over/under-calibration this rule exists to fix — and under-calling FULL is the dangerous direction. |
| "A finder flagged something on the token path but this is a STANDARD cluster, I'll note it and move on" | Escalation is one-way (1h): a finding on a 1a surface promotes the unit to FULL NOW — dispatch the skipped `security-sentinel`/`performance-oracle` on this same unit before proceeding. You do not get to keep the lighter tier once a 1a finding appears. |
| "The plan-time threat model means I can skip /security-review since the panel was STANDARD" | Backwards. `/security-review` is independent of tier — if a `## Threat model` was authored at plan time, it fires regardless. Tier governs finder/persona fan-out, never the security-review obligation. |
| "I'll just run `/speckit.implement` to execute the tasks" | That bypasses every Stage-2 gate — threat-model verify, per-task tiers, review-cluster HALT, the `subagent-stop` backstop. The handoff is `tasks.md`; Stage 2 executes it under the netdust spine. NEVER `/speckit.implement`. |
| "`/speckit.analyze` passed, I'll start dispatching" | analyze is only half of Stage 1.5. Run `gate-check.py` (the mechanical part) — it is what catches a skipped threat model, an un-tiered task, or an oversized cluster. A green checker is the Stage-2 entry condition. |
| "Tests are green, the task is done" | Tests are half the close. Run `standards-gate` too (Step 2.6b) and record the `Standards:` line — or the `subagent-stop` hook blocks your close when a linter is configured. |
| "I'll just have the implementer write its own test, it's faster than two dispatches" | That is the exact self-grading flaw the test/dev split removes (`<test_dev_split>`). The coder shaping its own test lets the denial path vanish and a guard get self-excused to Tier B. Dispatch `test-author` FIRST, then the implementer. Two commits, two agents — non-negotiable, even for Class E. |
| "The RED test the author wrote is a bit off — I'll just tweak it so it passes" | Editing/weakening the contract test to reach green moves the grader one seat over — the split is defeated. The implementer's `Weakened?` line must be `NO`. If the test is genuinely wrong, escalate `NEEDS_CONTEXT`; the author fixes it, not the implementer. |
| "This is a brand-new function so the RED is just 'module not found' — good enough" | Import-error RED proves nothing about the contract. The test-author writes the minimal signature shell (declaration + sentinel body) so the RED is BEHAVIORAL (`expected 403, got not-implemented`). Shell only — no logic; the logic is the implementer's. |
| "It's obviously just glue, I'll mark it Tier B and skip the test" | The tier call belongs to the independent `test-author`, not the coder who benefits from the skip. Self-classifying your own code Tier B is the loophole the split closes. Let the author classify; a guard/parser/state-machine is Tier A no matter how short. |

</red_flags>

<success_criteria>

This skill has succeeded when:

1. The work was classified (A/B/C/D/E) in the transcript before any action — and the class was the *smallest* that fits the work (a tweak called E, not a defensive Class A).
2. For any feature touching the 1a trigger surface, a `## Threat model` exists (in the plan, or run on the diff for Class D) BEFORE implementation.
3. For any feature touching a named convergence point, the relevant invariants were cited.
4. Any "reuse X for Y" premise was ground-truthed against X's source before the plan shipped.
5. The execution upstream skill was invoked via the Skill tool and its checklist followed.
6. Every code task ran as a `test-author → implementer` PAIR (the test/dev split): an independent test-author authored the RED test and reported `## Test contract` + `RED_READY` in its own commit BEFORE the implementer, and the implementer greened that same test with `Weakened? NO`, both dispatches carrying their verbatim addendum. No agent authored and greened its own contract test (except the recorded Class E inline exception, where the controller — not the coder — authored the RED). The two structured blocks + the two commits are the auditable evidence — NOT a per-task `Skill("testing-workflow")` re-invocation, which the gate skill itself has retired.
7. Step 2.5 ground-truthing was performed per-task for every task integrating against other code.
8. Phase close handed off to `shake-out` and then `superpowers:finishing-a-development-branch`.
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
| `spec-authoring` | **STAGE 0.5.** Wraps `/speckit.specify` + `/speckit.clarify`; HALTs on unresolved `[NEEDS CLARIFICATION]`. Produces the `spec.md` Stage 1 plans against. |
| `spec-analysis` | **STAGE 1.5.** Wraps `/speckit.analyze` + the mechanical `spec-kit/gate-check.py` — the pre-execution barrier that makes the 1a/1b/1d/1f gates machine-checked, not skill-honored. |
| `standards-gate` | **STAGE 2 GATE (Step 2.6b).** Runs the project linter on touched files at each code-task close; records the `Standards:` line; backstopped by `subagent-stop.py`. Closes goal #2 (enforced coding standards). |
| `constitution-bridge` | **SETUP.** Generates the spec-kit constitution as a view over RULES/SOUL/invariants; declares the standard `standards-gate` enforces. No governance fork. |
| spec-kit graft (`spec-kit/` + `/spec-kit-setup`) | **GRAFT MECHANISM.** Override templates bake the gates into spec-kit's spec/plan/tasks; `gate-check.py` verifies them. Keystone invariant: handoff is `tasks.md`, `/speckit.implement` is never run. |
| `threat-modeling` | **STAGE 1 GATE (1a).** Fired by trigger list, at plan-time OR on an ad-hoc security diff (Class D). Becomes the /code-review convergence target. |
| `architecture-invariants` | **STAGE 1 GATE (1b).** Fired when a convergence point is touched. |
| `superpowers:subagent-driven-development` | **STAGE 2 — primary branch.** Parallel-independent tasks — dispatched as `test-author → implementer` pairs (`<test_dev_split>`). |
| `superpowers:executing-plans` | **STAGE 2 — secondary branch.** Sequential / solo execution, still split test-author → implementer per task. |
| `test-author` (agent) | **STAGE 2 — RED half.** Independent per-task test-author: owns the tier decision + writes the RED-first behavioral test (+ signature shell) from the contract, before the implementer. Reports `## Test contract` + `RED_READY`. The reason no agent grades its own homework. |
| `implementer` (agent) | **STAGE 2 — GREEN half.** Greens the test-author's RED without weakening it; reports Test-evidence + STATUS with `Weakened? NO`. Never authors its own contract test. |
| `testing-workflow` | **STAGE 2 MANDATORY GATE.** Per-task close split across the pair: the test-author classifies the tier + proves RED-first; the implementer greens + records the deferral line. The two structured blocks ARE the auditable gate — not a per-task Skill re-invocation. Plus phase-complete. |
| `test-effectiveness` | **STAGE 3 GATE.** Phase-close audit (Situation A), after the integration gate and before shake-out: the integration gate proved tests *pass*; this proves they would *bite*. Walks the seven green-but-blind failure modes over the phase diff; its `covered`/`blind`/`fixed` manifest is the shake-out + `/code-review` convergence target. Sibling to testing-workflow (write-time/per-task) at audit-time/per-phase altitude. |
| `superpowers:systematic-debugging` | **STAGE 2 (Class C).** One invocation per bug, on the implementer half — after the test-author has written the reproducing RED test for that finding. |
| `feature-acceptance` | **STAGE 1g (author) + STAGE 3 (drive).** Plan-time, embeds an `## Acceptance flows` matrix for user-facing features (intended-use flows + mandatory per-flow edge enumeration), alongside threat-model/invariants. At Stage 3 / `/shakeout` (after test-effectiveness, before reviewer dispatch) it DRIVES that matrix — UI flows through the real browser, backend flows through the un-mocked wire — emitting a `pass`/`fail`/`not-reachable`/`unverified-no-browser` manifest. Behavioral sibling to test-effectiveness (which audits code-bite); proves the feature behaves, not just that the code is correct. |
| `shake-out` | **STAGE 3.** Spec-close, after upstream final-review. |
| `superpowers:finishing-a-development-branch` | **STAGE 3.** After shake-out. |
| `compounding` | **STAGE 3 closer (step 6, spec-close only).** After finish, harvests spec knowledge into PROPOSALS — a `CODE-MAP.md` patch (codebase) + `/skill-audit` scoped to touched skills (tools). Report-only; user approves. Closes the knowledge loop beside the Stop hook's `LESSON:`/`DECISION:` tag capture. NOT per sub-phase. |
| `ntdst-execute-with-tests` (historical) | **DELETED — fully absorbed here.** The old execution-only skill is gone (2026-06-05). Its triggers ("execute the plan", "work the plan") now resolve to THIS skill, which does everything it did plus the planning gates. Older handoff docs that name it need no change — the trigger phrases route here. |
| `subagent-stop.py` hook | **BACKSTOP (both halves).** This plugin's SubagentStop hook blocks a code-editing subagent that never ran a test command — it backstops the test-author (RED test ran) and the implementer (suite ran) alike. It cannot verify authorship independence (one invocation sees one transcript); the dispatch order + two commits enforce that. Backstop, not primary mechanism — the reconciled `## Test contract` + Test-evidence blocks are. |

**Calibration data behind these rules** (all from Folio Phase 3):
- *Test/dev split (the flaw this closes):* the original harness had the implementer author its own Tier-A test and self-report the Test-evidence that gated the task. RED-first softened it, but the coder still wrote both sides — the test drifts to fit the code, the denial path goes missing, and a risky guard gets self-classified "Tier B, just wiring" by the very agent that benefits from skipping the test. Grading your own homework. The fix (`<test_dev_split>`): an independent `test-author` writes the RED test from the contract BEFORE the implementer exists; the implementer greens it without weakening. Two agents, two commits — the coder is no longer the grader.
- *Verbatim addendum:* Sub-phase A — 0/7 subagents re-invoked the testing-workflow skill under a weaker one-liner, yet the work was correct. The lesson the harness took from this (2026-06-04): the audit trail must rest on the **structured blocks** the addenda demand, not on a per-task Skill-tool re-invocation — which is unverifiable from git and which the testing-workflow gate skill has itself retired.
- *Step 2.5 plan-freshness:* caught plan-vs-source drift 4 consecutive sub-phases (A, C.2, C.3, Phase C).
- *Stage 1c spec-premise:* Sub-phase E — a false "reuse TableView" premise survived spec + plan + handoff.
- *Stage 1a on ad-hoc diffs (Class D):* 2026-06-03 — a security-guard edit shipped without threat-modeling because the trigger was plan-only.

</integration>
