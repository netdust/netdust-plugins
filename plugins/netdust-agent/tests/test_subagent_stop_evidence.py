"""
test_subagent_stop_evidence.py — the green gate + close-out evidence contract
(testimony-seams P0, ported onto the 0.16 hook).

The seam this closes: subagent-stop.py verified a test command RAN, explicitly
not that it PASSED — green-ness was enforced only by prose. Now the building
addenda specify ONE machine-parseable close-out line:

    HARNESS-EVIDENCE: role=<implementer|test-author> suite="<cmd>" exit=<int> [lint=<int>] [mode=<split|solo>]

and the hook consumes it (designed evidence), falling back to scraping the last
test-command tool_result (scraped evidence) when the line is absent. Rules:

  - role resolves from FACTS, never trust alone: test-author honored iff every
    edited code path is a test path; any production edit → implementer.
  - implementer + suite exit ≠ 0 → block naming the command + exit code.
  - test-author → run-only suffices (RED is its job).
  - evidence suite command must match the hook's test-command recognizer or the
    suite claim is ignored (a claim can tighten the verdict, never loosen it).
    The recognizer is the CURRENT tree's TEST_CMD_PATTERN — composer gate /
    bin/gate.sh count (main's recognizers are preserved, not replaced).
  - no line + no test command → the pre-existing "no test ran" block.
  - malformed line / unknown exit → fail-open (the old ran-only behavior).
  - implementer green + loop armed → exactly one `suite-green` run-trace event
    (sha + cmd); unarmed → none; broken trace path → decision unchanged.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "subagent-stop.py"

BIG_CODE = "\n".join(f"export const v{i} = {i};" for i in range(10))
BIG_TEST = "\n".join(f"assert {i} == {i}" for i in range(10))


def _msg(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def _text(s):
    return {"type": "text", "text": s}


def _write(content, file_path="src/foo.ts"):
    return {"type": "tool_use", "name": "Write",
            "input": {"file_path": file_path, "content": content}}


def _bash(cmd, tool_id=None):
    block = {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}
    if tool_id:
        block["id"] = tool_id
    return block


def _result(tool_id, is_error=False, content=""):
    """A user-turn tool_result message (the real Claude Code transcript shape)."""
    return {"type": "user", "message": {"content": [{
        "type": "tool_result", "tool_use_id": tool_id,
        "is_error": is_error, "content": content,
    }]}}


def _evidence(line):
    return _msg(_text(f"Task complete.\n\n{line}\n"))


def _run(messages, cwd: Path | None = None):
    """Invoke the hook; return (decision, stdout). If cwd is given, it is used
    as the hook's cwd (for marker/git fixtures); else a bare temp dir."""
    with tempfile.TemporaryDirectory() as tmp:
        base = cwd if cwd is not None else Path(tmp)
        transcript = Path(tmp) / "t.jsonl"
        transcript.write_text("\n".join(json.dumps(m) for m in messages) + "\n")
        payload = {"transcript_path": str(transcript), "cwd": str(base),
                   "stop_hook_active": False}
        proc = subprocess.run([sys.executable, str(HOOK)],
                              input=json.dumps(payload),
                              capture_output=True, text=True, timeout=15)
        decision = "passthrough"
        if proc.stdout.strip():
            try:
                decision = json.loads(proc.stdout).get("decision", "?")
            except json.JSONDecodeError:
                decision = f"unparseable: {proc.stdout!r}"
        return decision, proc.stdout


def _git(cwd: Path, *args) -> str:
    p = subprocess.run(["git", "-C", str(cwd), *args],
                       capture_output=True, text=True, timeout=15)
    return p.stdout.strip()


def _armed_fixture(tp: Path, feature_dir_exists=True) -> Path:
    """A cwd with an armed loop marker + git repo. Returns the feature dir."""
    (tp / "tasks").mkdir()
    (tp / "tasks" / ".harness-loop.json").write_text(
        json.dumps({"feature_dir": "specs/demo", "iteration": 0}))
    feature = tp / "specs" / "demo"
    if feature_dir_exists:
        feature.mkdir(parents=True)
    _git(tp, "init", "-q")
    _git(tp, "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-q", "--allow-empty", "-m", "seed")
    return feature


