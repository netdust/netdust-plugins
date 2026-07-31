"""
test_integration_contract.py — `Integration test: <contract>` as a first-class per-task
contract in bin/gate-check.py's unit-test-contract check (1d).

T07 (harness-gate-adaptations, FR-5/SC-1): a task may state its behavioral contract on a
`  Unit test: ...` continuation line OR a `  Integration test: ...` continuation line —
for ANY tier. There is NO waiver form inside `Integration test:` (only the existing
`Unit test: no unit test: Tier B, <reason>` remains a waiver; `Integration test: no ...`
reads as a CONTRACT). Both lines on one task is belt+braces, not an error; the first
matching line wins for reporting. Partial-presence FAIL, Tier-A-waiver FAIL, and the
zero-lines retro-compat WARN keep their existing outcomes.

RED-first: the new-behavior fixtures below FAIL against the shipped checker (1dc9bef) —
the Integration-only task is counted as bare, so partial-presence names it — and flip to
PASS after the grammar lands. The regression fixtures hold the same outcome before and
after (baselines recorded against the shipped checker before implementation).
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).parent.parent / "bin" / "gate-check.py"

import importlib.util as _ilu

_GATE_SPEC = _ilu.spec_from_file_location("gate_check_module_ic", CHECKER)
_gate_check = _ilu.module_from_spec(_GATE_SPEC)
_GATE_SPEC.loader.exec_module(_gate_check)


# ── new-behavior fixtures (RED against the shipped checker → GREEN after) ─────

# (a) A [Tier A] task whose only contract line is `Integration test:`, beside a
# Unit-contracted sibling. TODAY: the sibling makes the convention "in use", so T02 is
# counted bare → partial-presence FAIL naming T02. AFTER: both tasks are contracted → PASS.
TASKS_TIER_A_INTEGRATION_ONLY = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier B] wire route  (files: routes.ts)
      Unit test: no unit test: Tier B, wiring only
- [ ] T02 [Tier A] persistence chain  (files: inc/save.php)
      Integration test: hooks fire and rows persist; denial: invalid payload persists nothing

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# (b) Same flip for a [Tier B] task carrying only an Integration line.
TASKS_TIER_B_INTEGRATION_ONLY = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects RFC1918; allows a public https URL
- [ ] T02 [Tier B] cron wiring  (files: inc/cron.php)
      Integration test: the scheduled event fires once and the row lands

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# (c) Mixed file: Unit contracts (incl. the Tier-B waiver form) and Integration contracts
# side by side → AFTER: PASS, and the pass message reflects reality ("test contract",
# integration lines counted) instead of claiming every task states a `Unit test:` line.
TASKS_MIXED_CONTRACTS = """# Tasks: x

### Cluster C1  (4 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects RFC1918; allows a public https URL
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Unit test: no unit test: Tier B, wiring only
- [ ] T03 [Tier A] persistence chain  (files: inc/save.php)
      Integration test: hooks fire and rows persist; denial: invalid payload persists nothing
- [ ] T04 [Tier B] cron wiring  (files: inc/cron.php)
      Integration test: the scheduled event fires once and the row lands

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# Belt+braces: one task carrying BOTH lines is contracted, not an error.
TASKS_BOTH_LINES_ONE_TASK = """# Tasks: x

### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] persistence chain  (files: inc/save.php)
      Unit test: transform maps payload to row shape; denial: malformed payload rejected
      Integration test: hooks fire and rows persist

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# The no-new-waiver rule: `Integration test: no unit test: Tier B, x` on a [Tier A] task is
# a CONTRACT (odd prose, but stated), NOT a waiver — it must NOT trip "Tier A may not
# waive", and the task counts as contracted. (Baseline against the shipped checker: the
# line is unrecognized, so this file WARNs as pre-contract — recorded before the change.)
TASKS_INTEGRATION_NO_WAIVER_FORM = """# Tasks: x

### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] persistence chain  (files: inc/save.php)
      Integration test: no unit test: Tier B, x

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# Partial presence under the NEW grammar: T01 Unit-contracted, T03 Integration-contracted,
# T02 truly bare → FAIL must name ONLY T02.
TASKS_PARTIAL_WITH_INTEGRATION_SIBLING = """# Tasks: x

### Cluster C1  (3 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects RFC1918; allows a public https URL
- [ ] T02 [Tier A] parse the payload  (files: lib/parse.ts)
- [ ] T03 [Tier B] cron wiring  (files: inc/cron.php)
      Integration test: the scheduled event fires once and the row lands

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# A FENCED `Integration test:` example (a plan's per-task format block) must never count —
# the two real tasks below carry no contract line at all, so the verdict must stay the
# retro-compat WARN, exactly as if the fence were absent.
TASKS_FENCED_INTEGRATION_IGNORED = """# Tasks: x

## Per-task format

```
- [ ] T99 [Tier A] sample
      Integration test: hooks fire and rows persist
```

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire route  (files: routes.ts)
"""

# ── regression fixtures (same outcome before AND after the change) ────────────
# Baselines recorded by running this module against the shipped checker (1dc9bef):
# R1 FAIL "Tier A may not waive", R2 FAIL naming T02 only, R3 WARN never FAIL.

# R1: a Tier A task waiving via the Unit-line waiver form → FAIL (rules unchanged).
TASKS_TIER_A_WAIVES = """# Tasks: x

### Cluster C1  (1 task · provisional tier: FULL)
- [ ] T01 [Tier A] rewrite the auth token store  (files: db/tokens.sql)
      Unit test: no unit test: it is mostly SQL

── REVIEW GATE ──  *(tier FULL)*
"""

# R2: classic partial presence — Unit-contracted siblings, one bare task → FAIL naming it.
TASKS_PARTIAL_CLASSIC = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects RFC1918; allows a public https URL
- [ ] T02 [Tier A] parse the payload  (files: lib/parse.ts)

── REVIEW GATE ──  *(tier STANDARD)*
"""

