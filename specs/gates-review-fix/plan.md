# review levels and /review-fix — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/feature-review` honours `REVIEW_LEVEL` and ends its report with a `Findings:` line. `/review-fix X` turns a saved review into follow-up commits on `feature/X`, the way a PR's review comments become commits. The Close orders by cost: gate → review → fix → shakeout.

**Architecture:** Text changes to the existing command, plus one new interactive command that reuses the policy's fix-pass rule. It has no agent of its own.

**Tech Stack:** Markdown commands; Python pin tests.

**Spec:** specs/feature-review/spec.md (R6, R7, R8, R9, R10)

## Global Constraints

- The report's last line is exactly `Findings: <b> Blocking · <s> Should fix · <n> Note`, because `make` prints it.
- `/review-fix` changes nothing Stefan did not pick. A finding that is a decision comes back as a question, never as a guess.
- The fix pass is the policy's Close step 4 (each fix RED→GREEN through the seam, no re-review). `/review-fix` points at it and does not restate it.
- The policy stays under 150 lines.

## Review Focus

- No saved report for X: say so, name `make review name=X`, change nothing. (Task 2 eval `review-fix-no-report`)
- A dirty checkout: stop before switching branches, never stash. (Task 2 prose pin only)

**First working version:** Task 1.

**Simplest design:** reuse the fix pass the policy already defines. I rejected a fixer agent because a reviewer that edits "becomes the fixer before Stefan approves anything" (tests/test_session_commands.py docstring).

---

### Task 1: levels and the Findings line in `/feature-review`

**Files:** Modify `plugins/netdust-gates/commands/feature-review.md` and `plugins/netdust-gates/tests/test_close_wiring.py`.

- [ ] **Step 1: Failing pin.** Add `"REVIEW_LEVEL"`, `"ultra"` and `"Findings: <b> Blocking"` to the tuple of the `/feature-review` pin in `test_close_wiring.py`. Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -2`. Expected: `test_close_wiring` fails.
- [ ] **Step 2: Text.** After "**What to review.**", add:

```markdown
**How much.** `$REVIEW_LEVEL` (`printenv REVIEW_LEVEL`), default `full`: `low` dispatches
superpowers' reviewer only; `full` adds the joiners below that apply; `ultra` adds, for a
feature, `staging-reviewer` on staging's promoted features with this feature added at its head, so
what it would collide with shows before it lands: base production, head
`origin/<staging branch>`, the features staging's `promote:` merges plus
`<name>:origin/feature/<name>` (replacing its old pin if it is already on staging). For the new
feature's files there is no merged version yet, so the reviewer compares the pins' diffs.
```

At the end of "**Report back**", add: "End with one plain line — no backticks, no bold: Findings: <b> Blocking · <s> Should fix · <n> Note"

- [ ] **Step 3: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1`. Expected: `All harness tests passed.` Then commit: `git commit -am "feat(gates): /feature-review levels and a Findings line"`.

### Task 2: `/review-fix`

**Files:**
- Create: `plugins/netdust-gates/commands/review-fix.md`
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md`, the "On demand" paragraph: add "`/review-fix <feature>` turns a saved review into follow-up commits on the branch — it changes only what Stefan picks", and make the closing sentence say the other three report
- Modify: `plugins/netdust-gates/evals/cases.json`: case `review-fix-no-report`
- Modify: `plugins/netdust-gates/tests/test_close_wiring.py`, one pin
- Modify: version 0.9.0 in `.claude-plugin/marketplace.json` and `plugins/netdust-gates/.claude-plugin/plugin.json`

- [ ] **Step 1: Failing pin.**

```python
        (all(t in _read("commands/review-fix.md") for t in (
            "git-common-dir", "Close step 4", "make promote name=", "which findings", "never stash"))
         and "/review-fix" in policy,
         "/review-fix: the saved report, Stefan picks, the policy's fix pass, re-promote"),
```

And the eval case:

```json
{"id": "review-fix-no-report", "prompt": "/netdust-gates:review-fix banner", "files": {"banner.php": "<?php echo 'hi';\n"},
 "expect": [{"where": "reply", "match": "make review name=banner"}, {"where": "banner.php", "match": "^<\\?php echo 'hi';\\n?$"}], "absent": []}
