"""test_close_wiring.py — the close (agents + /shakeout) speaks the checker's grammar and
carries none of the 0.28 machinery it replaces."""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
AGENTS = ("security-sentinel", "invariant-auditor", "shakeout-qa")
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
    stale = sorted({s for t in (*agents.values(), command) for s in STALE if s in t})
    qa = agents["shakeout-qa"]
    return [
        (all(_frontmatter_ok(agents[a], a) for a in AGENTS), "each agent has `name:` matching its file and a description"),
        (all(s in qa for s in ("Accepted-by-human:", "shakeout-check.py", "Browser:", "shakeout/<name>.png", "edge-classes.md"))
         and "Ruling:" not in qa,
         "shakeout-qa writes the checker's grammar and never `Ruling:`"),
        (all(s in command for s in ("bin/shakeout-check.py", "make gate", "Accepted-by-human:", "shakeout-qa",
                                    "screenshot", "netdust-gates:policy")),
         "/shakeout runs make gate, the qa agent, the checker, the screenshot yield and points at the policy close"),
        (not stale, f"none of the 0.28 machinery survives in the close (found {stale})"),
    ]
