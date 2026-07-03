"""
test_no_auto_memory.py — fix 5 (2026-07-03): a project can opt out of ALL
Stop-hook writes (memory/, tasks/, .gitignore, auto-commit) by placing a
.no-auto-memory marker at its root. Contract driver: the Layer-B fleet dir
(~/Sites/netdust-wp-manager) is manual-only per Stefan's CLAUDE.md — the
hook must never write into or commit it.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-stop.py"


def _msg(role: str, text: str, uuid: str) -> dict:
    return {
        "type": role,
        "uuid": uuid,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _write_transcript(path: Path, messages: list[dict]) -> None:
    with open(path, "w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")


def _run_hook(cwd: Path, transcript: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    return subprocess.run(
        ["python3", str(HOOK)],
        input=payload, capture_output=True, text=True, timeout=10,
        env={**os.environ},
    )


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-noautomem-"))
    try:
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("assistant", "DECISION: this must never be auto-captured here", "u1"),
            _msg("assistant", "LESSON: fleet memory is manual-only", "u2"),
            _msg("assistant", "TODO: should not appear", "u3"),
        ])

        # ── DENIAL: marker present → zero writes, zero commits ──────────────
        excluded = tmp / "fleet"
        excluded.mkdir()
        (excluded / ".no-auto-memory").touch()
        _git(excluded, "init", "-q")
        _git(excluded, "commit", "-q", "--allow-empty", "-m", "baseline")
        before = _git(excluded, "rev-parse", "HEAD").stdout.strip()

        proc = _run_hook(excluded, transcript)
        results.append((proc.returncode == 0, "hook exits 0 on excluded project"))
        results.append((not (excluded / "memory").exists(), "DENIAL: no memory/ created"))
        results.append((not (excluded / "tasks").exists(), "DENIAL: no tasks/ created"))
        results.append((not (excluded / ".gitignore").exists(), "DENIAL: no .gitignore written"))
        after = _git(excluded, "rev-parse", "HEAD").stdout.strip()
        results.append((before == after, "DENIAL: no auto-commit landed"))
        status = _git(excluded, "status", "--porcelain").stdout.strip()
        # Only the marker itself may show as untracked.
        results.append((
            status in ("", "?? .no-auto-memory"),
            f"DENIAL: working tree untouched (status: {status!r})",
        ))

        # ── ALLOW: no marker → normal capture ────────────────────────────────
        normal = tmp / "normal"
        normal.mkdir()
        _run_hook(normal, transcript)
        state = (normal / "memory" / "STATE.md")
        results.append((
            state.exists() and "never be auto-captured here" in state.read_text(),
            "ALLOW: capture proceeds without the marker",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results
