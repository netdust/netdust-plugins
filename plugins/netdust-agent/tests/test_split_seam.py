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
          "## The seam — STOP" in planning)
    check("planning: forbids invoking building itself",
          "not invoke `building`" in planning)
    check("planning: carries the plan-time gates (threat model, invariants, ground-truth, stakes, deliverable-first, task shaping)",
          all(k in planning for k in ("## Threat model", "Architecture invariants",
              "ground-truth", "Stakes", "First working version", "Task shaping")))
    check("planning: carries the Source: rule and the behaviour-block grammar",
          "`Source:`" in planning and "Behaviour:" in planning)
    check("planning: no execution machinery (dispatch addendum stays in building)",
          "addendum_for_dispatch" not in planning
          and "Netdust addendum — mandatory close-out" not in planning)

    # ── the seam, building side ──────────────────────────────────────────────
    body = building.split("---", 2)[2]
    check("building: precondition is the FIRST section after frontmatter",
          body.lstrip().startswith("# Building") and
          body.index("## Precondition") < body.index("## Stage 2"))
    check("building: precondition demands a fresh gate-check run (exit 0), not an assertion",
          "gate-check.py" in building and "run NOW by you" in building)
    check("building: precondition covers every plan-less class entry (C, D, E)",
          all(f"| {c} " in building for c in "CDE"))
    check("building: carries the machine-parsed dispatch contract the stop hook consumes",
          "HARNESS-EVIDENCE" in building and "subagent-stop.py" in building)
    # The seam's other half: tasks.md is executed task-by-task THROUGH the gates.
    # Any flat executor over the task list bypasses threat-model verify, per-task
    # tiers, the review-cluster HALT and the subagent-stop backstop — so the red
    # flag against it must survive, whatever tool is proposing to do the walking.
    check("building: keeps the flat-executor red flag (tasks.md is never run flat)",
          "flat" in building.lower()
          and "bypass" in building.lower()
          and "The handoff is `tasks.md`" in building)
    check("building: repositions the test-author to feature tests after each contract-lane cluster",
          "Feature tests after each contract-lane cluster" in building)
    check("building: owns the armed loop protocol",
          "loop-gate.py" in building and "loop-check.py" in building)
    check("building: no plan-authoring content (threat-model section shape lives in planning only)",
          not any(ln.startswith("## Threat model") for ln in building.splitlines()))

    # ── the router stays thin ────────────────────────────────────────────────
    check("router: routes to both spines",
          "`planning`" in router and "`building`" in router)
    check("router: keeps the class dial (A–F intake table)",
          all(f"**{c}**" in router for c in "ABCDEF"))
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
    check("calibrations: index file still exists and names the load-bearing slugs",
          all(slug in calibrations for slug in
              ("contact-page-8k", "deliverable-last", "plan-drift-4x")))

    return results


if __name__ == "__main__":
    for passed, desc in run():
        print(("pass" if passed else "FAIL") + "\t" + desc)
