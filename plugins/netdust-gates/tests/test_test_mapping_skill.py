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
