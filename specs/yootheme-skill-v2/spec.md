# Spec — ntdst-yootheme v2: teach the module, lint the JSON, measure the render

**Repo:** `netdust-plugins` (marketplace source — never the cache) · **Plugins:** `netdust-wp` (the skill) + `netdust-agent` (one hook fix)
**Provenance:** Stefan's 2026-09-02 intake — "look at the skills and scripts, look at all the
templates that were used to build these skills, look at lessons learned already building
josworld, and now edushare. maybe you find gaps or even ways to improve, so agents get smarter
in this and faster, use less tokens" — then "in edushare the latest version of yootheme is
installed, here you also see something that could be interesting?", then "do all the work you
deem necessary to improve". The review that preceded this spec is the session's two reports;
every FR below is one of its findings.

## Problem / why

The skill works — two sites were built with it — but it is now a year of accretion read
end-to-end by every session:

1. **It teaches a route the fleet retired.** `references/yootheme.md`, the source template,
   SKILL.md's PHP section and the golden path all teach a theme-level
   `YOOthemeDynamicContentService` + per-project `{Type}SourcesService`. Since
   ntdst-baseline 2.3.0 the bridge is an opt-in module; `ntdst-framework/references/baseline.md`
   calls the hand-registered source "drift since 2.3.0". Four copies of one retired pattern.
2. **It still says ACF.** `content-binding.md` §1 and its anti-pattern table present ACF as the
   content model. The fleet rule (never ACF) reached SKILL.md fact 4 and never the reference an
   agent opens to write a binding. The same file's repeat pattern ("the container carries the
   list query") shipped four one-card grids on edushare.
3. **The loop is not written down.** Figma → LESS → recompile → section test page → library →
   assemble → measure → pin. josworld converged on it; edushare re-derived it by reading
   josworld's memory. Edushare's lesson: "the skill documents the JSON grammar but never this
   loop."
4. **Twenty verified traps live only in project memory** (`_condition` on arrays, section
   `style` inversion, `args` vs `arguments`, lone-column fill, orphan `_item` 500, …). The
   edushare harvest was blocked on 2026-09-02 by an orphaned marketplace worktree.
5. **The shape costs tokens.** A page-build session loads ~88 KB (≈28k tokens) of skill text
   before work, and `lessons.md`'s own §7 admits the section that would have saved the session
   is at the bottom. Most traps are mechanical (a prop the element does not declare, a sibling
   prop missing, a structural rule) and belong in a script.
6. **Per-project tooling grew outside the skill:** josworld's eight `build-*.py` (1,293 lines
   re-declaring the same node constructors), `make-widget.php`, four seed scripts; edushare's
   e2e measurement helpers; both projects driving "Recompile style" by hand through the
   browser.
7. **The stop hook writes `memory/` into cwd.** Seventeen stray dirs sit inside theme, plugin
   and vendor trees, two inside edushare's licensed YOOtheme parent.
8. **The version anchor is 5.0.38; the fleet's canonical copy is 5.0.38; 5.0.41 closed two
   contributor-level CVEs.** Both sites run 5.0.43; the diff to the skill's claims is nil.

## User stories, prioritized

### P1 — What the skill says is true
As an agent on a YOOtheme project, the references teach the baseline module, ntdst-core
models and the bindings that actually render; nothing in the skill contradicts the framework
skill or the fleet rule.

### P2 — The machine catches the silent traps
As an agent hand-authoring layout JSON, one command tells me which props are inventions,
which structure will fall back or 500, and which binding is mis-scoped — before the write.
As an agent verifying a page, one command gives me the rendered geometry and computed styles
to diff against the design.

### P3 — The loop is one file
As a session starting a section, `workflow.md` tells me the order of work, the Figma calls
that return exact values, and the naming conventions the other projects use.

### P4 — Less to read
As any session, SKILL.md is a router and lessons.md is a by-task index of symptom → fix;
the page-build load is half of today's.

### P5 — The hook stays in the project root
As the human partner, no `memory/` appears inside a vendor tree because a session `cd`'d.

## Functional requirements

