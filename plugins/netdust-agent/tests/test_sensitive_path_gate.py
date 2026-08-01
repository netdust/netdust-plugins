"""
test_sensitive_path_gate.py — the sensitive-path routing floor
(testimony-seams P1b, re-implemented on the 0.16 tree).

The seam this closes: split-vs-solo routing was planner self-classification,
verified only for FORMAT by gate-check — misclassified work bypassed the
deeper review lane. hooks/subagent-stop.py now blocks a SOLO implementer
close that edited a production (non-test) path matching the sensitive-glob
list, with an escalation instruction naming the paths + the split obligation.

Two deliberate divergences from the donor branch:

  - The mode is resolved from the current task's `Test-author:` line in
    tasks.md (machine artifact; feature dir from the loop marker or an edited
    specs/<feature>/ path) — NEVER from the subagent-echoed evidence line,
    where the donor violated its own tighten-never-loosen rule. No resolvable
    tasks.md/mode → fail-open (no block).
  - The glob list is recalibrated to the post-contact-page-8k posture:
    anchored on path segments / filename stems, never bare full-path
    substrings — `tokenizer.ts` and `capability-table.ts` are production
    false hits the donor's `*token*` / `*capabilit*` would have blocked.

Defaults ship in bin/sensitive-globs.txt; a project's
.claude/sensitive-globs.txt REPLACES them; an unreadable override fails open
(floor off, logged) — never a crash, never a wrong block.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HOOK = Path(__file__).parent.parent / "hooks" / "subagent-stop.py"
CHECKER = Path(__file__).parent.parent / "bin" / "gate-check.py"
REPO_SPECS = Path(__file__).resolve().parents[3] / "specs"

BIG_CODE = "\n".join(f"$v{i} = {i};" for i in range(10))

TASKS_SOLO = """# Tasks: demo
### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] current task under test  (files: src/whatever.php)
      Test-author: solo — fixture (misclassified on purpose)
      Unit test: contract
"""

TASKS_SPLIT = """# Tasks: demo
### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] current task under test  (files: src/whatever.php)
      Test-author: split — 1a surface
      Unit test: contract
"""

TASKS_PRE08 = """# Tasks: demo
### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] current task under test  (files: src/whatever.php)
      Unit test: contract
"""

TASKS_SOLO_SECOND = """# Tasks: demo
### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [x] T01 [Tier A] done task  (files: src/done.php)
      Test-author: split — 1a surface
      Unit test: contract
- [ ] T02 [Tier A] current task  (files: src/whatever.php)
      Test-author: solo — fixture
      Unit test: contract
"""

# I4: [P] siblings both unchecked — the first-unchecked heuristic alone would
# misresolve; the files-segment intersection disambiguates when exactly one
# unchecked task names an edited file.
TASKS_PARALLEL_SPLIT_SECOND = """# Tasks: demo
### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [P] [Tier B] plain sibling in flight  (files: src/plain.php)
      Test-author: solo — Tier B glue
      Unit test: no unit test: Tier B, glue
- [ ] T02 [P] [Tier A] auth task  (files: src/auth/login.php)
      Test-author: split — 1a surface
      Unit test: contract
"""

TASKS_PARALLEL_SOLO_SECOND = """# Tasks: demo
### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [P] [Tier A] split sibling in flight  (files: src/auth/login.php)
      Test-author: split — 1a surface
      Unit test: contract
- [ ] T02 [P] [Tier A] solo auth task  (files: src/auth/token-store.php)
      Test-author: solo — fixture (misrouted on purpose)
      Unit test: contract
"""

TASKS_FENCED_SOLO = """# Tasks: demo
## Per-task format
```
- [ ] T99 [Tier A] example  (files: src/auth/example.php)
      Test-author: solo — never counted, lives in a fence
```
### Cluster C1
- [ ] T01 [Tier A] plain task  (files: src/plain.php)
      Test-author: split — 1a surface
      Unit test: contract
