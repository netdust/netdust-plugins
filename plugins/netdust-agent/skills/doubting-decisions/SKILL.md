---
name: doubting-decisions
description: "CRAFT skill — no superpowers base exists for this (a genuine gap), so it carries its own content, folding in the addyosmani doubt-driven-development concept. It spins up a FRESH-CONTEXT skeptic to adversarially attack a DECISION just made (a plan's key architectural/approach choice), to catch the confirmation bias of the agent that made it. Reached for post-plan (after harnessed-development Stage 1, before Stage 2 execution) OR post-build (before shake-out), when a significant decision should be attacked before more work is committed to it. Use when a plan's core approach was just chosen and you want it stress-tested by a skeptic with no stake in it. Distinct from thinking-deeply (technical first-principles analysis) and devils-advocate (business/strategy decisions) — this is specifically an adversarial review of a DECISION/PLAN to surface what the deciding agent rationalized away. Its output feeds back as a plan-correction, or fires threat-modeling (security doubt) / architecture-invariants (convergence doubt)."
---

<objective>
The agent that just made a decision is the worst-placed to attack it — it spent effort reaching the choice and now defends it (confirmation bias, sunk-cost, "I already see why this is right"). There is no `superpowers:*` base for guarding against that on a DECISION (the closest, `receiving-code-review`, is about reacting to feedback, not generating skepticism). This skill fills that gap: it spins up a **fresh-context skeptic** — an actor with no memory of the reasoning, no stake in the conclusion — whose only job is to find why the decision is WRONG before more work is committed to it.

This is a how-to the harness reaches for, not a gate that fires on its own. It carries its own content because no upstream owns the craft.
</objective>

<not_these_other_skills>
Pick the right tool — this one is narrow on purpose:

- **`thinking-deeply`** — first-principles TECHNICAL analysis of an open question ("Is X best?", "should I use A or B?"). It explores; it does not adversarially attack a choice already made. Use it to MAKE a hard technical decision.
- **`devils-advocate`** — stress-tests BUSINESS / strategy / pricing / positioning decisions. Non-technical. Use it on a proposal or direction.
- **`doubting-decisions` (this skill)** — a fresh-context skeptic spun up to ATTACK an architectural/approach decision *already made* (usually a plan's key choice), specifically to catch the confirmation bias of the agent who made it. The decision exists; the doubt is the deliverable.

If the decision isn't made yet → thinking-deeply. If it's a business call → devils-advocate. If a technical/architectural decision was just locked and you want it attacked before building on it → here.
</not_these_other_skills>

<where_you_are>
Two harness moments reach for this skill:

- **Post-plan** — after `harnessed-development` Stage 1 (plan + its gates), before Stage 2 execution. The plan's core approach is the freshest, most consequential decision in the session — attack it before any task is dispatched, while a correction is still cheap (a plan edit, not a re-build).
- **Post-build, pre-shake-out** — before Stage 3, when a significant approach decision survived into the artifact and you want it doubted before the merge gate.

It is invoked deliberately, not auto-fired. The signal: a non-trivial architectural/approach decision was just made and the cost of it being wrong is high.
</where_you_are>

<the_method>
**1. Spin up a genuinely fresh context.** The doubt has value only if the skeptic does NOT inherit the deciding agent's reasoning. Dispatch a subagent whose prompt states the DECISION and its claimed justification as flatly as possible — not the journey to it — and whose sole instruction is to argue the decision is wrong. (If you must do it in-session, write the decision as a bare claim first and adopt the skeptic stance against that claim; do not re-read your own reasoning trail.)

**2. Attack the DECISION, not the code.** The unit under doubt is the choice — "reuse table X for use Y", "make this synchronous", "put the guard in the route", "this needs no new abstraction". Ask:
- What has to be TRUE for this to be right? Is each of those things actually true, or assumed? (This is the same premise-falsification Stage 1c does against source — here applied to the decision's logic.)
- What is the strongest case for the rejected alternative? Why was it rejected — for a real reason, or because the chosen path was already in motion?
- What does this decision make HARD or impossible later that the alternative wouldn't?
- Where is the confirmation bias — what evidence was discounted because it complicated the preferred answer?
- What's the failure mode no one priced in (scale, concurrency, an actor with different authority, a future requirement the wedge implies)?

**3. Classify each surviving doubt — this routes it back into the harness.**
A doubt is only useful if it changes something. For each one that survives scrutiny, route it:
- **Plan-defect doubt** → feed back as a **plan-correction** (a plan edit + commit) before Stage 2 — the cheapest possible place to fix a wrong approach.
- **Security doubt** (the decision exposes a URL/auth/token/untrusted-parse/BYOK/tenancy surface that wasn't threat-modeled) → **fire `harnessed-development`'s 1a gate — `threat-modeling`** on the decision's surface. A doubt that smells like an attack is a missing threat model.
- **Convergence doubt** (the decision bypasses or duplicates a place where authorization / data-access / live-updates / error-handling / entity-modeling is supposed to be decided once) → **fire the 1b gate — `architecture-invariants`** and check the touched invariant. A doubt that smells like "this decides the same thing in a second place" is a bypassed convergence point.
- **No-change doubt** → if the decision survives the attack intact, RECORD that it was doubted and held. The audit value is real: a decision that withstood a fresh skeptic is one you commit to with evidence, not just momentum.

**4. Stay at decision altitude.** This skill doubts the CHOICE. It does not debug code (that's `systematic-debugging`), does not write tests (`testing-workflow`/`writing-tests`), and does not re-make the decision from scratch (`thinking-deeply`). One decision, attacked, routed.
</the_method>

<success_criteria>
A doubt pass done under this skill:
- Attacked a SPECIFIC decision/plan-choice already made — not an open question (that's thinking-deeply) and not a business call (that's devils-advocate).
- Was run from a **fresh context** that did not inherit the deciding agent's reasoning trail.
- Tested the decision's load-bearing premises ("what must be true for this to be right?") and the strongest case for the rejected alternative.
- Routed every surviving doubt: plan-correction, OR fired `threat-modeling` (security doubt) / `architecture-invariants` (convergence doubt), OR recorded "doubted and held".
- Stayed at decision altitude — did not slide into debugging, testing, or re-deciding.
</success_criteria>

<integration>
- **no superpowers base** — this is a genuine gap; the skill carries its own content. Primary concept folded in from `addyosmani/agent-skills` `doubt-driven-development` (MIT), Netdust-voiced — fresh-context adversarial review applied to a DECISION rather than to code.
- **harnessed-development (Stage 1→2 boundary, and pre-Stage-3)** — the moments that reach for this skill. Its output feeds a plan-correction before execution, or a final doubt before the merge gate.
- **harnessed-development 1a / `threat-modeling`** — fired when a doubt surfaces a security surface the plan didn't model. A security-shaped doubt IS a missing threat model.
- **harnessed-development 1b / `architecture-invariants`** — fired when a doubt surfaces a bypassed/duplicated convergence point. A "decides this twice" doubt IS an invariant concern.
- **thinking-deeply** — use BEFORE the decision (makes the technical call); this is used AFTER (attacks the made call). Complementary, not overlapping.
- **devils-advocate** — its business-decision counterpart. Same adversarial spirit, different domain. Do not use this skill on pricing/strategy.
- **refining-ideas** — the sibling at the front of the pipeline: that one sharpens an idea pre-plan; this one doubts the decision post-plan. Together they bracket Stage 1.
</integration>
