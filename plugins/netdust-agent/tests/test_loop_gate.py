"""Tests for hooks/loop-gate.py — the Stop-hook loop driver."""

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LOOP_GATE = Path(__file__).resolve().parent.parent / "hooks" / "loop-gate.py"
RUN_TRACE = Path(__file__).resolve().parent.parent / "bin" / "run-trace.py"

TASKS_ONE_OPEN = (
    "- [x] T01 [Tier A] done  (files: a.py)\n"
    "      Test-author: solo — A-lite fixture task\n"
    "      Unit test: contract\n"
    "- [ ] T02 [Tier B] open  (files: b.py)\n"
    "      Test-author: solo — Tier B\n"
    "      Unit test: no unit test: Tier B, glue\n"
)
TASKS_ALL_DONE = (
    "- [x] T01 [Tier A] done  (files: a.py)\n"
    "      Test-author: solo — A-lite fixture task\n"
    "      Unit test: contract\n"
)
TASKS_HUMAN_NEXT = (
    "- [x] T01 [Tier A] done  (files: a.py)\n"
    "      Test-author: solo — A-lite fixture task\n"
    "      Unit test: contract\n"
    "- [ ] T02 [HUMAN] [Tier B] approve the teardown migration\n"
    "      Test-author: solo — Tier B\n"
    "      Unit test: no unit test: Tier B, human approval step\n"
)


def run_gate(cwd: Path, stdin_obj: dict, home: Path,
             gate: Path = LOOP_GATE) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(gate)],
        input=json.dumps(stdin_obj), capture_output=True, text=True,
        timeout=120, env={"HOME": str(home), "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    return p.returncode, p.stdout


# ── budget-seam stub (I-3 re-contract) ───────────────────────────────────────
# A scratch plugin tree with the REAL loop-gate + loop-check + run-trace but a STUBBED
# verify-budget.py speaking the RETIRED pre-0b6ccd1 HALT contract — output no real
# verify-budget can produce anymore. The gate must never consult it: the stub records
# its argv iff invoked, so an empty recording proves the seam is gone.

STUB_HALT = """#!/usr/bin/env python3
import sys
open(__file__ + '.argv', 'w').write(' '.join(sys.argv[1:]))
print('BUDGET: HALT — stub says the spend outran the stakes')
sys.exit(1)
"""


def setup_stub_plugin(tmp: str, stub_body: str) -> Path:
    plug = Path(tmp) / "plug"
    (plug / "hooks").mkdir(parents=True)
    (plug / "bin").mkdir()
    shutil.copy(LOOP_GATE, plug / "hooks" / "loop-gate.py")
    shutil.copy(LOOP_GATE.parent.parent / "bin" / "loop-check.py",
                plug / "bin" / "loop-check.py")
    shutil.copy(RUN_TRACE, plug / "bin" / "run-trace.py")
    (plug / "bin" / "verify-budget.py").write_text(stub_body)
    return plug / "hooks" / "loop-gate.py"


def git_master(cwd: Path) -> None:
    """Make cwd a git repo whose only branch is `master` — the Daan incident shape."""
    def g(*args):
        subprocess.run(["git", *args], cwd=cwd, check=True,
                       capture_output=True, text=True, timeout=30)
    g("init", "-q", "-b", "master")
    g("-c", "user.email=t@t.t", "-c", "user.name=t", "commit",
      "-q", "--allow-empty", "-m", "base")


def stub_argv(gate: Path) -> str:
    p = gate.parent.parent / "bin" / "verify-budget.py.argv"
    return p.read_text() if p.exists() else ""


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


def finished_evidence(cwd: Path) -> None:
    """Since testimony-seams P1a, FINISHED needs green evidence current with
    the last code-touching commit, not just checked boxes — arm the fixture
    with both."""
    def git(*args):
        return subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, timeout=30).stdout.strip()
    git("init", "-q")
    git("-c", "user.email=t@t", "-c", "user.name=t",
        "commit", "-q", "--allow-empty", "-m", "seed")
    sha = git("rev-parse", "HEAD")
    with (cwd / "specs" / "demo" / "run-log.jsonl").open("a") as f:
        f.write(json.dumps({"ts": "2026-07-16T10:00:00+00:00",
                            "event": "suite-green",
                            "data": {"sha": sha, "cmd": "bun test"}}) + "\n")


