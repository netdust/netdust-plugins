#!/usr/bin/env python3
"""gate-check.py — deterministic verification that a feature directory
carries the netdust harness gates.

Used by:
  - spec-authoring  (Stage 0.5): with only spec.md present
                    → enforces the [NEEDS CLARIFICATION] HALT.
  - spec-analysis   (Stage 1.5): with spec.md + plan.md + tasks.md
                    → enforces gate-presence (threat model, invariants, spec-premise,
                      review clusters) + per-task test tiers + the [P]/cluster rules.

It checks whatever of spec.md / plan.md / tasks.md exist, so the same tool serves both
stages. This is the MECHANICAL backstop that turns the harness's previously skill-honored
non-test gates into a verifiable check — the sibling of subagent-stop.py for the testing gate.

Usage:
    gate-check.py <feature-spec-dir>      # dir containing spec.md / plan.md / tasks.md
    gate-check.py --json <dir>

Exit code: 0 if no FAIL findings, 1 otherwise. WARN findings never fail the gate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ── section / line helpers ────────────────────────────────────────────────────

HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
TASK_LINE = re.compile(r"^- \[[ xX]\]\s+(T\d+)\b(.*)$")
CLUSTER_HEADING = re.compile(r"^###\s+Cluster\b(.*)$", re.IGNORECASE)


def heading_text(line: str) -> tuple[int, str] | None:
    m = HEADING.match(line)
    if not m:
        return None
    return len(m.group(1)), m.group(2).strip()


def section_body(text: str, name: str) -> str | None:
    """Return the body under the first `## <name>` heading (any [GATE] suffix tolerated),
    up to the next heading of level <= 2. None if the heading is absent."""
    lines = text.splitlines()
    start = None
    for i, line in enumerate(lines):
        h = heading_text(line)
        if h and h[0] == 2 and h[1].split("[")[0].strip().lower() == name.lower():
            start = i + 1
            break
    if start is None:
        return None
    body = []
    for line in lines[start:]:
        h = heading_text(line)
        if h and h[0] <= 2:
            break
        body.append(line)
    return "\n".join(body)


# ── checks ────────────────────────────────────────────────────────────────────

class Findings:
    def __init__(self) -> None:
        self.items: list[tuple[str, str, str]] = []  # (status, check, detail)

    def add(self, status: str, check: str, detail: str) -> None:
        self.items.append((status, check, detail))

    @property
    def failed(self) -> bool:
        return any(s == "fail" for s, _, _ in self.items)


# real unresolved marker = [NEEDS CLARIFICATION: <substance>], not a heading, not backticked,
# not the template's `…`/`...` placeholder example.
CLAR_MARKER = re.compile(r"\[NEEDS CLARIFICATION:([^\]]*)\]")


def check_clarify(spec_text: str, f: Findings) -> None:
    unresolved = []
    for ln in spec_text.splitlines():
        if ln.lstrip().startswith("#"):
            continue
        for m in CLAR_MARKER.finditer(ln):
            content = m.group(1).strip()
            if content in ("", "…", "...", "specific question"):
                continue  # template guidance / placeholder, not a real marker
            # ignore backtick-wrapped examples
            s = ln[: m.start()].count("`")
            if s % 2 == 1:
                continue
            unresolved.append(content)
    if unresolved:
        f.add("fail", "clarify-halt",
              f"{len(unresolved)} unresolved [NEEDS CLARIFICATION] marker(s): "
              + "; ".join(unresolved[:5]))
    else:
        f.add("pass", "clarify-halt", "no unresolved [NEEDS CLARIFICATION] markers")


# SC line = `- **SC-1:** <text>`; measurable means the text carries a digit. A body that is
# only a bracketed placeholder (`[e.g. …]`) is placeholder text, not a criterion.
SC_LINE = re.compile(r"^\s*[-*]\s+\**SC-(\d+)\**\s*:?\s*\**\s*(.*)$")
PLACEHOLDER = re.compile(r"^\[.*\]$")
DIGIT = re.compile(r"\d")


def check_success_criteria(spec_text: str, f: Findings) -> None:
    """Feature-level success must be measurable — this is what shake-out signs off against.

    FAIL: no `## Success criteria` section · section present but no SC line survives the
    placeholder filter · an SC line carrying no number (unmeasurable by construction).
    """
    body = section_body(spec_text, "Success criteria")
    if body is None:
        # Spec predates the contract (same retro-compat stance as test-author-mode). The two
        # live specs/ dirs are the only reason this is not "fail" — flip it once they carry
        # the section. The contract itself lives in the spec-authoring skill, not a template.
        f.add("warn", "success-criteria", "no ## Success criteria section (spec predates the contract)")
        return

    real, unmeasurable = [], []
    for ln in body.splitlines():
        m = SC_LINE.match(ln)
        if not m:
            continue
        sc_id, text = f"SC-{m.group(1)}", m.group(2).strip()
        if not text or PLACEHOLDER.match(text):
            continue  # untouched template line
        real.append(sc_id)
        if not DIGIT.search(text):
            unmeasurable.append(sc_id)

    if not real:
        f.add("fail", "success-criteria",
              "## Success criteria has no filled-in SC line (template placeholders only)")
        return
    if unmeasurable:
        f.add("fail", "success-criteria",
              f"{len(unmeasurable)}/{len(real)} criterion/criteria carry no number: "
              + ", ".join(unmeasurable[:5]))
        return
    f.add("pass", "success-criteria", f"{len(real)} measurable criterion/criteria: "
          + ", ".join(real[:8]))


REQUIRED_PLAN_GATES = [
    "Constitution check",
    "Threat model",
    "Architecture invariants touched",
    "Spec-premise ground-truth",
    "Phases & review clusters",
]


def check_plan_gates(plan_text: str, f: Findings) -> None:
    for name in REQUIRED_PLAN_GATES:
        if section_body(plan_text, name) is None:
            f.add("fail", "plan-gate-heading", f"missing required [GATE] section: ## {name}")
        else:
            f.add("pass", "plan-gate-heading", f"## {name} present")


SURFACE_NONE = re.compile(r"none of the above", re.IGNORECASE)
CHECKED_BOX = re.compile(r"^\s*- \[[xX]\]\s+(.*)$")
NUMBERED_ATTACK = re.compile(r"^\s*\d+\.\s+.*(\*\*|→|->)")


def spec_security_triggered(spec_text: str) -> list[str]:
    """Any checked box under 'Security-relevant surfaces' that isn't 'None of the above'."""
    body = section_body(spec_text, "Security-relevant surfaces")
    if body is None:
        return []
    hits = []
    for ln in body.splitlines():
        m = CHECKED_BOX.match(ln)
        if m and not SURFACE_NONE.search(m.group(1)):
            hits.append(m.group(1).strip())
    return hits


