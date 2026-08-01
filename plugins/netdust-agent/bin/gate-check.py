#!/usr/bin/env python3
"""gate-check.py — deterministic verification that a feature directory
carries the netdust harness gates.

Used by:
  - spec-authoring  (Stage 0.5): with only spec.md present
                    → enforces the [NEEDS CLARIFICATION] HALT.
  - spec-analysis   (Stage 1.5): with spec.md + plan.md + tasks.md
                    → enforces gate-presence (threat model, invariants, spec-premise,
                      review clusters) + per-task test tiers + the [P]/cluster rules
                      + the stakes dial (1i) + the per-task evidence rung (`Proven by:`).

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


# ── the legacy waiver ─────────────────────────────────────────────────────────
#
# Several checks used to soften to WARN whenever a convention was WHOLLY absent from an
# artifact: `success-criteria`, `test-author-mode`, `requirement-coverage`,
# `unit-test-contract`, and (post-0.16) `stakes`. The reasoning was retro-compat — the live
# specs/ dirs predate the conventions — but the mechanism was silence, and silence has two
# costs. It rewards writing ZERO lines over writing some (partial presence FAILs, total
# absence passed), and it is invisible: a brand-new spec with no success criteria read
# exactly like a 2026-06 one.
#
# So absence now FAILs, and a genuinely older artifact says so out loud:
#
#     <!-- gate-check: legacy-artifact — <why this predates the convention> -->
#
# The reason is mandatory, exactly as `Test-author: solo — <reason>` requires one. The waiver
# covers ABSENCE ONLY — it never excuses partial presence, an unmeasurable SC line, an
# invalid mode, or a coverage gap once the convention is in use. It cannot make a bad
# artifact pass; it can only mark an old one as old. And the finding it produces is a WARN
# that names the waiver, so exercising it stays visible in gate output rather than reading
# as a clean pass.
#
# The `stakes` pre-0.16 floor is deliberately INSIDE the regime (flipped to
# FAIL-unless-waived like the others): a silent fallback-to-standard made a brand-new plan
# indistinguishable from a pre-dial one, and consistency beats a fourth silent floor. The
# one floor deliberately still OUTSIDE it is `proven-by`'s pre-0.16 WARN — the newest field,
# not yet adopted by the corpus beyond this repo; flip it into the regime when it is.
#
# This is the same stance as `no unit test: Tier B, <reason>`: a stated waiver, not an
# omission.
LEGACY_WAIVER = re.compile(
    r"<!--\s*gate-check:\s*legacy-artifact\s*[—–-]\s*(?P<reason>[^>]*?)\s*-->", re.IGNORECASE)


def legacy_waiver(text: str | None) -> str | None:
    """The stated reason this artifact predates a convention, or None. A marker with no
    reason is not a waiver — same rule as a bare Tier-A `solo`."""
    if not text:
        return None
    m = LEGACY_WAIVER.search(text)
    if not m:
        return None
    reason = m.group("reason").strip()
    return reason or None


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
        waiver = legacy_waiver(spec_text)
        if waiver:
            f.add("warn", "success-criteria",
                  f"no ## Success criteria section — legacy waiver exercised: {waiver}")
        else:
            f.add("fail", "success-criteria",
                  "no ## Success criteria section — shake-out has nothing to sign off "
                  "against. An artifact that genuinely predates the contract says so with a "
                  "`<!-- gate-check: legacy-artifact — <reason> -->` marker")
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


# ── the stakes dial (what a failure here costs) ───────────────────────────────
#
# The class dial (harnessed-development A–F) scales PLANNING ceremony: how much design
# a piece of work warrants. This scales VERIFICATION effort, which is a different
# question — not "how big is this work?" but "what does a failure here cost?" Nothing
# in the harness asked that until 2026-07-31, and its absence is what let a contact page
# buy an auth subsystem's verification (calibration: `contact-page-8k`).
#
# Set ONCE, at plan time, read everywhere after — the same no-self-downgrade posture the
# `Test-author:` field has under D1. No run-time agent may lower it to save effort.

# The line match is deliberately loose (any non-empty tail); the LEVEL is the tail's first
# word-token and the reason is whatever follows, however punctuated — `Stakes: high — x`,
# `Stakes: high (x)`, `Stakes: high, x` and bare `Stakes: high` all parse to `high`. A
# stricter tail-shape here silently demoted a DECLARED level to the no-line WARN whenever
# the reason used parentheses or a comma, and a silent downgrade is the one outcome this
# field must never have.
STAKES_LINE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?Stakes(?:\*\*)?:\s*(\S.*?)\s*$",
    re.IGNORECASE | re.MULTILINE)
STAKES_TOKEN = re.compile(r"[A-Za-z][\w-]*")
STAKES_LEVELS = ("high", "standard", "low")

# I8's keyword net for the under-call WARN — deliberately narrow (money and PII terms that
# are unambiguous in any sentence), for the same reason PROSE_SECURITY is narrow: a WARN
# nobody trusts is a WARN nobody reads.
SPEC_HIGH_STAKES = re.compile(
    r"\b(payment|billing|invoice|refund|checkout|payout|PII"
    r"|personally identifiable|credit card|bank account)s?\b", re.IGNORECASE)


def plan_stakes(plan_text: str) -> tuple[str | None, str]:
    """(level, reason) from the plan's `Stakes:` line.

    `level` is None when the plan states no line at all, and the raw lowercased token when
    it states an unrecognised one — the caller decides which of those is a failure.

    NOTE: `bin/verify-budget.py` parses the same field to pick its ratio ceiling. The FIELD
    is parsed in two places because the bin/ scripts are deliberately standalone (no
    cross-imports, hyphenated filenames); the RULE — what each level buys — lives in exactly
    one place per axis: the ceilings in verify-budget.py, the verification obligations in
    `skills/testing-workflow/SKILL.md`. Keep the tolerant token parsing mirrored in both.
    """
    m = STAKES_LINE.search(strip_fenced(plan_text))
    if not m:
        return None, ""
    tail = m.group(1).strip()
    tok = STAKES_TOKEN.match(tail)
    if not tok:
        return tail.lower(), ""
    level = tok.group(0).lower()
    reason = tail[tok.end():].strip(" \t—–-,;:()")
    return level, reason


def check_stakes(plan_text: str, spec_text: str | None, f: Findings) -> None:
    """1i — the stakes dial is stated, readable, and not talked below the spec's own evidence.

    Three findings, in the order they matter:

      - **No line at all** → FAIL, unless the plan states a legacy waiver — then WARN
        naming it, and every downstream gate falls back to `standard` (exactly what it did
        unconditionally before the dial existed). This floor used to be a silent pre-0.16
        WARN; it joined the waiver regime deliberately — a silent fallback made a brand-new
        plan indistinguishable from a pre-dial one, and consistency with the other flipped
        floors beats a fourth silent floor. (`bin/verify-budget.py`, which parses the same
        field, keeps its own absent→standard fallback — it is a run-time reader, not a
        plan-time gate, and never blocks.)
      - **An unrecognised level** → FAIL. A dial nobody can read is worse than no dial:
        each downstream gate would silently pick its own default and they would diverge.
      - **`low` on a spec that flagged a security surface** → FAIL. This is the erosion
        control, and it is the one place the dial is not a judgment call. `low` buys the
        lightest verification in the harness; it must never be reachable on work the SPEC
        ITSELF says touches untrusted input, auth, or outbound requests. The spec's
        checkboxes are the evidence and no plan prose overrides them.

    `standard` on a security-flagged spec is *fine* — it is the honest classification for
    most input-handling features, and the presence-vs-decision rule (testing-workflow) is
    what keeps it cheap. The dial never waives a guard; it governs how much evidence beyond
    that guard's proven presence the feature buys.
    """
    level, reason = plan_stakes(plan_text)

    if level is None:
        waiver = legacy_waiver(plan_text)
        if waiver:
            f.add("warn", "stakes",
                  "no `Stakes:` line — pre-0.16 plan; verification gates fall back to "
                  f"`standard` — legacy waiver exercised: {waiver}")
        else:
            f.add("fail", "stakes",
                  "no `Stakes:` line — every downstream verification gate reads this dial "
                  "and nothing else re-decides it. A plan that genuinely predates the 0.16 "
                  "dial says so with a `<!-- gate-check: legacy-artifact — <reason> -->` "
                  "marker")
        return

    if level not in STAKES_LEVELS:
        f.add("fail", "stakes",
              f"unreadable stakes level `{level}` — must be one of: "
              + ", ".join(STAKES_LEVELS))
        return

    if level == "low" and spec_text is not None:
        flagged = spec_security_triggered(spec_text)
        if flagged:
            f.add("fail", "stakes",
                  "`Stakes: low` on a spec that flagged a security-relevant surface "
                  f"({'; '.join(flagged[:3])}) — `low` is not reachable here; the honest "
                  "classification is `standard`, and presence-vs-decision is what keeps it cheap")
            return

    # I8 — the under-call WARN. Money/PII in the spec's own prose while the plan declares
    # less than `high` deserves one visible question. WARN, never FAIL: prose keywords are
    # weaker evidence than the spec's checked security boxes (which drive the `low` FAIL
    # above), and a FAIL on a keyword would teach people to route around the dial.
    # S9 — the two advisory WARNs are independent questions and BOTH surface: an early
    # return after the first would suppress the second, and a reviewer owed two questions
    # should see two.
    warned = False

    if level != "high" and spec_text is not None:
        m = SPEC_HIGH_STAKES.search(strip_fenced(spec_text))
        if m:
            f.add("warn", "stakes",
                  f"`Stakes: {level}` while the spec mentions `{m.group(0)}` — money/PII "
                  "surfaces usually read `high`; confirm the under-call is deliberate")
            warned = True

    if level in ("high", "low") and not reason:
        f.add("warn", "stakes",
              f"`Stakes: {level}` states no reason — both are departures from the default; "
              "say why in one line so a reviewer can challenge it")
        warned = True

    if not warned:
        f.add("pass", "stakes", f"Stakes: {level}" + (f" — {reason[:60]}" if reason else ""))


HAS_P = re.compile(r"\[P\]")
HAS_HUMAN = re.compile(r"\[HUMAN\]", re.IGNORECASE)


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

# ANCHORED at line start (bold markup tolerated, as `**Integration gate (C1):**` is what the
# corpus writes). An unanchored match would be satisfied by a task's own prose — TASKS_GOOD's
# `Unit test: … covered by the cluster integration gate` is exactly that false positive, and a
# cluster must not be able to declare its integration gate by mentioning one.
INTEGRATION_GATE_LINE = re.compile(r"^\s*[-*>]?\s*\**\s*Integration gate\b", re.IGNORECASE)


def parse_clusters(tasks_text: str):
    """Yield dicts {name, tasks:[(id, has_p)], irreversible:bool, gate:bool, tier:str|None,
    integration_gate:bool}. Tasks under a `### Cluster` heading until the next cluster or
    level-2 heading.

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
                   "gate": False, "tier": tier.group(1) if tier else None,
                   "integration_gate": False}
            continue
        h = heading_text(ln)
        if h and h[0] <= 2:  # phase boundary or end-of-clusters section
            if cur:
                clusters.append(cur)
                cur = None
            continue
        if cur is not None and INTEGRATION_GATE_LINE.match(ln):
            cur["integration_gate"] = True
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
    section D1). Walks each task's continuation block via the shared
    `task_blocks()` walker (one boundary definition for every block-based
    check); fenced blocks are stripped there so documentation examples never
    count."""
    total = 0
    missing = []          # task ids with NO Test-author: line at all
    invalid = []          # (task_id, raw_value) — line present but doesn't match split|solo
    tier_a_solo_bare = [] # task ids: [Tier A] + solo with no reason after a dash
    tier_b_split = []     # task ids: [Tier B] + split (over-ceremony)

    for task_id, task_rest, cont in task_blocks(tasks_text):
        total += 1
        is_tier_a = bool(TIER_A.search(task_rest))

        found_line = None
        for nxt in cont:
            m = TEST_AUTHOR_LINE.match(nxt)
            if m:
                found_line = (m.group(1), (m.group(2) or "").strip())
                break
            any_m = TEST_AUTHOR_ANY_VALUE.match(nxt)
            if any_m:
                found_line = ("__invalid__", any_m.group(1).strip())
                break

        if found_line is None:
            missing.append(task_id)
            continue

        mode, reason = found_line
        if mode == "__invalid__":
            invalid.append((task_id, reason))
        elif mode == "solo" and is_tier_a and not reason:
            tier_a_solo_bare.append(task_id)
        elif mode == "split" and not is_tier_a:
            tier_b_split.append(task_id)

    present = total - len(missing)

    if total == 0:
        return  # nothing to say here — check_task_tiers already reports "no task lines"

    if present == 0:
        waiver = legacy_waiver(tasks_text)
        if waiver:
            f.add("warn", "test-author-mode",
                  f"no Test-author: lines — legacy waiver exercised: {waiver} "
                  "(building's controller defaults every task to `split`)")
        else:
            f.add("fail", "test-author-mode",
                  f"no task carries a Test-author: line ({total} tasks) — D1's mode is the "
                  "planner's decision and the controller only reads it. An artifact that "
                  "genuinely predates the field says so with a "
                  "`<!-- gate-check: legacy-artifact — <reason> -->` marker")
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


# D1's security-boundary categories, detected in TWO places with different confidence.
#
# Calibrated against the live corpus, which rejected the first attempt: matching the task
# DESCRIPTION for words like "session" and "guard" flagged three doc-editing tasks — "no code
# will change this session", and prose discussing the erosion *guard* — pure noise. A WARN
# nobody trusts is a WARN nobody reads, so:
#
#   FILES  — the `(files: …)` paths carry the truth. A task touching db/tokens.sql IS token
#            work whatever its prose says; one touching skills/building/SKILL.md is not,
#            however much it discusses guards. Broad list, matched here.
#   PROSE  — only terms that are unambiguous in any sentence. Deliberately narrow; "session",
#            "guard", "token", "parse" and friends are excluded because English uses them for
#            everything.
#
# This makes a downgrade VISIBLE. It cannot know what a task really touches, and the planner
# applying D1 remains the real control.
# Substring matching on purpose (so `tokens.sql` and `migrations/` hit), which makes the
# exclusions load-bearing — the corpus found three: `auth` inside test-AUTHor.md, `acl` inside
# performance-orACLe.md, and `pars` inside sPARSe. Hence the lookahead and the two anchors.
FILES_SECURITY = re.compile(
    r"(auth(?!or)|authoris|authoriz|token|session|credential|password|secret|api[-_]?key|crypt"
    r"|csrf|nonce|guard|permission|capabilit|migrat|schema|upload|payment|billing|invoice"
    r"|tenant|sanitiz|\bpars|login|signin|signup|\bacl\b|role|scope)", re.IGNORECASE)
PROSE_SECURITY = re.compile(
    r"\b(authn|authz|authoris\w*|authoriz\w*|credential\w*|password|api[-_ ]?key|encrypt\w*"
    r"|decrypt\w*|csrf|sanitiz\w*|sql injection|injection attack|multi[- ]?tenanc\w*"
    r"|cross[- ]tenant|untrusted input|untrusted pars\w*)\b", re.IGNORECASE)
FILES_SEGMENT = re.compile(r"\(\s*f(?:iles?)?\s*:\s*([^)]*)\)", re.IGNORECASE)


def _boundary_hit(task_rest: str) -> str | None:
    """The matched term, or None. Files first (higher confidence), then narrow prose."""
    seg = FILES_SEGMENT.search(task_rest)
    if seg:
        m = FILES_SECURITY.search(seg.group(1))
        if m:
            return m.group(0).lower()
    m = PROSE_SECURITY.search(FILES_SEGMENT.sub("", task_rest))
    return m.group(0).lower() if m else None


def check_security_boundary_mode(tasks_text: str, f: Findings) -> None:
    """D1's no-self-downgrade rule, made visible where the mode check cannot reach.

    `test-author-mode` verifies a Tier-A `solo` states SOME reason; it cannot judge whether the
    reason is true. So it accepts `solo — A-lite, pure transform` on a task that rewrites an
    auth token store — precisely the self-downgrade the split exists to prevent. Two heuristic
    WARNs close the visibility gap:

      - **Tier A + solo + a security-boundary signal** — D1 says a Tier-A task in one of those
        categories is ALWAYS `split`. Either the mode is wrong, or the stated reason is
        describing a different task than the one in front of you.
      - **Tier B + a security-boundary signal AND no presence proof** — a guard classified
        Tier B with nothing at all proving it. Note the second half of that condition: it is
        new, and it is the fix for `contact-page-8k`.

    **Why Tier B on a boundary surface is no longer suspicious by itself.** This check used
    to warn on EVERY Tier-B task whose files matched the boundary list, on the reading that
    `testing-workflow`'s erosion guard makes security work Tier A regardless of size. That
    reading conflated two obligations the skill now separates:

      - **presence** — the guard is actually there, on every path, and actually reached.
        Cheapest and broadest as a machine gate over the whole diff; never waived.
      - **decision** — the predicate encodes a rule THIS PROJECT invented (a role, a window,
        an ownership test, a threshold). That is Tier A at every stakes level.

    A direct call to a hardened framework primitive — `wp_verify_nonce`, `current_user_can`,
    `sanitize_text_field`, `is_email` — carries no decision of its own; its behaviour is
    upstream's and upstream tests it. The project's risk is *omission*, which a presence proof
    catches on every call site forever and a bespoke unit test catches on one call site once.
    Warning on those pushed every form handler in a WordPress feature up to Tier A + `split`,
    which is how a contact page bought an auth subsystem's verification.

    So the signal is now the ABSENCE OF EVIDENCE, not the tier: Tier B on a boundary surface
    is fine when the task names a presence proof on the ladder's first three rungs, and is a
    WARN when it names nothing — or names `new test`, which contradicts its own tier
    (exempt: the task also states an `Integration test:` contract — Tier B + an integration
    contract + `Proven by: new test` is the designed WP wiring path, not a contradiction).

    WARN, never FAIL: a keyword is not knowledge. A false positive costs one dismissal; a FAIL
    on a false positive would teach people to route around the gate.
    """
    downgraded, unproven, contradictory = [], [], []

    for task_id, task_rest, cont in task_blocks(tasks_text):
        term = _boundary_hit(task_rest)
        if term is None:
            continue
        is_tier_a = bool(TIER_A.search(task_rest))

        mode = None
        for ln in cont:
            m = TEST_AUTHOR_LINE.match(ln)
            if m:
                mode = m.group(1)
                break

        if is_tier_a and mode == "solo":
            downgraded.append(f"{task_id} ({term})")
        elif not is_tier_a and TIER.search(task_rest):
            value = task_proven_by(cont)
            rung = None
            if value:
                m = PROVEN_BY_RUNG.match(value)
                rung = m.group(1).lower() if m else None
            if rung in EVIDENCE_ELSEWHERE:
                continue                      # presence proven elsewhere — the designed path
            if rung == "new test":
                # F2 exemption: Tier B + an `Integration test:` contract + `new test` is
                # the designed WP wiring path — the "new test" IS the integration test the
                # contract line states, not a contradiction of the tier.
                if any(m and m.group(1) == "Integration"
                       for m in (CONTRACT_LINE.match(ln) for ln in cont)):
                    continue
                contradictory.append(f"{task_id} ({term})")
            else:
                unproven.append(f"{task_id} ({term})")

    if downgraded:
        f.add("warn", "security-boundary-mode",
              "Tier A + `solo` on what reads like a security-boundary category — D1 says "
              "ALWAYS split; confirm the mode or correct it: " + ", ".join(downgraded[:6]))
    if unproven:
        f.add("warn", "security-boundary-mode",
              "Tier B on a security-boundary surface with NOTHING proving it — name the "
              "presence proof (`Proven by: machine gate|framework|existing test — <what>`) "
              "or raise the tier: " + ", ".join(unproven[:6]))
    if contradictory:
        f.add("warn", "security-boundary-mode",
              "Tier B but `Proven by: new test` — the tier says no bespoke test and the "
              "evidence line says one is being written; one of them is wrong: "
              + ", ".join(contradictory[:6]))


def check_files_segment(tasks_text: str, f: Findings) -> None:
    """The task line's `(files: <paths>)` segment — declared grammar, and the thing that
    keeps check_security_boundary_mode's high-confidence path alive.

    `planning`'s output contract states the task-line shape as
    `- [ ] T01 [P?] [Tier A|B] <description>  (files: <paths>)`, but nothing read the
    segment, so it was contract-in-prose only. That mattered more than a formatting nit:
    `_boundary_hit` deliberately trusts FILES over PROSE (the calibration above explains why
    PROSE_SECURITY is narrow — "session"/"guard"/"token" flagged three doc tasks and a WARN
    nobody trusts is a WARN nobody reads). With no files segment, only the narrow prose list
    runs. A task reading `[Tier B] build the invoice wizard, auth, payment capture and
    email` drew NO security-boundary warning at all: `auth` and `payment` live in
    FILES_SECURITY, not in PROSE_SECURITY, and there was no segment to match them against.
    Omitting `(files:)` was a free way to blind the no-self-downgrade detector.

    FAIL, with no absent-floor: every task line across the live corpus carries the segment,
    so there is no legacy shape to tolerate. The short `(f: …)` form counts — FILES_SEGMENT
    is the single reader of this grammar and already accepts it. Walks the shared
    `task_blocks()` boundary (the segment lives on the task line itself, `task_rest`).

    **`[HUMAN]` tasks are exempt, and the exemption is reported rather than silent.** A
    `[HUMAN]` step is a planned yield point — destructive-migration approval, credentials, a
    deploy confirmation — an ACTION the agent may not take alone, not a file edit. Demanding
    paths there would push a planner to invent one to satisfy the checker, which is the
    back-filled-field defect this contract exists to prevent, and it would buy nothing: the
    segment is read by the security-boundary check, which is about code tasks.
    """
    missing, total, exempt = [], 0, []
    for task_id, task_rest, _cont in task_blocks(tasks_text):
        total += 1
        if HAS_HUMAN.search(task_rest):
            exempt.append(task_id)
            continue
        seg = FILES_SEGMENT.search(task_rest)
        if not seg or not seg.group(1).strip():
            missing.append(task_id)
    if total == 0:
        return  # check_task_tiers already reports "no task lines"
    note = f" ({len(exempt)} [HUMAN] yield point(s) exempt)" if exempt else ""
    if missing:
        f.add("fail", "files-segment",
              f"{len(missing)}/{total} task(s) carry no `(files: <paths>)` segment — the "
              "security-boundary check reads those paths, so an omission silently narrows it "
              "to prose matching: " + ", ".join(missing[:8]) + note)
    else:
        f.add("pass", "files-segment", f"all {total} tasks name their files{note}")


def check_human_yield(tasks_text: str, f: Findings) -> None:
    """1d loop-auditability — a `[HUMAN]` step is a planned yield point, never `[P]`.

    `planning` states the rule outright: mark any step no agent may take alone (destructive
    migration approval, credentials, deploy confirmation) with `[HUMAN]` on its task line,
    "a planned yield point, never `[P]`". The two markers contradict each other by
    construction: `[P]` tells the controller it may dispatch this task alongside its
    siblings, and the whole purpose of `[HUMAN]` is that execution STOPS and waits for a
    person. A task carrying both is a yield point an armed `/loop` can run straight past —
    the failure the mark exists to prevent, wearing the mark that was supposed to prevent
    it.

    This is `check_clusters`'s irreversible-and-`[P]` rule one level down, on the task
    rather than the cluster (walked on the shared `task_blocks()` boundary), and it FAILs
    for the same reason: nothing here is a heuristic. Both markers are literal, and their
    combination is never correct.

    Nothing is REQUIRED — most features have no `[HUMAN]` step at all (both live plans say
    so explicitly), so this check is silent unless it finds the contradiction.
    """
    offenders, human_seen = [], False
    for task_id, task_rest, _cont in task_blocks(tasks_text):
        if not HAS_HUMAN.search(task_rest):
            continue
        human_seen = True
        if HAS_P.search(task_rest):
            offenders.append(task_id)
    if offenders:
        f.add("fail", "human-yield",
              f"{len(offenders)} task(s) marked both [HUMAN] and [P] — a planned yield point "
              "is never parallelizable, and [P] lets an armed /loop dispatch straight past it: "
              + ", ".join(offenders[:8]))
    elif human_seen:
        f.add("pass", "human-yield", "every [HUMAN] yield point is non-[P]")


def check_integration_gate(tasks_text: str, f: Findings) -> None:
    """1d — every review cluster states what to verify ACROSS its tasks.

    `planning`'s task-shaping gate: "Every phase gets an 'Integration gate: [what to verify
    across tasks]' line. A plan without these is not ready to execute." The corpus writes it
    per CLUSTER rather than per phase, which is the tighter reading and the one that matches
    where execution actually stops — `building` Step 2.8 HALTs at the cluster marker and
    runs `/integration` on that cluster's diff. A cluster with a `── REVIEW GATE ──` and no
    stated integration gate sends the agent into that HALT with nothing to verify against,
    which is where the review silently degrades to reading the diff for style.

    A bare cluster FAILs, with one absence-shaped exception: when NO cluster in the file
    carries the line AND the file states a legacy waiver, the finding is a WARN naming the
    waiver — the wp-manager corpus predates the per-cluster line entirely, and the waiver
    regime's absence-only rule covers exactly that shape. Once ANY cluster states a gate the
    convention is in use, and a bare sibling is a defect no waiver excuses.
    """
    clusters = parse_clusters(tasks_text)
    if not clusters:
        return  # check_clusters already reports "no `### Cluster` headings"
    missing = [c["name"].lstrip("# ").split("(")[0].strip()
               for c in clusters if not c["integration_gate"]]
    if not missing:
        f.add("pass", "integration-gate",
              f"all {len(clusters)} cluster(s) state an integration gate")
        return
    if len(missing) == len(clusters):
        waiver = legacy_waiver(tasks_text)
        if waiver:
            f.add("warn", "integration-gate",
                  f"no cluster states an `Integration gate:` ({len(clusters)} clusters) — "
                  f"legacy waiver exercised: {waiver}")
            return
    f.add("fail", "integration-gate",
          f"{len(missing)}/{len(clusters)} cluster(s) state no `Integration gate:` — "
          "nothing for the Step 2.8 HALT to verify across the cluster: "
          + ", ".join(missing[:5]))


# The plan's loop-auditability line. `bin/run-score.py` reads the SAME line for the loop
# budget it grades against — keep the two tolerant of the same shapes, including the bold
# `- **Loop budget:** ~20 iterations` form the corpus actually writes. Searched over
# strip_fenced(plan_text), so a fenced template sample never reads as a declared ceiling
# (the same rule STAKES_LINE and the task walkers already follow).
LOOP_BUDGET = re.compile(r"Loop budget:?\**\s*[:~]?\s*\**\s*~?\s*(\d+)", re.IGNORECASE)


def check_loop_budget(plan_text: str, f: Findings) -> None:
    """1d loop-auditability — the plan declares the iteration ceiling an armed `/loop` reads.

    `planning`: "The plan is execution-mode-agnostic — you never know whether `building`
    will run it under an armed `/loop`," which is why the line is unconditional rather than
    something a planner decides is unnecessary. `run-score.py` grades the run against this
    number and degrades to ungraded without it, so an absent line costs the evaluator
    silently.

    FAIL, no absent-floor: every live plan carries it (the wp-manager corpus in the plain
    form, this repo's in the bold form — both parse).
    """
    m = LOOP_BUDGET.search(strip_fenced(plan_text))
    if m:
        f.add("pass", "loop-budget", f"loop budget declared: ~{m.group(1)} iterations")
    else:
        f.add("fail", "loop-budget",
              "no `Loop budget: ~N iterations` line — an armed /loop has no ceiling to read "
              "and run-score.py cannot grade the run against one")


# ── the evidence ladder ───────────────────────────────────────────────────────
#
# Before authoring a test, name what ALREADY proves the property. The ladder, cheapest and
# broadest first:
#
#   1. machine gate   — a check the project already runs over the whole diff, every run
#   2. framework      — the primitive is hardened upstream; your risk is omission, not
#                       behaviour, and omission is a presence proof (rung 1), not a test
#   3. existing test  — a test or seam assertion already reaches this path
#   4. new test       — only now do you write one
#
# The point is not to write fewer tests. It is that evidence which is cheap, broad and
# permanent outranks evidence that is expensive, narrow and one-off: a gate proving every
# handler carries a nonce, forever, beats a unit test proving one handler carried one once.
# Re-proving rung 1 or 2 by hand is the duplicated-evidence failure `contact-page-8k` is
# made of — and the expensive copy is the weaker one.

PROVEN_BY_RUNGS = ("machine gate", "framework", "existing test", "new test")
PROVEN_BY_LINE = re.compile(r"^\s+Proven by:\s*(\S.*)$")
PROVEN_BY_RUNG = re.compile(r"^(" + "|".join(PROVEN_BY_RUNGS) + r")\b", re.IGNORECASE)

# Rungs 1–3 say the evidence lives SOMEWHERE ELSE. That one property drives both uses below,
# which is why it is one tuple and not two:
#   - it must be NAMED — an unnamed "Proven by: machine gate" is precisely the assertion this
#     harness refuses to trust (rung 4 needs no name; `Unit test:` carries the contract);
#   - it counts as a PRESENCE proof, so a Tier-B task on a security-boundary surface that
#     names one is the designed path, not tier erosion (see check_security_boundary_mode).
EVIDENCE_ELSEWHERE = ("machine gate", "framework", "existing test")


def task_blocks(tasks_text: str):
    """Yield (task_id, task_rest, [continuation lines]) per task, fences already stripped.

    THE one boundary definition for every block-based check (`test-author-mode`,
    `proven-by`, `security-boundary-mode`, `unit-test-contract` all walk it): a task's
    continuation block ends at the next COLUMN-0 bullet (`- `) or heading. A top-level
    bullet is never a continuation of the previous task, *even when its id doesn't
    parse* — otherwise a malformed `- [ ] T07b …` bullet leaks its `Test-author:` /
    `Proven by:` / waiver lines into the task above it, and that task gets graded on
    another task's evidence (the ae65211 rule, generalized from unit-test-contract).
    """
    lines = strip_fenced(tasks_text).splitlines()
    n = len(lines)
    i = 0
    while i < n:
        tm = TASK_LINE.match(lines[i])
        if not tm:
            i += 1
            continue
        cont = []
        j = i + 1
        while j < n and not lines[j].startswith("- ") and not heading_text(lines[j]):
            cont.append(lines[j])
            j += 1
        yield tm.group(1), tm.group(2), cont
        i = j


def task_proven_by(cont: list[str]) -> str | None:
    """The task's `Proven by:` value, or None."""
    for ln in cont:
        m = PROVEN_BY_LINE.match(ln)
        if m:
            return m.group(1).strip()
    return None


def check_proven_by(tasks_text: str, f: Findings) -> None:
    """1d — every task names what proves its behaviour, from the evidence ladder.

    Retro-compat matches `test-author-mode`: a task list where NO task carries the line is a
    pre-0.16 plan → WARN. Once any task carries one, they all must — a half-adopted field is
    worse than an absent one, because a reader cannot tell "nothing proves this" from
    "nobody filled it in".

    An unrecognised rung FAILs: the ladder is the whole point, and a free-text answer
    ("covered by the suite") is the vagueness it replaces. Rungs 1–3 must NAME their
    evidence; rung 4 need not, because `Unit test:` already states the contract.
    """
    total = 0
    missing, bad_rung, unnamed = [], [], []

    for task_id, _rest, cont in task_blocks(tasks_text):
        total += 1
        value = task_proven_by(cont)
        if value is None:
            missing.append(task_id)
            continue
        m = PROVEN_BY_RUNG.match(value)
        if not m:
            bad_rung.append(f"{task_id} ({value[:24]})")
            continue
        rung = m.group(1).lower()
        if rung in EVIDENCE_ELSEWHERE:
            rest = value[m.end():].strip(" —–-\t")
            if not rest:
                unnamed.append(f"{task_id} ({rung})")

    if total == 0:
        f.add("warn", "proven-by", "no task lines found (- [ ] T..)")
        return
    if len(missing) == total:
        f.add("warn", "proven-by", "pre-0.16 tasks.md — no `Proven by:` lines")
        return
    if missing:
        f.add("fail", "proven-by",
              f"{len(missing)}/{total} task(s) missing a `Proven by:` line: "
              + ", ".join(missing[:8]))
    if bad_rung:
        f.add("fail", "proven-by",
              "unrecognised evidence rung (use: " + " | ".join(PROVEN_BY_RUNGS) + "): "
              + ", ".join(bad_rung[:6]))
    if unnamed:
        f.add("fail", "proven-by",
              "rung states evidence exists elsewhere but does not NAME it — an unnamed "
              "proof is the assertion this harness refuses to trust: " + ", ".join(unnamed[:6]))
    if not (missing or bad_rung or unnamed):
        f.add("pass", "proven-by", f"all {total} tasks name their evidence rung")


CONTRACT_LINE = re.compile(r"^\s+(Unit|Integration) test:\s*(\S.*)$")
NO_UNIT_TEST = re.compile(r"^no unit test\b", re.IGNORECASE)


def check_unit_test_contract(tasks_text: str, f: Findings) -> None:
    """1d — every task states the behavioral contract its test asserts.

    `Test-author:` says WHO writes the test; this says WHAT it must prove. Either line
    satisfies, for any tier: `Unit test: <contract>` or `Integration test: <contract>`;
    both on one task is belt+braces. Tier B may opt out explicitly with
    `Unit test: no unit test: Tier B, <reason>` — a stated waiver, not an omission.
    Text after `Integration test:` is NEVER a waiver; it always reads as a contract.

    The task's WHOLE continuation block (per the shared `task_blocks()` walker) is
    scanned and every contract/waiver line collected before deciding, so line order
    never changes an outcome. The block ends at the next top-level list item or
    heading — a column-0 bullet is never a continuation of the previous task, even
    when its id doesn't parse. Enforced:
    - a **Tier A** task carrying the unit-waiver form FAILs, even when an
      `Integration test:` line accompanies it — the waiver text is a defect or an
      erosion attempt, and either deserves the loud stop;
    - a task whose ONLY contract is `Integration test:` may not be marked `[P]` —
      integration-contract tasks are never parallel; serialize them.

    **No silent retro-compat floor here any more.** This check once WARNed whenever NO task
    carried either line, on the same pre-convention reasoning as its siblings. That branch
    was unreachable on the live corpus (every dir carries a contract on every task) — while
    an all-or-nothing floor rewards writing ZERO contracts over writing some, which is the
    shape a hollow tasks.md walks through. Total absence now FAILs unless the file states a
    legacy waiver, which downgrades ABSENCE ONLY to a WARN naming it; partial presence is a
    defect and FAILs regardless.
    """
    total, missing, tier_a_waived, integration_parallel = 0, [], [], []
    for task_id, task_rest, cont in task_blocks(tasks_text):
        total += 1
        is_tier_a = bool(TIER_A.search(task_rest))

        has_unit_contract = has_unit_waiver = has_integration = False
        for ln in cont:
            m = CONTRACT_LINE.match(ln)
            if m:
                is_unit_form = m.group(1) == "Unit"
                if not is_unit_form:
                    has_integration = True
                elif NO_UNIT_TEST.match(m.group(2).strip()):
                    has_unit_waiver = True
                else:
                    has_unit_contract = True

        if not (has_unit_contract or has_unit_waiver or has_integration):
            missing.append(task_id)
        if is_tier_a and has_unit_waiver:
            tier_a_waived.append(task_id)
        if has_integration and not has_unit_contract and HAS_P.search(task_rest):
            integration_parallel.append(task_id)

    if total == 0:
        return  # check_task_tiers already reports "no task lines"

    if len(missing) == total:
        waiver = legacy_waiver(tasks_text)
        if waiver:
            f.add("warn", "unit-test-contract",
                  f"no task carries a `Unit test:` or `Integration test:` line "
                  f"({total} tasks) — legacy waiver exercised: {waiver}")
        else:
            f.add("fail", "unit-test-contract",
                  f"no task states a test contract ({total} tasks): "
                  + ", ".join(missing[:8])
                  + " — an all-or-nothing floor rewarded writing zero contracts over "
                  "writing some. An artifact that genuinely predates the contract line "
                  "says so with a `<!-- gate-check: legacy-artifact — <reason> -->` marker")
        return
    if missing:
        f.add("fail", "unit-test-contract",
              f"{len(missing)}/{total} task(s) state no test contract "
              "(`Unit test:` / `Integration test:`): " + ", ".join(missing[:8]))
    if tier_a_waived:
        f.add("fail", "unit-test-contract",
              "Tier A may not waive its test with `no unit test:` — "
              + ", ".join(tier_a_waived[:8]))
    if integration_parallel:
        f.add("fail", "unit-test-contract",
              "integration-contract task(s) marked [P] — integration contracts are "
              "never parallel, serialize: " + ", ".join(integration_parallel[:8]))
    if not (missing or tier_a_waived or integration_parallel):
        f.add("pass", "unit-test-contract", f"all {total} tasks state a test contract")


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
        waiver = legacy_waiver(tasks_text)
        if waiver:
            f.add("warn", "requirement-coverage",
                  f"no requirement id cited in tasks.md, so all {len(ids)} "
                  f"({ids[0]}…{ids[-1]}) are untraced and coverage is a human read — "
                  f"legacy waiver exercised: {waiver}")
        else:
            f.add("fail", "requirement-coverage",
                  f"no requirement id is cited in tasks.md, so all {len(ids)} "
                  f"({ids[0]}…{ids[-1]}) are untraced — cite the id on the task that "
                  "satisfies it, or mark a genuinely older list with a "
                  "`<!-- gate-check: legacy-artifact — <reason> -->` marker")
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
        check_stakes(plan_text, spec_text, f)
        check_loop_budget(plan_text, f)
    if tasks_text is not None:
        check_task_tiers(tasks_text, f)
        check_files_segment(tasks_text, f)
        check_human_yield(tasks_text, f)
        check_test_author_mode(tasks_text, f)
        check_proven_by(tasks_text, f)
        check_security_boundary_mode(tasks_text, f)
        check_unit_test_contract(tasks_text, f)
        check_clusters(tasks_text, f)
        check_review_gates(tasks_text, f)
        check_review_tiers(tasks_text, f)
        check_integration_gate(tasks_text, f)
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