def trace_events(cwd: Path, feature_dir: str = "specs/demo") -> list[dict]:
    """Read run-log.jsonl directly (more robust than shelling out to `show`,
    which only renders human-readably)."""
    log_path = cwd / feature_dir / "run-log.jsonl"
    if not log_path.exists():
        return []
    events = []
    for line in log_path.read_text().splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events


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
        finished_evidence(cwd)
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("FINISHED -> disarm, allow stop",
             rc == 0 and out.strip() == "" and marker_of(cwd) is None)

    with tempfile.TemporaryDirectory() as tmp:
        # boxes all checked but NO suite-green evidence → the loop must NOT
        # finish: loop-check says CONTINUE (re-verify) and the gate blocks.
        cwd = setup(tmp, TASKS_ALL_DONE, marker={"iteration": 3, "last_done": 1})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("checked boxes without green evidence -> block (re-verify), stay armed",
             rc == 0 and '"decision": "block"' in out
             and "evidence stale/missing" in out and marker_of(cwd) is not None)

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

    # --- T02: run-trace emission at each loop-gate decision site --------
    # Each decision site must ALSO append a run-trace event carrying
    # iteration/done/total/reason (as available). These are new
    # behavioral assertions against the CURRENT hook, which emits NO
    # trace events anywhere — expected to fail RED until the implementer
    # wires run-trace.py append calls into hooks/loop-gate.py.

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        events = trace_events(cwd)
        block_events = [e for e in events if e.get("event") == "loop-block"]
        case("block decision -> run log gains a loop-block event",
             rc == 0 and len(block_events) == 1)
        if block_events:
            data = block_events[0].get("data", {})
            case("loop-block event carries iteration/reason",
                 data.get("iteration") == "1" and "reason" in data)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={})
        rc, out = run_gate(cwd, {"cwd": str(cwd), "stop_hook_active": True}, Path(tmp))
        events = trace_events(cwd)
        bypass_events = [e for e in events if e.get("event") == "loop-bypass"]
        case("stop_hook_active bypass -> run log gains a loop-bypass event",
             rc == 0 and len(bypass_events) == 1)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ALL_DONE, marker={"iteration": 3, "last_done": 1})
        finished_evidence(cwd)
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        events = trace_events(cwd)
        finished_events = [e for e in events if e.get("event") == "loop-disarm-finished"]
        case("FINISHED disarm -> run log gains a loop-disarm-finished event",
             rc == 0 and len(finished_events) == 1)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_HUMAN_NEXT, marker={})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        events = trace_events(cwd)
        yield_events = [e for e in events if e.get("event") == "loop-yield-blocked"]
        case("[HUMAN] yield -> run log gains a loop-yield-blocked event",
             rc == 0 and len(yield_events) == 1)

    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={"iteration": 25})
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        events = trace_events(cwd)
        budget_events = [e for e in events if e.get("event") == "loop-disarm-budget"]
        case("budget exhausted disarm -> run log gains a loop-disarm-budget event",
             rc == 0 and len(budget_events) == 1)

    with tempfile.TemporaryDirectory() as tmp:
        # done-count stuck at 1 across stops: dry 1 (block), dry 2 (disarm)
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={"last_done": 1})
        run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        rc2, out2 = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        events = trace_events(cwd)
        dry_events = [e for e in events if e.get("event") == "loop-disarm-dry"]
        case("dry-loop disarm -> run log gains a loop-disarm-dry event",
             rc2 == 0 and len(dry_events) == 1)

    # --- I-3 re-contract: the gate no longer reads budget output at all -----------
    # The HALT consumer branch is retired (verify-budget always exits 0 and never
    # prints HALT since 0b6ccd1; the old stub pinned a contract no real input can
    # produce — green-but-blind). Adversarial shape: a git-master repo with a stub
    # verify-budget speaking the OLD HALT contract is exactly the environment where
    # the retired branch would have fired. The gate must emit the NORMAL next-unit
    # block, never a budget block, and must not invoke verify-budget at all.

    with tempfile.TemporaryDirectory() as tmp:
        gate = setup_stub_plugin(tmp, STUB_HALT)
        cwd = setup(tmp, TASKS_ONE_OPEN, marker={})
        git_master(cwd)
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp), gate=gate)
        case("I-3: old-contract HALT stub present -> normal next-unit block, "
             "never the budget block",
             rc == 0 and '"decision": "block"' in out
             and "verify-budget HALT" not in out and "BUDGET" not in out
             and "T02" in out)
        case("I-3: verify-budget is never consulted (stub argv recording empty)",
             stub_argv(gate) == "")
        case("I-3: the block keeps the marker armed and iterating",
             marker_of(cwd) is not None and marker_of(cwd)["iteration"] == 1)

    # --- T02: fail-open contract (FR-2) -----------------------------------
    # Tracing must NEVER change the gate's decision or stdout. Force
    # run-trace's own append to hit its denial path (feature_dir does not
    # exist) and confirm loop-gate's stdout is byte-identical to the
    # unafflicted control run.

    with tempfile.TemporaryDirectory() as tmp_control:
        cwd = setup(tmp_control, TASKS_ONE_OPEN, marker={})
        rc_control, out_control = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp_control))

    with tempfile.TemporaryDirectory() as tmp_broken:
        cwd = setup(tmp_broken, TASKS_ONE_OPEN, marker={})
        # revoke write perms so run-trace's append fails while loop-check.py's read still succeeds
        feature_dir_path = cwd / "specs" / "demo"
        feature_dir_path.chmod(0o500)  # read+execute, no write
        try:
            rc_broken, out_broken = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp_broken))
        finally:
            feature_dir_path.chmod(0o700)  # restore so tempdir cleanup succeeds

        case("fail-open: broken trace path -> decision unchanged (rc)",
             rc_broken == rc_control)
        case("fail-open: broken trace path -> stdout byte-identical",
             out_broken == out_control)

    with tempfile.TemporaryDirectory() as tmp_missing:
        # bypass site has no loop-check subprocess, so deleting feature_dir only affects the trace call
        cwd = setup(tmp_missing, TASKS_ONE_OPEN, marker={})
        shutil.rmtree(cwd / "specs" / "demo")
        rc_missing, out_missing = run_gate(
            cwd, {"cwd": str(cwd), "stop_hook_active": True}, Path(tmp_missing))

        with tempfile.TemporaryDirectory() as tmp_bypass_control:
            cwd_c = setup(tmp_bypass_control, TASKS_ONE_OPEN, marker={})
            rc_bypass_control, out_bypass_control = run_gate(
                cwd_c, {"cwd": str(cwd_c), "stop_hook_active": True},
                Path(tmp_bypass_control))

        case("fail-open: nonexistent feature_dir on bypass -> rc unchanged",
             rc_missing == rc_bypass_control)
        case("fail-open: nonexistent feature_dir on bypass -> stdout byte-identical",
             out_missing == out_bypass_control)

    # ── foreign-marker stand-down (one marker path, two drivers) ─────────
    # A marker carrying `flow`/`node` fields was written by a driver other
    # than this plugin (whose marker never has them). The gate must leave it
    # entirely alone — no block, no disarm, no trace — because that driver
    # has its own Stop hook, and a second driver here could block a stop it
    # deliberately allowed. Defensive: nothing in this plugin writes one.
    with tempfile.TemporaryDirectory() as tmp:
        cwd = setup(tmp, TASKS_ONE_OPEN,
                    marker={"flow": "site", "node": "build"})
        before = (cwd / "tasks" / ".harness-loop.json").read_text()
        rc, out = run_gate(cwd, {"cwd": str(cwd)}, Path(tmp))
        case("foreign marker: allows the stop (rc 0)", rc == 0)
        case("foreign marker: emits nothing", out == "")
        case("foreign marker: marker left byte-identical",
             (cwd / "tasks" / ".harness-loop.json").read_text() == before)
        case("foreign marker: no trace events written", trace_events(cwd) == [])

    return results
