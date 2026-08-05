# YOOtheme LESS Styling — child themes, the styler, and design tokens

The rest of this skill covers YOOtheme's **PHP/builder** integration (content
sources, resolvers, custom elements). This file covers the other half: how a
project's **visual design system** gets into YOOtheme, via a child theme's LESS
style.

Read this before: making a theme a YOOtheme child, writing a `theme.*.less`,
mapping design tokens onto UIkit, or debugging "my style doesn't show up".

---

## The model in one paragraph

YOOtheme Pro is the **parent** theme and owns rendering — it ships the page
templates and the builder. A project's theme is a **thin child** that carries the
site's own wiring and ONE LESS file: `less/theme.<slug>.less`. That file is a
"style" in YOOtheme's vocabulary, selected in Customizer → Theme → Style. It maps
the project's design tokens onto UIkit variables, so every element built in the
builder inherits the right font, colour, spacing and radius automatically.

**A child theme carries NO template files.** `header.php`, `footer.php`,
`page.php`, `single.php`, `index.php`, `404.php`, `searchform.php`, `partials/`
— all of them OVERRIDE the parent and bypass the builder. Deleting them is the
first step of converting a classic theme to a YOOtheme child.

---

## Style discovery — how YOOtheme finds a child's LESS

`packages/styler/src/Styler.php`:

```php
// getThemes() — globs BOTH the parent and the child
File::glob("{{$rootDir},{$childDir}}/less/theme.*.less")
```

So a style in the CHILD theme is found automatically. Two consequences:

1. **The filename IS the style id.** `theme.acme.less` → `id=acme`. The compiled
   artifact is `theme.<id>.css` (`StyleController.php`). Renaming the style means
   renaming the file, which changes the id everywhere and orphans saved settings.
2. **`@import` paths resolve relative to the LESS file**, so a child reaches the
   parent with `../../yootheme/…`:

```less
@import "../../yootheme/less/platform.less";
@import "../../yootheme/vendor/assets/uikit/src/less/uikit.less";
@import "../../yootheme/vendor/assets/uikit-themes/master/_import.less";
@import "../../yootheme/less/theme.less";
```

**The style NAME comes from the first comment block**, parsed by `getMeta()`:

```less
/*

Name: Acme
Background: Light
Color: Brown
Type: Flat

*/
```

`getMeta()` regex-parses `name|style|background|color|type|preview` out of the
**first** comment. Editing anything above that block risks breaking the name —
re-verify after touching the header:

```bash
ddev wp eval '$s=\YOOtheme\Application::getInstance()->get(\YOOtheme\Theme\Styler\Styler::class);
foreach($s->getThemes() as $t) printf("id=%s name=%s\n",$t["id"],$t["name"]);'
```

Absent a `Name:`, YOOtheme falls back to `namify(id)` (`ucwords`, dashes→spaces).

### ⚠ `getMeta()` reads only the first 8 KB

```php
$content = str_replace("\r", "\n", fread($handle, 8192));
```

The metadata comment must be within the **first 8192 bytes** of the file. Put the
header comment at the very top and keep it there — pushing it down past a long
licence block or an import list silently loses the style's name and facets.

### Variant blocks (`Style:`)

After the base metadata, each `Style: <id>` line opens a **variant** and the keys
under it attach to that variant (`$meta['styles'][<id>]`):

```less
/*
Name: Glowbar
Background: White
Color: Black
Type: Skeuomorphic
Preview: https://yootheme.com/api/style/glowbar/default.jpg

Style: light-brown
Name: Light Brown
Background: Light
Color: Brown
Preview: https://yootheme.com/api/style/glowbar/light-brown.jpg
*/
```

`Background` / `Color` / `Type` are comma-splittable facets used to filter the
style picker; `Preview` resolves relative to the LESS file. Glowbar ships a base
plus five variants. All six official demos ship with the **base** style selected
and **no** Customizer overrides (`config.less: []`, `config.custom_less: ""`) —
so a shipped demo is a clean read of what the LESS alone produces.

### The parent ships 49 production styles — read them

`wp-content/themes/yootheme/less/theme.*.less` contains every official style
(`balou`, `district`, `fjord`, `oakville`, `woolberry`, …), each paired with
`vendor/assets/uikit-themes/master-<style>/`. A real shipped style is four
imports and then variable overrides:

```less
@import "platform.less";
@import "../vendor/assets/uikit/src/less/uikit.less";
@import "../vendor/assets/uikit-themes/master/_import.less";
@import "../vendor/assets/uikit-themes/master-glowbar/_import.less";   // per-style layer
@import "theme.less";
```

