---
name: architecture-invariants
description: Use when writing a plan or spec for a non-trivial feature, OR when onboarding to / auditing an existing codebase, to name the project's CONVERGENCE POINTS — the single places where each cross-cutting property (authorization, data access, live updates, error handling, entity modeling) is DECIDED. Produces an `ARCHITECTURE-INVARIANTS.md` doc the project commits. Becomes the convergence target for /code-review and /shakeout — reviews flag any code path that bypasses a convergence point, instead of re-discovering wiring/dedup/safety concerns free-form each round. Sibling to threat-modeling (which does this for attacks). Opt-in via the project's CLAUDE.md — not auto-invoked.
---

<objective>
Produce (or update) a project's `ARCHITECTURE-INVARIANTS.md` — a one-page contract naming the codebase's CONVERGENCE POINTS and the rule for each. A convergence point is the SINGLE place where a cross-cutting property is decided: where authorization is enforced, where data is fetched, where live updates are applied, where errors become user-facing, where new entity types are modeled. The doc exists so that:

1. "Is this safe / wired / non-duplicated?" becomes a CHEAP, MECHANICAL check ("does this path go through the convergence point?") instead of an expensive audit ("did I check all N call sites?").
2. `/code-review` and `/shakeout` have a fixed target — they flag paths that BYPASS a convergence point, rather than re-discovering the same wiring/dedup/safety concerns free-form every round.
3. A new contributor — human OR an in-app agent editing the code — reads ONE doc and stays inside the rails, instead of inferring the architecture from scattered senior-engineer comments in the commit history.
4. The reflex "can this be data instead of a new subsystem?" / "does this reuse the gate or open a path around it?" is written down, not tacit.

Without this doc, confidence is a thing the human re-earns by audit every session ("is X still tight? is Y bloated?"). The whole point is to make confidence a PROPERTY OF THE REPO, verifiable on demand, not a recurring manual review.
</objective>

<core_idea>
**A bug is almost always a path that skips a convergence point.**

The strongest codebases aren't the ones that are vigilant everywhere — they're the ones where each cross-cutting property is DECIDED IN ONE PLACE, so there's one place to verify and one kind of bug to look for (a path that went around it).

Worked example (Folio, 2026-06-01): authorization converges on `executeTool` (the scope double-check) + `intersectAgentProjects` (the ceiling). Because of that, an auth audit was EASY and the verdict was GOOD. The one real hole found — token-minting accepting caller-supplied scopes with no role check (`tokens.ts`) — was precisely the ONE write path that bypassed the convergence point (`roleToScopes`). It was latent for months. The invariant "token authority never exceeds the minting caller's role" would have made it a mechanical review finding ("this path skips `roleToScopes`") instead of a thing a human had to happen to notice.

This skill's job is to NAME those convergence points so the codebase can be CHECKED instead of AUDITED.
</core_idea>

<when_to_use>

Invoke this skill in two situations:

**A. At plan-writing time** for a non-trivial feature (3+ tasks, or anything that adds a route/tool/data-fetch/live-update path) — alongside `superpowers:writing-plans`. The plan references the relevant invariants so the implementer routes through the convergence points instead of opening parallel paths.

**B. As an audit / onboarding pass** on an existing codebase that doesn't yet have an `ARCHITECTURE-INVARIANTS.md` — to extract the convergence points already living in the code (in middleware, shared libs, registries, base classes) and write them down as a contract.

