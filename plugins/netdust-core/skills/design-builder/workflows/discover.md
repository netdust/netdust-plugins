# Discover Workflow

**Purpose:** Capture the reference with real tooling and lock a token sheet +
measured motion tables through interview.

**Gate:** User confirms the token sheet before moving to Plan.

## Step 0: Identify the reference and its destination

Confirm (or assign) a reference name and confirm it has — or will get — a
directory at `~/Sites/design-references/<name>/`, per that store's `README.md`
(read it if you haven't this session — store shape, `REFERENCE.md` template).
If this is a brand-new reference, you'll write its `REFERENCE.md` once Discover
locks (Step 6).

**Two capture routes:**

- **Live URL available** — run the full analyzer trio against the live page
  (Step 1).
- **Video-only reference** (no live URL — the site is gone, gated, or the
  reference is a captured screen recording) — do not fail or fall back to
  eyeballing. Route to `~/Sites/design-references/<name>/videos/` and any
  stored screenshots already in `capture/`: derive the token sheet from
  `analyze_page` run against a locally-served HTML snapshot if one exists,
  or from direct pixel inspection of the stored screenshots/video frames.
  Motion in this route comes from watching the stored video frame-by-frame
  and recording actual measured timings (frame-counted, not guessed) into the
  same table shape Step 4 produces — `capture_motion` cannot run without a
  live page, but the discipline is identical: a number you counted, not a
  number you assumed.

## Step 1: Run the analyzer trio (live-URL route)

Before any token or motion claim, run all three page-analyzer MCP tools
against the reference. Do not pass a literal `~` in `outputDir` — Node does
no tilde expansion, so a verbatim `~/Sites/...` string mkdirs a literal
`./~` tree next to wherever the process runs instead of your home directory.
Omit `outputDir` and let the server's `OUTPUT_DIR` env default place the
output under the reference store:

```
analyze_page(
  url: "<reference URL>",
  includeScreenshots: true,
  includeAssets: true,
  breakpoints: ["mobile", "desktop"]
)

capture_motion(
  url: "<reference URL>",
  probes: ["load", "scroll", "hover", "declared"]
)

download_assets(
  url: "<reference URL>",
  types: ["all"]
)
```

The `OUTPUT_DIR` default slugs by the target URL's hostname
(`<OUTPUT_DIR>/<hostname-slug>/capture` or `/assets`), not by the reference
name you picked in Step 0 — after capture, rename or move that slugged
directory into the curated `~/Sites/design-references/<name>/` layout. If you
want the curated name written directly (skipping the rename), pass an
ABSOLUTE, already-expanded `outputDir` path instead (e.g. resolve `~` to the
real home directory yourself before writing the call) — never a literal `~`.

`analyze_page` returns its DOM structure, computed CSS, typography, spacing,
and color-palette findings in the tool RESPONSE — cite those values directly
from the response in-session, there is no analysis JSON on disk. With
`includeScreenshots: true` it writes screenshot PNGs at each breakpoint into
`outputDir`; that's the only thing it puts on disk. `capture_motion` writes
`motion.json` and `motion-spec.md` into `outputDir` — measured durations,
easings (including a fitted cubic-bezier with its max error where no named
easing matches), scroll ranges as viewport percentages, and stagger groups,
one table per trigger (page-load, scroll-triggered, hover, continuous).
`download_assets` writes assets plus `manifest.json` into its own
`outputDir`.

**Present the full capture summary before asking questions.**

## Step 2: Progressive interview

Maximum 3-4 questions per round. Never dump everything at once.

### Round 1 — Core intent

- Purpose: what is this build for?
- Audience: who visits?
- Reference: what specifically drew you to this design?
- Platform: confirmed at Plan time, but flag now if the user already knows.

### Round 2 — Layout precision (never skip)

- "Is this 2-column or 3-column? Is whitespace a deliberate empty column?"
- "Column ratio — 60/40, fixed/fluid, something else?"
- "Single image or layered/stacked images with offset?"
- "Container padding: who handles it, nav or sections?"
- "Section transitions: tight, standard, or generous?"
- "All UI text — same base size, or intentionally varied?"

### Round 3 — Edge cases (if needed)

- Mobile behavior for complex sections.
- Explicitly out-of-scope items.

**Interview complete when every token and section decision is concrete.**

## Step 3: Categorize findings

- **Measured**: came from `analyze_page` (cite the tool RESPONSE — it has no
  on-disk analysis file) or `capture_motion` (cite the on-disk file,
  `motion.json` / `motion-spec.md`).
- **Confirmed**: user explicitly stated in interview.
- **Open**: unresolved — resolve before Plan.
- **Out of scope**: explicitly excluded.

There is no "inferred" or "probable" category. If it isn't measured or
confirmed, it's open — ask, don't guess.

## Step 4: Present the token sheet

Design tokens from `analyze_page`'s captured CSS, confirmed against the
interview:

```css
COLORS
--color-bg:          #f5f0eb
--color-text:        #1a1a1a
--color-accent:      #c8a882

TYPOGRAPHY
--font-display:      'Cormorant Garamond', serif
--size-display:      72px / 80px
--weight-display:    300

SPACING
--space-section:     120px
--space-gap:         40px
```

Motion tables transcribed directly from `motion-spec.md` — **one table per
trigger, with that trigger's own column set exactly as `motion-spec.md`
renders it.** Never merge triggers into one table, and never add a column a
trigger's table doesn't have (a scroll-triggered row has no Stagger column —
if you want to note a stagger, that means you're actually looking at a
page-load row).

**Page-load** (`Selector | Delay | Properties | Duration | Easing | Stagger`):

| Selector | Delay | Properties | Duration | Easing | Stagger |
|---|---|---|---|---|---|
| `.hero h1` | 200ms | opacity: 0→1; transform: translateY(40px)→0 | 600ms | cubic-bezier(0.16,1,0.3,1) (fitted, max error 0.004) | - |

**Scroll-triggered** (`Selector | Scroll range | Properties | Duration | Easing`
— no Stagger column; scroll-triggered motion doesn't stagger by definition
in this capture, so don't invent one):

| Selector | Scroll range | Properties | Duration | Easing |
|---|---|---|---|---|
| `.card` | 12–28% | opacity: 0→1 | 400ms | ease-out |

**Hover** (`Selector | Properties | Duration | Easing`):

| Selector | Properties | Duration | Easing |
|---|---|---|---|
| `.nav a` | text-decoration-color: transparent→currentColor | 200ms | ease |

**Continuous** (`Selector | Properties | Duration | Easing | Iterations`):

| Selector | Properties | Duration | Easing | Iterations |
|---|---|---|---|---|
| `.loader-ring` | transform: rotate(0deg)→rotate(360deg) | 1200ms | linear | infinite |

A row with no measured value gets no row — leave it out rather than guess a
placeholder. If `motion-spec.md` marks a candidate `unmeasurable` or
`skipped`, carry that reason into the sheet rather than silently dropping it.

**Ask:** "Do these tokens and motion values match `motion-spec.md`? Correct
anything before we lock."

**Do not proceed until user confirms.**

## Step 5: Lock spec

Summarize confirmed decisions: all tokens verified, layout structure per
section, motion values per section (cited from `motion-spec.md`), out-of-scope
list.

**Say:** "Spec is locked. Ready to generate the build plan — shall I proceed?"

## Step 6: Write or update REFERENCE.md

If this reference is new to the store, write
`~/Sites/design-references/<name>/REFERENCE.md` per the store's template
(what it is, provenance, live URL(s), what to reuse, license/usage boundary).
If it already exists, leave it — Discover doesn't overwrite provenance notes
another session wrote.

## Pitfalls (hard-won lessons)

| Issue | What to check |
|---|---|
| Whitespace column | 2-column may be 3 with an empty third. Ask. |
| Image layering | Never assume single image. Ask if stacked, with offset. |
| Container padding | Section padding + container padding can double up. Document who handles it. |
| Section spacing | Default is often too generous. Ask per transition. |
| Motion without measurement | If `capture_motion` didn't run (video-only route), don't fill the table from memory — frame-count the video or mark the row open. |
| Mobile columns | A 3-col desktop layout may be 1 or 2 on mobile. Don't assume — `analyze_page`'s mobile breakpoint capture tells you. |