These are the best available worked examples of the variable vocabulary — when
you need to know which variable controls something, `grep` the 49 of them for the
effect rather than guessing a name. (A child theme uses the same four imports via
`../../yootheme/…`, minus the `master-<style>` layer unless you're extending one.)

The site's selected style id is stored in `theme_mods_<active-stylesheet>` →
`config.style`. See `yootheme-site-model.md`.

---

## ⚠ YOOtheme compiles LESS in the BROWSER, not in PHP

This is the single most misleading thing about the styler. `Styler::resolveImports()`
only *gathers* file contents and strips comments — the actual compile is **less.js
in the Customizer**. There is NO PHP compile step to invoke from the CLI, and
nothing on disk to inspect until a style is selected and saved.

**To prove a style compiles**, install less locally and run it by hand:

```bash
cd <scratchpad> && npm install less@4 --no-save
cd <theme>/less && <scratchpad>/node_modules/.bin/lessc --no-color theme.acme.less out.css
```

Three traps when doing that:

| Trap | Detail |
|---|---|
| **SIGPIPE false failure** | Piping to `head` makes `lessc` exit 1 even on success. Redirect to a file and check `${PIPESTATUS[0]}`, or read the whole output. |
| **`@import url()` gets inlined** | The local CLI **fetches** `@import url(https://fonts.googleapis.com/...)` and inlines the `@font-face` rules. The browser compiler does NOT. Its absence from local output is expected, not a bug — and it's a handy way to prove a Google Fonts URL is valid and its weights exist. |
| **Harmless noise** | `WARNING: Targeting complex selectors` and `Skipped data-uri embedding` come from YOOtheme's own vendor files. Filter them out; they are not your errors. |

A clean compile is ~650 KB / ~19 k lines — most of it UIkit.

---

## Fonts — the Customizer selector, not `wp_enqueue_style`

`packages/styler/src/StyleFontLoader.php` **downloads Google Fonts and
self-hosts them** (`load($url)` → cached woff2 → generated `@font-face`). That is
GDPR-friendly, same-origin, and needs no preconnect.

Two routes reach it:

1. **Customizer → Theme → Style → Fonts** — the normal one. Keeps the choice
   editable and is what a client can use.
2. An `@import url(https://fonts.googleapis.com/...)` **inside the LESS** —
   `StyleFontLoader::parse()` regex-matches exactly that, strips it, and rewrites
   it to self-hosted `@font-face`. Pins the choice in source.

**Never `wp_enqueue_style` the same families.** That loads them twice AND from
Google's CDN instead of the server. If a project's `functions.php` has a font
enqueue, delete it and leave a comment saying why, or it gets "helpfully" re-added.

**Font-name trap (design tools):** Figma reports optical-size CUTS as if they were
families — `"Fraunces 72pt SuperSoft"`, `"Inter 18pt"`. Google serves these as
`Fraunces` and `Inter`, with the cut selected by the `opsz` axis. Using the design
tool's name verbatim in a CSS font stack silently falls back to the next font.

---

## The two-section shape of a style file

Structure every `theme.<slug>.less` in two parts. This matters more than it looks,
because the halves behave DIFFERENTLY in the Customizer.

### Section 1 — project tokens (`@prj-*`)

The design system's own values: palette, type scale, spacing, radii, shadows.
Name them with a project prefix and quote the design-tool variable next to each,
so a future session can diff against the source of truth without guessing.

### Section 2 — the mapping onto UIkit

This is the half that does the work. Setting `@global-*` and the component
variables is what makes **builder elements correct out of the box** — without it,
filling section 1 changes nothing on screen.

```less
@global-color:              @prj-text;
@global-emphasis-color:     @prj-ink;
@global-background:         @prj-bg;
@global-primary-background: @prj-primary;
@global-font-family:        @prj-font-body;
@global-font-size:          @prj-t-body;
// …then @base-*, @button-*, @card-*, @form-*, @navbar-*, @section-*, @inverse-*
```

### ⚠ The Customizer drift trap

`packages/styler/config/styler.php` exposes variables by **pattern whitelist**
(`@global-*`, `@button-*`, `@card-*`, `@inverse-*`, …). So:

- **Section 2 variables ARE editable** in the Customizer.
- **Section 1 `@prj-*` tokens are NOT** — they match no pattern.

Editing a colour in Customizer → Global → Colors overrides the MAPPED value while
the token it derived from still reads the old one. They diverge silently, **the DB
copy wins at runtime**, and the LESS file — the one that looks authoritative —
is stale.

**Decide and write down which is the source of truth.** For a design-system-driven
site, that is the LESS file: change values in section 1, use the Customizer for
fonts and per-page work. Put that statement in the file header, and note the escape
hatch — renaming a token to match an exposed pattern makes it client-editable, at
the cost of moving its source of truth into the DB, outside git.

**Where variables actually live** (verify names against the install, they are
per-component, not in one file):

```bash
grep -rn "^@button-primary-background:" vendor/assets/uikit/src/less/components/button.less
grep -rn "^@base-h1-font-size" vendor/assets/uikit/src/less/components/base.less
```

### Responsive headings — use UIkit's own mechanism

UIkit already has a desktop/mobile split. Don't hand-roll `clamp()`:

```less
@base-h1-font-size-m:  76px;        // ≥ 960px
@base-h1-font-size:    76px * 0.6;  // below (UIkit's own default is -m * 0.85)
```

### Things the master theme forces that a brand usually overrides

- `@button-text-transform: uppercase` and a small button font size
- `@base-blockquote-font-style: italic`

UIkit exposes no per-heading `letter-spacing` or `font-weight` variable, so those
are the rare rules (not variable assignments) that belong in section 2.

### Optional section 3 — emit CSS custom properties

LESS variables are compile-time only. Re-emitting them as `--prj-*` custom
properties in `:root` lets builder Custom CSS, page JS, and later section work
share one token vocabulary instead of re-typing hex values.

---

## Converting a classic theme to a YOOtheme child

Observed cost when skipped: ~3,900 deleted lines across 26 files.

1. **Delete every template file** — `header/footer/front-page/page/single/index/
   404/searchform.php`, `partials/`, and any nav walker or fallback-menu helper.
   They override the parent and bypass the builder.
2. **Add `Template: yootheme`** to the child's `style.css` header.
3. **Strip the CSS toolchain** — Tailwind, PostCSS, stylelint, `src/css/*`.
   Styling now lives in LESS. Keep the JS pipeline (Vite + Alpine) if used.
4. **Keep `style.css`** — WordPress needs it to recognise the theme at all, and
   its `Template:` line is what makes it a child. Note that both the parent's and
   the child's `style.css` are typically comment-only (YOOtheme ships its real CSS
   through the styler), so the conventional enqueues deliver ~1 KB of nothing.
   Harmless; just know it before "optimising" them away.
