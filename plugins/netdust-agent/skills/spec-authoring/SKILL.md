---
name: spec-authoring
description: Stage 0.5 of the harness — the gate over a feature's spec.md (what/why, prioritized user stories, functional + acceptance criteria, measurable success criteria, NO tech stack). The spec is AUTHORED by superpowers:brainstorming into specs/<feature>/spec.md; this skill verifies it mechanically with bin/gate-check.py and HALTs until every [NEEDS CLARIFICATION] marker is resolved and every SC line carries a number. Owns the ambiguity rule: anything still open is handed back as a marker, never resolved by picking a plausible default. Runs AFTER brainstorming (Stage 0) and BEFORE writing-plans (Stage 1), so the plan is built on a clarified spec instead of vibes. Triggers when starting a new feature whose intent is concrete enough to specify but not yet planned. NOT for trivial one-file edits, Class D security one-liners, research, or prose — those skip the spec stage.
---

<objective>
Drive `specs/<feature>/spec.md` — the *what and why*, with no technology stack — to **zero unresolved ambiguity and measurable success** before any plan is written.

**Division of labour: content comes from upstream, verification lives here.** `superpowers:brainstorming` runs the design dialogue and writes the spec; this skill does not re-author it and does not duplicate brainstorming's craft. What this stage adds is the netdust HALT: **a plan may not be written against a spec that still contains `[NEEDS CLARIFICATION]`, or whose success criteria nobody can sign off against.**

The HALT is mechanical. `bin/gate-check.py` parses the spec and fails on any real unresolved marker (template guidance and backticked examples are correctly ignored) and on any `SC-n` line carrying no number. The gate is the script's exit code, not a human glance — same philosophy as the testing gate's structured evidence.

**This stage depends on no external tooling.** `gate-check.py` lints whatever of `spec.md` / `plan.md` / `tasks.md` exists in a directory. The one thing that makes it fire is the spec being at `specs/<feature>/spec.md` — which is why that location is a standing preference in `memory/GLOBAL.md`, not a per-project choice.
</objective>

<process>

**Step 1 — Confirm the spec landed where the gate reads.** The spec must be at `specs/<feature>/spec.md`, shaped by `templates/spec-template.md`. `superpowers:brainstorming` defaults to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and yields to a stated user preference — that preference is set in `memory/GLOBAL.md` and is injected every session. If the spec landed at the upstream default anyway, **move it before doing anything else**: a spec outside `specs/<feature>/` is a spec no gate ever checks, and every check below silently passes by never running.

**Step 2 — Check the spec against the template's required shape.** Not prose review — brainstorming owns the content. Confirm the sections the downstream gates read are present and filled:

  - `## Success criteria` — feature-level, technology-agnostic, **every `SC-n` line carries a number**. This is what shake-out (Stage 3) signs off against, so that sign-off is a comparison rather than a judgement call. A criterion that cannot be given a number belongs in `## Acceptance criteria` instead.
  - `## User stories` — prioritized P1/P2/P3, each with `Why this priority` + `Independent test`, each an independently shippable slice. These story boundaries become the review-cluster boundaries in `plan.md`'s `## Phases & review clusters`, so clusters stop being invented at plan time.
  - `## Acceptance criteria` — the contracts the Tier-A tests will assert, denial/negative paths included.
  - `## Assumptions` — every default that was chosen on the user's behalf, one line each (see Step 3).
  - `## Security-relevant surfaces` — the pre-flag checkboxes.
  - No technology stack anywhere. Stack belongs in `plan.md` (Stage 1).

  - **Fill the Security-relevant surfaces checkboxes honestly.** They are not the threat model (that is authored at plan-time), but they are the trigger flag: `spec-analysis` later cross-checks them against the plan's `## Threat model`. A checked box here with an N/A threat model there is a gate failure — so check them by the literal 1a trigger list, not by gut.

**Step 3 — The ambiguity rule (spec phase: the human decides).** Brainstorming's spec self-review says that if a requirement could be read two ways, you pick one and make it explicit. **The harness overrides that. The HALT wins.**

  - Anything still open after the design dialogue is written as a `[NEEDS CLARIFICATION: <substance>]` marker and **handed back** — never resolved by choosing a plausible default. The marker is the deliverable; ask the one sharp question (per SOUL.md) rather than inventing an answer.
  - Defaults you *did* legitimately choose go in `## Assumptions`, explicitly, one line each — so they are visible at brainstorming's user review gate.
  - **Know the residual limit.** `gate-check.py` can detect an *unresolved* marker; it can never detect a *silently resolved* one. `## Assumptions` plus the human review gate are the only control on that failure mode — which is exactly why an under-filled Assumptions section is a real defect and not a formatting nit.

**Step 4 — HALT gate (mechanical).** Run the checker over the spec:

```bash
python3 <netdust-agent>/bin/gate-check.py specs/<feature>
```

