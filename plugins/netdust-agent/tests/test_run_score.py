"""Tests for spec-kit/run-score.py — the evaluator rubric compiler.

Contract (specs/run-observability/spec.md FR-4/FR-5, plan.md's thresholds
table, tasks.md T04):

  run-score.py <feature-dir> compiles
      <feature-dir>/run-log.jsonl
    + <feature-dir>/tasks.md
    + <feature-dir>/plan.md (for the `Loop budget: ~N` line)
    + `gate-check.py --json <feature-dir>` (run live)
  into <feature-dir>/run-rubric.md — a markdown rubric with letter grades
  (A/B/C/D/n/a) for five dimensions, graded EXACTLY per the plan's
  threshold table (see module docstring for the table restated below).

  Dimension | A | B | C | D | n/a
  ---|---|---|---|---|---
  Seam integrity | gate-check-green traced before first execute/loop event
      | green verified only at scoring time | — | red/missing at scoring | —
  Cluster discipline | every declared cluster has a traced review-gate
      event with a stated tier | — | some clusters missing events
      | none traced | no clusters declared
  Loop efficiency | finished <= budget, 0 dry | <= budget, <=1 dry
      | budget exhausted before FINISHED with progress | disarmed dry
      (2-strike) | loop never armed
  Yield discipline | 0 unplanned yields | 1 unplanned | 2 unplanned
      | >=3 unplanned | no yields at all and no [HUMAN] tasks
  Completion | 100% checked | >=80% | >=50% | <50% | —

  Denial path (mandatory, never fabricate grades): missing run-log.jsonl
  -> exit 0, "no trace recorded" note, NO run-rubric.md written.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

RUN_SCORE = Path(__file__).resolve().parent.parent / "spec-kit" / "run-score.py"


def run_score(feature_dir: Path) -> tuple[int, str, str]:
    p = subprocess.run(
        [sys.executable, str(RUN_SCORE), str(feature_dir)],
        capture_output=True, text=True, timeout=60,
    )
    return p.returncode, p.stdout, p.stderr


def rubric_path(feature_dir: Path) -> Path:
    return feature_dir / "run-rubric.md"


def rubric_text(feature_dir: Path) -> str | None:
    p = rubric_path(feature_dir)
    return p.read_text() if p.exists() else None


def write_log(feature_dir: Path, events: list[tuple[str, dict]]) -> None:
    lines = []
    for i, (event, data) in enumerate(events):
        lines.append(json.dumps({
            "ts": f"2026-07-04T00:00:{i:02d}+00:00",
            "event": event,
            "data": data,
        }))
    (feature_dir / "run-log.jsonl").write_text("\n".join(lines) + "\n")


# ── tasks.md fixture builders ────────────────────────────────────────────

def tasks_md(clusters: list[tuple[str, list[str]]]) -> str:
    """Build a minimal tasks.md. `clusters` is [(cluster_heading_suffix, [task_lines])].
    Each task_line's FIRST CHARACTER is the box content ('x' checked, ' ' unchecked),
    followed by a single space then the rest of the task text, e.g.
    'x T01 [Tier A] first  (files: a.py)' or ' T02 [HUMAN] [Tier B] wait'."""
    out = ["# Tasks: demo\n"]
    for suffix, task_lines in clusters:
        out.append(f"### Cluster {suffix}\n")
        for tl in task_lines:
            box, rest = tl[0], tl[1:].lstrip(" ")
            out.append(f"- [{box}] {rest}\n")
        out.append("\n")
    return "".join(out)


ALL_DONE_ONE_CLUSTER = tasks_md([
    ("C1  (2 tasks)", [
        "x T01 [Tier A] first  (files: a.py)",
        "x T02 [Tier B] second  (files: b.py)",
    ]),
])

TWO_CLUSTERS_ALL_DONE = tasks_md([
    ("C1  (1 tasks)", ["x T01 [Tier A] first  (files: a.py)"]),
    ("C2  (1 tasks)", ["x T02 [Tier A] second  (files: b.py)"]),
])

NO_CLUSTERS_ALL_DONE = (
    "# Tasks: demo\n\n"
    "- [x] T01 [Tier A] first  (files: a.py)\n"
    "- [x] T02 [Tier B] second  (files: b.py)\n"
)

ONE_HUMAN_TASK = tasks_md([
    ("C1  (2 tasks)", [
        "x T01 [Tier A] first  (files: a.py)",
        " T02 [HUMAN] [Tier A] approve teardown  (files: c.py)",
    ]),
])


def completion_tasks(done: int, total: int) -> str:
    lines = []
    for i in range(1, total + 1):
        box = "x" if i <= done else " "
        lines.append(f"{box} T{i:02d} [Tier A] task {i}  (files: f{i}.py)")
    return tasks_md([("C1  (%d tasks)" % total, lines)])


PLAN_BUDGET_10 = "# Plan\n\nLoop budget: ~10 iterations — some tasks.\n"

# A plan.md carrying all 5 of gate-check.py's REQUIRED_PLAN_GATES headings
# (Constitution check, Threat model, Architecture invariants touched,
# Spec-premise ground-truth, Phases & review clusters), each with enough
# body that check_plan_gates()'s section_body() finds non-empty content —
# PLUS the `Loop budget: ~10 iterations` line the loop-efficiency dimension
# reads. No spec.md is written alongside it in these fixtures, so
# check_threat_model()'s spec_security_triggered() always returns []; an
# explicit N/A threat-model body is therefore safe and never fails that check.
PLAN_GATES_CLEAN = (
    "# Plan\n\n"
    "Loop budget: ~10 iterations — some tasks.\n\n"
    "## Constitution check  [GATE]\n\n"
    "- [x] No non-negotiable violated.\n\n"
    "## Threat model  [GATE]\n\n"
    "N/A — no 1a-trigger surface (fixture: same-repo harness artifacts only).\n\n"
    "## Architecture invariants touched  [GATE]\n\n"
    "N/A — no ARCHITECTURE-INVARIANTS.md in this fixture repo.\n\n"
    "## Spec-premise ground-truth  [GATE]\n\n"
    "N/A — no reuse premise for this fixture.\n\n"
    "## Phases & review clusters  [GATE]\n\n"
    "| Phase | Cluster | Tasks | Integration gate | Extra gate |\n"
    "|---|---|---|---|---|\n"
    "| P1 | C1 | T01-T02 (2) | suite green | — |\n"
)


def make_feature(tmp: str, tasks: str, plan: str = PLAN_BUDGET_10,
                  spec_extra: bool = True) -> Path:
    """A feature dir with a tasks.md + a minimal plan.md (NOT gate-check-clean
    by default — the default PLAN_BUDGET_10 plan.md fails gate-check.py's
    plan-gate-heading check on all 5 required [GATE] sections; use
    plan=PLAN_GATES_CLEAN when a case needs a live `gate-check.py --json`
    PASS). When spec_extra is False, the dir has NO spec/plan/tasks at all
    beyond what's given — used to force a gate-check FAIL for the D case."""
    d = Path(tmp) / "specs" / "demo"
    d.mkdir(parents=True)
    (d / "tasks.md").write_text(tasks)
    (d / "plan.md").write_text(plan)
    return d