# R3: zero contract lines of EITHER form anywhere → retro-compat WARN, never FAIL.
TASKS_ZERO_CONTRACT_LINES = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire route  (files: routes.ts)
"""


def _run(files: dict) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as d:
        for name, content in files.items():
            (Path(d) / name).write_text(content)
        proc = subprocess.run([sys.executable, str(CHECKER), d],
                               capture_output=True, text=True, timeout=15)
        return proc.returncode, proc.stdout + proc.stderr


def _contract(tasks_text: str):
    """Run check_unit_test_contract directly; return (verdicts, details, failed)."""
    f = _gate_check.Findings()
    _gate_check.check_unit_test_contract(tasks_text, f)
    verdicts = [s for s, c, d in f.items if c == "unit-test-contract"]
    details = [d for s, c, d in f.items if c == "unit-test-contract"]
    return verdicts, details, f.failed


def run():
    results = []

    # ── new behavior: `Integration test:` is a stated contract ───────────────

    # 1. THE flip case (RED proof): Tier A task contracted only by an Integration line,
    # beside a Unit-contracted sibling → PASS through the live CLI (was: exit 1,
    # partial-presence naming T02).
    rc, out = _run({"tasks.md": TASKS_TIER_A_INTEGRATION_ONLY})
    results.append((rc == 0 and "✓ [unit-test-contract]" in out,
                    "a Tier A task contracted by `Integration test:` alone PASSes 1d "
                    "(was: partial-presence FAIL naming it)"))

    # 2. same flip for Tier B (unit level): verdict is pass, nothing named missing.
    verdicts, details, failed = _contract(TASKS_TIER_B_INTEGRATION_ONLY)
    results.append((verdicts == ["pass"] and not failed,
                    "a Tier B task contracted by `Integration test:` alone passes 1d"))

    # 3. mixed Unit + Integration file → pass, and the message reflects reality:
    # it reports a test contract for all 4 (not a `Unit test:` line on all 4).
    verdicts, details, failed = _contract(TASKS_MIXED_CONTRACTS)
    results.append((verdicts == ["pass"]
                     and any(re.search(r"\ball 4 tasks state a test contract\b", d)
                             and "Integration test:" in d for d in details),
                    "mixed Unit/Integration contracts pass with the all-contracted "
                    "message reflecting both forms"))

    # 4. belt+braces: BOTH lines on one task → contracted, no error.
    verdicts, details, failed = _contract(TASKS_BOTH_LINES_ONE_TASK)
    results.append((verdicts == ["pass"] and not failed,
                    "a task carrying BOTH a Unit and an Integration line counts as "
                    "contracted (belt+braces, not an error)"))

    # 5. NO-NEW-WAIVER: `Integration test: no unit test: Tier B, x` on a Tier A task is a
    # CONTRACT, not a waiver — must NOT trip "Tier A may not waive"; verdict is pass.
    verdicts, details, failed = _contract(TASKS_INTEGRATION_NO_WAIVER_FORM)
    results.append((verdicts == ["pass"] and not failed
                     and not any("may not waive" in d for d in details),
                    "`Integration test: no unit test: …` on Tier A reads as a CONTRACT "
                    "(no waiver form exists inside Integration test:)"))

    # 6. partial presence under the new grammar: an Integration-contracted sibling does
    # not shield the truly bare task — FAIL names ONLY T02.
    verdicts, details, failed = _contract(TASKS_PARTIAL_WITH_INTEGRATION_SIBLING)
    results.append((verdicts == ["fail"]
                     and any("T02" in d and "T03" not in d and "T01" not in d
                             for d in details),
                    "a bare task among Unit- and Integration-contracted siblings still "
                    "FAILs, naming only the bare one (T02)"))

    # 7. a fenced `Integration test:` example never counts — real bare tasks still WARN.
    verdicts, details, failed = _contract(TASKS_FENCED_INTEGRATION_IGNORED)
    results.append((verdicts == ["warn"] and not failed,
                    "a fenced `Integration test:` example is stripped and never counted"))

    # ── regressions: every pre-existing unit-test-contract outcome unchanged ──

    # 8. R1: Tier A waiving via the Unit waiver form → FAIL "Tier A may not waive".
    verdicts, details, failed = _contract(TASKS_TIER_A_WAIVES)
    results.append((verdicts == ["fail"]
                     and any("Tier A may not waive" in d for d in details),
                    "regression: Tier A `Unit test: no unit test:` waiver still FAILs"))

    # 9. R2: classic partial presence → FAIL naming the bare task (T02).
    verdicts, details, failed = _contract(TASKS_PARTIAL_CLASSIC)
    results.append((verdicts == ["fail"] and any("T02" in d for d in details),
                    "regression: partial presence still FAILs naming the bare task"))

    # 10. R3: zero contract lines anywhere → WARN, never FAIL.
    verdicts, details, failed = _contract(TASKS_ZERO_CONTRACT_LINES)
    results.append((verdicts == ["warn"] and not failed,
                    "regression: zero contract lines WARNs as pre-contract, never FAILs"))

    # ── seam: the real checker over the real spec corpus (SC-1) ───────────────

    # 11/12. Both live spec dirs still exit 0 and still pass 1d — the live regression.
    # (The old-vs-new output diff is run at commit time outside this module; here the
    # test pins the exit-code floor so a future grammar change cannot silently re-fail
    # the shipped corpus.)
    for spec_dir, label in [
        (Path.home() / "Sites/netdust-wp-manager/specs/wp-gate-harness",
         "specs/wp-gate-harness"),
        (Path.home() / "Sites/netdust-wp-manager/specs/harness-gate-adaptations",
         "specs/harness-gate-adaptations"),
    ]:
        if not spec_dir.is_dir():
            results.append((True, f"seam: {label} not present on this machine — skipped"))
            continue
        proc = subprocess.run([sys.executable, str(CHECKER), str(spec_dir)],
                               capture_output=True, text=True, timeout=15)
        results.append((proc.returncode == 0 and "✓ [unit-test-contract]" in proc.stdout,
                        f"seam: gate-check.py on {label} exits 0, 1d passes (live corpus)"))

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
