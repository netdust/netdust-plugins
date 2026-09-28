# Test mapping — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (Native) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Each task is one unit, written in one pass and closed by its row's command in the Test map below.

**Goal:** A `## Test map` plan section, produced by a new `netdust-gates:test-mapping` skill that also owns the unit cut, and five consumers in netdust-gates that read it instead of deciding.

**Architecture:** One new prose skill beside `threat-modeling`; small edits to the policy, the WordPress pack, three agents and the plugin's `CLAUDE.md`; one pin test file; one eval case; a version bump. Nothing under superpowers or `netdust-agent` is touched. The plan itself carries a Test map and is cut into units, so it is the first artifact written the way it prescribes.

**Tech Stack:** Markdown skills and agents; bare `python3` pin tests (`bash plugins/netdust-gates/tests/run.sh`); `claude -p` for the eval.

**Spec:** `specs/test-mapping/spec.md`

**First working version:** Task 1 — after it, a session on a WordPress project that writes a plan produces a `## Test map` and unit-shaped tasks; `bash plugins/netdust-gates/tests/run.sh` proves the skill and policy have the shape before any consumer reads it.

**Simplest design:** The simplest design that meets the ask is one new skill and one invocation line in the policy, with every consumer left as it is. It is not chosen because the consumers are the reason the decision is scattered: `shakeout-qa` would still derive its own flows and `plan-reviewer` would still check Review Focus lines against tests rather than rows, so the map would be a seventh opinion instead of the only one (spec R6). What the plan adds beyond that minimum is exactly those five reads, one pin file and one eval case; no checker, no new hook, no plan grammar.

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| The producer: `test-mapping` skill, policy invocation, pack bullet, growth rule | the plan a session writes | pin · `plugins/netdust-gates/tests/test_test_mapping_skill.py`, `test_policy_skill.py`, `test_plugin_manifest.py` · `bash plugins/netdust-gates/tests/run.sh` | `python3 plugins/netdust-gates/evals/run-evals.py unit-cut-plan` |
| The consumers: `shakeout-qa`, `plan-reviewer`, `threat-modeling`, `test-pruner` | the agents' prompts as dispatched | pin · same file · same command | none — the agents run only in a live session (Ruling 3) |
| `wp-testing` pointer (netdust-wp) | the skill text a WP dispatch loads | pin · same file · same command | none |
| Eval case and version | `evals/cases.json`, both manifests | pin · `test_evals_shape.py`, `test_plugin_manifest.py` · same command | `python3 plugins/netdust-gates/evals/run-evals.py unit-cut-plan` |

## Global Constraints

- The policy skill stays under 150 lines (`test_policy_skill.py` pins it); the new skill stays under 50 and cites `netdust-wp:wp-testing` and `edge-classes.md` rather than restating them.
- No 0.28 plan grammar anywhere in the skills: `gate-check`, `tasks.md`, `Lane:`, `Cluster`, `Stakes:`, `Test-author` (`test_policy_skill.py` scans for them). "tier" is fine; the pack uses it.
- Nothing under `plugins/netdust-agent/` (retired) and nothing in superpowers is edited (spec R8). The edits outside netdust-gates are Task 3, in `plugins/netdust-wp/skills/wp-testing/SKILL.md` (two paragraphs become one), and the marketplace entry in Task 4.
- `bash plugins/netdust-gates/tests/run.sh` exits 0 after every task; its `All harness tests passed.` line is quoted in the task report. The eval is run by hand once at the end and its result reported, red or green (stochastic: red tightens the skill).
- Commit by path on `feature/test-mapping`. No merge, no push to `main`, no `git add -A`, no stash.
- Version 0.10.0 in `plugins/netdust-gates/.claude-plugin/plugin.json` and the matching entry in `.claude-plugin/marketplace.json`, with a description line prepended in the plugin's convention.
- Skills are contracts, not books: the skill says the shape, the question, the cut and the evidence rule, and nothing that `wp-testing` or `edge-classes.md` already says.

