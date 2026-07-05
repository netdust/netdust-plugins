"""
test_spec_gate_check.py — verifies the spec-kit gate checker (spec-kit/gate-check.py).

The checker is the MECHANICAL backstop for the harness's non-test gates: it must FAIL a
spec/plan/tasks set that skips a gate, and PASS one that carries them. The load-bearing
case (ADR Phase B gate): a spec that flags a security surface but whose plan leaves the
## Threat model as N/A must FAIL — that is the proactive 1a gate the harness exists to keep.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKER = Path(__file__).parent.parent / "spec-kit" / "gate-check.py"

# ── fixtures ──────────────────────────────────────────────────────────────────

SPEC_TRIGGERED = """# Feature Specification: Webhook receiver

## Security-relevant surfaces
- [x] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] None of the above

## Open questions / [NEEDS CLARIFICATION]
[List remaining ambiguities as `[NEEDS CLARIFICATION: …]`. This section must be empty.]
"""

SPEC_CLEAN_NOSEC = """# Feature Specification: Rename a label

## Security-relevant surfaces
- [ ] User-controlled URLs / server-side outbound requests
- [x] None of the above

## Clarifications
- Q: which label? → A: the footer copyright label
"""

SPEC_WITH_UNRESOLVED = """# Feature Specification: Importer

## Functional requirements
- FR-1: import a CSV [NEEDS CLARIFICATION: max file size?]

## Security-relevant surfaces
- [x] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
"""

PLAN_GATES_FULL = """# Implementation Plan: Webhook receiver

## Constitution check  [GATE]
- [x] No RULES.md non-negotiable violated.

## Threat model  [GATE]
> guidance blockquote that should be ignored by the checker
### Attacks → Mitigations
1. **SSRF via webhook URL → resolves to RFC1918** → **shared validator in lib/url.ts, called from both routes**

## Architecture invariants touched  [GATE]
N/A — no convergence point touched.

## Spec-premise ground-truth  [GATE]
N/A — no reuse premise.

## Phases & review clusters  [GATE]
See tasks.md.
"""

PLAN_THREATMODEL_NA = """# Implementation Plan: Webhook receiver

## Constitution check  [GATE]
- [x] ok

## Threat model  [GATE]
N/A — small feature.

## Architecture invariants touched  [GATE]
N/A.

## Spec-premise ground-truth  [GATE]
N/A.

## Phases & review clusters  [GATE]
See tasks.md.
"""

PLAN_MISSING_HEADING = """# Implementation Plan: Webhook receiver

## Constitution check  [GATE]
- [x] ok

## Threat model  [GATE]
1. **x → y** → **z**

## Spec-premise ground-truth  [GATE]
N/A.

## Phases & review clusters  [GATE]
See tasks.md.
"""

TASKS_GOOD = """# Tasks: Webhook receiver

## Phase 1 — receiver

### Cluster C1  (<=4 tasks)
- [ ] T01 [P] [Tier A] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire route  (files: routes.ts)

── REVIEW GATE ──

### Cluster C2 — (irreversible: drop legacy table) — solo
- [ ] T03 [Tier A] migration  (files: migrations/001.sql)

── REVIEW GATE ──
"""

TASKS_NO_TIER = """# Tasks: x

### Cluster C1
- [ ] T01 [P] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire  (files: r.ts)
"""

TASKS_OVERSIZED = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] a  (f: a)
- [ ] T02 [Tier A] b  (f: b)
- [ ] T03 [Tier A] c  (f: c)
- [ ] T04 [Tier A] d  (f: d)
- [ ] T05 [Tier A] e  (f: e)
"""

TASKS_IRREVERSIBLE_PARALLEL = """# Tasks: x

### Cluster C1 — (irreversible: teardown) — solo
- [ ] T01 [P] [Tier A] drop table  (f: m.sql)
"""

# ── D1 `test-author-mode` fixtures (plan.md section D1 rules table) ──────────
# gate-check.py: from `plugins.netdust_agent... ` — imported directly below via
# importlib since this file already resolves CHECKER by path; check_test_author_mode
# is called DIRECTLY (unit-level) — it is NOT yet wired into run_checks()/main(),
# so these are NOT subprocess/CLI assertions. The seam (subprocess) tests further
# down cover the CLI floor separately.

import importlib.util as _ilu

_GATE_SPEC = _ilu.spec_from_file_location("gate_check_module", CHECKER)
_gate_check = _ilu.module_from_spec(_GATE_SPEC)
_GATE_SPEC.loader.exec_module(_gate_check)

