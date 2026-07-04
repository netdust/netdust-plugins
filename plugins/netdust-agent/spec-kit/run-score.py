#!/usr/bin/env python3
"""
run-score.py — the evaluator rubric compiler (netdust-agent)

    usage: run-score.py <feature-dir>

Compiles `<feature-dir>/run-log.jsonl` + `<feature-dir>/tasks.md` +
`<feature-dir>/plan.md` (for the `Loop budget: ~N` line) +
`gate-check.py --json <feature-dir>` (run live) into
`<feature-dir>/run-rubric.md` — a markdown rubric grading five dimensions
(seam integrity, cluster discipline, loop efficiency, yield discipline,
completion) with letter grades A/B/C/D/n/a derived mechanically from the
plan's documented thresholds table (specs/run-observability/plan.md):

  Dimension | A | B | C | D | n/a
  ---|---|---|---|---|---
  Seam integrity | gate-check-green traced before first execute/loop event
      | green verified only at scoring time | — | red/missing at scoring
      | —
  Cluster discipline | every declared cluster has a traced review-gate
      event with a stated tier | — | some clusters missing events
      | none traced | no clusters declared
  Loop efficiency | finished <= budget, 0 dry | <= budget, <=1 dry
      | budget exhausted before FINISHED with progress | disarmed dry
      (2-strike) | loop never armed
  Yield discipline | 0 unplanned yields | 1 unplanned | 2 unplanned
      | >=3 unplanned | no yields at all and no [HUMAN] tasks
  Completion | 100% checked | >=80% | >=50% | <50% | —

Denial path (mandatory, never fabricate grades): if `<feature-dir>/
run-log.jsonl` does not exist, OR exists but is empty, exit 0 with a
"no trace recorded" note and write NO run-rubric.md — even if tasks.md
shows 100% completion.

Exit codes: 0 success (including the no-trace denial path), 1 usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

LOG_NAME = "run-log.jsonl"
RUBRIC_NAME = "run-rubric.md"
GATE_CHECK = Path(__file__).resolve().parent / "gate-check.py"

TASK_RE = re.compile(r"^- \[( |x|X)\]\s+(T\d+)\b(.*)$")
CLUSTER_HEADING = re.compile(r"^###\s+Cluster\b\s*(\S+)", re.IGNORECASE)
BUDGET_RE = re.compile(r"Loop budget:\s*~?\s*(\d+)", re.IGNORECASE)

LOOP_EVENTS = {
    "loop-block", "loop-disarm-finished", "loop-disarm-budget",
    "loop-disarm-dry", "loop-yield-blocked", "loop-bypass",
}


# ── shared parsing (mirrors loop-check.py's parse_tasks fencing rule) ──────

def parse_tasks(tasks_md: str) -> list[dict]:
    """Task lines outside fenced code blocks. Same fencing rule as
    spec-kit/loop-check.py's parse_tasks — a fenced format-example line
    must never count as a real task."""
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


def parse_clusters(tasks_md: str) -> list[str]:
    """Return the list of declared cluster identifiers (e.g. 'C1'), parsed
    from `### Cluster <id> ...` headings, ignoring fenced blocks."""
    clusters = []
    in_fence = False
    for line in tasks_md.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = CLUSTER_HEADING.match(line)
        if m:
            clusters.append(m.group(1))
    return clusters


def read_log(log_path: Path) -> list[dict]:
    events = []
    for raw in log_path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            events.append(json.loads(raw))
        except json.JSONDecodeError:
            continue  # torn/corrupt line — skip, never crash scoring
    return events


def read_budget(plan_text: str | None) -> int | None:
    if not plan_text:
        return None
    m = BUDGET_RE.search(plan_text)
    return int(m.group(1)) if m else None


def run_gate_check(feature_dir: Path) -> dict:
    try:
        p = subprocess.run(
            [sys.executable, str(GATE_CHECK), "--json", str(feature_dir)],
            capture_output=True, text=True, timeout=60,
        )
        return json.loads(p.stdout)
    except Exception:
        return {"failed": True, "findings": []}


# ── dimension graders ───────────────────────────────────────────────────────

def grade_seam_integrity(events: list[dict], gate_result: dict) -> str:
    first_execute_or_loop_idx = None
    green_idx = None
    for i, e in enumerate(events):
        name = e.get("event", "")
        if name == "gate-check-green" and green_idx is None:
            green_idx = i
        if first_execute_or_loop_idx is None and (
            name == "stage-enter" or name in LOOP_EVENTS
        ):
            first_execute_or_loop_idx = i

    if green_idx is not None and (
        first_execute_or_loop_idx is None or green_idx < first_execute_or_loop_idx
    ):
        return "A"

    if gate_result.get("failed"):
        return "D"
    return "B"


def grade_cluster_discipline(clusters: list[str], events: list[dict]) -> str:
    if not clusters:
        return "n/a"

    traced = {}
    for e in events:
        if e.get("event") == "review-gate":
            data = e.get("data", {})
            cluster = data.get("cluster")
            tier = data.get("tier")
            if cluster and tier:
                traced[cluster] = tier

    covered = [c for c in clusters if c in traced]
    if not covered:
        return "D"
    if len(covered) == len(clusters):
        return "A"
    return "C"


def grade_loop_efficiency(events: list[dict], budget: int | None) -> str:
    loop_events = [e for e in events if e.get("event") in LOOP_EVENTS]
    if not loop_events:
        return "n/a"

    names = [e.get("event") for e in loop_events]
    dry_count = names.count("loop-disarm-dry")
    finished = "loop-disarm-finished" in names
    budget_exhausted = "loop-disarm-budget" in names

    if finished:
        if dry_count == 0:
            return "A"
        if dry_count <= 1:
            return "B"
        return "D"

    if budget_exhausted:
        has_progress = any(e.get("event") == "loop-block" for e in loop_events)
        if has_progress:
            return "C"
        return "D"

    if dry_count > 0:
        return "D"

    # loop armed (events exist) but neither finished nor budget-exhausted nor
    # dry-disarmed — still in-flight; treat as no evidence of a completed
    # efficiency story yet, closest to budget-exhaustion-with-progress.
    has_progress = any(e.get("event") == "loop-block" for e in loop_events)
    return "C" if has_progress else "D"


HUMAN_TASK_ID_RE = re.compile(r"\b(T\d+)\b")


def grade_yield_discipline(events: list[dict], tasks: list[dict]) -> str:
    human_ids = {t["id"] for t in tasks if t["human"]}
    yields = [e for e in events if e.get("event") == "loop-yield-blocked"]

    if not yields:
        return "n/a" if not human_ids else "A"

    unplanned = 0
    for e in yields:
        reason = e.get("data", {}).get("reason", "")
        m = HUMAN_TASK_ID_RE.search(reason)
        task_id = m.group(1) if m else None
        if task_id not in human_ids:
            unplanned += 1

    if unplanned == 0:
        return "A"
    if unplanned == 1:
        return "B"
    if unplanned == 2:
        return "C"
    return "D"


def grade_completion(tasks: list[dict]) -> str:
    if not tasks:
        return "D"
    done = sum(1 for t in tasks if t["done"])
    pct = (done / len(tasks)) * 100
    if pct >= 100:
        return "A"
    if pct >= 80:
        return "B"
    if pct >= 50:
        return "C"
    return "D"


# ── rubric rendering ─────────────────────────────────────────────────────────

def render_rubric(grades: dict[str, str]) -> str:
    lines = [
        "# Run rubric",
        "",
        "| Dimension | Grade |",
        "|---|---|",
    ]
    for dim in (
        "Seam integrity", "Cluster discipline", "Loop efficiency",
        "Yield discipline", "Completion",
    ):
        lines.append(f"| {dim} | {grades[dim]} |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description="run-score.py — compile the per-feature run log + tasks.md "
                     "+ plan.md + gate-check verdict into a graded run-rubric.md")
    ap.add_argument("feature_dir", type=Path)
    args = ap.parse_args(argv)

    feature_dir: Path = args.feature_dir
    log_path = feature_dir / LOG_NAME

    if not log_path.exists():
        print("no trace recorded")
        return 0

    events = read_log(log_path)
    if not events:
        print("no trace recorded")
        return 0

    tasks_path = feature_dir / "tasks.md"
    tasks_text = tasks_path.read_text(encoding="utf-8") if tasks_path.exists() else ""
    plan_path = feature_dir / "plan.md"
    plan_text = plan_path.read_text(encoding="utf-8") if plan_path.exists() else None

    tasks = parse_tasks(tasks_text)
    clusters = parse_clusters(tasks_text)
    budget = read_budget(plan_text)
    gate_result = run_gate_check(feature_dir)

    grades = {
        "Seam integrity": grade_seam_integrity(events, gate_result),
        "Cluster discipline": grade_cluster_discipline(clusters, events),
        "Loop efficiency": grade_loop_efficiency(events, budget),
        "Yield discipline": grade_yield_discipline(events, tasks),
        "Completion": grade_completion(tasks),
    }

    rubric_path = feature_dir / RUBRIC_NAME
    rubric_path.write_text(render_rubric(grades), encoding="utf-8")
    print(f"wrote {rubric_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
