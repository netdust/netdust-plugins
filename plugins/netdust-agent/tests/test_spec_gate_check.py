"""
test_spec_gate_check.py — verifies the harness gate checker (bin/gate-check.py).

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

CHECKER = Path(__file__).parent.parent / "bin" / "gate-check.py"

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

# ── `success-criteria` fixtures (spec-template.md `## Success criteria`) ─────
# The gate exists so shake-out signs off against a comparison rather than a
# judgement call: every SC line must carry a number. Measurability is tested
# crudely — "the line contains a digit" — which admits `100% of users are
# happy` but catches the failure mode that actually occurs: prose success
# criteria nobody can sign off against.

SPEC_SC_MEASURABLE = """# Feature Specification: Course publishing

## Success criteria

> Feature-level, technology-agnostic, and **measurable** — every line carries a number.

- **SC-1:** an editor publishes a course module in under 3 minutes, unassisted
- **SC-2:** the module list renders in under 500 ms at 4,000 users

## Security-relevant surfaces
- [x] None of the above
"""

# Mixed: SC-1 carries a number, SC-2/SC-3 are prose. FAIL must name the offenders,
# not just report a count — the author needs to know WHICH line to rewrite.
SPEC_SC_VAGUE = """# Feature Specification: Course publishing

## Success criteria

- **SC-1:** an editor publishes a course module in under 3 minutes, unassisted
- **SC-2:** editors find the publishing flow intuitive
- **SC-3:** the module list feels fast

## Security-relevant surfaces
- [x] None of the above
"""

# The section present but never filled in — bracketed `[e.g. …]` bodies exactly as
# templates/spec-template.md ships them. Template guidance is not a criterion, so this
# must FAIL rather than PASS on the placeholder's own digits ("3 minutes", "500 ms").
SPEC_SC_TEMPLATE_UNTOUCHED = """# Feature Specification: [FEATURE NAME]

## Success criteria

> Feature-level, technology-agnostic, and **measurable** — every line carries a number.

- **SC-1:** [e.g. an editor publishes a course module in under 3 minutes, unassisted]
- **SC-2:** [e.g. the module list renders in under 500 ms at 4,000 users]

## Security-relevant surfaces
- [x] None of the above
"""

# A spec authored before the template carried the section at all → WARN, never FAIL.
# Same retro-compat stance as test-author-mode's pre-0.8 WARN: the gate only bites
# once the template is in use. Flip gate-check.py's "warn" to "fail" when every live
# specs/ dir carries the section.
SPEC_PRE_TEMPLATE_NO_SC = """# Feature Specification: Rename a label

## Problem / why

The footer copyright label reads 2019.

## Security-relevant surfaces
- [x] None of the above
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
# is called DIRECTLY (unit-level) here — a deliberate choice to isolate the
# function's own branch logic from the CLI plumbing. It was authored as a RED
# sentinel shell at commit cee7b48 and wired into run_checks() at c8d5087 (see
# gate-check.py:376); the seam (subprocess) tests further down cover the CLI
# floor separately, now exercising the same wired check end-to-end.

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