```

Run the suite. Expected: `test_close_wiring` fails (a missing file).

- [ ] **Step 2: `commands/review-fix.md`.**

````markdown
---
description: Follow up a review, like commits on a PR — show the saved findings for a feature, Stefan picks which to act on, one fix pass on feature/<name>, push, then re-promote.
argument-hint: <feature>
allowed_tools: ["Bash", "Read", "Glob", "Grep", "Edit", "Write", "Skill", "AskUserQuestion"]
---

1. **The review.** Read `$(git rev-parse --git-common-dir)/reviews/$ARGUMENTS.md`. None: say
   so, name `make review name=$ARGUMENTS` (`/feature-review $ARGUMENTS` on a project without
   devops, whose summary is then the review), change nothing, stop.
2. **The branch.** Work where `feature/$ARGUMENTS` is checked out: in another worktree, go
   there; a dirty checkout, stop and say what is dirty — never stash. Otherwise
   `git checkout feature/$ARGUMENTS && git pull --ff-only`.
3. **Stefan picks.** Show the findings, Blocking first, and ask which findings to act on. A
   finding that is a decision (which source, which behaviour) is a question to him, not a fix.
4. **The fix pass** is the `netdust-gates:policy` Close step 4, on the picked findings only.
   Copy the report to `specs/$ARGUMENTS/review.md` and commit it with the fixes.
5. **Push and hand back.** `git push`, then tell Stefan: `make promote name=$ARGUMENTS` puts
   the fixed tip on staging; it finds the saved review and skips it — no re-review of a fix pass
   (`review=low` if he wants the fixes looked at).
````

- [ ] **Step 3: Policy line, version 0.9.0.** The description starts "0.9.0: /feature-review honours REVIEW_LEVEL (low · full · ultra, which checks collisions with staging before landing) and ends with a Findings line; /review-fix <feature> turns a saved review into follow-up commits on the branch, the way a PR's review comments become commits. "
- [ ] **Step 4: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1` (expected: `All harness tests passed.`) and `python3 plugins/netdust-gates/evals/run-evals.py review-fix-no-report` (expected: 1/1). Commit: `git add .claude-plugin/marketplace.json plugins/netdust-gates && git commit -m "feat(gates): /review-fix — follow-up commits on the branch (0.9.0)"`.

### Task 3: Close orders by cost: gate → review → fix → shakeout (R9)

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md`, the Close list and the Stops reference "(Close, step 2)"
- Modify: `plugins/netdust-gates/commands/shakeout.md`, the frontmatter description and Step 4 (it no longer starts the review; the review came first)
- Modify: `plugins/netdust-gates/tests/test_close_wiring.py`: the `/shakeout` pin's `"superpowers:requesting-code-review"` becomes `"came before"`, and one order pin
- Modify: `plugins/netdust-gates/evals/cases.json`: `close-calls-make-review` gets an order expectation

- [ ] **Step 1: Failing pins.** Add before the `not stale` line:

```python
        (policy.index("make review name=<feature>") < policy.index("runs `/shakeout`")
         and "(Close, step 4)" in policy,
         "Close orders by cost: gate, review, fix pass, then the shakeout once on settled code"),
```

In the `/shakeout` pin tuple, replace `"superpowers:requesting-code-review"` with `"came before"`. In `cases.json`, add to `close-calls-make-review`'s `expect`: `{"where": "reply", "match": "(?s)make review name=banner.*make promote name=banner"}`. Run the suite. Expected: `test_close_wiring` fails.

- [ ] **Step 2: The Close list.** Reorder the four steps to gate (1), feature review (2, the current step 3's text unchanged), fix pass (3, the current step 4's first two sentences, ending "No re-review — named checks and the suites close it."), and shake-out (4, the current step 2's text, with "once, on the fixed code" after "`/shakeout`"). The closing sentence, starting "Then `superpowers:finishing-a-development-branch`", follows step 4 and reads:

```markdown
   Then `superpowers:finishing-a-development-branch` — on a project with `site.yml`, in place of
   its menu: the branch pushed and `make promote name=<feature>` handed to Stefan (it finds the
   saved review and skips it); a feature never merges into production by hand.
