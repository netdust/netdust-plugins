"""test_close_wiring.py — the close (agents + /shakeout) speaks the checker's grammar and
carries none of the 0.28 machinery it replaces."""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
AGENTS = ("security-sentinel", "invariant-auditor", "shakeout-qa", "plan-reviewer")
STALE = ("gate-check", "tasks.md", "Lane", "verify-budget", "model-ladder", "herdr-moments",
         "implementer", "Stage 3", "Acceptance flows", "Shake-out access", "FULL tier", "FULL-tier")


def _read(rel: str) -> str:
    return (PLUGIN / rel).read_text()


def _in_order(text: str, *needles: str) -> bool:
    positions = [text.find(n) for n in needles]
    return all(p >= 0 for p in positions) and positions == sorted(positions)


def _frontmatter_ok(text: str, name: str) -> bool:
    m = re.match(r"---\n(?P<fm>.*?)\n---\n", text, re.S)
    return bool(m) and f"name: {name}" in m.group("fm") and "description:" in m.group("fm")


def run() -> list[tuple[bool, str]]:
    agents = {a: _read(f"agents/{a}.md") for a in AGENTS}
    command = _read("commands/shakeout.md")
    plan_cmd = _read("commands/plan-review.md")
    policy = _read("skills/policy/SKILL.md")
    reviewer = agents["plan-reviewer"]
    stale = sorted({s for t in (*agents.values(), command, plan_cmd) for s in STALE if s in t})
    qa = agents["shakeout-qa"]
    return [
        (all(_frontmatter_ok(agents[a], a) for a in AGENTS), "each agent has `name:` matching its file and a description"),
        (all(s in plan_cmd for s in ("git hash-object", "plan-reviewer", "Reviewed-plan:", "plan-review.md"))
         and "Blocking" in plan_cmd,
         "/plan-review computes the blob, dispatches plan-reviewer, files the report with Reviewed-plan:"),
        (all(s in reviewer for s in ("Reviewed-plan:", "Blocking", "Should fix", "Premises checked"))
         and "tools: Read, Grep, Glob, Bash" in reviewer,
         "plan-reviewer writes the report grammar the guard reads, and ships without Edit/Write"),
        (all(s in policy for s in ("/plan-review", "plan-review.md", "Reviewed-plan:")),
         "the policy skill names /plan-review, its artifact and its token"),
        (all(s in qa for s in ("Accepted-by-human:", "shakeout-check.py", "Browser:", "shakeout/<name>.png", "edge-classes.md"))
         and "Ruling:" not in qa,
         "shakeout-qa writes the checker's grammar and never `Ruling:`"),
        (all(s in qa for s in ("@e2e", "@smoke", "specs/CHECKS.md", "tests/e2e/smoke/", "no login", "Never production")),
         "shakeout-qa registers the driven flows as @e2e and leaves a read-only @smoke check"),
        (all(s in command for s in ("specs/CHECKS.md", "make e2e", "make smoke"))
         and all(s in policy for s in ("specs/CHECKS.md", "make e2e", "make smoke")),
         "/shakeout reads the registry first, and the policy close names both verbs"),
        (all(s in command for s in ("bin/shakeout-check.py", "make gate", "Accepted-by-human:", "shakeout-qa",
                                    "screenshot", "netdust-gates:policy", "came before")),
         "/shakeout runs make gate, the qa agent, the checker, and points at the policy close"),
        (all(s in qa for s in ("specs/<feature>/shakeout/*.revert.txt", "revert-run", "Test: <path> :: <title>", "first in Evidence",
                               "~/.claude/plugins/netdust-gates/bin/revert-run <feature> <test-path> <title> -- <command running that one test>",
                               "specs/<feature>/shakeout/<name>.png", "never the scratchpad", "built assets",
                               "the policy's fix round, then its stop", "re-driven", "git show", "one `shakeout.md`",
                               "at the feature's end"))
         and "until the checker exits 0" not in qa
         and all(s in command for s in ("make shakeout name=<feature>", "steps 5-9"))
         and not any(s in command for s in ("until it exits 0", "Step 4", "screenshot yield", "back to Step 3")),
         "the shake-out proves each new test on the base (revert-run, the Test: marker, the derived log), captures to the repo, "
         "runs the policy's one fix round, and leaves the yield to the Close"),
        (all(s in reviewer for s in ("The cut", "too broad", "artificially split")) and "/plan-review <topic>" in policy
         and "Spec:\\**" in plan_cmd and "in place of its menu" in policy and "Scope Check" in policy,
         "a spec cut into several plans is reviewed as one set, and the reviewer judges the cut"),
        ("make ship" in command and "`ship` waits for it" in policy,
         "the feature shake-out writes the checks; staging's e2e run is the gate ship waits for"),
        (all(t in _read("commands/feature-review.md") for t in (
            "printenv REVIEW_NAME", "most capable", "ntdst-drift-reviewer", "Pass each reviewer the diff",
            "environments.staging.branch", "REVIEW_LEVEL", "ultra", "Findings: <b> Blocking")),
         "/feature-review reads make's env, hands reviewers the diff, keeps the model and the WP join"),
        (all(t in _read("commands/feature-review.md") for t in (
            "git worktree add --detach", "git worktree remove", "**Spec:**")),
         "/feature-review's reviewers read a detached checkout of the head — code, plan and spec — not this checkout (two-session R7)"),
        ("flows.md" in command and "no spec" in command and "flows.md" in qa
         and "flow list" in policy and "no `plan.md`" in command and "**Stop.**" in command
         and "new flows" in qa and "Write" in command.split("---")[1] and "or `flows.md`" in command,
         "/shakeout on a branch with no spec proposes flows.md and stops; shakeout-qa drives only the approved list"),
        (all(s in qa for s in ("never hunts again", "dev site only", "first-time visitor", "goes RED on its assertion",
                               "never a timeout", "not ours:", "never blocks this close", "rejected:",
                               "Hunt: <n> charters", "the one addition", "Re-seed", "Hunt: 0 charters — <why>",
                               "keeps the record", "in doubt, it is ours", "git diff --name-only", "actions it spent"))
         and "hunt" in qa.split("**Sweep.**")[1].split("**Drive.**")[0]
         and "hunt" in qa.split("Done when:")[1]
         and all(s in command for s in ("hunt", "not ours:", "✗ [shakeout-hunt]"))
         and not any(s in t for s in ("e2e.config.ts", "npx e2e", ".e2e/") for t in (qa, command))
         and all(s in _read("CLAUDE.md") for s in ("on trial", "^Hunt: [1-9]", "0 confirmed · 0 not ours")),
         "every browser shake-out hunts once on the dev site with no tool of its own, or says why not; a bug is a failed assertion; not-ours only when the diff provably misses the surface; the hunt is on trial"),
        ((PLUGIN / "commands" / "review-fix.md").is_file()
         and all(t in _read("commands/review-fix.md") for t in (
            "git-common-dir", "Close's fix pass", "make promote name=", "which findings", "never stash",
            "specs/$ARGUMENTS/review.md"))
         and "/review-fix" in policy,
         "/review-fix: the saved report, Stefan picks, the policy's fix pass, the record in specs/, re-promote"),
        (_in_order(policy, "make review name=<feature>", "runs `/shakeout`", "`make shakeout name=<feature>`",
                   "`make report name=<feature>`", "7. `make gate`", "\n9. Every change:")
         and "(Close, step 8)" in policy and "every Blocking and Should fix finding" in policy
         and "else `specs/$ARGUMENTS/review.md`" in _read("commands/review-fix.md"),
         "Close orders by cost: gate, review, fix pass, the shakeout and its check, the report, the last gate on the report's "
         "commit (the stamp promote needs), the yield, the finish"),
        (all(s in policy.split("8. ")[1].split("9. ")[0] for s in ("overrule", "the hunt's tally", "Accepted-by-human:", "report.md"))
         and "Slice" in policy and "## Slice" not in policy and "the report yield" in policy
         and all(s in _read(f) for f, _ in (("commands/feature-review.md", 0), ("agents/security-sentinel.md", 0),
                                              ("agents/invariant-auditor.md", 0)) for s in ("studio-checks", "revert"))
         and "INV-2" in _read("skills/policy/wordpress.md")
         and all(s in _read("CLAUDE.md") for s in ("revert-passed:", "Slice M"))
         and "layer" in reviewer
         and "/plan-review` again" not in plan_cmd and "cap" in plan_cmd,
         "the yield lives in the policy's step 8; slices in the plan rule; the reviewers check tests exist and leave quality to "
         "studio-checks; the pack carries INV-2; CLAUDE.md the revert trial and the slice label; the plan reviewer flags a layer; "
         "/plan-review defers to the cap"),
        (all(s in policy.split("\n3. ")[1].split("\n4. ")[0] for s in ("copied from `make review`'s saved report", "specs/<feature>/review.md"))
         and all(s in policy.split("\n6. ")[1].split("\n7. ")[0] for s in ("report.md", "specs/CHECKS.md"))
         and all(s in qa for s in ("Hunt: deferred — runs at the feature's end", "regex-escaped", "revert-run's own output",
                                   ".git/revert-run.swapped", "`recover:`"))
         and "Hunt: deferred" in command
         and all(s in _read("CLAUDE.md") for s in ("<date> · <feature> · revert-passed:", "| sort | tail -5"))
         and "than the review it protects" not in _read("CLAUDE.md"),
         "the fix pass's wording (review S7, N2): review.md copied from make review's saved report, report.md committed with "
         "specs/CHECKS.md, an intermediate slice's deferred hunt, --grep regex-escaped, the log is revert-run's own output, the "
         "sentinel's recover line; CLAUDE.md's trial line is dated and the removal grep sorts by it, the cost comparison gone"),
        (not stale, f"none of the 0.28 machinery survives in the close (found {stale})"),
    ]
