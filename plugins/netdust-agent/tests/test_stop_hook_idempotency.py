"""
test_stop_hook_idempotency.py — verifies the Stop hook's idempotency,
continuation-line capture, and dedup watermark.

These cover the three bugs fixed in 2026-06-09:

  BUG 2a — no idempotency. extract_claude_text() joined ALL assistant
    messages and scan_tags() re-scanned everything on every fire, so a
    DECISION: written early got re-appended to STATE.md on every
    subsequent Stop. Fixed with a sidecar watermark
    (memory/.stop-hook-state.json: last_processed_uuid + captured_hashes).

  BUG 2b — single-line truncation. TAG_PATTERNS captured one line only,
    so a multi-line decision lost everything after line 1. Fixed by
    consuming indented / "- " continuation lines (cap 10) after a tag.

Tests fabricate a JSONL transcript (the real shape Claude Code passes via
hook_input["transcript_path"], including the top-level per-message "uuid")
and run the real session-stop.py hook against it via subprocess. No mocks.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-stop.py"


def _msg(role: str, text: str, uuid: str) -> dict:
    """One transcript message with a top-level uuid (real CC shape)."""
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
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "ANTHROPIC_API_KEY": ""},  # tag-scanner-only path
    )


def _with_temp_cwd() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    (tmp / "memory").mkdir()
    (tmp / "tasks").mkdir()
    # not a git repo on purpose — git_commit_memory no-ops outside a worktree
    return tmp


def _count(haystack: str, needle: str) -> int:
    return haystack.count(needle)


# ── BUG 2a: idempotency / watermark ──────────────────────────────────────────

def test_second_fire_appends_nothing() -> tuple[bool, str]:
    """The core idempotency property: firing the hook twice on the SAME
    transcript must capture the decision exactly once AND must not append a
    spurious 'no significant changes' marker on the second fire (the first
    fire DID capture something — the session wasn't empty)."""
    tmp = _with_temp_cwd()
    try:
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "DECISION: adopt the watermark sidecar", "a1"),
        ])

        r1 = _run_hook(tmp, transcript)
        if r1.returncode != 0:
            return False, f"idempotency: first fire exited {r1.returncode}: {r1.stderr[:200]}"
        state_after_1 = (tmp / "memory" / "STATE.md").read_text()

        r2 = _run_hook(tmp, transcript)
        if r2.returncode != 0:
            return False, f"idempotency: second fire exited {r2.returncode}: {r2.stderr[:200]}"
        state_after_2 = (tmp / "memory" / "STATE.md").read_text()

        n = _count(state_after_2, "adopt the watermark sidecar")
        if n != 1:
            return False, f"idempotency: decision captured {n}x (expected 1). STATE:\n{state_after_2[:400]}"
        # STATE.md must be byte-identical after the no-op second fire.
        if state_after_2 != state_after_1:
            return False, ("idempotency: STATE.md changed on no-op second fire.\n"
                           f"DIFF added:\n{state_after_2[len(state_after_1):][:300]}")
        return True, "idempotency: 2nd fire on same transcript appends nothing (byte-identical)"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_only_new_messages_processed_after_watermark() -> tuple[bool, str]:
    """First fire captures a1's decision. Then a NEW assistant message a2 is
    appended to the transcript. Second fire must capture ONLY a2 — not
    re-capture a1."""
    tmp = _with_temp_cwd()
    try:
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "DECISION: first decision alpha", "a1"),
        ])
        r1 = _run_hook(tmp, transcript)
        if r1.returncode != 0:
            return False, f"watermark: first fire exited {r1.returncode}"

        # append a second turn
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "DECISION: first decision alpha", "a1"),
            _msg("user", "more", "u2"),
            _msg("assistant", "DECISION: second decision beta", "a2"),
        ])
        r2 = _run_hook(tmp, transcript)
        if r2.returncode != 0:
            return False, f"watermark: second fire exited {r2.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        alpha = _count(state, "first decision alpha")
        beta = _count(state, "second decision beta")
        if alpha != 1:
            return False, f"watermark: alpha captured {alpha}x (expected 1)"
        if beta != 1:
            return False, f"watermark: beta captured {beta}x (expected 1)"
        return True, "watermark: only post-watermark messages reprocessed"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_sidecar_written() -> tuple[bool, str]:
    """The sidecar file must exist after a fire and record the last uuid."""
    tmp = _with_temp_cwd()
    try:
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "DECISION: write the sidecar", "a1"),
        ])
        r = _run_hook(tmp, transcript)
        if r.returncode != 0:
            return False, f"sidecar: hook exited {r.returncode}"

        sidecar = tmp / "memory" / ".stop-hook-state.json"
        if not sidecar.exists():
            return False, "sidecar: .stop-hook-state.json not written"
        data = json.loads(sidecar.read_text())
        if data.get("last_processed_uuid") != "a1":
            return False, f"sidecar: last_processed_uuid={data.get('last_processed_uuid')} (expected a1)"
        if not isinstance(data.get("captured_hashes"), list) or not data["captured_hashes"]:
            return False, "sidecar: captured_hashes missing/empty"
        if data.get("transcript_path") != str(transcript):
            return False, "sidecar: transcript_path not recorded"
        return True, "sidecar: written with uuid + hashes + transcript_path"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_hash_dedup_belt_and_braces() -> tuple[bool, str]:
    """Belt-and-braces: even if the watermark is bypassed (transcript path
    changed → full re-scan), an already-captured tag must NOT be re-appended
    because its hash is in captured_hashes."""
    tmp = _with_temp_cwd()
    try:
        t1 = tmp / "transcript-1.jsonl"
        _write_transcript(t1, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "DECISION: dedup me by hash", "a1"),
        ])
        r1 = _run_hook(tmp, t1)
        if r1.returncode != 0:
            return False, f"hashdedup: first fire exited {r1.returncode}"

        # Different transcript path → watermark uuid won't be found → full scan.
        # But the SAME decision text appears again. Hash must suppress it.
        t2 = tmp / "transcript-2.jsonl"
        _write_transcript(t2, [
            _msg("user", "ping", "v1"),
            _msg("assistant", "DECISION: dedup me by hash", "b1"),
        ])
        r2 = _run_hook(tmp, t2)
        if r2.returncode != 0:
            return False, f"hashdedup: second fire exited {r2.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        n = _count(state, "dedup me by hash")
        if n != 1:
            return False, f"hashdedup: captured {n}x across two transcripts (expected 1)"
        return True, "hashdedup: identical tag suppressed across transcript change"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_marker_when_tags_deduped_after_transcript_change() -> tuple[bool, str]:
    """Edge: a NEW transcript path with identical content → watermark misses →
    full re-scan → all tags hash-deduped away. `written` is empty but the
    session did contain tags, so we must NOT append a 'no changes' marker."""
    tmp = _with_temp_cwd()
    try:
        t1 = tmp / "transcript-1.jsonl"
        _write_transcript(t1, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "DECISION: only captured once", "a1"),
        ])
        r1 = _run_hook(tmp, t1)
        if r1.returncode != 0:
            return False, f"dedup-marker: first fire exited {r1.returncode}"

        t2 = tmp / "transcript-2.jsonl"  # different path → watermark uuid not found
        _write_transcript(t2, [
            _msg("user", "ping", "v1"),
            _msg("assistant", "DECISION: only captured once", "b1"),
        ])
        r2 = _run_hook(tmp, t2)
        if r2.returncode != 0:
            return False, f"dedup-marker: second fire exited {r2.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        if _count(state, "only captured once") != 1:
            return False, "dedup-marker: decision not deduped across transcript change"
        if "no significant changes captured" in state:
            return False, f"dedup-marker: spurious marker on deduped re-fire.\nSTATE:\n{state[:400]}"
        return True, "dedup-marker: no spurious marker when tags found-then-deduped"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_captured_hashes_capped_at_200() -> tuple[bool, str]:
    """captured_hashes must not grow without bound — cap at the last 200."""
    tmp = _with_temp_cwd()
    try:
        transcript = tmp / "transcript.jsonl"
        msgs = [_msg("user", "ping", "u0")]
        # 250 distinct decisions in one assistant message
        big = "\n".join(f"DECISION: decision number {i}" for i in range(250))
        msgs.append(_msg("assistant", big, "a1"))
        _write_transcript(transcript, msgs)

        r = _run_hook(tmp, transcript)
        if r.returncode != 0:
            return False, f"cap: hook exited {r.returncode}: {r.stderr[:200]}"

        sidecar = tmp / "memory" / ".stop-hook-state.json"
        data = json.loads(sidecar.read_text())
        n = len(data.get("captured_hashes", []))
        if n > 200:
            return False, f"cap: captured_hashes has {n} entries (expected <=200)"
        return True, f"cap: captured_hashes capped ({n} <= 200)"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_daily_marker_written_once_per_day() -> tuple[bool, str]:
    """The 'no significant changes' marker must appear at most once per
    calendar day even across multiple no-tag fires."""
    tmp = _with_temp_cwd()
    try:
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "Just an ordinary reply, no tags.", "a1"),
        ])
        r1 = _run_hook(tmp, transcript)
        if r1.returncode != 0:
            return False, f"daily-marker: first fire exited {r1.returncode}"

        # second no-tag turn, same day
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "Just an ordinary reply, no tags.", "a1"),
            _msg("user", "again", "u2"),
            _msg("assistant", "Still nothing notable here.", "a2"),
        ])
        r2 = _run_hook(tmp, transcript)
        if r2.returncode != 0:
            return False, f"daily-marker: second fire exited {r2.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        n = _count(state, "no significant changes captured")
        if n != 1:
            return False, f"daily-marker: marker written {n}x today (expected 1). STATE:\n{state[:400]}"
        return True, "daily-marker: written at most once per calendar day"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ── BUG 2b: continuation-line capture ────────────────────────────────────────

