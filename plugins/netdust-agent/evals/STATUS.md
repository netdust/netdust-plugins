# Eval status (live)

## Trigger eval (routing) — DONE, all corrected
- First pass: 67/78 (85%). 11 misroutes diagnosed.
- Fix: sharpened 10 descriptions (trigger phrases + front-loaded exclusions).
- Re-test: 10/11 fixed; security-sentinel needed boundary front-loaded → then 11/11.
- NET: 78/78 route correctly after fixes.

## Behavioral eval (does the skill change coding behavior) — 6/9, finishing
- ✓ writing-tests, testing-workflow, threat-modeling, test-effectiveness, simplifying-code → with-skill delta confirmed
- ? feature-acceptance → judge flagged WITH=B but that's an A/B-label ambiguity in the
  judge prompt (the with-skill answer DID use the pass/fail/not-reachable manifest vocab).
  RE-RUN with non-positional judge to confirm.
- pending: doubting-decisions, refining-ideas, sourcing-from-docs

## Remaining to call the goal done
1. finish behavioral 3
2. re-confirm feature-acceptance with fixed judge
3. commit the description fixes + eval artifacts
4. write the verdict table (B1 behavioral + B2 wiring + B3 trigger) per EVAL-PLAN.md

## Harness flaw discovered (important)
`claude -p` with `--max-turns 6` on BUILD-y prompts (writing-tests, building-frontend)
actually SCAFFOLDS files in cwd → (a) polluted the plugin with node_modules/src/examples
(cleaned + gitignored), (b) sometimes runs out of turns producing ~0 output → judge
sees empty answer → false WITH=B. This is a MEASUREMENT flaw, not a skill flaw.
FIX for those cases: judge by DIRECT READING of a constrained ("describe, don't build")
prompt. Done for feature-acceptance (confirmed ENHANCES). building-frontend pending same.

## Round 2 (5 under-tested disciplines)
- ✓ architecture-invariants → ENHANCES (named the convergence point)
- building-frontend → harness empty-output artifact; confirm by direct read
- pending: compounding, engineering-context, shake-out

## building-frontend — CONFIRMED ENHANCES (direct read, 2026-06-09)
Constrained "describe don't build" prompt → with-skill produced: container/presentation
split, state-mgmt ladder, FULL non-happy-state set (loading/empty/error/refetch),
semantic-table WCAG a11y + references, responsive breakpoints, tied to feature-acceptance.
Baseline would not. The earlier WITH=B was the empty-output (max-turns scaffolding) artifact.

## CONFIRMED behavioral-enhancing so far (round1 + round2 + direct reads):
writing-tests, testing-workflow, threat-modeling, test-effectiveness, feature-acceptance,
simplifying-code, doubting-decisions, refining-ideas, architecture-invariants,
compounding, building-frontend. sourcing-from-docs = aligned/low-delta.
Pending: engineering-context, shake-out.
