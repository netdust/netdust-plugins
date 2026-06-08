---
name: compounding
description: Use at spec-close (after finishing-a-development-branch) to harvest what the work taught and write it where it compounds instead of evaporating — a proposed patch to docs/architecture/CODE-MAP.md (codebase knowledge) plus a scoped skill-audit over the skills touched this spec (tool knowledge). Report-only: emits a proposed-deltas manifest you approve; never auto-edits a CODE-MAP or a skill. The Stage 3 closer in harnessed-development, beside the memory/STATE loop that already compounds decisions. Triggers on "compound", "compound this", "spec is done", "wrap up the spec", "update the code map", "what did this teach", at /shakeout-level boundaries. NOT per sub-phase, NOT for trivial changes.
---

<objective>
Close the knowledge loop at spec-close. A session generates knowledge about three objects; only one compounds today. This skill compounds the other two — as PROPOSALS you approve, never auto-writes.

| Object the work taught about | Compounds to | Owned by |
|---|---|---|
| Decisions / risks / state | `memory/STATE.md`, `lessons.md` | the Stop hook + `DECISION:`/`RISK:`/`LESSON:` tags (already closed) |
| **The codebase's structure** | `docs/architecture/CODE-MAP.md` | **this skill, Pass A** |
| **The skills (tools) themselves** | skill `lessons.md` | **this skill, Pass B** (reuses `/skill-audit`) |

Without this gate, codebase structure and skill edge-cases are re-derived every session — the "patching" feeling. With it, "what did this spec teach?" is answered in ONE named place at ONE boundary, the same way the spine already makes threat-modeling and test-effectiveness structural instead of honor-system.
</objective>

<core_idea>
**Knowledge that isn't written at a boundary evaporates and gets re-derived.** The memory loop proves the pattern works for decisions. This applies the identical loop to the codebase map and the skills — at the one boundary where the work is actually landed (post-finish), so what's compounded is true, not in-flight.

Report-only is not timidity. Editing a skill changes behavior for every future session in every project — exactly why `/skill-audit` and `/pattern-miner` already say "never auto-edit." A wrong auto-written CODE-MAP is worse than none (it gets trusted). The gate makes the *evaluation* structural (fires every spec) without making the *mutation* automatic. You keep the editorial veto.
</core_idea>

<when_to_use>
Invoke at **spec-close** — when a whole spec/feature is done and `superpowers:finishing-a-development-branch` has run. This is `/shakeout`-level cadence, NOT every sub-phase. A 2-task phase rarely teaches enough to justify the pass.

**Do NOT invoke for:** a single sub-phase close, trivial one-file changes, formatting, dependency bumps, prose, or any work that didn't change a module boundary / convergence point / data flow AND didn't surface a skill edge-case.

Fires as **Stage 3, step 6 of `harnessed-development`** — after finish. Can also be run standalone when you want to refresh the map or harvest skill lessons.
</when_to_use>

<process>

Run two passes over the spec's full diff + transcript. Both emit PROPOSALS into one manifest. Write nothing until the user approves items.

**Pass A — Codebase compound → `docs/architecture/CODE-MAP.md`**

Ask: *what did this spec teach about the SYSTEM that a future session should not have to re-derive?*

1. Read the current `docs/architecture/CODE-MAP.md` (if absent, the first run proposes creating it from the spec's touched areas — don't try to map the whole codebase, only what this spec touched plus its immediate neighbors).
2. Over the spec diff, identify: new/changed modules, entry points, **convergence points** (cross-ref `architecture-invariants` — if the spec touched one, the CODE-MAP entry names the invariant), data flows, cross-cutting seams, removed/renamed surfaces.
3. Diff reality against the current map. Propose: additions (`+`), changes (`~`), and **staleness flags** (`!`) where the map still describes something the diff moved or deleted.
4. **Output: a proposed patch to `CODE-MAP.md`. NOT applied.**

**Pass B — Skill compound → skill `lessons.md` (report-only)**

Ask: *what did this spec teach about the TOOLS?* Reuse existing machinery — this pass is a *trigger + scoping* layer over `/skill-audit`, not new logic.

