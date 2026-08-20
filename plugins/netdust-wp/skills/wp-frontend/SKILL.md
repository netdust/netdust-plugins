---
name: wp-frontend
description: >
  Use when working on the theme layer of a Netdust WordPress project — templates,
  the asset pipeline (Vite / wp-scripts / npm), enqueueing, theme.json, block or
  pattern work, Tailwind or Alpine in a theme. Triggers on file edits under
  themes/, on theme.json, block.json, vite.config.*, or a theme's package.json,
  and on the keywords enqueue, wp_enqueue_script, manifest, hot reload, child theme.
---

# WP frontend

**Read `site.yml` first.** `structure.theme_flavour` says what you are in:
`yootheme` · `custom` · `tbd`. There is no default theme base to assume — the fleet
is not uniform, and guessing one is how a skill starts lying. If the field says
`tbd`, look at `themes/` before writing anything.

- **`yootheme`** — YOOtheme Pro parent, child theme for overrides. The builder owns
  layout; you own the child theme's LESS, sources and templates.
  See the `ntdst-yootheme` skill, which owns that stack.
- **`custom`** — a theme written for this site. No parent assumptions.

Either way the child/site theme overrides everything important, and the parent is
Composer-managed — **never edit the parent**. An edit there is gone at the next
`composer update`, and it is invisible until then.

## Assets go through the framework, not through config

```php
$theme->style('handle',  $src, $deps, $ver, 'all', $priority);
$theme->script('handle', $src, $deps, $ver, $in_footer, $priority);
```

Both defer to `wp_enqueue_scripts` and pass through to WordPress verbatim — compute
versions and conditions at the call site. `$priority` is the ordering lever: a child
overriding its parent's CSS needs a late one (YOOtheme children use 20). For
`admin_enqueue_scripts` use `$theme->on()`; there is no admin variant.

> **The `assets` config key is DELETED and fails silently.** An `assets` block in
> `theme-config.php` is merged into config, read by nothing, and the page loads
> without your CSS. `validate_config()` reads only `textdomain`, `content_width`,
> `theme_support`, `image_sizes`, `menus`, `sidebars`, `excerpt`.

## Vite

The manifest is the contract. Read it at runtime rather than hardcoding hashed
filenames, and enqueue what it names:

```php
$manifest = json_decode(file_get_contents(get_stylesheet_directory() . '/assets/dist/.vite/manifest.json'), true);
$entry    = $manifest['resources/js/main.js'];
$theme->script('main', get_stylesheet_directory_uri() . '/assets/dist/' . $entry['file'], [], null);
foreach ($entry['css'] ?? [] as $css) {
    $theme->style('main', get_stylesheet_directory_uri() . '/assets/dist/' . $css, [], null);
}
```

Pass `null` for `$ver` — the hash in the filename already busts the cache, and a
second version string only splits it.

## Templates

Templates resolve through `ntdst_response()` / `NTDST_Template_Loader`, not
`ob_start` + `include`. Paths are registered live; there is no cache to clear.
Use `page()` when WordPress must still fire `wp_head()`/`wp_footer()`, `render()`
to echo and exit, `html()` to get a string.

## See also

- `ntdst-framework` — the response/template contract and its traps
- `ntdst-yootheme` — everything YOOtheme Pro
- `wp-infra` — the build and deploy side of the pipeline