## Review Focus

Most likely first. Each line points at a Test map row and names its pin.

1. **A consumer still decides.** `shakeout-qa` keeps "No plan table lists them; you derive them", or `plan-reviewer` still checks Review Focus lines against tests instead of rows. → consumers row; pins in `test_test_mapping_skill.py`: `shakeout-qa.md` contains `Test map` and not `No plan table lists them`; `plan-reviewer.md` contains `Test map`.
2. **The growth rule now forbids the map.** `CLAUDE.md` still says "Never as a new plan field" while the map is a section, and `test_plugin_manifest.py` pins the old wording. → producer row; the manifest pin changes with the wording, and asserts `a skill does not own`.
3. **The policy tips over 150 lines.** Two bullets leave (Scaffolding, the two-check pinning detail) and one enters; the count must end below 150. → producer row; the existing line-count pin.
4. **The unit cut is prose the planner can skip.** Superpowers' `writing-plans` still says bite-sized tasks; if the skill only describes the map and not the cut, plans come back with twenty red/green tasks under a good table. → producer row; the eval `unit-cut-plan` fails a plan with a fifth task or a "run the test to verify it fails" step.
5. **The bar comes back in three copies.** `test-pruner` keeps its six rules verbatim. → consumers row; pin: `test-pruner.md` contains `What a test owes` and not `A test survives only when all six hold`.
6. **The eval case is malformed.** → eval row; `test_evals_shape.py` (id, prompt, files, expect, absent; every regex compiles).

## Rulings made while planning

| # | Ruling | Costs if wrong |
|---|---|---|
| 1 | **Task 3 edits `netdust-wp`.** Spec R6/R7 name `wp-testing` as the home of the bar and the runners; its "Choosing the tier" paragraph is the sixth place that decides tier. Replacing its two paragraphs with one pointer is the only edit in another plugin. | Stefan strikes Task 3; the paragraph stays and disagrees with the map by a sentence. |
| 2 | **The skill carries one example row.** An example is text agents copy, which is the point here: the table shape is the contract. The example is a booking, so it matches the eval. | Plans copy "BookingService" into unrelated features; the eval would show it. |
| 3 | **No e2e for the consumers.** The agents only run dispatched in a live session; the eval drives the planner, not `shakeout-qa`. Their proof is the pin on the prompt text plus the next real shake-out. | A consumer edit reads well and misbehaves live; found on the first feature that runs it. |
| 4 | **Execution mode: Native.** Four prose units sharing one test run; no security boundary; nothing outlives one context. | None material. |
| 5 | **`flows.md` stays.** A branch with no plan still has no map; `shakeout-qa` keeps that path unchanged. | None. |
| 6 | **A plan with no Test map does not block the shake-out.** `shakeout-qa` falls back to one flow per user-facing requirement and says so; the policy already rules that an old or half plan never holds up the work (`skills/policy/SKILL.md`, "Nothing blocks code on a plan's state"). The fallback is the one decision left in a consumer, and it is written here. | A pre-0.10 plan gets a thinner shake-out than a mapped one; the report names it. |

## For Stefan at review

- Task 3 is the only cross-plugin edit; strike it if you want this branch inside netdust-gates only.
- The eval needs the `claude` CLI and is run by hand at the end of Task 4.

---

### Task 1: The producer — the skill, the policy, the pack, the growth rule

**Files:**
- Create: `plugins/netdust-gates/skills/test-mapping/SKILL.md`
- Create: `plugins/netdust-gates/tests/test_test_mapping_skill.py`
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md` (`## The plan`, `## Execution mode`)
- Modify: `plugins/netdust-gates/skills/policy/wordpress.md` (Plan shape, first bullet)
- Modify: `plugins/netdust-gates/CLAUDE.md` (the growth rule)
- Modify: `plugins/netdust-gates/tests/test_policy_skill.py` (token), `tests/test_plugin_manifest.py` (growth-rule wording)

