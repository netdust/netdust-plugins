---
name: threat-modeling
description: Use when writing a plan or spec for any feature that touches user-controlled URLs, auth/session/token surfaces, untrusted parsing (frontmatter from external sources, AI tool-call args, JSON-from-network, file uploads, MD-from-third-parties), BYOK credentials, multi-tenancy boundaries, or any surface where an attacker could supply input the server will trust. Produces a `## Threat model` section that the plan embeds inline. Becomes the convergence target for /code-review on the implementing sub-phases — reviews verify against the named mitigations instead of free-form bug hunting. Opt-in via the project's CLAUDE.md — not auto-invoked.
---

# Threat modeling — the plan-time gate

Produce a `## Threat model` section embedded in the plan BEFORE task breakdown — never
retrofitted after a review finds the hole (`drop-workspace-retrofit`).

**Fires when the work touches any of:** user-controlled URLs (webhooks, BYOK provider
URLs, OAuth redirects), auth/session/token/capability surfaces, untrusted parsing
(uploads, payloads, frontmatter, AI tool-call args), stored credentials, multi-tenancy /
cross-actor visibility, outbound requests to user-supplied addresses. A Class D ad-hoc
edit to such a surface runs this on the DIFF, even for a one-liner (`class-d-gap`).

**The section's shape** — four short lists, concrete over complete:

1. **Assets** — what an attacker would want (tokens, PII, private content, write access).
2. **Attacks** — numbered, per surface: `1. **<attack>** → **<mitigation>**`. Name the
   actor and the input path; "someone bad does something" is not an attack.
3. **Mitigations** — each one names WHERE it lives (the function/gate/check), so
   `/code-review` verifies against a named list instead of hunting free-form.
4. **Deferrals** — what is explicitly NOT defended, and why that is acceptable.

A property statement ("BYOK keys are encrypted") is not a threat model — it is a claim
the model must interrogate. On WP, the four-pillar rule (validate / sanitize / escape /
authorize) applies per data-flow; the stack plugin's plan-requirements skill injects it.

The mitigations become per-task acceptance criteria and the review convergence target.
`gate-check.py` FAILs a plan whose spec flags a security surface but whose threat model
is N/A.
