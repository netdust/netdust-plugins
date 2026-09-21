"""
test_session_start.py — verifies the SessionStart hook loads memory correctly.

The hook reads cwd, looks for memory/STATE.md, memory/lessons.md, tasks/todo.md,
and site.yml, and emits them as a markdown block on stdout. It also logs every
fire to ~/.claude/logs/memory-hook.log with found/missing keys.

The bug this guards against: the hook silently emits nothing when memory files
are missing (correct), but the log MUST still record the fire — otherwise the
hook can be silently broken for months. The audit found exactly that pattern
in the Stop hook; testing both hooks closes the symmetry.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-start.sh"
LOG = Path.home() / ".claude" / "logs" / "memory-hook.log"


def _read_log_tail(lines: int = 5) -> str:
    if not LOG.exists():
        return ""
    return "\n".join(LOG.read_text().splitlines()[-lines:])


def _run_hook(cwd: Path, env_extra: dict | None = None) -> tuple[int, str, str]:
    """Run the hook with a given cwd. Returns (rc, stdout, stderr).

    env_extra overrides/adds environment variables for this run only.
    """
    proc = subprocess.run(
        ["bash", str(HOOK)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, **(env_extra or {})},
    )
    return proc.returncode, proc.stdout, proc.stderr


def test_empty_cwd_emits_nothing_but_logs() -> tuple[bool, str]:
    """Empty cwd (no memory/, no tasks/, no site.yml) — hook should emit no
    output block, but MUST still write a log line. Silent failure is the bug."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        rc, stdout, _ = _run_hook(tmp)
        if rc != 0:
            return False, f"empty: hook exited {rc}"

        # In an empty dir, harness_global should still be 'found' (it lives
        # in the plugin) — that alone produces output. So we can't assert
        # 'stdout is empty'. We CAN assert the log line was written.
        tail = _read_log_tail()
        if "session-start" not in tail:
            return False, "empty: no session-start log line written"
        if str(tmp) not in tail:
            return False, f"empty: log doesn't mention test cwd {tmp}"
        return True, "empty cwd: hook ran and logged the fire"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_full_project_emits_all_blocks() -> tuple[bool, str]:
    """Project with STATE.md, lessons.md, todo.md, site.yml — all four blocks
    should appear in the emitted memory context."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        (tmp / "memory").mkdir()
        (tmp / "tasks").mkdir()

        (tmp / "memory" / "STATE.md").write_text("Sentinel-STATE-A1B2C3")
        (tmp / "memory" / "lessons.md").write_text("Sentinel-LESSON-D4E5F6")
        (tmp / "tasks" / "todo.md").write_text("Sentinel-TODO-G7H8I9")
        (tmp / "site.yml").write_text(
            "site:\n  name: test-project\n  risk: low\n"
            "hosting:\n  provider: ddev\n"
        )

        rc, stdout, _ = _run_hook(tmp)
        if rc != 0:
            return False, f"full: hook exited {rc}"

        checks = [
            ("Sentinel-STATE-A1B2C3" in stdout, "STATE sentinel missing from output"),
            ("Sentinel-LESSON-D4E5F6" in stdout, "lessons sentinel missing"),
            ("Sentinel-TODO-G7H8I9" in stdout, "todo sentinel missing"),
            ("test-project" in stdout, "site.yml content missing"),
            ("## Project State" in stdout, "STATE header missing"),
            ("## Project Lessons" in stdout, "lessons header missing"),
            ("## Open Tasks" in stdout, "tasks header missing"),
            ("## site.yml summary" in stdout, "site.yml header missing"),
        ]
        failures = [msg for ok, msg in checks if not ok]
        if failures:
            return False, "full: " + "; ".join(failures)

        tail = _read_log_tail()
        if "found=[" not in tail:
            return False, "full: log line missing found=[...]"
        # Must list all four locally-found keys
        for key in ("site_yml", "state", "lessons", "todo"):
            if key not in tail:
                return False, f"full: log doesn't list found key '{key}'"
        return True, "full project: all 4 memory blocks emitted + logged"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_log_records_missing_keys() -> tuple[bool, str]:
    """The hook records 'missing' keys explicitly. This catches the case
    where memory files were renamed or moved silently — the log will show
    'missing=[state,lessons]' instead of failing silently."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        # No memory/ or tasks/ dirs — site.yml only
        (tmp / "site.yml").write_text("site:\n  name: partial\n")

        rc, _, _ = _run_hook(tmp)
        if rc != 0:
            return False, f"missing: hook exited {rc}"

        tail = _read_log_tail()
        # Look for our specific run (matching the test cwd)
        run_line = next(
            (l for l in tail.splitlines() if str(tmp) in l), None
        )
        if not run_line:
            return False, f"missing: no log line for cwd {tmp}"
        if "missing=[" not in run_line:
            return False, f"missing: log line missing 'missing=[...]'. Got: {run_line}"
        for key in ("state", "lessons", "todo"):
            if key not in run_line.split("missing=")[1]:
                return False, f"missing: '{key}' not reported as missing"
        return True, "missing keys: log explicitly reports what wasn't found"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_site_yml_summary_carries_environments() -> tuple[bool, str]:
    """The site.yml summary must surface `environments:` — the branch-to-server
    binding every make verb and the PreToolUse flow guard read.

    Until 2026-09-04 the grep matched only the retired schema
    (hosting.remote_path_*, deploy.staging_command/production_command) and had
    no `environments` anchor at all, so every session opened with the live
    topology stripped out: the agent could not see which branch belonged to
    which environment, and reached for raw git on rung branches instead.
    """
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        (tmp / "site.yml").write_text(
            "schema: 2\n"
            "site:\n  name: envproj\n  risk: low\n"
            "structure:\n  stack: wp\n  webroot: web\n"
            "environments:\n"
            "  staging:\n"
            "    url: https://staging.example.com\n"
            "    path: /srv/staging\n"
            "    branch: staging\n"
            "    role: \"colleague-facing\"\n"
            "    confirm: false\n"
            "  production:\n"
            "    url: https://example.com\n"
            "    path: /srv/prod\n"
            "    branch: main\n"
            "    role: \"live\"\n"
            "    confirm: true\n"
            "deploy:\n  method: rsync\n  state_dir: /srv/.state\n"
        )
        rc, stdout, _ = _run_hook(tmp)
        if rc != 0:
            return False, f"environments: hook exited {rc}"

        summary = stdout.split("## site.yml summary", 1)[-1]
        checks = [
            ("environments:" in summary, "`environments:` anchor missing"),
            ("staging:" in summary and "production:" in summary, "environment names missing"),
            ("branch: staging" in summary, "staging branch binding missing"),
            ("branch: main" in summary, "production branch binding missing"),
            ("confirm: true" in summary, "production confirm flag missing"),
            ("path: /srv/prod" in summary, "environment path missing"),
            ("stack: wp" in summary, "structure.stack missing — selects mk/<stack>.mk"),
            ("rung" in stdout, "no rung warning emitted for a project with environments"),
            ("netdust-devops:devops" in stdout, "devops skill not named"),
        ]
        failures = [msg for ok, msg in checks if not ok]
        if failures:
            return False, "environments: " + "; ".join(failures)
        return True, "site.yml summary carries environments (branch/path/role/confirm) + the rung warning"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_site_yml_summary_omits_rung_warning_without_environments() -> tuple[bool, str]:
    """A site.yml with no `environments:` is not a flow project — the rung
    warning would be noise, and naming branches that do not exist is worse."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        (tmp / "site.yml").write_text("site:\n  name: flat\n  risk: low\n")
        rc, stdout, _ = _run_hook(tmp)
        if rc != 0:
            return False, f"no-env: hook exited {rc}"
        if "rung" in stdout:
            return False, "no-env: rung warning emitted for a project without environments"
        return True, "no rung warning when site.yml declares no environments"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_agent_harness_text() -> tuple[bool, str]:
    """v0 carries memory injection only: no herdr/placement block, no skill-audit nudge, no
    0.28 harness vocabulary — even under HERDR_ENV=1 in a project with memory scaffolding."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        (tmp / "memory").mkdir()
        (tmp / "memory" / "STATE.md").write_text("Sentinel-STATE-X1")
        rc, out, _ = _run_hook(tmp, {"HERDR_ENV": "1", "HERDR_PANE_ID": "w1:p1",
                                     "NETDUST_SKILL_AUDIT_STAMP": str(tmp / "no-such-stamp")})
        stale = [w for w in ("herdr", "PLACEMENT", "skill-audit", "gate-check", "harnessed-development",
                             "spec-authoring", "Harness preferences") if w in out]
        return rc == 0 and "Sentinel-STATE-X1" in out and not stale, \
            f"session-start carries memory only, no 0.28 harness text (rc={rc}, found {stale})"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_backslashes_in_memory_survive() -> tuple[bool, str]:
    """Memory content is data: a Windows path or a stray `\\c` must arrive verbatim and must not
    cut off the files loaded after it."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        (tmp / "memory").mkdir()
        (tmp / "tasks").mkdir()
        (tmp / "memory" / "STATE.md").write_text("Sentinel-A C:\\code\\notes and \\c cut \\n stays\n")
        (tmp / "memory" / "lessons.md").write_text("Sentinel-LESSON-AFTER\n")
        (tmp / "tasks" / "todo.md").write_text("todo with \\t tab-looking text\n")
        rc, out, _ = _run_hook(tmp)
        ok = (rc == 0 and "C:\\code\\notes and \\c cut \\n stays" in out
              and "Sentinel-LESSON-AFTER" in out and "\\t tab-looking text" in out
              and "Total injected by session-start" in out)
        return ok, "backslashes in STATE/lessons/todo arrive verbatim and truncate nothing after them"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run() -> list[tuple[bool, str]]:
    return [
        test_empty_cwd_emits_nothing_but_logs(),
        test_full_project_emits_all_blocks(),
        test_log_records_missing_keys(),
        test_no_agent_harness_text(),
        test_backslashes_in_memory_survive(),
        test_site_yml_summary_carries_environments(),
        test_site_yml_summary_omits_rung_warning_without_environments(),
    ]
