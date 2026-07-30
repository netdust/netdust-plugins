---
name: spec-authoring
description: Stage 0.5 of the harness — the gate over a feature's spec.md (what/why, prioritized user stories, functional + acceptance criteria, measurable success criteria, NO tech stack). The spec is AUTHORED by superpowers:brainstorming into specs/<feature>/spec.md; this skill verifies it mechanically with bin/gate-check.py and HALTs until every [NEEDS CLARIFICATION] marker is resolved and every SC line carries a number. Owns the ambiguity rule: anything still open is handed back as a marker, never resolved by picking a plausible default. Runs AFTER brainstorming (Stage 0) and BEFORE writing-plans (Stage 1), so the plan is built on a clarified spec instead of vibes. Triggers when starting a new feature whose intent is concrete enough to specify but not yet planned. NOT for trivial one-file edits, Class D security one-liners, research, or prose — those skip the spec stage.
---

<objective>
Drive `specs/<feature>/spec.md` — the *what and why*, with no technology stack — to **zero unresolved ambiguity and measurable success** before any plan is written.

**Division of labour: content comes from upstream, verification lives here.** `superpowers:brainstorming` runs the design dialogue and writes the spec; this skill does not re-author it and does not duplicate brainstorming's craft. What this stage adds is the netdust HALT: **a plan may not be written against a spec that still contains `[NEEDS CLARIFICATION]`, or whose success criteria nobody can sign off against.**

The HALT is mechanical. `bin/gate-check.py` parses the spec and fails on any real unresolved marker (bracketed placeholder text and backticked examples are correctly ignored) and on any `SC-n` line carrying no number. The gate is the script's exit code, not a human glance — same philosophy as the testing gate's structured evidence.

**This stage depends on no external tooling.** `gate-check.py` lints whatever of `spec.md` / `plan.md` / `tasks.md` exists in a directory. The one thing that makes it fire is the spec being at `specs/<feature>/spec.md` — which is why that location is a standing preference in `memory/GLOBAL.md`, not a per-project choice.
</objective>

<artifact_contract>
**There is no spec template.** The spec is authored, not filled in — a skeleton whose untouched state passes the gate is worse than no skeleton, which is exactly how the security checkboxes below came to be disarmed by default. Write the sections; do not copy a form.

Two kinds of requirement live here, and the difference matters:

**PARSED — `gate-check.py` reads these literally. The grammar is a contract, not a suggestion.**

| Must appear | Exact shape | Read by |
|---|---|---|
| `## Success criteria` | `- **SC-1:** <text containing a number>` — one line per criterion, numbered `SC-n` | `success-criteria` check: FAILs on a line with no digit, and on a body that is only a bracketed `[…]` placeholder |
| `## Security-relevant surfaces` | one `- [ ]` / `- [x]` line per surface, from the six in `<security_surfaces>` | `security-surfaces` check: **FAILs** on a missing section, on zero boxes checked, and on a real surface checked together with `None of the above`. `threat-model` check: any checked box that isn't "none of the above" ARMS the plan's 1a gate |
| anywhere in the file | `[NEEDS CLARIFICATION: <substance>]` | `clarify-halt` check: any real marker FAILs the gate (backticked examples and empty `…` placeholders are correctly ignored) |

Historically a section whose heading was absent, or whose boxes were all blank, did not fail loudly — it made the 1a gate **pass by finding nothing**, and the checker printed "no spec surface flagged" as reassurance while an auth feature walked through. `security-surfaces` now FAILs all three shapes, so the silent-disarm path is closed. `## Success criteria` is the one that still WARNs rather than FAILs when wholly absent, and only because two live spec dirs predate it.

**AUTHORED — required content, your words, no prescribed shape.**

- **Problem / why** — the user or business problem this exists to solve.
- **User stories, prioritized P1/P2/P3** — each an independently shippable slice, each with why it ranks there and how it is verified alone. These story boundaries become the review clusters in `plan.md`'s `## Phases & review clusters`, so clusters stop being invented at plan time.
- **Functional requirements**, `FR-n` numbered so Stage 1.5 can trace each to a task.
- **Acceptance criteria** — the contracts the Tier-A tests will assert, denial and negative paths included. A criterion that cannot carry a number belongs here rather than in Success criteria.
- **Assumptions** — every default chosen on the user's behalf, one line each (Step 3).
- **Out of scope** — what this explicitly does not do, so the plan is bounded.
- **No technology stack anywhere.** Stack belongs in `plan.md` (Stage 1).
</artifact_contract>

<security_surfaces>
The six surfaces. Answer by the literal list, not by gut — a checked box here is what arms the plan's threat-model gate (1a), and `spec-analysis` cross-checks the two. `None of the above` is a real answer and must be stated explicitly; **blank is not an answer**, it is a disarmed gate.

- User-controlled URLs / server-side outbound requests
- Auth / session / token / capability surfaces
- Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- BYOK / stored credentials
- Multi-tenancy / cross-actor visibility
- None of the above — *(state so explicitly)*
</security_surfaces>

<process>