SURFACE_BOX = re.compile(r"^\s*- \[([ xX])\]\s+(.*)$")


def check_security_surfaces(spec_text: str, f: Findings) -> None:
    """The arming switch for the plan's 1a gate — and the one check whose absence is
    invisible rather than loud.

    A `## Security-relevant surfaces` section that is missing, or present with every box
    blank, makes `spec_security_triggered()` return nothing. check_threat_model then reads
    "no surface flagged", a plan's `N/A — small feature` PASSES, and the checker prints
    reassurance. So an auth feature reaches execution with no threat model, by INACTION.
    Blank is not "none": answer the surfaces that apply, or "None of the above" explicitly.
    """
    body = section_body(spec_text, "Security-relevant surfaces")
    if body is None:
        f.add("fail", "security-surfaces",
              "no ## Security-relevant surfaces section — nothing can arm the plan's 1a "
              "threat-model gate, so a security feature would pass with an N/A threat model")
        return

    boxes = [m for m in (SURFACE_BOX.match(ln) for ln in body.splitlines()) if m]
    if not boxes:
        f.add("fail", "security-surfaces",
              "## Security-relevant surfaces carries no `- [ ]` checkbox lines — the 1a gate "
              "reads checkboxes, so prose here arms nothing")
        return

    checked = [m.group(2).strip() for m in boxes if m.group(1) in "xX"]
    if not checked:
        f.add("fail", "security-surfaces",
              f"## Security-relevant surfaces: 0 of {len(boxes)} boxes answered — blank is not "
              "'none', it silently disarms the 1a gate. Check what applies, or "
              "'None of the above' explicitly")
        return

    armed = [c for c in checked if not SURFACE_NONE.search(c)]
    none_of_the_above = len(armed) < len(checked)
    if armed and none_of_the_above:
        f.add("fail", "security-surfaces",
              "## Security-relevant surfaces checks both a real surface "
              f"[{armed[0][:40]}] and 'None of the above' — contradictory; pick one")
        return
    if armed:
        f.add("pass", "security-surfaces",
              f"{len(armed)} surface(s) flagged — the plan's 1a threat model is REQUIRED")
    else:
        f.add("pass", "security-surfaces",
              "answered 'None of the above' — a plan threat model of N/A is legitimate")


