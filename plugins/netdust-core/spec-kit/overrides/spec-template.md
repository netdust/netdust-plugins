# Feature Specification: [FEATURE NAME]

> **netdust override template.** Overrides spec-kit's core `spec-template.md`. Produced by
> `/speckit.specify` (wrapped by the `spec-authoring` skill, Stage 0.5). Describes **what**
> and **why** — **no technology stack** (that is deferred to `plan.md`). All
> `[NEEDS CLARIFICATION]` markers must be resolved by `/speckit.clarify` before a plan is
> written — that is the Stage 0.5 HALT gate.

**Branch:** `[feature-branch]` · **Created:** [DATE] · **Status:** Draft → Clarified → Planned

## Problem / why

[Why this feature exists. The user/business problem. One paragraph.]

## User stories

- As a [actor], I want [capability], so that [outcome].
- [more as needed]

## Functional requirements

- **FR-1:** [system MUST …]
- **FR-2:** [system MUST …]

## Acceptance criteria

> These become the contracts the Tier-A tests assert (testing-workflow). Write them so a
> test can be derived from each — concrete and falsifiable, including denial/negative paths.

- [ ] [Given … When … Then … — incl. the negative/denial case]

## Security-relevant surfaces  [pre-flag for the plan's threat model]

> Not a threat model (that is authored at plan-time). This is an early flag so the planner
> knows the `threat-modeling` gate (1a) will fire. Check any that apply:

- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [ ] None of the above — *(state so explicitly)*

## Clarifications

> Filled by `/speckit.clarify`. Each resolved ambiguity recorded as Q→A. The Stage-0.5 gate
> HALTS if any `[NEEDS CLARIFICATION: …]` marker remains anywhere in this spec.

- Q: [question] → A: [answer]

## Out of scope

[What this feature explicitly does NOT do — bounds the plan.]

## Open questions / [NEEDS CLARIFICATION]

[List remaining ambiguities as `[NEEDS CLARIFICATION: …]`. This section must be empty
before `/speckit.plan`.]
