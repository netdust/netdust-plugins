"""
test_stop_hook_dedup.py — fix 4 (2026-07-03): dedup must survive sidecar loss.

The 200-entry captured_hashes ring lives in the GITIGNORED sidecar
(memory/.stop-hook-state.json). Lose the sidecar (fresh clone, cleanup,
crash before the sidecar write) and the ring resets — the old code then
re-appended every tag on the next full re-scan. The fix makes the TARGET
FILE the durable dedup record: before appending, the hook checks whether
the normalized tag body already exists in the target file.
"""

import shutil
import tempfile
from pathlib import Path

from hook_test_utils import (
    msg as _msg,
    write_transcript as _write_transcript,
    run_stop_hook as _run_hook,
)


def run() -> list[tuple[bool, str]]:
    results = []
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-dedup-"))
    try:
        cwd = tmp / "project"
        cwd.mkdir()
        transcript = tmp / "transcript.jsonl"
        msgs = [
            _msg("assistant", "DECISION: use marker files for hook exclusion", "u1"),
            _msg("assistant", "LESSON: sidecar hash ring is not durable", "u2"),
            _msg("assistant", "TODO: promote resolver into invariants doc", "u3"),
        ]
        _write_transcript(transcript, msgs)

        # Fire 1 — captures everything.
        _run_hook(cwd, transcript)
        state = (cwd / "memory" / "STATE.md").read_text()
        results.append((
            state.count("use marker files for hook exclusion") == 1,
            "fire 1 captures DECISION once",
        ))

        # Simulate sidecar loss, then re-fire the SAME transcript.
        sidecar = cwd / "memory" / ".stop-hook-state.json"
        results.append((sidecar.exists(), "sidecar exists after fire 1"))
        sidecar.unlink()
        _run_hook(cwd, transcript)

        state = (cwd / "memory" / "STATE.md").read_text()
        lessons = (cwd / "memory" / "lessons.md").read_text()
        todo = (cwd / "tasks" / "todo.md").read_text()
        results.append((
            state.count("use marker files for hook exclusion") == 1,
            "DENIAL: sidecar loss does NOT duplicate DECISION in STATE.md",
        ))
        results.append((
            lessons.count("sidecar hash ring is not durable") == 1,
            "DENIAL: sidecar loss does NOT duplicate LESSON in lessons.md",
        ))
        results.append((
            todo.count("promote resolver into invariants doc") == 1,
            "DENIAL: sidecar loss does NOT duplicate TODO in todo.md",
        ))

        # A genuinely NEW tag on a lost-sidecar re-fire still lands, once.
        sidecar.unlink(missing_ok=True)
        msgs.append(_msg("assistant", "DECISION: brand new decision after loss", "u4"))
        _write_transcript(transcript, msgs)
        _run_hook(cwd, transcript)
        state = (cwd / "memory" / "STATE.md").read_text()
        results.append((
            state.count("brand new decision after loss") == 1,
            "ALLOW: new tag still captured exactly once after sidecar loss",
        ))
        results.append((
            state.count("use marker files for hook exclusion") == 1,
            "DENIAL holds across a third fire",
        ))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return results