**Interfaces:**
- Produces: the `## Test map` section shape (four columns) and the `netdust-gates:test-mapping` name every consumer cites.
- Produces: `tests/test_test_mapping_skill.py` exposing `run() -> list[tuple[bool, str]]`, extended by Task 2 and 3.

- [ ] **Step 1: Write the skill.** `plugins/netdust-gates/skills/test-mapping/SKILL.md`:

````markdown
---
name: test-mapping
description: Use while writing a plan, after the threat model and before the tasks — produces the plan's `## Test map` (one row per unit: seam · tier · file · command · e2e flows) and cuts the tasks to those units. Invoked by netdust-gates:policy. Not for writing tests; `netdust-wp:wp-testing` owns how.
---

# Test mapping — the units and what proves them

Produce `## Test map` in the plan BEFORE the tasks. It is the plan's one answer to "where are
the tests and what do they test"; every consumer (`Review Focus`, `plan-reviewer`,
`shakeout-qa`, the threat model) reads it, and none re-decides it.

## The table

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| BookingService | `POST /ntdst/v1/bookings` | integration · `tests/Integration/BookingTest.php` · `ddev composer test:int` | book-table, booking-denied-without-nonce |
| Booking admin list | `wp-admin?page=bookings` | none — proven by flow | staff-sees-today |

- **Unit** — one thing a single test run can judge: a service or module together with what it
  needs to be judged. A unit that needs another unit's code to be judged is one unit.
- **Seam** — what a caller uses: a route, a render, a public method. Never a private one.
- **Tests** — the tier by one question: does this unit encode a rule THIS project chose (a
  window, a role, a price, a parse of guest input), or is it configuration over a framework that
  already carries the rule (a CPT, a field map, a template)? The first gets a behavioural test
  through its seam — integration when it needs WordPress or the database, unit otherwise. The
  second gets `none — proven by flow`. Every data flow's denial (the refused actor, the missing
  nonce) is a test in its unit's row, written RED first. A scaffold reads `scaffold — deleted by
  task N`. Runners, layout and what a test owes: `netdust-wp:wp-testing`. Edges: `edge-classes.md`.
- **E2E flows** — the flows a person drives, by name. `shakeout-qa` drives exactly these through
  the real browser or the un-mocked wire and commits them. The implementer never drives its own.

## The unit cut

A task is one row. It writes the unit and its tests in one pass, runs the row's command, then
`make gate`, quotes both in its report, and commits. No RED-first step inside a unit except the
denial test; RED-first also holds for every fix in the Close's fix pass. A row with an empty tests
cell is the plan saying that unit is unverified: fill it or say so. Order rows by the named ask,
riskiest first.
````

- [ ] **Step 2: Policy — invoke it, point Review Focus at rows, drop what the map now carries.** In `plugins/netdust-gates/skills/policy/SKILL.md`, under `## The plan`, replace the `Review Focus` bullet and its two sub-bullets, and the `Scaffolding` bullet, with:

```markdown
- **Test map** — invoke `netdust-gates:test-mapping`, after the threat model and before the
  tasks: one row per unit (seam · tier · file · command · e2e flows); a task is one row.
- **Review Focus** — one line per mitigation in the threat model, per convergence point of an
  `ARCHITECTURE-INVARIANTS.md` the diff touches, and per class in `edge-classes.md` the feature
  can actually meet, most likely first. Each line points at a Test map row; an absence or a count
  ("never", "only", "exactly one") points at an `ARCHITECTURE-INVARIANTS.md` check instead, which
  `invariant-auditor` runs at review — never a test that reads source (`source-scan-ratchets`).
```

  Replace the `## Execution mode` paragraph with:

```markdown
Stefan chooses at the plan handoff; you recommend by rule. **Native** by default: it runs each
unit as the plan wrote it. Recommend **subagent-driven** only for a security-boundary unit or a
plan that outlives one context: its implementers follow upstream's per-task TDD, which undoes
the unit cut. Name the rule that fired.
```

  Check: `wc -l plugins/netdust-gates/skills/policy/SKILL.md` prints a number below 150.

