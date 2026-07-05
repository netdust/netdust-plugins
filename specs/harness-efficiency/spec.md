# Feature Specification: Harness efficiency tuning (empirical adjustments from the 2026-07-04 runs)

> **netdust override template.** Overrides spec-kit's core `spec-template.md`. Produced by
> `/speckit.specify` (wrapped by the `spec-authoring` skill, Stage 0.5). Describes **what**
> and **why** — **no technology stack** (that is deferred to `plan.md`). All
> `[NEEDS CLARIFICATION]` markers must be resolved by `/speckit.clarify` before a plan is
> written — that is the Stage 0.5 HALT gate.

**Branch:** `main` (planning artifacts only — no implementation this session) · **Created:** 2026-07-05 · **Status:** Clarified

## Problem / why

The 2026-07-04 runs produced the harness's first empirical self-measurement, and four costs showed up that the discipline does not need to pay:

1. **The unconditional test-author/implementer split taxes every task at the price meant for risky ones.** In the run-observability run the split doubled dispatches and added 4–6 min sequential latency per task; the only incident of the day was the test-author's own defective fixtures (T04, ~15 min + 3 extra dispatches to repair), while the review gates + test-effectiveness audit independently caught every real bug. Independent authorship earns its cost exactly where self-graded tests are proven bad practice — auth/guards, untrusted parsing, migrations, money, security-boundary logic — and nowhere else.
2. **Background planner dispatch fights a present, steering human.** In the Sofie session, background planner agents finished plans the user invalidated within 10 minutes (two pivots); each correction cost a background-agent round-trip. Meanwhile the plan-review ladder before UNATTENDED execution caught 4 real loop-breakers — the highest-ROI gate of the day. The dispatch mode must follow human presence, not habit.
3. **Vision-stage briefs get routed into full planning ceremony.** In the teacher-app session, a "we don't implement today" brief was classified into the plan spine; the user waited 30+ minutes asking "still planning?". The intake table has no class for shaping-only work.
4. **"Is the orchestration worth it" required hand-mining session JSONLs.** The run trace records what happened but not what it cost — no per-stage wall-clock, no per-dispatch token totals.

## User stories

- As the harness operator (Stefan), I want the independent test-author dispatched only for the tasks whose risk warrants it — with the boundary fixed at plan time so no implementer can downgrade its own task — so that routine tasks stop paying double dispatches and sequential latency for a control that wasn't catching their bugs anyway.
- As the harness operator steering an interactive session, I want planning to happen inline in the conversation while I'm present and requirements are moving, so that a pivot costs a sentence instead of a background-agent round-trip — and I want the full review ladder to stay mandatory whenever the output feeds an unattended run.
- As the harness operator describing a vision, I want intake to recognize shaping-only work and route it to brainstorming with at most a notes doc, so that no plan artifact is manufactured for work that will not change code this session.
- As the harness operator (and `/evaluate`), I want per-stage wall-clock and per-dispatch/per-stage token totals compiled mechanically from the run log and the session transcripts, so that the orchestration-overhead question is answered from artifacts, not scrollback archaeology.

## Functional requirements

