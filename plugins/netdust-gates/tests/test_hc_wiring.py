"""test_hc_wiring.py — no live plugin still teaches the herdr 0.9 flow (hc-flow spec R2), and
parallel-work carries the urgent-only worktree rule (R6). Tokens are built by concatenation so
this file never matches itself."""
from pathlib import Path

PLUGINS = Path(__file__).resolve().parent.parent.parent
ROOTS = [PLUGINS / name for name in ("netdust-core", "netdust-gates", "netdust-devops")]
TEXT = {".md", ".py", ".sh", ".json", ".toml", ""}
SKIP_FILES = {"tests/test_session_start.py", "tests/test_policy_skill.py", "tests/test_evals_shape.py",
              "tests/test_hc_wiring.py", ".claude-plugin/plugin.json"}
STALE = ("herdr" + "-orchestration", "herdr agent" + " start", "herdr" + "-watcher", "HERDR" + "_ENV",
         "herdr" + " --skill")
PARALLEL = PLUGINS / "netdust-devops" / "skills" / "parallel-work" / "SKILL.md"
HC_SKILL = PLUGINS / "netdust-core" / "skills" / "hc-orchestration" / "SKILL.md"
SESSION_LEARN = PLUGINS / "netdust-gates" / "commands" / "session-learn.md"
POLICY = PLUGINS / "netdust-gates" / "skills" / "policy" / "SKILL.md"


def _live_files():
    for root in ROOTS:
        for path in root.rglob("*"):
            rel = path.relative_to(root).as_posix()
            if (path.is_file() and path.suffix in TEXT and "__pycache__" not in path.parts
                    and not rel.startswith("evals/stubs/") and rel not in SKIP_FILES):
                yield path


def _stale_hits() -> list[str]:
    hits = []
    for path in _live_files():
        try:
            text = path.read_text()
        except UnicodeDecodeError:
            continue
        hits += [f"{path.relative_to(PLUGINS)}: {tok}" for tok in STALE if tok in text]
    return hits


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    end = text.find("\n#", start + len(heading))
    return text[start:end if end > 0 else len(text)]


def run() -> list[tuple[bool, str]]:
    hits = _stale_hits()
    parallel = PARALLEL.read_text()
    skill = HC_SKILL.read_text()
    return [
        ("AF_UNIX" in skill and "connect" in skill,
         "hc-orchestration decides whether a core runs by connecting to its socket, not by the file existing"),
        ("inside hc, probe only after an hc connection error" in skill.lower() and "unsandboxed" in skill,
         "hc-orchestration: probe before the first call outside hc; inside hc only after a connection error (reviewer ruling A)"),
        ("holder's environment" in skill,
         "hc-orchestration: a crashed core is restarted by its holder, with the holder's environment"),
        ("your reviewer is now" in skill,
         "hc-orchestration: a restarted reviewer tells its coder its new address (hc has no reparent)"),
        ("HC_TERMINAL_ID" in parallel and "outside hc" in parallel.lower(),
         "parallel-work prescribes hc helper terminals inside hc only, and sends sessions outside hc to the core rule"),
        ("in its own worktree" not in SESSION_LEARN.read_text(),
         "session-learn's netdust proposals no longer cut a worktree by default (hc-flow R6)"),
        ("from its own\ncheckout" not in POLICY.read_text() and "from its own checkout" not in POLICY.read_text(),
         "policy: the reviewer shares the project's checkout now; make review reads the pushed branch"),
        (not hits, f"no live file in core, gates or devops teaches the herdr 0.9 flow (found {hits[:8]})"),
        ("~/.herdr/worktrees" in parallel, "parallel-work puts a worktree under ~/.herdr/worktrees, never ~/Sites"),
        ("**worktree**, always" not in parallel, "parallel-work no longer gives every editing agent a worktree"),
        ("urgent" in _section(parallel, "### A second agent"),
         "parallel-work's second-agent rule: other work waits for the coder unless it is urgent"),
    ]
