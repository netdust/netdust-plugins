#!/usr/bin/env python3
"""gate-check.py — deterministic verification that a spec-kit feature directory
carries the netdust harness gates.

Used by:
  - spec-authoring  (Stage 0.5): after /speckit.clarify, with only spec.md present
                    → enforces the [NEEDS CLARIFICATION] HALT.
  - spec-analysis   (Stage 1.5): after /speckit.tasks, with spec.md + plan.md + tasks.md
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
HAS_P = re.compile(r"\[P\]")


def parse_clusters(tasks_text: str):
    """Yield dicts {name, tasks:[(id, has_p)], irreversible:bool}. Tasks under a
    `### Cluster` heading until the next cluster or level-2 heading."""
    clusters = []
    cur = None
    for ln in tasks_text.splitlines():
        cm = CLUSTER_HEADING.match(ln)
        if cm:
            if cur:
                clusters.append(cur)
            label = cm.group(1)
            cur = {"name": ln.strip(), "tasks": [],
                   "irreversible": bool(re.search(r"irreversible|solo", label, re.IGNORECASE))}
            continue
        h = heading_text(ln)
        if h and h[0] <= 2:  # phase boundary or end-of-clusters section
            if cur:
                clusters.append(cur)
                cur = None
            continue
        tm = TASK_LINE.match(ln)
        if tm and cur is not None:
            cur["tasks"].append((tm.group(1), bool(HAS_P.search(tm.group(2)))))
    if cur:
        clusters.append(cur)
    return clusters


def check_task_tiers(tasks_text: str, f: Findings) -> None:
    missing = []
    total = 0
    for ln in tasks_text.splitlines():
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
    if plan_text is not None:
        check_plan_gates(plan_text, f)
        check_threat_model(plan_text, spec_text, f)
    if tasks_text is not None:
        check_task_tiers(tasks_text, f)
        check_clusters(tasks_text, f)
    return f


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="netdust × spec-kit gate checker")
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
