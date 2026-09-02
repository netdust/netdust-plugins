"""
test_stop_hook_add_pathspec.py — regression for the 2026-09-02 silent-no-commit bug.

`git_commit_memory()` staged with a single `git add memory/ tasks/`. git treats a
pathspec that matches nothing as fatal for the WHOLE command, so in a project with
no tasks/ directory it staged NOTHING, the following `diff --cached --quiet` saw an
empty index, and the hook returned as if there were simply nothing to commit.

capture_output=True swallowed the fatal, and the `done cwd=... wrote=[...]` log line
is written BEFORE the commit attempt — so the hook logged a clean run every time
while committing nothing, for as long as the project lacked tasks/.

Cost: ntdst-core and ntdst-baseline were the only two Netdust projects with no
tasks/ dir, and the only two whose memory/ was never committed. ntdst-core's
STATE.md — a release gate and an open ruling — sat untracked for weeks.

Two cases:
  A. memory/ only, NO tasks/ dir  → the hook must still commit memory/ (the bug).
  B. both dirs present            → unchanged; still commits both.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from hook_test_utils import (
    msg as _msg,
    write_transcript as _write_transcript,
    run_stop_hook as _run_hook,
)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _init_repo(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@netdust.test")
    _git(root, "config", "user.name", "test")
    (root / "README.md").write_text("base\n")
    _git(root, "add", "README.md")
    _git(root, "commit", "-qm", "base")


def _committed_paths(root: Path) -> str:
    """Paths in HEAD's most recent commit, empty string when nothing was committed."""
    out = _git(root, "show", "--name-only", "--format=", "HEAD")
    return out.stdout.strip()


def _head_subject(root: Path) -> str:
    return _git(root, "log", "-1", "--format=%s").stdout.strip()


def run() -> list[tuple[bool, str]]:
    results = []

    # --- Case A: no tasks/ directory (the bug) --------------------------------
    tmp = Path(tempfile.mkdtemp())
    try:
        cwd = tmp / "no-tasks"
        cwd.mkdir()
        _init_repo(cwd)
        # memory/ exists and carries content; tasks/ deliberately does NOT exist.
        (cwd / "memory").mkdir()
        assert not (cwd / "tasks").exists()

        transcript = tmp / "t-a.jsonl"
        _write_transcript(transcript, [
            _msg("assistant", "DECISION: the add pathspec must tolerate a missing dir", "a1"),
        ])
        _run_hook(cwd, transcript)

        state = cwd / "memory" / "STATE.md"
        results.append((state.exists(), "A: hook wrote memory/STATE.md with no tasks/ dir"))
        results.append((
            "auto-capture" in _head_subject(cwd),
            "A: hook COMMITTED with no tasks/ dir (the regression)",
        ))
        results.append((
            "memory/STATE.md" in _committed_paths(cwd),
            "A: the commit contains memory/STATE.md",
        ))
        # Scope holds: the commit carries memory/ and nothing else. .gitignore is
        # written by _ensure_sidecar_gitignored and deliberately stays OUT of the
        # auto-capture commit, so "clean tree afterwards" would be the wrong claim.
        results.append((
            all(p.startswith("memory/") for p in _committed_paths(cwd).splitlines() if p),
            "A: the commit carries memory/ paths ONLY",
        ))
        results.append((
            ".gitignore" not in _committed_paths(cwd),
            "A: the sidecar .gitignore is not swept into the memory commit",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # --- Case B: both dirs present, behaviour unchanged -----------------------
    tmp = Path(tempfile.mkdtemp())
    try:
        cwd = tmp / "both"
        cwd.mkdir()
        _init_repo(cwd)
        (cwd / "memory").mkdir()
        (cwd / "tasks").mkdir()
        (cwd / "tasks" / "todo.md").write_text("# todo\n")

        transcript = tmp / "t-b.jsonl"
        _write_transcript(transcript, [
            _msg("assistant", "TODO: keep committing both dirs", "b1"),
        ])
        _run_hook(cwd, transcript)

        committed = _committed_paths(cwd)
        results.append((
            "auto-capture" in _head_subject(cwd),
            "B: hook still commits when both dirs exist",
        ))
        results.append((
            "tasks/todo.md" in committed,
            "B: tasks/ still reaches the commit",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return results
