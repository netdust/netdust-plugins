"""Tests for hooks/loop-gate.py — the Stop-hook loop driver."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

LOOP_GATE = Path(__file__).resolve().parent.parent / "hooks" / "loop-gate.py"

TASKS_ONE_OPEN = (
    "- [x] T01 [Tier A] done  (files: a.py)\n"
    "- [ ] T02 [Tier B] open  (files: b.py)\n"
    "      Unit test: no unit test: Tier B, glue\n"
)
TASKS_ALL_DONE = "- [x] T01 [Tier A] done  (files: a.py)\n"
TASKS_HUMAN_NEXT = (
    "- [x] T01 [Tier A] done  (files: a.py)\n"
    "- [ ] T02 [HUMAN] [Tier B] approve the teardown migration\n"
)


def run_gate(cwd: Path, stdin_obj: dict, home: Path) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(LOOP_GATE)],
        input=json.dumps(stdin_obj), capture_output=True, text=True,
        timeout=120, env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    return p.returncode, p.stdout


def setup(tmp: str, tasks: str, marker: dict | None) -> Path:
    cwd = Path(tmp) / "proj"
    (cwd / "specs" / "demo").mkdir(parents=True)
    (cwd / "specs" / "demo" / "tasks.md").write_text(tasks)
    (cwd / "tasks").mkdir()
    if marker is not None:
        base = {"feature_dir": "specs/demo", "iteration": 0,
                "max_iterations": 25, "last_done": 0, "dry": 0}
        base.update(marker)
        (cwd / "tasks" / ".harness-loop.json").write_text(json.dumps(base))
    return cwd


def marker_of(cwd: Path) -> dict | None:
    p = cwd / "tasks" / ".harness-loop.json"
    return json.loads(p.read_text()) if p.exists() else None


def run() -> list[tuple[bool, str]]:
    results = []

    def case(desc, passed):
        results.append((passed, desc))

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker=None)
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("no marker -> silent passthrough", rc == 0 and out.strip() == "")

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        m = marker_of(cwd)
        case("armed + open task -> block with next unit",
             rc == 0 and '"decision": "block"' in out and "T02" in out)
        case("block increments iteration in marker",
             m is not None and m["iteration"] == 1 and m["last_done"] == 1)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={})
        rc, out = run_gate(cwd, {"cwd": str(cwd), "stop_hook_active": True}, Path(tmp))
        case("stop_hook_active -> bypass, marker untouched",
             rc == 0 and out.strip() == "" and marker_of(cwd)["iteration"] == 0)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={"iteration": 25})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("budget exhausted -> disarm, allow stop",
             rc == 0 and out.strip() == "" and marker_of(cwd) is None)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ALL_DONE, marker={"iteration": 3, "last_done": 1})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("FINISHED -> disarm, allow stop",
             rc == 0 and out.strip() == "" and marker_of(cwd) is None)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_HUMAN_NEXT, marker={})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("[HUMAN] next -> yield (no block), marker stays armed",
             rc == 0 and out.strip() == "" and marker_of(cwd) is not None)

    with tempfile.TemporaryDirectory() as tmp:
        # done-count stuck at 1 across stops: dry 1 (block), dry 2 (disarm)
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={"last_done": 1})
        rc1, out1 = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        m1 = marker_of(cwd)
        rc2, out2 = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("dry loop: first stuck stop still blocks (dry=1)",
             '"decision": "block"' in out1 and m1 is not None and m1["dry"] == 1)
        case("dry loop: second stuck stop disarms, allows",
             rc2 == 0 and out2.strip() == "" and marker_of(cwd) is None)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={})
        (cwd / "tasks" / ".harness-loop.json").write_text("{corrupt")
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("corrupt marker -> fail open (allow stop)",
             rc == 0 and '"decision"' not in out)

    return results
