<overview>
WCAG 2.1 AA verification checklist — the concrete line-item version of the principles in
building-frontend's `<accessibility>` section. That section states the principles
(keyboard-reachable, semantic-first, focus management in modals, never color-alone,
empty/error states); this checklist makes them VERIFIABLE. Walk it before a UI flow goes
to feature-acceptance. The empty/error/loading rows below ARE the feature-acceptance edge
classes — building them here is what makes those acceptance flows pass.

Tick each `[ ]` against the real component. Skip a section only if it genuinely doesn't apply.
Source: WCAG 2.1 AA, folded from addyosmani/agent-skills accessibility-checklist (MIT).
</overview>

<keyboard>
**Keyboard — operable without a mouse**
- [ ] Every interactive element (link, button, input, custom control) is reachable by Tab
- [ ] Every interactive element is operable by keyboard (Enter/Space activates, arrows where expected)
- [ ] A visible focus ring is present on every focusable element (don't `outline: none` without a replacement)
- [ ] No keyboard trap — focus can always move away (except an intentional modal trap, see below)
- [ ] Tab order is logical and follows visual/reading order (no DOM-order surprises)
- [ ] Escape closes overlays (modal, slideover, popover, menu) and returns focus
</keyboard>

<focus_management>
**Focus Management — overlays and dynamic content**
- [ ] Focus moves INTO a modal/slideover when it opens (to the dialog or first focusable)
- [ ] Focus is TRAPPED inside the open modal/slideover (Tab cycles within, doesn't escape behind)
- [ ] Focus is RESTORED to the triggering element when the overlay closes
- [ ] `:focus-visible` styling is preserved — never globally stripped
- [ ] Newly revealed content (async results, expanded sections) is announced or focus-managed, not silent
</focus_management>

<semantic_aria>
**Semantic HTML & ARIA — structure first**
- [ ] Native elements used first (`<button>`, `<a href>`, `<nav>`, `<input>`) — not a `<div>` with a click handler
- [ ] ARIA used ONLY to fill gaps native HTML can't express — never to paper over the wrong element
- [ ] Landmarks present and correct (`<header>`/`banner`, `<nav>`, `<main>`, `<footer>`/`contentinfo`)
- [ ] Heading hierarchy is logical and unskipped (one `<h1>`, no jump from `<h2>` to `<h4>`)
- [ ] Interactive controls have accessible names (visible label, `aria-label`, or `aria-labelledby`)
- [ ] Icon-only buttons carry an `aria-label`; decorative icons are `aria-hidden`
- [ ] Custom widgets carry correct roles + states (`role`, `aria-expanded`, `aria-selected`, `aria-checked`)
</semantic_aria>

<color_contrast>
**Color & Contrast**
- [ ] Normal text meets 4.5:1 against its background
- [ ] Large text (≥18.66px bold or ≥24px) meets 3:1
- [ ] UI components and graphical objects (icons, borders, focus rings, chart strokes) meet 3:1
- [ ] State is NEVER signalled by color alone — pair it with an icon, text label, or shape
  (error/success/required/selected all carry a non-color cue)
</color_contrast>

<images_media>
**Images & Media**
- [ ] Meaningful images have descriptive `alt` text conveying their purpose
- [ ] Decorative images have empty `alt=""` (so screen readers skip them)
- [ ] Complex images (charts, diagrams) have a longer text alternative nearby
- [ ] Video/audio has captions or a transcript where content is conveyed
</images_media>

<forms>
**Forms**
- [ ] Every input has an associated `<label>` (via `for`/`id`, not placeholder-as-label)
- [ ] Errors are announced (live region / `aria-describedby`) AND visually associated with their field
- [ ] Required fields are indicated by text or `aria-required`, not by color/asterisk alone
- [ ] Grouped controls (radios, related fields) use `<fieldset>` + `<legend>`
- [ ] Input purpose set where it helps autofill (`autocomplete`, `type="email"`, etc.)
</forms>

<motion_states>
**Motion & States**
- [ ] `prefers-reduced-motion` is respected — animations/transitions reduced or removed when set
- [ ] No content flashes more than 3×/second
- [ ] Loading state is meaningful (skeleton/text), not a blank region
- [ ] Empty state is meaningful (guidance/CTA), not a blank region
- [ ] Error state is meaningful and recoverable, not a blank region or silent failure
  (these three are the feature-acceptance edge classes — build them deliberately)
</motion_states>

<how_to_verify>
**How to verify — don't eyeball it, drive it**
- [ ] **Keyboard-only pass** — unplug the mouse; complete every flow (open/close overlays, submit forms, navigate) using only Tab/Shift-Tab/Enter/Space/Escape/arrows
- [ ] **Automated scan** — run axe-core (or Lighthouse Accessibility) against the live page; triage every violation
- [ ] **Accessibility-tree inspection** — use `driving-the-browser` to read the live a11y tree (names, roles, states) and confirm controls expose what assistive tech needs
- [ ] **Contrast check** — sample real rendered colors (DevTools contrast picker), not the design-token values in isolation
- [ ] Feed the empty/error/loading rows above into **feature-acceptance** as the edge classes for each flow
</how_to_verify>

<integration>
- Extends building-frontend's `<accessibility>` section — that names the principles, this is the verifiable line-item version.
- An `accessibility-reviewer` pass (or `driving-the-browser`'s a11y-tree inspection) can load this checklist as its rubric.
- The empty/error/loading rows are `feature-acceptance` edge classes — verify them through a real browser, not a jsdom render.
</integration>
