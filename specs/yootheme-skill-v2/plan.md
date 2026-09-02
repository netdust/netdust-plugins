# ntdst-yootheme v2 — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `netdust-wp:ntdst-yootheme` true (the baseline module, never ACF, bind the item), mechanical where it can be (lint, measure, recompile, layout helpers), and half the size to load — plus one hook fix so `memory/` stops landing in vendor trees.

**Architecture:** Five clusters, each closed by a script that is RED on `main` today. Cluster A rewrites the references and is gated by a grep for retired claims. Cluster B adds the scripts and is gated by hermetic fixtures (a fake `elements/` dir, no WordPress). Cluster C rewrites the prose and is gated by a byte budget. Cluster D fixes the stop hook (contract lane — the file name trips the boundary floor; gated by the plugin's own test runner). Cluster E adds the eval cases and bumps versions. All prose cites the script that enforces it, never the other way round.

**Tech Stack:** Markdown skill files · PHP 8 CLI + WP-CLI `eval-file` (`yoo-lint.php`, `yoo-content.php`, `yoo-seed.php`) · Node 20 + Playwright (`yoo-measure.mjs`, `yoo-recompile.mjs`) · Python 3 (`yoo_layout.py`, hook, tests) · bash eval gates.

**Spec:** `specs/yootheme-skill-v2/spec.md`

**Loop budget: ~17 iterations** (12 tasks + 5 cluster gates; no fix rounds budgeted — every gate is a script the task runs before closing).

## Global Constraints

- Edit the MARKETPLACE SOURCE (`~/Projects/netdust-plugins`), never the plugin cache; the cache is refreshed by `/plugin` after the version bump (FR-14).
- Every skill claim about YOOtheme is read against the installed 5.0.43 parent (`~/Sites/edushare/app/content/themes/yootheme`) before it is written; the anchor line names 5.0.43 (FR-3).
- ACF appears in the skill only inside the "reading a demo package" aside (FR-2). Never as an option.
- No script writes to the DB without the existing backup + `config.save|filter` / builder-pipeline route in `yoo-content.php` / `yoo-config.php` (unchanged).
- Comments follow the house rule: short, "why" only; no banners.
- SKILL.md ≤ 7,000 bytes · lessons.md ≤ 18,000 bytes · the page-build load ≤ 55,000 bytes (SC-3, relaxed from 45,000 at T10).
- Superpowers' `docs/superpowers/plans/` location is overridden by this repo's `specs/<feature>/` convention.

---

## Stakes

**Stakes: low** — a wrong doc or a script bug in a skill repo is caught by the next session
running the script, and reverted in one commit. No money, data, access or irreversible
operation anywhere in the diff.

### Per-cluster stakes

| Cluster | Stakes | Why |
|---|---|---|
| A — the truth | **low** | markdown; the anchor script proves the retired claims are gone |
| B — the machine | **low** | new scripts; `yoo-content.php` changes are additive and every write still backs up first |
| C — the text | **low** | markdown; budget script |
| D — the hook | **standard** | the stop hook writes to a project's `memory/`; a wrong root resolution would write a real project's lessons elsewhere — caught by three new cases in the plugin's test runner, reverted in one commit |
| E — the record | **low** | eval JSON, a local asset copy, version strings |

## First working version

**Task:** T01
**Demonstrates:** a human opens `references/yootheme.md` and reads the module route — enable
by assignment, the coverage table, the derived query names — and runs the anchor script to see
the four retired-pattern claims it used to carry are gone (the remaining hits are T02/T03's).
**Verify by:** `bash plugins/netdust-wp/evals/yootheme-anchor.sh` → prints 0 hits for the
`YOOthemeDynamicContentService` / `attach_post_meta` / `{Type}SourcesService` patterns.

## Constitution check

| Rule | This plan |
|---|---|
| Skills are contracts, not books — decisions, convergence points, traps | Cluster C removes narrative; the mechanical traps move into a script and the prose points at it |
| Plugins provide capability, custom skills provide domain knowledge | the linter and measure script are capability; the workflow and lessons are the domain knowledge |
| A netdust skill restating upstream content is a defect | `yootheme.md` no longer restates the baseline module's README — it links `ntdst-framework/references/baseline.md` and adds only the builder-side facts |
| Every skill ships with evals | FR-12: six behavioural cases + three script gates |
| Simplicity — smallest change | no new plugin, no new agent, no new hook; one existing hook gains a root walk |

## Threat model

N/A — the spec answers "None of the above" on every security surface. The tooling runs as the
operator's own admin under WP-CLI (the existing `--user=<admin>` rule for page writes stays
mandatory and `yoo-content.php` still refuses without `unfiltered_html`); Playwright reads its
login from the environment and never stores it; the linter reads local files. FR-13 makes the
hook write to fewer places, not more.

## Acceptance flows

N/A — no user-facing surface is flagged. The behavioural contracts are the four cluster
gates below, each a command with an exit code, and the DDEV integration gate in Cluster B.

## Architecture invariants touched

N/A — this repo carries no `ARCHITECTURE-INVARIANTS.md`; the work touches no authorization,
data-access or entity-modelling path. The one convergence point this plan *creates* is
internal to the skill: "a layout is checked by `yoo-lint.php`, never by reading the JSON",
stated in `workflow.md` and cited by `lessons.md`.

## Spec-premise ground-truth

| Premise | Verified against | Finding |
|---|---|---|
| The baseline module replaces the per-project source | `~/Sites/edushare/app/content/mu-plugins/ntdst-baseline/services/yootheme/*` (2.3.0) + `ntdst-framework/references/baseline.md` §"The yootheme module" | Confirmed. `YOOthemeSourcesService`, `FieldTypeBridge`, `ModelSchema`, `resolvers.php`; opt-in by assignment; OFF by default; `baseline.md` names the hand-registered source as drift since 2.3.0. |
| The yootheme skill still teaches the old route | `SKILL.md` lines 102–329, `references/yootheme.md`, `templates/yootheme-source.php.md`, `ntdst-patterns/golden-paths/yootheme-integration.md` | Confirmed, four copies. `yootheme.md` also names `permalink`/`featured_image`, fields of the Rossi engine, not YOOtheme. |
| `content-binding.md` recommends ACF and the wrong repeat shape | its §1, §3 and the anti-pattern table | Confirmed: "❌ Write PHP for a CPT → ✅ ACF post type + field group"; "the container carries the list query and repeats its single child". |
| 5.0.38 → 5.0.43 changes nothing in the grammar | file-level diff of `_assets/yootheme` vs edushare's parent: 15 PHP files, `config.php` version only | Confirmed. Grammar-relevant: `button_item` modal condition reads `lightbox` (field already present at 5.0.38); `grid_item` `{@content_expand}`. 5.0.41 CVE fixes are in `FinderController` (`Path::isBasePath`) and `Helper::orderBy` (`ASC\|DESC` forced). |
| `element.php` files are plain PHP arrays a CLI can `include` | `packages/builder/elements/*/element.php` | Confirmed — `return [...]` under `namespace YOOtheme;` with no function calls needing the app, except `${builder.*}` field-set references resolved by the builder. The linter treats a `${…}` string as "shared field set" and reads `packages/builder/config/builder.php` for those props. |
| Column `width_*` is rendered but not declared in `fields` | `elements/column/element.php` vs `templates/template.php` | Confirmed (edushare lesson 2026-09-02). The linter carries a render-only allow-list per element. |
| josworld's build scripts share one constructor set | `~/Sites/josworld/specs/waarom-jos-page/build-*.py` | Confirmed: identical `text/headline/button/image/column/row/section` in 3 of 8 files, `sec()`/`at()` in 5. |
| edushare measures with `getBoundingClientRect` + computed styles | `tests/E2E/verhaal-template.spec.ts` `box()`/`style()` | Confirmed. |
| The stop hook writes to `cwd` | `hooks/session-stop.py:206,303,321`; `find ~/Sites -name .stop-hook-state.json` | Confirmed: `Path(cwd) / "memory"`; 17 stray dirs under `themes/ plugins/ mu-plugins/ vendor/ packages/`. `session-start.sh:202` reads `$CWD/memory/STATE.md` the same way. |
| The edushare parent copy is clean enough to become `_assets` | `ls` of the tree | Carries `memory/` (two stray hook dirs), `cache/`, a `.gitignore` in one package; excluded by the copy. |

## Phases & review clusters

| Cluster | Tasks | Delivers | Lane | Gate |
|---|---|---|---|---|
| **A — the truth** | T01–T03 | references that match the fleet; the version anchor | behaviour | `evals/yootheme-anchor.sh` exit 0 |
| **B — the machine** | T04–T07 | lint, content verbs, measure, recompile, layout helpers, sections, seed | behaviour | `tests/yootheme/run.sh` exit 0 + the DDEV check (SC-4) |
| **C — the text** | T08–T10 | workflow.md, lessons by task, SKILL.md router | behaviour | `evals/yootheme-budget.sh` exit 0 |
| **D — the hook** | T11 | hook root walk + tests | contract — `session-stop.py` trips the boundary floor (`session`) | `netdust-agent/tests/run.sh` |
| **E — the record** | T12 | eval cases, `_assets` refresh, versions | behaviour | `evals/yootheme-cases.sh` exit 0 |

Order: A first (a wrong claim is the costliest thing to leave standing), B before C (the prose
points at scripts that must exist), D and E last.

`[HUMAN]` yield points: none. The `_assets` refresh (T12) is a local copy the operator asked
for; it is logged in the task, not gated.

**Follow-up, not a task:** the server-side YOOtheme version per host (15 of 17 local checkouts
are below the 5.0.41 CVE floor) — a `wp-infra` / `ploi` action.

## The twenty harvested traps (T09's input — each is verified in the project memory it cites)

| # | Trap (symptom → fix) | Source |
|---|---|---|
| 1 | `_condition` on an array field kills the node everywhere → gate with the SOURCE query + a `slice` directive of limit 1; a source with only `query` and no `props` is inert | edushare lessons 2026-09-02 |
| 2 | section `style` inverts the whole subtree (white card title on white) → `preserve_color` on the section + `text_color: light` on the heading's column; assert both colours | edushare lessons |
| 3 | "behind the next section" → position the FOLLOWING section (`position: relative; z-index: 1` via `css`); `z-index: -1` hides it behind its own section | edushare lessons |
| 4 | invented keys stored silently: `padding`→`padding_top/_bottom` (`""` = default), `margin`→`margin_top`, `border`→`image_border`, `alt`→`image_alt`, binding `args`→`arguments` | edushare lessons + STATE |
| 5 | bare `row` inside a column renders but shows a broken icon in the tree → nest with `fragment` | edushare lessons |
| 6 | a test derived from the same assumption as the code cannot falsify it; `.uk-container` is content-box → assert the measured box | edushare lessons |
| 7 | list query on the `grid` = one grid per story → bind the `grid_item` | edushare lessons `f091f0a` |
| 8 | the YOOtheme config drifts between sessions → `yoo-config.php get` at entry, never trust a snapshot | edushare lessons |
| 9 | a menu item with `href="#"` is dropped, no `<li>`; WP puts menu classes on the `<li>` not the `<a>` | edushare STATE |
| 10 | a builderwidget's content is echoed raw — no `.tm-*` wrapper | edushare STATE |
| 11 | `@global-secondary-background` claims toolbar + offcanvas; `@global-muted-color` tints toolbar/offcanvas/footer nav | edushare STATE |
| 12 | Figma reports `letterSpacing`/`lineHeight` in percent; opsz cuts are not families | edushare STATE, josworld ARCHIVE |
| 13 | a lone column fills its row (`tm-grid-expand`) unless the row has `alignment`; column count must match `layout` — supply the empty column | josworld lessons + STATE |
| 14 | percent `position_top` on an absolute element in a zero-height panel computes to 0 → use px | josworld STATE |
| 15 | every section needs a `name` or it lists as bare SECTION | josworld STATE |
| 16 | an orphaned `_item` node (no matching parent) throws a TypeError → 500 on every page rendering it; restore the parent wrapper | josworld atomic memory |
| 17 | `panel_link` (needs `show_link`) runs `striptags()` over title/meta/content — flattens `<taxonomy>String` links; blank `link_text` suppresses "Read more" | josworld lessons |
| 18 | a CPT archive beats a same-slug page → the layout belongs in an `archive-<type>` template | josworld lessons |
| 19 | a library insert is a COPY — fix a section before saving it; `template get → patch → set` loses concurrent human saves → `patch` re-fetches | josworld STATE + lessons |
| 20 | an SVG coloured by an internal `<style>` class is immune to `uk-svg` recolouring → target the paths; `await img.decode()` before a fullpage capture | josworld lessons |
