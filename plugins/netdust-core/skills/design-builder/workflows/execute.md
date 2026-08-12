# Execute Workflow

**Purpose:** Build the approved plan one section at a time, with mandatory
visual verification per section.

**Gate:** Each section verified with a screenshot before moving to the next.

**Prerequisite:** Approved plan from `workflows/plan.md`. Target stack
confirmed there.

## The Iron Law

```
NO SECTION COMPLETION WITHOUT VISUAL VERIFICATION
```

This applies to every section. No exceptions.

## Step 1: Setup (always first)

Load `tokens.css` from the plan as-is — don't re-derive values here. Wire it
into the chosen stack's base layer (its own framework skill owns HOW; this
skill only owns that the tokens and motion values are the plan's, verbatim).

Self-check before the first section:
- [ ] All CSS custom properties from the plan are present.
- [ ] Font loading confirmed.
- [ ] `prefers-reduced-motion` override present.

## Step 2: Build loop (per section)

### 2a. Write the section

Use the plan's section spec exactly — layout, tokens, motion attributes named
there. Semantic HTML; class names describe purpose (`section-hero`, not
`big-dark-section`).

### 2b. Screenshot and compare (desktop)

Take a screenshot of the built section at desktop width (per the plan's
target, typically 1440px).

**Comparison checklist — run for every section:**

| Category | Check |
|---|---|
| Layout | Column count and widths match the plan |
| Layout | Container width and edge alignment |
| Typography | Headline size, weight, family |
| Typography | Body size, line height |
| Colors | Background, text, accents |
| Spacing | Section padding, element gaps |
| Images | Crop, aspect ratio, object-fit |
| Motion | Attributes present and match the plan's motion-plan row (duration/easing) |

**Do not report "section complete" unless every check passes in the
screenshot.**

### 2c. Screenshot and compare (mobile, 375px)

Every section, no exceptions:
- Columns stack per the plan's responsive spec.
- Typography scales to the mobile tokens.
- No horizontal scroll.
- Touch targets adequate.

### 2d. Fix loop

For each mismatch: identify the specific cause, fix it, re-screenshot, compare
again.

**Max 3 attempts per issue.** After 3, stop and escalate:

> "I've tried 3 times to match [specific thing]. Screenshot shows [what I
> see] vs. the plan's [what it should be, citing the plan's value]. Should I
> [option A] or [option B]?"

Do not move to the next section until both desktop and mobile screenshots
pass.

### 2e. Report with evidence

When all checks pass at both widths:

> **Section [N] complete: [Name]**
>
> [Screenshot]
>
> Verified: layout, typography, colors, spacing, mobile (375px), motion
> attributes against the plan's motion-plan row.
>
> Proceed to Section [N+1]: [Name]?

**Wait for user approval before proceeding.**

## Step 3: Motion pass

After all sections are built, verify the full page against the plan's motion
plan: page-load sequence, scroll triggers, hover transitions, stagger timing.
Screenshot before/after states for anything not visible as a static frame.
Check no layout shift or jank.

## Step 4: Mobile pass

Full-page mobile verification at 375px across all sections: no horizontal
scroll, typography scaled, images resize, navigation works.

## Step 5: Final handoff

> **Build complete.**
>
> All [N] sections built and verified with screenshots at desktop and mobile.
> Tokens and motion values trace to `~/Sites/design-references/<name>/capture/motion-spec.md`.
>
> [Full-page screenshot]
>
> Anything to refine?

## Standards

- Semantic elements, `alt` text on images, `loading="lazy"` below the fold.
- One H1 per page.
- No inline styles for design decisions — tokens carry those.
- Never animate `width`/`height`/`top`/`left` — `transform`/`opacity` only.
- Reference imagery, copy, and brand marks never ship — only the abstracted
  technique (see `SKILL.md` — Reference material never ships).

## Red flags during execute

| Temptation | Response |
|---|---|
| Skip the screenshot "this time" | Take the screenshot. |
| "Close enough" | Measure the pixel values. |
| "I'll verify later" | Verify now. |
| Move to next section quickly | Wait for the checklist to pass. |
| "Mobile can wait" | Mobile is part of verification. |
| Report without evidence | Attach the screenshot. |

The screenshot is your evidence. No screenshot means no completion claim.