### The truth (kills problems 1, 2, 8)
- **FR-1:** `references/yootheme.md` is rewritten around the ntdst-baseline `yootheme` module:
  opt-in by assignment, the type-coverage table (int/float/bool/string family, `repeater` →
  `listOf` row type, `relation` → `listOf` of the related type published-only,
  `image`/`file`/`gallery` → YOOtheme `Attachment` with `thumbnail`/`medium`/`large`, `array`/
  `json` dropped), the derived query names (`Helper::getBase()` rule, `single<Type>`,
  `custom<Base>`), the `Attachment` sub-field rule, and a ≤40-line custom-`queryType` escape
  hatch for a curated list. `templates/yootheme-source.php.md` is deleted; SKILL.md's "Essential
  Principles (PHP extension)" through "Asset Control" collapses to a pointer plus the asset-control
  note; `ntdst-patterns/golden-paths/yootheme-integration.md` is re-anchored on the module
  (enable + bind) with the escape hatch as its only PHP. Source: "look at the skills and
  scripts… find gaps" (Stefan, 2026-09-02) + `baseline.md` "drift since 2.3.0".
- **FR-2:** `references/yootheme-content-binding.md` §1 becomes "The content model is an
  ntdst-core model" with the module's field → binding table; the ACF table shrinks to a
  ≤10-line "reading a demo package" aside; the repeat pattern states the listing rule (bind the
  `grid_item`; a list query on the container repeats a grid per item) with both shapes named;
  the anti-pattern rows that recommend ACF are replaced. Source: `never-acf-always-ntdst-core`
  (Stefan, 2026-08-27) + edushare `f091f0a`.
- **FR-3:** Stale strings go: `yoo-config.php`'s header and SKILL.md "Reading vs writing" item
  2 say the recompile is scriptable (`yoo-recompile.mjs`), `yoo-content.php page set`'s error no
  longer says templates are bare arrays, `demo-mine.py`'s docstring lists `pages`. The skill's
  version anchor reads 5.0.43 with one line on what 5.0.38→5.0.43 changed for the grammar
  (`button_item` `lightbox`, `grid_item` `{@content_expand}`) and one line naming the 5.0.41
  CVEs as the floor. Source: "in edushare the latest version of yootheme is installed" (Stefan,
  2026-09-02); the diff was read in-session.

### The machine (kills problem 5's mechanical half, problem 6)
- **FR-4:** `scripts/yoo-lint.php` reads a layout (file, `page <id>`, `template <id>`, or
  `--all` over every tree in the DB: pages, templates, `footer.content`, `menu.items[*].content`,
  builder widgets, library) against the installed parent's `packages/builder*/elements/*/element.php`
  + the render-only props (`width_*` on column, `class`, `attributes`, `css`, `id`, `name`,
  `version`) and reports, with the fix named: unknown prop (`error`), missing root `version`,
  orphan `_item` (parent type ≠ name minus `_item`), row `layout` column count ≠ children,
  single column in a row without `alignment`, `block_align` without `maxwidth`, section
  `background_color` without `style: ""`, `grid_*` above 6, `#parent` at a template root,
  binding `args`, bare `featuredImage` binding, bare `row` under a column, list query on a
  container whose only child is its `_item`, section without `name`, `_condition` on a field
  whose type is a list. Exit 1 on any `error`. Runs as `php yoo-lint.php --theme=<parent> <file>`
  (no WordPress) and as `wp eval-file yoo-lint.php …` (DB modes). Source: invented — approved
  2026-09-02 ("agents get smarter… faster, use less tokens"; twelve lessons collapse into it).
- **FR-5:** `scripts/yoo-content.php` gains: root `version` auto-filled from an existing layout
  when absent (logged, never silent); `page patch <id> <json-path> <json>` and
  `template patch <id> …` that re-fetch the live copy immediately before writing and fail with
  exit 1 when the path resolves to nothing; `widget list|get <id>|set <id> <file>|new <position>
  <title> <file>`; a lint pass before every write (`--no-lint` to bypass, logged); a warning when
  `page set` targets a slug a CPT archive shadows. Source: josworld lessons 2026-08-06 (lost
  concurrent save; ons-werk archive) + `make-widget.php`; invented — approved 2026-09-02.
