"""
test_stop_hook_no_git.py — the Stop hook writes memory and never touches git.

It used to `git add memory/ tasks/` and commit on whatever branch was checked
out, and append its sidecar to .gitignore. On netdust (2026-09-24) that meant a
dirty .gitignore blocking every `git checkout` of a branch without the line, and
an auto-capture commit on `main` — a deploy rung — that made `make feature`
refuse until the rung was reset by hand. Memory is the author's to commit, on a
feature branch; the hook only writes files.

One repo on `main` with a tracked .gitignore, a transcript carrying a DECISION:
  - memory/STATE.md gets the decision (the capture still works)
  - HEAD does not move, nothing is staged
  - .gitignore is byte-for-byte unchanged
  - the watermark sidecar does not show in `git status` (it is excluded locally)
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


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-nogit-"))
    try:
        repo = tmp / "site"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "test@netdust.test")
        _git(repo, "config", "user.name", "test")
        gitignore = "vendor/\n.env\n"
        (repo / ".gitignore").write_text(gitignore)
        (repo / "memory").mkdir()
        (repo / "memory" / "STATE.md").write_text("# State\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "baseline")
        head_before = _git(repo, "rev-parse", "HEAD").stdout.strip()

        transcript = tmp / "t.jsonl"
        _write_transcript(transcript, [
            _msg("assistant", "DECISION: prices stay off the site", "n1"),
        ])
        _run_hook(repo, transcript)

        state = (repo / "memory" / "STATE.md").read_text()
        results.append(("prices stay off the site" in state,
                        "the decision is captured into memory/STATE.md"))
        results.append((_git(repo, "rev-parse", "HEAD").stdout.strip() == head_before,
                        "HEAD does not move — the hook commits nothing"))
        results.append((_git(repo, "diff", "--cached", "--name-only").stdout.strip() == "",
                        "nothing is staged"))
        results.append(((repo / ".gitignore").read_text() == gitignore,
                        ".gitignore is untouched"))

        porcelain = _git(repo, "status", "--porcelain", "--untracked-files=all").stdout
        results.append((".stop-hook-state.json" not in porcelain,
                        f"the watermark sidecar is excluded, not listed ({porcelain!r})"))
        results.append(("memory/STATE.md" in porcelain,
                        f"non-vacuity: the captured memory shows as the author's change ({porcelain!r})"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results


if __name__ == "__main__":
    for ok, label in run():
        print(f"  {'PASS' if ok else 'FAIL'}: {label}")
