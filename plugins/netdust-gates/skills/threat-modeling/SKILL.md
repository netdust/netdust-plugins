---
name: threat-modeling
description: Use when a plan or a diff touches user-controlled URLs, auth/session/token/capability surfaces, untrusted parsing (uploads, payloads, frontmatter, AI tool-call args), stored credentials, multi-tenancy or cross-actor visibility, or outbound requests to user-supplied addresses. Produces the plan's `## Threat model` — assets, attacks, mitigations, deferrals — which becomes its Review Focus lines and the security review's target. Invoked by netdust-gates:policy.
---

# Threat modeling — before the tasks

Produce a `## Threat model` section in the plan BEFORE task breakdown — never retrofitted
after a review finds the hole (`drop-workspace-retrofit`: 2 review rounds and 11 findings,
against 1 round and 3–4 for the phases that modelled first).

**Fires when the work touches:** user-controlled URLs (webhooks, provider URLs, OAuth
redirects), auth/session/token/capability surfaces, untrusted parsing, stored credentials,
multi-tenancy or cross-actor visibility, outbound requests to user-supplied addresses. A
change to such a surface runs this on the DIFF, even for a one-liner (`class-d-gap`).

**The section's shape** — four short lists, concrete over complete:

1. **Assets** — what an attacker would want (tokens, PII, private content, write access).
2. **Attacks** — numbered, per surface: `1. **<attack>** → **<mitigation>**`. Name the actor
   and the input path; "someone bad does something" is not an attack.
3. **Mitigations** — each names WHERE it lives (the function, gate or check), so the review
   verifies a named list instead of hunting.
4. **Deferrals** — what is explicitly NOT defended, and why that is acceptable.

A property statement ("keys are encrypted") is not a threat model — it is a claim to
interrogate. On WordPress the four pillars (validate / sanitize / escape / authorize) apply
per data flow; `netdust-wp:wp-security` owns them.

Every mitigation becomes a `Review Focus` line pinned to a test, and the denial — the actor
who is refused — is asserted, not only the allowed path (`traverse-clause`: every route had a
guard, no test asserted the denial, cross-tenant reads shipped green).
