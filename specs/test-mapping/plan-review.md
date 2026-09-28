# Plan review — test mapping

Reviewed-plan: cd807b5b8adf694e4b829a9bac89bb1268a26f44
Verdict: ready with fixes

Filed 2026-09-28 by a fresh, read-only plan-reviewer dispatched on the plan as committed in
d929ebc. The three Should fix findings and Notes 1, 2, 3 and 6 were folded into the plan in the
commit that carries this file; the reviewed blob above is the text the findings quote.

## Blocking

None. Every "replace X with Y" quotes text that exists in the named file at the current text; every requirement R1–R10 has a task; the plan's Test map, Review Focus lines and Rulings hold against the source.

## Should fix

1. **R7 is only half-tasked: `plan-reviewer` still carries its own copy of the bar and never cites `wp-testing`.** Task 2, Step 2 replaces `agents/plan-reviewer.md:30-31` with a three-clause restatement of the bar the spec calls the third copy (spec R7). Task 2 Step 4 does this for `test-pruner`; nothing does it for `plan-reviewer`, and the Step 5 pin asserts only `"Test map" in …`. Smallest change: end the replacement with "— the bar is "What a test owes" in `netdust-wp:wp-testing`", drop the three clauses; extend the pin to `"What a test owes" in (AGENTS / "plan-reviewer.md").read_text()`. → folded in.

2. **Task 2, Step 1 reintroduces the self-derivation the spec removes.** The replacement for `agents/shakeout-qa.md:25-30` ends with a fallback ("A plan with no Test map … fall back to one flow per user-facing requirement"). Spec R6: "none of them decides". The sentence is a decision rule in a consumer, not stated as a Ruling, and the pin cannot see it. Smallest change: strike it, or keep it and add it as a Ruling with its cost (`skills/policy/SKILL.md:99`, "an old or half plan never holds up the work", is the argument for keeping it). → kept, Ruling 6.

3. **Task 2, Step 4 leaves two dangling references to "six" in `test-pruner.md`, and the pin cannot see them.** `test-pruner.md:42` "passes all six unchanged" and `:61` "items 1–6" survive the rewrite; the pin checks `"all six hold"`, which line 42 does not contain. Smallest change: rewrite `:42` and `:61`; tighten the pin to `"all six" not in …`. → folded in.

## Note

1. **Two quoted strings are line-wrapped in the file.** `plugins/netdust-gates/CLAUDE.md:16-17` breaks after "plan"; `agents/plan-reviewer.md:30-31` breaks after "names a". Match the wrapped text; keep "a skill does not own" on one line for the pin. → folded in.
2. **Global Constraints vs Task 4.** Task 4 also edits the repo-root `.claude-plugin/marketplace.json`, and Task 3 replaces two paragraphs (`wp-testing/SKILL.md:46`, `:48`) with one rather than removing one; Ruling 1's "four-line deletion" is the same mis-sizing. → folded in.
3. **The banned-grammar pin does not scan the new skill.** `tests/test_policy_skill.py:37` reads four files and will not read `skills/test-mapping/SKILL.md`. Add it to the scan. → folded in.
4. **`CLAUDE.md` Boundaries lists "tiers" as not to be re-added (`CLAUDE.md:22`), and the map has a tier column.** The plan pre-empts this ("tier is fine; the pack uses it" — `wordpress.md:28-31`, `CLAUDE.md:15` "a gate tier"). Holds; flagged so Stefan sees the word was weighed.
5. **The eval's fourth regex catches superpowers' canonical phrasing but not every variant.** Rejects "Run test to verify it fails" and "run tests to confirm they fail"; passes "Run the test - should fail", "Watch it fail", "Expected: FAIL". Superpowers is not installed in this container, so the template wording could not be re-read. Acceptable for a stochastic eval; widen the alternation if the first run passes an `Expected: FAIL` step.
6. **`threat-modeling`'s description line still says mitigations become Review Focus lines** (`skills/threat-modeling/SKILL.md:3`). Still true, reads as the old model. → folded in (one phrase).
7. **R4's "after the unit's last edit"** is not in the skill's unit-cut paragraph; the pack carries the rule at `wordpress.md:29-30` and the skill cites `wp-testing`. Adequate; noting where the evidence rule lives.

## Premises checked

- Policy `## The plan` has a Review Focus bullet with two sub-bullets and a Scaffolding bullet, contiguous → `skills/policy/SKILL.md:72-83` → holds
- Policy `## Execution mode` is one paragraph → `skills/policy/SKILL.md:103-105` → holds
- Policy is 146 lines now and ends at 143 after Task 1 Step 2 → holds
- Policy keeps every `ok_tok` token after the edit → `tests/test_policy_skill.py:25-29` → holds
- `"Test map"` and `"netdust-gates:test-mapping"` appear in the replacement policy text → holds
- `wordpress.md` Plan shape first bullet → `skills/policy/wordpress.md:52-53` → holds; `Tests:` constraint stays → `:28-32` → holds; pack stays ≤ 60 lines → holds
- `CLAUDE.md` growth rule wording and the manifest pin → `CLAUDE.md:16`, `tests/test_plugin_manifest.py:25` → holds (wrapped)
- `shakeout-qa.md` `## Which flows` first paragraph and the `flows.md` paragraph → `:25-30`, `:32-34` → holds
- `plan-reviewer.md` question 2, mitigation sentence, description, Should fix template → `:30-31`, `:33`, `:3`, `:65` → holds
- `threat-modeling/SKILL.md` last paragraph and the four list names → `:30-33`, `:19-24` → holds
- `test-pruner.md` `## The bar` and "The usual suspects" → `:17-30`, `:32` → holds
- `wp-testing/SKILL.md` `### Choosing the tier` two paragraphs; "What a test owes" section → `:44-48`, `:15` → holds
- No pin other than the manifest pin reads text being removed; netdust-wp's tests do not pin `wp-testing` → holds
- Task 3 pin path resolves → holds
- `test_evals_shape.py` requirements; all four regexes compile → holds
- `run-evals.py` accepts `where: "plan"` and a case id → `:38-39`, `:73` → holds
- Version convention and the marketplace pin → `.claude-plugin/plugin.json:3-4`, `tests/test_plugin_manifest.py:22-24` → holds
- New skill 38 lines, frontmatter regex, every pinned token, no banned token → holds
- Simplest design: consumers would still decide → `agents/shakeout-qa.md:25`, `agents/plan-reviewer.md:30` → holds
- R8: nothing under superpowers or `plugins/netdust-agent/` in any task → holds
- Review Focus 1–6 each name a Test map row and an existing pin → holds
