"""
test_tag_scanner.py — verifies the Stop hook's deterministic tag scanner.

The tag scanner is the workhorse of the memory pipeline. It runs on every
session end and lifts DECISION:/RISK:/LESSON:/TODO:/SKILL-EDGE: lines from
the transcript into the right memory files. If this is broken, no project
memory ever gets captured.

Tests fabricate a JSONL transcript file (the real shape Claude Code passes
in via hook_input["transcript_path"]) and run the real session-stop.py
hook against it. They assert on actual file contents on disk.
"""

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "session-stop.py"


def _make_transcript(tmp: Path, assistant_text: str) -> Path:
    """Write a minimal JSONL transcript with one assistant message."""
    path = tmp / "transcript.jsonl"
    messages = [
        {"type": "user", "message": {"content": "ping"}},
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": assistant_text}],
            },
        },
    ]
    with open(path, "w") as f:
        for m in messages:
            f.write(json.dumps(m) + "\n")
    return path


def _run_hook(cwd: Path, transcript: Path) -> subprocess.CompletedProcess:
    """Invoke the real Stop hook the way Claude Code does: stdin = JSON."""
    payload = json.dumps({"transcript_path": str(transcript), "cwd": str(cwd)})
    return subprocess.run(
        ["python3", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=10,
        env={**os.environ, "ANTHROPIC_API_KEY": ""},  # force tag-scanner-only path
    )


def _with_temp_cwd():
    tmp = Path(tempfile.mkdtemp(prefix="netdust-test-"))
    (tmp / "memory").mkdir()
    (tmp / "tasks").mkdir()
    return tmp


def test_decision_tag_written_to_state() -> tuple[bool, str]:
    tmp = _with_temp_cwd()
    try:
        transcript = _make_transcript(tmp, "DECISION: ship the new feature flag by Friday")
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"decision: hook exited {result.returncode}: {result.stderr[:200]}"

        state = (tmp / "memory" / "STATE.md").read_text()
        if "ship the new feature flag by Friday" not in state:
            return False, f"decision: tag not in STATE.md. Content: {state[:300]}"
        if "**Decisions**" not in state:
            return False, "decision: missing **Decisions** section header"
        return True, "DECISION: captured to STATE.md"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_risk_tag_written_to_state() -> tuple[bool, str]:
    tmp = _with_temp_cwd()
    try:
        transcript = _make_transcript(tmp, "RISK: the migration is destructive on rollback")
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"risk: hook exited {result.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        if "destructive on rollback" not in state:
            return False, f"risk: tag not in STATE.md. Content: {state[:300]}"
        if "**Risks**" not in state:
            return False, "risk: missing **Risks** section header"
        return True, "RISK: captured to STATE.md"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_lesson_tag_written_to_lessons() -> tuple[bool, str]:
    tmp = _with_temp_cwd()
    try:
        transcript = _make_transcript(tmp, "LESSON: always check the cache before flushing redis")
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"lesson: hook exited {result.returncode}"

        lessons = (tmp / "memory" / "lessons.md").read_text()
        if "check the cache before flushing redis" not in lessons:
            return False, f"lesson: tag not in lessons.md. Content: {lessons[:300]}"
        return True, "LESSON: captured to lessons.md"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_todo_tag_written_to_tasks() -> tuple[bool, str]:
    tmp = _with_temp_cwd()
    try:
        transcript = _make_transcript(tmp, "TODO: refactor the auth middleware next sprint")
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"todo: hook exited {result.returncode}"

        todo = (tmp / "tasks" / "todo.md").read_text()
        if "refactor the auth middleware next sprint" not in todo:
            return False, f"todo: tag not in todo.md. Content: {todo[:300]}"
        if "- [ ]" not in todo:
            return False, "todo: missing checkbox markdown"
        return True, "TODO: captured to tasks/todo.md"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_multiple_tags_in_one_session() -> tuple[bool, str]:
    """Realistic case: one session writes a decision, a risk, and a todo."""
    tmp = _with_temp_cwd()
    try:
        transcript = _make_transcript(
            tmp,
            "DECISION: use redis for queue backing\n"
            "RISK: redis eviction can drop in-flight jobs\n"
            "TODO: write reconciliation script before launch\n"
            "LESSON: don't run wp cache flush on prod without exclusions",
        )
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"multi: hook exited {result.returncode}"

        state = (tmp / "memory" / "STATE.md").read_text()
        lessons = (tmp / "memory" / "lessons.md").read_text()
        todo = (tmp / "tasks" / "todo.md").read_text()

        checks = [
            ("redis for queue backing" in state, "decision missing from STATE.md"),
            ("eviction can drop in-flight" in state, "risk missing from STATE.md"),
            ("reconciliation script before launch" in todo, "todo missing"),
            ("flush on prod without exclusions" in lessons, "lesson missing"),
        ]
        failures = [msg for ok, msg in checks if not ok]
        if failures:
            return False, "multi: " + "; ".join(failures)
        return True, "multi-tag session: all 4 tags routed to correct files"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_tags_writes_marker() -> tuple[bool, str]:
    """When no tags appear, the hook should still write a marker so the
    file timestamp updates and Stefan can see it ran. Audit found this
    was the visibility fix for the months-of-silent-failure bug."""
    tmp = _with_temp_cwd()
    try:
        transcript = _make_transcript(tmp, "Just an ordinary response with no tags at all.")
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"marker: hook exited {result.returncode}"

        state_path = tmp / "memory" / "STATE.md"
        if not state_path.exists():
            return False, "marker: STATE.md not created"

        content = state_path.read_text()
        if "session ended" not in content:
            return False, f"marker: expected 'session ended' marker. Got: {content[:200]}"
        return True, "no-tag session: visibility marker written"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_skill_edge_tag_routes_to_skill_lessons() -> tuple[bool, str]:
    """SKILL-EDGE: <skill>: <text> should land in the named skill's lessons.md.
    The audit specifically fixed this to glob all netdust-* plugins, not
    just netdust-wp. Verify it finds skills in any of the three plugins.

    Uses a real, currently-installed skill ('wp-security') so the test
    actually exercises the cross-plugin lookup. Cleans up its single line
    after."""
    tmp = _with_temp_cwd()
    skill = "wp-security"
    target = (
        Path.home()
        / ".claude" / "plugins" / "netdust-wp" / "skills" / skill / "lessons.md"
    )
    if not target.parent.exists():
        return True, f"skill-edge: skipped (skill {skill} not installed)"

    pre_existing = target.read_text() if target.exists() else ""

    try:
        marker = f"test-edge-{os.getpid()}"
        transcript = _make_transcript(
            tmp, f"SKILL-EDGE: {skill}: {marker} — synthetic test, safe to delete"
        )
        result = _run_hook(tmp, transcript)
        if result.returncode != 0:
            return False, f"skill-edge: hook exited {result.returncode}"

        if not target.exists():
            return False, f"skill-edge: {target} not created"

        post = target.read_text()
        if marker not in post:
            return False, f"skill-edge: marker '{marker}' not appended"

        return True, f"SKILL-EDGE: routed to {skill}/lessons.md"
    finally:
        # Restore the skill's lessons.md to its pre-test state
        if pre_existing or target.exists():
            target.write_text(pre_existing)
        shutil.rmtree(tmp, ignore_errors=True)


def run() -> list[tuple[bool, str]]:
    return [
        test_decision_tag_written_to_state(),
        test_risk_tag_written_to_state(),
        test_lesson_tag_written_to_lessons(),
        test_todo_tag_written_to_tasks(),
        test_multiple_tags_in_one_session(),
        test_no_tags_writes_marker(),
        test_skill_edge_tag_routes_to_skill_lessons(),
    ]
