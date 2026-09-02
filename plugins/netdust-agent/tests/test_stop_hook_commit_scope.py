"""
test_stop_hook_commit_scope.py — regression for the 2026-08 data-loss bug.

The Stop hook's auto-capture commit must be structurally incapable of
committing anything outside memory/ + tasks/. The original bug: `git commit`
with no pathspec committed the WHOLE index, so a source deletion staged during
the session (a mid-build `git rm`) was swept into a "memory(...): auto-capture
session end" commit and lost from HEAD — 308 lines of PHP deleted under a
memory label, nothing else.

Two cases, both with an unrelated deletion pre-staged before the hook fires:
  A. No memory content this session → the hook must NOT commit at all, and the
     staged deletion must NOT land in HEAD.
  B. Memory content present → the hook DOES commit, but the commit contains
     only memory/ and never the staged deletion; the deletion stays pending.
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


def _init_repo_with_source(root: Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@netdust.test")
    _git(root, "config", "user.name", "test")
    src = root / "src"
    src.mkdir()
    # A tracked source file with real line count, to mirror the deleted templates.
    (src / "template.php").write_text("<?php\n" + "\n".join(f"// line {i}" for i in range(20)) + "\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "baseline: source present")


def _head(root: Path) -> str:
    return _git(root, "rev-parse", "HEAD").stdout.strip()


def _source_in_head(root: Path) -> bool:
    return _git(root, "cat-file", "-e", "HEAD:src/template.php").returncode == 0


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-commitscope-"))
    try:
        # ── Case A: unrelated staged deletion, NO memory content ─────────────
        a = tmp / "case-a"
        a.mkdir()
        _init_repo_with_source(a)
        _git(a, "rm", "-q", "src/template.php")          # stage the deletion
        before = _head(a)

        # Transcript with no capturable tags → hook writes no memory.
        transcript_a = tmp / "a.jsonl"
        _write_transcript(transcript_a, [
            _msg("assistant", "just some ordinary text, no tags here", "a1"),
        ])
        _run_hook(a, transcript_a)

        results.append((_head(a) == before,
                        "A: no memory content → hook creates no commit"))
        results.append((_source_in_head(a),
                        "A: staged deletion did NOT land in HEAD (source still there)"))

        # ── Case B: unrelated staged deletion + real memory content ──────────
        b = tmp / "case-b"
        b.mkdir()
        _init_repo_with_source(b)
        _git(b, "rm", "-q", "src/template.php")          # stage the deletion
        before_b = _head(b)

        transcript_b = tmp / "b.jsonl"
        _write_transcript(transcript_b, [
            _msg("assistant", "DECISION: capture this to STATE.md", "b1"),
        ])
        _run_hook(b, transcript_b)

        after_b = _head(b)
        results.append((after_b != before_b,
                        "B: memory content → a commit IS created"))

        touched = _git(b, "show", "--name-only", "--pretty=format:", "HEAD").stdout.split()
        results.append((any(t.startswith("memory/") for t in touched),
                        f"B: commit contains memory/ ({touched})"))
        results.append(("src/template.php" not in touched,
                        f"B: commit does NOT contain the staged deletion ({touched})"))
        results.append((_source_in_head(b),
                        "B: source still in HEAD after the memory commit"))

        # The deletion must still be pending (staged), not silently discarded.
        porcelain = _git(b, "status", "--porcelain", "--", "src/template.php").stdout
        results.append((porcelain.strip().startswith("D"),
                        f"B: the staged deletion is still pending, untouched ({porcelain!r})"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results


if __name__ == "__main__":
    for ok, label in run():
        print(f"  {'PASS' if ok else 'FAIL'}: {label}")
