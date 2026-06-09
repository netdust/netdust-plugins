---
name: simplifying-code
description: "CRAFT skill — the how-to that the code-simplicity-reviewer agent and the /simplify command embody: reduce complexity while PRESERVING behavior. Restated from addyosmani/agent-skills code-simplification (MIT): YAGNI, remove unnecessary abstraction/indirection, delete dead code, prefer the simpler construct. Reached for at harnessed-development Stage 3 (review), or any time a fix feels hacky ('knowing what I know now, the elegant version'). The Netdust layer: simplification must NOT change behavior, so the testing-workflow suite is the safety net — green before AND after the change is the proof it stayed behavior-preserving; this skill is quality-only and never hunts for bugs (that is /code-review). Aligns with the Netdust core principle 'Simplicity First / impact minimal code.' Use when reducing complexity of working code."
---

<objective>
This skill is the how-to for **making working code simpler without changing what it does**. The `code-simplicity-reviewer` agent and the `/simplify` command are the *doers*; this skill is the discipline they embody. It restates `addyosmani/agent-skills:code-simplification` (MIT) as the base, then binds it to the one Netdust guarantee: the test suite is the safety net that proves behavior was preserved. You are at Stage 3 (review) of `harnessed-development`, or you just wrote a fix that feels hacky and want the elegant version instead.
</objective>

<preserve_behavior>
**The contract of simplification: behavior in == behavior out.** You are changing the *shape* of the code, never its observable result. If a change alters what a caller sees, it is not a simplification — it is a refactor with a behavior change, and it belongs back in the harness with its own test. Quality only: **this skill does not hunt for bugs** — that is `/code-review`. If you find a bug while simplifying, hand it to the harness; do not silently "fix" it inside a simplification pass.
</preserve_behavior>

<the_moves>
The simplifications, in rough order of payoff:
- **YAGNI** — delete the speculative generality: the config flag with one value, the parameter every caller passes the same, the abstraction built for a second case that never came.
- **Remove unnecessary abstraction / indirection** — collapse a wrapper that only forwards, a one-implementation interface, a layer that adds a hop and no value. Fewer hops to read = simpler.
- **Delete dead code** — unreachable branches, unused exports, commented-out blocks, a helper with no callers. Dead code is a maintenance tax with no payer.
- **Prefer the simpler construct** — the plain map/filter over the hand-rolled loop, the early return over the nested `if`, the standard-library call over the bespoke utility, the direct expression over the temporary that is used once.
</the_moves>

<the_safety_net>
This is the Netdust spine — why this how-to lives inside *this* harness, and the part addy cannot know:

**The `testing-workflow` suite is the proof that behavior was preserved.** Because simplification must not change behavior, the suite is your net, run on **both sides** of the change:
1. **Green BEFORE** — confirm the suite passes on the code as-is. If it is red first, you have nothing to compare against — fix or characterize before simplifying.
2. Make the simplification.
3. **Green AFTER, identically** — the same tests pass with no edits to the tests themselves. *Editing a test to make a simplification pass is the tell that you changed behavior* — back it out.

If a surface has no test covering the behavior you are about to reshape, that gap is real: characterize it with a Tier-A test (via `testing-workflow` → `writing-tests`) *before* simplifying, so the net actually catches a regression. Simplifying untested behavior on faith is how a "harmless cleanup" ships a defect.
</the_safety_net>

<the_elegance_trigger>
Beyond the scheduled Stage 3 review, reach for this skill the moment **a fix feels hacky**. The Netdust principle is "knowing everything I know now, implement the elegant solution" — when you have just made something work by force, pause and ask whether the simpler construct now exists. This is also the project's "Simplicity First / impact minimal code" core principle in action: the smallest change that preserves behavior, not the cleverest.
</the_elegance_trigger>

<success_criteria>
A simplification done under this skill:
- **Preserved behavior** — the suite was green BEFORE and is green AFTER, with the **tests themselves unchanged**.
- Applied the moves: **YAGNI, removed indirection, deleted dead code, preferred the simpler construct** — only where it genuinely reduces complexity.
- Was **quality-only** — no bug-hunting (that is `/code-review`); any bug found was handed to the harness, not fixed inline.
- Characterized any **untested behavior with a test first**, so the safety net could actually catch a regression.
</success_criteria>

<integration>
- **`code-simplicity-reviewer` agent + `/simplify` command** — the DOERS that embody this skill. This skill is the how-to; those are the tools that run it. Pair them.
- **`addyosmani/agent-skills:code-simplification`** (MIT) — the base craft (YAGNI, remove abstraction, delete dead code, simpler construct) restated here in Netdust voice.
- **`harnessed-development` Stage 3 (review)** — the step that reaches for this skill; also the elegance trigger when any fix feels hacky.
- **`testing-workflow` / `writing-tests`** — the safety net. Green before AND after, tests unchanged, is the proof behavior was preserved; characterize untested behavior here before simplifying.
- **`/code-review`** — the bug-hunting sibling. This skill is quality-only; correctness defects go there.
- **Provenance** — simplification moves from `addyosmani/agent-skills:code-simplification` (MIT); the behavior-preservation-via-the-suite contract, the test-unchanged tell, and the "Simplicity First" alignment are the Netdust spine this file adds.
</integration>