def check_threat_model(plan_text: str, spec_text: str | None, f: Findings) -> None:
    body = section_body(plan_text, "Threat model")
    if body is None:
        return  # already reported by check_plan_gates
    stripped = body.strip()
    # strip leading blockquote guidance lines to find the author's content
    author_lines = [ln for ln in stripped.splitlines() if not ln.lstrip().startswith(">")]
    author = "\n".join(author_lines).strip()
    is_na = bool(re.match(r"^N/?A\b", author, re.IGNORECASE))
    has_substance = any(NUMBERED_ATTACK.match(ln) for ln in author_lines)

    triggered = spec_security_triggered(spec_text) if spec_text else []
    if triggered and (is_na or not has_substance):
        f.add("fail", "threat-model",
              "spec flags security surface(s) "
              f"[{', '.join(triggered[:3])}] but plan's ## Threat model is "
              f"{'N/A' if is_na else 'empty/placeholder'} — proactive 1a gate not satisfied")
    elif has_substance:
        f.add("pass", "threat-model", "## Threat model has numbered attack→mitigation content")
    elif is_na:
        f.add("pass", "threat-model", "## Threat model marked N/A and no spec surface flagged")
    else:
        f.add("warn", "threat-model",
              "## Threat model is neither N/A nor substantive — confirm it is intentional")


TIER = re.compile(r"\[Tier\s+[AB]\]", re.IGNORECASE)
TIER_A = re.compile(r"\[Tier\s+A\]", re.IGNORECASE)
HAS_P = re.compile(r"\[P\]")


def strip_fenced(text: str) -> str:
    """Drop fenced code blocks before parsing task lines — the tasks template
    ships a fenced per-task format example, and a fenced `- [ ] Tnn` sample in
    a real plan must not count as (or fail as) a real task."""
    out, in_fence = [], False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(ln)
    return "\n".join(out)


# A review-gate STOP marker, and the provisional review tier (1h) that rides either the
# cluster heading (`### Cluster C1  (3 tasks · provisional tier: STANDARD)`) or the marker
# line itself (`── REVIEW GATE ──  *(STOP: … — tier STANDARD)*`). Either location counts:
# the corpus writes both, and over-constraining the placement buys nothing.
REVIEW_GATE_MARKER = re.compile(r"──\s*REVIEW GATE\s*──")
REVIEW_TIER = re.compile(r"\b(FULL|STANDARD|LIGHT)\b")