- [ ] **Step 3: Pack — the denial lives in the row.** In `wordpress.md`, Plan shape, replace the first bullet with:

```markdown
- Each data flow's unit carries the test that drives the **denial** — the unauthorized actor
  refused, the missing nonce rejected — RED first, named in its Test map row.
```

- [ ] **Step 4: Growth rule.** In `plugins/netdust-gates/CLAUDE.md` (the sentence wraps after "plan"; match the wrapped text, and keep the five words "a skill does not own" on one line for the pin), replace "Never as a new plan field or a new check on plan grammar." with "Never as a plan section a skill does not own (the threat model and the test map are the two, each owned by its skill) or a new check on plan grammar." Update `tests/test_plugin_manifest.py`: the CLAUDE.md pin asserts `"a skill does not own" in claude_md` in place of `"Never as a new plan field" in claude_md`.

- [ ] **Step 5: Pins.** Add `"Test map"` and `"netdust-gates:test-mapping"` to the `ok_tok` tuple in `test_policy_skill.py`, and add `SKILLS / "test-mapping" / "SKILL.md"` to the files its `BANNED_GRAMMAR` scan reads. Create `tests/test_test_mapping_skill.py`:

```python
"""test_test_mapping_skill.py — the Test map has one producer and its consumers read it."""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
GATES = PLUGIN / "skills" / "test-mapping" / "SKILL.md"
AGENTS = PLUGIN / "agents"


def run() -> list[tuple[bool, str]]:
    skill = GATES.read_text()
    head = re.match(r"---\nname: test-mapping\ndescription: .+\n---\n", skill)
    return [
        (head is not None, "test-mapping: frontmatter is `name: test-mapping` + one-line description"),
        (len(skill.splitlines()) < 50, f"test-mapping: under 50 lines (got {len(skill.splitlines())})"),
        ("| Unit | Seam | Tests: tier · file · command | E2E flows |" in skill, "test-mapping: the four-column table header"),
        (all(t in skill for t in ("netdust-wp:wp-testing", "edge-classes.md", "## The unit cut", "RED first", "none — proven by flow")),
         "test-mapping: cites wp-testing and edge-classes, carries the unit cut, the denial rule and the no-test tier"),
    ]
```

- [ ] **Step 6: Run and commit.** `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -3` — expected last line `All harness tests passed.`; quote it. `git add plugins/netdust-gates && git commit -m "feat(gates): the Test map — test-mapping skill, policy invocation, unit cut"`.

---

### Task 2: The consumers — shakeout-qa, plan-reviewer, threat-modeling, test-pruner

**Files:**
- Modify: `plugins/netdust-gates/agents/shakeout-qa.md` ("Which flows")
- Modify: `plugins/netdust-gates/agents/plan-reviewer.md` (description; question 2; the Should fix line)
- Modify: `plugins/netdust-gates/skills/threat-modeling/SKILL.md` (last paragraph)
- Modify: `plugins/netdust-gates/agents/test-pruner.md` ("The bar")
- Modify: `plugins/netdust-gates/tests/test_test_mapping_skill.py`

**Interfaces:**
- Consumes: the `## Test map` section and column names from Task 1. Produces nothing new.

- [ ] **Step 1: shakeout-qa.** Replace the first paragraph of `## Which flows` (from "No plan table lists them" through "is `unverified`, not `pass`.") with:

