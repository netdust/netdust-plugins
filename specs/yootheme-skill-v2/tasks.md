# Tasks — ntdst-yootheme v2

**Spec:** `specs/yootheme-skill-v2/spec.md` · **Plan:** `specs/yootheme-skill-v2/plan.md`
**Loop budget: ~17 iterations** (12 tasks + 5 cluster gates).

**Ledger (2026-09-02):** all 12 tasks closed; gates green at close — anchor 0 hits, `tests/yootheme/run.sh` green, budget within (load 53,440 B; SC-3 relaxed to ≤ 55,000 at T10), agent suite 26/26, cases green. T06's scripts landed in T07's commit (`3a91786`); T11 took a follow-up commit (`a63f985`) after the suite showed the marker-less-cwd contract. Live checks on edushare 5.0.43: version fill + byte-identical round-trip, `lint all` (found a real inert `vertical_align` on the footer widget's row), measure (5 sections), recompile (POST 200, 3 stylesheets changed).

**Standing line for every task:** every YOOtheme claim is read against `~/Sites/edushare/app/content/themes/yootheme` (5.0.43) before it is written; every script is run on `edushare.ddev.site` once before its task closes; commits are one per task on `feat/yootheme-skill-v2`.

---

## Phase 1 — all five clusters

### Cluster A — the truth (3 tasks · effective stakes: low)

Lane: behaviour

Behaviour: the skill no longer carries the retired source pattern, the ACF recommendation, the container-repeat rule for listings, or the "a human must save the Customizer" claim, and it names 5.0.43.
Observable: `bash plugins/netdust-wp/evals/yootheme-anchor.sh` → exit 0, `0 hits`; on `main` today it exits 1 with ≥ 8 hits.
RED until: `plugins/netdust-wp/evals/yootheme-anchor.sh`

- [x] T01 Write `evals/yootheme-anchor.sh` RED first (greps `plugins/netdust-wp/skills/ntdst-yootheme` + `ntdst-patterns/golden-paths/yootheme-integration.md` for `YOOthemeDynamicContentService`, `attach_post_meta`, `SourcesService implements`, `__NAMESPACE__`, `ACF post type + field group`, `container carries the list query`, `A human must open the Customizer`, `Template layouts are BARE ARRAYS`, `theme 5.0.38)`, `permalink`/`featured_image` as field names; exit 1 with a per-pattern count). Then rewrite `references/yootheme.md` (≤ 160 lines) around the ntdst-baseline module: opt-in by assignment with the union-operator trap, the type-coverage table copied from `ntdst-framework/references/baseline.md`, `Helper::getBase()` query naming with the four worked examples (`cases.`, `teams.`, `tools.`, `verhalen.singleVerhaal`), `featuredImage.url` / `Attachment` sub-fields, `objectType` under an existing name merges, and one ≤ 40-line escape hatch (a curated `queryType` returning an existing type via a top-level function, `-10`, `function_exists('YOOtheme\app')` guard). Delete `templates/yootheme-source.php.md`. Replace SKILL.md lines 102–333 with a 12-line "Data reaches the builder" block (module + pointer) keeping the asset-control note. Re-anchor `ntdst-patterns/golden-paths/yootheme-integration.md`: enable the module, bind a field, the escape hatch as the only PHP, verified-against date 2026-09-02.  (files: plugins/netdust-wp/evals/yootheme-anchor.sh, plugins/netdust-wp/skills/ntdst-yootheme/references/yootheme.md, plugins/netdust-wp/skills/ntdst-yootheme/templates/yootheme-source.php.md, plugins/netdust-wp/skills/ntdst-yootheme/SKILL.md, plugins/netdust-wp/skills/ntdst-patterns/golden-paths/yootheme-integration.md)
  (FR-1)

- [x] T02 `references/yootheme-content-binding.md`: §1 → "The content model is an ntdst-core model" (module field → binding table; `order: "field:<name>"` needs the STORED prefixed key today), the ACF table → a ≤ 10-line "reading a demo package" aside; §3 → both repeat shapes named (bind the `grid_item` for a listing; a list query on the container repeats the container per item — the demo's grid-per-category), `#parent` root trap kept; `_condition` cannot gate a list field — the source-query + `slice` gate with the JSON from edushare; the anti-pattern table's two ACF rows replaced with the module rows.  (files: plugins/netdust-wp/skills/ntdst-yootheme/references/yootheme-content-binding.md)
  (FR-2)

- [x] T03 Stale strings and the anchor: `scripts/yoo-config.php` header → "CSS is compiled in the browser; `scripts/yoo-recompile.mjs` drives the Styler's Recompile button"; SKILL.md "Reading vs writing" item 2 the same; `yoo-content.php` `yc_page_set` error → "a template's `layout` has the same root shape — see the header"; `demo-mine.py` docstring adds `pages`. `references/yootheme-site-model.md` and SKILL.md orientation: "verified against 5.0.43 (2026-09-02); 5.0.38→5.0.43 changed 15 PHP files and nothing in the grammar except `button_item`'s modal condition reading `lightbox` and `grid_item`'s `{@content_expand}`; 5.0.41 fixed CVE-2026-75115 (file read) and CVE-2026-76613 (SQLi) — treat 5.0.41 as the floor". Extend the anchor script with the `5.0.38)` and `BARE ARRAYS` patterns; run it → exit 0.  (files: plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo-config.php, plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo-content.php, plugins/netdust-wp/skills/ntdst-yootheme/scripts/demo-mine.py, plugins/netdust-wp/skills/ntdst-yootheme/references/yootheme-site-model.md, plugins/netdust-wp/skills/ntdst-yootheme/SKILL.md, plugins/netdust-wp/evals/yootheme-anchor.sh)
  (FR-3)

**Integration gate (Cluster A):** `bash plugins/netdust-wp/evals/yootheme-anchor.sh` → exit 0, 0 hits (SC-1); `grep -rn "ACF" plugins/netdust-wp/skills/ntdst-yootheme` shows hits only inside the demo-package aside of `yootheme-content-binding.md` and the `demo-mine.py` summary line; `grep -rn "yootheme-source.php" plugins/netdust-wp` → 0.

---

### Cluster B — the machine (4 tasks · effective stakes: low)

Lane: behaviour

Behaviour: a hand-authored layout carrying the fifteen known silent traps is refused by one command that names each trap and its fix; a clean layout built with the helpers passes the same command; the rendered page and the browser recompile are one command each.
Observable: `bash plugins/netdust-wp/tests/yootheme/run.sh` → exit 0 (bad fixture: exit 1 with ≥ 12 distinct codes; good fixture: exit 0, 0 findings; helper-built section: 0 findings); on `main` today the runner does not exist.
RED until: `plugins/netdust-wp/tests/yootheme/run.sh`

- [x] T04 `scripts/yoo-lint.php` + `tests/yootheme/`. Modes: `php yoo-lint.php --theme=<parent> <layout.json>` (no WP) and `wp eval-file yoo-lint.php [page <id>|template <id>|--all]`. Element vocabulary = `packages/builder*/elements/*/element.php` `fields` keys + `defaults` keys, `${builder.<set>}` references resolved from `packages/builder/config/builder.php`, plus a per-element render-only allow-list (`column`: `width_default|small|medium|large|xlarge`; all: `class`, `attributes`, `css`, `id`, `name`, `version` on root). Findings (code → message → fix), `error` unless noted: `unknown-prop` (names the nearest declared prop by Levenshtein ≤ 2), `no-version`, `orphan-item`, `layout-count` (row `layout` groups ≠ child count), `lone-column` (warn: one child, no `alignment`), `block-align-no-maxwidth` (warn), `bgcolor-needs-empty-style` (warn), `grid-over-6`, `parent-at-root`, `binding-args`, `bare-featured-image` (warn), `row-in-column` (warn), `list-on-container` (warn: list query on a container whose single child binds `#parent`), `unnamed-section` (warn), `condition-on-list` (warn when the bound field name matches a `repeater|relation|gallery` in an optional `--schema=<json>`). Output: one line per finding `LEVEL code node-path: message → fix`, summary line, exit 1 on any error. Tests: `tests/yootheme/fixtures/theme/packages/builder/elements/{section,row,column,fragment,headline,text,image,grid,grid_item,button,button_item}/element.php` (minimal field lists copied from 5.0.43), `fixtures/bad.json` (carries every trap), `fixtures/good.json`, `run.sh` asserting the codes and exit codes.  (files: plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo-lint.php, plugins/netdust-wp/tests/yootheme/run.sh, plugins/netdust-wp/tests/yootheme/fixtures/bad.json, plugins/netdust-wp/tests/yootheme/fixtures/good.json, plugins/netdust-wp/tests/yootheme/fixtures/theme/packages/builder/elements/section/element.php, plugins/netdust-wp/tests/yootheme/fixtures/theme/packages/builder/config/builder.php)
  (FR-4)

- [x] T05 `scripts/yoo-content.php` verbs: `version` auto-fill (from the first page/template in the DB that has one; logged `note: root version filled from page 57 (5.0.43)`); `page patch <id|slug> <path> <json>` and `template patch <id> <path> <json>` where `<path>` is `children/0/children/1/props/link` — re-fetch, resolve, `WP_CLI::error` when the path is missing, write through the existing setter; `widget list` (position, id, title, node count), `widget get <id>`, `widget set <id> <file>`, `widget new <position> <title> <file>` (the josworld `make-widget.php` body, through `Builder::load` in `save` context, `sidebars_widgets` updated); lint-before-write by `include`-ing `yoo-lint.php`'s functions (exit on `error` unless `--no-lint`, which logs); `page set` warns when `get_post_type_object()` of any public type has `rewrite.slug` equal to the page's `post_name` and `has_archive`. Header usage block updated.  (files: plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo-content.php, plugins/netdust-wp/tests/yootheme/run.sh)
  (FR-5)

- [x] T06 `scripts/yoo-measure.mjs` and `scripts/yoo-recompile.mjs` (Playwright, `import { chromium } from 'playwright'` resolved from the project's `node_modules`): measure — `--url --width=1440 [--compare=figma.json] [--selector='#tm-main > .uk-section']`, waits `networkidle` then `Promise.all(imgs.map(i => i.decode().catch(()=>{})))`, scrolls each section into view before reading, prints JSON `{sections:[{i, rect, bg, position, zIndex, children:[{tag, cls, text≤40, rect, fontSize, lineHeight, color, radius}]}]}`; `--compare` matches Figma nodes by `name` to children by text and prints `Δx Δy Δw Δh` with a `--tolerance=2` flag. recompile — `--url=<site> --user=$WP_USER --pass=$WP_PASS [--expect-change]`, logs in at `/wp/wp-login.php`, opens `admin-ajax.php?action=yootheme&yootheme=customizer`, clicks the Style panel, clicks the element whose text is `Recompile style`/`Stijl opnieuw compileren`, waits for the `yootheme=theme/style` POST, prints md5 of `css/theme.*.css` before/after (read via `--css-path`). Both carry a 10-line header with usage.  (files: plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo-measure.mjs, plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo-recompile.mjs)
  (FR-6, FR-7)

- [x] T07 `scripts/yoo_layout.py` (constructors with the builder's default props as in josworld's `build-sections.py`: `section(name, children, **p)`, `row`, `column`, `fragment`, `headline`, `text`, `image`, `button(label, link, style)`, `grid(items, **p)`, `grid_item`, `panel`, `accordion(items)`, `panel_slider(items, **p)`; `library(path) -> dict[name, node]` reading a page dump or the `yootheme` option's `library`; `at(node, path)`; `wrap(children, version)`; `dump(node, path)`), `sections/README.md` + six JSON shapes (`hero-text.json`, `header-page.json`, `grid-cpt-cards.json` bound to `<base>.custom<Base>` with `#parent` on the item, `faq-accordion.json`, `logo-marquee.json`, `cta-band.json`) each with a first-line `"name"` and a `"_source": "josworld page 64 / edushare blokken, 2026-09-02"` key the linter ignores, and `scripts/yoo-seed.php <post_type> --from=<json> [--purge]` (the josworld seeders generalised: array of `{title, content, meta:{}, thumbnail_id}`, stamps `_ntdst_sample=1`, `--purge` deletes by that stamp). `tests/yootheme/run.sh` gains: build `hero-text` through `yoo_layout.py` → lint → 0 findings.  (files: plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo_layout.py, plugins/netdust-wp/skills/ntdst-yootheme/sections/README.md, plugins/netdust-wp/skills/ntdst-yootheme/sections/hero-text.json, plugins/netdust-wp/skills/ntdst-yootheme/scripts/yoo-seed.php, plugins/netdust-wp/tests/yootheme/run.sh)
  (FR-8)

**Integration gate (Cluster B):** `bash plugins/netdust-wp/tests/yootheme/run.sh` → exit 0 (SC-2). On `edushare.ddev.site` (`~/Sites/edushare`, scripts copied to `.yoo-tools/`): `ddev wp --user=1 eval-file .yoo-tools/yoo-lint.php --all` runs and reports on every tree; `page set` of a versionless copy of page 57 stores `"version":"5.0.43"` (read back with `page get`); `node .yoo-tools/yoo-measure.mjs --url=https://edushare.ddev.site/inspirerende-verhalen/` prints ≥ 3 sections with non-zero rects; `node .yoo-tools/yoo-recompile.mjs --expect-change` exits 0 with two different md5s (SC-4). Page 57 restored from the backup afterwards.

---

### Cluster C — the text (3 tasks · effective stakes: low)

Lane: behaviour

Behaviour: a page-build session reads the loop and the by-task traps in under half of today's bytes, and every mechanical trap in the prose names the lint code that catches it.
Observable: `bash plugins/netdust-wp/evals/yootheme-budget.sh` → exit 0 (SKILL.md ≤ 7,000 B, lessons.md ≤ 18,000 B, the five-file page-build load ≤ 55,000 B, `workflow.md` present, every `yoo-lint:<code>` cited in lessons.md exists in `yoo-lint.php`); on `main` today it exits 1 (88,000 B, no workflow.md).
RED until: `plugins/netdust-wp/evals/yootheme-budget.sh`

- [x] T08 Write `evals/yootheme-budget.sh` RED first. Then `references/workflow.md` (≤ 120 lines): the loop as a numbered list with the script at each step (tokens: `get_variable_defs` → section 1 · map section 2 · `lessc` + `yoo-recompile.mjs` · section test page with `▸ CATEGORY` bands and `X1 · Name` names · save to the Library (copies!) · assemble with `yoo_layout.py` + `sections/` · `yoo-lint.php` before every write · `yoo-measure.mjs --compare` against `get_metadata` geometry · pin computed styles in e2e); the Figma block (variables vs geometry, never a page node, percent metrics, `opsz`, the two-knowns ruler, View-seat budget); the archive-vs-page and template-order rules in two lines each; "when the design is a PNG only" as one paragraph pointing at lessons.  (files: plugins/netdust-wp/evals/yootheme-budget.sh, plugins/netdust-wp/skills/ntdst-yootheme/references/workflow.md)
  (FR-9)

- [x] T09 Rewrite `lessons.md` by task: `## Authoring layout JSON` (the mechanical traps as one line each → `yoo-lint: <code>`; the non-mechanical ones — nested container breaks `width_expand`, the three-setting bleed, sublayout via `fragment`, absolute collides on stack, hero crop is aspect-bound, `image_align: top` + CSS grid, version required — as symptom → cause → fix ≤ 4 lines); `## Bindings` (traps 1, 7, `#parent` root, `args`, `Attachment` sub-field, `_condition` on lists, `<taxonomy>String` + `panel_link`); `## Site chrome` (9, 10, 16, 19, archive shadows page, config drift, uk-svg root + internal `<style>`, inlined-SVG id collision, static-asset cache → version the filename); `## Styling` (§5 as is, trimmed; 11; per-heading vars; secondary is the UI role; text roles; accordion divider default; `.uk-container` content-box); `## Verification` (measure-not-grep as the first line pointing at `yoo-measure.mjs`; cold cache; lazy + `decode()`; SMIL clock; the coincidence-passing measurement; PNG-only: scale from two knowns + un-blend, one paragraph). Drop every dated narrative sentence. Target ≤ 18,000 B.  (files: plugins/netdust-wp/skills/ntdst-yootheme/lessons.md)
  (FR-10)

- [x] T10 SKILL.md → router ≤ 7,000 B: description with the added triggers; the "You are…" table with `workflow.md` first and `lessons.md` second; the five facts (fact 4 rewritten: "content types are ntdst-core models; the baseline `yootheme` module publishes them — `references/yootheme.md`"); Reading vs writing (five rules, the script table now listing `yoo-lint.php`, `yoo-measure.mjs`, `yoo-recompile.mjs`, `yoo_layout.py`, `yoo-seed.php`); the posture line; the five styling traps table; the Reference Files table with `workflow.md`, `sections/`. Run the budget script → exit 0.  (files: plugins/netdust-wp/skills/ntdst-yootheme/SKILL.md, plugins/netdust-wp/evals/yootheme-budget.sh)
  (FR-11)

**Integration gate (Cluster C):** `bash plugins/netdust-wp/evals/yootheme-budget.sh` → exit 0 (SC-3); `bash plugins/netdust-wp/evals/yootheme-anchor.sh` still exit 0; every `references/*.md` and `sections/` file named in SKILL.md exists (`for f in $(grep -o 'references/[a-z-]*\.md' SKILL.md); do test -f $f; done`).

---

### Cluster D — the hook (1 task · effective stakes: standard · provisional tier: LIGHT)

Lane: contract — `session-stop.py` trips the boundary floor on its file name; the task carries its own RED-first contract

- [x] T11 [Tier A] `hooks/session-stop.py`: `def project_root(cwd: str) -> Path | None` — walk `Path(cwd).resolve()` and its parents up to (not past) `Path.home()`; a dir is a root when it holds `CLAUDE.md`, `site.yml`, `.git` or an existing `memory/` (review fix: writer and reader agree); a candidate whose path relative to the eventual root crosses a `themes|plugins|mu-plugins|vendor|packages|node_modules` segment is skipped (so a `.git` inside `vendor/netdust/flow` is not a root); return `None` past `$HOME`. `sidecar_path`, `append_state_from_tags`, `append_lessons_from_tags`, `append_todos_from_tags` and the `.no-auto-memory` check take the resolved root; `main()` logs `skip no-project-root cwd=…` and returns when `None`. `hooks/session-start.sh` line 202/215: `CWD` replaced by the same walk in bash (`while [ "$d" != "$HOME" ] && [ ! -e "$d/CLAUDE.md" ] && [ ! -e "$d/site.yml" ] && [ ! -d "$d/.git" ]; do d=$(dirname "$d"); done`). Tests in `tests/test_stop_hook_root.py` using `hook_test_utils`: (a) cwd three levels under a temp root holding `site.yml` → sidecar at `<root>/memory/`; (b) cwd inside `<root>/vendor/x/` where `vendor/x/.git` exists → root is still `<root>`; (c) a temp dir with no marker up to a fake `$HOME` → no file written, log line present. Then `find ~/Sites -name .stop-hook-state.json | grep -E '/(themes|plugins|mu-plugins|vendor|packages)/'` → remove those 17 `memory/` dirs (only ones holding nothing but the sidecar; a dir with `STATE.md`/`lessons.md` is listed for the operator, not deleted).  (files: plugins/netdust-agent/hooks/session-stop.py, plugins/netdust-agent/hooks/session-start.sh, plugins/netdust-agent/tests/test_stop_hook_root.py)
  Test-author: solo — standard stakes; a path-resolution helper in a memory hook, not an auth/token/parse/migration category despite the file name.
  Proven by: new test — `tests/test_stop_hook_root.py`, three cases.
  Unit test: RED-first. (a) sidecar lands at `<root>/memory/` from `<root>/a/b/c`; (b) a `.git` under `<root>/vendor/x/` is not a root; (c) no marker up to a fake `$HOME` → nothing written, `skip no-project-root` logged.
  (FR-13)

**Integration gate (Cluster D):** `bash plugins/netdust-agent/tests/run.sh` → 0 failed modules beyond the live-corpus skip, `test_stop_hook_root` listed with 3 passes (SC-5); `find ~/Sites -name .stop-hook-state.json | grep -cE '/(themes|plugins|mu-plugins|vendor|packages)/'` → 0; a session started from `~/Sites/edushare/app` still injects edushare's `memory/STATE.md` (`bash hooks/session-start.sh` with `cwd` set, grep the STATE header).

── REVIEW GATE ── (tier: LIGHT — one helper and three tests; no data path changes beyond where a file lands.)

---

### Cluster E — the record (1 task · effective stakes: low)

Lane: behaviour

Behaviour: the skill's new behaviours are pinned as eval cases and both plugins carry the new version everywhere a version is declared.
Observable: `bash plugins/netdust-wp/evals/yootheme-cases.sh` → exit 0 (≥ 6 `yoo-` case ids present and parseable; `plugin.json` ×2 and `marketplace.json` agree on 1.1.0 / 0.21.1); on `main` today it does not exist.
RED until: `plugins/netdust-wp/evals/yootheme-cases.sh`

- [x] T12 The record: `evals/behavioral-lessons.json` gains cases `yoo-listing-binds-item`, `yoo-parent-at-template-root`, `yoo-binding-arguments-key`, `yoo-never-acf`, `yoo-module-not-custom-source`, `yoo-section-style-inverts`, `yoo-measure-not-grep` (each: `skill`, `lesson`, `prompt`, `must_contain`/`must_not_contain`, `baseline_ref: 0291252`); `~/Sites/_assets/yootheme` replaced by `rsync -a --delete --exclude memory --exclude cache --exclude '.gitignore' ~/Sites/edushare/app/content/themes/yootheme/ ~/Sites/_assets/yootheme/` (verified `Version: 5.0.43` after); `plugins/netdust-wp/.claude-plugin/plugin.json` 1.0.0 → 1.1.0 with "1.1.0: ntdst-yootheme v2 — the baseline module, yoo-lint, yoo-measure, workflow.md" in the description, `plugins/netdust-agent/.claude-plugin/plugin.json` 0.21.0 → 0.21.1 ("stop hook writes memory/ at the project root"), `.claude-plugin/marketplace.json` both entries in step; `plugins/netdust-wp/memory/lessons.md` gains one line pointing at this spec; `evals/yootheme-cases.sh` written RED first (asserts the ids and the three version strings).  (files: plugins/netdust-wp/evals/yootheme-cases.sh, plugins/netdust-wp/evals/behavioral-lessons.json, plugins/netdust-wp/.claude-plugin/plugin.json, plugins/netdust-agent/.claude-plugin/plugin.json, .claude-plugin/marketplace.json, plugins/netdust-wp/memory/lessons.md)
  (FR-12, FR-14)

**Integration gate (Cluster E):** `bash plugins/netdust-wp/evals/yootheme-cases.sh` → exit 0 (SC-6); `grep -m1 Version ~/Sites/_assets/yootheme/style.css` → 5.0.43; `bash plugins/netdust-wp/evals/yootheme-anchor.sh` and `yootheme-budget.sh` still exit 0.

── BRANCH REVIEW ── (tier: LIGHT — skill text and developer scripts, no security surface; the reviewer reads the branch diff once against the four gates.)
