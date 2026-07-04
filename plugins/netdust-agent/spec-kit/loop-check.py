#!/usr/bin/env python3
"""
loop-check.py — the loop ledger (netdust-agent)

Deterministic answer to "is Stage 2 finished?" for an armed harness loop,
derived ONLY from artifacts and exit codes — never from an agent asserting
"done". Sibling of gate-check.py; consumed by hooks/loop-gate.py (and usable
standalone by /loop status, /shakeout, /evaluate).

    usage: loop-check.py <feature-dir>

    exit 0  FINISHED  — every task in tasks.md is checked; Stage 2 is complete.
                        Stage 3 (shake-out) is deliberately OUT of loop scope:
                        it is designed around human judgment (manual sweep
                        track, manifest sign-off, deferral decisions), so the
                        loop disarms here and Stage 3 runs attended.
    exit 1  CONTINUE  — prints the next unit of work on stdout.
    exit 2  BLOCKED   — a human is needed: no/empty tasks.md (arming error),
                        or the next unchecked task carries a [HUMAN] marker.

stdout contract (line 1 is the reason; the progress line feeds the loop
gate's dry-iteration detection):

    LOOP: CONTINUE — next: T03 [Tier A] wire the adapter
    progress: done=2 total=7

Scope: v1 requires the spec-kit graft (a machine-readable tasks.md). Class
C/D/E work is a single cycle — there is nothing to loop.
"""

import re
import subprocess
import sys
from pathlib import Path

GATE_CHECK = Path(__file__).resolve().parent / "gate-check.py"

TASK_RE = re.compile(r"^- \[( |x|X)\] (T\d+)\b(.*)$")


def parse_tasks(tasks_md: str) -> list[dict]:
    """Task lines outside fenced code blocks (the template's format examples
    live inside fences and must not count as work)."""
    tasks = []
    in_fence = False
    for line in tasks_md.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = TASK_RE.match(line)
        if m:
            tasks.append({
                "done": m.group(1).lower() == "x",
                "id": m.group(2),
                "text": (m.group(2) + m.group(3)).strip(),
                "human": "[HUMAN]" in line,
            })
    return tasks


def run_gate_check(feature_dir: Path) -> tuple[int, str]:
    """gate-check green is part of not-finished-yet hygiene: plan artifacts
    that regressed mid-loop are the next unit of work. Degrades to pass if
    the script is absent (partial install)."""
    if not GATE_CHECK.exists():
        return 0, ""
    try:
        p = subprocess.run(
            [sys.executable, str(GATE_CHECK), str(feature_dir)],
            capture_output=True, text=True, timeout=60,
        )
        fails = [l.strip() for l in p.stdout.splitlines() if "FAIL" in l][:3]
        return p.returncode, "; ".join(fails)
    except Exception as e:  # fail toward CONTINUE-able, never crash the loop
        return 0, f"gate-check unavailable ({type(e).__name__})"


def main() -> int:
    if len(sys.argv) != 2:
        print("LOOP: BLOCKED — usage: loop-check.py <feature-dir>")
        return 2

    feature_dir = Path(sys.argv[1])
    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.exists():
        print(f"LOOP: BLOCKED — no tasks.md in {feature_dir} (arming error: "
              "the loop needs the spec-kit graft's machine-readable task list)")
        return 2

    tasks = parse_tasks(tasks_path.read_text())
    if not tasks:
        print(f"LOOP: BLOCKED — tasks.md has no `- [ ] Tnn` task lines")
        return 2

    done = sum(1 for t in tasks if t["done"])
    progress = f"progress: done={done} total={len(tasks)}"

    gate_rc, gate_why = run_gate_check(feature_dir)
    if gate_rc != 0:
        print(f"LOOP: CONTINUE — plan artifacts regressed, fix them first "
              f"(gate-check FAIL: {gate_why})")
        print(progress)
        return 1

    nxt = next((t for t in tasks if not t["done"]), None)
    if nxt is None:
        print("LOOP: FINISHED — all tasks complete; disarm and run Stage 3 "
              "(/shakeout) attended")
        print(progress)
        return 0

    if nxt["human"]:
        print(f"LOOP: BLOCKED — next task is human-only: {nxt['text']}")
        print(progress)
        return 2

    print(f"LOOP: CONTINUE — next: {nxt['text']}")
    print(progress)
    return 1


if __name__ == "__main__":
    sys.exit(main())
