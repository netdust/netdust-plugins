<?php
/**
 * Read and write YOOtheme builder PAGES and TEMPLATES from WP-CLI.
 *
 *   # pages (layouts stored in post_content)
 *   wp eval-file yoo-content.php page list
 *   wp eval-file yoo-content.php page get 44            > layout.json
 *   wp eval-file yoo-content.php page get about-us      > layout.json
 *   wp eval-file yoo-content.php page set 44 layout.json
 *   wp eval-file yoo-content.php page patch 44 children/0/children/1/props/link '"/contact/"'
 *
 *   # templates (stored in the `yootheme` option — ORDER IS ROUTING PRIORITY)
 *   wp eval-file yoo-content.php template list
 *   wp eval-file yoo-content.php template get bFIb-syj  > tpl.json
 *   wp eval-file yoo-content.php template set bFIb-syj tpl.json
 *   wp eval-file yoo-content.php template set new tpl.json      # generates an id
 *   wp eval-file yoo-content.php template patch bFIb-syj layout/children/2/props/style '"muted"'
 *   wp eval-file yoo-content.php template reorder id1,id2,id3
 *   wp eval-file yoo-content.php template delete <id>
 *   wp eval-file yoo-content.php template export        > all-templates.json
 *
 *   # library (My Layouts — starter layouts and saved sections, upsert by name)
 *   wp eval-file yoo-content.php library list
 *   wp eval-file yoo-content.php library get 3f2a9c1e   > starter.json
 *   wp eval-file yoo-content.php library set starter.json     # root: a named layout or section
 *   wp eval-file yoo-content.php library delete 3f2a9c1e
 *
 *   # builder widgets (layouts in header / dialog / bottom positions)
 *   wp eval-file yoo-content.php widget list
 *   wp eval-file yoo-content.php widget get 2           > widget.json
 *   wp eval-file yoo-content.php widget set 2 widget.json
 *   wp eval-file yoo-content.php widget new navbar "Navbar CTA" widget.json
 *
 * `patch` re-fetches the LIVE copy immediately before writing and fails when the
 * path resolves to nothing — a get → edit → set cycle silently drops whatever a
 * human saved in the builder meanwhile. Paths are slash-separated node keys.
 *
 * Every write runs yoo-lint.php first and refuses on an error (the word `no-lint`
 * as an extra argument bypasses it, logged). A root `version` missing from a hand-authored layout is filled
 * from the site's config and logged — without it every element migration runs on
 * save and rewrites props.
 *
 * ⚠ RUN AS AN ADMIN: `wp --user=1 eval-file yoo-content.php page set …`
 *   Without a user, WordPress applies KSES to post_content and **mangles the
 *   builder JSON comment**. This script refuses to write a page unless the
 *   current user can `unfiltered_html`, or you pass `--allow-kses-strip`.
 *
 * Fidelity: both writers run the SAME builder pipeline the UI uses, so output is
 * byte-identical to a Customizer/Builder save (verified on a live install):
 *
 *   page:     $fulltext  = json_encode($builder->withParams(['context'=>'save'])->load($json),
 *                                      JSON_UNESCAPED_SLASHES|JSON_UNESCAPED_UNICODE)
 *             $introtext = $builder->withParams(['context'=>'content'])->render($json)
 *             post_content = "{$introtext}\n<!--more-->\n<!-- {$fulltext} -->"
 *             (packages/builder-wordpress/src/PageController.php::savePage)
 *
 *   template: layout normalised through ['context'=>'save'], stored via the
 *             Storage service with `id`/`url` omitted
 *             (packages/builder-templates/src/TemplateController.php)
 *
 * A template's `layout` has the SAME root shape as a page's —
 * {"type":"layout","children":[…],"version":"…"} — NOT a bare node array.
 * `Builder::load()` returns null for any non-object, which is how you can tell.
 * A bare array passed here is wrapped for you.
 *
 * Storage note: the `yootheme` option is written by Storage on the **shutdown**
 * hook, not immediately — verified to fire under WP-CLI. Don't `exit()` early.
 */

