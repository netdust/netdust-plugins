"""test_session_commands.py — /session-review and /session-learn are wired, and their reviewers
cannot write.

Only what breaks a dispatch or the approval rule is pinned: an agent's `name:` matching its
file (the command dispatches by name), its tools carrying no Edit/Write (a finder that can
edit becomes the fixer before Stefan approves anything), and every agent and file a command
names existing. The prose itself is not string-tested.
"""
import re
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent.parent
PAIRS = {"session-review": "session-reviewer", "session-learn": "session-learner"}
WRITE_TOOLS = ("Edit", "Write", "NotebookEdit")


def _frontmatter(text: str) -> dict:
    m = re.match(r"---\n(?P<fm>.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group("fm").splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def run() -> list[tuple[bool, str]]:
    r: list[tuple[bool, str]] = []
    agents = {p.stem for p in (PLUGIN / "agents").glob("*.md")}
    for command, agent in PAIRS.items():
        cmd_path = PLUGIN / "commands" / f"{command}.md"
        agent_path = PLUGIN / "agents" / f"{agent}.md"
        r.append((cmd_path.is_file() and agent_path.is_file(),
                  f"/{command} and its agent {agent} both exist"))
        if not (cmd_path.is_file() and agent_path.is_file()):
            continue
        cmd, body = cmd_path.read_text(), agent_path.read_text()
        fm = _frontmatter(body)
        r.append((fm.get("name") == agent and bool(fm.get("description")),
                  f"{agent}: `name:` matches the file and it has a description"))
        tools = [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]
        r.append((bool(tools) and not any(t in WRITE_TOOLS for t in tools),
                  f"{agent} is read-only (tools {tools})"))
        named = set(re.findall(r"`([a-z]+(?:-[a-z]+)+)`", cmd)) & (agents | {agent})
        missing = sorted(n for n in named if n not in agents)
        r.append((agent in named and not missing,
                  f"/{command} dispatches {agent}, and every agent it names exists (missing {missing})"))
    reviewer = (PLUGIN / "agents" / "session-reviewer.md")
    if reviewer.is_file():
        r.append(("core-fit.md" in reviewer.read_text() and (PLUGIN / "skills" / "policy" / "core-fit.md").is_file(),
                  "session-reviewer's core-fit.md exists beside the policy skill"))
    return r


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
