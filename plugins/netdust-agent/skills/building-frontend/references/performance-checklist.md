# Frontend Performance Checklist — The Engineering-Perf Layer

The scannable perf checklist `building-frontend` (and the `performance-oracle` agent) points at. This is the **engineering** perf layer — bundle, render, network, Core Web Vitals — NOT the visual layer (`frontend-design` owns look). Each item is a control you confirm present (`[x]`) or flag (`[ ]`).

Source material folded from `addyosmani/agent-skills:performance-checklist` (MIT): Core Web Vitals, bundle budgets, image optimization, caching, N+1. Adapted into this harness's vocabulary.

> The `performance-oracle` agent loads this checklist for its analysis. Measure-first ties to the `driving-the-browser` craft skill (real Chrome DevTools profiling) — never optimize from source-reading alone.

---

## Core Web Vitals targets

| Metric | Target | What it measures | Worst offender |
|---|---|---|---|
| **LCP** Largest Contentful Paint | **< 2.5s** | Main content visible | Unoptimized hero image, render-blocking JS/CSS, slow server |
| **INP** Interaction to Next Paint | **< 200ms** | Responsiveness to input | Long tasks on the main thread, un-debounced handlers, heavy re-renders |
| **CLS** Cumulative Layout Shift | **< 0.1** | Visual stability | Images without dimensions, late-injected banners, font swap (FOUT) |

- [ ] LCP element identified and its load path is on the critical path (preloaded if needed)
- [ ] INP-heavy interactions broken up / yielded; no single long task > ~50ms blocking input
- [ ] CLS guarded — every async-inserted element reserves its space

---

## Measure-first (do NOT optimize without a profile)

- [ ] Profiled BEFORE changing anything — via `driving-the-browser` (real Chrome DevTools Performance panel), not from reading source. A from-source guess was wrong before (see building-frontend lessons / measure-DOM-for-layout-bugs).
- [ ] Bottleneck confirmed with a number (a flame chart span, a network waterfall entry, a `getBoundingClientRect`/`scrollHeight` measurement), not a hunch
- [ ] After the fix: re-profiled to prove the number moved — `performance-oracle` projects at 10×/100×/1000× data volume
- [ ] No micro-optimization of a path the profile shows is cold

---

## Bundle & code-splitting

- [ ] A bundle budget is set and checked (initial JS gzip target — flag regressions)
- [ ] Routes lazy-loaded (`React.lazy` / dynamic `import()` at the TanStack Router route boundary) — not one monolithic bundle
- [ ] Heavy editors (Milkdown / CodeMirror) code-split, loaded only when a document opens — not on first paint
- [ ] Tree-shaking effective — no barrel-file or default-import pulling a whole library for one util; named imports
- [ ] No giant dependency where a small one (or none) works; dedupe duplicate deps in the lockfile

---

## Images

- [ ] Responsive `srcset` + `sizes` — the browser picks the right resolution per viewport
- [ ] Modern formats (AVIF/WebP) with fallback
- [ ] **Explicit `width`/`height` (or aspect-ratio box)** on every image — the primary CLS fix; ties to building-frontend's responsive/layout content
- [ ] Below-the-fold images `loading="lazy"`; the LCP/hero image is NOT lazy (eager + optionally preloaded)
- [ ] Images compressed; no full-resolution asset served into a thumbnail slot

---

## Rendering

- [ ] No layout thrash — reads (`getBoundingClientRect`) and writes batched, not interleaved in a loop
- [ ] Expensive renders memoized (`React.memo`, `useMemo`, `useCallback`) — but only where a profile shows the cost; not reflexively
- [ ] **Long lists virtualized** (windowing) — a table/feed of hundreds of rows doesn't mount every node
- [ ] Stable `key`s (no array index where order changes) so React reconciles instead of remounting
- [ ] No unstable inline object/array/function props forcing memoized children to re-render every cycle
- [ ] Derived state computed, not stored-and-synced (a synced buffer caused the React-Query refetch-toggle oscillation)

---

## Data & network

- [ ] Server state through the query cache (TanStack Query) — not hand-rolled `useEffect` fetches; cache + invalidation, not refetch-everything
- [ ] **No N+1**: a list view fetches in one query/batch, not one request per row (the `performance-oracle` DB check — eager-load / join / batch)
- [ ] Paginated (keyset/cursor where order matters) — no unbounded "fetch all rows"
- [ ] User-typed triggers (search, inline-edit save) **debounced**; high-frequency events throttled
- [ ] Cache headers / immutable hashed asset filenames so the browser and CDN can cache statics
- [ ] Invalidation keyed correctly — broad enough to refresh every consumer, narrow enough not to thrash (the narrow-key list-invalidation miss)
- [ ] SSE/EventSource streams reused, not opened per-component (≈6 per-origin cap → pool exhaustion = "stuck on Saving…")

---

## Red flags — stop and fix

- "Optimizing" before profiling — you don't know the bottleneck yet (Measure-first)
- An image with no `width`/`height` — guaranteed CLS
- A list rendering hundreds of rows with no virtualization
- One bundle for the whole app — no route splitting, editors loaded on first paint
- A `useEffect` fetch loop where the query library belongs — refetch storms, no cache
- One DB request per row in a list — N+1
- A save/search handler firing on every keystroke un-debounced
- Reflexive `useMemo`/`React.memo` everywhere with no profile justifying it (memoization has its own cost)
- A new EventSource per component instead of a shared stream

---

Using this list: profile first (`driving-the-browser`), confirm the bottleneck with a number, then walk the relevant section. A red flag in the diff with no measurement behind the "fix" is itself a finding — `performance-oracle` reports the number, not the vibe.