if (!defined('WP_CLI') || !WP_CLI) {
    exit("Run via: wp eval-file yoo-content.php <page|template> <cmd> [args]\n");
}

use YOOtheme\Builder;
use YOOtheme\Storage;

define('YOO_LINT_LIBRARY', true);
require_once __DIR__ . '/yoo-lint.php';

$argv = $args ?? [];
// WP-CLI eval-file rejects --flags it does not declare, so flags are bare words too.
const YC_FLAGS = ['no-lint', 'allow-kses-strip'];
$flags = array_map(fn($a) => '--' . ltrim($a, '-'), array_filter($argv, fn($a) => in_array(ltrim($a, '-'), YC_FLAGS, true)));
$argv = array_values(array_filter($argv, fn($a) => !in_array(ltrim($a, '-'), YC_FLAGS, true)));
$group = array_shift($argv) ?: '';
$cmd = array_shift($argv) ?: '';

const LAYOUT_RE = '/<!--\s?(\{.*})\s?-->/s';        // PostHelper::PATTERN

function yc_builder(): Builder {
    if (!function_exists('YOOtheme\app')) {
        WP_CLI::error('YOOtheme app not booted — is the theme (or its child) active?');
    }
    $b = \YOOtheme\app(Builder::class);
    if (!$b) WP_CLI::error('Could not resolve the Builder service.');
    return $b;
}

function yc_storage(): Storage {
    $s = \YOOtheme\app(Storage::class);
    if (!$s) WP_CLI::error('Could not resolve the Storage service.');
    return $s;
}

/**
 * Decode WITHOUT assoc so empty objects stay objects.
 *
 * ⚠ Layout JSON distinguishes `"arguments":{}` from `"arguments":[]`. Decoding
 * with assoc=true turns every empty object into an empty array, and re-encoding
 * then writes `[]` — a silent, site-wide diff against what the builder stored.
 * `PageController` decodes with `json_decode($page)` (no second arg) for exactly
 * this reason. Verified: assoc=true round-trip corrupted 2 of 10 nodes on a real
 * page while keeping the byte count identical.
 */
function yc_read_json(string $file) {
    if (!is_readable($file)) WP_CLI::error("cannot read $file");
    $d = json_decode(file_get_contents($file));
    if ($d === null) WP_CLI::error("$file is not valid JSON");
    return $d;
}

/** Property/key access that works on stdClass and array alike. */
function yc_prop($o, string $k, $default = null) {
    if (is_object($o)) return $o->$k ?? $default;
    if (is_array($o))  return $o[$k] ?? $default;
    return $default;
}