**Step 1 — Confirm the spec landed where the gate reads.** The spec must be at `specs/<feature>/spec.md`. `superpowers:brainstorming` defaults to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` and yields to a stated user preference — that preference is set in `memory/GLOBAL.md` and is injected every session. If the spec landed at the upstream default anyway, **move it before doing anything else**: a spec outside `specs/<feature>/` is a spec no gate ever checks, and every check below silently passes by never running.

**Step 2 — Check the spec against `<artifact_contract>` above.** Not prose review — brainstorming owns the content and the words. Confirm the sections the downstream gates read are present and answered.

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
  - `[success-criteria]` FAIL — the section is present but carries only bracketed placeholder text, or an `SC-n` line carries no number. The finding names the offending ids. Rewrite those lines with a number, or move them to `## Acceptance criteria`.
  - `[security-surfaces]` FAIL — the section is missing, no box is checked, or a real surface is checked alongside `None of the above`. Answer the six; blank is a disarmed gate, not a "no".
  - `[success-criteria]` WARN — the section is missing entirely. This is retro-compat for the spec dirs that predate the contract, **not** a licence to omit it: on a new spec, treat the WARN as a defect and add the section.

**Do not proceed to Stage 1 planning until the checker passes.** A spec with an open ambiguity is too generic to plan, and a plan built on it inherits the ambiguity as a wrong premise.

**Step 5 — Hand off to Stage 1.** Once the gate is green, `planning` Stage 1 (`superpowers:writing-plans`, against Stage 1's own artifact contract) writes `plan.md` + `tasks.md` from this clarified spec. The plan's threat-model gate (1a) will fire if any Security-relevant surface was checked here, and the plan's review clusters follow the P1/P2/P3 story boundaries.

</process>

<red_flags>

| Thought | Reality |
|---|---|
| "The design doc brainstorming wrote is good enough where it is" | Then no gate ever reads it. `gate-check.py` reads `specs/<feature>/`. A spec at the upstream default path passes every check by never being checked. Move it (Step 1). |
| "This requirement could be read two ways — I'll pick the sensible one and note it" | That is upstream's rule, and the harness overrides it. Write the `[NEEDS CLARIFICATION]` marker and hand it back. A default you chose alone is a wrong premise the plan inherits (Step 3). |
| "There's one [NEEDS CLARIFICATION] left but it's minor, I'll plan around it" | The HALT is binary and mechanical — the checker fails. Resolve it. |
| "Success criteria: 'the flow feels fast and editors are happy'" | Unmeasurable, and the gate FAILs it by naming the SC id. Shake-out has to sign off against a comparison, not a judgement call. Give it a number or move it to Acceptance criteria. |
| "I'll skip the Success criteria section — the gate only WARNs" | The WARN is retro-compat for the two spec dirs that predate the contract, and the comment at the flip point in `gate-check.py` says so. Omitting it on new work is exactly the hole the WARN was chosen to tolerate, not to bless. |
| "I'll note the tech stack in the spec so the plan is easier" | No. The spec is what/why. Tech in the spec leaks implementation into requirements and pre-commits the plan. Stack lands in plan.md. |
| "I'll leave the Security-relevant surfaces boxes blank to move faster" | Blank ≠ none — blank is a **disarmed gate**. With nothing checked, `spec_security_triggered()` returns empty, the plan's `N/A` threat model PASSES, and the checker prints "no spec surface flagged" as reassurance. Answer the six explicitly, `None of the above` included. |

</red_flags>

<success_criteria>
1. `specs/<feature>/spec.md` exists **at that path**: what/why, prioritized user stories, functional + acceptance criteria, no tech stack.
2. `## Success criteria` present, every `SC-n` line measurable — `gate-check.py` reports `success-criteria` PASS, not WARN.
3. `gate-check.py` passes the `clarify-halt` check — zero unresolved `[NEEDS CLARIFICATION]`.
4. Every default chosen on the user's behalf is written in `## Assumptions`, not left implicit.
5. `## Security-relevant surfaces` **answered** — at least one of the six boxes checked (`None of the above` counts, blank does not), by the literal list rather than by gut.
6. Control handed to Stage 1 with a clarified spec.
</success_criteria>

<integration>

| Skill / artifact | Relationship |
|---|---|
| `superpowers:brainstorming` | **UPSTREAM (Stage 0) — AUTHORS the spec.** Runs the design dialogue and the user review gate, and writes `specs/<feature>/spec.md` (per the `memory/GLOBAL.md` spec-location preference). This skill verifies that output; it does not re-author it. Its self-review's "pick one reading" rule is overridden by Step 3. |
| `<artifact_contract>` (this file) | **THE SHAPE.** The single home of the spec.md contract — parsed grammar and authored content. There is no template; a skeleton's untouched state was itself the defect. |
| `bin/gate-check.py` | **THE GATE.** Mechanical `clarify-halt` + `success-criteria` checks; its exit code is the HALT. Reads the feature dir directly. |
| `memory/GLOBAL.md` | **THE PREFERENCE.** Holds the spec-location and hand-back-ambiguity preferences that make Step 1 and Step 3 bind on brainstorming at runtime. |
| `superpowers:writing-plans` | **DOWNSTREAM (Stage 1).** Plans against the clarified spec; review clusters follow this spec's P1/P2/P3 story boundaries. |
| `netdust-agent:spec-analysis` | **DOWNSTREAM (Stage 1.5).** Cross-checks the Security-relevant surfaces flags against the plan's threat model. |
| `netdust-agent:shake-out` | **DOWNSTREAM (Stage 3).** Signs off against this spec's `## Success criteria` — which is why they must carry numbers. |
| `netdust-agent:planning` | **SEQUENCER.** Fires this as Stage 0.5, unconditionally. |

</integration>