5. **Enqueue parent then child** stylesheet at priority 20, filemtime-versioned.

### ⚠ Activating a child does NOT rewrite the `template` option

If the theme was ever activated as a standalone BEFORE `Template: yootheme` was
added, the `template` option stays the child's own slug and the parent is never
used — templates silently resolve to `theme-compat`. **Fix:** activate the parent,
then re-activate the child. **Verify:** `get_template_directory()` must point at
the parent.

### ⚠ PHPStan must exclude the parent

The parent is ~41 MB of licensed vendor code. Without an exclude, analysis
produces 1000+ errors. Add it to `phpstan.neon`'s `excludePaths`.

### ⚠ Vite `base` depends on the WP layout

Bedrock's default `/app/themes/<slug>/dist/` is wrong on a stackedWP `/content/`
layout. Set `base` explicitly to match the real content dir.

### ⚠ The parent is gitignored

At ~41 MB and licensed, it updates in place and is not committed. `.gitignore`
typically ignores `themes/*` and re-includes only the child. **It must be
installed separately on any other host** — copy it from another project.

---

## Checklist for a new YOOtheme child style

- [ ] Child has NO template files; `Template: <parent>` in `style.css`
- [ ] `less/theme.<slug>.less` with a `Name:` in the FIRST comment block
- [ ] Four parent `@import`s via `../../<parent>/…`
- [ ] Section 1 tokens prefixed and annotated with their design-tool source
- [ ] Section 2 maps `@global-*` + components (verify names against the install)
- [ ] Source-of-truth statement in the header (LESS vs Customizer)
- [ ] Fonts picked in the Customizer selector — no `wp_enqueue_style`
- [ ] Compiles: `lessc` exit 0 (mind SIGPIPE)
- [ ] `Styler::getThemes()` reports the expected `id` and `name`
- [ ] PHPStan excludes the parent; Vite `base` matches the layout
- [ ] Style selected in Customizer and eyeballed in a browser

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Add `header.php`/`page.php` to a child | Let the parent + builder render |
| `wp_enqueue_style` a Google Font used by the style | Pick it in the Customizer font selector |
| Assume a style compiles because it's discoverable | Run `lessc` and check exit 0 |
| Fill section 1 only | Map onto `@global-*`/component vars in section 2 |
| Edit brand colours in the Customizer AND the LESS | Pick one source of truth; state it in the header |
| Use a design tool's font name verbatim | Resolve the real family (`opsz` cuts ≠ families) |
| Hand-roll `clamp()` for headings | Use `@base-hN-font-size-m` + `@base-hN-font-size` |
| Guess UIkit variable names | `grep` them in `vendor/assets/uikit/src/less/components/` |
| Rename a style for cosmetics | The filename is the id; renaming orphans saved settings |
| Analyse the parent with PHPStan | Exclude it — 41 MB of vendor code |