def parse_clusters(tasks_text: str):
    """Yield dicts {name, tasks:[(id, has_p)], irreversible:bool, gate:bool, tier:str|None}.
    Tasks under a `### Cluster` heading until the next cluster or level-2 heading.

    `gate` is True when a `── REVIEW GATE ──` marker appears after the cluster's own lines
    and before the next cluster / level-2 heading. A marker in the file's prose legend sits
    ahead of every cluster heading, so it is never miscounted as a cluster's gate.
    """
    clusters = []
    cur = None
    for ln in strip_fenced(tasks_text).splitlines():
        cm = CLUSTER_HEADING.match(ln)
        if cm:
            if cur:
                clusters.append(cur)
            label = cm.group(1)
            tier = REVIEW_TIER.search(label)
            cur = {"name": ln.strip(), "tasks": [],
                   "irreversible": bool(re.search(r"irreversible|solo", label, re.IGNORECASE)),
                   "gate": False, "tier": tier.group(1) if tier else None}
            continue
        h = heading_text(ln)
        if h and h[0] <= 2:  # phase boundary or end-of-clusters section
            if cur:
                clusters.append(cur)
                cur = None
            continue
        if cur is not None and REVIEW_GATE_MARKER.search(ln):
            cur["gate"] = True
            if cur["tier"] is None:
                tier = REVIEW_TIER.search(ln)
                if tier:
                    cur["tier"] = tier.group(1)
            continue
        tm = TASK_LINE.match(ln)
        if tm and cur is not None:
            cur["tasks"].append((tm.group(1), bool(HAS_P.search(tm.group(2)))))
    if cur:
        clusters.append(cur)
    return clusters


def check_review_gates(tasks_text: str, f: Findings) -> None:
    """1f / building Step 2.8 — every cluster ends at a `── REVIEW GATE ──` STOP marker.

    Cluster SIZING was already checked; the marker is what makes the boundary exist at run
    time. `building` HALTs *at the marker*: no marker, no HALT, and execution runs the phase
    flat into the un-bisectable mega-diff the cluster rule exists to prevent (calibration:
    `teardown-cluster`). Sized clusters with no markers is the shape that passed before.
    """
    clusters = parse_clusters(tasks_text)
    if not clusters:
        return  # check_clusters already reports "no `### Cluster` headings"
    missing = [c["name"].lstrip("# ").split("(")[0].strip() for c in clusters if not c["gate"]]
    if missing:
        f.add("fail", "review-gate-marker",
              f"{len(missing)}/{len(clusters)} cluster(s) end with no `── REVIEW GATE ──` "
              "marker, so nothing HALTs execution there: " + ", ".join(missing[:5]))
    else:
        f.add("pass", "review-gate-marker",
              f"all {len(clusters)} cluster(s) close at a `── REVIEW GATE ──` STOP marker")


def check_review_tiers(tasks_text: str, f: Findings) -> None:
    """1h — each cluster carries a provisional review tier (FULL / STANDARD / LIGHT).

    `building` restates the tier at each gate and may escalate one-way from it. With no tier
    declared there is nothing to restate and nothing to escalate FROM, so the fan-out
    silently becomes whatever the executing agent feels like.
    """
    clusters = parse_clusters(tasks_text)
    if not clusters:
        return
    missing = [c["name"].lstrip("# ").split("(")[0].strip() for c in clusters if not c["tier"]]
    if missing:
        f.add("fail", "review-tier",
              f"{len(missing)}/{len(clusters)} cluster(s) declare no provisional review tier "
              "(FULL/STANDARD/LIGHT): " + ", ".join(missing[:5]))
    else:
        f.add("pass", "review-tier",
              "all cluster(s) carry a provisional tier: "
              + ", ".join(f"{c['tier']}" for c in clusters[:6]))


