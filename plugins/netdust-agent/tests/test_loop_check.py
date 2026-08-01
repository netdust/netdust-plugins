"""Tests for bin/loop-check.py — the loop ledger.

Since testimony-seams (P1a), FINISHED is keyed to green EVIDENCE, not just
checked boxes: all tasks checked AND the latest `suite-green` run-log event
is still CURRENT — no commit since its sha touched a code path. Checkboxes
are agent testimony; the suite-green event is the machine-checked fact the
SubagentStop hook recorded. Freshness is measured against code-touching
commits, not raw HEAD equality, so the controller's own checkbox/ledger/docs
commits never invalidate the green (the design-debt fix over the donor's
sha == HEAD comparison). Missing/stale evidence → CONTINUE with a re-verify
unit; unreadable trace fails toward CONTINUE; an undeterminable HEAD (no git
repo) degrades to accepting the green event (mirrors run_gate_check's
degradation)."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

LOOP_CHECK = Path(__file__).resolve().parent.parent / "bin" / "loop-check.py"

TIERED = """# Tasks: demo

## Phase 1

### Cluster C1  (3 tasks · provisional tier: STANDARD)
- [{t1}] T01 [Tier A] first task  (files: a.py)
      Test-author: solo — A-lite, pure logic
      Unit test: contract
- [{t2}] T02 [Tier B] second task  (files: b.py)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, glue
- [{t3}] T03 {human}[Tier A] third task  (files: c.py)
      Test-author: solo — A-lite, pure logic
      Unit test: contract

**Integration gate (C1):** the three tasks compose end to end.

── REVIEW GATE ──  *(STOP: commit C1, `/integration`, `/code-review` — tier STANDARD)*
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


def _git(cwd, *args) -> str:
    p = subprocess.run(["git", "-C", str(cwd), *args],
                       capture_output=True, text=True, timeout=30)
    return p.stdout.strip()


def _commit(cwd, msg: str) -> str:
    _git(cwd, "add", "-A")
    _git(cwd, "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", msg)
    return _git(cwd, "rev-parse", "HEAD")


def git_repo(tmp: str) -> str:
    """git-init the fixture root with one commit; return HEAD sha."""
    _git(tmp, "init", "-q")
    return _commit(tmp, "seed")


def green_event(feature_dir: Path, sha: str) -> None:
    with (feature_dir / "run-log.jsonl").open("a") as f:
        f.write(json.dumps({"ts": "2026-07-16T10:00:00+00:00",
                            "event": "suite-green",
                            "data": {"sha": sha, "cmd": "bun test"}}) + "\n")


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

    # ── FINISHED is keyed to green evidence (testimony-seams P1a) ──────────

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)
        sha = git_repo(tmp)
        green_event(d, sha)
        rc, out = check(d)
        case("all checked + suite-green sha == HEAD -> FINISHED (0), Stage 3 attended",
             rc == 0 and "FINISHED" in out and "/shakeout" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="") + FENCED_EXAMPLE
        d = make_feature(tmp, tasks)
        green_event(d, git_repo(tmp))
        rc, out = check(d)
        case("fenced example task lines are not counted",
             rc == 0 and "total=3" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)
        git_repo(tmp)  # repo exists, but NO suite-green event was ever traced
        rc, out = check(d)
        case("all checked, no green evidence -> CONTINUE (1) with re-verify unit",
             rc == 1 and "evidence stale/missing" in out and "re-run the suite" in out)
        case("re-verify CONTINUE still prints the progress line",
             "progress: done=3 total=3" in out)

    with tempfile.TemporaryDirectory() as tmp:
        # a CODE commit after the green invalidates it
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)
        old_sha = git_repo(tmp)
        green_event(d, old_sha)
        (Path(tmp) / "src").mkdir()
        (Path(tmp) / "src" / "guard.py").write_text("VALUE = 1\n")
        _commit(tmp, "feat: real code moved on")
        rc, out = check(d)
        case("all checked, code commit after green -> CONTINUE (1, evidence stale)",
             rc == 1 and "evidence stale/missing" in out)

    with tempfile.TemporaryDirectory() as tmp:
        # …but a docs/tasks-only commit does NOT: the controller's own
        # checkbox/ledger commits must never perpetually invalidate the green
        # (the design-debt fix over raw sha == HEAD equality).
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)
        old_sha = git_repo(tmp)
        green_event(d, old_sha)
        (d / "tasks.md").write_text(tasks + "\n<!-- ledger tick -->\n")
        (Path(tmp) / "notes.md").write_text("# controller notes\n")
        _commit(tmp, "docs: check the boxes")
        rc, out = check(d)
        case("all checked, docs/tasks-only commit after green -> still FINISHED",
             rc == 0 and "FINISHED" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)
        sha = git_repo(tmp)
        green_event(d, "deadbeef")           # stale event first…
        green_event(d, sha)                  # …latest one is current
        rc, out = check(d)
        case("latest suite-green wins over an older stale one -> FINISHED",
             rc == 0)

    with tempfile.TemporaryDirectory() as tmp:
        # unknown green sha (not in this repo's history) → freshness is
        # undeterminable → CONTINUE, never a false FINISHED
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)
        git_repo(tmp)
        green_event(d, "deadbeef")
        rc, out = check(d)
        case("all checked, green sha unknown to git -> CONTINUE (1)",
             rc == 1 and "evidence stale/missing" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)
        git_repo(tmp)
        (d / "run-log.jsonl").write_text("{not json at all\n\x00\x01\n")
        rc, out = check(d)
        case("all checked, corrupt/unreadable trace -> CONTINUE (1), never crash",
             rc == 1 and "evidence stale/missing" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tasks = TIERED.format(t1="x", t2="x", t3="x", human="")
        d = make_feature(tmp, tasks)   # NO git repo anywhere above the fixture
        green_event(d, "whatever-sha")
        rc, out = check(d)
        # HEAD undeterminable (no repo) → degrade to accepting the green event
        # (documented run_gate_check-style degradation: never trap a loop on a
        # broken/absent git; the dry-loop guardrail still bounds a false pass).
        case("no git repo + green event -> FINISHED (documented degradation)",
             rc == 0 and "FINISHED" in out)

    with tempfile.TemporaryDirectory() as tmp:
        # T02 has no [Tier] marker -> gate-check FAIL -> loop says fix artifacts
        tasks = "- [x] T01 [Tier A] ok  (files: a.py)\n- [ ] T02 broken task\n"
        rc, out = check(make_feature(tmp, tasks))
        case("gate-check FAIL -> CONTINUE (1) pointing at plan artifacts",
             rc == 1 and "gate-check FAIL" in out)

    return results