function yc_dump($v): void {
    WP_CLI::log(json_encode($v, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
}

function yc_backup(string $tag, $data): string {
    $f = getcwd() . "/yoo-{$tag}-backup-" . gmdate('Ymd-His') . '.json';
    file_put_contents($f, json_encode($data, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
    WP_CLI::log("backup: $f");
    return $f;
}

/** Resolve a page by numeric ID or slug. */
function yc_find_post(string $ref): \WP_Post {
    $post = ctype_digit($ref) ? get_post((int) $ref) : get_page_by_path($ref, OBJECT, get_post_types());
    if (!$post) {
        global $wpdb;
        $id = $wpdb->get_var($wpdb->prepare("SELECT ID FROM {$wpdb->posts} WHERE post_name=%s LIMIT 1", $ref));
        $post = $id ? get_post($id) : null;
    }
    if (!$post) WP_CLI::error("no post found for '$ref'");
    return $post;
}

/** Decode WITHOUT assoc — see yc_read_json() for why `{}` must not become `[]`. */
function yc_layout_of(?string $content) {
    if (!$content || !preg_match(LAYOUT_RE, $content, $m)) return null;
    return json_decode($m[1]);
}

/** The site's theme version, for a hand-authored layout that carries none. */
function yc_site_version(): string
{
    $cfg = json_decode((string) get_theme_mod('config'));
    if (!empty($cfg->version)) return (string) $cfg->version;
    $themeCfg = @include get_template_directory() . '/config.php';
    return (string) ($themeCfg['version'] ?? '');
}

function yc_ensure_version(object $layout): void
{
    if (yc_prop($layout, 'type') === 'layout' && empty($layout->version)) {
        $v = yc_site_version();
        if ($v === '') WP_CLI::error('layout has no root `version` and the site version is unknown — add it by hand (copy from `page get <id>`).');
        $layout->version = $v;
        WP_CLI::log("note: root version filled in ($v) — without it every element migration runs on save.");
    }
}

/** Refuse a layout the linter finds an error in, unless --no-lint (logged). */
function yc_lint(object $layout, string $label, array $flags): void
{
    if (in_array('--no-lint', $flags, true)) { WP_CLI::warning('lint skipped (--no-lint)'); return; }
    $vocab = new \YooLint\Vocab(get_template_directory());
    $linter = new \YooLint\Linter($vocab);
    $linter->lint($layout, $label);
    $errors = 0;
    foreach ($linter->findings as $f) {
        WP_CLI::log(sprintf('%-5s %-26s %s: %s → %s', $f['level'], $f['code'], $f['path'], $f['msg'], $f['fix']));
        if ($f['level'] === 'error') $errors++;
    }
    if ($errors) WP_CLI::error("$errors lint error(s) — fix them or pass --no-lint.");
}

/** Resolve `a/0/b` into $root and set it; error when any segment is missing. */
function yc_patch(object $root, string $path, $value): void
{
    $segs = array_values(array_filter(explode('/', trim($path, '/')), 'strlen'));
    if (!$segs) WP_CLI::error('empty path');
    $last = array_pop($segs);
    $ref = $root;
    foreach ($segs as $s) {
        $next = is_array($ref) ? ($ref[$s] ?? null) : ($ref->$s ?? null);
        if ($next === null) WP_CLI::error("path segment `$s` does not exist in the LIVE copy — nothing written (re-fetch and look).");
        $ref = $next;
    }
    if (is_array($ref)) {
        if (!array_key_exists($last, $ref)) WP_CLI::error("`$last` does not exist at the end of the path — nothing written.");
        $ref[$last] = $value;
    } elseif (is_object($ref)) {
        $ref->$last = $value;
    } else {
        WP_CLI::error("cannot set `$last` on a scalar.");
    }
}

/** A CPT archive at the page's own slug wins the rewrite — the page renders nowhere. */
function yc_warn_archive_shadow(\WP_Post $post): void
{
    foreach (get_post_types(['public' => true], 'objects') as $pt) {
        if (empty($pt->has_archive)) continue;
        $slug = is_string($pt->has_archive) ? $pt->has_archive : ($pt->rewrite['slug'] ?? $pt->name);
        if (trim((string) $slug, '/') === $post->post_name && $post->post_parent === 0) {
            WP_CLI::warning("the `{$pt->name}` archive rewrites to /{$post->post_name}/ too — the archive wins; build this layout in an `archive-{$pt->name}` template instead.");
        }
    }
}

// ---------------------------------------------------------------- pages

function yc_page_list(): void {
    global $wpdb;
    $rows = $wpdb->get_results("SELECT ID, post_type, post_status, post_name, post_title, post_content
                                FROM {$wpdb->posts}
                                WHERE post_status NOT IN ('auto-draft','inherit','trash')
                                  AND post_type NOT IN ('revision','nav_menu_item','attachment')
                                ORDER BY post_type, ID");
    foreach ($rows as $r) {
        $has = yc_layout_of($r->post_content) ? 'builder' : '-';
        WP_CLI::log(sprintf('%6d  %-12s %-9s %-34s %s',
            $r->ID, $r->post_type, $r->post_status, substr($r->post_name, 0, 33), $has));
    }
}

function yc_page_set(string $ref, string $file, array $flags): void
{
    $post = yc_find_post($ref);
    $layout = yc_read_json($file);
    if (yc_prop($layout, 'type') !== 'layout') {
        WP_CLI::error("root node must be {\"type\":\"layout\",...} — got '"
            . (yc_prop($layout, 'type') ?? 'nothing') . "'. A page's root and a template's "
            . '`layout` share this shape — see the header; wrap a bare node array in it.');
    }
    yc_page_write($post, $layout, $flags);
}

function yc_page_patch(string $ref, string $path, string $json, array $flags): void
{
    $post = yc_find_post($ref);                       // the LIVE copy, read now
    $layout = yc_layout_of($post->post_content);
    if ($layout === null) WP_CLI::error("post {$post->ID} has no builder layout.");
    $value = json_decode($json);
    if ($value === null && strtolower(trim($json)) !== 'null') WP_CLI::error("value is not valid JSON: $json");
    yc_patch($layout, $path, $value);
    yc_page_write($post, $layout, $flags);
}

function yc_page_write(\WP_Post $post, object $layout, array $flags): void
{
    if (!current_user_can('unfiltered_html') && !in_array('--allow-kses-strip', $flags, true)) {
        WP_CLI::error("current user cannot 'unfiltered_html' — KSES would mangle the builder "
            . 'JSON. Re-run with `wp --user=<admin-id> eval-file …` '
            . '(or pass --allow-kses-strip if you truly want the filtered result).');
    }
    yc_ensure_version($layout);
    yc_lint($layout, "page:{$post->post_name}#{$post->ID}", $flags);
    yc_warn_archive_shadow($post);

    yc_backup("page-{$post->ID}", ['ID' => $post->ID, 'post_content' => $post->post_content]);

    $builder = yc_builder();
    $json = json_encode($layout, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

    $loaded = $builder->withParams(['context' => 'save'])->load($json);
    if (!$loaded) WP_CLI::error('builder->load() returned nothing — layout JSON rejected.');
    $fulltext = json_encode($loaded, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);

    $introtext = (string) $builder->withParams(['context' => 'content'])->render($json);

    $content = "{$introtext}\n<!--more-->\n<!-- {$fulltext} -->";
    $res = wp_update_post(['ID' => $post->ID, 'post_content' => wp_slash($content)], true);
    if (is_wp_error($res)) WP_CLI::error($res->get_error_message());

    update_post_meta($post->ID, '_edit_last', get_current_user_id() ?: 1);

    $back = yc_layout_of(get_post($post->ID)->post_content);
    if ($back === null) WP_CLI::error('POST-WRITE CHECK FAILED: layout no longer parses. Restore the backup.');

    WP_CLI::success(sprintf('page %d updated — %d nodes, %d bytes layout + %d bytes introtext.',
        $post->ID, substr_count($fulltext, '"type":'), strlen($fulltext), strlen($introtext)));
}

// ------------------------------------------------------------ templates

function yc_templates(): array {
    return yc_storage()->get('templates', []) ?: [];
}

function yc_template_list(): void {
    $t = yc_templates();
    if (!$t) { WP_CLI::log('(no templates)'); return; }
    $i = 0;
    foreach ($t as $id => $tpl) {
        WP_CLI::log(sprintf('%2d. [%-10s] %-26s %-30s query=%s%s',
            $i++, $id, $tpl['type'] ?? '?', substr((string) ($tpl['name'] ?? ''), 0, 29),
            json_encode($tpl['query'] ?? []),
            ($tpl['status'] ?? '') === 'disabled' ? '  DISABLED' : ''));
    }
    WP_CLI::log("\n# match() takes the FIRST hit top-down. A template with an empty query is the\n"
        . '# catch-all for its type and must be LAST. Use `template reorder` to fix.');
}

function yc_template_id(): string {
    $a = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-';
    $s = '';
    for ($i = 0; $i < 8; $i++) $s .= $a[random_int(0, strlen($a) - 1)];
    return $s;
}

function yc_template_set(string $id, string $file, array $flags): void
{
    $tpl = yc_read_json($file);
    $type = yc_prop($tpl, 'type');
    $layout = yc_prop($tpl, 'layout');
    if (!$type) WP_CLI::error("template needs a 'type' (e.g. single-post, archive-event, taxonomy-category, error-404, search).");
    if ($layout === null) WP_CLI::error("template needs a 'layout'.");
    // A template's layout has the SAME root shape as a page: {"type":"layout",…}.
    // Builder::load() returns null for anything that isn't an object, so accept a
    // bare node array as a convenience but wrap it before handing it over.
    if (is_array($layout)) {
        WP_CLI::log('note: wrapping bare node array in {"type":"layout",…} — that is the stored shape.');
        $layout = (object) ['type' => 'layout', 'children' => $layout];
        $tpl->layout = $layout;
    }
    if (yc_prop($layout, 'type') !== 'layout') {
        WP_CLI::error("'layout' root must be {\"type\":\"layout\",…} — got '" . yc_prop($layout, 'type') . "'.");
    }
    yc_template_write($id, $tpl, $flags);
}

function yc_template_patch(string $id, string $path, string $json, array $flags): void
{
    $all = yc_templates();                            // the LIVE copy, read now
    if (!isset($all[$id])) WP_CLI::error("no template '$id' — try `template list`.");
    $tpl = json_decode(json_encode($all[$id]));       // stdClass end to end, `{}` preserved
    $value = json_decode($json);
    if ($value === null && strtolower(trim($json)) !== 'null') WP_CLI::error("value is not valid JSON: $json");
    yc_patch($tpl, $path, $value);
    yc_template_write($id, $tpl, $flags);
}

function yc_template_write(string $id, object $tpl, array $flags): void
{
    $type = yc_prop($tpl, 'type');
    $layout = $tpl->layout;
    yc_ensure_version($layout);
    yc_lint($layout, "template:$id", $flags);

    $all = yc_templates();
    yc_backup('templates', $all);

    if ($id === 'new') {
        do { $id = yc_template_id(); } while (isset($all[$id]));
        WP_CLI::log("new template id: $id");
    }

    $builder = yc_builder();
    $loaded = $builder->withParams(['context' => 'save'])
        ->load(json_encode($layout, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    if ($loaded === null) WP_CLI::error('builder->load() rejected the layout.');
    $tpl->layout = $loaded;

    unset($tpl->id, $tpl->url);                           // Arr::omit, as the controller does
    yc_storage()->set("templates.{$id}", $tpl);
    WP_CLI::success("template '$id' saved ($type) — persisted at shutdown.");
}

function yc_template_reorder(string $csv): void {
    $sorting = array_values(array_filter(array_map('trim', explode(',', $csv))));
    $templates = yc_templates();
    if (!$templates) WP_CLI::error('no templates to reorder.');
    foreach ($sorting as $id) {
        if (!isset($templates[$id])) WP_CLI::error("unknown template id '$id'");
    }
    yc_backup('templates', $templates);
    // exactly TemplateController::reorderTemplates
    yc_storage()->set('templates',
        array_merge(array_intersect_key(array_flip($sorting), $templates), $templates));
    WP_CLI::success('reordered — new order: ' . implode(', ', array_keys(
        array_merge(array_intersect_key(array_flip($sorting), $templates), $templates))));
}

// -------------------------------------------------------------- widgets

function yc_widgets(): array
{
    $w = get_option('widget_builderwidget', ['_multiwidget' => 1]);
    return is_array($w) ? $w : ['_multiwidget' => 1];
}

function yc_widget_positions(): array
{
    $where = [];
    foreach ((array) get_option('sidebars_widgets', []) as $position => $ids) {
        foreach ((array) $ids as $wid) {
            if (is_string($wid) && str_starts_with($wid, 'builderwidget-')) $where[substr($wid, 14)] = $position;
        }
    }
    return $where;
}

function yc_widget_layout($content)
{
    return is_string($content) ? json_decode($content) : json_decode(json_encode($content));
}

function yc_widget_list(): void
{
    $where = yc_widget_positions();
    foreach (yc_widgets() as $id => $w) {
        if (!is_numeric($id) || !is_array($w)) continue;
        $lay = yc_widget_layout($w['content'] ?? '');
        WP_CLI::log(sprintf('%-16s builderwidget-%-3s %-30s %s nodes', $where[(string) $id] ?? 'unplaced', $id,
            substr((string) ($w['title'] ?? ''), 0, 29), $lay ? substr_count(json_encode($lay), '"type":') : 0));
    }
}

function yc_widget_write(int $id, object $layout, array $flags, ?string $title = null, ?string $position = null): void
{
    yc_ensure_version($layout);
    yc_lint($layout, "widget:builderwidget-$id", $flags);
    $widgets = yc_widgets();
    yc_backup('widgets', $widgets);
    $content = json_encode(yc_builder()->withParams(['context' => 'save'])
        ->load(json_encode($layout, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE)));
    if (!$content || $content === 'null') WP_CLI::error('builder rejected the layout.');
    $widgets[$id] = ['title' => $title ?? ($widgets[$id]['title'] ?? ''), 'content' => $content, 'element' => $widgets[$id]['element'] ?? ''];
    $widgets['_multiwidget'] = 1;
    update_option('widget_builderwidget', $widgets);
    if ($position !== null) {
        $sidebars = get_option('sidebars_widgets', []);
        $sidebars[$position] = array_values(array_unique(array_merge($sidebars[$position] ?? [], ["builderwidget-$id"])));
        update_option('sidebars_widgets', $sidebars);
    }
    WP_CLI::success("builderwidget-$id written" . ($position ? " → position '$position'" : ''));
}

// ------------------------------------------------------------- library

function yc_library(): array {
    return yc_storage()->get('library', []) ?: [];
}

function yc_library_list(): void {
    $lib = yc_library();
    if (!$lib) { WP_CLI::log('(empty library)'); return; }
    foreach ($lib as $id => $el) {
        WP_CLI::log(sprintf('[%-10s] %-8s %s', $id, $el['type'] ?? '?', $el['name'] ?? ''));
    }
}

/**
 * Upsert one library entry from a file whose root is a named `layout` or `section`.
 * The `name` is the key the builder lists and the key this upserts on; a layout
 * root is linted like a page. The id is stable per name so re-runs update in place.
 */
function yc_library_set(string $file, array $flags): void
{
    $el = yc_read_json($file);
    $name = yc_prop($el, 'name');
    $type = yc_prop($el, 'type');
    if (!$name) WP_CLI::error("library entry needs a 'name' — it is the upsert key and what the builder lists.");
    if (!in_array($type, ['layout', 'section'], true)) WP_CLI::error("library entry root must be a 'layout' or a 'section' — got '$type'.");
    if ($type === 'layout') {
        yc_ensure_version($el);
        yc_lint($el, "library:$name", $flags);
    }
    $lib = yc_library();
    yc_backup('library', $lib);
    $id = null;
    foreach ($lib as $k => $entry) {
        if (($entry['name'] ?? null) === $name) { $id = (string) $k; break; }
    }
    $id ??= substr(md5($name), 0, 8);
    $loaded = yc_builder()->withParams(['context' => 'save'])
        ->load(json_encode($el, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
    if ($loaded === null) WP_CLI::error('builder->load() rejected the entry.');
    yc_storage()->set("library.{$id}", $loaded);
    WP_CLI::success("library '$name' " . (isset($lib[$id]) ? 'updated' : 'added') . " as $id ($type) — persisted at shutdown.");
}

// ------------------------------------------------------------- dispatch

switch ("$group $cmd") {
    case 'page list':   yc_page_list(); break;

    case 'page get':
        $post = yc_find_post($argv[0] ?? '');
        $lay = yc_layout_of($post->post_content);
        if ($lay === null) WP_CLI::error("post {$post->ID} has no builder layout.");
        yc_dump($lay);
        break;

    case 'page set':
        if (count($argv) < 2) WP_CLI::error('usage: page set <id|slug> <layout.json> [no-lint]');
        yc_page_set($argv[0], $argv[1], $flags);
        break;

    case 'page patch':
        if (count($argv) < 3) WP_CLI::error('usage: page patch <id|slug> <children/0/props/key> <json-value>');
        yc_page_patch($argv[0], $argv[1], $argv[2], $flags);
        break;

    case 'template list':    yc_template_list(); break;
    case 'template export':  yc_dump(yc_templates()); break;

    case 'template get':
        $t = yc_templates();
        $id = $argv[0] ?? '';
        if (!isset($t[$id])) WP_CLI::error("no template '$id' — try `template list`.");
        yc_dump($t[$id]);
        break;

    case 'template set':
        if (count($argv) < 2) WP_CLI::error('usage: template set <id|new> <tpl.json> [no-lint]');
        yc_template_set($argv[0], $argv[1], $flags);
        break;

    case 'template patch':
        if (count($argv) < 3) WP_CLI::error('usage: template patch <id> <layout/children/0/props/key> <json-value>');
        yc_template_patch($argv[0], $argv[1], $argv[2], $flags);
        break;

    case 'widget list':   yc_widget_list(); break;

    case 'widget get':
        $w = yc_widgets();
        $id = $argv[0] ?? '';
        if (!isset($w[$id])) WP_CLI::error("no builderwidget-$id — try `widget list`.");
        yc_dump(yc_widget_layout($w[$id]['content'] ?? ''));
        break;

    case 'widget set':
        if (count($argv) < 2) WP_CLI::error('usage: widget set <id> <layout.json>');
        if (!isset(yc_widgets()[$argv[0]])) WP_CLI::error("no builderwidget-{$argv[0]}");
        yc_widget_write((int) $argv[0], yc_read_json($argv[1]), $flags);
        break;

    case 'widget new':
        if (count($argv) < 3) WP_CLI::error('usage: widget new <position> <title> <layout.json>');
        $ids = array_filter(array_keys(yc_widgets()), 'is_numeric');
        yc_widget_write($ids ? max($ids) + 1 : 2, yc_read_json($argv[2]), $flags, $argv[1], $argv[0]);
        break;

    case 'library list':   yc_library_list(); break;

    case 'library get':
        $lib = yc_library();
        $id = $argv[0] ?? '';
        if (!isset($lib[$id])) WP_CLI::error("no library entry '$id' — try `library list`.");
        yc_dump($lib[$id]);
        break;

    case 'library set':
        if (count($argv) < 1) WP_CLI::error('usage: library set <entry.json> [no-lint]');
        yc_library_set($argv[0], $flags);
        break;

    case 'library delete':
        $id = $argv[0] ?? '';
        $lib = yc_library();
        if (!isset($lib[$id])) WP_CLI::error("no library entry '$id'");
        yc_backup('library', $lib);
        yc_storage()->del("library.{$id}");
        WP_CLI::success("library entry '$id' deleted — persisted at shutdown.");
        break;

    case 'template delete':
        $id = $argv[0] ?? '';
        $all = yc_templates();
        if (!isset($all[$id])) WP_CLI::error("no template '$id'");
        yc_backup('templates', $all);
        yc_storage()->del("templates.{$id}");
        WP_CLI::success("template '$id' deleted — persisted at shutdown.");
        break;

    case 'template reorder':
        yc_template_reorder($argv[0] ?? '');
        break;

    default:
        WP_CLI::error("unknown: '$group $cmd'\n"
            . "  page     list | get <id|slug> | set <id|slug> <file.json> | patch <id|slug> <path> <json>\n"
            . "  template list | get <id> | set <id|new> <file.json> | patch <id> <path> <json> | delete <id> | reorder <ids> | export\n"
            . "  widget   list | get <id> | set <id> <file.json> | new <position> <title> <file.json>\n"
            . '  library  list | get <id> | set <entry.json> | delete <id>   (entry root: a named layout or section)');
}
