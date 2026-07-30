---
name: building
description: The BUILD spine of the Netdust harness — execute → test → standards → review clusters → shake-out → finish. PRECONDITION-FIRST — for plan-driven work (Class A/B) it REFUSES to start unless an approved `tasks.md` exists and `spec-kit/gate-check.py` is GREEN; the seam artifact from `planning` is the entry ticket, and a missing or red gate-check routes the work BACK to `planning`, never forward. Also the home of the plan-less classes — a bug-fix bundle from review findings is one TDD cycle per finding (Class C), an ad-hoc security-boundary edit runs after its diff threat model (Class D), a small self-contained tweak is one straight TDD cycle (Class E). Owns the Stage-2 armed loop (`/loop` + loop-gate). Normally entered via `harnessed-development` intake; also triggers directly on "execute the plan", "work the plan", "execute todo.md", "execute tasks.md", "start building", "implement the plan", "run the tasks", "fix the code-review findings", "address the review feedback". NOT for writing or reshaping a plan — that is `planning`; if you find yourself re-deciding plan content here, you are in the wrong spine. Stack-agnostic; defers to the loaded stack sub-plugin for stack-specific skills, reviewers, and test runners. Replaces the deleted `ntdst-execute-with-tests` skill (its "execute the plan" / "work the plan" triggers resolve here).
---

<precondition>
**Check this BEFORE anything else — before loading an execution skill, before reading the plan, before touching a file.** Entry is by class (stated at `harnessed-development` intake; restate it here in one sentence):