Two spec-stage findings decide the HALT:

  - `[clarify-halt]` FAIL — ambiguity remains. Loop back to Step 3: resolve it *with the human*, not by defaulting.
  - `[success-criteria]` FAIL — the section is present but only carries untouched template placeholders, or an `SC-n` line carries no number. The finding names the offending ids. Rewrite those lines with a number, or move them to `## Acceptance criteria`.
  - `[success-criteria]` WARN (`pre-template spec`) — the section is missing entirely. This is retro-compat for specs written before the template carried it, **not** a licence to omit it: on a new spec, treat the WARN as a defect and add the section.

**Do not proceed to Stage 1 planning until the checker passes.** A spec with an open ambiguity is too generic to plan, and a plan built on it inherits the ambiguity as a wrong premise.

**Step 5 — Hand off to Stage 1.** Once the gate is green, `planning` Stage 1 (`superpowers:writing-plans` + the `plan-template.md` gate sections) writes `plan.md` against this clarified spec. The plan's threat-model gate (1a) will fire if any Security-relevant surface was checked here, and the plan's review clusters follow the P1/P2/P3 story boundaries.

</process>

<red_flags>

| Thought | Reality |
|---|---|
| "The design doc brainstorming wrote is good enough where it is" | Then no gate ever reads it. `gate-check.py` reads `specs/<feature>/`. A spec at the upstream default path passes every check by never being checked. Move it (Step 1). |
| "This requirement could be read two ways — I'll pick the sensible one and note it" | That is upstream's rule, and the harness overrides it. Write the `[NEEDS CLARIFICATION]` marker and hand it back. A default you chose alone is a wrong premise the plan inherits (Step 3). |
| "There's one [NEEDS CLARIFICATION] left but it's minor, I'll plan around it" | The HALT is binary and mechanical — the checker fails. Resolve it. |
| "Success criteria: 'the flow feels fast and editors are happy'" | Unmeasurable, and the gate FAILs it by naming the SC id. Shake-out has to sign off against a comparison, not a judgement call. Give it a number or move it to Acceptance criteria. |
| "I'll skip the Success criteria section — the gate only WARNs" | The WARN is retro-compat for old specs, and the comment at the flip point in `gate-check.py` says so. Omitting it on new work is exactly the hole the WARN was chosen to tolerate, not to bless. |
| "I'll note the tech stack in the spec so the plan is easier" | No. The spec is what/why. Tech in the spec leaks implementation into requirements and pre-commits the plan. Stack lands in plan.md. |
| "I'll leave the Security-relevant surfaces boxes blank to move faster" | Blank ≠ none. If a surface applies and you leave it unchecked, the plan's threat-model gate never fires and spec-analysis can't catch the omission. Check by the literal 1a list. |

</red_flags>

<success_criteria>
1. `specs/<feature>/spec.md` exists **at that path**: what/why, prioritized user stories, functional + acceptance criteria, no tech stack.
2. `## Success criteria` present, every `SC-n` line measurable — `gate-check.py` reports `success-criteria` PASS, not WARN.
3. `gate-check.py` passes the `clarify-halt` check — zero unresolved `[NEEDS CLARIFICATION]`.
4. Every default chosen on the user's behalf is written in `## Assumptions`, not left implicit.
5. Security-relevant surfaces checkboxes filled by the literal 1a trigger list.
6. Control handed to Stage 1 with a clarified spec.
</success_criteria>

<integration>

| Skill / artifact | Relationship |
|---|---|
| `superpowers:brainstorming` | **UPSTREAM (Stage 0) — AUTHORS the spec.** Runs the design dialogue and the user review gate, and writes `specs/<feature>/spec.md` (per the `memory/GLOBAL.md` spec-location preference). This skill verifies that output; it does not re-author it. Its self-review's "pick one reading" rule is overridden by Step 3. |
| `templates/spec-template.md` | **THE SHAPE.** The section contract this skill checks against. |
| `bin/gate-check.py` | **THE GATE.** Mechanical `clarify-halt` + `success-criteria` checks; its exit code is the HALT. Reads the feature dir directly. |
| `memory/GLOBAL.md` | **THE PREFERENCE.** Holds the spec-location and hand-back-ambiguity preferences that make Step 1 and Step 3 bind on brainstorming at runtime. |
| `superpowers:writing-plans` + `templates/plan-template.md` | **DOWNSTREAM (Stage 1).** Plans against the clarified spec; review clusters follow this spec's P1/P2/P3 story boundaries. |
| `netdust-agent:spec-analysis` | **DOWNSTREAM (Stage 1.5).** Cross-checks the Security-relevant surfaces flags against the plan's threat model. |
| `netdust-agent:shake-out` | **DOWNSTREAM (Stage 3).** Signs off against this spec's `## Success criteria` — which is why they must carry numbers. |
| `netdust-agent:planning` | **SEQUENCER.** Fires this as Stage 0.5, unconditionally. |

</integration>
