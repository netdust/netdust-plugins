"""
test_spec_gate_check.py — verifies the spec-kit gate checker (spec-kit/gate-check.py).

The checker is the MECHANICAL backstop for the harness's non-test gates: it must FAIL a
spec/plan/tasks set that skips a gate, and PASS one that carries them. The load-bearing
case (ADR Phase B gate): a spec that flags a security surface but whose plan leaves the
## Threat model as N/A must FAIL — that is the proactive 1a gate the harness exists to keep.
"""
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

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