- **FR-1 (tier-conditional test/dev split):** The BUILD spine MUST dispatch the independent test-author only for tasks the PLAN marks as requiring it (security-boundary Tier A work: auth/guards, untrusted parsing, migrations, money — aligned with the existing testing-workflow tier definitions and erosion guard). All other tasks (Tier B, and Tier A logic outside those categories) MUST run as a single implementer performing RED-first TDD itself — the RED test remains mandatory, authored by the implementer — with the cluster review gate + test-effectiveness audit named as the independent check.
- **FR-2 (plan-time mode decision, machine-visible):** The per-task format MUST gain an explicit test-author mode field (`split`/`solo`), decided by the planner at plan time and read by the CONTROLLER at dispatch time. No run-time agent may decide, change, or downgrade its own task's mode. The gate checker MUST verify the field: present on every task when used at all, valid values only, and a stated reason required for a Tier-A task marked solo. Pre-existing feature dirs without the field MUST NOT retro-fail.
- **FR-3 (presence-aware planning mode):** The PLAN spine MUST plan inline (main conversation / foreground) when the human is present and actively steering, and dispatch background planner / plan-correction agents only when the human has stepped away or the output feeds an unattended run (armed `/loop`, tmux loop, scheduled). The plan-review ladder before unattended execution MUST remain mandatory and be explicitly named as such.
- **FR-4 (brainstorm-only intake class):** The intake router MUST offer a class for shaping / vision-stage exploration (no code will change this session) that routes to brainstorming/refining-ideas only, produces at most a scope sketch / notes doc, explicitly NO spec/plan/tasks artifact and NO gate ceremony, and names the promotion path (re-enter as Class A when it becomes real work). A red-flag row MUST warn against manufacturing a plan artifact for a described vision.
- **FR-5 (wall-clock report):** The system MUST compute wall-clock durations per stage/gate segment from the timestamps already recorded in the per-feature run log, and render them on demand without changing the default trace rendering.
- **FR-6 (token/cost report):** The system MUST compile per-dispatch and per-stage token totals (output, cache-read, cache-creation, input) from the local Claude Code session transcripts (main session + subagent transcripts), joined to the run trace by timestamp windows. It MUST treat the transcript directory as strictly read-only, MUST degrade cleanly when transcripts or the run log are absent (clean exit + one-line note, never a crash, never fabricated numbers), and MUST only aggregate counts — never reproduce transcript message content.
- **FR-7 (version):** The plugin MUST be versioned 0.7.0 → 0.8.0 (minor — behavior change in the agent dispatch protocol), with the plugin and marketplace manifests' descriptions corrected where they currently state the unconditional split.

## Acceptance criteria

> These become the contracts the Tier-A tests assert (testing-workflow). Write them so a
> test can be derived from each — concrete and falsifiable, including denial/negative paths.

- [ ] Given a `tasks.md` whose every task carries a test-author mode line with a valid value, the gate checker passes; given one task missing the line while siblings carry it, the check FAILS naming the task; given a Tier-A task marked `solo` with no stated reason, the check FAILS; given a Tier-B task marked `split`, the check WARNs but passes; given a pre-0.8 `tasks.md` with no mode lines at all, the check WARNs but passes (never retro-fails an existing feature dir); a fenced format example never counts as a task.
- [ ] Given the new per-task mode line, the existing task parsers (gate check, loop ledger, rubric compiler) produce byte-identical results to before — the field lives on continuation lines they already ignore.
- [ ] Given a run log with N timestamped events, the durations rendering lists each consecutive-event segment with its wall-clock delta plus a total; given a log with fewer than 2 parseable events, it reports that durations are not derivable and exits cleanly; without the durations option, the trace rendering is byte-identical to today; a corrupt line is skipped, never crashes.
- [ ] Given a fixture transcript dir (main session JSONL + subagent JSONLs + metadata) and a fixture run log, the cost report emits per-dispatch totals matching the summed usage fields of each transcript's assistant lines, attributes each dispatch to the correct run-log timestamp window, and parses both `Z`-suffixed and `+00:00`-suffixed timestamps; given NO transcript dir (or no session overlapping the run window), it exits 0 with a "no transcript found" note and no report; given transcripts but NO run log, it emits per-dispatch totals with a "per-stage attribution skipped" note; after any invocation the transcript dir's contents are unchanged (nothing created, nothing modified — read-only, asserted); a malformed transcript line is skipped, never crashes.
- [ ] Given the shipped skills prose: the BUILD spine's Stage 2 instructs the controller to read the per-task mode from `tasks.md` and dispatch split pairs only for `split` tasks; the solo path still demands a RED-first test with evidence blocks naming self-authorship under plan authority; the PLAN spine states the presence rule and the mandatory pre-unattended review ladder; the intake table contains the shaping class with its promotion path and red-flag row. (Prose contracts — verified at the cluster review gates, not by unit test.)

## Security-relevant surfaces  [pre-flag for the plan's threat model]

> Not a threat model (that is authored at plan-time). This is an early flag so the planner
> knows the `threat-modeling` gate (1a) will fire. Check any that apply:

- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [x] None of the above — *all inputs are local harness-authored artifacts (`tasks.md`, `run-log.jsonl`, gate-check JSON) plus local Claude Code session transcripts written by the same-trust-domain local process; no network, no credentials, no cross-actor data. Privacy note (not a threat surface): transcripts can contain sensitive session content — the cost tool reads them strictly read-only and emits only aggregate token counts and metadata (agent type, description, timestamps), never message content.*

## Clarifications

> Filled by `/speckit.clarify`. Each resolved ambiguity recorded as Q→A. The Stage-0.5 gate
> HALTS if any `[NEEDS CLARIFICATION: …]` marker remains anywhere in this spec.

- Q: Who decides split vs solo — a third test tier, or a separate field? → A: A separate per-task field (`Test-author: split|solo`), not a new tier. The `[Tier A|B]` vocabulary and the testing-workflow tier rule stay untouched; the field encodes the security-boundary sub-distinction *within* Tier A ("A-lite" = real logic, no 1a-category surface → solo with a stated reason). Keeps gate-check's tier regex and every downstream consumer stable.
- Q: What is the independent check for solo tasks, since the coder authors its own RED? → A: The cluster review gate + the phase-close test-effectiveness audit — both already exist and both independently caught every real bug in the 2026-07-04 evidence. The honesty ledger in the BUILD spine must state this openly: solo mode reintroduces self-authorship BY DESIGN for non-security tasks and moves the independent check downstream.
- Q: Does Class E keep the mandatory split? → A: No — Class E follows the same rule: solo implementer RED-first by default, split only if the change touches a 1a-category surface (which makes it Class D anyway, where the diff threat model names the contract). The "controller authors the RED inline" escape hatch remains available but is no longer the mandated floor.
- Q: Wall-clock report — new script or a flag on an existing one? → A: A `--durations` flag on the trace renderer (`run-trace.py show`). It is derived *rendering* of data the log already holds, not grading (run-score) and not new state (append). Per-task wall-clock is deliberately NOT derived from the run log (it has no per-task spans, by the run-observability clarification); per-dispatch wall-clock comes from the transcripts via the cost tool instead.
- Q: Does the cost report write an artifact like run-rubric.md? → A: No — stdout only for v1. Token totals are machine/session-specific (transcript dirs differ per machine), so committing them as a spec artifact is misleading; `/evaluate` or the operator captures the output when comparing runs. Revisit only if cross-run comparison shows a real need.
- Q: Presence-aware planning — who applies the rule, the router or the spine? → A: The PLAN spine (its persona-dispatch guidance), because that is where "dispatch `planner` or run inline" is decided today. The router's job stays classify-and-route. Note: the operator's global CLAUDE.md rule 0b currently mandates always dispatching the planner persona — that file is outside this repo and must be reconciled by the operator after this ships (named in the plan as a follow-up, not a task).
- Q: New class letter for shaping work? → A: **F — Shaping / vision-stage exploration.** Appended to the dial (never renumbering A–E), with the explicit promotion path "when it becomes real work, re-enter intake as Class A".

## Out of scope

- Any change to the testing-workflow tier definitions themselves (Tier A/B boundaries, erosion guard, litmus) — the field composes with them, it does not amend them.
- Dollar pricing in the cost report — token counts and wall-clock only; pricing varies by model/plan and belongs to the consumer of the numbers.
- OpenTelemetry or any network export of trace/cost data; daemons; dashboards.
- Rewriting `/evaluate` or `/shakeout` around the new reports — they may point at them; no behavior rewrite.
- Editing the operator's global `~/.claude/CLAUDE.md` (outside this repo) — named as a post-ship follow-up for the operator.
- Editing per-task span emission into the run trace — per-dispatch timing comes from transcripts.
- Any new gate or HALT — every change here removes or scopes ceremony, or reports; nothing new blocks (standing rule: new gates must replace or merge, never append).

## Open questions / [NEEDS CLARIFICATION]

(none — section intentionally empty; all shape questions resolved under Clarifications)