```

In Stops, change "(Close, step 2)" to "(Close, step 4)".

- [ ] **Step 3: `/shakeout`.** Change the description's last sentence to "The review and its fix pass came before it (netdust-gates:policy Close)." Rename Step 4 to "## Step 4 — The screenshot yield", and replace its final paragraph ("Then the whole-branch review…") with:

```markdown
The review and its fix pass came before this shake-out (the `netdust-gates:policy` Close); what
remains is `superpowers:finishing-a-development-branch`. Report the manifest and every `Ruling:`
from the ledger together.
```

- [ ] **Step 4: GREEN.** Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -1` (expected: `All harness tests passed.`, policy under 150 lines), then `python3 plugins/netdust-gates/evals/run-evals.py close-calls-make-review close-hands-over-promote` (expected: 2/2). Commit: `git commit -am "feat(gates): Close orders by cost — gate, review, fix, shakeout"`.

### Task 4: every artifact in one obvious place (R10)

**Files:**
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md`, replacing the "Where artifacts live" paragraph with the table below
- Modify: `plugins/netdust-gates/skills/policy/SKILL.md` Close step 3 (the fix pass): add "copy the saved review to `specs/<feature>/review.md` and commit it with the fixes"
- Create: `plugins/netdust-gates/tests/test_artifact_layout.py`

- [ ] **Step 1: Failing test.** `tests/test_artifact_layout.py`:

```python
"""test_artifact_layout.py — every specs/ path a command or agent names is in the policy's
"Where artifacts live" table, so no artifact grows a second home (R10)."""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
ALLOWED = re.compile(
    r"^specs/(CHECKS\.md"
    r"|<(?:feature|topic|name)>/(?:spec|plan|plan-review|review|flows|shakeout|session-review)\.md"
    r"|<(?:feature|name)>/shakeout/[^`\s]*"
    r"|<(?:feature|topic|name)>/?)$")
PATH = re.compile(r"specs/[A-Za-z0-9_<>$./*-]+")


def _norm(p: str) -> str:
    p = p.rstrip(".,)")
    return re.sub(r"\$ARGUMENTS|<[a-z-]+>|\*", lambda m: "<feature>" if m.group(0) != "*" else "x", p)


def run() -> list[tuple[bool, str]]:
    texts = {f.relative_to(PLUGIN): f.read_text() for d in ("commands", "agents", "skills")
             for f in (PLUGIN / d).rglob("*.md")}
    stray = sorted({f"{f}: {p}" for f, t in texts.items() for p in PATH.findall(t)
                    if not ALLOWED.match(_norm(p))})
    policy = (PLUGIN / "skills" / "policy" / "SKILL.md").read_text()
    return [
        ("| `review.md` |" in policy and "| `CHECKS.md` |" in policy,
         "the policy lists every artifact in one table"),
        (not stray, f"every specs/ path a command, agent or skill names is in the table (stray: {stray[:6]})"),
    ]
```

Run `bash plugins/netdust-gates/tests/run.sh 2>&1 | tail -3`. Expected: it fails on the missing table (and lists any stray path; each stray is either added to the table because it is real, or moved into `specs/<feature>/`; ledger each as a ruling).

- [ ] **Step 2: The table.** Replace the "Where artifacts live" paragraph's first sentence with:

```markdown
Everything about a feature lives in `specs/<feature>/`; `<feature>` is its branch name.

| File | Holds | Written by |
|---|---|---|
| `spec.md` | the requirements, each with its `Source:` | brainstorming |
| `plan.md` | the plan, its `**Spec:**` header naming the spec | writing-plans |
| `plan-review.md` | the plan review, `Reviewed-plan:` per plan | `/plan-review` |
| `review.md` | the feature review, committed with its fix pass | `make review` / `/review-fix` |
| `flows.md` | the approved flow list of a branch with no spec | `/shakeout` |
| `shakeout.md`, `shakeout/*.png` | the shake-out manifest and screenshots | `/shakeout` |
| `session-review.md` | the on-demand session audit | `/session-review` |
| `CHECKS.md` | (in `specs/` itself) every surface's `@e2e` and `@smoke` checks | `/shakeout` |

A split spec stays at `specs/<topic>/spec.md` with no plan beside it. Nothing else goes elsewhere;
superpowers' ledger (`.superpowers/sdd/`) is its own scratch, deleted at finish.
```

(Keep the existing sentence naming the `docs/superpowers/...` override, and the "The plan is the feature" paragraph.)

- [ ] **Step 3: GREEN.** Run the suite (expected: `All harness tests passed.`, policy under 150 lines; if the table pushes it over, move the table to `skills/policy/artifacts.md` beside the skill and link it — ledger the ruling). Commit: `git commit -am "feat(gates): every artifact in one obvious place — the table and its test"`.
