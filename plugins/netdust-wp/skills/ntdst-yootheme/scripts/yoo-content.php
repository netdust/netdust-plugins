<?php
/**
 * Read and write YOOtheme builder PAGES and TEMPLATES from WP-CLI.
 *
 *   # pages (layouts stored in post_content)
 *   wp eval-file yoo-content.php page list
 *   wp eval-file yoo-content.php page get 44            > layout.json
 *   wp eval-file yoo-content.php page get about-us      > layout.json
 *   wp eval-file yoo-content.php page set 44 layout.json
 *
 *   # templates (stored in the `yootheme` option — ORDER IS ROUTING PRIORITY)
 *   wp eval-file yoo-content.php template list
 *   wp eval-file yoo-content.php template get bFIb-syj  > tpl.json
 *   wp eval-file yoo-content.php template set bFIb-syj tpl.json
 *   wp eval-file yoo-content.php template set new tpl.json      # generates an id
 *   wp eval-file yoo-content.php template reorder id1,id2,id3
 *   wp eval-file yoo-content.php template delete <id>
 *   wp eval-file yoo-content.php template export        > all-templates.json
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

$argv = $args ?? [];
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

function yc_page_set(string $ref, string $file, array $flags): void {
    $post = yc_find_post($ref);
    $layout = yc_read_json($file);

    if (yc_prop($layout, 'type') !== 'layout') {
        WP_CLI::error("root node must be {\"type\":\"layout\",...} — got '"
            . (yc_prop($layout, 'type') ?? 'nothing') . "'. Template layouts are BARE ARRAYS; "
            . 'wrap one before using it as a page.');
    }

    if (!current_user_can('unfiltered_html') && !in_array('--allow-kses-strip', $flags, true)) {
        WP_CLI::error("current user cannot 'unfiltered_html' — KSES would mangle the builder "
            . 'JSON. Re-run with `wp --user=<admin-id> eval-file …` '
            . '(or pass --allow-kses-strip if you truly want the filtered result).');
    }

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

function yc_template_set(string $id, string $file): void {
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
    }
    if (yc_prop($layout, 'type') !== 'layout') {
        WP_CLI::error("'layout' root must be {\"type\":\"layout\",…} — got '" . yc_prop($layout, 'type') . "'.");
    }

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
        if (count($argv) < 2) WP_CLI::error('usage: page set <id|slug> <layout.json>');
        yc_page_set($argv[0], $argv[1], array_slice($argv, 2));
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
        if (count($argv) < 2) WP_CLI::error('usage: template set <id|new> <tpl.json>');
        yc_template_set($argv[0], $argv[1]);
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
            . "  page     list | get <id|slug> | set <id|slug> <file.json>\n"
            . '  template list | get <id> | set <id|new> <file.json> | delete <id> | reorder <ids> | export');
}