```markdown
The plan's `## Test map` lists them: drive every flow named in its `E2E flows` column, and no
other — your report shows the list so nothing is silently absent. Take each flow's edges from
`edge-classes.md` beside the `netdust-gates:policy` skill (empty, denied actor, re-entry,
concurrent, boundary, mid-flow failure, delivery seam). A flow driven on its happy path only is
`unverified`, not `pass`. A plan with no Test map is a plan-review finding, not yours to repair:
fall back to one flow per user-facing requirement and say so in the report.
```

  The `flows.md` paragraph that follows stays as it is.

- [ ] **Step 2: plan-reviewer.** In question 2 (the sentence wraps after "names a"; match the wrapped text), replace "Each `Review Focus` line names a test that exists in a task's steps with a real assertion, not a wish — through a caller's seam, expected value from the spec." with "Every `## Test map` row has its test in the task that is that row — the bar is \"What a test owes\" in `netdust-wp:wp-testing`, the row's command runnable; each `Review Focus` line points at a row." Replace "Each threat-model mitigation has a named home in a task." with "Each threat-model mitigation has a row." In the description line, replace "each Review Focus line a test" with "each Test map row a test". In the report template, the Should fix line reads `(a Test map row with no real test; an invented task; a contradiction)`.

- [ ] **Step 3: threat-modeling.** In the description line, replace "which becomes its Review Focus lines and the security review's target" with "whose mitigations become Test map rows and the security review's target". Replace the last paragraph ("Every mitigation becomes a `Review Focus` line pinned as the policy says …") with:

```markdown
Every mitigation is a `## Test map` row (`netdust-gates:test-mapping`) or, for a "never"/"only"
mitigation, an `ARCHITECTURE-INVARIANTS.md` check — and the denial, the actor who is refused, is
asserted, not only the allowed path (`traverse-clause`: every route had a guard, no test asserted
the denial, cross-tenant reads shipped green).
```

- [ ] **Step 4: test-pruner.** Replace the six-rule list under `## The bar` (from "A test survives only when all six hold." through rule 6) with:

```markdown
A test survives only when it meets "What a test owes" in `netdust-wp:wp-testing` — a decided
behaviour, an expected value that can disagree with the implementation, outcomes not call shape,
a caller's seam, and it can fail — plus one rule of this audit: it sits at the lowest seam that
proves it and duplicates no nearby test; a behaviour the project does not own (a vendor package it
never edits, WordPress core) belongs in that package's suite. Missing evidence for any one is DELETE.
```

  Keep "The usual suspects" and everything after, with two touches: the KEEP disposition reads "looks suspect, passes the bar unchanged", and the report line reads "Each KEEP and REWRITE: each point of the bar and the audit rule, one line each, with evidence".

- [ ] **Step 5: Pins.** Append to the list returned by `run()` in `test_test_mapping_skill.py`:

```python
        ("Test map" in (AGENTS / "shakeout-qa.md").read_text() and "No plan table lists them" not in (AGENTS / "shakeout-qa.md").read_text(),
         "shakeout-qa reads the Test map's flows and no longer derives them"),
        ("Test map" in (AGENTS / "plan-reviewer.md").read_text() and "What a test owes" in (AGENTS / "plan-reviewer.md").read_text(),
         "plan-reviewer checks rows and cites the bar"),
        ("Test map" in (PLUGIN / "skills" / "threat-modeling" / "SKILL.md").read_text(), "threat-modeling points mitigations at rows"),
        ("What a test owes" in (AGENTS / "test-pruner.md").read_text() and "all six" not in (AGENTS / "test-pruner.md").read_text(),
         "test-pruner cites the bar instead of carrying it"),
```

- [ ] **Step 6: Run and commit.** `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -3` → `All harness tests passed.`, quoted. `git add plugins/netdust-gates && git commit -m "feat(gates): consumers read the Test map — shakeout-qa, plan-reviewer, threat-modeling, test-pruner"`.

---

### Task 3: wp-testing stops deciding the tier (netdust-wp — strike if unwanted)

**Files:**
- Modify: `plugins/netdust-wp/skills/wp-testing/SKILL.md` (`### Choosing the tier`)
- Modify: `plugins/netdust-gates/tests/test_test_mapping_skill.py`

- [ ] **Step 1:** Replace the two paragraphs under `### Choosing the tier` (from "Put each behaviour at the lowest tier" through "proves the rule is actually wired in.") with:

