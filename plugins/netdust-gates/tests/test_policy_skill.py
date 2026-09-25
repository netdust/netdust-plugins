"""test_policy_skill.py — pins the policy skill's shape: it invokes upstream, names each
Netdust addition once, stays a contract (<150 lines), and the pack cites, never restates."""
import re
from pathlib import Path

SKILLS = Path(__file__).resolve().parent.parent / "skills"
BANNED_GRAMMAR = ("gate-check", "tasks.md", "Lane:", "Cluster", "Stakes:", "Test-author")


def _has_all(text: str, needles: tuple[str, ...]) -> tuple[bool, list[str]]:
    missing = [n for n in needles if n not in text]
    return not missing, missing


def run() -> list[tuple[bool, str]]:
    policy = (SKILLS / "policy" / "SKILL.md").read_text()
    pack = (SKILLS / "policy" / "wordpress.md").read_text()
    edges = (SKILLS / "policy" / "edge-classes.md").read_text()
    threat = (SKILLS / "threat-modeling" / "SKILL.md").read_text()
    frontmatter = re.match(r"---\nname: policy\ndescription: .+\n---\n", policy)

    ok_up, miss_up = _has_all(policy, ("superpowers:brainstorming", "superpowers:writing-plans",
                                       "superpowers:finishing-a-development-branch",
                                       "superpowers:requesting-code-review"))
    ok_tok, miss_tok = _has_all(policy, (
        "Global Constraints", "Review Focus", "First working version", "Simplest design",
        "Source:", "Accepted-by-human:", "Ruling:", "make gate", "shakeout-check.py",
        "security-sentinel", "invariant-auditor", "wordpress.md", "edge-classes.md",
        "netdust-gates:threat-modeling", "Spec:", "make promote name=<feature>", "make review name=<feature>"))
    ok_pack, miss_pack = _has_all(pack, (
        "netdust-wp:ntdst-framework", "netdust-wp:ntdst-patterns", "netdust-wp:wp-security",
        "netdust-wp:wp-testing", "netdust-devops:devops", "make gate", "Brain Monkey",
        "wp-phpunit", "Playwright", "four pillars"))
    ok_edge, miss_edge = _has_all(edges, (
        "Empty", "Denied actor", "re-entry", "Concurrent", "Boundary", "Mid-flow", "Delivery seam"))
    ok_thr, miss_thr = _has_all(threat, ("Assets", "Attacks", "Mitigations", "Deferrals"))
    banned = [b for text in (policy, pack, edges, threat) for b in BANNED_GRAMMAR if b in text]

    return [
        (frontmatter is not None, "policy: frontmatter is `name: policy` + one-line description"),
        (len(policy.splitlines()) < 150, f"policy: under 150 lines (got {len(policy.splitlines())})"),
        (ok_up, f"policy: invokes the upstream skills (missing {miss_up})"),
        (ok_tok, f"policy: names each Netdust addition once (missing {miss_tok})"),
        (ok_pack, f"pack: cites the owning skills and runners (missing {miss_pack})"),
        (len(pack.splitlines()) <= 60 and "esc_html" not in pack and "sanitize_text_field" not in pack,
         "pack: short, and restates no wp-security function table"),
        (ok_edge, f"catalog: the edge classes are present (missing {miss_edge})"),
        (ok_thr, f"threat-modeling: the four lists are named (missing {miss_thr})"),
        (not banned, f"no 0.28 plan grammar anywhere in the skills (found {sorted(set(banned))})"),
    ]
