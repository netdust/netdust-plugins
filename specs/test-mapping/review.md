# Branch review — test-mapping

Range: f999fab..7380554 (feature/test-mapping, 8 commits, 18 files)
Reviewer: a fresh, read-only whole-branch reviewer, 2026-09-28. No threat model on the plan and no
`ARCHITECTURE-INVARIANTS.md` in this repo, so no security-sentinel and no invariant-auditor joined.
The fix pass is the commit that carries this file; each finding below says what it did.

Read-only. Spec R1–R10 all land where the plan promised; nothing under superpowers or `plugins/netdust-agent/` is touched (diff stat confirms). The only edits outside netdust-gates are `plugins/netdust-wp/skills/wp-testing/SKILL.md:44-50` (Task 3) and the marketplace entry, both declared in Global Constraints.

## Blocking

None.

## Should fix

1. **`plugins/netdust-gates/commands/shakeout.md:43-44` and `:50` still describe the old model.** Step 2 tells the controller shakeout-qa "derives the flow list from the spec and the plan's `Review Focus`, or `flows.md` on a branch with no spec" and "reports the flow list it derived". The agent it dispatches now reads the `E2E flows` column and never derives (`agents/shakeout-qa.md:25-30`); the two prompts contradict each other in the same dispatch. → fixed as proposed.

2. **`plugins/netdust-gates/skills/policy/edge-classes.md:4` keeps the "pinned to a test" wording the spec removes.** "pin each to a test in the task that owns the code" while the policy now says "Each line points at a Test map row". → fixed: "point each at the Test map row whose test proves it."

## Note

1. **`agents/plan-reviewer.md:13-14`** lists Netdust's additions to the writing-plans format without the two sections a skill owns. → fixed: "`## Threat model`, `## Test map`, `First working version` and `Simplest design`".
2. **`agents/session-reviewer.md:37`** "did the plan's `Review Focus` lines get real assertions" — old phrasing. → fixed: "did each Test map row's test land with a real assertion".
3. **`skills/test-mapping/SKILL.md:9-10`** named the threat model among the consumers that read the map; it feeds it. → fixed.
4. **`skills/test-mapping/SKILL.md:37-38`** "Order rows by the named ask, riskiest first" gives two orderings. → fixed: "Order rows riskiest first."
5. **`evals/cases.json`, `unit-cut-plan` regex 1**: the `\n` after `## Test map` was consumed before the tempered dot's lookahead, so `## Test map\n## Other\n| Unit | Seam |` passed. → fixed: the `\n` dropped. The other regexes behave as the plan says (verified against hand-written samples: a fifth task fails regex 3, a "Run test to verify it fails" step fails regex 4).
6. **`tests/test_evals_shape.py:8` `IDS` and `CLAUDE.md:34`** still said "three" cases, so the eval row's pin would not go red if `unit-cut-plan` were dropped. → fixed: `unit-cut-plan` added to `IDS`; `CLAUDE.md` says "runs the behavioural cases".
7. **The hand-run eval verdict is not recorded on the branch.** → the eval was started after Task 4 (`python3 plugins/netdust-gates/evals/run-evals.py unit-cut-plan`); its verdict is reported in the session and appended below when it returns.
8. **`specs/netdust-gates/spec.md:54-55`** (the authority) still says Review Focus lines are "each line pinned to a test in the owning task". Outside the plan's file list and a dated record. → left for Stefan: a one-clause amendment there, or a line pointing at `specs/test-mapping/spec.md` R6.

No other stale hits: `Scaffolding` as a plan bullet is gone; `six` survives only in session-review's "six dimensions" and the growth rule's "six weeks"; `derive` in `commands/shakeout.md:28` is the no-spec path Ruling 5 keeps. `commands/plan-review.md` carries nothing from the old model. Versions match (0.10.0).

## Review Focus checked

1. A consumer still decides — holds. `agents/shakeout-qa.md:25-30`, `agents/plan-reviewer.md:29-31`; pins `tests/test_test_mapping_skill.py:19-22`. (The controller command said "derives" — Should fix 1, fixed.)
2. Growth rule forbids the map — holds. `CLAUDE.md:16-17`; `tests/test_plugin_manifest.py:25`.
3. Policy over 150 — holds. 142 lines (was 146); pin `tests/test_policy_skill.py:42`.
4. Unit cut skippable — holds. `skills/test-mapping/SKILL.md` `## The unit cut`; eval regexes 3 and 4 reject a fifth task and a verify-fails step.
5. Bar in three copies — holds. `agents/test-pruner.md:17-21` and `agents/plan-reviewer.md:30` cite "What a test owes"; pin `tests/test_test_mapping_skill.py:24-25`.
6. Eval malformed — holds. `tests/test_evals_shape.py:27-29`; all four regexes compile.

Pin falsifiability: every assertion in `test_test_mapping_skill.py` goes red if the edit it guards is reverted; none is vacuous.

## Suite

`bash plugins/netdust-gates/tests/run.sh` — last line: `All harness tests passed.` (Modules passed: 20, failed: 0), before and after the fix pass.
`wc -l`: policy 142 (< 150) · pack 59 (≤ 60) · new skill 37 (< 50).

Findings: 0 Blocking · 2 Should fix · 8 Note
