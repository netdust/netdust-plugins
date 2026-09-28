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
        ("Test map" in (AGENTS / "shakeout-qa.md").read_text() and "No plan table lists them" not in (AGENTS / "shakeout-qa.md").read_text(),
         "shakeout-qa reads the Test map's flows and no longer derives them"),
        ("Test map" in (AGENTS / "plan-reviewer.md").read_text() and "What a test owes" in (AGENTS / "plan-reviewer.md").read_text(),
         "plan-reviewer checks rows and cites the bar"),
        ("Test map" in (PLUGIN / "skills" / "threat-modeling" / "SKILL.md").read_text(), "threat-modeling points mitigations at rows"),
        ("What a test owes" in (AGENTS / "test-pruner.md").read_text() and "all six" not in (AGENTS / "test-pruner.md").read_text(),
         "test-pruner cites the bar instead of carrying it"),
        ("netdust-gates:test-mapping" in (PLUGIN.parent / "netdust-wp" / "skills" / "wp-testing" / "SKILL.md").read_text(),
         "wp-testing points tier choice at the Test map"),
    ]
