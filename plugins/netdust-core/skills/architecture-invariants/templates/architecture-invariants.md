# Architecture Invariants — <PROJECT NAME>

> <One paragraph: what this project is, when this doc was written (so readers gauge staleness), and one sentence on why it exists.> Example: "Folio's confidence comes from a small set of convergence points — single places where each cross-cutting property is decided. This doc names them so /code-review and /shakeout can flag any path that bypasses one, instead of re-auditing wiring/dedup/safety every session. Written 2026-06-01."

**How to read an invariant:** each names a CONVERGENCE POINT (the one place a property is decided) and the BYPASS that is a bug (a path that does the property itself instead of routing through the convergence point). Reviews check diffs against these, mechanically.

---

## Invariants (converged — enforced)

> One per property the project HAS. Number them. Each: the rule + `file:symbol` of the convergence point + the bypass that's a bug + what to do instead. Aim for 4–7 total. Delete properties the project doesn't have.

1. **Authentication identity: <the rule>.** Converges on `<file:symbol>` (the one identity primitive every request carries). A request that <fabricates / infers identity another way> is a bug — <route it through the primitive>.

2. **Authorization: <the rule>.** Converges on `<file:symbol>`. A path that <checks permissions itself instead of routing through the gate> is a bug — <route it through the gate>.

3. **Data access: <the rule>.** Converges on `<file:symbol>` (the one read/write path + key convention). A <raw query / fetch> outside it is a bug — <use the repository/client>.

4. **Live updates: <the rule>.** Converges on `<file:symbol>`. The event stream <teaches WHEN to refresh; it is NEVER a source of truth>. A consumer that <treats an event as authoritative state> is a bug.

5. **Error handling: <the rule>.** Converges on `<file:symbol>` (the one envelope + surface path). A handler that <swallows the error / surfaces it bespoke> is a bug — <throw/return the standard shape>.

6. **Entity modeling / extensibility: <the rule>.** Converges on `<the schemaless seam>`. A new <field/entity> that <adds a column/table when frontmatter/meta would do> is a bug — <model it as data first>.

---

## Open — NOT yet converged (gaps)

> Properties where Step 1's grep found N independent implementations and no single decision point. These are the codebase's one-drift-from-a-bug spots. Do NOT fake an invariant for these — record the gap honestly. Empty if everything is converged.

- **<Property>:** not converged — <N independent implementations at file:line, file:line>. Risk: <they can drift; one will silently stop enforcing>. Convergence would mean <the one place to introduce>.

---

## Deliberate exceptions (intentional bypasses — do not re-flag)

> Bypasses that are on purpose, so reviews don't surface them every round. One line each with the reason. Mirror threat-modeling's out-of-scope list.

- **<file:symbol> bypasses invariant <N>** because <reason — e.g. "no GET endpoint exists; the event is the only source, so it writes the cache directly">.

---

## How to use this doc

- **`/code-review` + `/shakeout`:** verify the diff against these invariants. FLAG (don't block) any path that bypasses a convergence point as a finding: "bypasses invariant <N> (<property> convergence) — confirm intentional or route through <symbol>." The human accepts (and adds to Deliberate exceptions) or fixes.
- **Plan-writers (`superpowers:writing-plans` + `architecture-invariants`):** a plan that touches one of these properties cites the invariant in a `## Architecture invariants touched` note, so the implementer routes through the convergence point.
- **In-app agents editing this code (if any):** read this doc before editing. Staying inside the invariants is what makes an agent safe to let touch the app.
- **Keep it current:** when a new convergence point is introduced, add an invariant. When a gap is closed, move it from Open to Invariants. A `/evaluate` retro that finds a bypass the doc didn't name should add or sharpen an invariant.
