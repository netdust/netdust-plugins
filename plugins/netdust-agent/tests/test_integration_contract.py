"""
test_integration_contract.py — `Integration test: <contract>` as a first-class per-task
contract in bin/gate-check.py's unit-test-contract check (1d).

C3 review (I1/I3 + simplicity trims): the checker scans a task's WHOLE continuation
block, collecting every contract/waiver line before deciding — so line ORDER never
changes an outcome. Rules pinned here:
- either form (`Unit test:` / `Integration test:`) states the contract, any tier;
- text after `Integration test:` is always a contract, never a waiver;
- a Tier A task carrying the unit-waiver form (`Unit test: no unit test: Tier B, …`)
  FAILs even when an `Integration test:` line accompanies it, in EITHER order (I1 —
  the shipped 239fc8b checker broke on the first matching line, so integration-then-
  waiver PASSed);
- a task whose ONLY contract is `Integration test:` may not be marked `[P]` (I3 —
  integration tests share one wptests DB with a per-run schema reinstall; serialize);
- partial-presence FAIL and the zero-lines retro-compat WARN keep their outcomes.

RED-first: the integration-then-waiver and integration+[P] fixtures FAIL against the
shipped checker (239fc8b) and flip after the whole-block scan lands. The classic
regression trio (Tier-A unit waiver / classic partial / zero lines) is pinned by
test_spec_gate_check.py cases 10l/m/n and is deliberately NOT duplicated here.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).parent.parent / "bin" / "gate-check.py"

import importlib.util as _ilu

_GATE_SPEC = _ilu.spec_from_file_location("gate_check_module_ic", CHECKER)
_gate_check = _ilu.module_from_spec(_GATE_SPEC)
_GATE_SPEC.loader.exec_module(_gate_check)


# ── fixtures ──────────────────────────────────────────────────────────────────

# CLI smoke: a [Tier A] task whose only contract line is `Integration test:`, beside a
# Tier-B unit-waiver sibling → the whole gate passes end-to-end.
TASKS_TIER_A_INTEGRATION_ONLY = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
      Unit test: no unit test: Tier B, wiring only
- [ ] T02 [Tier A] persistence chain  (files: inc/save.php)
      Test-author: solo — A-lite, WP persistence wiring, no security-boundary category
      Integration test: hooks fire and rows persist; denial: invalid payload persists nothing

**Integration gate (C1):** the wired route persists a row end to end.

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# Mixed file: Unit contracts (incl. the Tier-B waiver form) and Integration contracts
# side by side (T04 = a Tier-B task contracted by an Integration line alone).
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

# Belt+braces: BOTH lines, both real CONTRACTS, on one task → contracted, not an error.
# (This is the only "both fine" shape — a waiver beside an Integration line is I1 below.)
TASKS_BOTH_CONTRACTS_ONE_TASK = """# Tasks: x

### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] persistence chain  (files: inc/save.php)
      Unit test: transform maps payload to row shape; denial: malformed payload rejected
      Integration test: hooks fire and rows persist

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# I1, order 1 (THE RED): Integration line BEFORE the unit-waiver line on a Tier A task.
# The shipped checker (239fc8b) broke on the first matching line, so this PASSed.
# Rule: a Tier A task carrying a unit-waiver line FAILs regardless of any accompanying
# Integration line — the waiver text is a defect or an erosion attempt; loud stop.
TASKS_INTEGRATION_THEN_WAIVER = """# Tasks: x

### Cluster C1  (1 task · provisional tier: FULL)
- [ ] T01 [Tier A] persistence chain  (files: inc/save.php)
      Integration test: hooks fire and rows persist; denial: invalid payload persists nothing
      Unit test: no unit test: Tier B, covered by the integration run

── REVIEW GATE ──  *(tier FULL)*
"""

# I1, order 2: unit-waiver line BEFORE the Integration line — same verdict (the shipped
# checker already FAILed this order; the pair pins order-independence).
TASKS_WAIVER_THEN_INTEGRATION = """# Tasks: x

### Cluster C1  (1 task · provisional tier: FULL)
- [ ] T01 [Tier A] persistence chain  (files: inc/save.php)
      Unit test: no unit test: Tier B, covered by the integration run
      Integration test: hooks fire and rows persist; denial: invalid payload persists nothing

── REVIEW GATE ──  *(tier FULL)*
"""

