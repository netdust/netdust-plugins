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
                                    "screenshot", "netdust-gates:policy", "superpowers:requesting-code-review")),
         "/shakeout runs make gate, the qa agent, the checker, the screenshot yield and points at the policy close"),
        (all(s in reviewer for s in ("The cut", "too broad", "artificially split")) and "/plan-review <topic>" in policy
         and "Spec:\\**" in plan_cmd and "in place of its menu" in policy and "Scope Check" in policy,
         "a spec cut into several plans is reviewed as one set, and the reviewer judges the cut"),
        ("make ship" in command and "`ship` waits for it" in policy,
         "the feature shake-out writes the checks; staging's e2e run is the gate ship waits for"),
        ("flows.md" in command and "no spec" in command and "flows.md" in qa
         and "flow list" in policy,
         "/shakeout on a branch with no spec proposes flows.md and stops; shakeout-qa drives only the approved list"),
        (not stale, f"none of the 0.28 machinery survives in the close (found {stale})"),
    ]
