#!/usr/bin/env python3
"""verify-budget.py — the verification-effort tripwire.

Every gate in this harness answers "is this verified?" None of them asked "is this
verification worth what it cost?" — so effort could compound, gate by gate, each step
individually correct, with nothing in the machine able to notice. On 2026-07-31 a contact
page bought ~8000 lines of tests that way; the human found out hours later, because the
human was the only thing in the loop capable of noticing (calibration: `contact-page-8k`).

This script is that missing sense. It compares test lines added against implementation
lines added over a git range, and HALTs when the ratio exceeds what the feature's declared
stakes justify.

WHAT IT IS NOT
--------------
It is not a quality measure and it must never be read as one. A high ratio is not "too many
tests" — a security-critical parser legitimately carries several times its own weight in
tests. A HALT means exactly one thing: **the spend has outrun the plan's declared stakes,
and a human should look before more is spent.** The right response is often "the stakes
line was wrong, raise it and continue", which is a perfectly good outcome — the dial gets
corrected while the work is still cheap to redirect.

It also cannot see effort that produced no lines: dispatch round-trips, re-planning, a
test-author/implementer pair ping-ponging on a fixture. For that, read `run-cost.py`'s
per-dispatch table. This catches the shape that leaves a trace in the diff.

Usage:
    verify-budget.py <feature-spec-dir> --base <ref>     # ref..HEAD, or any git range
    verify-budget.py <feature-spec-dir> --base main --json
    verify-budget.py --stakes standard --base main       # no feature dir (Class C/D/E)

Exit code: 0 under the ceiling (or not enough diff to judge), 1 on HALT.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

# ── the ceilings ──────────────────────────────────────────────────────────────
#
# Ratio of added test lines to added implementation lines. These are the RULE for what each
# stakes level buys on this axis, and this is their single home — `gate-check.py` validates
# that the plan states a level, and says nothing about what a level costs.
#
# The numbers are deliberately generous. A tripwire that fires on ordinary work is a
# tripwire people learn to route around, and a routed-around gate is worse than none: it
# still costs a run and it no longer informs. These are set to catch runaways, not to tune
# anybody's testing taste.
#
#   high     — money, data, access, privacy, irreversibility. Several times the
#              implementation in tests is the correct shape here.
#   standard — a failure breaks a working feature for real users, recoverably. The default,
#              and where most work lives.
#   low      — a failure shows a broken or empty page and is caught by looking at it.
CEILINGS = {"high": 4.0, "standard": 2.5, "low": 1.0}
DEFAULT_STAKES = "standard"   # what a pre-0.16 plan (no Stakes: line) falls back to

# Below this many added test lines the ratio is noise — a 3-line implementation with a
# 40-line fixture is not a runaway, it is a normal small task. The tripwire is looking for
# accumulation, so it stays quiet until there is some.
MIN_TEST_LINES = 200

# Mirrors gate-check.py's STAKES_LINE + STAKES_TOKEN. The FIELD is parsed in two places
# because bin/ scripts are standalone by convention (no cross-imports, hyphenated
# filenames); the RULE lives once, in CEILINGS above. If you change the field's shape,
# change it in both. Tolerant tail (any reason punctuation), whole-token level match
# (`low-ish` is unreadable, never its `low` prefix), and fenced examples stripped first —
# all three mirrored from gate-check.py so the two tools never read one plan differently.
STAKES_LINE = re.compile(
    r"^\s*(?:[-*]\s+)?(?:\*\*)?Stakes(?:\*\*)?:\s*(\S.*?)\s*$",
    re.IGNORECASE | re.MULTILINE)
STAKES_TOKEN = re.compile(r"[A-Za-z][\w-]*")


def strip_fenced(text: str) -> str:
    """Drop fenced code blocks — a plan quoting the `Stakes:` template must not have the
    quoted sample read as its declared level (minimal mirror of gate-check.py's)."""
    out, in_fence = [], False
    for ln in text.splitlines():
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(ln)
    return "\n".join(out)

# ── what counts as a test file ────────────────────────────────────────────────
#
# Path-shaped, across the stacks this harness runs on. Deliberately broad: a MISSED test
# file understates the ratio and lets a runaway pass silently, which no one ever notices;
# over-matching at worst overstates it and surfaces a question to a human — the recoverable
# direction for a tripwire (I6: this comment originally had the direction inverted).
TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec|specs|e2e|cypress)(/|$)"
    r"|\.(test|spec)\.[jt]sx?$"
    r"|(^|/)test_[^/]+\.py$|_test\.py$"
    r"|[^/]*(Test|Cest|TestCase)\.php$"
    r"|\.feature$",
    re.IGNORECASE)

# Neither test nor implementation — changing these should move the ratio in no direction.
NON_CODE = re.compile(
    r"\.(md|markdown|txt|rst|json|ya?ml|toml|ini|cfg|lock|svg|png|jpe?g|gif|webp|ico)$"
    r"|(^|/)(docs?|specs?/[^/]+/(spec|plan|tasks)\.md)(/|$)"
    r"|(^|/)\.github(/|$)",
    re.IGNORECASE)


def git_numstat(rng: str, repo: Path) -> list[tuple[int, int, str]]:
    """[(added, deleted, path)] for a git range. Binary files (numstat '-') are dropped."""
    out = subprocess.run(
        ["git", "diff", "--numstat", rng],
        cwd=repo, capture_output=True, text=True, timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.strip() or f"git diff --numstat {rng} failed")
    rows = []
    for line in out.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) != 3 or parts[0] == "-":
            continue
        path = parts[2]
        # `git diff` renders renames as `old => new`; charge the new path. S1: a whole-path
        # rename (`old.py => new.py`, no braces) takes the RIGHT side — the old
        # `.replace(" => ", "")` concatenated both halves into a path that matched nothing.
        if " => " in path:
            path = re.sub(r"\{[^}]*=> *([^}]*)\}", r"\1", path).split(" => ")[-1]
        rows.append((int(parts[0]), int(parts[1]), path))
    return rows


