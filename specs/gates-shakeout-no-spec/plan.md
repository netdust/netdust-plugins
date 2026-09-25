# /shakeout without a spec — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/shakeout <name>` on a branch with no spec proposes a flow list from the diff and the running app, stops for Stefan's approval, then drives, commits and registers those flows as usual.

**Architecture:** The command gains a step for the no-spec path. It writes `specs/<name>/flows.md`, a proposed list, and stops. `shakeout-qa` takes its flows from the spec and plan when they exist, and otherwise from the approved `flows.md` and nothing else. Nothing downstream changes: `shakeout-check.py` already needs only `specs/<name>/shakeout.md`.

**Tech Stack:** Markdown command and agent; Python pin tests (`tests/run.sh`).

**Spec:** specs/feature-review/spec.md (R5)

## Global Constraints

- With no spec, nothing records the feature's intent except Stefan. No test is written from an unapproved flow list: tests of current behaviour would guard its bugs.
- The flow list comes from what the branch changed (`git diff` over production and the commit messages), then exploration of those surfaces on the running dev site. The whole site is never explored.
- It stays separate from `/feature-review`: shakeout drives the app and writes tests, review reads code and reports.
- The policy stays under 150 lines.

## Review Focus

- A branch whose diff touches no user-facing surface: the command says so and ends. It never invents flows. (Task 1 pin)
- Stefan strikes a flow: that flow gets no test and no row. (Task 1: the agent's "nothing else")

**First working version:** Task 1.

**Simplest design:** one step in the existing command plus one sentence in the agent. I rejected a separate `/flows` command because it would split one job across two entry points.

---

### Task 1: the no-spec path

**Files:**
- Modify: `plugins/netdust-gates/commands/shakeout.md`, adding a step between Step 1 and Step 2
- Modify: `plugins/netdust-gates/agents/shakeout-qa.md`, section "Which flows"
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md`, the Stops paragraph
- Modify: `plugins/netdust-gates/tests/test_close_wiring.py`, one pin
- Modify: version 0.8.1 in `.claude-plugin/marketplace.json` and `plugins/netdust-gates/.claude-plugin/plugin.json` (0.8.1 if `/feature-review`'s 0.8.0 lands first, otherwise 0.8.0; decide at merge)

- [ ] **Step 1: Failing pin.** In `test_close_wiring.py`, before the `not stale` line:

```python
        ("flows.md" in command and "no spec" in command and "flows.md" in qa
         and "flow list" in policy,
         "/shakeout on a branch with no spec proposes flows.md and stops; shakeout-qa drives only the approved list"),
```

Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -3`. Expected: `test_close_wiring` fails.

- [ ] **Step 2: `commands/shakeout.md`.** Insert after Step 1 (`make gate`):

```markdown
## Step 1b — No spec: propose the flows, then stop

When `specs/<feature>/spec.md` does not exist, nothing records what this feature should do
except Stefan. Derive a proposal:

1. What changed: `git diff --name-only $(git merge-base origin/<production> HEAD)..HEAD` and
   `git log --format=%s` over the same range — the routes, templates, forms, REST endpoints,
   admin screens and shortcodes the branch touched. None user-facing: say so and go to Step 4.
2. Explore only those surfaces on the running dev site (`superpowers-chrome:browsing`, or the
   Playwright planner against those URLs).
3. Write `specs/<feature>/flows.md`: one line per flow — surface, what a person does, what they
   should see — with its edges from `edge-classes.md`.

**Stop.** Show Stefan the list. He confirms, strikes or adds; the file is edited to what he
approved. Only then Step 2, with `flows.md` as the flow source.
```

- [ ] **Step 3: `agents/shakeout-qa.md`.** Append to "Which flows":

```markdown
With no spec, the flows are the ones in `specs/<feature>/flows.md` that Stefan approved,
and nothing else — a struck flow gets no test and no row.
```

- [ ] **Step 4: Policy Stops.** In the Stops paragraph, after "the shake-out screenshot yield (Close, step 2);", add "the flow list a shake-out proposes for a branch with no spec;".

- [ ] **Step 5: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1`. Expected: `All harness tests passed.`

- [ ] **Step 6: Commit.** `git add .claude-plugin/marketplace.json plugins/netdust-gates && git commit -m "feat(gates): /shakeout on a branch with no spec proposes the flows and stops"`
