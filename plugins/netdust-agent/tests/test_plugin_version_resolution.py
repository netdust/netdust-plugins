"""
test_plugin_version_resolution.py — fix 3 (2026-07-03): "active plugin
version" must come from Claude Code's own registry
(~/.claude/plugins/installed_plugins.json, v2 schema:
plugins.<name>@<marketplace> = [{installPath, ...}]), NOT from version-dir
mtimes. Real incident: netdust-agent 0.2.1's mtime was 4 ms newer than the
actually-installed 0.3.0, so SKILL-EDGE lessons routed to the stale dir and
the ~/.claude/plugins/<plugin> symlinks pointed at 0.2.1.

Covers both resolvers: session-stop.py (_netdust_plugin_dirs, this file's
Python tests) and session-start.sh (symlink refresh, bash tests — Task 5).
"""

import json
import os
import subprocess
import shutil
import tempfile
import time
from pathlib import Path

HOOKS = Path(__file__).parent.parent / "hooks"
HOOK_STOP = HOOKS / "session-stop.py"
HOOK_START = HOOKS / "session-start.sh"


def _fake_home(tmp: Path) -> tuple[Path, Path, Path]:
    """Build a fake $HOME with two cache versions of netdust-agent where the
    WRONG one (stale) has the newer mtime, plus a registry naming the right one.
    Returns (home, active_dir, stale_dir)."""
    home = tmp / "home"
    cache = home / ".claude" / "plugins" / "cache" / "netdust-plugins" / "netdust-agent"
    active = cache / "9.9.9"
    stale = cache / "9.9.8"
    for d in (active, stale):
        (d / "skills" / "probe-skill").mkdir(parents=True)
        (d / "skills" / "probe-skill" / "SKILL.md").write_text("# probe\n")
    # mtime trap: stale NEWER than active.
    now = time.time()
    os.utime(active, (now - 60, now - 60))
    os.utime(stale, (now, now))
    registry = home / ".claude" / "plugins" / "installed_plugins.json"
    registry.write_text(json.dumps({
        "version": 2,
        "plugins": {
            "netdust-agent@netdust-plugins": [
                {"scope": "user", "installPath": str(active), "version": "9.9.9"}
            ]
        },
    }))
    return home, active, stale


def _run_stop_hook(cwd: Path, transcript: Path, home: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    env = {**os.environ, "HOME": str(home)}
    env.pop("CLAUDE_PLUGIN_ROOT", None)  # force registry path, no climb hint
    return subprocess.run(
        ["python3", str(HOOK_STOP)],
        input=payload, capture_output=True, text=True, timeout=10, env=env,
    )


def _msg(text: str, uuid: str) -> dict:
    return {"type": "assistant", "uuid": uuid,
            "message": {"content": [{"type": "text", "text": text}]}}


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-verres-"))
    try:
        home, active, stale = _fake_home(tmp)
        cwd = tmp / "project"
        cwd.mkdir()
        transcript = tmp / "t.jsonl"
        with open(transcript, "w") as f:
            f.write(json.dumps(_msg(
                "SKILL-EDGE: probe-skill: registry beats mtime", "u1")) + "\n")

        _run_stop_hook(cwd, transcript, home)
        active_lessons = active / "skills" / "probe-skill" / "lessons.md"
        stale_lessons = stale / "skills" / "probe-skill" / "lessons.md"
        results.append((
            active_lessons.exists() and "registry beats mtime" in active_lessons.read_text(),
            "SKILL-EDGE routes to installPath version (registry wins)",
        ))
        results.append((
            not stale_lessons.exists(),
            "DENIAL: newer-mtime stale version receives nothing",
        ))

        # Fallback: registry absent → mtime heuristic still resolves (via
        # CLAUDE_PLUGIN_ROOT climb), so the hook keeps working outside CC.
        home2, active2, stale2 = _fake_home(tmp / "second")
        (home2 / ".claude" / "plugins" / "installed_plugins.json").unlink()
        cwd2 = tmp / "project2"
        cwd2.mkdir()
        payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd2)})
        env = {**os.environ, "HOME": str(home2),
               "CLAUDE_PLUGIN_ROOT": str(stale2)}
        subprocess.run(["python3", str(HOOK_STOP)], input=payload,
                       capture_output=True, text=True, timeout=10, env=env)
        results.append((
            (stale2 / "skills" / "probe-skill" / "lessons.md").exists(),
            "FALLBACK: no registry → mtime climb still routes (stale2 is newest)",
        ))

        # ── bash side: session-start.sh symlink refresh (Task 5) ────────────
        home3, active3, stale3 = _fake_home(tmp / "third")
        proj3 = tmp / "project3"
        proj3.mkdir()
        env3 = {**os.environ, "HOME": str(home3),
                "CLAUDE_PLUGIN_ROOT": str(active3)}
        subprocess.run(["bash", str(HOOK_START)], cwd=proj3,
                       capture_output=True, text=True, timeout=15, env=env3)
        link = home3 / ".claude" / "plugins" / "netdust-agent"
        results.append((
            link.is_symlink() and os.readlink(link) == str(active3),
            "symlink targets installPath, not newest-mtime dir",
        ))

        # Fallback: registry removed → mtime pick (stale3 is newest).
        (home3 / ".claude" / "plugins" / "installed_plugins.json").unlink()
        subprocess.run(["bash", str(HOOK_START)], cwd=proj3,
                       capture_output=True, text=True, timeout=15, env=env3)
        results.append((
            link.is_symlink() and os.readlink(link) == str(stale3),
            "FALLBACK: no registry → symlink uses newest-mtime dir",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results
