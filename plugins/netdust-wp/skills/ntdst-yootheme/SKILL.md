---
name: ntdst-yootheme
description: Use when building, styling, or extending a YOOtheme Pro site — building a page or template from a Figma design, composing sections, menus, headers and footers, wiring ntdst-core content into the builder, writing a child theme's less/theme.<slug>.less style, mapping design tokens onto UIkit variables, or checking a layout before it is written. Triggers on file edits under themes/*/less/theme.*.less and .yoo-tools/, and on keywords YOOtheme, YOOtheme Pro, builder, section, block, symbol, sublayout, fragment, customizer, styler, uikit, UIkit variables, theme.<slug>.less, dynamic content, content source, archive template, single template, layout JSON, parallax, panel-slider, Figma to YOOtheme, build a page from a design, recompile style. Symptoms include "my LESS style does not show up", "the builder cannot do X", a prop that changes nothing on screen, an element that renders empty, a style that compiles but renders wrong, or needing to know whether a value is a setting, a variable, a hook, or a rule.
---

# NTDST YOOtheme — the router

Most YOOtheme work needs no PHP. **`references/workflow.md` first**, then the file for
the question; `lessons.md` is the by-task list of things that silently do something else.

| You are… | Read |
|---|---|
| Starting a page, a section or a template from a design | **`references/workflow.md`** — the loop, the Figma calls, the naming conventions |
| About to author or edit layout JSON | `lessons.md` §1–2, then `scripts/yoo-lint.php` before the write |
| Composing or editing a page (grammar, elements, props, responsive grid) | `references/yootheme-builder-json.md` + `sections/` |
| Driving pages from DATA (model → module source → bindings → template routing) | `references/yootheme-content-binding.md` |
| Getting a model's fields into the picker, or a curated query | `references/yootheme.md` |
| Asking WHERE something lives (pages, menus, header, footer, templates, a demo) | `references/yootheme-site-model.md` |
| Setting up SITE CHROME (header/mobile/top/bottom/sidebar, post & blog defaults) | `references/yootheme-customizer.md` |
| Deciding how the site LOOKS (child theme, LESS, tokens, fonts) | `references/yootheme-less.md` + `templates/theme.child.less.md` |

## Five facts that reframe everything

1. **A YOOtheme site lives in the database.** Page layouts are JSON in
   `post_content` (a trailing `<!-- {…} -->`), templates in the `yootheme` option, header /
   footer / menus / style in `theme_mods_<child-slug>.config` (read with `get_theme_mod`).
2. **One layout grammar, four homes** — page, template, `config.footer.content`, builder
   widget. `layout → section → row → column → element`; `fragment` nests a row.
3. **Site chrome is named positions** (`navbar`, `header`, `dialog`, `top`, `bottom`,
   `builder-1…6`, each with a `-mobile` twin). Mobile is a separate config, not a media
   query. Arbitrary header content is a Builder widget in a position — never `header.php`.
4. **Content types are ntdst-core models; the ntdst-baseline `yootheme` module publishes
   them to the picker.** The official demos use ACF — read them for binding idioms, never
   propose ACF, never hand-register a source (`references/yootheme.md`).
5. **Templates scale, pages don't.** "A page for each X" is one CPT + an `archive-` and a
   `single-` template. A CPT archive shadows a same-slug page.

Verified against YOOtheme **5.0.43** (2026-09-02); 5.0.38→5.0.43 changed nothing in the
grammar but `button_item`'s `lightbox` condition and `grid_item`'s `{@content_expand}`.
**5.0.41 is the floor** — it closed CVE-2026-75115 (file read) and CVE-2026-76613 (SQLi),
both reachable by a contributor account.

## Reading and writing

Reading is free (`scripts/demo-mine.py` on a dump, `wp option get`). Writing goes through
the scripts, which run the same builder / event pipeline the UI runs and back up first:

| Script | Does |
|---|---|
| `scripts/yoo-config.php` | the `config` theme_mod — get / set / unset / backup / restore (emits `config.save\|filter`) |
| `scripts/yoo-content.php` | pages, templates, builder widgets, the library — get / set / **patch** (live copy) / reorder / export; `library set` upserts a starter layout by name; fills a missing root `version`; lints before every write |
| `scripts/yoo-lint.php` | a layout against the installed parent's element definitions — 17 finding codes, the fix named; `all` walks every tree in the DB |
| `scripts/yoo-measure.mjs` | the rendered page as rects + computed styles, `--compare` against Figma geometry |
| `scripts/yoo-recompile.mjs` | the Styler's "Recompile style", headless, md5 proven before/after |
| `scripts/yoo_layout.py` · `sections/` | build layouts in Python with the builder's default props; six verified shapes to copy |
| `scripts/yoo-seed.php` | sample posts for a listing, stamped for `purge` |

Five rules: **always `wp --user=<admin-id>`** (KSES destroys a layout otherwise) ·
decode layout JSON without `assoc` (`{}` must stay `{}`) · never `set_theme_mod` on
`config` · a hand-authored layout needs a root `version` · there is no server-side LESS
compiler — `yoo-recompile.mjs` after a style change.

## Posture

**A setting, then a variable, then a hook, and only then a rule.** Text sizes are the
four roles + `h1`–`h6`; radii and shadows are variables; the FAQ divider is the default
accordion; a marquee is a `panel-slider`. Check `element.php` `fields` and
`packages/styler/config/styler.php` before concluding "YOOtheme can't".

## Styling — the five traps that cost the most

1. LESS compiles in the BROWSER — prove it with `lessc`, then recompile.
2. A child theme carries NO template files — they bypass the builder.
3. Activating a child does not rewrite the `template` option — activate parent, then child.
4. Fonts belong to the Customizer's selector (self-hosted); never `wp_enqueue_style` them.
5. The Customizer edits section 2, never section 1 tokens — decide the source of truth.

## Files

`references/` — `workflow.md` · `yootheme-builder-json.md` · `yootheme-content-binding.md`
· `yootheme.md` · `yootheme-site-model.md` · `yootheme-customizer.md` · `yootheme-less.md` ·
`templates/theme.child.less.md` · `sections/README.md` ·
`ntdst-patterns/golden-paths/yootheme-integration.md` (enable the module, bind a field).
