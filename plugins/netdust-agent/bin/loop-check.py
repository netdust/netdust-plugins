#!/usr/bin/env python3
"""
loop-check.py — the loop ledger (netdust-agent)

Deterministic answer to "is Stage 2 finished?" for an armed harness loop,
derived ONLY from artifacts and exit codes — never from an agent asserting
"done". A tasks.md checkbox is agent-written testimony, so checked boxes
alone do NOT finish the loop: FINISHED additionally requires the machine
fact the SubagentStop hook recorded — the latest `suite-green` event in
<feature-dir>/run-log.jsonl, still CURRENT: no commit since its sha touched
a CODE path (testimony-seams P1a). Freshness is measured against
code-touching commits, not raw HEAD equality, so the controller's own
checkbox/ledger/docs commits never invalidate the green — a docs-only
commit after a green close does not buy an extra suite re-run. Sibling of
gate-check.py; consumed by hooks/loop-gate.py (and usable standalone by
/loop status, /shakeout, /evaluate).

    usage: loop-check.py <feature-dir>

    exit 0  FINISHED  — every task in tasks.md is checked AND the latest
                        suite-green trace event is current (no code-touching
                        commit since it); Stage 2 is complete. Stage 3
                        (shake-out) is deliberately OUT of loop scope: it is
                        designed around human judgment (manual sweep track,
                        manifest sign-off, deferral decisions), so the loop
                        disarms here and Stage 3 runs attended.
    exit 1  CONTINUE  — prints the next unit of work on stdout. With all
                        boxes checked but green evidence missing/stale, the
                        next unit is re-running the suite and closing out
                        green.
    exit 2  BLOCKED   — a human is needed: no/empty tasks.md (arming error),
                        or the next unchecked task carries a [HUMAN] marker.

Degradations (never crash the loop): an unreadable/corrupt run-log counts as
no evidence (fail toward CONTINUE); an undeterminable freshness range (green
sha unknown to git) also fails toward CONTINUE — never a false FINISHED; an
undeterminable HEAD (no git repo at all) accepts the green event — mirroring
run_gate_check's degrade-to-pass, so a broken git never traps a loop (the
dry-loop guardrail still bounds it).

stdout contract (line 1 is the reason; the progress line feeds the loop
gate's dry-iteration detection):

    LOOP: CONTINUE — next: T03 [Tier A] wire the adapter
    progress: done=2 total=7

Scope: v1 requires a machine-readable tasks.md. Class
C/D/E work is a single cycle — there is nothing to loop.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

GATE_CHECK = Path(__file__).resolve().parent / "gate-check.py"
RUN_LOG_NAME = "run-log.jsonl"

# Suffixes that do NOT count as code when judging green-evidence freshness —
# mirrors the subagent-stop hook's NON_CODE_SUFFIXES (plus .jsonl for the run
# log itself). A commit touching only these (checkbox ticks, ledger writes,
# memory/docs updates) leaves the last green verdict valid.
NON_CODE_SUFFIXES = (
    ".md", ".mdx", ".markdown", ".txt", ".rst",
    ".json", ".jsonl", ".yaml", ".yml", ".toml", ".csv",
    ".lock", ".log",
)

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


def latest_suite_green_sha(feature_dir: Path) -> str | None:
    """The sha of the NEWEST suite-green event in the feature's run log, or
    None when there is no log / no such event / the log is unreadable — all of
    which fail toward CONTINUE (missing evidence is never FINISHED). Corrupt
    lines are skipped, matching run-trace.py show's degradation."""
    log_path = feature_dir / RUN_LOG_NAME
    sha = None
    try:
        for raw in log_path.read_text().splitlines():
            raw = raw.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if not isinstance(entry, dict) or entry.get("event") != "suite-green":
                continue
            data = entry.get("data")
            sha = (data or {}).get("sha") if isinstance(data, dict) else None
    except Exception:
        return None  # unreadable trace → no evidence, fail toward CONTINUE
    return sha


def head_sha(feature_dir: Path) -> str | None:
    """git HEAD for the repo containing the feature dir, or None when it
    cannot be determined (no repo, no git, empty history)."""
    try:
        p = subprocess.run(
            ["git", "-C", str(feature_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        out = p.stdout.strip()
        return out if p.returncode == 0 and out else None
    except Exception:
        return None


def code_touched_since(feature_dir: Path, sha: str) -> bool | None:
    """True when any commit AFTER `sha` (i.e. in sha..HEAD) touched a CODE
    path — a path not ending in NON_CODE_SUFFIXES. False when every commit
    since was docs/tasks/ledger-only, which leaves the green evidence valid
    (the design-debt fix: the controller's own checkbox commits must not
    perpetually invalidate the green). None when the range is undeterminable
    (green sha unknown to this repo, git error) — the caller fails toward
    CONTINUE, never a false FINISHED."""
    try:
        p = subprocess.run(
            ["git", "-C", str(feature_dir), "log", "--format=", "--name-only",
             f"{sha}..HEAD"],
            capture_output=True, text=True, timeout=30,
        )
        if p.returncode != 0:
            return None
        return any(not ln.strip().lower().endswith(NON_CODE_SUFFIXES)
                   for ln in p.stdout.splitlines() if ln.strip())
    except Exception:
        return None


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
              "the loop needs a machine-readable tasks.md)")
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
        # All boxes checked — testimony. FINISHED additionally requires the
        # machine fact: the latest suite-green evidence still current (no
        # code-touching commit since its sha).
        green_sha = latest_suite_green_sha(feature_dir)
        head = head_sha(feature_dir)
        stale = False
        if green_sha is None:
            stale = True
        elif head is not None and green_sha != head:
            touched = code_touched_since(feature_dir, green_sha)
            stale = touched is not False  # True or None (undeterminable) → stale
        # head is None → accept the green event (documented degradation:
        # never trap a loop on broken/absent git; dry-loop guardrail bounds it)
        if stale:
            print("LOOP: CONTINUE — next: re-run the suite and close out "
                  "green (evidence stale/missing)")
            print(progress)
            return 1
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
