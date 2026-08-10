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
RUN_TRACE = Path(__file__).parent.parent / "bin" / "run-trace.py"

BIG_CODE = "\n".join(f"export const v{i} = {i};" for i in range(10))
BIG_TEST = "\n".join(f"assert {i} == {i}" for i in range(10))

# ── FR-8 / T05 fixtures: behaviour-cluster transition tolerance ─────────────
# Ledger dialect (PINNED by these tests — the implementer and the T07 skill
# text follow what is asserted here):
#   • cluster events live in the SAME ledger as suite-green: minted through
#     bin/run-trace.py append into <feature-dir>/run-log.jsonl, one JSON line
#     {"ts": ..., "event": ..., "data": {...}} per event (feature dir resolved
#     from the tasks/.harness-loop.json marker, as the hook already does).
#   • `cluster-open` carries data.red_test = "<path>::<method>" — the FR-6
#     `RED until:` identity. "Open" = a cluster-open with no later
#     cluster-close event.
#   • `cluster-close` closes the tolerance; it carries no required data (the
#     named test is read from the matching cluster-open).
#   • an ADMITTED red close is RECORDED as one `cluster-red-admitted` event
#     whose data.red_test names the admitted test — and it never mints
#     `suite-green` (C1c: only a scraped green may mint the fact loop-check
#     trusts).
# Matching key: the failure identity as the hook's scraper can actually see
# it — `FAILED <path>::<method>` lines in the last test run's tool_result
# text (the scraped channel the hook already reads). Tolerance is EXACT: the
# set of scraped failing identities must equal {named}.

NAMED_RED = "tests/test_musician_guard.py::test_denies_nonmember"
OTHER_RED = "tests/test_other.py::test_unrelated"


def _trace(feature: Path, event: str, *kv: str) -> None:
    """Mint a ledger event through the real single writer (run-trace.py) so
    the fixture shape can never drift from the house dialect."""
    subprocess.run(
        [sys.executable, str(RUN_TRACE), "append", str(feature), event, *kv],
        capture_output=True, text=True, timeout=15, check=True)


def _ledger_events(feature: Path) -> list[dict]:
    log = feature / "run-log.jsonl"
    if not log.exists():
        return []
    events = []
    for ln in log.read_text().splitlines():
        try:
            events.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    return events


def _fail_text(*idents: str, passed: int = 12) -> str:
    """Suite output for a red run failing exactly `idents` — the scraped
    channel's view of WHICH tests failed."""
    lines = [f"FAILED {i} - AssertionError" for i in idents]
    lines.append(f"{len(idents)} failed, {passed} passed in 0.42s")
    lines.append("Exit code: 1")
    return "\n".join(lines)


