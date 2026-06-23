---
name: spec-authoring
description: Stage 0.5 of the harness — author a feature's spec.md (what/why, user stories, functional + acceptance criteria, NO tech stack) by sequencing spec-kit's /speckit.specify then /speckit.clarify, and HALT until every [NEEDS CLARIFICATION] marker is resolved. The clarification HALT is enforced mechanically by spec-kit/gate-check.py, not by eyeballing. Runs AFTER brainstorming (Stage 0) and BEFORE writing-plans (Stage 1), so the plan is built on a clarified spec instead of vibes. Triggers when starting a new feature whose intent is concrete enough to specify but not yet planned. NOT for trivial one-file edits, Class D security one-liners, research, or prose — those skip the spec stage. Requires the spec-kit graft installed (/spec-kit-setup).
---

<objective>
Produce `specs/<feature>/spec.md` — the *what and why*, with no technology stack — and drive it to **zero unresolved ambiguity** before any plan is written. The harness was spec-light: `harnessed-development` jumped from brainstorm almost straight to task breakdown. This stage fills that gap with spec-kit's `/speckit.specify` (functional spec) + `/speckit.clarify` (coverage-based questioning), then adds the netdust HALT: **a plan may not be written against a spec that still contains `[NEEDS CLARIFICATION]`.**

The HALT is mechanical. `spec-kit/gate-check.py` parses the spec and fails on any real unresolved marker (template guidance and backticked examples are correctly ignored). The gate is the script's exit code, not a human glance — same philosophy as the testing gate's structured evidence.
</objective>

<process>

**Step 1 — Confirm the graft is installed.** `specs/` and `.specify/templates/overrides/spec-template.md` must exist. If not, run `/spec-kit-setup` first.

**Step 2 — `/speckit.specify`.** Invoke spec-kit's specify command with the feature intent from Stage 0 brainstorming. It writes `specs/<feature>/spec.md` from the netdust override `spec-template.md` — what/why, user stories, functional requirements, acceptance criteria, and the **Security-relevant surfaces** pre-flag checkboxes. Keep technology OUT — stack belongs in `plan.md` (Stage 1).

  - **Fill the Security-relevant surfaces checkboxes honestly.** They are not the threat model (that is authored at plan-time), but they are the trigger flag: `spec-analysis` later cross-checks them against the plan's `## Threat model`. A checked box here with an N/A threat model there is a gate failure — so check them by the literal 1a trigger list, not by gut.

**Step 3 — `/speckit.clarify`.** Invoke spec-kit's clarify command. It asks sequential, coverage-based questions over the under-specified areas and records each as Q→A in the Clarifications section, replacing the matching `[NEEDS CLARIFICATION: …]` markers.

**Step 4 — HALT gate (mechanical).** Run the checker over the spec:

```bash
python3 <netdust-agent>/spec-kit/gate-check.py specs/<feature>
```

If it reports `[clarify-halt]` FAIL, ambiguity remains — loop back to Step 3 (or ask your human partner the one sharp question, per SOUL.md). **Do not proceed to Stage 1 planning until the checker passes the clarify check.** A spec with an open ambiguity is too generic to plan, and a plan built on it inherits the ambiguity as a wrong premise.

**Step 5 — Hand off to Stage 1.** Once clarify passes, `harnessed-development` Stage 1 (`superpowers:writing-plans` + the override `plan-template.md`) writes `plan.md` against this clarified spec. The plan's threat-model gate (1a) will fire if any Security-relevant surface was checked here.

</process>

<red_flags>

| Thought | Reality |
|---|---|
| "The spec is clear enough, I'll skip /clarify" | The whole point of coverage-based questioning is that *you* think it's clear; the gaps are the ones you don't see. Run it. |
| "I'll note the tech stack in the spec so the plan is easier" | No. The spec is what/why. Tech in the spec leaks implementation into requirements and pre-commits the plan. Stack lands in plan.md. |
| "There's one [NEEDS CLARIFICATION] left but it's minor, I'll plan around it" | The HALT is binary and mechanical — the checker fails. A minor ambiguity planned-around is a wrong premise the plan inherits. Resolve it. |
| "I'll leave the Security-relevant surfaces boxes blank to move faster" | Blank ≠ none. If a surface applies and you leave it unchecked, the plan's threat-model gate never fires and spec-analysis can't catch the omission. Check by the literal 1a list. |

</red_flags>

<success_criteria>
1. `specs/<feature>/spec.md` exists: what/why, user stories, functional + acceptance criteria, no tech stack.
2. Security-relevant surfaces checkboxes filled by the literal 1a trigger list.
3. `gate-check.py` passes the `clarify-halt` check — zero unresolved `[NEEDS CLARIFICATION]`.
4. Control handed to Stage 1 with a clarified spec.
</success_criteria>

<integration>

| Skill / artifact | Relationship |
|---|---|
| `superpowers:brainstorming` | **UPSTREAM (Stage 0).** Feeds the feature intent this skill specifies. |
| spec-kit `/speckit.specify` + `/speckit.clarify` | **WRAPPED.** This skill sequences them and adds the HALT. |
| `spec-kit/gate-check.py` | **THE GATE.** Mechanical `clarify-halt` check; its exit code is the HALT. |
| `superpowers:writing-plans` + override `plan-template.md` | **DOWNSTREAM (Stage 1).** Plans against the clarified spec. |
| `netdust-agent:spec-analysis` | **DOWNSTREAM (Stage 1.5).** Cross-checks the Security-relevant surfaces flags against the plan's threat model. |
| `netdust-agent:harnessed-development` | **SEQUENCER.** Inserts this as Stage 0.5 (Phase C edit). |

</integration>