1. Scope to skills **touched this spec** — invoked in the transcript or named in commits. Do NOT audit all skills (that's the standalone `/skill-audit`'s job).
2. For each touched skill, run the `/skill-audit` checks (stale lessons, body-vs-reality drift, description quality) AND harvest any `SKILL-EDGE:` deltas raised during the spec.
3. Split by blast radius: `lessons.md` appends are low-risk proposals; SKILL.md **body** changes are always report-only flags, never proposed as edits.
4. **Output: proposed `lessons.md` appends + body-staleness flags. NOT applied.**

</process>

<output_template>
```
Compound — <spec name> — YYYY-MM-DD
===================================

A. CODEBASE  → docs/architecture/CODE-MAP.md
   proposed:  <N> deltas
   1. + Module: <path>  (<why — e.g. new convergence point, ref invariant #4>)
   2. ~ <surface>: <what changed>
   3. ! STALE: <map entry> — <how reality diverged>

B. SKILLS  (touched this spec: <skill, skill, skill>)
   proposed:  <N> lessons appends · <M> body flags
   1. + <skill>/lessons.md: "<edge case / SKILL-EDGE raised this spec>"
   2. ! <skill> body: <staleness signal — e.g. high-usage this spec, untouched 90d>

Nothing written. Approve items to apply: ____
```
</output_template>

<red_flags>

| Thought | Reality |
|---|---|
| "I'll just auto-apply the CODE-MAP patch, it's only a doc" | A wrong map gets trusted and misleads the next session worse than no map. Report-only. The user approves. |
| "Let me audit all 30 skills" | That's `/skill-audit` standalone. Pass B scopes to skills TOUCHED this spec — cheap and relevant. |
| "This sub-phase is done, run compound" | Spec-close cadence, not sub-phase. A 2-task phase doesn't earn the pass. |
| "I'll propose SKILL.md body edits too" | Body edits change behavior everywhere — flag staleness, never auto-propose the edit. Only `lessons.md` appends are proposals. |
| "The CODE-MAP should document the whole codebase" | No — it tracks what specs have touched, growing incrementally. First run maps only this spec's footprint + neighbors, not the universe. |
| "This duplicates the memory loop" | Different object. Memory loop = decisions/state. This = codebase structure + skill edge-cases. Same shape, three objects, no overlap. |

</red_flags>

<success_criteria>
1. At spec-close, a proposed-deltas manifest exists naming CODE-MAP changes + skill-lesson harvest — without any file being auto-edited.
2. The CODE-MAP stays true: a later session reads it instead of re-deriving module/convergence-point structure, and it doesn't describe moved/deleted surfaces (staleness flags caught them).
3. Skill edge-cases hit during the spec land in the right skill's `lessons.md` (after approval) instead of evaporating.
4. If the gate is never cited and the CODE-MAP drifts stale, it failed — wire it into Stage 3 or delete it.
</success_criteria>

<integration>

| Skill / gate | Relationship |
|---|---|
| `superpowers:finishing-a-development-branch` | **UPSTREAM.** This runs immediately after finish — compound what landed, not what's in flight. |
| `netdust-core:architecture-invariants` | **PASS A CROSS-REF.** CODE-MAP entries for convergence points name the invariant. A spec that added a convergence point updates both. |
| `/skill-audit` | **PASS B REUSE.** Pass B is `/skill-audit` scoped to touched skills + auto-fired. The standalone command still exists for full audits. |
| `/pattern-miner` | **ADJACENT.** Cross-project pattern promotion; compound is single-spec, single-project. Patterns surfaced repeatedly by compound are pattern-miner candidates. |
| `SKILL-EDGE:` tag | **PASS B INPUT.** Edge-cases tagged during the spec are harvested here into proposals. |
| memory/STATE loop | **SIBLING.** Same loop, third object (decisions). This skill does NOT touch STATE/lessons — that's the hook's job. |
| `harnessed-development` | **HOST.** Stage 3, step 6 (after finish). Spec-close cadence. |

</integration>
