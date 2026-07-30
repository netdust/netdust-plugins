"""Tests for bin/loop-check.py — the loop ledger."""

import subprocess
import sys
import tempfile
from pathlib import Path

LOOP_CHECK = Path(__file__).resolve().parent.parent / "bin" / "loop-check.py"

TIERED = """# Tasks: demo

## Phase 1

### Cluster C1
- [{t1}] T01 [Tier A] first task  (files: a.py)
      Unit test: contract
- [{t2}] T02 [Tier B] second task  (files: b.py)
      Unit test: no unit test: Tier B, glue
- [{t3}] T03 {human}[Tier A] third task  (files: c.py)
      Unit test: contract
"""

FENCED_EXAMPLE = """
## Per-task format

```
- [ ] T99 [Tier A|B] never counted — lives in a fence
```
"""


def check(feature_dir: Path) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(LOOP_CHECK), str(feature_dir)],
        capture_output=True, text=True, timeout=60,
    )
    return p.returncode, p.stdout


def make_feature(tmp: str, tasks: str | None) -> Path:
    d = Path(tmp) / "specs" / "demo"
    d.mkdir(parents=True)
    if tasks is not None:
        (d / "tasks.md").write_text(tasks)
    return d


def run() -> list[tuple[bool, str]]:
    results = []

    def case(desc, passed):
        results.append((passed, desc))

    with tempfile.TemporaryDirectory() as tmp:
        rc, out = check(make_feature(tmp, None))
        case("missing tasks.md -> BLOCKED (2)", rc == 2 and "BLOCKED" in out)

    with tempfile.TemporaryDirectory() as tmp:
        rc, out = check(make_feature(tmp, "# Tasks\n\nno task lines here\n"))
        case("tasks.md without Tnn lines -> BLOCKED (2)", rc == 2)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2=" ", t3=" ", human="")
        rc, out = check(make_feature(tmp, tasks))
        case("unchecked task -> CONTINUE (1) naming next unit",
             rc == 1 and "T02" in out)
        case("progress line reports done/total",
             "progress: done=1 total=3" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3=" ", human="[HUMAN] ")
        rc, out = check(make_feature(tmp, tasks))
        case("next unchecked is [HUMAN] -> BLOCKED (2) with the task text",
             rc == 2 and "T03" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        rc, out = check(make_feature(tmp, tasks))
        case("all tasks checked -> FINISHED (0), Stage 3 attended",
             rc == 0 and "FINISHED" in out and "/shakeout" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="") + FENCED_EXAMPLE
        rc, out = check(make_feature(tmp, tasks))
        case("fenced example task lines are not counted",
             rc == 0 and "total=3" in out)

    with tempfile.TemporaryDirectory() as tmp:
        # T02 has no [Tier] marker -> gate-check FAIL -> loop says fix artifacts
        tasks = "- [x] T01 [Tier A] ok  (files: a.py)\n- [ ] T02 broken task\n"
        rc, out = check(make_feature(tmp, tasks))
        case("gate-check FAIL -> CONTINUE (1) pointing at plan artifacts",
             rc == 1 and "gate-check FAIL" in out)

    return results