def run() -> list[tuple[bool, str]]:
    results = []

    def case(desc, passed):
        results.append((passed, desc))

    # ── Denial path: missing run-log.jsonl ──────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)
        # deliberately no run-log.jsonl written
        rc, out, err = run_score(feature)
        case("missing run-log.jsonl -> exit 0", rc == 0)
        case("missing run-log.jsonl -> 'no trace recorded' message",
             "no trace recorded" in (out + err).lower())
        case("missing run-log.jsonl -> NO run-rubric.md written",
             not rubric_path(feature).exists())

    # ── Denial path, reinforced: 100% completion tasks.md does NOT excuse
    # a missing run-log — the whole compile requires a real run-log. ──────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(5, 5))
        rc, out, err = run_score(feature)
        case("100% complete tasks.md but no run-log -> still no rubric",
             rc == 0 and not rubric_path(feature).exists())

    # ── Denial path: empty run-log.jsonl (present but empty) also must not
    # fabricate a rubric — treated the same as absent by the documented
    # contract (never fabricate from absent/empty data). ──────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)
        (feature / "run-log.jsonl").write_text("")
        rc, out, err = run_score(feature)
        case("empty run-log.jsonl -> exit 0, no rubric fabricated",
             rc == 0 and not rubric_path(feature).exists())

    # ── Seam integrity: A — gate-check-green traced before first
    # execute/loop event ─────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)
        write_log(feature, [
            ("gate-check-green", {}),
            ("stage-enter", {"stage": "execute"}),
            ("review-gate", {"cluster": "C1", "tier": "STANDARD"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("seam integrity A: gate-check-green traced before first stage/loop event",
             rc == 0 and text is not None
             and _dimension_grade(text, "Seam integrity") == "A")

    # ── Seam integrity: B — green verified only at scoring time (no traced
    # gate-check-green event at all, but a live gate-check --json says
    # failed: false) ─────────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER, plan=PLAN_GATES_CLEAN)
        write_log(feature, [
            ("stage-enter", {"stage": "execute"}),
            ("review-gate", {"cluster": "C1", "tier": "STANDARD"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("seam integrity B: green only at scoring time (no traced event)",
             rc == 0 and text is not None
             and _dimension_grade(text, "Seam integrity") == "B")

    # ── Seam integrity: D — gate-check --json reports failed: true at
    # scoring time (tasks.md missing Tier markers -> task-tier FAIL) ──────
    with tempfile.TemporaryDirectory() as tmp:
        broken_tasks = "# Tasks: demo\n\n### Cluster C1  (1 tasks)\n- [ ] T01 no tier marker here\n"
        feature = make_feature(tmp, broken_tasks)
        write_log(feature, [
            ("stage-enter", {"stage": "execute"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("seam integrity D: gate-check --json failed:true at scoring time",
             rc == 0 and text is not None
             and _dimension_grade(text, "Seam integrity") == "D")

    # ── Cluster discipline: A — every declared cluster has a review-gate
    # event with a tier ──────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, TWO_CLUSTERS_ALL_DONE)
        write_log(feature, [
            ("review-gate", {"cluster": "C1", "tier": "STANDARD"}),
            ("review-gate", {"cluster": "C2", "tier": "STANDARD"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("cluster discipline A: all declared clusters traced with tier",
             rc == 0 and text is not None
             and _dimension_grade(text, "Cluster discipline") == "A")

    # ── Cluster discipline: C — some clusters missing events ─────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, TWO_CLUSTERS_ALL_DONE)
        write_log(feature, [
            ("review-gate", {"cluster": "C1", "tier": "STANDARD"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("cluster discipline C: some clusters traced, some missing",
             rc == 0 and text is not None
             and _dimension_grade(text, "Cluster discipline") == "C")

    # ── Cluster discipline: D — none traced despite clusters existing ────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, TWO_CLUSTERS_ALL_DONE)
        write_log(feature, [
            ("stage-enter", {"stage": "execute"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("cluster discipline D: clusters declared, zero review-gate events traced",
             rc == 0 and text is not None
             and _dimension_grade(text, "Cluster discipline") == "D")

    # ── Cluster discipline: n/a — zero `### Cluster` headings declared ────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, NO_CLUSTERS_ALL_DONE)
        write_log(feature, [
            ("stage-enter", {"stage": "execute"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("cluster discipline n/a: zero clusters declared in tasks.md",
             rc == 0 and text is not None
             and _dimension_grade(text, "Cluster discipline") == "n/a")

    # ── Loop efficiency: A — finished, under budget (10), 0 dry stops ─────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER, plan=PLAN_BUDGET_10)
        events = [("loop-block", {"iteration": str(i), "done": str(i - 1),
                                   "total": "10", "reason": "x"}) for i in range(1, 4)]
        events.append(("loop-disarm-finished", {"iteration": "4"}))
        write_log(feature, events)
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("loop efficiency A: finished under budget, 0 dry-disarms",
             rc == 0 and text is not None
             and _dimension_grade(text, "Loop efficiency") == "A")

    # ── Loop efficiency: B — finished, under budget, exactly 1 dry-disarm
    # event somewhere in the (longer) run before eventually finishing ─────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER, plan=PLAN_BUDGET_10)
        events = [("loop-block", {"iteration": str(i), "done": "0",
                                   "total": "10", "reason": "x"}) for i in range(1, 3)]
        events.append(("loop-disarm-dry", {"iteration": "2", "done": "0"}))
        events.append(("loop-block", {"iteration": "3", "done": "1",
                                       "total": "10", "reason": "x"}))
        events.append(("loop-disarm-finished", {"iteration": "4"}))
        write_log(feature, events)
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("loop efficiency B: finished under budget with exactly 1 dry-disarm",
             rc == 0 and text is not None
             and _dimension_grade(text, "Loop efficiency") == "B")

    # ── Loop efficiency: C — budget exceeded before FINISHED, but there IS
    # progress (loop-block events exist, no disarm-finished, no dry) ──────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(2, 5), plan=PLAN_BUDGET_10)
        events = [("loop-block", {"iteration": str(i), "done": "1",
                                   "total": "10", "reason": "x"}) for i in range(1, 13)]
        events.append(("loop-disarm-budget", {"iteration": "13", "max_iterations": "10"}))
        write_log(feature, events)
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("loop efficiency C: budget exhausted before FINISHED, with progress",
             rc == 0 and text is not None
             and _dimension_grade(text, "Loop efficiency") == "C")

    # ── Loop efficiency: D — a loop-disarm-dry event exists (2-strike dry
    # disarm actually fired; run never subsequently finished) ─────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(1, 5), plan=PLAN_BUDGET_10)
        events = [("loop-block", {"iteration": "1", "done": "0",
                                   "total": "10", "reason": "x"}),
                  ("loop-disarm-dry", {"iteration": "2", "done": "0"})]
        write_log(feature, events)
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("loop efficiency D: loop-disarm-dry event present (2-strike fired)",
             rc == 0 and text is not None
             and _dimension_grade(text, "Loop efficiency") == "D")

    # ── Loop efficiency: finished but OVER budget (Finding 1, C2 review) —
    # 15 loop-block events (iteration 1..15) then loop-disarm-finished, 0 dry
    # stops, budget=10. Reviewers confirmed grade_loop_efficiency's `finished`
    # branch never consulted budget at all, so this graded "A" before the
    # fix (finished + 0 dry => A) despite blowing the budget by 5 iterations.
    # Per the fix, finishing over budget must never grade A or B — it falls
    # through to the same in-flight C/D bucket (C here: loop-block progress
    # evidence exists). ───────────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(5, 5), plan=PLAN_BUDGET_10)
        events = [("loop-block", {"iteration": str(i), "done": "1",
                                   "total": "10", "reason": "x"}) for i in range(1, 16)]
        events.append(("loop-disarm-finished", {"iteration": "16"}))
        write_log(feature, events)
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        grade = _dimension_grade(text, "Loop efficiency") if text is not None else None
        case("loop efficiency: finished but OVER budget must NOT grade A or B",
             rc == 0 and grade not in ("A", "B"))
        case("loop efficiency: finished over budget with loop-block progress grades C",
             rc == 0 and grade == "C")

    # ── Loop efficiency: n/a — no loop-armed/loop-* events at all ─────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER, plan=PLAN_BUDGET_10)
        write_log(feature, [
            ("stage-enter", {"stage": "execute"}),
            ("review-gate", {"cluster": "C1", "tier": "STANDARD"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("loop efficiency n/a: loop never armed (no loop-* events)",
             rc == 0 and text is not None
             and _dimension_grade(text, "Loop efficiency") == "n/a")

    # ── Yield discipline: A — 0 unplanned yields (a [HUMAN] task exists so
    # yielding was possible, but the run log shows no yield event at all) ──
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ONE_HUMAN_TASK)
        write_log(feature, [
            ("stage-enter", {"stage": "execute"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("yield discipline A: 0 unplanned yields (a [HUMAN] task exists but no yield fired)",
             rc == 0 and text is not None
             and _dimension_grade(text, "Yield discipline") == "A")

    # ── Yield discipline: B — 1 unplanned yield (BLOCKED without a
    # [HUMAN] task in tasks.md) ────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)  # no [HUMAN] tasks
        write_log(feature, [
            ("loop-yield-blocked", {"iteration": "1",
                                     "reason": "LOOP: BLOCKED — next task is human-only: T02 do a thing"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("yield discipline B: 1 unplanned yield",
             rc == 0 and text is not None
             and _dimension_grade(text, "Yield discipline") == "B")

    # ── Yield discipline: C — exactly 2 unplanned yields (Finding 2, C2
    # review) — no [HUMAN] tasks in tasks.md so both loop-yield-blocked
    # events are unplanned. This is the only defined grade boundary in the
    # whole rubric with zero fixture coverage before this fix. ────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)  # no [HUMAN] tasks
        events = [("loop-yield-blocked",
                    {"iteration": str(i),
                     "reason": "LOOP: BLOCKED — next task is human-only: T02 do a thing"})
                   for i in range(1, 3)]
        write_log(feature, events)
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("yield discipline C: exactly 2 unplanned yields",
             rc == 0 and text is not None
             and _dimension_grade(text, "Yield discipline") == "C")

    # ── Yield discipline: D — >=3 unplanned yields ────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)  # no [HUMAN] tasks
        events = [("loop-yield-blocked",
                    {"iteration": str(i),
                     "reason": "LOOP: BLOCKED — next task is human-only: T02 do a thing"})
                   for i in range(1, 4)]
        write_log(feature, events)
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("yield discipline D: 3 unplanned yields",
             rc == 0 and text is not None
             and _dimension_grade(text, "Yield discipline") == "D")

    # ── Yield discipline: planned yield (tied to a real [HUMAN] task) does
    # NOT count as unplanned -> should grade A despite a yield event ──────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ONE_HUMAN_TASK)
        write_log(feature, [
            ("loop-yield-blocked", {"iteration": "1",
                                     "reason": "LOOP: BLOCKED — next task is human-only: T02 [HUMAN] [Tier A] approve teardown"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("yield discipline: a yield tied to a real [HUMAN] task is planned, not unplanned",
             rc == 0 and text is not None
             and _dimension_grade(text, "Yield discipline") == "A")

    # ── Yield discipline: n/a — zero yields AND zero [HUMAN] tasks ───────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)  # no [HUMAN] tasks, no yields
        write_log(feature, [
            ("stage-enter", {"stage": "execute"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("yield discipline n/a: no yields and no [HUMAN] tasks declared",
             rc == 0 and text is not None
             and _dimension_grade(text, "Yield discipline") == "n/a")

    # ── Completion: A — 100% checked ──────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(5, 5))
        write_log(feature, [("stage-enter", {"stage": "execute"})])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("completion A: 100% tasks checked",
             rc == 0 and text is not None
             and _dimension_grade(text, "Completion") == "A")

    # ── Completion: B — >=80% ─────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(4, 5))  # 80%
        write_log(feature, [("stage-enter", {"stage": "execute"})])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("completion B: 80% tasks checked",
             rc == 0 and text is not None
             and _dimension_grade(text, "Completion") == "B")

    # ── Completion: C — >=50% ─────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(2, 4))  # 50%
        write_log(feature, [("stage-enter", {"stage": "execute"})])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("completion C: 50% tasks checked",
             rc == 0 and text is not None
             and _dimension_grade(text, "Completion") == "C")

    # ── Completion: D — <50% ───────────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, completion_tasks(1, 5))  # 20%
        write_log(feature, [("stage-enter", {"stage": "execute"})])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("completion D: 20% tasks checked",
             rc == 0 and text is not None
             and _dimension_grade(text, "Completion") == "D")

    # ── Completion: fenced example task lines must not be counted (same
    # fencing rule as loop-check.py's parse_tasks) ────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        fenced = completion_tasks(2, 2) + (
            "\n```\n- [ ] T99 [Tier A] never counted — lives in a fence\n```\n"
        )
        feature = make_feature(tmp, fenced)
        write_log(feature, [("stage-enter", {"stage": "execute"})])
        rc, out, err = run_score(feature)
        text = rubric_text(feature)
        case("completion: fenced example task lines are excluded from the tally",
             rc == 0 and text is not None
             and _dimension_grade(text, "Completion") == "A")

    # ── Full rubric shape sanity: all five dimension headers present ─────
    with tempfile.TemporaryDirectory() as tmp:
        feature = make_feature(tmp, ALL_DONE_ONE_CLUSTER)
        write_log(feature, [
            ("gate-check-green", {}),
            ("stage-enter", {"stage": "execute"}),
            ("review-gate", {"cluster": "C1", "tier": "STANDARD"}),
        ])
        rc, out, err = run_score(feature)
        text = rubric_text(feature) or ""
        case("rubric mentions all five dimensions",
             all(dim in text for dim in (
                 "Seam integrity", "Cluster discipline", "Loop efficiency",
                 "Yield discipline", "Completion")))

    return results


def _dimension_grade(rubric_text: str, dimension: str) -> str | None:
    """Extract the letter grade recorded for `dimension` from the rendered
    run-rubric.md. Tolerant of either a markdown table row
    (`| Seam integrity | A | ... |`) or a simple `Seam integrity: A` line —
    the compiler's exact rendering is an implementation detail; the test
    only requires the dimension name and its graded letter to appear
    together, unambiguously, on the same line."""
    import re
    for line in rubric_text.splitlines():
        if dimension in line:
            m = re.search(r"\b(A|B|C|D|n/a)\b", line.split(dimension, 1)[1])
            if m:
                return m.group(1)
    return None
