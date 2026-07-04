#!/usr/bin/env python3
"""
loop-gate.py — netdust-agent harness

Stop hook: the loop driver. When a feature loop is ARMED (marker file
tasks/.harness-loop.json exists, written by /loop), this hook runs
spec-kit/loop-check.py at every session stop and BLOCKS the stop while
Stage 2 is unfinished — the exact mechanism subagent-stop.py uses on
subagents, one level up. No marker → no-op (zero cost for every normal
session).

Token cost of the loop itself: ~zero. The gate is deterministic Python;
the only context it ever adds is the 2-line block reason.

Decision table (marker present, stop_hook_active false):
  loop-check exit 0 (FINISHED) → disarm (delete marker), allow stop.
  loop-check exit 2 (BLOCKED)  → allow stop, KEEP marker — the agent has
                                 already surfaced the human question in its
                                 transcript; when the human answers and work
                                 resumes, the loop re-engages at next stop.
  loop-check exit 1 (CONTINUE) → block with the next unit, UNLESS a
                                 guardrail disarms first:
    • iteration >= max_iterations           → disarm, allow (budget spent)
    • done-count unchanged 2 stops in a row → disarm, allow (dry loop)

Guardrails that always win: stop_hook_active bypass (one block per stop
cycle), marker deletion by the human, and fail-open — any internal error
allows the stop. Logs to ~/.claude/logs/memory-hook.log.

Marker schema (tasks/.harness-loop.json — runtime state, gitignored by /loop):
  {"feature_dir": "specs/<feature>", "iteration": 0, "max_iterations": 25,
   "last_done": 0, "dry": 0}
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

LOG_PATH = Path.home() / ".claude" / "logs" / "memory-hook.log"
LOOP_CHECK = Path(__file__).resolve().parent.parent / "spec-kit" / "loop-check.py"
MARKER_REL = Path("tasks") / ".harness-loop.json"
DEFAULT_MAX_ITERATIONS = 25
MAX_DRY = 2


def log(msg: str) -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_PATH, "a") as f:
            f.write(f"[{ts}] loop-gate: {msg}\n")
    except Exception:
        pass


def read_progress(stdout: str) -> int | None:
    for line in stdout.splitlines():
        if line.startswith("progress: done="):
            try:
                return int(line.split("done=")[1].split()[0])
            except (IndexError, ValueError):
                return None
    return None


def main() -> None:
    raw = sys.stdin.read()
    hook_input = json.loads(raw) if raw.strip() else {}

    cwd = Path(hook_input.get("cwd") or Path.cwd())
    marker_path = cwd / MARKER_REL
    if not marker_path.exists():
        return  # not armed — the common case, exit silently

    if hook_input.get("stop_hook_active"):
        log(f"bypass stop_hook_active cwd={cwd}")
        return

    marker = json.loads(marker_path.read_text())
    feature_dir = cwd / marker.get("feature_dir", "")
    max_iter = int(marker.get("max_iterations", DEFAULT_MAX_ITERATIONS))
    iteration = int(marker.get("iteration", 0))

    check = subprocess.run(
        [sys.executable, str(LOOP_CHECK), str(feature_dir)],
        capture_output=True, text=True, timeout=120, cwd=str(cwd),
    )
    reason = (check.stdout.splitlines() or ["LOOP: no output"])[0]

    if check.returncode == 0:
        marker_path.unlink(missing_ok=True)
        log(f"disarm reason=finished iter={iteration} cwd={cwd}")
        return

    if check.returncode == 2:
        log(f"yield reason=blocked iter={iteration} detail={reason!r}")
        return  # human's turn; marker stays armed for when work resumes

    # CONTINUE — apply guardrails, then block the stop.
    iteration += 1
    if iteration > max_iter:
        marker_path.unlink(missing_ok=True)
        log(f"disarm reason=budget-exhausted iter={iteration} max={max_iter}")
        return

    done = read_progress(check.stdout)
    if done is not None:
        if done <= int(marker.get("last_done", -1)):
            marker["dry"] = int(marker.get("dry", 0)) + 1
        else:
            marker["dry"] = 0
        marker["last_done"] = done
        if marker["dry"] >= MAX_DRY:
            marker_path.unlink(missing_ok=True)
            log(f"disarm reason=dry-loop iter={iteration} done={done}")
            return

    marker["iteration"] = iteration
    marker_path.write_text(json.dumps(marker))

    log(f"block iter={iteration}/{max_iter} done={done} detail={reason!r}")
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"{reason} [harness loop {iteration}/{max_iter}] Rebuild state "
            "from tasks.md + the plan (never from scrollback), dispatch the "
            "next unit per building Stage 2, and HALT at "
            "── REVIEW GATE ── markers as normal. To stop the loop, delete "
            f"{MARKER_REL}."
        ),
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Fail OPEN: a broken gate must never trap a session.
        log(f"unhandled-exception err={type(e).__name__}:{e} (failing open)")
    sys.exit(0)
