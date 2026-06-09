# harnessed-development — skill-eval iteration 1

Skill under test: `netdust-core:harnessed-development` (SKILL.md, 254 lines, dev tree).
Judges/runners: Sonnet 4.6 subagents. Date: 2026-06-07.

## Part A — Trigger eval (20 queries × 3 independent judges, query order shuffled per judge)

**Result: 20/20 correct on majority vote. 0 false positives, 0 false negatives.**

| | should-trigger | should-NOT |
|---|---|---|
| correctly classified (maj. of 3) | 10/10 | 10/10 |

Split votes (non-determinism, not failures):
- **Q10** "Fix the 6 findings from the code review" (Class C, should-trigger): 2/3 fired. One judge read it as a "research/decision question." The description lists build/plan/security triggers but **never names code-review-finding / Class C bug-fix bundles** as a trigger phrase — a real coverage gap given Class C is one of the four work classes the skill handles.
- **Q20** "FTS5 vs separate search index for v1.1?" (design Q, should-NOT): 1/3 over-fired. Acceptable — a design question legitimately *could* warrant brainstorming; a lone over-fire is noise, not a defect.

## Part B — Behavioral eval (baseline vs with-skill)

**Key context:** the Sonnet baseline is already strong — it threat-analyzes before coding and writes tests-first by default. So discriminating assertions must target the *structural artifacts* the harness mandates that baseline reliably omits, NOT "did it think about security" (baseline already does).

### Eval 1 — "add a webhook receiver … let's get this built" (Class A, 1a-triggering)

| Assertion | Baseline | With-skill | Discriminates? |
|---|---|---|---|
| Does security/threat analysis *before* the route handler | PASS | PASS | NO — baseline already does. Drop. |
| Explicitly **classifies the work** (Class A/B/C/D) before acting | FAIL | PASS (states "Work class: A") | **YES** |
| Names a **`## Threat model` section embedded in the plan** (not just ad-hoc reasoning) | FAIL (reasons about threats, never names the section/gate) | PASS (Stage 1a, BLOCKING, embeds section before task breakdown) | **YES** |
| Fires the **architecture-invariants** check (events-emit / access convergence) | PARTIAL (mentions events rule from memory) | PASS (Stage 1b, cites ARCHITECTURE-INVARIANTS.md + access convergence) | **YES** |
| Plans an **acceptance-flow matrix with edge classes** before breakdown | FAIL | PASS (Stage 1g, enumerates 6 edge classes) | **YES** |
| Mandates the **verbatim test addendum / structured STATUS blocks** on subagent dispatch | FAIL | PASS (Step 2.1 addendum) | **YES** |
| Plans **review-cluster sizing** (~3–4 tasks, STOP markers, security-review on token cluster) | FAIL | PASS (1f, 3 clusters, /security-review on token cluster) | **YES** |

### Eval 2 — "tighten the SSRF check … just a one-line fix" (Class D)

| Assertion | Baseline | With-skill | Discriminates? |
|---|---|---|---|
| Reads the file + greps callers before fixing | PASS | PASS | NO — baseline already does. Drop. |
| Writes a RED-first test before the fix | PASS | PASS | NO — baseline already does. Drop. |
| **Recognizes this as Class D** (named security-boundary file, one-liner notwithstanding) | FAIL (treats as ordinary fix) | PASS (states "Classification: Class D") | **YES** |
| Runs a **structured threat model on the diff** (vs "5-minute informal pass") | FAIL — baseline *explicitly declines*: "not a full formal model, ~5 minutes" | PASS (invokes threat-modeling skill, blocking, on the diff) | **YES** |
| Frames the discipline as a **gate that fires regardless of size**, citing the 2026-06-03 gap | FAIL | PASS (cites the closed gap by name) | **YES** |

## Interpretation

- **The skill works where it claims to.** Its entire value proposition is *gate-coverage durability* — making structural artifacts (work-class label, named threat-model section, invariant citations, acceptance matrix, verbatim addendum, review-cluster STOP markers, Class-D recognition) fire every time instead of relying on the agent to remember. Baseline produced **none** of those structural artifacts; with-skill produced **all** of them. Every discriminating assertion passed with-skill and failed baseline. None of them are passing-in-both (noise) — I dropped the 4 that were.
- **Baseline is not careless** — it does the *spirit* (threat-thinks, tests-first). The skill converts spirit-when-remembered into structure-every-time + auditable evidence. That is exactly the gap the skill's `<objective>` claims to close, and the eval confirms it does.
- **The one concrete description defect:** Class C (bug-fix bundle from code-review/security-review) is a first-class work class in the skill body but absent from the description's trigger-phrase list. It cost a split vote on Q10. Cheap, high-value fix.

## Recommended change (iteration 2 candidate)

Add a Class-C trigger phrase to the description so it fires reliably on review-finding bundles. E.g. append to the trigger list:
`… "ship X", "fix the code-review findings", "fix the findings from /code-review or /security-review", "address review feedback on the branch".`
This is the only change the eval surfaced; everything else measured clean.