| Class | Entry ticket — verify, then proceed |
|---|---|
| **A / B — plan-driven work** | The seam artifact, all three parts: **(1)** `tasks.md` exists for the feature; **(2)** `python3 <plugin>/spec-kit/gate-check.py specs/<feature>` exits **0** — run it NOW, do not trust a transcript assertion (yours or `planning`'s); **(3)** your human partner has approved the plan. **Any part missing → REFUSE to start.** Name the missing part and route the work to `planning` (Class B additionally gets `planning`'s freshness review when the plan is stale or externally authored). **There is no graft-less variant of this ticket.** `gate-check.py` needs nothing from spec-kit — it reads `specs/<feature>/` directly — so "this project has no spec-kit" is never a reason to accept a stated 1a–1g checklist in place of exit 0. Run the script; a checklist an agent says it applied is the self-attestation the seam exists to refuse. If the feature dir isn't where the script can read it, that is the defect to fix, not to work around. A task carrying **no `Test-author:` line at all** (a pre-0.8 `tasks.md` — `gate-check.py` WARNs but still passes, for retro-compat) defaults to **`split`**, never `solo`: see Step 2.1b. |
| **C — bug-fix bundle from `/code-review` or `/security-review`** | No plan needed. Each finding is one TDD cycle (Step 2.7); Stage 3 verifies. If any finding touches a security boundary, the 1a diff threat model (from `planning`) must exist first. |
| **D — ad-hoc edit to a named security-boundary file** (auth/session/token, URL-allow-list, crypto) | The thin plan gate: a `## Threat model` **on the diff** (produced by `threat-modeling` via `planning`'s 1a) must exist BEFORE implementation. Even for a one-liner. Then: implement with TDD → verify. (Slug: `class-d-gap`.) |
| **E — small self-contained change, no plan warranted** | Straight to one TDD cycle (Step 2.0, third row). **Default mode is `solo`** (Step 2.0's rules table) — the controller may author the RED inline for a genuinely trivial change and dispatch only the implementer to green it. Any change touching a named security-boundary file is **Class D, not E**, and Class D is always `split` — its diff threat model names the contract the test-author asserts. No plan, no spec, no shake-out. The per-task testing gate STILL applies — tier it, record the evidence blocks; the `subagent-stop` hook still backstops it. Verify with the suite + `/integration` on the diff. |

This precondition is the whole point of the plan/build split: the gates `planning` sequences are only durable because THIS skill will not run without their machine-checked output. Talking yourself past a red or missing gate-check re-fuses what the split separated.
</precondition>

<objective>
Make one truth hold: **every task that ships crossed its gates — per-task test evidence, standards, review-cluster HALTs, phase-close audits — and none was left to "remember to do it."** The plan (or the class's single TDD cycle) says what to build; this spine proves, auditably in reports and commit bodies, that it was built gated.

This skill enforces what the upstream superpowers skills do not:

1. **Entry is gated at the seam** (`<precondition>`) — the plan-time gates cannot be skipped upstream and slip through, because their machine-checked output is the entry ticket.
2. **Every task close is gated on the RED-first Iron Law, auditably — and its authorship mode is set by the plan, not the runtime agent.** `testing-workflow` discipline is mandatory at each task close. Each task in `tasks.md` carries a `Test-author:` mode set by the planner (`split` or `solo — <reason>`, D1 rule): `split` tasks get the test written by a separate `test-author` agent BEFORE the implementer touches the code, so no agent grades its own homework on security-boundary work (`<test_dev_split>`); `solo` tasks have the implementer author its own RED-first test for everything else, with the independent check moved to the cluster review gate + phase-close test-effectiveness audit. No run-time agent — test-author, implementer, or controller — may re-decide which mode a task uses; it reads the field. Both structured blocks are visible in the transcript, and for `split` tasks the two are separate commits — verifiable from git, not honor-system.

Everything in between — TDD red→green, dispatch shape, two-stage review, status handling, escalation — belongs to the upstream superpowers skills. This skill is a **sequencer**: at each stage it loads the right upstream skill and adds the netdust-specific gate around it. Do NOT duplicate upstream content. Stack-agnostic by design — see `<stack_overrides>`.
</objective>

<how_each_gate_is_actually_enforced>
Be honest about enforcement strength — the gates are NOT equally hard:

- **The seam precondition is MACHINE-CHECKED.** `gate-check.py` exits non-zero; you run it and read the exit code. It cannot be talked out of a finding.
- **The per-task testing + standards gates are HOOK-ENFORCED.** `subagent-stop.py` (a real SubagentStop hook) blocks a subagent that edited code from stopping without a test command having actually run, and blocks a close that skipped a configured linter. It backstops BOTH halves of the split: the `test-author` must have run its RED test, the `implementer` must have run the suite. Even so, the *auditable* evidence is the structured blocks in the reports/commits — the hook is the backstop.
- **The tier/mode boundary itself is MACHINE-CHECKED.** `gate-check.py`'s `test-author-mode` check (T01) verifies, at the seam, that every task carries a valid `Test-author:` line and that a `[Tier A]` task claiming `solo` states a reason — it FAILs a bare Tier-A solo and WARNs an over-ceremonious Tier-B split. This closes the loophole one layer up from dispatch: the *decision* of which tasks get which mode is checked before execution ever starts, not trusted to the controller's judgment mid-run.
- **The controller reading that field is SEQUENCER-ENFORCED.** Given a machine-checked `tasks.md`, nothing hooks-enforces that the controller actually dispatches per the stated mode instead of improvising — that discipline is this skill's job (Step 2.1b).
- **The test/dev split (authorship independence) is SEQUENCER-ENFORCED, not hook-enforced, for `split` tasks.** The hook can confirm a test *ran*; it cannot confirm the implementer didn't *write* the test it ran — a single SubagentStop invocation sees one subagent's transcript, not the pair. What guarantees independence on a `split` task is the DISPATCH ORDER this skill mandates (Step 2.1b): `test-author` first, RED_READY received, only then the `implementer` with that test already committed. The two separate commits (test predates code, different authors) are the audit trail. Do not collapse them into one dispatch to save a round-trip — that silently reverts to self-grading, and nothing will hard-stop you.
- **`solo` mode reintroduces self-authorship BY DESIGN, for non-security tasks, with the independent check named explicitly.** On a `solo` task the same implementer authors and greens its own RED-first test — there is no pair to enforce ordering over. The independent check is NOT skipped, it is relocated: the cluster review gate (Step 2.8) and the phase-close test-effectiveness audit (Stage 3) are the controls that catch a soft or missing denial path on solo work. This is a stated trade (2026-07-04 evidence: 2× dispatches + 4–6 min/task bought zero unique catches outside security surfaces; review + test-effectiveness caught everything real), not a silent gap — see `<test_dev_split>`.
- **The review-cluster HALTs (Step 2.8) and Stage-3 sequence are SEQUENCER-ENFORCED.** No hook stops you from running past a `── REVIEW GATE ──` marker. Treat the marker as non-negotiable as a failing test, precisely because nothing will hard-stop you.
</how_each_gate_is_actually_enforced>

<test_dev_split>
**The flaw this closes.** Until 2026-07-04 ONE agent — the implementer — wrote the code AND its own Tier-A test AND self-reported the Test-evidence that gated the task. RED-first softened it, but the same agent still authored both sides: the test drifts to fit the code it was written against, the denial path quietly goes missing, and a risky guard gets self-classified "just wiring, Tier B" — and the agent that benefits from the skip is the one who judged it. Grading your own homework. (Slug: `self-grading-split`.)

**The fix, made tier-conditional (2026-07-04).** Test authorship is no longer fused to the coder by default, but it is also no longer independently dispatched for EVERY task — each task in `tasks.md` carries a `Test-author:` mode set by the **planner**, at plan time, per the D1 decision rule (`split` iff the task is Tier A **and** in a security-boundary category — auth/guards, untrusted-input parsing, migrations/schema, money/billing, or a named 1a-trigger surface; otherwise `solo — <reason>`). The controller READS this field at dispatch; **no run-time agent — implementer, test-author, or the controller itself — may re-decide it.** A task deciding its own mode is the exact self-downgrade loophole the D1 machine check (`gate-check.py`'s `test-author-mode`, T01) exists to close. (Calibration: `tier-conditional-split`.)

**The `split` path — byte-for-byte today's protocol, scoped to `Test-author: split` tasks.** Test authorship and execution are owned by a separate `test-author` agent, dispatched BEFORE the implementer for the same task:

1. `test-author` classifies the tier (from the acceptance criteria + threat model, NOT the code — which for a new symbol doesn't exist yet), and for Tier A writes the RED-first behavioral test including the denial path. For a brand-new symbol it creates only the minimal **signature shell** (declaration + sentinel body) so the RED is behavioral, not "module not found" — never the logic. It proves RED, commits the test + shell as its own commit, and hands over a `## Test contract` block with `STATUS: RED_READY`.
2. `implementer` receives that failing, contract-derived test as an **immutable input**. It drives the test to GREEN — filling the shell / modifying the symbol — WITHOUT editing, weakening, deleting, or skipping the contract test. It may ADD edge tests. If it thinks the test is wrong, it escalates `NEEDS_CONTEXT`; it does not rewrite the test to pass.

The gate on a `split` task is the PAIR: the test-author's RED authorship + the implementer's GREEN on the same unweakened test, in two separate commits.

**The `solo` path — ONE implementer dispatch, for everything outside the security-boundary categories.** RED-first remains the Iron Law even here: the implementer authors the behavioral RED test itself (shell rule included for a brand-new symbol), watches RED→GREEN, and reports `Contract test author: self — solo mode (plan: Test-author: solo)` and `Weakened? n/a — self-authored (solo mode)` in its Test-evidence block. The `subagent-stop.py` backstop is untouched (it checks that tests ran; it never checked authorship, on either path). The independent check for `solo` tasks is NOT skipped — it is the cluster review gate (Step 2.8) + the phase-close test-effectiveness audit (Stage 3), the two controls that caught all real bugs on 2026-07-04.

**Class E — default `solo`; a security-boundary file is always Class D, never E.** A small tweak is one TDD cycle (no plan, no shake-out) with the mode read the same way: `solo` by default, where the controller may act as the implementer's own RED-author for a genuinely trivial inline change (record `Contract test author: self — solo mode (Class E inline, controller authored RED)`). Anything touching a named security-boundary file is Class D, not E, and Class D is **always `split`** — its diff threat model (from `planning`'s 1a) names the contract the test-author asserts.
</test_dev_split>

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
| Stage 2 — author the test (test-author, BEFORE the implementer) | `testing-workflow` (per-task tier gate, Step 2.6) | `writing-tests` (Tier-A RED-first on top of `superpowers:test-driven-development`) |
| Stage 2 — green the test (implementer) | `testing-workflow` (recognize the tier; do not re-author) | `superpowers:test-driven-development` (green the handed-over RED without weakening it) |
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
| Stage 2 — author the test (`Test-author: split` tasks only, FIRST) | `test-author` (one per task, before the implementer) | testing-workflow/writing-tests; owns the tier decision + the RED-first behavioral test (+ signature shell); closes with the `## Test contract` block + `RED_READY` |
| Stage 2 — author + green (`Test-author: solo` tasks, ONE dispatch) | `implementer` (one per task) | testing-workflow/writing-tests + test-driven-development, building-frontend, versioning-with-git; authors its own RED-first test, watches RED→GREEN, records the solo evidence lines; closes with the Test-evidence + STATUS blocks |
| Stage 2 — green the test (`split` tasks only, SECOND) | `implementer` (one per task, often parallel across independent tasks) | test-driven-development, building-frontend, versioning-with-git; greens the test-author's RED without weakening it; closes with the Test-evidence + STATUS blocks |
| Stage 3 — whole-diff review | `reviewer` (generalist, five-pillar) + the specialist reviewers | reviews the diff against the threat model, invariants, and test-effectiveness manifest |
| Stage 3 — exercise the artifact | `shakeout-qa` | drives the acceptance matrix through the real browser / un-mocked wire; compiles the bug manifest |

For a `split` task the Stage-2 pair is a hard ordering: `test-author` (RED) → `implementer` (GREEN), per task, two separate commits. Never dispatch the implementer for a `split` task whose RED test doesn't exist yet, and never let one agent do both — that is the self-grading loop `<test_dev_split>` removes. For a `solo` task the single `implementer` dispatch does both roles by design — the mode came from the plan, read by the controller, never decided by the implementer itself.

At Stage 3 the `/shakeout` command auto-dispatches `reviewer` + the specialists in parallel, after `shakeout-qa` (or the inline sweep) has exercised the artifact.
</stage_personas>

<process>

## Stage 2 — Execute

**Handoff seam (spec-kit graft).** When the plan came through spec-kit, execution starts from `tasks.md` — it feeds THIS stage. **NEVER run `/speckit.implement`:** it executes tasks flat with none of the Stage-2 gates below (no threat-model verify, no per-task tiers, no review-cluster HALT, no `subagent-stop.py` backstop). spec-kit owns spec→plan→tasks; this spine owns execute→verify→finish. Nothing downstream of `tasks.md` runs under spec-kit.

**Armed loop (optional, `/loop`).** When `tasks/.harness-loop.json` exists, the `loop-gate.py` Stop hook drives this stage: the session cannot stop while unchecked non-`[HUMAN]` tasks remain — the gate blocks the stop and names the next unit (`spec-kit/loop-check.py` is the ledger; FINISHED is derived from `tasks.md`, never asserted). Two obligations while armed: (1) stay a THIN SCHEDULER — rebuild your working state from `tasks.md` + the plan on every re-entry, never from scrollback (compaction must not kill the loop); (2) the loop changes NOTHING below — review-gate HALTs, tiers, and the subagent-stop backstop apply exactly as written. The loop ends at Stage 2 complete; Stage 3 runs attended.

**Trace emission (honor-system, when the feature has a run-log seam).** If `specs/<feature>/run-log.jsonl` exists or the loop is armed for that feature, emit a trace event at two controller-level points: when Stage 2 execution begins (`python3 <plugin>/spec-kit/run-trace.py append specs/<feature> stage-enter stage=2`), and at each `── REVIEW GATE ──` HALT (Step 2.8), with the stated tier (`python3 <plugin>/spec-kit/run-trace.py append specs/<feature> review-gate cluster=<Cn> tier=<FULL|STANDARD|LIGHT>`). This is sequencer-enforced, not hook-enforced — same standing as every other prose discipline in this stage.

**Step 2.0 — Pick and invoke the execution upstream skill.** State your choice and one-sentence reason first.

| Plan shape | Upstream skill |
|---|---|
| Independent tasks suitable for parallel subagents (most common) | `superpowers:subagent-driven-development` |
| Sequential tasks needing shared context, or solo execution | `superpowers:executing-plans` |
| **No plan — a single small change (Class E)** | None. Do the one cycle directly. Mode defaults to `solo` (controller-authored RED → implementer, for a genuinely trivial inline change, or the implementer authors its own RED). A security-boundary file makes it Class D, not E — always `split` (`test-author → implementer`). `superpowers:test-driven-development` is the base; record both the `## Test contract` (split) or the solo evidence lines, and the Test-evidence blocks. |

Invoke it via the Skill tool. Its content is your primary instruction set for execution from here on; this skill only adds the netdust gates below.

**Every task's dispatch shape is read from its `Test-author:` mode in `tasks.md`, never decided at run time** (`<test_dev_split>`): a `split` task is a PAIR of dispatches — first `test-author` (writes the RED test), then `implementer` (greens it); a `solo` task is a SINGLE `implementer` dispatch that authors its own RED-first test and greens it. Independent tasks parallelize by mode — dispatch several `split` pairs and several `solo` implementers concurrently — but within one `split` task the order never inverts and the two roles are never fused into one agent, and no task's mode is ever re-decided by the agent executing it.

**Step 2.1 — Append the right netdust addendum to every dispatch prompt.** There are THREE Stage-2 dispatch addenda in `<addendum_for_dispatch>`: the **test-author addendum** (for a `split` task's RED-authoring dispatch), the **implementer addendum** (for a `split` task's GREEN dispatch), and the **solo implementer addendum** (for a `solo` task's single dispatch — addendum C). Append the matching one VERBATIM to each dispatch, selected by that task's `Test-author:` mode; reviewer dispatches keep the STATUS-only variant. Do not summarize, paraphrase, or selectively include — the verbatim form is what closes the audit gap, because it demands the structured blocks (the `## Test contract` from the test-author; the Test-evidence + STATUS from the implementer, whichever mode produced them). (Calibration: `subphase-a-0of7` — the blocks are verifiable in the report + commit; a Skill-tool call in a subagent transcript is not. Full story under `<integration>` below.)

**Step 2.1b — Read the task's `Test-author:` mode from `tasks.md` and dispatch accordingly; never let the mode be re-decided at run time.** For a `split` task: dispatch the `test-author` FIRST with the acceptance criteria + the plan's `## Threat model` / `## Acceptance flows` rows for this task. It returns a `## Test contract` block with `STATUS: RED_READY` (or `BLOCKED`/`NEEDS_CONTEXT`). Do NOT dispatch the implementer for a `split` task whose test-author has not returned `RED_READY` — a missing RED test means the implementer would author its own, collapsing the split. Pass the test-author's contract block (test path, RED proof, tier, any signature shell, the "immutable — do not weaken" instruction) into the implementer's dispatch prompt. For a `solo` task: dispatch ONLY the `implementer`, with the solo addendum, the acceptance criteria, and the plan's threat-model / flow rows for this task — it authors its own RED-first test per the Iron Law. In neither case does the implementer (or any dispatched agent) get to choose which of these two shapes applies — that decision was made by the planner and is read, not made, here. **Missing-field default:** if a task carries NO `Test-author:` line at all (a pre-0.8 `tasks.md` — `gate-check.py`'s `test-author-mode` check WARNs but still passes, for retro-compat), the controller treats it as `split`, never `solo` — the pre-existing unconditional-split default from before the tier-conditional relaxation. `solo` is the newly-introduced relaxation and must be read explicitly from the field; defaulting missing data to the safer historical behavior keeps that undefined branch from being filled by any run-time agent's judgment, which is the exact vacuum the no-self-downgrade invariant exists to close.

**Step 2.5 — Ground-truth the dependency surface before each dispatch (plan-freshness gate).** A written plan is a *hypothesis* about the code it integrates against; the source is truth. When the plan is more than a few days old, OR it integrates against another sub-phase's / module's code (calls its functions, names its enums, scopes, env vars, table columns, event payloads), the controller MUST — for the specific task about to be dispatched, AFTER the upstream skill is loaded (never as pre-flight before Step 2.0) — Read the actual exported signatures + types + enums of that task's named dependencies and reconcile them against the plan's code samples. Bake the verified-true signatures into the dispatch prompt and flag any drift inline so the implementer builds to reality, not the stale sample. Per-task, not whole-plan up front. If reconciliation surfaces drift big enough to change the task's shape, correct the plan (a plan-correction commit) before dispatching.

  Calibration (why this is a hard rule, not advice): FOUR consecutive Folio sub-phases hit plan-vs-source drift this catch resolved — A (Zod house-style + migration columns), C.2 (an entire provider API that didn't exist), C.3 (`recoverOrphanRuns` signature + a contaminated `db:generate` migration), Phase C (triggers carry `fm.agent`, not the plan's `target_agent_id`). Every drift was caught at controller ground-truthing and corrected before/at dispatch. Skipping it ships the drift into the subagent, which builds the wrong thing confidently. (Slug: `plan-drift-4x`.)

**Step 2.6 — Gate every task close on the RED-first output for its mode — reconciled for `split`, self-attested for `solo`.** A task is not done until you hold the required structured block(s) for its mode:

  - **`split` task:** BOTH blocks, and they reconcile.
    - From the `test-author`: the `## Test contract` block with the **tier classification** (A/B + one-sentence justification, owned by the author, not the coder), the **RED-first behavioral proof** (or the `no unit test: Tier B, <reason>` line), and the denial/seam obligations.
    - From the `implementer`: the Test-evidence + STATUS blocks showing the **same** contract test now GREEN, the `Weakened? NO` line (or `ESCALATED`), and the **deferral line** naming the risk handed downstream.
    - Reconcile the two: the implementer's `RED proof (author's)` must match the test-author's, its `Contract test author` must name the independent author (not "self", except the Class E solo-mode inline exception), and `Weakened?` must be `NO`. A GREEN with no matching independent RED, or a `Weakened?` that isn't `NO`, means the split was bypassed — treat the task as NOT done regardless of a green suite.
  - **`solo` task:** ONE block, from the implementer, still complete: the Test-evidence + STATUS blocks showing the tier it classified, its own RED-first proof (or the Tier-B line), `Contract test author: self — solo mode (plan: Test-author: solo)`, `Weakened? n/a — self-authored (solo mode)`, and the deferral line. There is no second author's block to reconcile against — the independent check for a `solo` task is NOT this step; it is the cluster review gate (Step 2.8) + the phase-close test-effectiveness audit (Stage 3), per `<test_dev_split>`.

  Those blocks — visible in the reports and commit bodies, one or two per task depending on mode — ARE the gate.

  Do **not** require either subagent to literally re-invoke `Skill("testing-workflow")` once per task: the gate skill itself states that *"Re-invoking the Skill tool once per task is **not** the discipline."* Each subagent reads testing-workflow **once per session** to internalize it; per-task re-invocation is the ghost ritual `subphase-a-0of7` retired.

If any required block or line is missing for the task's mode, or a `split` task's two blocks don't reconcile, treat the task as DONE_WITH_CONCERNS or NEEDS_CONTEXT per the upstream skill's status handling. Do not mark complete without them. The `subagent-stop.py` hook (tests actually ran) is a backstop on both modes, not the primary mechanism — the recorded blocks are.

**Step 2.6b — Standards gate at every code-task close.** Alongside the testing gate, invoke `netdust-agent:standards-gate`: run the project's configured linter/formatter (eslint/prettier/biome, or phpcs/php-cs-fixer) on the touched files and record a `Standards: clean | <N fixed> | n/a — no linter` line in the Test-evidence block. The same `subagent-stop.py` hook backstops it: it blocks a code-editing subagent's close when a linter is configured for the project but was never run. If no linter is configured, the gate (and the backstop) no-op — do not impose a style of your own.

**Step 2.7 — Bug-fix bundles (Class C) get one TDD cycle per finding; the D1 rule decides split vs solo per finding.** Each `/code-review` or `/security-review` finding is a behavior change → the Iron Law applies to its reproduction. A finding on a 1a trigger surface → **split reproduction**: the `test-author` writes the RED test that **reproduces** the bug (the failing case from the finding) independently, then the `implementer` invokes `superpowers:systematic-debugging` and fixes to green on that reproducing test without weakening it. Any other finding → **solo reproduction**: the implementer itself authors the reproducing RED test, then fixes to green — same `superpowers:systematic-debugging` discipline. Either way: one bug per cycle, one systematic-debugging invocation per bug, re-sweep between — that rule is unchanged by the mode. Authoring the reproduction independently on a 1a finding is what proves the fix addresses the reported defect and not a convenient near-miss. "I already see the fix, the phases are obvious here" is the exact rationalization the debugging skill's red-flags table names. (2026-05-30, Sub-phase F: bundling I2+I3 into one cycle drifted the process even though outcomes were sound. Slug: `one-cycle-per-bug`.)

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

Stage 2 dispatch shape is read from the task's `Test-author:` mode: a `split` task dispatches in PAIRS (`test-author` RED, then `implementer` GREEN — addenda A and B); a `solo` task dispatches ONCE (`implementer` doing both — addendum C). Append the matching addendum verbatim at the bottom of the dispatch prompt; it supplements (does not replace) the upstream template.

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

**C — solo implementer dispatch addendum** (append to a `Test-author: solo` task's single dispatch; the implementer plays BOTH roles):

```
---

## Netdust addendum — solo implementer close-out (RED-first, self-authored)

This task's plan line reads `Test-author: solo` — you author your own
contract test AND green it. RED-first is still the Iron Law; solo mode
changes WHO authors it, not whether it happens. Before reporting STATUS,
you MUST:

1. Apply the `testing-workflow` discipline (read it once per session):
   classify the task's risk tier (A/B) from the ACCEPTANCE CRITERIA + threat
   model — not from code you're about to write. Apply the erosion guard
   literally (guard/parser/state-machine = Tier A regardless of line count).
   You do NOT get to re-decide `solo` vs `split` — that mode arrived from
   the plan via the controller; if you believe this task should have been
   `split` (a security-boundary Tier-A task marked solo by mistake), escalate
   `NEEDS_CONTEXT` naming why — do not silently self-downgrade OR
   self-upgrade the mode.

2. Derive the contract from the criteria / threat-model mitigation, never
   from code you intend to write. For Tier A, write the RED-first BEHAVIORAL
   test incl. the denial path. For a brand-new symbol, create ONLY the
   minimal signature shell first, prove it fails behaviorally, THEN
   implement — never author the test after the logic already passes it.

3. Watch RED, then implement to GREEN on that same test. You may ADD edge
   tests. Run the affected app's full unit suite from the app's own
   directory, then static analysis on touched files, then
   `netdust-agent:standards-gate` on touched files if a linter is
   configured.

4. End your final message with these two blocks, verbatim and complete:

   ## Test evidence
   - Tier: <A | B> — <one-sentence justification (erosion guard applied)>
   - Contract test author: self — solo mode (plan: Test-author: solo)
   - Test file(s): <paths, or "none — Tier B">
   - RED proof: <command> → <1-3 line snippet showing BEHAVIORAL fail>
     (Tier B: replace with `no unit test: Tier B, <reason>`)
   - Weakened? n/a — self-authored (solo mode)
   - GREEN proof: <command you ran> → <1-3 line snippet showing the test now passes>
   - Seam test (if this task WIRES a piece into the real chain):
     <1 un-mocked-chain assertion + 1 negative/adversarial case, or "n/a — not a wiring task">
   - Suite delta: <app> was <N>, now <M>, <K> fails
   - Typecheck: <command> → <clean | errors>
   - Standards: <clean | N fixed | n/a — no linter> (cmd: <what you ran>)
   - Deferral: Risk this does NOT cover: <concurrency | adversarial-input |
     cross-actor | multi-component | un-mocked-seam | none> → <integration-gate | /code-review | invariant-auditor | /shakeout>
     Independent check for this solo task happens at the cluster review gate
     (Step 2.8) and the phase-close test-effectiveness audit, not here.

   ## STATUS
   STATUS: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
   COMMIT: <sha>
   FILES TOUCHED: <list>
   DIVERGENCES FROM PLAN: <list, or "matched plan verbatim">

Missing any item, or a `Weakened?` line that isn't the solo-mode form above,
= task NOT done. Do not rationalize. Do not substitute prose for the
structured form.

---
```

For **doc-only or tooling-only tasks** (no code-touching changes) there is no test to author — dispatch only the implementer, which may omit the Test-evidence block but MUST still include the STATUS block.

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
| "This is a `Test-author: split` task — I'll just have the implementer write its own test, it's faster than two dispatches" | That is the exact self-grading flaw the test/dev split removes (`<test_dev_split>`, slug `self-grading-split`). The coder shaping its own test lets the denial path vanish and a guard get self-excused to Tier B. Dispatch `test-author` FIRST, then the implementer. Two commits, two agents — non-negotiable for a `split` task, even a `split` Class E. |
| "The RED test the author wrote is a bit off — I'll just tweak it so it passes" (`split` task) | Editing/weakening the contract test to reach green moves the grader one seat over — the split is defeated. The implementer's `Weakened?` line must be `NO`. If the test is genuinely wrong, escalate `NEEDS_CONTEXT`; the author fixes it, not the implementer. |
| "This is a brand-new function so the RED is just 'module not found' — good enough" | Import-error RED proves nothing about the contract, on either mode. Whoever authors the test (test-author on `split`, the implementer itself on `solo`) writes the minimal signature shell (declaration + sentinel body) so the RED is BEHAVIORAL (`expected 403, got not-implemented`). Shell only — no logic; the logic comes after, in the same or the next dispatch depending on mode. |
| "It's obviously just glue, I'll mark it Tier B and skip the test" | The tier call belongs to whoever is authoring the test — the independent `test-author` on a `split` task, the implementer itself on a `solo` task — never to a coder deciding its OWN code doesn't need one after the fact. Self-classifying your own code Tier B to dodge the test is the loophole the split closes regardless of mode; a guard/parser/state-machine is Tier A no matter how short. |
| "This task looks like plain glue to me, I'll just treat it as solo even though the plan says split" (or the reverse) | The mode is NOT the executing agent's call, ever. `Test-author: split \| solo` was decided by the planner at plan time under the D1 rule and machine-checked by `gate-check.py` before you started. An implementer (or test-author) deciding its own task's mode is the exact self-downgrade loophole the machine check exists to close — read the field, don't re-derive it. |

</red_flags>

<success_criteria>

This skill has succeeded when:

1. The seam precondition was verified at entry — `gate-check.py` run fresh (exit 0) + human approval confirmed for Class A/B; the class-specific ticket for C/D/E.
2. The execution upstream skill was invoked via the Skill tool and its checklist followed.
3. Every code task's dispatch shape MATCHED its `Test-author:` mode from `tasks.md`, read by the controller and never re-decided by a dispatched agent: a `split` task ran as a `test-author → implementer` PAIR — an independent test-author authored the RED test and reported `## Test contract` + `RED_READY` in its own commit BEFORE the implementer, and the implementer greened that same test with `Weakened? NO`; a `solo` task ran as ONE `implementer` dispatch that authored its own RED-first test and greened it, recording `Contract test author: self — solo mode` and `Weakened? n/a — self-authored (solo mode)`. Every dispatch carried its matching verbatim addendum (A/B for split, C for solo). No `split` task's agent authored and greened its own contract test (except the recorded Class E solo-mode inline exception, where the controller — not the coder — authored the RED), and no task's mode was decided by the agent executing it.
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
| `harnessed-development` | **ROUTER / UPSTREAM.** Classifies the work (A–F); every code-changing class's execution lands here (Class F never builds — it produces no artifact for this spine). |
| `planning` | **UPSTREAM — the other spine.** Produces the seam artifact this skill's precondition demands (approved `tasks.md` + gate-check GREEN). A red/missing ticket routes work back there; so does a mid-execution discovery that the plan's shape is wrong. |
| stack sub-plugins | **OVERRIDE LAYER.** Stack-specific execute/shake-out skills, reviewers, and test runners replace the generics — see `<stack_overrides>`. |
| `superpowers:subagent-driven-development` | **STAGE 2 — primary branch.** Parallel-independent tasks — dispatched per-task mode: `test-author → implementer` pairs for `split` tasks, single `implementer` dispatches for `solo` tasks (`<test_dev_split>`). |
| `superpowers:executing-plans` | **STAGE 2 — secondary branch.** Sequential / solo execution, still dispatched per the task's `Test-author:` mode. |
| `superpowers:test-driven-development` | **STAGE 2 — Class E branch.** The single red→green cycle — mode defaults `solo` (RED authored by the implementer, or the controller for a trivial inline change); a security-boundary file is Class D, always `split`. |
| `test-author` (agent) | **STAGE 2 — RED half, `split` tasks only.** Dispatched ONLY when the task's mode is `split`: owns the tier decision + writes the RED-first behavioral test (+ signature shell) from the contract, before the implementer. Reports `## Test contract` + `RED_READY`. The reason no agent grades its own homework on security-boundary work (slug: `self-grading-split`, superseded tier-conditionally by `tier-conditional-split`). |
| `implementer` (agent) | **STAGE 2 — GREEN half (`split`) or the whole cycle (`solo`).** On `split`: greens the test-author's RED without weakening it, reports Test-evidence + STATUS with `Weakened? NO`. On `solo`: authors its own RED-first test AND greens it, reporting `Contract test author: self — solo mode` and `Weakened? n/a — self-authored (solo mode)`. Never chooses which mode applies to its own task. |
| `superpowers:systematic-debugging` | **STAGE 2 (Class C).** One invocation per bug, on the implementer half — after the reproducing RED test exists (test-author on a 1a-surface finding, the implementer itself otherwise). |
| `testing-workflow` | **STAGE 2 MANDATORY GATE.** Per-task close, mode-dependent: on `split`, the test-author classifies the tier + proves RED-first and the implementer greens + records the deferral line (two reconciled blocks); on `solo`, the implementer does all of that itself in one block, with the independent check moved to the cluster review gate + phase-close test-effectiveness audit. Plus phase-complete. |
| `standards-gate` | **STAGE 2 GATE (Step 2.6b).** Project linter on touched files at each code-task close; backstopped by `subagent-stop.py`. |
| `test-effectiveness` | **STAGE 3 GATE.** Phase-close audit: green tests proved to *bite*; its manifest is the reviewers' convergence target. |
| `feature-acceptance` | **STAGE 3 (drive).** Drives the `## Acceptance flows` matrix `planning` authored at 1g — real browser / un-mocked wire. |
| `shake-out` | **STAGE 3.** Spec-close, after upstream final-review; panel composition read from the branch tier. |
| `superpowers:finishing-a-development-branch` | **STAGE 3.** After shake-out. |
| `compounding` | **STAGE 3 closer (step 6, spec-close only).** Harvests spec knowledge into PROPOSALS; report-only. |
| `/loop` + `loop-gate.py` + `spec-kit/loop-check.py` | **STAGE 2 DRIVER (optional).** The armed loop that runs execution unattended through `tasks.md`; drives *through* the gates, never around them. This spine owns the loop protocol. |
| `subagent-stop.py` hook | **BACKSTOP (both halves).** Blocks a code-editing subagent's close when no test command ran (test-author: the RED run; implementer: the suite) or when a configured linter was skipped. It cannot verify authorship independence (one invocation sees one transcript) — the dispatch order + two commits enforce that. Backstop, not primary — the reconciled blocks are. |
| `ntdst-execute-with-tests` (historical) | **DELETED (2026-06-05) — absorbed into the god-skill, whose execution half is now THIS spine.** Its triggers ("execute the plan", "work the plan") resolve here. |

**Calibration data behind these rules** (index: `skills/_shared/calibrations.md`):
- *Test/dev split (`self-grading-split`, history):* until 2026-07-04 the implementer authored its own Tier-A test and self-reported the evidence that gated the task. RED-first only reordered the same author's two acts — the test drifts to fit the code, the denial path goes missing, a risky guard gets self-classified "Tier B, just wiring" by the agent that benefits from the skip. Fixed by `<test_dev_split>`: an independent `test-author` writes the RED from the contract before the implementer exists; the implementer greens without weakening. Two agents, two commits — the coder is no longer the grader. **This unconditional split later became the tier-conditional dispatch documented above** — see calibration `tier-conditional-split` (2026-07-04 evidence: split still fires for every security-boundary Tier-A task; the fix was scoping it, not removing it).
- *Verbatim addendum (`subphase-a-0of7`):* Sub-phase A — 0/7 subagents re-invoked the testing-workflow skill under a weaker one-liner, yet the work was correct. The lesson (2026-06-04): the audit trail must rest on the **structured blocks** the addenda demand, not on a per-task Skill-tool re-invocation — which is unverifiable from git and which the testing-workflow gate skill has itself retired.
- *Step 2.5 (`plan-drift-4x`), Step 2.7 (`one-cycle-per-bug`), Step 2.8 (`teardown-cluster`):* told in full at their steps above.

</integration>