def check_task_tiers(tasks_text: str, f: Findings) -> None:
    missing = []
    total = 0
    for ln in strip_fenced(tasks_text).splitlines():
        tm = TASK_LINE.match(ln)
        if tm:
            total += 1
            if not TIER.search(tm.group(2)):
                missing.append(tm.group(1))
    if total == 0:
        f.add("warn", "task-tier", "no task lines found (- [ ] T..)")
    elif missing:
        f.add("fail", "task-tier",
              f"{len(missing)}/{total} task(s) missing a [Tier A|B] marker: {', '.join(missing[:8])}")
    else:
        f.add("pass", "task-tier", f"all {total} tasks carry a test tier")


TEST_AUTHOR_LINE = re.compile(r"^\s+Test-author:\s*(split|solo)\b\s*(?:[—-]\s*(.*))?$")
TEST_AUTHOR_ANY_VALUE = re.compile(r"^\s+Test-author:\s*(\S.*)$")


def check_test_author_mode(tasks_text: str, f: Findings) -> None:
    """D1 — verify every task's `Test-author:` continuation line per the
    harness-efficiency plan's rules table (specs/harness-efficiency/plan.md
    section D1). Scans continuation lines between a matched TASK_LINE and the
    next task line / heading / fence; fenced blocks are stripped first via the
    existing strip_fenced so documentation examples never count."""
    total = 0
    missing = []          # task ids with NO Test-author: line at all
    invalid = []          # (task_id, raw_value) — line present but doesn't match split|solo
    tier_a_solo_bare = [] # task ids: [Tier A] + solo with no reason after a dash
    tier_b_split = []     # task ids: [Tier B] + split (over-ceremony)

    lines = strip_fenced(tasks_text).splitlines()
    n = len(lines)
    i = 0
    while i < n:
        tm = TASK_LINE.match(lines[i])
        if not tm:
            i += 1
            continue
        total += 1
        task_id = tm.group(1)
        task_rest = tm.group(2)
        is_tier_a = bool(TIER_A.search(task_rest))

        # Scan continuation lines until the next task line / heading / end.
        j = i + 1
        found_line = None
        while j < n:
            nxt = lines[j]
            if TASK_LINE.match(nxt) or heading_text(nxt):
                break
            m = TEST_AUTHOR_LINE.match(nxt)
            if m:
                found_line = (m.group(1), (m.group(2) or "").strip())
                break
            any_m = TEST_AUTHOR_ANY_VALUE.match(nxt)
            if any_m:
                found_line = ("__invalid__", any_m.group(1).strip())
                break
            j += 1

        if found_line is None:
            missing.append(task_id)
            i += 1
            continue

        mode, reason = found_line
        if mode == "__invalid__":
            invalid.append((task_id, reason))
        elif mode == "solo" and is_tier_a and not reason:
            tier_a_solo_bare.append(task_id)
        elif mode == "split" and not is_tier_a:
            tier_b_split.append(task_id)

        i += 1

    present = total - len(missing)

    if total == 0:
        return  # nothing to say here — check_task_tiers already reports "no task lines"

    if present == 0:
        f.add("warn", "test-author-mode", "pre-0.8 tasks.md — no Test-author: lines")
        return

    if missing:
        f.add("fail", "test-author-mode",
              f"{len(missing)}/{total} task(s) missing a Test-author: line: "
              + ", ".join(missing[:8]))
        return

    if invalid:
        f.add("fail", "test-author-mode",
              "invalid Test-author: value (must be split or solo…) on "
              + ", ".join(t for t, _ in invalid[:8]))
        return

    if tier_a_solo_bare:
        f.add("fail", "test-author-mode",
              "Tier A solo requires a stated A-lite reason: "
              + ", ".join(tier_a_solo_bare[:8]))
        return

    if tier_b_split:
        f.add("warn", "test-author-mode",
              "over-ceremony — split is for security-boundary Tier A: "
              + ", ".join(tier_b_split[:8]))
        return

    f.add("pass", "test-author-mode", f"all {total} tasks carry a test-author mode")


UNIT_TEST_LINE = re.compile(r"^\s+Unit test:\s*(\S.*)$")
NO_UNIT_TEST = re.compile(r"^no unit test\b", re.IGNORECASE)