- **FR-6:** `scripts/yoo-measure.mjs` (Playwright): opens a URL at a given width (default 1440),
  waits for every image's `decode()`, and prints JSON for each `#tm-main > .uk-section` — index,
  rect, background-color, computed `position`/`z-index` — and, inside it, every heading, `.el-item`,
  `.uk-label`, `img` with rect + font-size/line-height/color/border-radius. `--compare <figma.json>`
  diffs against a node list of `{name, x, y, width, height}` and prints deltas. Source: edushare
  lesson 2026-09-02 ("verified by MEASURING the rendered page"), the `box()`/`style()` helpers
  in `tests/E2E/verhaal-template.spec.ts`.
- **FR-7:** `scripts/yoo-recompile.mjs` (Playwright): logs in with `WP_USER`/`WP_PASS`, opens
  `Url::route("customizer")`, clicks Style → "Recompile style", waits for the style POST, and
  prints the compiled CSS's md5 before/after. Exit 1 when the md5 is unchanged and `--expect-change`
  was passed. Source: lessons §6 as it stands + both projects re-driving it through `use_browser`.
- **FR-8:** `scripts/yoo_layout.py`: node constructors (`section`, `row`, `column`, `fragment`,
  `headline`, `text`, `image`, `button`, `grid`, `grid_item`, `panel`, `accordion`, `panel_slider`)
  carrying the props the builder writes by default, `library(path)` → `{name: section}` from a
  page/library dump, `at(node, path)`, `wrap(children, version)`. Plus `sections/` — six verified
  shapes stripped of project content, each with the source project and date in a header line:
  text hero, page header (eyebrow + h1 + intro), CPT card grid bound to a list query, FAQ
  accordion, logo marquee (`panel-slider` + `slider_parallax`), CTA band. Plus
  `scripts/yoo-seed.php <post_type> --from=<json> [--purge]` stamping `_ntdst_sample = 1`.
  Source: josworld `specs/waarom-jos-page/build-*.py` (1,293 lines); invented — approved
  2026-09-02.

### The text (kills problems 3, 4, 5)
- **FR-9:** `references/workflow.md` (≤ 120 lines): the loop in order — tokens → LESS →
  recompile → section test page → library → assemble → measure → pin in e2e; the Figma calls
  and their traps (`get_variable_defs` for tokens, `get_metadata` for geometry, never a page node,
  percent `letterSpacing`/`lineHeight`, `opsz` cuts, the two-knowns ruler check, the View-seat
  budget); the conventions (`▸ CATEGORY` divider bands, `X1 · Name` section names, library
  items are copies, every section named); which script runs at which step. Source: edushare
  lesson "It needs a section on measure-and-compare" + josworld STATE conventions.
- **FR-10:** `lessons.md` is restructured by task — authoring JSON · bindings · site chrome ·
  styling/LESS · verification — every entry symptom → cause → fix in ≤ 4 lines, no session
  narrative; the mechanical entries become one line pointing at the lint code that catches
  them; the twenty project-memory traps listed in the plan are harvested; the screenshot-scale
  material shrinks to one line under "PNG-only reference". Source: "use less tokens" (Stefan) +
  lessons §7's own last bullet.
- **FR-11:** SKILL.md is a router ≤ 7 KB: the "You are…" table (workflow.md first), the five
  facts, the write rules, the script table, the posture line, the styling traps table; the PHP
  content moves per FR-1. The description gains the triggers "build a page from a design",
  "Figma to YOOtheme", "archive template", "section", "block". Source: "use less tokens".

### The record and the hook (kills problems 7, 8)
- **FR-12:** `plugins/netdust-wp/evals/behavioral-lessons.json` gains ≥ 6 cases: grid_item
  listing binding, `#parent` at a template root, `args`→`arguments`, ACF never proposed, the
  module instead of a custom source, section-style inversion, measure-not-grep. `evals/yootheme-
  anchor.sh` greps the skill for the retired claims (FR-1/2/3) and exits 1 on any hit;
  `tests/yootheme/run.sh` runs the lint fixtures and the `yoo_layout.py` round-trip. Source:
  global rule §8 "a lesson that changes a skill's behaviour ships with an eval case".