# Row: "No task in the file carries a `Test-author:` line" → WARN, never FAIL
# (this is retro-compat: a run-observability-shaped tasks.md must never retro-fail)
TASKS_NO_TEST_AUTHOR_LINES = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
- [ ] T02 [Tier B] wire route  (files: routes.ts)
"""

# Row: "Some tasks carry it, some don't" → FAIL, naming the bare task ids
TASKS_PARTIAL_TEST_AUTHOR = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
- [ ] T02 [Tier B] wire route  (files: routes.ts)
- [ ] T03 [Tier B] docs tweak  (files: README.md)
      Test-author: solo — Tier B
"""

# Row: "Value not `split` or `solo…`" → FAIL
TASKS_INVALID_VALUE = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: maybe
"""

# Row: "[Tier A] task with `solo` and no reason text after a dash" → FAIL
TASKS_TIER_A_SOLO_NO_REASON = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: solo
"""

# Row: "[Tier B] task with `split`" → WARN (over-ceremony)
TASKS_TIER_B_SPLIT = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier B] rename a label  (files: labels.ts)
      Test-author: split
"""

# Row: "All present and coherent" → PASS
TASKS_ALL_COHERENT = """# Tasks: x

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
- [ ] T03 [Tier A] pure threshold logic  (files: calc.ts)
      Test-author: solo — A-lite, pure transform, no security-boundary category
"""

# A FENCED `Test-author:` example (as tasks-template.md ships) must never count —
# neither as "present" (it's documentation, not a real task's mode) nor trip the
# partial-presence FAIL. Wrapping TASKS_NO_TEST_AUTHOR_LINES's real tasks with a
# fenced per-task-format example ahead of them must still yield the WARN verdict,
# not FAIL, and the fenced line's task-like content (`T<NN>`) must not be treated
# as a real task either.
TASKS_FENCED_EXAMPLE_IGNORED = """# Tasks: x

## Per-task format

```
- [ ] T<NN> [P?] [Tier A|B] <imperative description>  (files: <paths>)
      Test-author: <split | solo — reason>  (D1 rule: split iff Tier A on a security-boundary
                  category — auth/guards, untrusted parsing, migrations, money, 1a surface)
```

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


