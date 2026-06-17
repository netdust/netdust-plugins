# ADR — Grafting spec-kit onto the netdust harness

**Status:** PROPOSED — design locked, implementation not started
**Created:** 2026-06-17
**Source of truth for this plan:** this file. Source repo: `github.com:netdust/netdust-plugins`, plugin path `plugins/netdust-core/`.
**Origin:** Evaluation of [github/spec-kit](https://github.com/github/spec-kit) (Spec-Driven Development) against the netdust-core harness. Branch `claude/writing-plans-thread-modeling-Se2Sx`.
**Decisions taken (Stefan, this session):**
- **Integration = WRAP spec-kit** (install `.specify/`, sequence the real `/speckit.*` commands, inject gates via override templates). Not a native port.
- **Build order = this ADR first**, then skills.
- **Goal restated:** strengthen the harness, do not replace it. Primary aim = high-quality tested code that respects given coding standards.

---

## Why

The netdust harness is **execution- and verification-heavy, spec-light**. `harnessed-development` defers the entire front end to `superpowers:brainstorming` (Stage 0) and `superpowers:writing-plans` (Stage 1), then concentrates its value on the back end: threat-modeling gate, per-task `testing-workflow` tiers, review-cluster sizing (1f / Step 2.8), `test-effectiveness`, `shake-out`, and the deterministic `subagent-stop.py` hook.

spec-kit is the mirror image — **spec-heavy, execution-light**. It adds exactly what the harness lacks:

| spec-kit capability | Gap it fills in the netdust harness |
|---|---|
| `/speckit.specify` → `spec.md` | A real *what/why* artifact (user stories, functional reqs). The harness jumps near-straight to task breakdown. |
| `/speckit.clarify` | Coverage-based questioning that kills ambiguity **before** planning. Stage 0 brainstorm is far thinner. |
| `/speckit.analyze` | Cross-artifact consistency (spec ↔ plan ↔ tasks). The harness has nothing at this altitude. |
| `research.md`, `data-model.md`, `contracts/` | Structured plan artifacts vs. the harness's single plan file. |

Conversely, spec-kit's **back end is unenforced** relative to ours: `/speckit.implement` runs tasks flat with no proactive threat model, no Tier-A RED-first denial tests, no review-cluster HALT, no `subagent-stop` backstop. So the integration is asymmetric by design.

**The keystone invariant (non-negotiable):** spec-kit owns **spec → plan → tasks**; the netdust spine owns **execute → verify → finish**; the handoff is `tasks.md`. **`/speckit.implement` is never invoked** — it would swap our enforced Stage 2 for an unenforced one.

---

## The two structural problems this graft is designed to solve

1. **The harness's non-test gates are skill-honored, not machine-checked.** Only the testing gate has a deterministic hook. Threat-model (1a), review-cluster sizing (1f), and architecture-invariants (1b) fire only because `harnessed-development` sequences them — a session that under-honors the skill can skip them silently. **`spec-kit:analyze` + gate-bearing templates turn these into mechanically verified artifact properties.**
2. **"Respect coding standards" (goal #2) is advisory only.** The mandatory close-out runs `tsc --noEmit` (a typecheck) — there is no `eslint`/`prettier`/`phpcs` gate. Conventions live in stack skills + review agents as suggestions. **`constitution-bridge` (declarative) + `standards-gate` (enforced) close this.**

---

## Command-by-command disposition

| spec-kit command | Disposition | Rationale |
|---|---|---|
| `/speckit.constitution` | **ADAPT** | Do not author a fresh constitution. `constitution-bridge` generates `constitution.md` as a *view* over `RULES.md` + `SOUL.md` + `architecture-invariants`. One source of truth, no fork. |
| `/speckit.specify` | **KEEP** (wrapped by `spec-authoring`) | Fills the missing what/why spec. |
| `/speckit.clarify` | **KEEP** (wrapped by `spec-authoring`) | Coverage-based clarification is the single biggest gap-filler. |
| `/speckit.plan` | **KEEP, with override templates** | Produces `plan.md` etc., but from `netdust-spec-templates` so the harness gates are baked in. |
| `/speckit.tasks` | **KEEP, with override templates** | `tasks.md` carries review-cluster markers + per-task test-tier lines. This is the handoff artifact. |
| `/speckit.analyze` | **KEEP** (wrapped by `spec-analysis`) | Cross-artifact consistency **plus** verification that the gate-sections landed. |
| `/speckit.checklist` | **KEEP (optional)** | Useful quality checklists; no conflict. |
| `/speckit.implement` | **REJECT** | Bypasses every Stage-2 gate. Handoff stops at `tasks.md`; Stage 2 takes over. |
| `/speckit.taskstoissues` / `converge` | **DEFER** | Revisit once the core seam is proven. |

---

## Proposed skills (3 new + 2 supporting + 1 edit)

Each new skill is a **sequencer** in the existing house style: it loads the spec-kit command, then adds the netdust gate around it. None duplicates spec-kit content.

### 1. `spec-authoring` (new) — Stage 0.5
- **Wraps:** `/speckit.specify` + `/speckit.clarify`.
- **Slots in:** after Stage 0 brainstorm, before Stage 1 plan.
- **Output:** `specs/<feature>/spec.md` (what/why, user stories, functional reqs — **no tech stack**).
- **Gate:** HALT if any `[NEEDS CLARIFICATION]` marker survives. A plan may not be written against an under-specified spec. (Mirrors `threat-modeling`'s "TBD = invisible to review" rule.)
- **Trigger:** Class A work where intent is concrete enough to specify but not yet planned.

### 2. `spec-analysis` (new) — Stage 1.5
- **Wraps:** `/speckit.analyze`.
- **Slots in:** after Stage 1 (plan + 1a/1b gates), before Stage 2 execute.
- **Gate (two-part):**
  - (a) spec ↔ plan ↔ tasks are consistent (spec-kit's native job);
  - (b) **the netdust gate-sections are present** — `## Threat model` exists iff the 1a trigger list matched; every phase >~4 tasks or containing an irreversible/security step has `── REVIEW GATE ──` cluster markers; every task line carries a test-tier; cross-cutting tasks carry a `## Sibling-site audit` block.
- **Why it matters:** converts the harness's previously skill-honored gates into a **mechanical pre-execution check**. This is the enforcement upgrade for everything except tests.

### 3. `standards-gate` (new, optional — closes goal #2) — Stage 2 close + hook
- **Native** (no spec-kit equivalent).
- **Adds:** `eslint` + `prettier --check` (TS), `phpcs` (PHP/WP) to `testing-workflow`'s close-out, **auto-detected per stack** exactly like the unit runner already is; a `Standards: clean | <violations>` line in the Test-evidence block.
- **Backstop:** extend `subagent-stop.py` to block a close on standards violations, so it is machine-enforced, not honor-system — parity with the testing gate.
- **Declarative source:** the standard itself lives in the constitution (below), enforced here.

### 4. `netdust-spec-templates` (supporting artifact — the graft mechanism)
- **Delivered via spec-kit's override stack** (`.specify/templates/overrides/`, highest priority).
- **Files:** `spec-template.md`, `plan-template.md`, `tasks-template.md` overrides that bake in:
  - `plan-template.md`: a `## Threat model` placeholder (assets → attacks → mitigations → deferrals), invariant-citation block, sibling-site audit block.
  - `tasks-template.md`: per-task `Unit test (tier): …` line, per-phase `Integration gate: …` line, `── REVIEW GATE ──` cluster markers with the ~3–4-task cap.
- **Effect:** spec-kit's planner *emits artifacts that already carry the gates*, so Stage 1 collapses to a freshness review (Class B) and `spec-analysis` has fixed targets to verify against.

### 5. `constitution-bridge` (supporting) — setup-time
- **Wraps/replaces:** `/speckit.constitution`.
- **Generates** `.specify/memory/constitution.md` as a **view over** `RULES.md` + `SOUL.md` + the project's `ARCHITECTURE-INVARIANTS.md`. No independent governance content — single source of truth.
- **Hosts** the declarative coding standard that `standards-gate` enforces.

### 6. `harnessed-development` (edit — the keystone)
- Insert **Stage 0.5** (`spec-authoring`) and **Stage 1.5** (`spec-analysis`) into the spine.
- Define the **`tasks.md → Stage 2` handoff** explicitly.
- Add a `<red_flags>` row: *"I'll just run `/speckit.implement`" → that bypasses every Stage-2 gate (threat-model verify, test tiers, review-cluster HALT, subagent-stop hook). Never. The handoff is `tasks.md`; Stage 2 executes."*
- Note in `<stack_overrides>` that spec-kit artifacts + override templates are stack-agnostic and a sub-plugin may ship its own template overrides.

---

## Revised stage map (after graft)

```
Stage 0    brainstorm                     superpowers:brainstorming        (existing)
Stage 0.5  spec + clarify   ── NEW ──►    spec-authoring  → spec.md        (HALT on [NEEDS CLARIFICATION])
Stage 1    plan + gates                   superpowers:writing-plans
              1a threat-model  ┐          + netdust-spec-templates inject the
              1b invariants    ├─ baked   gate-sections into plan.md / tasks.md
              1d test-tiers    │  into
              1f review-clusters┘ templates
Stage 1.5  cross-artifact   ── NEW ──►    spec-analysis   → consistency + gate-presence check
Stage 2    execute                        subagent-driven-development + testing-workflow
              ▲ HANDOFF: tasks.md feeds here.  /speckit.implement is NEVER used.
              + standards-gate at task close (NEW), backed by subagent-stop.py
Stage 3    shake-out + finish             test-effectiveness → shake-out → finishing-a-branch  (existing)
```

---

## Build order (phased, each independently reviewable per 1f)

**Phase A — Foundation (no behavior change yet).**
1. Vendor/initialize spec-kit `.specify/` into the harness (decide: bundled in `netdust-core` vs. installed per-project by a setup command). 
2. `netdust-spec-templates` override files. 
3. `constitution-bridge` generator.
*Gate: a sample feature run produces spec/plan/tasks artifacts carrying the gate-sections.*

**Phase B — Front-end skills.**
4. `spec-authoring` (Stage 0.5) with the `[NEEDS CLARIFICATION]` HALT. 
5. `spec-analysis` (Stage 1.5) with the two-part consistency+gate-presence check.
*Gate: `spec-analysis` correctly fails a plan with a missing `## Threat model` on a triggering surface.*

**Phase C — Spine edit + standards enforcement.**
6. Edit `harnessed-development` to sequence 0.5 / 1.5 and document the `tasks.md` handoff + the `/speckit.implement` red flag. 
7. `standards-gate` + `subagent-stop.py` extension.
*Gate (irreversible/hook change → own review cluster): the hook blocks a close with a lint violation; existing testing-gate behavior unchanged.*

---

## Risks & open questions

- **Two planning vocabularies.** spec-kit's `tasks.md` (`[P]` parallel markers) vs. the harness's review-cluster model. The override `tasks-template.md` must reconcile these — `[P]` for parallelizable *within* a cluster, `── REVIEW GATE ──` *between* clusters. Verify they compose, don't collide. **(Phase A spike.)**
- **Bundled vs. per-project `.specify/`.** Bundling in `netdust-core` tracks one version; per-project install lets features pin. Lean bundled for consistency; revisit if a project needs to pin.
- **Upstream drift.** Wrapping ties us to spec-kit's command names/contract (already namespaced `/speckit.*`). Pin a version; re-test the override stack on upgrade.
- **Standards auto-detection breadth.** `standards-gate` must degrade gracefully when a project ships no linter config (warn, don't block) — mirror `testing-workflow`'s "no framework? set it up" stance but do not hard-fail a project that legitimately has none.
- **Altitude creep.** Three new stages risk making an already-heavy harness heavier. Keep `spec-authoring`/`spec-analysis` scoped to Class A; trivial/Class D work skips them entirely (same intake discipline already in `harnessed-development`).

---

## Success criteria

This graft has succeeded when:
1. A Class-A feature flows brainstorm → `spec.md` (clarified) → `plan.md`/`tasks.md` (gates baked in) → Stage 2 execution, with **no `/speckit.implement`**.
2. `spec-analysis` mechanically fails any plan that touches a 1a-trigger surface without a `## Threat model`, and any >4-task/irreversible phase without `── REVIEW GATE ──` markers — i.e. the non-test gates are now machine-checked, not skill-honored.
3. `standards-gate` blocks a task close on a real lint/format violation, with the standard sourced from the constitution — closing goal #2.
4. The existing testing spine (`testing-workflow`, `test-effectiveness`, `shake-out`, `subagent-stop.py`) is unchanged and still fires.