```markdown
The plan's `## Test map` decides the tier per unit (`netdust-gates:test-mapping`): a rule the
project chose gets a behavioural test through its seam, integration when it needs WordPress or
the database; configuration over the framework is proven by the e2e flow that renders it. Never
prove the same thing at two tiers. A stubbed unit suite proves the code matches the stubs, not
that the feature works — the flow through the real entry point proves the wiring.
```

- [ ] **Step 2: Pin.** Append: `("netdust-gates:test-mapping" in (PLUGIN.parent / "netdust-wp" / "skills" / "wp-testing" / "SKILL.md").read_text(), "wp-testing points tier choice at the Test map"),`

- [ ] **Step 3: Run and commit.** `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -3` → quoted. `git add plugins/netdust-wp/skills/wp-testing/SKILL.md plugins/netdust-gates/tests/test_test_mapping_skill.py && git commit -m "docs(wp): wp-testing points tier choice at the Test map"`.

---

### Task 4: The eval case and the version

**Files:**
- Modify: `plugins/netdust-gates/evals/cases.json`
- Modify: `plugins/netdust-gates/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

- [ ] **Step 1: Eval case.** Append to `cases.json`:

```json
{
  "id": "unit-cut-plan",
  "prompt": "specs/booking/spec.md is approved by Stefan; do not ask questions. Write the implementation plan to specs/booking/plan.md.",
  "files": {
    "site.yml": "structure:\n  type: bedrock\n  wpcli_path: web/wp\n",
    "composer.json": "{\"require\": {\"roots/wordpress\": \"^6.6\", \"netdust/ntdst-core\": \"^5.1\"}}\n",
    "specs/booking/spec.md": "# Booking — spec\n\n## Requirements\n\n**R1 — Booking request.** A visitor books a table from a form: date, time, party size, name, e-mail. The booking is stored as a `booking` post with those fields.\n*Source: \"people book a table from the site\"*\n\n**R2 — Confirmation.** The visitor gets a confirmation mail with the booking's reference.\n*Source: \"they get a confirmation\"*\n\n**R3 — Admin list.** Staff see bookings per day in wp-admin.\n*Source: \"we need to see the bookings per day\"*\n\n## Security-relevant surfaces\n- [x] A form or REST route taking guest input (R1)\n"
  },
  "expect": [
    {"where": "plan", "match": "(?s)## Test map\\n(?:(?!\\n#{1,2} ).)*?\\| Unit \\| Seam \\|"},
    {"where": "plan", "match": "(?is)## Threat model"},
    {"where": "plan", "match": "(?s)\\A(?:(?!### Task [5-9]:).)*\\Z"},
    {"where": "plan", "match": "(?s)\\A(?:(?!(?i:run (the )?tests? to (verify|confirm|watch) (it|they) fails?)).)*\\Z"}
  ],
  "absent": []
}
```

- [ ] **Step 2: Version.** Set `"version": "0.10.0"` in both manifests and prepend to both descriptions: `0.10.0: the Test map — netdust-gates:test-mapping writes a plan section with one row per unit (seam · tier · file · command · e2e flows) and cuts the tasks to those units; RED-first stays for the denial test and the Close fix pass; shakeout-qa, plan-reviewer, threat-modeling and test-pruner read it instead of deciding; the growth rule reads "never a plan section a skill does not own". Eval case unit-cut-plan. `

- [ ] **Step 3: Run, eval, commit.** `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -3` → quoted. `python3 plugins/netdust-gates/evals/run-evals.py unit-cut-plan` → report its verdict as it comes, red or green. `git add plugins/netdust-gates .claude-plugin/marketplace.json && git commit -m "feat(gates): 0.10.0 — eval unit-cut-plan, version"`. Push the branch; the Close is `make review`-less here (no `site.yml`): one whole-branch review by a fresh reviewer, then Stefan merges.