def run():
    results = []

    # 1. THE load-bearing case: triggered surface + N/A threat model → FAIL
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_THREATMODEL_NA, "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "threat-model" in out,
                    "triggered surface + N/A threat model FAILS the gate"))

    # 2. triggered surface WITH a substantive threat model → PASS
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_GATES_FULL, "tasks.md": TASKS_GOOD})
    results.append((rc == 0, "triggered surface + substantive threat model PASSES"))

    # 3. no security surface + N/A threat model → PASS (legitimate)
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC, "plan.md": PLAN_THREATMODEL_NA, "tasks.md": TASKS_GOOD})
    results.append((rc == 0, "no security surface + N/A threat model PASSES"))

    # 4. unresolved [NEEDS CLARIFICATION] in spec → FAIL (Stage 0.5 HALT)
    rc, out = _run({"spec.md": SPEC_WITH_UNRESOLVED})
    results.append((rc == 1 and "clarify-halt" in out,
                    "unresolved [NEEDS CLARIFICATION] HALTS (spec-only stage)"))

    # 5. clean spec (template guidance present but no real marker) → PASS clarify
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC})
    results.append((rc == 0, "template guidance is not mistaken for an unresolved marker"))

    # 6. missing a required [GATE] heading (invariants) → FAIL
    rc, out = _run({"spec.md": SPEC_CLEAN_NOSEC, "plan.md": PLAN_MISSING_HEADING, "tasks.md": TASKS_GOOD})
    results.append((rc == 1 and "Architecture invariants" in out,
                    "missing required [GATE] heading FAILS"))

    # 7. a task without a test tier → FAIL
    rc, out = _run({"tasks.md": TASKS_NO_TIER})
    results.append((rc == 1 and "task-tier" in out, "task missing a test tier FAILS"))

    # 8. oversized cluster (>4 tasks) → FAIL
    rc, out = _run({"tasks.md": TASKS_OVERSIZED})
    results.append((rc == 1 and "review-cluster" in out, "cluster with >4 tasks FAILS"))

    # 9. irreversible cluster with a [P] task → FAIL
    rc, out = _run({"tasks.md": TASKS_IRREVERSIBLE_PARALLEL})
    results.append((rc == 1 and "review-cluster" in out, "irreversible cluster marked [P] FAILS"))

    # 10. fully good set → PASS
    rc, out = _run({"spec.md": SPEC_TRIGGERED, "plan.md": PLAN_GATES_FULL, "tasks.md": TASKS_GOOD})
    results.append((rc == 0 and "GATE: PASS" in out, "complete, gate-bearing set PASSES"))

    # ── D1 `test-author-mode` — one fixture per plan.md D1 rules-table row ────
    # check_test_author_mode() is called DIRECTLY (unit level): it exists as a
    # signature shell in gate-check.py but is NOT wired into run_checks() yet,
    # so calling run_checks()/the CLI would never reach it. These assertions are
    # the BEHAVIORAL contract the implementer must satisfy once wired.

    # 11. retro-compat: zero Test-author: lines anywhere → WARN, GATE stays PASS
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_NO_TEST_AUTHOR_LINES, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["warn"] and not f.failed,
                    "zero Test-author: lines (run-observability-shaped) WARNs, never FAILs"))

    # 12. partial presence → FAIL, naming the bare task ids (T02 here)
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_PARTIAL_TEST_AUTHOR, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"] and any("T02" in d for d in details),
                    "partial Test-author: presence FAILs and names the bare task id (T02)"))

    # 13. invalid value (not split/solo) → FAIL
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_INVALID_VALUE, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"],
                    "Test-author: value other than split/solo FAILs"))

    # 14. [Tier A] + solo with no reason after a dash → FAIL
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_TIER_A_SOLO_NO_REASON, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["fail"],
                    "[Tier A] task with solo and no stated reason FAILs"))

    # 15. [Tier B] + split → WARN (over-ceremony), gate does not fail on this alone
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_TIER_B_SPLIT, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["warn"] and not f.failed,
                    "[Tier B] task with split WARNs as over-ceremony, does not FAIL"))

    # 16. all present and coherent → PASS
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_ALL_COHERENT, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["pass"]
                     and any(re.search(r"\ball\s+3\s+tasks\b", d) for d in details),
                    "all tasks carrying a coherent Test-author: mode PASSes"))

    # 17. a FENCED Test-author: example must never count — same real tasks as #11
    # (no real Test-author: lines outside the fence) must still WARN, not FAIL,
    # and the fenced example's own line must not be double-counted as "present".
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_FENCED_EXAMPLE_IGNORED, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["warn"] and not f.failed,
                    "a fenced Test-author: example is stripped and never counted"))

    # ── Seam tests: real (un-mocked) subprocess run of gate-check.py ──────────
    # NOTE: check_test_author_mode is intentionally NOT wired into run_checks()
    # yet (signature-shell only) — the live CLI's behavior on real dirs must stay
    # unchanged until the implementer wires it. #18/#19 are expected to pass NOW
    # (they assert the unchanged floor). #20 is the true RED seam case: it proves
    # a tasks.md that violates D1 does NOT yet fail the live gate — because the
    # check isn't wired in. Once wired, #20 must flip to exit 1.

    # 18. real script against specs/run-observability (zero Test-author: lines) → exit 0
    repo_root = Path(__file__).parent.parent.parent.parent
    ro_dir = repo_root / "specs" / "run-observability"
    proc = subprocess.run([sys.executable, str(CHECKER), str(ro_dir)],
                           capture_output=True, text=True, timeout=15)
    results.append((proc.returncode == 0,
                    "seam: gate-check.py on specs/run-observability still exits 0 (retro-compat live)"))

    # 19. real script against specs/harness-efficiency (dogfoods the field) → exit 0
    he_dir = repo_root / "specs" / "harness-efficiency"
    proc = subprocess.run([sys.executable, str(CHECKER), str(he_dir)],
                           capture_output=True, text=True, timeout=15)
    results.append((proc.returncode == 0,
                    "seam: gate-check.py on specs/harness-efficiency (dogfood) exits 0"))

    # 20. TRUE RED seam case: a tmp fixture dir violating D1 (partial presence)
    # must exit 1 once test-author-mode is wired into run_checks(). Pre-wiring,
    # this is expected to still exit 0 (the check never runs live) — that is the
    # correct floor the implementer must flip to 1 by wiring check_test_author_mode
    # into run_checks() beside check_task_tiers.
    rc, out = _run({"tasks.md": TASKS_PARTIAL_TEST_AUTHOR})
    results.append((rc == 1 and "test-author-mode" in out,
                    "seam: a tmp fixture dir violating D1 (partial presence) exits 1 "
                    "once test-author-mode is wired into run_checks()"))

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