- **FR-13:** `netdust-agent/hooks/session-stop.py` resolves the memory root by walking up
  from the hook's `cwd` to the nearest dir holding `CLAUDE.md`, `site.yml` or `.git`, stopping
  at `$HOME`; when the walk crosses a `themes/`, `plugins/`, `mu-plugins/`, `vendor/`,
  `packages/` or `node_modules/` segment it keeps walking; when nothing is found it writes
  nowhere and logs. `session-start.sh` reads `memory/` from the same resolution. The seventeen
  stray dirs under `~/Sites` are removed. Source: invented — approved 2026-09-02 (found while
  reading edushare's parent theme).
- **FR-14:** `~/Sites/_assets/yootheme` is refreshed to 5.0.43 from edushare's copy (excluding
  `memory/`, `cache/`, `.gitignore`); `netdust-wp` bumps 1.0.0 → 1.1.0 and `netdust-agent`
  0.21.0 → 0.21.1 with the marketplace manifest in step. Source: invented — approved 2026-09-02.

## Success criteria

- **SC-1:** `bash plugins/netdust-wp/evals/yootheme-anchor.sh` exits 0 with 0 hits across the
  skill and the golden path (it exits 1 with ≥ 8 hits on `main` today).
- **SC-2:** `bash plugins/netdust-wp/tests/yootheme/run.sh` passes: the bad fixture yields ≥ 12
  distinct finding codes and exit 1, the good fixture yields 0 findings and exit 0, and a
  `yoo_layout.py`-built section round-trips through lint with 0 findings.
- **SC-3:** SKILL.md ≤ 7,000 bytes; lessons.md ≤ 18,000 bytes; SKILL.md + workflow.md +
  lessons.md + yootheme-builder-json.md + yootheme-content-binding.md ≤ 55,000 bytes (88,000
  today; relaxed from 45,000 at T10 — the two references keep their prop tables, which are
  the lookup an agent needs) — checked by `evals/yootheme-budget.sh`.
- **SC-4:** 3 checks pass on `edushare.ddev.site`: `yoo-content.php page set` of a layout
  without `version` stores the root version; `yoo-measure.mjs` on `/inspirerende-verhalen/` prints ≥ 3 sections
  with non-zero rects; `yoo-recompile.mjs` changes the md5 of `css/theme.*.css` in 1 run.
- **SC-5:** `bash plugins/netdust-agent/tests/run.sh` passes with ≥ 3 new cases proving the
  sidecar lands at the project root from a 3-deep subdirectory, is not written under `vendor/`,
  and is skipped with a log line when no root exists.
- **SC-6:** `behavioral-lessons.json` carries ≥ 6 new `ntdst-yootheme` cases and the eval runner
  parses them (`python3 -c 'import json…'` exit 0); `find ~/Sites -name .stop-hook-state.json`
  returns 0 paths under `themes/|plugins/|mu-plugins/|vendor/|packages/`.

## Security-relevant surfaces

- [ ] User-controlled URLs / server-side outbound requests
- [ ] Auth / session / token / capability surfaces
- [ ] Untrusted parsing (frontmatter, payloads, uploads, AI tool-call args)
- [ ] BYOK / stored credentials
- [ ] Multi-tenancy / cross-actor visibility
- [x] None of the above

Everything here is developer tooling run by the operator under their own WP-CLI admin user
(the existing `--user=<admin>` rule) or Playwright against a local DDEV site with credentials
from the environment; the linter reads local files. The hook fix narrows where a file may be
written, it opens no new path.

## User-facing surfaces

- [ ] A new or changed public page / view / listing
- [ ] A new or changed admin screen or editing surface
- [ ] An endpoint a client or agent will drive
- [x] None of the above

Skill text and CLI scripts; their contract lives in the anchor/budget/lint gates and the
DDEV integration gate.

## Clarifications

- Q: Retire or re-anchor the golden path? → A: re-anchor on the module; the only PHP left in
  it is the escape hatch (a curated `queryType`). A second copy of FR-1 is the drift FR-1 removes.
- Q: Lint in PHP or Python? → A: PHP — `element.php` files are PHP arrays; `include` reads them
  natively and the same file runs under `wp eval-file` for the DB modes. Layout helpers stay
  Python, matching josworld's builders and `demo-mine.py`.
- Q: The fleet's server-side parent versions? → Out of scope here; it is a `wp-infra`/`ploi`
  action and is recorded in the plan as a follow-up, not a task.
