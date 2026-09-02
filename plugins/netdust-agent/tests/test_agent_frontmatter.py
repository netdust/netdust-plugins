"""
test_agent_frontmatter.py — every agent persona declares its default model, and the
ladder has exactly one home (harness-inversion FR-10 / FR-11, AC-4, SC-4).
"""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
AGENTS = sorted((PLUGIN / "agents").glob("*.md"))
LADDER = PLUGIN / "skills" / "_shared" / "model-ladder.md"
ALLOWED = {"haiku", "sonnet", "opus", "inherit"}
# the table's first data row — the string SC-4 greps for outside the ladder's home
FIRST_ROW = "| ground-truth read"


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text()
    if not text.startswith("---\n"):
        return {}
    body = text[4:].split("\n---", 1)[0]
    out = {}
    for ln in body.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", ln)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def run() -> list[tuple[bool, str]]:
    results = []
    fms = {p.stem: frontmatter(p) for p in AGENTS}

    results.append((len(fms) >= 7, f"{len(fms)} agent files found under agents/"))

    missing = [n for n, fm in fms.items() if "model" not in fm]
    results.append((not missing, "every agent declares a `model:` in its frontmatter"
                    + (f" — missing: {missing}" if missing else "")))

    bad = [f"{n}={fm.get('model')}" for n, fm in fms.items() if fm.get("model") not in ALLOWED]
    results.append((not bad, "every declared model is one of haiku/sonnet/opus/inherit"
                    + (f" — bad: {bad}" if bad else "")))

    # denial path: the parser itself must not accept a model outside the allowed set
    results.append((frontmatter(Path(__file__)) == {},
                    "a file with no frontmatter parses to an empty mapping (never a false model)"))

    ladder = LADDER.read_text() if LADDER.exists() else ""
    results.append((bool(ladder), "skills/_shared/model-ladder.md exists"))
    unrouted = [n for n in fms if f"`{n}`" not in ladder]
    results.append((not unrouted, "the ladder routes every agent by name"
                    + (f" — unrouted: {unrouted}" if unrouted else "")))
    results.append((FIRST_ROW in ladder, "the ladder carries its first table row"))

    # SC-4: no restatement of the table anywhere else under skills/**, agents/**, commands/**
    homes = [p for d in ("skills", "agents", "commands")
             for p in (PLUGIN / d).rglob("*.md")
             if FIRST_ROW in p.read_text() and p != LADDER]
    results.append((not homes, "the ladder table is stated in exactly one file"
                    + (f" — also in: {[str(p.relative_to(PLUGIN)) for p in homes]}" if homes else "")))
    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