# I3 (RED): a task whose ONLY contract is `Integration test:` marked [P] → FAIL naming
# it. Integration-contract tasks are never parallel (shared wptests DB, per-run schema
# reinstall). The shipped checker had no such rule.
TASKS_INTEGRATION_PARALLEL = """# Tasks: x

### Cluster C1  (2 tasks · provisional tier: STANDARD)
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Unit test: rejects RFC1918; allows a public https URL
- [ ] T02 [P] [Tier B] cron wiring  (files: inc/cron.php)
      Integration test: the scheduled event fires once and the row lands

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# The no-new-waiver rule: `Integration test: no unit test: Tier B, x` on a [Tier A] task
# is a CONTRACT (odd prose, but stated), NOT a waiver — it must NOT trip "Tier A may not
# waive", and the task counts as contracted.
TASKS_INTEGRATION_NO_WAIVER_FORM = """# Tasks: x

### Cluster C1  (1 task · provisional tier: STANDARD)
- [ ] T01 [Tier A] persistence chain  (files: inc/save.php)
      Integration test: no unit test: Tier B, x

── REVIEW GATE ──  *(STOP: commit C1 — tier STANDARD)*
"""

# Partial presence: T01 Unit-contracted, T03 Integration-contracted, T02 truly bare →
# FAIL must name ONLY T02 (an Integration sibling does not shield a bare task).
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
# the two real tasks below carry no contract line at all, and the file states a legacy
# waiver, so the verdict is the absence WARN that names the waiver, exactly as if the fence
# were absent. (If the fenced line leaked, the verdict would flip to partial-presence FAIL.)
TASKS_FENCED_INTEGRATION_IGNORED = """# Tasks: x

<!-- gate-check: legacy-artifact — predates the per-task test-contract line -->

## Per-task format