def run():
    results = []

    def case(desc, passed):
        results.append((passed, desc))

    # ── designed evidence: the line decides ─────────────────────────────────

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=True, content="3 tests, 1 failed\nExit code: 1"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=1'),
    ])
    case("implementer + evidence exit=1 → block naming cmd + exit",
         d == "block" and "bun test" in out and "1" in out)

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=False, content="3 tests, 0 failed"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=0'),
    ])
    case("implementer + evidence exit=0 → passthrough", d == "passthrough")

    d, out = _run([
        _msg(_write(BIG_TEST, file_path="tests/test_guard.py")),
        _msg(_bash("vendor/bin/phpunit", tool_id="tu1")),
        _result("tu1", is_error=True, content="FAILURES!\nExit code: 1"),
        _evidence('HARNESS-EVIDENCE: role=test-author suite="vendor/bin/phpunit" exit=1'),
    ])
    case("test-author, test paths only, RED run → passthrough (RED is its job)",
         d == "passthrough")

    d, out = _run([
        _msg(_write(BIG_CODE, file_path="src/guard.ts")),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=True, content="Exit code: 1"),
        _evidence('HARNESS-EVIDENCE: role=test-author suite="bun test" exit=1'),
    ])
    case("claimed test-author but edited a production path, red → block "
         "(claims never loosen)", d == "block")

    # a claim can TIGHTEN: implementer claim on an all-test-paths edit is held to green
    d, out = _run([
        _msg(_write(BIG_TEST, file_path="tests/test_guard.py")),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=True, content="Exit code: 1"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=1'),
    ])
    case("claimed implementer on test-only edit, red → block (claims tighten)",
         d == "block")

    # unrecognized suite command on the line → suite claim ignored, scrape wins
    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=True, content="Exit code: 2"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="echo ok" exit=0'),
    ])
    case("pseudo-test suite claim (echo) + scraped red → block (claim can't loosen)",
         d == "block" and "2" in out)

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="echo ok" exit=0'),
    ])
    case("pseudo-test suite claim, no real test command → block (no test ran)",
         d == "block")

    # ── main's recognizers are PRESERVED at the evidence seam ────────────────
    # composer gate / bin/gate.sh count as suite evidence (the recognizers the
    # donor's stale pattern copies would have dropped).

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("composer gate", tool_id="tu1")),
        _result("tu1", is_error=True, content="Exit code: 1"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="composer gate" exit=1'),
    ])
    case("evidence suite=\"composer gate\" is recognized → red gate run blocks",
         d == "block" and "composer gate" in out)

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("sh bin/gate.sh", tool_id="tu1")),
        _result("tu1", is_error=False, content="all tiers green"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="sh bin/gate.sh" exit=0'),
    ])
    case("evidence suite=\"sh bin/gate.sh\" is recognized → green passthrough",
         d == "passthrough")

    # ── scraped evidence: fallback when the line is absent ──────────────────

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("npx vitest run", tool_id="tu1")),
        _result("tu1", is_error=False, content="12 passed"),
    ])
    case("no line, scraped last test result green → passthrough (back-compat)",
         d == "passthrough")

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("npx vitest run", tool_id="tu1")),
        _result("tu1", is_error=True, content="2 failed\nExit code: 1"),
    ])
    case("no line, scraped last test result red → block naming cmd",
         d == "block" and "npx vitest" in out)

    # last run wins: red then re-run green → allow
    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=True, content="Exit code: 1"),
        _msg(_bash("bun test", tool_id="tu2")),
        _result("tu2", is_error=False, content="all green"),
    ])
    case("red run then green re-run → passthrough (last result wins)",
         d == "passthrough")

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test")),  # no tool id, no result → exit unknown
    ])
    case("no line, test ran, exit unknown → passthrough (old ran-only behavior)",
         d == "passthrough")

    # ── fail-open ────────────────────────────────────────────────────────────

    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test")),
        _evidence("HARNESS-EVIDENCE: role=implementer exit=banana suite=oops"),
    ])
    case("malformed evidence line → fail-open to ran-only (passthrough), logged",
         d == "passthrough")

    with tempfile.TemporaryDirectory() as tmp:
        payload = {"transcript_path": str(Path(tmp) / "missing.jsonl"),
                   "cwd": tmp, "stop_hook_active": False}
        proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                              capture_output=True, text=True, timeout=15)
        case("unreadable transcript → fail-open allow (exit 0, no stdout)",
             proc.returncode == 0 and not proc.stdout.strip())

    # ── suite-green trace emission (the C2 emit side) ────────────────────────

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        head = _git(tp, "rev-parse", "HEAD")
        d, out = _run([
            _msg(_write(BIG_CODE)),
            _msg(_bash("bun test", tool_id="tu1")),
            _result("tu1", is_error=False, content="ok"),
            _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=0'),
        ], cwd=tp)
        log = feature / "run-log.jsonl"
        lines = [json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
        greens = [l for l in lines if l.get("event") == "suite-green"]
        case("armed + implementer green → exactly one suite-green event",
             d == "passthrough" and len(greens) == 1)
        case("suite-green event carries sha=HEAD and the suite cmd",
             bool(greens) and greens[0]["data"].get("sha") == head
             and greens[0]["data"].get("cmd") == "bun test")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        d, out = _run([
            _msg(_write(BIG_CODE)),
            _msg(_bash("bun test", tool_id="tu1")),
            _result("tu1", is_error=True, content="Exit code: 1"),
            _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=1'),
        ], cwd=tp)
        log = feature / "run-log.jsonl"
        case("armed + implementer RED → no suite-green event",
             d == "block" and not log.exists())

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)  # unarmed: no marker at all
        d, out = _run([
            _msg(_write(BIG_CODE)),
            _msg(_bash("bun test", tool_id="tu1")),
            _result("tu1", is_error=False, content="ok"),
            _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=0'),
        ], cwd=tp)
        case("unarmed + green → passthrough, no run-log anywhere",
             d == "passthrough" and not list(tp.rglob("run-log.jsonl")))

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed_fixture(tp, feature_dir_exists=False)  # append will be rejected
        d, out = _run([
            _msg(_write(BIG_CODE)),
            _msg(_bash("bun test", tool_id="tu1")),
            _result("tu1", is_error=False, content="ok"),
            _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=0'),
        ], cwd=tp)
        case("broken trace path (missing feature dir) → decision unchanged (fail-open)",
             d == "passthrough")

    return results


if __name__ == "__main__":
    rs = run()
    for ok, desc in rs:
        print(("pass" if ok else "FAIL") + "\t" + desc)
    sys.exit(0 if all(p for p, _ in rs) else 1)
