"""test_artifact_layout.py — every specs/ path a command, agent or skill names is in the policy's
"Where artifacts live" table, so no artifact grows a second home (R10)."""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
ALLOWED = re.compile(
    r"^specs/(CHECKS\.md|test-prune/<date>\.md"
    r"|<feature>/(?:spec|plan|plan-review|review|flows|shakeout|session-review)\.md"
    r"|<feature>/shakeout/[^`\s]*"
    r"|<feature>/?)$")
PATH = re.compile(r"specs/[A-Za-z0-9_<>$./*\\-]+")


def _norm(p: str) -> str:
    p = p.replace("\\", "").rstrip(".,)")
    p = re.sub(r"<YYYY-MM-DD>", "<date>", p)
    return re.sub(r"\$ARGUMENTS|<[a-z-]+>(?<!<date>)|\*", lambda m: m.group(0) if m.group(0) == "<date>" else "<feature>", p)


def run() -> list[tuple[bool, str]]:
    texts = {f.relative_to(PLUGIN): f.read_text() for d in ("commands", "agents", "skills")
             for f in (PLUGIN / d).rglob("*.md")}
    stray = sorted({f"{f}: {p}" for f, t in texts.items() for p in PATH.findall(t)
                    if not ALLOWED.match(_norm(p))})
    policy = (PLUGIN / "skills" / "policy" / "SKILL.md").read_text()
    return [
        ("| `review.md` |" in policy and "| `CHECKS.md` |" in policy,
         "the policy lists every artifact in one table"),
        (not stray, f"every specs/ path a command, agent or skill names is in the table (stray: {stray[:8]})"),
    ]


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