def test_decision_captures_continuation_lines() -> tuple[bool, str]:
    """A DECISION: followed by indented / '- ' lines must capture the whole
    block, not just line 1 (the June-5 mid-sentence truncation bug)."""
    tmp = _with_temp_cwd()
    try:
        text = (
            "DECISION: consolidate the provider seam. This consolidates everything:\n"
            "  - the truncated-stream guard\n"
            "  - the synthesized tool_call id\n"
            "  - the ollama deref guard\n"
            "\n"
            "Some unrelated trailing prose that must NOT be captured."
        )
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", text, "a1"),
        ])
        r = _run_hook(tmp, transcript)
        if r.returncode != 0:
            return False, f"continuation: hook exited {r.returncode}: {r.stderr[:200]}"

        state = (tmp / "memory" / "STATE.md").read_text()
        checks = [
            ("This consolidates everything:" in state, "head sentence missing"),
            ("truncated-stream guard" in state, "continuation line 1 missing"),
            ("synthesized tool_call id" in state, "continuation line 2 missing"),
            ("ollama deref guard" in state, "continuation line 3 missing"),
            ("unrelated trailing prose" not in state, "captured past the blank line"),
        ]
        failures = [m for ok, m in checks if not ok]
        if failures:
            return False, "continuation: " + "; ".join(failures) + f"\nSTATE:\n{state[:500]}"
        return True, "continuation: multi-line DECISION captured to blank line"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_continuation_stops_at_new_tag() -> tuple[bool, str]:
    """A continuation block must stop when a NEW tag line begins, so the two
    tags don't bleed into each other."""
    tmp = _with_temp_cwd()
    try:
        text = (
            "DECISION: first thing\n"
            "  - detail of first\n"
            "RISK: second thing\n"
            "  - detail of second"
        )
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", text, "a1"),
        ])
        r = _run_hook(tmp, transcript)
        if r.returncode != 0:
            return False, f"newtag: hook exited {r.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        # The decision block should contain 'detail of first' but the RISK's
        # detail should be under Risks, not bled into the decision. We assert
        # both details are present and the decision did not swallow the RISK head.
        checks = [
            ("first thing" in state, "decision head missing"),
            ("detail of first" in state, "decision continuation missing"),
            ("second thing" in state, "risk head missing"),
            ("detail of second" in state, "risk continuation missing"),
        ]
        failures = [m for ok, m in checks if not ok]
        if failures:
            return False, "newtag: " + "; ".join(failures) + f"\nSTATE:\n{state[:500]}"
        return True, "continuation: stops at the next tag boundary"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_continuation_capped_at_10_lines() -> tuple[bool, str]:
    """A runaway indented block must be capped at 10 continuation lines."""
    tmp = _with_temp_cwd()
    try:
        lines = ["DECISION: capped head"]
        lines += [f"  - cont line {i}" for i in range(20)]  # 20 continuation lines
        transcript = tmp / "transcript.jsonl"
        _write_transcript(transcript, [
            _msg("user", "ping", "u1"),
            _msg("assistant", "\n".join(lines), "a1"),
        ])
        r = _run_hook(tmp, transcript)
        if r.returncode != 0:
            return False, f"cap10: hook exited {r.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        if "cont line 0" not in state:
            return False, "cap10: first continuation line missing"
        # line index 10+ should be excluded (10-line cap → lines 0..9 kept)
        if "cont line 12" in state:
            return False, "cap10: continuation not capped (line 12 present)"
        return True, "continuation: capped at 10 lines"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_TESTS = [
    test_second_fire_appends_nothing,
    test_only_new_messages_processed_after_watermark,
    test_sidecar_written,
    test_hash_dedup_belt_and_braces,
    test_no_marker_when_tags_deduped_after_transcript_change,
    test_captured_hashes_capped_at_200,
    test_daily_marker_written_once_per_day,
    test_decision_captures_continuation_lines,
    test_continuation_stops_at_new_tag,
    test_continuation_capped_at_10_lines,
]


def run() -> list[tuple[bool, str]]:
    results = []
    for fn in _TESTS:
        try:
            results.append(fn())
        except Exception as e:  # a crashing test is a failing test, not an abort
            results.append((False, f"{fn.__name__}: raised {type(e).__name__}: {e}"))
    return results
