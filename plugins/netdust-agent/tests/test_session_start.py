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

    env_extra overrides/adds environment variables for this run only — the
    test seam for NETDUST_SKILL_AUDIT_STAMP (0.3.3).
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


def test_skill_audit_nudge_when_stamp_missing() -> tuple[bool, str]:
    """No stamp (or >30d old) → one-line /skill-audit nudge is injected."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-nudge-"))
    try:
        (tmp / "memory").mkdir()
        (tmp / "memory" / "STATE.md").write_text("Sentinel-STATE-skillaudit\n")
        rc, stdout, _ = _run_hook(tmp, env_extra={
            "NETDUST_SKILL_AUDIT_STAMP": str(tmp / "no-such-stamp"),
        })
        if rc != 0:
            return False, f"stale stamp: hook exited {rc}"
        ok = "Skill-audit cadence" in stdout
        return ok, ("stale stamp: nudge injected" if ok
                    else f"nudge missing from output: {stdout[:300]}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_skill_audit_nudge_when_stamp_fresh() -> tuple[bool, str]:
    """DENIAL: a fresh stamp (<30d) must suppress the nudge."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-nudge2-"))
    try:
        (tmp / "memory").mkdir()
        (tmp / "memory" / "STATE.md").write_text("Sentinel-STATE-skillaudit\n")
        stamp = tmp / "skill-audit-last-run"
        stamp.write_text("2026-07-03\n")  # mtime = now
        rc, stdout, _ = _run_hook(tmp, env_extra={
            "NETDUST_SKILL_AUDIT_STAMP": str(stamp),
        })
        if rc != 0:
            return False, f"fresh stamp: hook exited {rc}"
        ok = "Skill-audit cadence" not in stdout
        return ok, ("fresh stamp: nudge suppressed" if ok
                    else "nudge injected despite fresh stamp")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _run_hook_env(cwd: Path, env: dict) -> tuple[int, str, str]:
    """Run the hook with an EXACT environment (HERDR_* stripped unless given) —
    the FR-19 seam: the calling shell's own herdr vars must not leak into a test."""
    base = {k: v for k, v in os.environ.items() if not k.startswith("HERDR_")}
    proc = subprocess.run(["bash", str(HOOK)], cwd=str(cwd), capture_output=True,
                          text=True, timeout=10, env={**base, **env})
    return proc.returncode, proc.stdout, proc.stderr


def test_herdr_lines() -> tuple[bool, str]:
    """FR-19: under HERDR_ENV=1 the hook appends the herdr block (ids + the pointer);
    with ids unset only the pointer; without HERDR_ENV the output is byte-identical."""
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    try:
        (tmp / "memory").mkdir()
        (tmp / "memory" / "STATE.md").write_text("Sentinel-STATE-HERDR")
        rc0, out0, _ = _run_hook_env(tmp, {})
        rc1, out1, _ = _run_hook_env(tmp, {"HERDR_ENV": "1", "HERDR_PANE_ID": "w3:p4",
                                            "HERDR_TAB_ID": "w3:t2", "HERDR_WORKSPACE_ID": "w3"})
        rc2, out2, _ = _run_hook_env(tmp, {"HERDR_ENV": "1"})
        rc3, out3, _ = _run_hook_env(tmp, {"HERDR_ENV": "0", "HERDR_PANE_ID": "w3:p4"})
        if (rc0, rc1, rc2, rc3) != (0, 0, 0, 0):
            return False, f"herdr: hook exited {(rc0, rc1, rc2, rc3)}"
        checks = [
            ("## herdr" not in out0, "block emitted without HERDR_ENV"),
            ("## herdr" in out1 and "w3:p4" in out1 and "w3:t2" in out1 and "herdr-moments.md" in out1,
             "ids or pointer missing under HERDR_ENV=1"),
            ("## herdr" in out2 and "herdr-moments.md" in out2 and "pane" not in out2.split("## herdr", 1)[1].split("\n\n", 1)[0],
             "ids unset should emit the pointer only"),
            ("## herdr" not in out3, "HERDR_ENV=0 must not emit the block"),
            # byte-identical outside herdr, apart from the injected-size line that counts its own bytes
            (out0 == out3, "HERDR_ENV=0 output differs from unset output"),
        ]
        failures = [msg for ok, msg in checks if not ok]
        if failures:
            return False, "herdr: " + "; ".join(failures)
        return True, "herdr block: ids + pointer under HERDR_ENV=1, pointer-only without ids, nothing otherwise"
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


def run() -> list[tuple[bool, str]]:
    return [
        test_empty_cwd_emits_nothing_but_logs(),
        test_full_project_emits_all_blocks(),
        test_log_records_missing_keys(),
        test_skill_audit_nudge_when_stamp_missing(),
        test_no_skill_audit_nudge_when_stamp_fresh(),
        test_herdr_lines(),
        test_site_yml_summary_carries_environments(),
        test_site_yml_summary_omits_rung_warning_without_environments(),
    ]
