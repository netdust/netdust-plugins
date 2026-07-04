# HANDOFF — Plan/Build split refactor of `harnessed-development`

**Status:** RESOLVED — executed 2026-07-04 (agent 0.5.0), option 1, Stefan's pick. See the ADR at the bottom.
**Created:** 2026-06-23
**Branch:** `claude/writing-plans-thread-modeling-Se2Sx` (design) → `claude/handoff-split-god-skill-ueb1kd` (execution)
**Source of truth:** this file. Plugin path: `plugins/netdust-agent/`.
**Origin:** Session reviewing the harness (spec-kit graft + "The Missing Layers" PDF). Stefan's critique at the end: *"this harness is trying to do too much. There's a clear distinction between planning and building. I don't know if this is really clear in the harness."* He is right. This handoff captures the agreed direction so a fresh session can execute it.

---

## The critique (the thing to fix)

`harnessed-development` is a **single god-skill** that spans the entire lifecycle — Stage 0 (brainstorm) → 0.5 (spec) → 1 (plan) → 1.5 (analyze) → 2 (execute) → 3 (shake-out/finish). Planning and building are **stages inside one skill**, not two phases that meet at a clean boundary. Symptoms:

1. **The `tasks.md` handoff — the natural plan/build seam — is buried inside Stage 2** instead of being the contract between two entry points.
2. **The intake table (Classes A/B/C/D)** exists only because one skill must fork its own behaviour by situation. That branching is the symptom of one entry point pretending to be four.
3. **History confirms the instinct:** there used to be a separate execution skill, `ntdst-execute-with-tests`. It was **deleted and absorbed** into `harnessed-development` (see the skill's `<integration>` note + `CLAUDE.md`). The harness deliberately fused build into plan. Stefan is now questioning that fusion — correctly.

**Why the fusion happened (must preserve this):** it bought *gate-coverage durability* — one skill sequences every gate so none is skipped (a security edit once shipped with no threat model because gates were keyed to prose reminders). Any split MUST keep that property.

---

## Agreed direction

Split `harnessed-development` into **two spines** with an approved, gate-checked `tasks.md` as the **enforced contract** between them:

```
PLAN spine     brainstorm → spec → plan → threat-model/invariants → analyze
               OUTPUT: tasks.md + gate-check.py GREEN  ──►  STOP. Human approves.
               ═══════════════════ the seam ═══════════════════
BUILD spine    PRECONDITION: approved tasks.md + gate-check green
               execute → test → standards → shake-out → finish
               REFUSES to start without the gated artifact.
```

**The key idea — the seam enforces "no skipped gates."** The build spine won't run unless `spec-kit/gate-check.py` is GREEN on the plan. That is the *exact* durability the fusion was chasing, but achieved **structurally at the boundary** rather than by one skill sequencing everything. So the split gives a clean plan/build separation **and** keeps the original protection. Strictly better.

This also aligns the whole stack on one boundary that everything else already draws: `superpowers:writing-plans` vs `executing-plans`; spec-kit `spec→plan→tasks` vs `implement`; Claude Code plan-mode vs execution. `harnessed-development` is currently the *only* layer that blurs it.

---

## OPEN DECISION (Stefan to confirm before/at execution)

**Split shape** — three options, no final pick yet:
1. **Two skills + thin router** *(my recommendation)* — new `planning` + `building` skills; a minimal `harnessed-development` remains only as a backward-compatible router so existing trigger phrases ("build a feature", "execute the plan", etc.) still resolve to the right spine. Cleanest separation, least disruption to muscle memory and to handoff docs that name the old skill.
2. **Two skills, retire the god-skill** — fully replace `harnessed-development`; update `CLAUDE.md` + every reference. Sharpest boundary, most churn.
3. **One skill, hard seam** — keep one skill but insert an explicit STOP/approval gate at `tasks.md`. Smallest change; does NOT fix the "does too much" root cause. (Listed for completeness; weakest.)

**Scope:** Stefan expressed no preference between "ADR first" vs "just do the refactor." Recommendation: since this is a *reduction* (no new behaviour), a short ADR is cheap insurance, but proceeding straight to the refactor is defensible. Suggest: write the ADR section into THIS file, get a one-word go, then execute.

---

## Mapping the current stages onto the two spines

| Current (harnessed-development) | New home |
|---|---|
| Stage 0 brainstorm | PLAN |
| Stage 0.5 spec-authoring | PLAN |
| Stage 1 writing-plans + 1a threat-model / 1b invariants / 1c premise / 1d tiers / 1e sibling / 1f review-clusters | PLAN |
| Stage 1.5 spec-analysis (gate-check) | PLAN — **produces the GREEN that the seam checks** |
| **`tasks.md` (approved + gate-check green)** | **THE SEAM / contract** |
| Stage 2 execute (subagent-driven / executing-plans) + Step 2.6b standards-gate + testing gate | BUILD |
| Stage 3 test-effectiveness → shake-out → finish | BUILD |

- **Class A** (new feature) = run PLAN spine, stop at seam, then BUILD spine.
- **Class B** (execute an existing plan) = **BUILD spine only** — this is the cleanest proof the split is natural; Class B is already "building without planning," currently a sub-mode, should become its own entry point.
- **Class C** (bug-fix bundle) = BUILD spine, one TDD cycle per finding (no full plan).
- **Class D** (ad-hoc security one-liner) = a thin PLAN-gate (threat-model on the diff) → BUILD. Keep as a documented exception.

So A/B/C/D largely *dissolve*: "do I have an approved plan?" decides which spine you enter.

---

## Explicit DO-NOT (direction discipline)

- **Do NOT add `reliability-modeling` or `product-maturity-audit` gates now.** They were floated earlier this session from "The Missing Layers" PDF. Adding surface to an already-overloaded skill is the wrong direction. Revisit *only after* the plan/build split is clean — and even then most of the 14-layer content stays as **spec-time prompts, not gates**.
- The split is a **reduction**. If a step makes the two skills bigger than the one they replace, stop and reconsider.

---

## Current state of the branch (context for the refactor)

This branch already contains a completed **spec-kit graft** (3 phases, all committed + pushed). The graft IS effectively the planning-harness front end — the refactor should treat it as belonging to the PLAN spine.

- `docs/spec-kit-integration-adr.md` — the graft design.
- `spec-kit/overrides/{spec,plan,tasks}-template.md` — gate-bearing templates (PLAN output).
- `spec-kit/gate-check.py` — deterministic gate checker (**this is the seam's enforcement mechanism**). Tested by `tests/test_spec_gate_check.py` (10 cases, green).
- `spec-kit/setup.sh` + `commands/spec-kit-setup.md` — per-project installer.
- `skills/spec-authoring/SKILL.md` — Stage 0.5 (→ PLAN spine).
- `skills/spec-analysis/SKILL.md` + `commands/spec-analysis.md` — Stage 1.5 gate (→ PLAN spine; runs gate-check).
- `skills/constitution-bridge/SKILL.md` — constitution as a view over RULES/SOUL/invariants.
- `skills/standards-gate/SKILL.md` — Stage 2 close gate (→ BUILD spine).
- `hooks/subagent-stop.py` — testing + standards backstop (→ BUILD spine). Tests: `tests/test_subagent_stop.py` (33 cases), `tests/test_standards_gate_hook.py` (7 cases).
- `skills/harnessed-development/SKILL.md` — **the god-skill to split.** Read it first.

**Tests:** `bash plugins/netdust-agent/tests/run.sh`. Expect 4 modules green; `test_session_start` and `test_skill_audit_glob` FAIL for ENVIRONMENTAL reasons only (need a provisioned `~/.claude/plugins/` install) — they are NOT caused by this branch. Do not chase them.

---

## Concrete next steps for the refactoring session

1. **Read** `skills/harnessed-development/SKILL.md` end to end, plus `CLAUDE.md`'s "Cross-stack workflow" bullet.
2. **Confirm the split shape** with Stefan (the 3 options above). Default to option 1 (two skills + thin router).
3. **Author `skills/planning/SKILL.md`** — Stages 0 → 1.5, ending at the seam: it must STOP at an approved `tasks.md` with `gate-check.py` GREEN, and explicitly NOT execute. Move the 1a–1f gate text here.
4. **Author `skills/building/SKILL.md`** — precondition block FIRST: refuse to start unless a `tasks.md` exists and `gate-check.py` is green (cite Class B/C/D entry). Then Stages 2 → 3 (execute, testing gate, standards-gate Step 2.6b, shake-out, finish). Move the dispatch addendum + `/speckit.implement`-is-never-run red flag here.
5. **Reduce `harnessed-development`** to a router (option 1) or delete + update refs (option 2).
6. **Update** `CLAUDE.md`, `.claude-plugin/plugin.json` description, and the `<integration>` tables in the moved skills.
7. **Verify** `bash tests/run.sh` still 4-green; add a test asserting the building spine's precondition (gate-check-green) if practical.
8. **Commit + push** to `claude/writing-plans-thread-modeling-Se2Sx`. Do NOT open a PR unless Stefan asks.

---

## Voice / discipline reminders for the next session

- `SOUL.md`: pushback over flattery; name trade-offs; YAGNI — no infrastructure before validated need. This refactor is the YAGNI principle applied to the harness itself.
- This is Stefan's call on shape. Ask one sharp question if blocked, then proceed.
- Keep the change a **reduction**. The win is two clear, smaller skills with a real review checkpoint at `tasks.md` — not a third system.

---

## ADR — decision + execution record (2026-07-04, agent 0.5.0)

**Decision (Stefan):** Option 1 — two skills + thin router.

**What shipped:**
- `skills/planning/SKILL.md` — PLAN spine, Stages 0 → 1.5. Ends at THE SEAM (approved `tasks.md` + `gate-check.py` GREEN + human approval) and explicitly never dispatches or invokes `building` — the human bridges the seam.
- `skills/building/SKILL.md` — BUILD spine, `<precondition>` FIRST: for Class A/B it re-runs `gate-check.py` itself at entry (an assertion in a transcript is not an exit code) and refuses on red/missing, routing back to `planning`. Then Stages 2 → 3, the verbatim dispatch addendum, and ownership of the armed `/loop` protocol (the loop is a Stage-2 driver, so it lives with the spine that runs Stage 2).
- `skills/harnessed-development/SKILL.md` — reduced to the intake router: class dial A–E → spine, the seam statement, intake-level red flags, and a historical mapping (old "Stage N" citations: 0–1.5 → `planning`, 2–3 → `building`). All old trigger phrases still resolve here.
- **Class dissolution, as predicted:** A = both spines with the seam between; B = `planning` freshness-review mode → seam → `building`; C/E = `building` directly; D = `planning`'s 1a on the diff → `building`. The intake table routes instead of forking one skill's behaviour.
- **Gate merge (constraint from the 2026-07-04 session):** 1d/1f/1h presented in `planning` as ONE task-shaping gate with three facets. Labels kept for compatibility with `gate-check.py`, the override templates, and `/shakeout` — a prose merge, zero mechanical churn.
- **Reduction check:** god-skill was ~375 lines; router (~70) + planning (~185) + building (~275, incl. the verbatim addendum block it inherited whole) ≈ 530 raw lines, BUT per-invocation context is what the rule protects: a Class-E tweak now loads ~70+~275 instead of ~375 of which most was plan-stage prose, and a planning session loads no execution machinery at all. War-story retellings were trimmed to slug cites per the 0.4.1 calibration rule; canonical homes moved with their gates (calibrations.md updated).
- **Naming:** `planning`/`building` are gerunds on the harness side — accepted as named exceptions (alongside the pre-existing `threat-modeling`/`compounding`) and recorded in CLAUDE.md's naming rule; the handoff's own names kept.
- **References:** updated in netdust-agent (CLAUDE.md, README, plugin.json, marketplace.json, agents planner/implementer, commands loop/shakeout/spec-kit-setup, hooks subagent-stop/loop-gate, spec-kit templates + setup.sh + README, sibling skills' integration tables, calibrations index). Sibling plugins (wp/statamic/core) deliberately NOT touched — their `harnessed-development` references still resolve via the router (the exact disruption-avoidance option 1 was chosen for); update them opportunistically on their next own version bump.
- **Enforcement gain vs the fusion:** the durability the 2026-06-05 fusion bought by one skill sequencing everything is now structural — `planning` cannot finish without the machine-checked artifact, `building` cannot start without re-checking it. A new deterministic test (`tests/test_split_seam.py`) asserts the seam wiring.