The five cross-cutting properties to find a convergence point for (the doc has one section per property that EXISTS in the project — skip properties the project doesn't have):

| Property | The convergence-point question | Stack-agnostic examples |
|---|---|---|
| **Authorization** | Where is "may this actor do this?" decided? | One gate function / middleware / policy class. WP: capability checks + nonce. Statamic: blueprint perms. Bun/Hono: a `requireScope`/`executeTool` gate. |
| **Authentication identity** | What is the ONE identity primitive every request carries? | A token/session shape. WP: current user + caps. A `{workspaceId,scopes,...}` token row. |
| **Data access / fetching** | What is the ONE path to read/write the store? | One ORM/repository/query layer + key convention. WP: a repository, NOT raw `$wpdb` scattered. Bun: one API client + query-key factories. |
| **Live updates / events** | How do server changes reach the UI/consumers, and what is the source of truth? | One event bus + one client subscription. "SSE teaches WHEN to invalidate; it is never a source of truth." |
| **Error handling** | How does a failure become user-facing, uniformly? | One error envelope → one toast/notice path. WP: `WP_Error` never swallowed. Hono: `{error:{code,message}}` → `formatApiError`. |
| **Entity modeling / extensibility** | How are new entity types/fields added without schema churn? | The schemaless-vs-typed seam. "New entity types are data (frontmatter/meta) before they are tables." |

**Do not invoke when:**
- Pure refactor / rename with no new cross-cutting path.
- UI polish, visual-only, accessibility, performance, test additions, docs.
- A throwaway / brochure project that won't be built upon (the doc earns its keep only on codebases with a future).

If unsure, prefer running it as an audit (situation B) once per project — the doc is written once and amortizes across every future phase.

</when_to_use>

<process>

**Situation A (plan-time):** identify which of the five properties the feature TOUCHES, cite the existing invariants for those properties in the plan (a short `## Architecture invariants touched` note), and flag any place the feature would need a NEW convergence point or would be tempted to bypass an existing one. If the project has no `ARCHITECTURE-INVARIANTS.md` yet, do situation B first.

**Situation B (audit / authoring the doc):** walk these steps; the output is `ARCHITECTURE-INVARIANTS.md` at the project root (or `docs/`).

**Step 1 — Find each convergence point by grepping for its consumers.**

For each of the five properties, DON'T guess — find the convergence point empirically by asking "what do all the consumers import / call?":

- **Authorization:** grep the routes/handlers for the auth/permission check. If 15 files all call `requireScope` / `current_user_can` / one policy object → that's the convergence point. If different handlers check permissions different ways → there ISN'T one yet (that's a finding: "authorization is NOT converged — N independent checks").
- **Data access:** grep for the store access. One repository/client/ORM facade, or scattered raw queries?
- **Live updates:** grep for the event/subscription mechanism. One bus + one client hook, or ad-hoc?
- **Error handling:** grep for how errors surface. One envelope + one formatter, or each handler bespoke?
- **Entity modeling:** read the schema. Is there a schemaless seam (JSON column / meta) that new fields ride, or does every field need a migration?

The grep is the evidence. Record the actual file:line of the convergence point. (See `references/finding-convergence-points.md` for the per-stack grep recipes.)

**Step 2 — For each convergence point, write the INVARIANT as an enforceable rule.**

An invariant is a one-line rule + the convergence point it names + the bypass that would be a bug. Format:

> **[N]. [Property]: [the rule].** Converges on `[file:symbol]`. A path that [does the property itself instead of routing through the convergence point] is a bug — [what to do instead].

Good (Folio):
> **5. Authorization: token authority never exceeds the minting caller's role.** Converges on `roleToScopes` (`lib/agent-schema.ts`) + the `executeTool` scope check. A write path that accepts caller-supplied scopes without intersecting `roleToScopes(role)` is a bug — route it through the ceiling.

Bad (vibes, not checkable):
> Authorization should be handled carefully. *(Names no convergence point, no bypass, can't be reviewed against.)*

**Step 3 — Note convergence points that DON'T exist yet (the gaps).**

If Step 1 found a property with NO single decision point (N independent implementations), record it as an OPEN invariant: "Authorization is not yet converged — see findings." This is itself high-value: it's the list of places the codebase is one-drift-away-from-a-bug. Don't fabricate a convergence point that isn't there.

**Step 4 — Record deliberate exceptions.**

Some bypasses are intentional (e.g. "the reactor-health hook writes the cache directly because there is no GET endpoint — SSE is the only source"). List them explicitly so reviews don't re-flag accepted exceptions every round. Mirror threat-modeling's "out of scope" list.

**Step 5 — Write the "how to use this doc" closer.**

Tell `/code-review` and `/shakeout` to flag bypasses against the named invariants. Tell plan-writers to cite touched invariants. Tell an in-app agent (if the project has one) to read this doc before editing. (See `templates/architecture-invariants.md` for the exact structure to copy.)

</process>

<output_template>
Copy `templates/architecture-invariants.md` and fill it. Structure: a one-paragraph context header (what project, when written, why), then one numbered invariant per converged property, an "open / not-yet-converged" section for gaps, a "deliberate exceptions" list, and a "how to use this doc" closer. Keep it to ~1 page — it is a contract, not documentation. If it sprawls, the convergence points aren't actually single.
</output_template>

<red_flags>

| Thought | Reality |
|---|---|
| "I'll just describe the architecture" | Description ≠ invariant. An invariant names a convergence point AND the bypass that's a bug. "We use middleware for auth" is description; "all auth converges on X, a path that checks scopes itself is a bug" is an invariant. |
| "There's obviously one auth path, I don't need to grep" | The Folio `tokens.ts` hole WAS the path that bypassed the obvious auth gate. The bypass is exactly the thing you can't see without checking consumers. Grep. |
| "This property doesn't have a single convergence point, so I'll invent one in the doc" | Don't. Record it as a GAP (Step 3). A fictional invariant is worse than an admitted gap — reviews will pass things the doc claims are enforced. |
| "The doc will just go stale" | It goes stale ONLY if nothing verifies against it. That's why this skill ships WITH gate-wiring (/code-review + /shakeout check against it) and the invariant-auditor agent. A doc no gate enforces IS the bloat — don't author it without the enforcement. |
| "Every project needs all five properties" | No. Write a section only for properties the project HAS. A static site has no live-update invariant. |
| "More invariants = better" | Fewer, load-bearing invariants beat many trivial ones. If you list 20, you're documenting code, not naming convergence points. Aim for 4-7. |

</red_flags>

<success_criteria>

This skill has succeeded when the project has an `ARCHITECTURE-INVARIANTS.md` where:

1. Each invariant names a REAL convergence point (verified by grep — actual file:symbol, not aspiration).
2. Each invariant states the BYPASS that would be a bug (so a reviewer can mechanically check a diff against it).
3. Gaps (properties with no convergence point yet) are recorded as OPEN, not faked.
4. Deliberate exceptions are listed so they aren't re-flagged.
5. `/code-review` and `/shakeout` are wired to verify diffs against it (the enforcement — without this the doc is dead).

If a later `/code-review` flags a real bypass ("PATCH /x writes scopes without `roleToScopes` — bypasses invariant 5") that a free-form review would have missed, the skill earned its keep. If the doc is never cited by any gate, it failed — wire the enforcement or delete the doc.

</success_criteria>

<integration>

| Skill / gate | Relationship |
|---|---|
| `threat-modeling` | **SIBLING.** Same pattern (name the convergence target so reviews verify instead of re-discover), applied to a different axis. threat-modeling = attacks/mitigations; this = structural convergence points. A security-rich feature runs BOTH; the threat model's mitigations often BECOME auth invariants. |
| `superpowers:writing-plans` | **COMPANION (situation A).** Runs alongside; the plan gets a short `## Architecture invariants touched` note citing the relevant invariants. |
| `/code-review` | **CONSUMER.** Reviews verify the diff against `ARCHITECTURE-INVARIANTS.md` and flag (don't block) any path that bypasses a convergence point. |
| `/shakeout` | **CONSUMER.** Auto-dispatches the `invariant-auditor` agent alongside the other reviewers. |
| `invariant-auditor` (agent) | **EXECUTOR.** The narrow reviewer that, for each invariant, finds the paths bypassing the convergence point. The agent version of an architecture audit pointed at a contract. |
| `reviewer` (agent) | **UPSTREAM/ADJACENT.** The generalist five-pillar whole-diff pass reviews code quality (including architecture) broadly; this gives it a named contract to review the architecture dimension against. |

**Calibration data behind this skill:** Folio, 2026-06-01. A whole-app auth audit was fast and returned "tight" precisely because authorization converged on `executeTool` + `intersectAgentProjects`. The one CRITICAL finding (member can mint a token above their role) was the single write path that bypassed the `roleToScopes` convergence point — latent for months, found only because building an in-app agent prompted the audit. The lesson: confidence comes from convergence points, and a bug is a path that skips one. This skill makes those points explicit so the next bypass is a mechanical review finding, not a lucky catch.

</integration>
