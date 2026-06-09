---
name: designing-apis
description: "CRAFT skill — the how-to harnessed-development Stage 1 (plan) reaches for once brainstorming / refining-ideas has concluded 'we need an API, a module boundary, or a type contract.' There is no strong superpowers base for interface design, so this skill carries the content: contract-first design, Hyrum's-Law-aware exposure, additive-only evolution, structured errors, boundary validation, predictable REST + TypeScript contract patterns — restated and extended from addyosmani/agent-skills api-and-interface-design (MIT). The Netdust layer superpowers/addy cannot know: this is where the project's architecture-invariants CONVERGENCE POINTS get designed in, so the API names them for gate 1b to later check, and where boundary-validation on untrusted input fires the threat-modeling gate 1a. Use when shaping an endpoint, an exported module surface, or a shared type."
---

<objective>
You are at the plan stage of `harnessed-development`, and brainstorming (or `refining-ideas`) just concluded the work needs an **interface**: an HTTP endpoint, an exported module surface, or a shared type contract. This skill shapes what the plan's tasks will contain — the *shape of the contract* — before any implementation task is written. Unlike `writing-tests`, there is no strong superpowers base for interface design, so this skill is the primary source: it restates and extends `addyosmani/agent-skills:api-and-interface-design` (MIT) and frames it as the how-to Stage 1 reaches for.
</objective>

<contract_first>
Design the interface BEFORE the implementation, and write it into the plan as the first task of the boundary. The consumer's view is the spec: a caller (a client, an agent over MCP, a sibling module) only ever sees the contract, never your internals. Decide request shape, response shape, error shape, and naming first — implementation becomes "satisfy this contract," which is also what your tests assert against.
</contract_first>

<hyrums_law>
**All observable behavior becomes a de facto contract.** With enough consumers, every quirk you expose — field ordering, an incidental 200-on-empty, a leaked internal id, an undocumented header — someone will depend on. So be *intentional about exposure*: expose the minimum that satisfies the use case, and treat anything you return as something you can never quietly change. The cheapest contract to keep is the one you never promised. This is also why a leaked `system_prompt` or internal id in a response is not cosmetic — it is a contract you did not mean to sign.
</hyrums_law>

<evolution>
**Additive-only.** Add new *optional* fields; never remove a field, never narrow a type, never repurpose a key, never make an optional field required, in place. Breaking changes get a new version or a new endpoint, never a silent mutation of the existing one. A consumer that worked yesterday must work today. When a field must die, deprecate-then-remove across versions, not in one diff.
</evolution>

<error_shape>
**One structured error body, everywhere.** Every error returns the same shape — `{ error: { code, message } }` (machine-readable `code`, human `message`), with the right status class (4xx caller fault, 5xx server fault). Callers branch on `code`, never parse `message`. This is not per-endpoint styling: it is a single convergence point (see below), so a consumer writes its error handling once.
</error_shape>

<validation_at_boundary>
**Validate untrusted input at the boundary, with a schema, before it reaches logic.** Parse-don't-validate: a Zod (TS) / schema parse at the edge turns untrusted input into a typed value, and everything downstream trusts the type. Reject malformed input with a 4xx structured error, never a 500 from a deep stack trace. **This is a threat-modeling trigger:** if any input crosses a trust boundary (a webhook body, a BYOK provider URL, AI tool-call args, frontmatter from outside, a file upload), Stage 1a (`threat-modeling`) fires — name the validated surface in the plan so the threat model can cite its mitigation.
</validation_at_boundary>

<rest_patterns>
For HTTP APIs, default to predictable REST so callers can guess correctly:
- **Resource endpoints, plural nouns:** `/work-items`, `/work-items/:id`. Verbs live in the HTTP method, not the path.
- **Method semantics:** GET (read, safe), POST (create), PATCH (partial update — send only changed fields), PUT (full replace), DELETE. Prefer PATCH for edits so callers need not round-trip the whole entity.
- **Pagination with metadata:** list endpoints return data plus paging metadata (cursor/next, total or has-more) — never a bare array, so the contract can grow. Keyset cursors over an offset for stable ordering.
- **Consistent field naming:** one casing convention per surface (this project: `snake_case` DB columns / frontmatter, `camelCase` TS fields, plural collection names) — never mix within a surface.
</rest_patterns>

<typescript_patterns>
For exported module / type contracts:
- **Discriminated unions for state:** model "one of N states" as a tagged union (`{ status: 'pending' } | { status: 'done', result: R }`), not a bag of optional fields — the compiler then forces every consumer to handle each case.
- **Input vs output type separation:** the type a caller *sends* is not the type it *receives* (no server-assigned `id`/`created_at` on input; no secrets on output). Separate `CreateXInput` from `X`.
- **Branded types to prevent id confusion:** brand ids (`type ProjectId = string & { __brand: 'ProjectId' }`) so a `UserId` can never be passed where a `ProjectId` is expected — a whole bug class deleted at compile time.
</typescript_patterns>

<the_netdust_layer>
This is the part superpowers and addy cannot know, and it is why this skill sits inside *this* harness: **the API you design here is where the project's convergence points get DESIGNED IN.**
- **Errors converge in one error-shape.** The structured body above is invariant — one error serializer, not per-handler strings.
- **Validation converges at the boundary.** One parse at the edge, not scattered re-checks downstream.
- **Auth converges at one guard.** Authorization is decided in one place the endpoint defers to (`lib/access.ts` in Folio), never re-implemented per route.
So **`designing-apis` FEEDS the architecture-invariants gate (1b):** name each convergence point in the plan — "errors via the shared serializer," "auth via the one guard," "validation at the boundary" — so the `ARCHITECTURE-INVARIANTS.md` doc can later let `/code-review` + `/shakeout` flag any path that *bypasses* it (e.g. "this route writes a raw 500 string → bypasses the error convergence point"). An API designed without naming its convergence points hands the invariant gate nothing to check.
</the_netdust_layer>

<success_criteria>
A boundary designed under this skill:
- Has its **contract written before** the implementation task (consumer's view first).
- Exposes the **minimum** observable surface (Hyrum's Law) and is **additive-only** going forward.
- Returns the **one structured error shape** and **validates untrusted input at the edge** with a schema.
- Follows predictable **REST** (plural resources, PATCH partial, paginated lists) and/or **TS contract** patterns (discriminated unions, input≠output, branded ids).
- **Names its convergence points in the plan** so the architecture-invariants gate (1b) can check for bypasses, and **flags any trust-boundary input** so threat-modeling (1a) fires.
</success_criteria>

<integration>
- **`harnessed-development` Stage 1 (plan)** — the step that reaches for this skill, once brainstorming / `refining-ideas` concluded an interface is needed. The contract this skill shapes becomes the plan's first boundary task.
- **`architecture-invariants` (gate 1b)** — this skill FEEDS it: the convergence points you name here (error shape, boundary validation, the one auth guard) are what the invariant doc later checks `/code-review` + `/shakeout` against.
- **`threat-modeling` (gate 1a)** — boundary validation on untrusted input is a threat-modeling trigger; name the validated surface so the threat model cites the mitigation.
- **`writing-tests`** — the contract you design here is exactly what the Tier-A test asserts against (acceptance-criteria contract + denial path), not the implementation.
- **Provenance** — concepts restated-and-extended from `addyosmani/agent-skills:api-and-interface-design` (MIT, the primary source since superpowers has no interface-design base); the convergence-point framing and the gate wiring (1a/1b) is the Netdust spine this file adds.
</integration>