def classify(path: str) -> str:
    """'test' | 'impl' | 'skip'."""
    if NON_CODE.search(path):
        return "skip"
    if TEST_PATH.search(path):
        return "test"
    return "impl"


def read_stakes(spec_dir: Path | None) -> tuple[str, str]:
    """(level, where it came from). Falls back to DEFAULT_STAKES, loudly."""
    if spec_dir is None:
        return DEFAULT_STAKES, "no feature dir given"
    plan = spec_dir / "plan.md"
    if not plan.exists():
        return DEFAULT_STAKES, f"no plan.md in {spec_dir}"
    m = STAKES_LINE.search(strip_fenced(plan.read_text()))
    if not m:
        return DEFAULT_STAKES, "plan states no `Stakes:` line (pre-0.16)"
    tok = STAKES_TOKEN.match(m.group(1).strip())
    level = tok.group(0).lower() if tok else m.group(1).strip().lower()
    if level not in CEILINGS:
        return DEFAULT_STAKES, f"plan states an unreadable level `{level}`"
    return level, str(plan)


def measure(rng: str, repo: Path):
    test_lines = impl_lines = 0
    per_file = []
    for added, _deleted, path in git_numstat(rng, repo):
        kind = classify(path)
        if kind == "test":
            test_lines += added
        elif kind == "impl":
            impl_lines += added
        if kind != "skip" and added:
            per_file.append((kind, added, path))
    return test_lines, impl_lines, per_file


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="verification-effort tripwire")
    ap.add_argument("spec_dir", type=Path, nargs="?",
                    help="feature dir holding plan.md (omit for Class C/D/E work)")
    ap.add_argument("--base", required=True,
                    help="git ref or range: `main` becomes `main...HEAD`")
    ap.add_argument("--stakes", choices=sorted(CEILINGS),
                    help="override the plan's level (does not edit the plan)")
    ap.add_argument("--repo", type=Path, default=Path("."))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    rng = args.base if ".." in args.base else f"{args.base}...HEAD"

    if args.stakes:
        level, source = args.stakes, "--stakes override"
    else:
        level, source = read_stakes(args.spec_dir)
    ceiling = CEILINGS[level]

    try:
        test_lines, impl_lines, per_file = measure(rng, args.repo)
    except (RuntimeError, subprocess.SubprocessError) as exc:
        print(f"verify-budget: cannot read the diff — {exc}", file=sys.stderr)
        return 0                      # fail-open: never block work on a tooling problem

    ratio = (test_lines / impl_lines) if impl_lines else (float("inf") if test_lines else 0.0)
    quiet = test_lines < MIN_TEST_LINES
    halt = (not quiet) and ratio > ceiling

    if args.json:
        print(json.dumps({
            "range": rng, "stakes": level, "stakes_source": source,
            "ceiling": ceiling, "test_lines": test_lines, "impl_lines": impl_lines,
            "ratio": None if ratio == float("inf") else round(ratio, 2),
            "below_measurement_floor": quiet, "halt": halt,
        }, indent=2))
        return 1 if halt else 0

    shown = "∞" if ratio == float("inf") else f"{ratio:.2f}"
    print(f"  range     {rng}")
    print(f"  stakes    {level}  (from: {source})")
    print(f"  added     {test_lines} test / {impl_lines} implementation")
    print(f"  ratio     {shown}×   ceiling {ceiling}×")

    if quiet:
        print()
        print(f"BUDGET: PASS — under the {MIN_TEST_LINES}-line measurement floor, "
              "too little to judge")
        return 0

    if not halt:
        print()
        print("BUDGET: PASS")
        return 0

    heaviest = sorted((r for r in per_file if r[0] == "test"),
                      key=lambda r: -r[1])[:5]
    print()
    if impl_lines == 0:
        # I7 — a test-only range has no ratio to judge, and that shape is a runaway by
        # definition once it clears the measurement floor: say what it is instead of
        # comparing ∞ against a ceiling.
        print(f"BUDGET: HALT — test-only range: {test_lines} test lines added against "
              f"ZERO implementation lines; there is no ratio to judge here, and a "
              f"test-only accumulation past the {MIN_TEST_LINES}-line floor is the "
              "runaway shape itself.")
    else:
        print(f"BUDGET: HALT — {shown}× exceeds the {ceiling}× a `{level}`-stakes feature buys.")
    print()
    print("  Heaviest test files in this range:")
    for _kind, added, path in heaviest:
        print(f"    {added:>6}  {path}")
    print()
    print("  STOP and put this in front of your human partner. Do NOT resolve it by deleting")
    print("  tests, and do NOT quietly continue. Report: what was verified, what it cost, and")
    print("  which of these is true —")
    print()
    print(f"    1. The stakes line is wrong. This work is riskier than `{level}` says.")
    print("       Raise it in the plan (a plan-correction commit) and carry on. This is a")
    print("       normal outcome, not a failure.")
    print("    2. Evidence is being duplicated. Something on the ladder's cheaper rungs — a")
    print("       machine gate, a framework guarantee — already proves what these tests")
    print("       re-prove by hand. See testing-workflow's evidence ladder.")
    print("    3. Edges are being driven as durable specs that should have been driven once.")
    print("       See feature-acceptance: a drive becomes a committed spec only on a")
    print("       money/data path or where the edge reproduced a real bug.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
