# The build loop — design to YOOtheme page, in order

Two sites converged on this (josworld 2026-08, edushare 2026-09). Each step names the
script that does the work; the prose is what the script cannot know.

## 0. Before the first section

- **Read the live config, never a note about it.** `yoo-config.php get` at session
  start; the Customizer rewrites the whole `config` on every human save.
- **Enable the bridge once**: `$modules['yootheme'] = true` in `<project>-core.php`
  (assignment, not union) and confirm the model's group shows in any element's Dynamic
  Content picker. `references/yootheme.md`.
- **Copy the scripts into the project**: `.yoo-tools/` (gitignored) holds
  `yoo-config.php`, `yoo-content.php`, `yoo-lint.php`, `yoo-lint-stubs.php`,
  `yoo-measure.mjs`, `yoo-recompile.mjs`, `yoo_layout.py`, `yoo-seed.php`.
  Always `wp --user=<admin-id>` for writes.
- **Singles built per post** (a CPT whose page is the builder, the model only its card
  fields): one starter layout per type in the library — `yoo-content.php library set
  single-tool.json` (root `{"type":"layout","name":"Single · Tool",…}`, header bound to
  `<plural>.single<Type>`); never bind `content` on such a page (`lessons.md` §6).

## 1. Tokens → LESS (the style)

1. **Figma variables, not screenshots.** `get_variable_defs` on the file returns the
   published colours and type styles compactly — it is the ruler, scale 1.0 by
   construction. `get_metadata` returns exact node geometry; call it on a SECTION node,
   never a page frame (a page node is ~300 KB and overflows the tool). Budget the calls:
   a View seat is rate-limited.
2. Figma traps: `letterSpacing: -2` is `-0.02em` and `lineHeight: 100` is the unitless
   `1` (percent metrics); "Fraunces 72pt SuperSoft" / "Inter 18pt" are optical-size cuts —
   the CSS family is `Fraunces` / `Inter`; a `drop-shadow` ink may not be the brand grey.
3. Prove the ruler before measuring anything: two independent knowns that must agree
   (the page gutter → the container width, and a column grid → the same width).
4. Write section 1 (`@prj-*` tokens, Figma name beside each) and section 2 (the UIkit
   mapping) of `less/theme.<slug>.less` — `templates/theme.child.less.md`. Verify every
   variable NAME exists in the install; LESS does not error on an assignment nothing reads.
5. `lessc` locally (exit 0, mind SIGPIPE), then `node .yoo-tools/yoo-recompile.mjs
   --url=… --expect-change` with a throwaway admin in `WP_USER`/`WP_PASS`. Then look at
   the page — compiled is not rendered.

## 2. Sections → the test page

6. **One private page holds every section**, grouped under `▸ CATEGORY` divider bands
   (a muted section with one headline), each section named `X1 · What it is`
   (`H` headers · `L` logos · `C` content · `W` work/CPT · `A` CTAs). The builder tree
   then reads in page order and a section can be found by name. josworld: page 64;
   edushare: page 57.
7. Build each section from `sections/` or a working section of another project —
   **copy the shape, swap content and bindings, keep every prop.** Author in Python with
   `yoo_layout.py` when the section is more than a copy.
8. Reach for a SETTING, then a VARIABLE, then a HOOK, and only then a rule. Text sizes
   are the four roles (`lead` / `large` / `small` / `meta`) and `h1`–`h6`; never a
   font-size class in content HTML.
9. `php .yoo-tools/yoo-lint.php --theme=<parent> section.json` (or let `yoo-content.php`
   lint on write). Fix every error; read every warning.
10. Write with `yoo-content.php page set <id> file.json` — never `wp post update`.
    A layout without a root `version` gets the site's version filled in.
11. **Measure, do not look**: `node .yoo-tools/yoo-measure.mjs --url=<page> --compare=<figma-nodes.json>`
    — rects and computed styles against the frame's geometry. A class being present is not
    a check: `uk-position-center` is `position:absolute` and the body floated over the
    hero while the grep said "the class is there".
12. Save the finished section to the YOOtheme Library. **A library insert is a COPY** —
    there is no back-reference — so a section is right BEFORE it is saved, and a fix
    never reaches pages already built from it.

## 3. Pages and templates — assembly

13. A page is a list of section names: `lib = y.library(".yoo-tools/page64.json")`, then
    `y.sec(lib, "H3 · Header — pagina")` per band, `y.wrap(…, version)`, lint, `page set`.
    Adjust per page in code (`y.at(node, "0/1/0")`), never by hand-editing the JSON.
14. **A CPT archive shadows a same-slug page** — an archive belongs in an
    `archive-<type>` template (`template set new tpl.json`), and its static bands still
    live on the test page. Templates are matched in stored order: the catch-all
    (`query: []`) goes last; `template list` shows the order, `reorder` fixes it.
15. Listings bind the `grid_item`; singles bind `<base>.single<Type>` at the root;
    `references/yootheme-content-binding.md`. Seed sample posts to judge a listing:
    `yoo-seed.php <type> from=items.json` (design copy, not lorem) and `purge` after.
16. `page patch` / `template patch` for a one-prop change on the LIVE copy — a
    get → edit → set cycle loses whatever a human saved in between.

## 4. Pin it

17. Every visual claim becomes an e2e assertion on COMPUTED values at the design width
    (`page.setViewportSize({width: 1440})`, `getComputedStyle`, `getBoundingClientRect`),
    never on a class name. A test derived from the same assumption as the code cannot
    falsify it — assert the measured box, not arithmetic over the same variables.
18. Export what the DB holds into the repo (`template export`, `page get`) so a
    DB-only artifact is reviewable and restorable.

## When the design is a PNG only

Derive the export's scale from two knowns before measuring (the gutter and the body
line-pitch must agree — scale varies per export, even same-day), un-blend an antialiased
1px rule per channel to recover its colour, and prefer the smaller of two candidate
tokens when a size cannot be measured. Detail in `lessons.md` → Verification.