def _red_close(fail_content: str, exit_claim: int = 1) -> list[dict]:
    """An implementer close (production edit) whose last suite run scraped
    red with `fail_content`."""
    return [
        _msg(_write(BIG_CODE)),
        _msg(_bash("npx vitest run", tool_id="tu1")),
        _result("tu1", is_error=True, content=fail_content),
        _evidence('HARNESS-EVIDENCE: role=implementer '
                  f'suite="npx vitest run" exit={exit_claim}'),
    ]


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

    # ── C1: facts beat testimony ────────────────────────────────────────────
    # The evidence line contributes exit/role/mode KNOWLEDGE (tightening);
    # it never substitutes for the run itself, and when it disagrees with a
    # scraped result the RED one wins (max severity).

    # (a) a recognized evidence claim with ZERO Bash test runs is testimony
    # about a run that never happened → the "no test ran" block.
    d, out = _run([
        _msg(_write(BIG_CODE)),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=0'),
    ])
    case("C1a: recognized evidence claim, zero Bash test runs → block (no run)",
         d == "block")

    # (b) evidence green vs scraped RED → the RED one wins.
    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=True, content="2 failed\nExit code: 1"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=0'),
    ])
    case("C1b: evidence exit=0 + scraped RED → block (RED wins on disagreement)",
         d == "block")

    # (b, tighten direction preserved) evidence RED vs scraped green → block.
    d, out = _run([
        _msg(_write(BIG_CODE)),
        _msg(_bash("bun test", tool_id="tu1")),
        _result("tu1", is_error=False, content="all green"),
        _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=1'),
    ])
    case("C1b: evidence exit=1 + scraped green → block (testimony tightens)",
         d == "block")

    # (c) suite-green emission requires a SCRAPED green corroboration
    # (matching Bash run, non-error result) — never evidence alone.
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        d, out = _run([
            _msg(_write(BIG_CODE)),
            _msg(_bash("bun test")),  # ran, but NO tool_result → exit unknown
            _evidence('HARNESS-EVIDENCE: role=implementer suite="bun test" exit=0'),
        ], cwd=tp)
        log = feature / "run-log.jsonl"
        case("C1c: armed + evidence green without scraped corroboration → "
             "passthrough but NO suite-green event",
             d == "passthrough" and not log.exists())

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

    # ── FR-8 / T05: behaviour-cluster transition tolerance ──────────────────
    # Contract source: deliverable-first FR-8 + AC-4/AC-5/SC-4 + the T05 task
    # block. RED-first against the pre-change hook: T05a (all three
    # assertions), T05b (the reason-naming half), T05d (the reason-naming
    # half) and T05f fail today; T05b2/T05c/T05e/T05f2 are green today and
    # stand as back-compat / exactness locks (SC-4's three demonstrated-RED
    # cases are a/b/d).

    # (a) open cluster-open + the ONLY scraped failure IS the named test →
    #     the close is ADMITTED, the admission is recorded, no green is minted.
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        _trace(feature, "cluster-open", f"red_test={NAMED_RED}")
        d, out = _run(_red_close(_fail_text(NAMED_RED)), cwd=tp)
        events = _ledger_events(feature)
        admits = [e for e in events if e.get("event") == "cluster-red-admitted"]
        greens = [e for e in events if e.get("event") == "suite-green"]
        case("T05a: open cluster-open + only failure IS the named test → "
             "close admitted (passthrough)", d == "passthrough")
        case("T05a: the admission is recorded — one cluster-red-admitted "
             "ledger event whose data.red_test names the test",
             len(admits) == 1
             and admits[0].get("data", {}).get("red_test") == NAMED_RED)
        case("T05a: an admitted RED close mints NO suite-green event "
             "(C1c: only a scraped green may mint the fact)", not greens)

    # (b) mid-cluster failure is a DIFFERENT test → block, and the reason
    #     names the unexpected failure (today's generic suite-red reason does
    #     not — this half is the RED).
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        _trace(feature, "cluster-open", f"red_test={NAMED_RED}")
        d, out = _run(_red_close(_fail_text(OTHER_RED)), cwd=tp)
        case("T05b: mid-cluster failure is a DIFFERENT test → block, reason "
             "names the unexpected failure", d == "block" and OTHER_RED in out)

    # (b2) the failing identity merely EXTENDS the named one — a substring
    #      match must not admit it (exact identity, not containment).
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        _trace(feature, "cluster-open", f"red_test={NAMED_RED}")
        d, out = _run(_red_close(_fail_text(NAMED_RED + "_variant")), cwd=tp)
        case("T05b2: failing test EXTENDS the named identity (substring trap) "
             "→ block", d == "block")

    # (c) named test red PLUS another red → block: the tolerance is exactly
    #     the named test, never a superset containing it.
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        _trace(feature, "cluster-open", f"red_test={NAMED_RED}")
        d, out = _run(_red_close(_fail_text(NAMED_RED, OTHER_RED, passed=11)),
                      cwd=tp)
        case("T05c: named test red PLUS another red → block (tolerance is "
             "exact, not a superset)", d == "block")

    # (d) cluster-close ends the tolerance: a close while the named test
    #     still fails blocks with a reason NAMING the test (today's block has
    #     no cluster concept and cannot name it — that half is the RED).
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        _trace(feature, "cluster-open", f"red_test={NAMED_RED}")
        _trace(feature, "cluster-close")
        d, out = _run(_red_close(_fail_text(NAMED_RED)), cwd=tp)
        case("T05d: cluster-close in ledger + named test still red → block, "
             "reason names the test", d == "block" and NAMED_RED in out)

    # (e) NO cluster-open anywhere in the ledger → bit-for-bit today's
    #     behaviour (AC-4 lock): the same named-test failure blocks, and the
    #     hook mints nothing cluster-shaped. (The rest of the AC-4 lock is
    #     every pre-existing case in this module, running unmodified.)
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        d, out = _run(_red_close(_fail_text(NAMED_RED)), cwd=tp)
        cluster_events = [e for e in _ledger_events(feature)
                          if str(e.get("event", "")).startswith("cluster")]
        case("T05e: no cluster-open in ledger → red close blocks exactly as "
             "today (AC-4 back-compat lock)", d == "block")
        case("T05e: and nothing cluster-shaped is minted into the ledger",
             not cluster_events)

    # (f) scraped-failure-wins stays intact across the tolerance: a claimed
    #     exit=0 with a scraped failure of the named test IS that failure —
    #     admitted under (a), and the false green claim mints no suite-green;
    #     with any other scraped failure it blocks.
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        _trace(feature, "cluster-open", f"red_test={NAMED_RED}")
        d, out = _run(_red_close(_fail_text(NAMED_RED), exit_claim=0), cwd=tp)
        greens = [e for e in _ledger_events(feature)
                  if e.get("event") == "suite-green"]
        case("T05f: claimed exit=0 + scraped failure of the named test → "
             "treated as that failure, admitted (scraped failure wins)",
             d == "passthrough")
        case("T05f: and the false green claim mints NO suite-green event",
             not greens)

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = _armed_fixture(tp)
        _trace(feature, "cluster-open", f"red_test={NAMED_RED}")
        d, out = _run(_red_close(_fail_text(OTHER_RED), exit_claim=0), cwd=tp)
        case("T05f2: claimed exit=0 + scraped failure of a DIFFERENT test → "
             "block (scraped failure wins over the claim)", d == "block")

    return results


if __name__ == "__main__":
    rs = run()
    for ok, desc in rs:
        print(("pass" if ok else "FAIL") + "\t" + desc)
    sys.exit(0 if all(p for p, _ in rs) else 1)