def check_unit_test_contract(tasks_text: str, f: Findings) -> None:
    """1d — every task states the behavioral contract its test asserts.

    `Test-author:` says WHO writes the test; this says WHAT it must prove. A task with a tier
    and an author but no contract hands the implementer a tier marker and no target, which is
    where a denial path quietly stops being tested. Tier B opts out explicitly with
    `no unit test: Tier B, <reason>` — a stated waiver, not an omission.

    A **Tier A** task may never take that waiver: security/auth/parsing/state/transform/
    migration work is Tier A precisely because it needs the RED-first behavioral test, and
    talking one down to "no unit test" is the erosion this tier system exists to stop.

    Retro-compat matches test-author-mode: no task carrying the line at all is an older
    tasks.md and WARNs; partial presence is a defect and FAILs.
    """
    lines = strip_fenced(tasks_text).splitlines()
    n = len(lines)
    total, missing, tier_a_waived = 0, [], []
    i = 0
    while i < n:
        tm = TASK_LINE.match(lines[i])
        if not tm:
            i += 1
            continue
        total += 1
        task_id, task_rest = tm.group(1), tm.group(2)
        is_tier_a = bool(TIER_A.search(task_rest))

        found = None
        j = i + 1
        while j < n:
            if TASK_LINE.match(lines[j]) or heading_text(lines[j]):
                break
            m = UNIT_TEST_LINE.match(lines[j])
            if m:
                found = m.group(1).strip()
                break
            j += 1

        if found is None:
            missing.append(task_id)
        elif is_tier_a and NO_UNIT_TEST.match(found):
            tier_a_waived.append(task_id)
        i += 1

    if total == 0:
        return  # check_task_tiers already reports "no task lines"

    if len(missing) == total:
        f.add("warn", "unit-test-contract",
              f"no task carries a `Unit test:` line ({total} tasks) — pre-contract tasks.md")
        return
    if missing:
        f.add("fail", "unit-test-contract",
              f"{len(missing)}/{total} task(s) state no `Unit test:` contract: "
              + ", ".join(missing[:8]))
        return
    if tier_a_waived:
        f.add("fail", "unit-test-contract",
              "Tier A may not waive its test with `no unit test:` — "
              + ", ".join(tier_a_waived[:8]))
        return
    f.add("pass", "unit-test-contract", f"all {total} tasks state a `Unit test:` contract")


REQ_ID = re.compile(r"\b(FR|SC)-(\d+)\b")


def _req_ids(text: str) -> list[str]:
    """Requirement ids in document order, de-duplicated. `FR-n` (literal n) is template
    prose and never matches; only real numbered ids do."""
    seen, out = set(), []
    for m in REQ_ID.finditer(strip_fenced(text)):
        rid = f"{m.group(1)}-{m.group(2)}"
        if rid not in seen:
            seen.add(rid)
            out.append(rid)
    return out


def check_requirement_coverage(spec_text: str, tasks_text: str, f: Findings) -> None:
    """Stage 1.5's coverage half — the only cross-artifact check here.

    Asks the weaker of two questions deliberately: **is each requirement visible in the task
    list at all**, not *which exact task owns it*. A citation anywhere in `tasks.md` counts.
    The stronger question needs a per-task citation convention the corpus does not have, and
    a check that demands one nobody writes is a check that gets worked around.

    Retro-compat matches test-author-mode and unit-test-contract: a task list citing NO
    requirement id is pre-convention and WARNs — both live specs/ dirs are exactly that
    shape, declaring FR-1..n while their task lists cite none. Once ANY id is cited the
    convention is in use, so a gap is a defect and FAILs, naming the untraced ids.

    Not checked, and noisier by nature: the reverse direction. A task tracing back to nothing
    in the spec is often legitimate infrastructure, so orphan-hunting stays a Stage-1.5 read.
    """
    ids = _req_ids(spec_text)
    if not ids:
        f.add("warn", "requirement-coverage",
              "spec declares no FR-n / SC-n identifiers — nothing can be traced to a task; "
              "number the functional requirements so coverage is checkable")
        return

    cited = set(_req_ids(tasks_text))
    covered = [r for r in ids if r in cited]
    uncovered = [r for r in ids if r not in cited]

    if not covered:
        f.add("warn", "requirement-coverage",
              f"no requirement id is cited in tasks.md — pre-convention task list, so all "
              f"{len(ids)} ({ids[0]}…{ids[-1]}) are untraced and coverage is a human read")
        return
    if uncovered:
        f.add("fail", "requirement-coverage",
              f"{len(uncovered)}/{len(ids)} requirement(s) traced to no task: "
              + ", ".join(uncovered[:8]))
        return
    f.add("pass", "requirement-coverage",
          f"all {len(ids)} requirement(s) cited in tasks.md: " + ", ".join(ids[:8]))


