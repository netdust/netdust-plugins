## 2026-08-12 — revival from `_backup/design-builder-skill`, T09

- **Motion is measured, never inferred.** The retired skill family's Discover
  step said "Animation (infer from context)" and its token sheet let
  "Inferred: Derived from reference (flag clearly)" stand as a legitimate
  category alongside "Confirmed". That's the exact failure mode that retired
  it — a screenshot doesn't carry duration, easing, or scroll-trigger range;
  guessing them produced motion that looked plausible and was wrong. The
  revived Discover has no "inferred" category at all: every motion value in
  the token sheet and every row in the Plan's motion plan traces to a
  `motion-spec.md` file the `capture_motion` MCP tool actually wrote (or, on
  the video-only route, a frame-counted measurement — still a number someone
  counted, never a number someone assumed).

- **Vocabulary-first skills under-document choreography.** The backup's
  `references/animation.md` gave a vocabulary (parallax, scrollspy, sticky)
  and a one-line "Animation Plan" table row per section
  (`| Cards | Stagger reveal | uk-scrollspy... | 100ms stagger | viewport |`).
  A vocabulary word and a guessed number cannot recreate a reference's actual
  choreography — the reference's stagger might be 60ms with an eased curve,
  not a round 100ms. This skill dropped the vocabulary reference entirely and
  replaced it with the measured per-trigger tables `motion-spec.md` produces
  (Page-load / Scroll-triggered / Hover / Continuous, each with Duration,
  Easing — including a fitted cubic-bezier with its max error — and Stagger
  columns). The lesson generalizes past this skill: any future skill that
  reduces a build-time behavior to a short descriptive label instead of a
  measured or captured value is repeating this mistake.

- Dropped `references/{uikit,animation,statamic,design-system}.md` and
  `patterns/` from the revival — those were the vocabulary-first material the
  second lesson above targets, and none of the netdust-core skill deliverables
  for this task called for them. Stack-specific HOW now lives with the
  project's own framework skill (chosen at Plan time — see `workflows/plan.md`
  Step 2); this skill only owns the measured WHAT.
