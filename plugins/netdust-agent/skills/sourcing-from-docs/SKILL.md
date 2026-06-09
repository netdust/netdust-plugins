---
name: sourcing-from-docs
description: "CRAFT skill — the how-to ANY harnessed-development stage (plan, execute, or debug) reaches for whenever a load-bearing decision rests on the claim 'library / framework / API X behaves like Y.' There is no superpowers base for this; it restates and extends addyosmani/agent-skills source-driven-development (MIT) to close a real discipline gap: never assert external-dependency behavior from memory (training data drifts), ground the claim in OFFICIAL docs, and record the citation inline so a reviewer can verify. Pairs with the context7 MCP (resolve-library-id → query-docs) for fetching current docs. The Netdust layer: an unverified load-bearing external-behavior claim is a Stage-1c (spec-premise) and Step-2.5 (plan-freshness) failure waiting to happen — this is the how-to those gates reach for when the premise is about an EXTERNAL dependency, not sibling code. Use the moment a behavioral claim about a third-party library is doing real work in your reasoning."
---

<objective>
A decision in your plan, your code, or your debugging hypothesis rests on "library / framework / API **X** behaves like **Y**" — a return shape, a default, a side effect, an error condition, a config key, a version-specific change. This skill is the how-to any `harnessed-development` stage reaches for at that moment. There is no superpowers base for source-grounding; this skill restates and extends `addyosmani/agent-skills:source-driven-development` (MIT) and frames it as a cross-cutting craft the gates reach for whenever an external-behavior claim is load-bearing.
</objective>

<the_core_discipline>
**Never assert external API / library behavior from memory.** Your training data is a snapshot — libraries ship breaking changes, defaults flip, signatures move, MCP tool schemas evolve. A confidently-remembered behavior that was true at training time is the highest-risk kind of claim precisely *because* it feels certain. The rule is simple: if a third-party behavior is doing real work in your reasoning, **ground it in the official source before you assert it** — and say which.
</the_core_discipline>

<verified_vs_believed>
Hold the line between two sentences, and write the one that is true:
- **"I verified this in the docs"** — you fetched the current official source and it says so. Cite it.
- **"I believe this is true"** — you are recalling from memory. This is a *hypothesis*, not a fact, and it must not silently become a plan premise or a fix.

Collapsing the second into the first is the failure mode this skill exists to prevent. When you catch yourself writing a definite behavioral claim with no citation, that is the trigger to stop and source it.
</verified_vs_believed>

<how_to_source_with_context7>
The `context7` MCP is available in this environment for fetching current library docs. Two steps:
1. **`resolve-library-id`** — turn the library name into context7's id (e.g. "hono" → the resolved id). Disambiguate if multiple match.
2. **`query-docs`** — query that id for the specific behavior you need (the function, the config key, the error path), not a vague topic dump. Ask the precise question your decision rests on.

If context7 has no coverage for the library, fall back to the official documentation site or the versioned source/README — but it is still a *fetched, citable* source, never memory. Prefer the version the project actually uses (check the lockfile) — docs for a different major can be worse than no docs.
</how_to_source_with_context7>

<record_the_citation_inline>
A verification a reviewer cannot check is not a verification. **Record the citation at the point the claim is used** — in the plan task, the code comment, or the debug note:
- what you checked (library + version),
- where (context7 id / doc URL / source path),
- what it said (the specific behavior, quoted or tightly paraphrased).

Inline beats a separate "sources" appendix — the reviewer reads the claim and its proof in one place. This is the same instinct as asserting a test from acceptance criteria: the evidence travels with the assertion.
</record_the_citation_inline>

<the_netdust_layer>
This is why the skill lives inside *this* harness rather than standing alone: a load-bearing unverified external-behavior claim is a **gate failure waiting to happen**, and this is the how-to two specific gates reach for when the shaky premise is about an *external dependency* rather than sibling code.
- **Stage 1c — spec-premise ground-truth.** The plan-gate checks that the spec's premises hold against the real codebase. When a premise is "X library does Y" rather than "our `lib/access.ts` does Y," the codebase can't confirm it — *this skill is how 1c ground-truths that premise* (fetch + cite, don't trust the spec's recollection).
- **Step 2.5 — plan-freshness.** Mid-execution, before acting on a task, the harness re-checks the plan against ground truth. When the task's correctness hinges on an external behavior, *this skill is the freshness check* — re-source it now, because the dependency (or your memory of it) may have drifted since the plan was written.
Sibling-code premises are verified by reading the repo (`engineering-context`); **external-dependency premises are verified here.** Both gates accept either kind of proof; this skill supplies the external kind.
</the_netdust_layer>

<success_criteria>
A decision made under this skill:
- Does **not** assert third-party behavior **from memory** when that behavior is load-bearing.
- Was **grounded in the official source** (via `context7` resolve-library-id → query-docs, or the versioned official docs as fallback) for the version the project uses.
- Carries an **inline citation** (library + version, source, what it said) a reviewer can re-check at the point of use.
- Distinguishes **"verified"** from **"believed"** in the wording — a believed claim stays a flagged hypothesis, never a silent premise.
- When invoked from **1c or 2.5**, hands those gates a sourced premise for the external dependency the codebase could not confirm.
</success_criteria>

<integration>
- **`harnessed-development` (any stage)** — reaches for this skill the moment an external-behavior claim becomes load-bearing in plan, execute, or debug. Cross-cutting, not tied to one stage.
- **Stage 1c (spec-premise ground-truth) + Step 2.5 (plan-freshness)** — the two gates this skill is the how-to for when the shaky premise is about an EXTERNAL dependency rather than sibling code. They ground-truth sibling code by reading the repo; they ground-truth a library via this skill.
- **`engineering-context`** — the sibling-code counterpart: verifies premises about *this* codebase by reading it. This skill is its external-dependency complement.
- **`designing-apis`** — when you design against a third-party contract, the behavior you depend on is exactly the kind of claim to source here before baking it into your interface.
- **`systematic-debugging`** — a debug hypothesis that rests on "the library does X" is sourced here before it becomes the fix.
- **Provenance** — concepts restated-and-extended from `addyosmani/agent-skills:source-driven-development` (MIT, the primary source since superpowers has no base for this); the gate wiring (1c / 2.5) and the verified-vs-believed discipline is the Netdust spine this file adds.
</integration>
