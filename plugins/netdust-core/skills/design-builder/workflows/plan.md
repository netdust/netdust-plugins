# Plan Workflow

**Purpose:** Turn the locked Discover spec into the design bundle: the stride-
style output contract this skill exists to produce.

**Gate:** User approves the plan before any code is written.

**Prerequisite:** Locked spec from Discover, including `motion-spec.md`
citations. If Discover hasn't run, redirect there first — Plan does not
re-derive tokens or motion values, it only assembles what Discover measured.

## Step 1: Verify the spec is complete

- [ ] All design tokens confirmed by user.
- [ ] Motion tables cite `motion-spec.md` values (or the video-frame-counted
      equivalent for the video-only route) — no open rows left unresolved.
- [ ] Section inventory complete.
- [ ] Out-of-scope list exists.

## Step 2: Choose the target stack

The reference is the result, never the stack. Pick the stack for THIS build
at Plan time, based on the project it's going into — not the reference's own
stack. If the project already has a framework skill (WP block theme, Statamic
Antlers, a component framework), defer HOW to build to that skill; this
workflow only fixes WHAT gets built and against which measured values.

## Step 3: Generate the design bundle

Output as a complete artifact, not a summary. Four parts:

### 1. `tokens.css` — single source of truth

```css
:root {
  /* Colors */
  --color-bg:           [value];
  --color-text:         [value];
  --color-accent:       [value];

  /* Typography */
  --font-display:       [family], [fallback];
  --size-display:       [px];
  --weight-display:     [100-900];

  /* Spacing */
  --space-section:      [px];
  --space-gap:          [px];

  /* Motion — durations/easings copied from motion-spec.md, not re-derived */
  --duration-load:      [ms from motion-spec.md];
  --easing-load:        [cubic-bezier(...) from motion-spec.md];
}

@media (max-width: 959px) {
  :root {
    --size-display:     [px];
    --space-section:    [px];
  }
}

@media (prefers-reduced-motion: reduce) {
  * { animation-duration: 0.01ms !important; transition-duration: 0.01ms !important; }
}
```

Every value here traces to a Discover token or a `motion-spec.md` row. If a
value in this file isn't traceable, it doesn't belong here — go back to
Discover.

### 2. Component sheet — all states

For each reusable component (nav, card, button, hero), a states matrix:
default, hover, focus, active, disabled, empty, loading, error — whichever
apply. Hover/active values come from `motion-spec.md`'s Hover table where the
component was captured there; states the capture didn't measure get an open
flag, not a guess.

### 3. Per-screen mockups

One section-by-section spec per screen, in build order:

| Attribute | Value |
|---|---|
| Layout | [column structure, from Discover] |
| Background | [color token] |
| Content | [what goes in this section, ordered] |
| Typography | [element → size token → weight] |
| Responsive | [how layout changes on mobile] |

**Acceptance criteria** per section — specific and screenshot-verifiable
(e.g. "image fills column height with object-fit cover", not "image looks
good").

### 4. Motion plan — citing measured values

| Section | Trigger | Selector | Duration | Easing | Scroll range / stagger | Source |
|---|---|---|---|---|---|---|
| Hero | load | `.hero h1` | 600ms | cubic-bezier(0.16,1,0.3,1) | stagger 80ms × 3 | motion-spec.md:Page-load |
| Cards | scroll | `.card` | 400ms | ease-out | 12–28% | motion-spec.md:Scroll-triggered |

The **Scroll range / stagger** column takes whichever field the row's own
Source table actually has — a Page-load row can carry a Stagger value, a
Scroll-triggered row only ever carries a scroll range (that table has no
Stagger column in `motion-spec.md`; don't invent one). The **Source** column
is mandatory — every row points at the `motion-spec.md` table it came from. A
motion row with no source is a guess and doesn't belong in the plan.

## Step 4: Get approval

**Say:** "Here's the design bundle — `tokens.css`, component sheet, per-screen
mockups, and the motion plan citing measured values. Review and confirm
before I write any code. Anything to change?"

**Wait for explicit approval.**

**When approved, say:** "Plan locked. Moving to Execute — one section at a
time, each verified with screenshots before the next."

Then proceed to `workflows/execute.md`.
