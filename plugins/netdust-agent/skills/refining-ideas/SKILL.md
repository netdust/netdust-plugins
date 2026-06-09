---
name: refining-ideas
description: "CRAFT skill — layers ON TOP of superpowers:brainstorming as its convergent SIBLING. Brainstorming GENERATES an idea (explores intent, requirements, design space); refining-ideas SHARPENS an already-generated-but-still-vague idea before it becomes a plan — a divergent→convergent refinement pass. Reached for at harnessed-development Stage 0, alongside brainstorming, when an idea exists but is fuzzy and needs stress-testing first. Use when you have a rough idea/feature/approach that is not yet crisp enough to plan: it sends you to superpowers:brainstorming for the generative base, then adds the Netdust layer — the divergent lenses, the convergent stress-tests, the explicit Not-Doing list, and how its output feeds Stage 1 (writing-plans), Stage 1's scope boundaries, and Stage 1c spec-premise ground-truth. Does NOT replace brainstorming and does NOT plan (that is writing-plans)."
---

<objective>
`superpowers:brainstorming` is generative — it opens the space, draws intent and requirements out of a half-formed wish. This skill is its **convergent sibling**: it takes an idea that already exists but is still vague and SHARPENS it into something crisp enough to plan. Brainstorming asks "what could this be?"; refining-ideas asks "of everything it could be, what is the one sharp version worth planning — and what are we explicitly NOT doing?"

Same relationship `harnessed-development` has to the superpowers process skills: the upstream owns generic craft; this skill adds the Netdust-specific layer and names the gate that reaches for it. Here, brainstorming owns idea generation; this skill owns the divergent→convergent refinement that turns a generated idea into a planning input.
</objective>

<first_load_the_base>
**Before refining anything, invoke `superpowers:brainstorming`.** It owns the generative craft this skill deliberately does not duplicate:

- drawing out true intent vs. stated request
- separating requirements from solutions
- exploring the design space before committing
- surfacing the user/problem the idea actually serves

If brainstorming already ran this session and produced the idea you now hold, you do not re-run it — you proceed straight to the refinement layer below. This skill assumes an idea exists; it does not invent one from nothing.
</first_load_the_base>

<where_you_are>
You are at **harnessed-development Stage 0**, alongside brainstorming — invoked when an idea EXISTS but is still fuzzy and needs stress-testing before Stage 1 can write a plan against it. Brainstorming may hand you a raw idea; this skill makes it sharp.

- If no idea exists yet — only a vague wish — that is brainstorming's job first. Come back here once there is a candidate to sharpen.
- This skill produces a planning INPUT, not a plan. The moment the idea is crisp + the Not-Doing list is set, hand off to Stage 1 (`superpowers:writing-plans`). Do not slide into task breakdown here.
</where_you_are>

<what_superpowers_cannot_know>
The Netdust refinement layer. Run it as two phases — diverge, then converge — and end with a one-pager.

**1. DIVERGE — re-open the idea through lenses before narrowing.**
A generated idea arrives pre-narrowed to its first framing. Force it wider through at least these lenses, capturing each branch:
- **Inversion** — what if we did the opposite? what would make this idea fail / be unnecessary?
- **Constraint-removal** — drop the assumed constraint (no time limit, no schema, no existing infra). What changes?
- **Simplification** — what is the smallest version that still delivers the core value? What if we shipped only that?
- **10x** — what would this look like if it had to be ten times better / serve ten times the scale?
Each lens is a branch to evaluate, not a decision yet. Breadth here is the point.

**2. CONVERGE — cluster, then stress-test against three axes.**
Cluster the branches into a few coherent candidate shapes. Stress-test each surviving candidate against:
- **User-value** — what concrete user goal does this reach that the alternatives don't?
- **Feasibility** — does this fit the locked stack + existing infra, or does it assume something that doesn't exist? (This is where hidden premises surface — see #4.)
- **Differentiation** — does this lean INTO the product's wedge, or could any competitor ship it? (For Folio: markdown-as-truth, agents-first, single-binary. An idea that erodes the wedge is a red flag even if feasible.)
Pick the candidate that wins the three axes. Name WHY the others lost — the discarded branches are evidence, not waste.

**3. Produce an explicit "Not Doing" list — this is the load-bearing Netdust output.**
A refined idea is defined as much by its boundaries as its content. Write the things you considered and are deliberately NOT doing, each with a one-line reason. This is not throat-clearing: **the Not-Doing list becomes the plan's scope boundaries at Stage 1.** A boundary you name here is a boundary writing-plans inherits — which keeps the plan from quietly re-absorbing the scope you just cut.

**4. Surface and record hidden assumptions — they become Stage-1c ground-truth targets.**
Every refined idea rests on premises about the codebase ("we'll reuse the existing X for Y", "the events table already carries Z", "this endpoint accepts that shape"). LIST them explicitly in the one-pager as assumptions, not facts. **Each one becomes a thing Stage 1c (spec-premise ground-truth) must verify against source before the plan ships.** You do not verify them here — refinement is design altitude, not a grep session — but you must NAME them so the gate downstream has a checklist. An unsurfaced premise is the wrong-architectural-premise bug waiting to happen (the "reuse TableView for runs" class).

**5. Output = a one-pager with explicit trade-offs.**
The deliverable is one page: the sharpened idea in a sentence, the candidate that won + why, the discarded branches, the **Not-Doing list**, the **surfaced assumptions**, and the trade-offs taken. That one-pager is the input `superpowers:writing-plans` consumes at Stage 1. Anything longer is drifting into planning; anything without the Not-Doing list + assumptions is an incomplete refinement.
</what_superpowers_cannot_know>

<success_criteria>
A refinement done under this skill:
- Started from `superpowers:brainstorming` for the generative base — not reinvented here.
- DIVERGED through the lenses (inversion, constraint-removal, simplification, 10x) before narrowing.
- CONVERGED by stress-testing candidates against user-value, feasibility, and differentiation — with the losers' reasons named.
- Produced an explicit **Not-Doing list** that Stage 1 will adopt as scope boundaries.
- **Surfaced hidden assumptions** as a checklist Stage 1c will ground-truth against source.
- Ended as a **one-pager with explicit trade-offs**, handed to `superpowers:writing-plans` — not turned into a task breakdown here.
</success_criteria>

<integration>
- **superpowers:brainstorming** — the BASE this skill layers on, and its generative SIBLING. Brainstorming generates the idea; this sharpens it. This skill does not restate intent-drawing or requirement-separation; it adds the convergent refinement above.
- **harnessed-development Stage 0** — the gate that reaches for this skill, alongside brainstorming, when a fuzzy idea needs stress-testing before a plan.
- **superpowers:writing-plans (Stage 1)** — the consumer of this skill's one-pager. The Not-Doing list becomes plan scope boundaries.
- **harnessed-development Stage 1c (spec-premise ground-truth)** — the gate that VERIFIES the assumptions this skill surfaced, reading the named source before the plan ships.
- **thinking-deeply** — for a single high-stakes technical fork inside a candidate, that skill goes deeper on one decision; this skill stays at idea-shape breadth.
- **Provenance** — generative craft from `superpowers` (+ divergent/convergent refinement concepts shared with `addyosmani/agent-skills` `idea-refine`, MIT); the Netdust spine — the Not-Doing-list→scope-boundary handoff, the assumptions→Stage-1c handoff, and the differentiation/wedge axis — is what this file adds.
</integration>
