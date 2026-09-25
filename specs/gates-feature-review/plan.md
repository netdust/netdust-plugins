# /feature-review — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/feature-review <name | staging>` dispatches the reviewers as subagents in parallel and reports one summary back. It works with or without a plan, and the policy's Close calls it through `make review`.

**Architecture:** One command coordinates the reviewers. Feature scope uses upstream's reviewer (a `general-purpose` subagent filling `requesting-code-review/code-reviewer.md`), joined by the existing netdust agents when they apply. Staging scope uses one new read-only agent, `staging-reviewer`.

**Tech Stack:** Markdown commands and agents; Python pin tests (`tests/run.sh`).

**Spec:** specs/feature-review/spec.md (R2, R3, R4)

## Global Constraints

- It reads and reports: no edits, no fixes, no questions, because it runs headless under `claude -p`.
- It never restates superpowers' reviewer. It supplies the inputs and the joiners, nothing more.
- The policy stays under 150 lines.

## Review Focus

- A feature with no plan is reviewed from its diff and commit messages. It is never refused. (Task 1 pin, Task 2 eval)
- A diff touching a security-boundary path brings in security-sentinel even without a plan. (Task 1 pin)

**First working version:** Task 1.

**Simplest design:** one command plus one small agent. I rejected a dedicated feature-reviewer agent because it would restate upstream's `code-reviewer.md`.

---

### Task 1: `/feature-review` and `staging-reviewer`

**Files:**
- Create: `plugins/netdust-gates/commands/feature-review.md`, `plugins/netdust-gates/agents/staging-reviewer.md`
- Modify: `plugins/netdust-gates/tests/test_session_commands.py`: add `"feature-review": "staging-reviewer"` to `PAIRS` (existence, `name:`, read-only tools)

- [ ] **Step 1: Failing pin.** Add the `PAIRS` entry, then run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -3`. Expected: `test_session_commands` fails.

- [ ] **Step 2: `commands/feature-review.md`.**

````markdown
---
description: Run the reviewers on a feature, with or without a plan, or with `staging` on where the promoted features meet, and report back. make review runs it. Report only.
argument-hint: <feature | staging>
allowed_tools: ["Bash", "Read", "Glob", "Grep", "Agent"]
---

You coordinate reviewers and report. You change nothing and ask nothing: this runs headless.

**What to review.** The name is `$ARGUMENTS`, else `$REVIEW_NAME`. For a feature, the head is
`origin/feature/<name>` (else the local branch), and the base is its merge-base with the
production branch (`environments.production.branch` in `site.yml`, else `main`). For `staging`,
the head is `origin/staging`, and the features are its `promote: <name>` merges, each with its
second parent.

**Feature.** When `specs/<name>/plan.md` exists, pass its requirements, `Review Focus` and
threat model to the reviewers. Otherwise pass the diff and the commit messages: a feature
without a plan is reviewed, never refused. Dispatch in parallel:
- superpowers' reviewer: a `general-purpose` subagent filling `requesting-code-review/code-reviewer.md` for the range;
- `security-sentinel`, when the plan has a `## Threat model` or the diff touches auth, sessions,
  capabilities, nonces, input parsing, outbound fetches of user URLs, credentials or tenancy;
- `invariant-auditor`, when the project has `ARCHITECTURE-INVARIANTS.md`.

**Staging.** Dispatch `staging-reviewer` with the base, the head and the feature list.

**Report back.** Give one summary: what was reviewed (range, plan or none), then the findings
grouped Blocking / Should fix / Note, each with its file:line and which reviewer raised it.
No findings is a legitimate report.
````

- [ ] **Step 3: `agents/staging-reviewer.md`.**

````markdown
---
name: staging-reviewer
description: Reviews only where the features promoted onto staging meet — files and symbols two of them touch, anything registered twice, one changing what another relies on. Read-only. Each feature had its own review; this never repeats it. Dispatched by /feature-review staging.
model: inherit
tools: Read, Grep, Glob, Bash
---

You get the production base, the staging head and the features as `name:pin`. Ask only: **what
can go wrong between them?**

1. Per feature, list the files it changed: `git diff --name-only $(git merge-base <base> <pin>) <pin>`.
2. The overlap is every file two or more features touch. With none, say "no overlaps" and stop.
3. In each overlapping file, compare the features' hunks with staging's merged version. Look for
   the same hook, route, option, post type, shortcode or migration registered twice; one feature
   changing a signature or data another relies on; and edits that merged cleanly but contradict
   each other.

Report one line per overlap: features → file:line → what collides → Blocking | Should fix | Note.
````

- [ ] **Step 4: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1`. Expected: `All harness tests passed.`

- [ ] **Step 5: One live run.** In a scratch repo with `main` plus a `feature/banner` commit and no `specs/`, run `claude -p "/netdust-gates:feature-review banner" --plugin-dir <this repo>/plugins/netdust-gates`. Expected: a summary naming the range and "no plan".

- [ ] **Step 6: Commit.** `git add plugins/netdust-gates && git commit -m "feat(gates): /feature-review runs the reviewers and reports back"`

### Task 2: Close calls it

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md`, Close step 3
- Modify: `plugins/netdust-gates/tests/test_policy_skill.py`: add the token `"make review name=<feature>"`
- Modify: `plugins/netdust-gates/evals/cases.json`: add the case `close-calls-make-review`
- Modify: version 0.8.0 in `.claude-plugin/marketplace.json` and `plugins/netdust-gates/.claude-plugin/plugin.json`

- [ ] **Step 1: Failing pin and eval.** Add the token to `ok_tok`. Add this case:

```json
{
  "id": "close-calls-make-review",
  "prompt": "feature/banner is done: make gate is green and it has no user-facing flow. It was started by hand — there is no plan. Close it as the policy says. Do not ask questions.",
  "files": {"site.yml": "structure:\n  type: bedrock\nenvironments:\n  staging: {branch: staging, url: https://stg.example.test}\n  production: {branch: main, url: https://example.test}\ncommands:\n  gate: composer gate\n  review: claude -p \"/netdust-gates:feature-review\"\n"},
  "expect": [{"where": "reply", "match": "make review name=banner"}, {"where": "reply", "match": "make promote name=banner"}],
  "absent": []
}
```

- [ ] **Step 2: Policy.** Close step 3's opening becomes:

```markdown
3. The feature review, plan or no plan:
   `make review name=<feature>` (`/feature-review <feature>` without devops) — superpowers'
   whole-branch review (`superpowers:requesting-code-review`, a fresh reviewer; the author never
   reviews its own diff), joined by `security-sentinel` when the plan carries a `## Threat model`
   or the diff touches a security-boundary path, and `invariant-auditor` when the project carries
   `ARCHITECTURE-INVARIANTS.md`.
```

Version 0.8.0, with the description starting "0.8.0: /feature-review runs the reviewers on a feature (plan or none) or on where staging's features meet, and reports back; Close step 3 is make review name=<feature>. Eval case close-calls-make-review. ".

- [ ] **Step 3: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1` and `python3 plugins/netdust-gates/evals/run-evals.py close-calls-make-review close-hands-over-promote`. Expected: all pass.

- [ ] **Step 4: Commit.** `git add .claude-plugin/marketplace.json plugins/netdust-gates && git commit -m "feat(gates): Close runs make review (0.8.0)"`
