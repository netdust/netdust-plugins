"""
test_split_seam.py — structural assertions for the plan/build split (agent 0.5.0).

The split's whole value is the enforced seam: `planning` must stop at an approved,
gate-checked tasks.md and never execute; `building` must demand that artifact FIRST,
before anything else; the router must stay thin (no stage content to drift). Skills are
prose, so these are wiring checks, not behavior checks — they catch the regressions that
would quietly re-fuse the spines: stage content creeping back into the router, the
precondition sliding below the process, the dispatch addendum drifting out of building,
or a calibration home left pointing at the pre-split god-skill.
"""
from pathlib import Path

SKILLS = Path(__file__).parent.parent / "skills"


def run():
    results = []

    def check(desc, cond):
        results.append((bool(cond), desc))

    planning = (SKILLS / "planning" / "SKILL.md").read_text()
    building = (SKILLS / "building" / "SKILL.md").read_text()
    router = (SKILLS / "harnessed-development" / "SKILL.md").read_text()
    calibrations = (SKILLS / "_shared" / "calibrations.md").read_text()

    # ── the seam, planning side ──────────────────────────────────────────────
    check("planning: names gate-check.py as the seam's machine check",
          "gate-check.py" in planning)
    check("planning: has an explicit STOP-at-the-seam section",
          "## The seam — STOP here" in planning)
    check("planning: forbids invoking building itself",
          "Do not invoke `building`" in planning)
    check("planning: carries the plan-time gates (1a/1b/1c/1e/1g + task-shaping 1d)",
          all(f"**1{k}." in planning for k in "abdeg"))
    check("planning: task-shaping gate absorbs 1f and 1h as facets",
          "(1f)" in planning and "(1h)" in planning)
    check("planning: no execution machinery (dispatch addendum stays in building)",
          "addendum_for_dispatch" not in planning
          and "Netdust addendum — mandatory close-out" not in planning)

    # ── the seam, building side ──────────────────────────────────────────────
    first_tag = building.split("---", 2)[2].lstrip()
    check("building: <precondition> is the FIRST section after frontmatter",
          first_tag.startswith("<precondition>"))
    check("building: precondition demands a fresh gate-check run (exit 0), not an assertion",
          "gate-check.py" in building
          and "do not trust a transcript assertion" in building)
    check("building: precondition covers every plan-less class entry (C, D, E)",
          all(f"**{c} —" in building for c in "CDE"))
    check("building: carries the verbatim dispatch addenda (test/dev split pair)",
          "## Netdust addendum — test-author close-out (RED)" in building
          and "## Netdust addendum — implementer close-out (GREEN)" in building)
    check("building: keeps the /speckit.implement red flag",
          "NEVER `/speckit.implement`" in building)
    check("building: owns the armed loop protocol",
          "loop-gate.py" in building and "loop-check.py" in building)
    check("building: no plan-authoring content (1a gate text lives in planning only)",
          "**1a." not in building)

    # ── the router stays thin ────────────────────────────────────────────────
    check("router: routes to both spines",
          "`planning`" in router and "`building`" in router)
    check("router: keeps the class dial (A–E intake table)",
          all(f"**{c} —" in router for c in "ABCDE"))
    check("router: no stage content re-fused in (no Step 2.x, no gate bodies, no addendum)",
          "Step 2.5" not in router
          and "## Stage" not in router
          and "addendum" not in router.lower())
    check("router: stays thin (< 120 lines; god-skill was ~375)",
          len(router.splitlines()) < 120)
    check("router: old trigger phrases still resolve here (execute-the-plan compat)",
          "execute the plan" in router and "ntdst-execute-with-tests" in router)

    # ── calibration homes moved with their gates ─────────────────────────────
    check("calibrations: no full-story home left at the god-skill's gate/step sections",
          "harnessed-development/SKILL.md` (gate" not in calibrations
          and "harnessed-development/SKILL.md` (Step" not in calibrations
          and "harnessed-development/SKILL.md` (integration" not in calibrations)
    check("calibrations: plan-time homes point at planning",
          "planning/SKILL.md` (gate 1a)" in calibrations)
    check("calibrations: execution homes point at building",
          "building/SKILL.md` (Step 2.5)" in calibrations)

    return results


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