def check_clusters(tasks_text: str, f: Findings) -> None:
    clusters = parse_clusters(tasks_text)
    if not clusters:
        f.add("warn", "review-cluster", "no `### Cluster` headings found")
        return
    ok = True
    for c in clusters:
        n = len(c["tasks"])
        if n > 4:
            ok = False
            f.add("fail", "review-cluster",
                  f"{c['name']} has {n} tasks (>4) — split into sub-clusters (1f)")
        if c["irreversible"]:
            if n != 1:
                ok = False
                f.add("fail", "review-cluster",
                      f"{c['name']} is irreversible/solo but has {n} tasks — must be exactly 1")
            if any(p for _, p in c["tasks"]):
                ok = False
                f.add("fail", "review-cluster",
                      f"{c['name']} is irreversible but a task is marked [P] — never parallelize it")
    if ok:
        f.add("pass", "review-cluster",
              f"{len(clusters)} cluster(s): all <=4 tasks; irreversible steps solo & non-[P]")


# ── driver ────────────────────────────────────────────────────────────────────

def run_checks(spec_dir: Path) -> Findings:
    f = Findings()
    spec = spec_dir / "spec.md"
    plan = spec_dir / "plan.md"
    tasks = spec_dir / "tasks.md"
    spec_text = spec.read_text() if spec.exists() else None
    plan_text = plan.read_text() if plan.exists() else None
    tasks_text = tasks.read_text() if tasks.exists() else None

    if spec_text is None and plan_text is None and tasks_text is None:
        f.add("fail", "input", f"no spec.md/plan.md/tasks.md in {spec_dir}")
        return f

    if spec_text is not None:
        check_clarify(spec_text, f)
        check_success_criteria(spec_text, f)
        check_security_surfaces(spec_text, f)
    if plan_text is not None:
        check_plan_gates(plan_text, f)
        check_threat_model(plan_text, spec_text, f)
    if tasks_text is not None:
        check_task_tiers(tasks_text, f)
        check_test_author_mode(tasks_text, f)
        check_unit_test_contract(tasks_text, f)
        check_clusters(tasks_text, f)
        check_review_gates(tasks_text, f)
        check_review_tiers(tasks_text, f)
    if spec_text is not None and tasks_text is not None:
        check_requirement_coverage(spec_text, tasks_text, f)  # the only cross-artifact check
    return f


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="netdust harness gate checker")
    ap.add_argument("spec_dir", type=Path)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    f = run_checks(args.spec_dir)

    if args.json:
        print(json.dumps({"failed": f.failed,
                          "findings": [{"status": s, "check": c, "detail": d}
                                       for s, c, d in f.items]}, indent=2))
    else:
        for status, check, detail in f.items:
            mark = {"pass": "✓", "warn": "!", "fail": "✗"}[status]
            print(f"  {mark} [{check}] {detail}")
        print()
        print("GATE: " + ("FAIL" if f.failed else "PASS"))
    return 1 if f.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
