# Feature Specification: [FEATURE NAME]

> **netdust spec template.** Authored by `superpowers:brainstorming` (Stage 0 → spec) and
> written to `specs/<feature>/spec.md`. Describes **what** and **why** — **no technology
> stack** (that is `plan.md`). `bin/gate-check.py` reads this file directly.
>
> **Gate contract** — gate-check.py FAILS on: any unresolved `[NEEDS CLARIFICATION: …]`
> marker anywhere in this file · a missing `## Success criteria` section or an SC line with
> no number in it · a checked box under `## Security-relevant surfaces` while `plan.md`'s
> `## Threat model` is left N/A.
>
> **Ambiguity rule (overrides brainstorming's self-review).** Anything still open after the
> design dialogue is written as a `[NEEDS CLARIFICATION: …]` marker and handed back — never
> resolved by picking a plausible default. Defaults you *did* choose go in `## Assumptions`,
> explicitly, so they are visible at the user review gate.

**Branch:** `[feature-branch]` · **Created:** [DATE] · **Status:** Draft → Clarified → Planned

## Problem / why

[Why this feature exists. The user/business problem. One paragraph.]

## User stories

> Prioritized P1, P2, P3… — P1 is the most critical. Each story must be an independently
> shippable slice: build only that one and something of value still works. Story boundaries
> become the review-cluster boundaries in `plan.md`'s `## Phases & review clusters`.

### Story 1 — [brief title] (P1)

[The journey in plain language.]

- **Why this priority:** [what value it carries, why it ranks here]
- **Independent test:** [how this slice is verified on its own]

### Story 2 — [brief title] (P2)

[…]

## Functional requirements

- **FR-1:** [system MUST …]
- **FR-2:** [system MUST …]

## Acceptance criteria

> These become the contracts the Tier-A tests assert (`testing-workflow`). Write them so a
> test can be derived from each — concrete and falsifiable, including denial/negative paths.

- [ ] [Given … When … Then … — incl. the negative/denial case]

## Success criteria

> Feature-level, technology-agnostic, and **measurable** — every line carries a number.
> This is what shake-out (Stage 3) signs off against, so that sign-off is a comparison
> rather than a judgement call. If a criterion cannot be given a number, it belongs in
> Acceptance criteria instead.

- **SC-1:** [e.g. an editor publishes a course module in under 3 minutes, unassisted]
- **SC-2:** [e.g. the module list renders in under 500 ms at 4,000 users]

## Security-relevant surfaces  [pre-flag for the plan's threat model]

> Not a threat model (that is authored at plan-time). This is an early flag so the planner
> knows the `threat-modeling` gate (1a) will fire. Check any that apply:

- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [ ] None of the above — *(state so explicitly)*

## Assumptions

> Every default chosen on your behalf, one line each — target users, scope bounds, data and
> environment, dependencies on existing systems. A silently-resolved ambiguity that lands
> here is reviewable; one that lands nowhere is invisible. When in doubt, make it a
> `[NEEDS CLARIFICATION]` marker instead.

- [assumption / chosen default]

## Out of scope

[What this feature explicitly does NOT do — bounds the plan.]

## Open questions / [NEEDS CLARIFICATION]

[Remaining ambiguities as `[NEEDS CLARIFICATION: <substance>]`. This section must be empty
before the plan is written — the Stage-0.5 HALT.]