```
- [ ] T99 [Tier A] sample
      Integration test: hooks fire and rows persist
```

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire route  (files: routes.ts)
"""


# ── machinery: direct import for unit cases + ONE CLI smoke case ──────────────

def _contract(tasks_text: str):
    """Run check_unit_test_contract directly; return (verdicts, details, failed)."""
    f = _gate_check.Findings()
    _gate_check.check_unit_test_contract(tasks_text, f)
    verdicts = [s for s, c, d in f.items if c == "unit-test-contract"]
    details = [d for s, c, d in f.items if c == "unit-test-contract"]
    return verdicts, details, f.failed


def run():
    results = []

    # 1. CLI smoke: the full gate over a Tier A task contracted only by an Integration
    # line → exit 0, 1d passes (the one subprocess case; everything else imports).
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "tasks.md").write_text(TASKS_TIER_A_INTEGRATION_ONLY)
        proc = subprocess.run([sys.executable, str(CHECKER), d],
                              capture_output=True, text=True, timeout=15)
    results.append((proc.returncode == 0 and "✓ [unit-test-contract]" in proc.stdout,
                    "CLI smoke: a Tier A task contracted by `Integration test:` alone "
                    "passes the whole gate (exit 0)"))

    # 2. mixed Unit + Integration file (incl. Tier-B integration-only T04) → pass.
    verdicts, details, failed = _contract(TASKS_MIXED_CONTRACTS)
    results.append((verdicts == ["pass"] and not failed,
                    "mixed Unit/Integration contracts pass 1d"))

    # 3. belt+braces: BOTH real contracts on one task → contracted, no error.
    verdicts, details, failed = _contract(TASKS_BOTH_CONTRACTS_ONE_TASK)
    results.append((verdicts == ["pass"] and not failed,
                    "a task carrying a Unit CONTRACT and an Integration contract "
                    "passes (belt+braces)"))

    # 4. I1 order 1 (RED vs 239fc8b): Integration line, THEN the unit-waiver line, on
    # Tier A → FAIL "Tier A may not waive" — the accompanying contract does not launder
    # the waiver.
    verdicts, details, failed = _contract(TASKS_INTEGRATION_THEN_WAIVER)
    results.append((verdicts == ["fail"]
                     and any("Tier A may not waive" in d for d in details),
                    "Tier A: `Integration test:` before the unit-waiver line still "
                    "FAILs 'Tier A may not waive' (order-independent)"))

    # 5. I1 order 2: waiver first, Integration second → same FAIL (the pair proves
    # order-independence).
    verdicts, details, failed = _contract(TASKS_WAIVER_THEN_INTEGRATION)
    results.append((verdicts == ["fail"]
                     and any("Tier A may not waive" in d for d in details),
                    "Tier A: unit-waiver line before `Integration test:` FAILs "
                    "'Tier A may not waive' (order-independent)"))

    # 6. I3 (RED vs 239fc8b): only-Integration contract + [P] on the task line → FAIL
    # naming the task (integration contracts are never parallel).
    verdicts, details, failed = _contract(TASKS_INTEGRATION_PARALLEL)
    results.append((verdicts == ["fail"]
                     and any("[P]" in d and "T02" in d and "T01" not in d
                             for d in details),
                    "an Integration-contract task marked [P] FAILs, naming it (T02)"))

    # 7. no-new-waiver: `Integration test: no unit test: …` on Tier A is a CONTRACT —
    # must NOT trip "Tier A may not waive"; verdict is pass.
    verdicts, details, failed = _contract(TASKS_INTEGRATION_NO_WAIVER_FORM)
    results.append((verdicts == ["pass"] and not failed
                     and not any("may not waive" in d for d in details),
                    "`Integration test: no unit test: …` on Tier A reads as a CONTRACT "
                    "(no waiver form exists inside Integration test:)"))

    # 8. partial presence: an Integration-contracted sibling does not shield the truly
    # bare task — FAIL names ONLY T02.
    verdicts, details, failed = _contract(TASKS_PARTIAL_WITH_INTEGRATION_SIBLING)
    results.append((verdicts == ["fail"]
                     and any("T02" in d and "T03" not in d and "T01" not in d
                             for d in details),
                    "a bare task among Unit- and Integration-contracted siblings still "
                    "FAILs, naming only the bare one (T02)"))

    # 9. a fenced `Integration test:` example never counts — the real bare tasks (waived)
    # still land on the absence WARN naming the waiver, not on partial-presence FAIL.
    verdicts, details, failed = _contract(TASKS_FENCED_INTEGRATION_IGNORED)
    results.append((verdicts == ["warn"] and not failed
                     and any("legacy waiver exercised" in d for d in details),
                    "a fenced `Integration test:` example is stripped and never counted "
                    "(absence WARN names the waiver)"))

    # ── seam: the real checker over the real spec corpus (SC-1) ───────────────
    # An absent dir is a distinct `skip`, never a silent pass, and the module FAILs if
    # NO corpus ran at all (skip-as-pass would let the live regression rot away).
    corpora_ran = 0
    for spec_dir, label in [
        (Path.home() / "Sites/netdust-wp-manager/specs/wp-gate-harness",
         "specs/wp-gate-harness"),
        (Path.home() / "Sites/netdust-wp-manager/specs/harness-gate-adaptations",
         "specs/harness-gate-adaptations"),
    ]:
        if not spec_dir.is_dir():
            results.append((True, f"skip: {label} not present on this machine "
                                  "(counted below — skip is not pass)"))
            continue
        corpora_ran += 1
        proc = subprocess.run([sys.executable, str(CHECKER), str(spec_dir)],
                              capture_output=True, text=True, timeout=15)
        results.append((proc.returncode == 0 and "✓ [unit-test-contract]" in proc.stdout,
                        f"seam: gate-check.py on {label} exits 0, 1d passes (live corpus)"))
    results.append((corpora_ran >= 1,
                    f"seam: at least one live spec corpus ran ({corpora_ran}/2 — "
                    "skip is not pass)"))

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