# A fenced example whose task line is REAL-SHAPED (`T99`, matches TASK_LINE)
# rather than the inert `T<NN>` placeholder above — this is what actually
# exercises the strip_fenced call inside check_test_author_mode: with
# fencing correctly stripped, T99 (and its fenced `Test-author: split` line)
# must never be counted at all, and the verdict must be driven ONLY by the
# 3 real, unfenced tasks below (all 3 carrying the field) -> PASS "all 3
# tasks". If strip_fenced were skipped, T99 would be picked up as a 4th
# real task whose Test-author: line sits at the wrong offset relative to
# the *unfenced* scan (the fence delimiters themselves would shift line
# indices), corrupting the total/verdict — see the mutation-proof below.
TASKS_FENCED_REALSHAPED_TASK_LINE = """# Tasks: x

## Per-task format

```
- [ ] T99 [Tier A] sample
      Test-author: split
```

### Cluster C1
- [ ] T01 [Tier A] validate URL  (files: lib/url.ts)
      Test-author: split
- [ ] T02 [Tier B] wire route  (files: routes.ts)
      Test-author: solo — Tier B
- [ ] T03 [Tier A] pure threshold logic  (files: calc.ts)
      Test-author: solo — A-lite, pure transform, no security-boundary category
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

    # ── `success-criteria` — the spec-stage half of the Stage-0.5 gate ────────
    # Run through the CLI (_run) rather than unit-level, because the WARN-vs-FAIL
    # distinction is only load-bearing via the exit code: a pre-template spec must
    # stay green while a filled-in-but-unmeasurable one must not.

    # 10a. every SC line carries a number → PASS
    rc, out = _run({"spec.md": SPEC_SC_MEASURABLE})
    results.append((rc == 0 and "✓ [success-criteria]" in out,
                    "measurable ## Success criteria PASSES"))

    # 10b. prose SC lines → FAIL, naming the offending ids (not just a count)
    rc, out = _run({"spec.md": SPEC_SC_VAGUE})
    results.append((rc == 1 and "success-criteria" in out
                     and "SC-2" in out and "SC-3" in out and "SC-1" not in out,
                    "SC line with no number FAILs and names SC-2/SC-3 only"))

    # 10c. section present but only untouched `[e.g. …]` placeholders → FAIL
    # (the placeholders' own digits must not be mistaken for a measurement)
    rc, out = _run({"spec.md": SPEC_SC_TEMPLATE_UNTOUCHED})
    results.append((rc == 1 and "success-criteria" in out and "placeholder" in out,
                    "untouched template placeholders FAIL, digits in the example ignored"))

    # 10d. retro-compat: no ## Success criteria section at all → WARN, gate stays PASS
    rc, out = _run({"spec.md": SPEC_PRE_TEMPLATE_NO_SC})
    results.append((rc == 0 and "! [success-criteria]" in out,
                    "pre-template spec with no ## Success criteria WARNs, never FAILs"))

    # ── D1 `test-author-mode` — one fixture per plan.md D1 rules-table row ────
    # check_test_author_mode() is called DIRECTLY (unit level), independent of
    # run_checks()/the CLI, to pin down the function's own branch logic. These
    # assertions were the BEHAVIORAL contract authored RED at commit cee7b48;
    # the function is now wired into run_checks() (c8d5087, gate-check.py:376)
    # and these still hold as the unit-level half of the coverage.

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

    # 17b. a REAL-SHAPED fenced task line (T99, matches TASK_LINE, carrying its
    # own fenced Test-author: line) alongside 3 real unfenced tasks (all 3
    # carrying the field) -> PASS counting the 3 unfenced tasks ONLY. T99
    # must neither count toward "present" nor be reported as "missing"/
    # partial — it must be invisible to the check entirely, proving
    # strip_fenced is actually exercised (the pre-existing fixture's
    # `T<NN>` placeholder never matched TASK_LINE, so this path went
    # unexercised even though the fixture existed).
    f = _gate_check.Findings()
    _gate_check.check_test_author_mode(TASKS_FENCED_REALSHAPED_TASK_LINE, f)
    verdicts = [s for s, c, d in f.items if c == "test-author-mode"]
    details = [d for s, c, d in f.items if c == "test-author-mode"]
    results.append((verdicts == ["pass"]
                     and any(re.search(r"\ball\s+3\s+tasks\b", d) for d in details),
                    "a real-shaped fenced task line (T99) neither counts nor "
                    "FAILs-as-partial; verdict PASSes on the 3 unfenced tasks only"))

    # ── Seam tests: real (un-mocked) subprocess run of gate-check.py ──────────
    # check_test_author_mode is wired into run_checks() (c8d5087, gate-check.py:376)
    # beside check_task_tiers, so these seam tests exercise the live CLI path.
    # #18/#19 assert the retro-compat floor holds unchanged on real spec dirs.
    # #20 is the true seam case: a tasks.md that violates D1 (partial presence)
    # now exits 1 through the live, wired gate — this was the RED seam case
    # authored at cee7b48 and flipped GREEN by the c8d5087 wiring.

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

    # 20. TRUE seam case: a tmp fixture dir violating D1 (partial presence)
    # exits 1 now that test-author-mode is wired into run_checks() (c8d5087,
    # gate-check.py:376, beside check_task_tiers). This was the RED case at
    # cee7b48 before the wiring landed; it now asserts the wired GREEN floor.
    rc, out = _run({"tasks.md": TASKS_PARTIAL_TEST_AUTHOR})
    results.append((rc == 1 and "test-author-mode" in out,
                    "seam: a tmp fixture dir violating D1 (partial presence) exits 1 "
                    "once test-author-mode is wired into run_checks()"))

    return results


if __name__ == "__main__":
    for ok, desc in run():
        print(("pass" if ok else "FAIL") + "\t" + desc)
