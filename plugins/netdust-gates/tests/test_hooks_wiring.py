"""test_hooks_wiring.py — hooks.json must reach every tool the hook scripts handle.

The 0.28 guard handled Write/Edit but hooks.json matched only `Bash`, so those floors never
ran live while every test — which calls the script over stdin — stayed green. These tests
read the wiring, not just the function."""
import importlib.util
import json
import os
import re
import subprocess
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"


def _hooks_json() -> dict:
    return json.loads((HOOKS / "hooks.json").read_text())["hooks"]


def _guard():
    spec = importlib.util.spec_from_file_location("pretooluse_guard", HOOKS / "pretooluse-guard.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _guard_matchers() -> list[str]:
    return [g["matcher"] for g in _hooks_json().get("PreToolUse", [])
            if any("pretooluse-guard.py" in h["command"] for h in g["hooks"])]


def _uncovered(tools, matchers) -> list[str]:
    return [t for t in tools if not any(re.fullmatch(m, t) for m in matchers)]


def _commands() -> list[str]:
    return [h["command"] for groups in _hooks_json().values() for g in groups for h in g["hooks"]]


def _exit_with_missing_script(command: str) -> int:
    """Run a registered hook command the way the shell does, with its script gone. Exit 2 is the
    one code that blocks a tool, so a launcher that cannot open its script must still exit 0."""
    env = {**os.environ, "CLAUDE_PLUGIN_ROOT": "/nonexistent-plugin-root"}
    return subprocess.run(["bash", "-c", command], input="{}", capture_output=True, text=True,
                          timeout=10, env=env).returncode


def run() -> list[tuple[bool, str]]:
    handled = _guard().HANDLED_TOOLS
    matchers = _guard_matchers()
    reproduced = _uncovered(handled, ["Bash"])
    scripts = [re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"\s]+)", c) for c in _commands()]
    return [
        (bool(matchers) and _uncovered(handled, matchers) == [],
         f"hooks.json matcher covers every tool the guard handles (matchers {matchers}, gap {_uncovered(handled, matchers)})"),
        (reproduced == [t for t in handled if t != "Bash"] and len(reproduced) >= 3,
         f"the test bites: the 0.28 matcher `Bash` is reported as missing {reproduced}"),
        (all(m and (HOOKS.parent / m.group(1)).is_file() for m in scripts),
         "every command hooks.json registers names a script that exists"),
        (set(_hooks_json()) == {"PreToolUse", "SessionStart", "Stop"},
         f"only the carried events are registered — no SubagentStop, no loop gate (got {sorted(_hooks_json())})"),
        (not any("loop-gate" in c or "subagent-stop" in c for c in _commands()),
         "no command names a hook that was not carried"),
        (any("session-start.sh" in c for c in _commands()) and any("session-stop.py" in c for c in _commands()),
         "SessionStart and Stop point at the carried scripts"),
        (all(_exit_with_missing_script(c) == 0 for c in _commands()),
         f"a missing script fails OPEN — exit codes {[_exit_with_missing_script(c) for c in _commands()]}"),
    ]