"""


def _msg(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def _write(content, file_path):
    return {"type": "tool_use", "name": "Write",
            "input": {"file_path": file_path, "content": content}}


def _bash(cmd, tool_id):
    return {"type": "tool_use", "name": "Bash", "id": tool_id,
            "input": {"command": cmd}}


def _result(tool_id, is_error=False, content=""):
    return {"type": "user", "message": {"content": [{
        "type": "tool_result", "tool_use_id": tool_id,
        "is_error": is_error, "content": content}]}}


def _evidence(line):
    return _msg({"type": "text", "text": line})


def _green_close(path, extra_msgs=None):
    """A green implementer transcript editing `path`."""
    return [
        _msg(_write(BIG_CODE, path)),
        *(extra_msgs or []),
        _msg(_bash("vendor/bin/phpunit", "t1")),
        _result("t1", is_error=False, content="OK (3 tests)"),
        _evidence('HARNESS-EVIDENCE: role=implementer '
                  'suite="vendor/bin/phpunit" exit=0'),
    ]


def _armed(cwd: Path, tasks: str | None) -> None:
    """Arm a loop marker pointing at specs/demo, with the given tasks.md."""
    (cwd / "tasks").mkdir(exist_ok=True)
    (cwd / "tasks" / ".harness-loop.json").write_text(
        json.dumps({"feature_dir": "specs/demo", "iteration": 0}))
    feature = cwd / "specs" / "demo"
    feature.mkdir(parents=True, exist_ok=True)
    if tasks is not None:
        (feature / "tasks.md").write_text(tasks)


def _run_hook(messages, cwd: Path):
    transcript = cwd / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(m) for m in messages) + "\n")
    payload = {"transcript_path": str(transcript), "cwd": str(cwd),
               "stop_hook_active": False}
    proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=15)
    decision = "passthrough"
    if proc.stdout.strip():
        try:
            decision = json.loads(proc.stdout).get("decision", "?")
        except json.JSONDecodeError:
            decision = f"unparseable: {proc.stdout!r}"
    return decision, proc.stdout


def run():
    results = []

    def case(desc, passed):
        results.append((passed, desc))

    # ── the floor: block / split-pass ───────────────────────────────────────

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("solo task (from tasks.md) + edit under */auth/* → block with escalation",
             d == "block" and "SENSITIVE" in out and "auth/login.php" in out
             and "split" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SPLIT)
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("same edit, tasks.md says split → passthrough", d == "passthrough")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        # no evidence line at all (older dispatch): floor still applies —
        # the mode comes from tasks.md, not from the line
        msgs = [_msg(_write(BIG_CODE, "src/auth/login.php")),
                _msg(_bash("vendor/bin/phpunit", "t1")),
                _result("t1", is_error=False, content="OK")]
        d, out = _run_hook(msgs, tp)
        case("no evidence line, solo sensitive production edit → block (floor on)",
             d == "block" and "SENSITIVE" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        # an echoed mode=split can NOT loosen the floor when tasks.md says solo
        _armed(tp, TASKS_SOLO)
        msgs = [
            _msg(_write(BIG_CODE, "src/auth/login.php")),
            _msg(_bash("vendor/bin/phpunit", "t1")),
            _result("t1", is_error=False, content="OK"),
            _evidence('HARNESS-EVIDENCE: role=implementer mode=split '
                      'suite="vendor/bin/phpunit" exit=0'),
        ]
        d, out = _run_hook(msgs, tp)
        case("echoed mode=split cannot loosen a tasks.md solo → still block",
             d == "block" and "SENSITIVE" in out)

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO_SECOND)
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("first UNCHECKED task is the current one (checked split task ignored) → block",
             d == "block")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        msgs = [_msg(_write(BIG_CODE, "tests/auth/test_login.php")),
                _msg(_bash("vendor/bin/phpunit", "t1")),
                _result("t1", is_error=True, content="FAILURES!\nExit code: 1"),
                _evidence('HARNESS-EVIDENCE: role=test-author '
                          'suite="vendor/bin/phpunit" exit=1')]
        d, out = _run_hook(msgs, tp)
        case("test-author RED on tests/auth/… → passthrough (test paths exempt)",
             d == "passthrough")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        d, out = _run_hook(_green_close("src/plain/helper.php"), tp)
        case("no sensitive path touched → zero behavior change (passthrough)",
             d == "passthrough")

    # migrations + token-stem defaults also gate
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        d, out = _run_hook(_green_close("db/migrations/001_drop.php"), tp)
        case("solo edit under */migrations/* → block", d == "block")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        d, out = _run_hook(_green_close("src/http/token-refresh.php"), tp)
        case("solo edit on a token-stem filename → block", d == "block")

    # ── recalibration: segment/stem anchoring, not bare substrings ──────────
    # (the post-contact-page-8k false-positive posture: production files whose
    # NAMES merely contain a risky word are not security surfaces)

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        d, out = _run_hook(_green_close("src/lexer/tokenizer.ts"), tp)
        case("false-positive negative: tokenizer.ts → passthrough",
             d == "passthrough")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        d, out = _run_hook(_green_close("src/rbac/capability-table.ts"), tp)
        case("false-positive negative: capability-table.ts → passthrough",
             d == "passthrough")

    # ── I3: the fleet glob battery (shipped defaults, direct matcher) ───────
    # HIT = a genuine security-surface shape; CLEAN = production files whose
    # names merely contain a risky substring (the cry-wolf posture).

    spec = importlib.util.spec_from_file_location("subagent_stop_mod", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    default_globs = mod.load_sensitive_globs("")  # no cwd → shipped defaults

    battery_hits = [
        "config/auth.php", "config/session.php", "scripts/migrate-users.php",
        "src/auth.ts", "crypto.ts", "payments.php",
    ]
    for path in battery_hits:
        case(f"glob battery HIT: {path}",
             mod.matches_sensitive(path, default_globs))

    battery_clean = [
        "src/lexer/tokenizer.ts", "src/rbac/capability-table.ts",
        "src/cache/nonced-cache.ts", "src/admin/rolesheet.ts",
        "src/passwordless-ui/copy.ts",
    ]
    for path in battery_clean:
        case(f"glob battery CLEAN: {path}",
             not mod.matches_sensitive(path, default_globs))

    # ── I4: [P] siblings — files-segment intersection disambiguation ────────

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_PARALLEL_SPLIT_SECOND)
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("I4: [P] siblings, edited file named by the SECOND (split) task → "
             "passthrough (not the first-unchecked solo)", d == "passthrough")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_PARALLEL_SOLO_SECOND)
        d, out = _run_hook(_green_close("src/auth/token-store.php"), tp)
        case("I4: [P] siblings, edited file named by the SECOND (solo) task → "
             "block (intersection resolves the real task)", d == "block")

    # ── fail-open: mode unresolvable → no block ─────────────────────────────

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)  # no marker, no tasks.md anywhere
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("no marker/tasks.md → fail-open (mode unresolvable, passthrough)",
             d == "passthrough")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_PRE08)
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("pre-0.8 tasks.md (no Test-author line) → fail-open "
             "(controller defaults split)", d == "passthrough")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_FENCED_SOLO)
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("fenced solo example never counts; real task says split → passthrough",
             d == "passthrough")

    # feature dir resolvable from an edited specs/<feature>/ path (no marker)
    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        feature = tp / "specs" / "demo"
        feature.mkdir(parents=True)
        (feature / "tasks.md").write_text(TASKS_SOLO)
        d, out = _run_hook(_green_close(
            "src/auth/login.php",
            extra_msgs=[_msg(_write("# notes\n", "specs/demo/notes.md"))]), tp)
        case("no marker, feature dir from edited specs/<feature>/ path → block",
             d == "block")

    # ── the override file replaces the defaults ──────────────────────────────

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        (tp / ".claude").mkdir()
        (tp / ".claude" / "sensitive-globs.txt").write_text(
            "# project override — billing only\n*/billing/*\n")
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("override without auth glob → auth edit passes (defaults replaced)",
             d == "passthrough")
        d, out = _run_hook(_green_close("src/billing/charge.php"), tp)
        case("override's own glob still gates → billing edit blocked",
             d == "block")

    with tempfile.TemporaryDirectory() as tmp:
        tp = Path(tmp)
        _armed(tp, TASKS_SOLO)
        (tp / ".claude").mkdir()
        # unreadable override: a DIRECTORY at the override path → read fails
        (tp / ".claude" / "sensitive-globs.txt").mkdir()
        d, out = _run_hook(_green_close("src/auth/login.php"), tp)
        case("unreadable override → fail-open (floor off, passthrough)",
             d == "passthrough")

    # ── retro-compat live: the repo's real feature dirs stay green ───────────
    # (the plan-time gate-check is untouched by this port)

    if REPO_SPECS.exists():
        for feature_dir in sorted(REPO_SPECS.iterdir()):
            if not (feature_dir / "tasks.md").exists():
                continue
            p = subprocess.run([sys.executable, str(CHECKER), str(feature_dir)],
                               capture_output=True, text=True, timeout=60)
            case(f"gate-check: specs/{feature_dir.name} still exits 0",
                 p.returncode == 0)

    return results


if __name__ == "__main__":
    rs = run()
    for ok, desc in rs:
        print(("pass" if ok else "FAIL") + "\t" + desc)
    sys.exit(0 if all(p for p, _ in rs) else 1)
