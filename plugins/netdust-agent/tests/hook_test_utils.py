"""hook_test_utils.py — shared helpers for the stop-hook test family.

Deliberately NOT named test_*.py: run.sh's glob must never execute this as
a test module. Only byte-equivalent helpers were lifted here; modules whose
_run_hook targets a different hook (session-start, subagent-stop,
standards-gate) keep their own local variants on purpose.
"""
import json
import os
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "hooks" / "session-stop.py"


def msg(role: str, text: str, uuid: str) -> dict:
    """One transcript message with a top-level uuid (real CC shape)."""
    return {
        "type": role,
        "uuid": uuid,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def write_transcript(path: Path, messages: list[dict]) -> None:
    with open(path, "w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")


def run_stop_hook(cwd: Path, transcript: Path,
                  env_extra: dict | None = None) -> subprocess.CompletedProcess:
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    return subprocess.run(
        ["python3", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, **(env_extra or {})},
    )
