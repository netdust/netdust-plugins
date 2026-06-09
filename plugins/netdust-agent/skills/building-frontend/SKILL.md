---
name: building-frontend
description: "CRAFT skill — the engineering layer for building UI, layered on the frontend-design plugin (the base, which owns distinctive production-grade visual craft and avoids the generic AI aesthetic). Reached for at harnessed-development Stage 2 (execute) on UI tasks. It defers the visual/creative implementation to frontend-design, then adds the engineering layer: component architecture, the state-management ladder, accessibility (WCAG 2.1 AA), responsive breakpoints, loading/transition states, and the red-flags that signal a component has drifted. The Netdust layer superpowers/addy cannot know: the empty/error/loading states you build here ARE the feature-acceptance edge classes that make those flows pass, and UI tasks are usually Tier B for unit tests — so the real verification is feature-acceptance through a real browser, not a jsdom render. Use when implementing a component, page, or interactive flow."
---

<objective>
This skill does NOT teach you how to make UI look good — `frontend-design` owns that, and owns avoiding the generic AI aesthetic. This skill **layers the engineering discipline on top**: how the component is structured, where its state lives, whether it is reachable by keyboard, how it behaves at every breakpoint and in every non-happy state. You are at Stage 2 (execute) of `harnessed-development`, on a UI task. `frontend-design` makes it distinctive; this skill makes it sound.
</objective>

<first_load_the_base>
**Before building anything, invoke the `frontend-design` plugin.** It owns the visual/creative craft this skill does not duplicate:

- distinctive, production-grade layout, type, color, and motion that avoids the generic AI look
- the creative implementation decisions — visual hierarchy, spacing rhythm, the polished feel

If frontend-design is not available, that is the prerequisite for the *look*. This skill assumes it and adds the engineering layer below.
</first_load_the_base>

<component_architecture>
**Colocate, compose, keep components focused.** A component does one job; if it does several, split it. Colocate a component with its styles, tests, and local hooks. **Separate data-fetching containers from presentation** — a presentational component takes props and renders, a container fetches and passes down — so the render is testable without the network and the data path is swappable. Compose small pieces over building one large conditional-laden component.
</component_architecture>

<state_management_ladder>
Reach for the *lowest* rung that works; climb only when forced. Prop-drilling past **3 levels** is the signal to climb.

1. **`useState`** — state used by one component.
2. **Lifted state** — shared by a couple of siblings; lift to the common parent.
3. **Context** — cross-cutting, low-churn (theme, current user); not for high-frequency updates.
4. **URL state** — anything that should survive reload or be shareable/linkable (filters, selected tab, open slideover).
5. **Server state** — server-owned data via a query library (react-query/TanStack Query); cache + invalidation, not hand-rolled `useEffect` fetches.
6. **Global store** — last resort, for genuinely app-wide client state no rung above fits.
</state_management_ladder>

<accessibility>
**WCAG 2.1 AA is the floor, not a nice-to-have.** Every interactive element is keyboard-reachable and operable (tab order, Enter/Escape/arrows where expected). Use semantic elements first; add ARIA only to fill gaps, never to paper over a `div` that should have been a `button`. **Manage focus in modals/slideovers** — trap focus inside, restore it to the trigger on close. Never signal state by **color alone** — pair it with an icon, text, or shape. Provide meaningful **empty and error states**, not a blank region.
</accessibility>

<responsive_and_states>
**Mobile-first**, then layer up. Test the real breakpoints: **320 / 768 / 1024 / 1440**. Build the full state set for every async surface — **skeletons** while loading (not a spinner-on-blank), **optimistic updates** that roll back on failure, and the empty + error states above. A component that only renders its happy, populated, desktop state is unfinished.
</responsive_and_states>

<red_flags>
Stop and refactor when you see: a component **over ~200 lines** (it is doing too much — split it); **inline magic pixels** scattered in JSX instead of tokens/scale; a **missing state** (no loading, empty, or error branch); a **color-only** status indicator; **prop-drilling past 3 levels** (climb the ladder); a presentational component that fetches its own data (split the container out).
</red_flags>

<the_netdust_layer>
The part frontend-design and addy cannot know — why this how-to lives inside *this* harness:

**1. The states you build here ARE the feature-acceptance edge classes.** The empty/zero state, the error/mid-flow-failure state, and the denied/loading states are exactly the edge classes the `feature-acceptance` gate (1g) enumerates per flow. Building them here is not polish — it is what makes those acceptance rows turn `pass` instead of `fail`. A component shipped without its empty/error states guarantees a failing acceptance flow downstream.

**2. UI tasks are usually Tier B — so a jsdom unit test is NOT the verification.** Per `testing-workflow`, a classname/layout/render assertion is Tier B (no bespoke unit test earns its keep, and jsdom masks real-browser behavior — this project shipped a jsdom-masked InlineEdit race that passed green). The real verification of a UI flow is `feature-acceptance` driving it through a **real browser** (via `driving-the-browser`), not a Vitest render. Do not mistake a green jsdom render for a working flow.
</the_netdust_layer>

<success_criteria>
A UI surface built under this skill:
- Started from `frontend-design` for the distinctive, production-grade look — not reinvented here.
- Has **focused, composed components** with data-fetching split from presentation; no component over ~200 lines.
- Uses the **lowest sufficient rung** of the state ladder; no prop-drilling past 3 levels.
- Is **keyboard-reachable, focus-managed, never color-only**, with meaningful empty/error states (WCAG 2.1 AA).
- Is **mobile-first**, verified at 320/768/1024/1440, with skeletons + optimistic-with-rollback.
- Built its empty/error/loading states deliberately so the **feature-acceptance** edge rows can pass — and is verified through a **real browser**, not a jsdom render.
</success_criteria>

<integration>
- **`frontend-design` plugin** — the BASE this skill layers on. Owns the distinctive visual/creative craft and the anti-AI-aesthetic. This skill does not restate it; it adds the engineering layer.
- **`harnessed-development` Stage 2 (execute)** — the step that reaches for this skill on UI tasks.
- **`feature-acceptance` (gate 1g/Stage 3)** — the empty/error/loading states you build here are its edge classes; building them is what makes its flows pass. It drives the flow through a real browser to earn the `pass`.
- **`testing-workflow`** — UI render/classname assertions are Tier B; the gate will usually not ask for a bespoke unit test here. The verification altitude is the browser, not jsdom.
- **`driving-the-browser`** — the how-to for the real-Chrome drive that feature-acceptance uses to verify these flows.
- **Provenance** — visual craft from the `frontend-design` plugin; the engineering layer (component architecture, state ladder, a11y, responsive, red flags) folded from `addyosmani/agent-skills:frontend-ui-engineering` (MIT); the feature-acceptance / Tier-B / real-browser wiring is the Netdust spine this file adds.
</integration>
