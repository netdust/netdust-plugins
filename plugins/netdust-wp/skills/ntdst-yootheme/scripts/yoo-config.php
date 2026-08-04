<?php
/**
 * Read and write YOOtheme's `config` theme_mod safely, from WP-CLI.
 *
 *   wp eval-file yoo-config.php get                       # whole config as JSON
 *   wp eval-file yoo-config.php get header.layout
 *   wp eval-file yoo-config.php set header.layout '"stacked-justify"'
 *   wp eval-file yoo-config.php set menu.positions.navbar.menu 33
 *   wp eval-file yoo-config.php set site.breadcrumbs true
 *   wp eval-file yoo-config.php unset top.image
 *   wp eval-file yoo-config.php backup                    # → yoo-config-backup-<ts>.json
 *   wp eval-file yoo-config.php restore <file.json>
 *
 * VALUES ARE JSON. Quote strings: '"expand"', not 'expand'.
 *
 * Why this exists rather than a `wp option update` one-liner:
 *
 *  1. `config` is a JSON string inside the PHP-serialized `theme_mods_<stylesheet>`
 *     option. A malformed write silently destroys the entire site configuration.
 *     This always backs up first and verifies the round-trip.
 *
 *  2. The Customizer's save path is NOT just a write — it runs
 *     `Event::emit('config.save|filter', $values)`, whose listeners
 *     (`SaveMenuLocations`, `SaveBuilderLayouts`) derive `nav_menu_locations`
 *     from `menu.positions[*].menu` and normalise the footer / mega-menu
 *     layouts through the builder. This script emits the SAME event, so the
 *     result is byte-identical to what the UI would have produced.
 *     (See packages/theme-wordpress/src/CustomizerController.php::save.)
 *
 *  3. It refuses to pretend it can do styling. See the warning below.
 *
 * ⚠ CANNOT recompile CSS. YOOtheme has no server-side LESS compiler — less.js
 *   compiles in the browser and uploads the result via StyleController::save.
 *   Changing `style`, `less` or `custom_less` here writes the value but leaves
 *   `css/theme.<id>.css` stale. A human must open the Customizer and hit Save.
 *   This script warns when you touch those keys.
 */

if (!defined('WP_CLI') || !WP_CLI) {
    exit("Run via: wp eval-file yoo-config.php <cmd> [args]\n");
}

$argv = $args ?? [];                       // wp eval-file passes extra args in $args
$cmd = array_shift($argv) ?: 'get';

const STYLE_KEYS = ['style', 'less', 'custom_less'];

function yoo_read(): array {
    $raw = get_theme_mod('config');
    if ($raw === false || $raw === null) {
        WP_CLI::error('No `config` theme_mod. Is the YOOtheme theme active? '
            . '(current: ' . get_stylesheet() . ')');
    }
    $cfg = is_string($raw) ? json_decode($raw, true) : $raw;
    if (!is_array($cfg)) {
        WP_CLI::error('`config` theme_mod is not decodable JSON — refusing to touch it.');
    }
    return $cfg;
}

function yoo_backup(array $cfg): string {
    $file = getcwd() . '/yoo-config-backup-' . gmdate('Ymd-His') . '.json';
    file_put_contents($file, json_encode($cfg, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES));
    return $file;
}

/** Write through YOOtheme's own save pipeline so listeners run. */
function yoo_write(array $cfg, array $touched = []): void {
    $backup = yoo_backup(yoo_read());
    WP_CLI::log("backup: $backup");

    if (class_exists('\YOOtheme\Event')) {
        $filtered = \YOOtheme\Event::emit('config.save|filter', $cfg);
        if (is_array($filtered) && $filtered) {
            $cfg = $filtered;
        } else {
            WP_CLI::warning('config.save returned nothing usable — writing unfiltered.');
        }
    } else {
        WP_CLI::warning('YOOtheme app not booted; config.save listeners did NOT run. '
            . 'nav_menu_locations and builder-layout normalisation may be stale.');
    }

    $encoded = json_encode($cfg, JSON_UNESCAPED_SLASHES);
    if ($encoded === false || json_decode($encoded, true) === null) {
        WP_CLI::error('Encode/round-trip failed — nothing written. Backup kept at ' . $backup);
    }
    foreach ($touched as $path) {
        if (in_array(strtok($path, '.'), STYLE_KEYS, true)) {
            WP_CLI::warning("`$path` is style-related. CSS is compiled IN THE BROWSER — "
                . 'open the Customizer and Save, or css/theme.*.css stays stale.');
        }
    }

    set_theme_mod('config', $encoded);
    WP_CLI::success('config written (' . strlen($encoded) . ' bytes).');
}

function yoo_get(array $cfg, string $path) {
    foreach (explode('.', $path) as $seg) {
        if (!is_array($cfg) || !array_key_exists($seg, $cfg)) return null;
        $cfg = $cfg[$seg];
    }
    return $cfg;
}

function yoo_set(array &$cfg, string $path, $value): void {
    $ref = &$cfg;
    foreach (explode('.', $path) as $seg) {
        if (!isset($ref[$seg]) || !is_array($ref[$seg])) $ref[$seg] = [];
        $ref = &$ref[$seg];
    }
    $ref = $value;
}

function yoo_unset(array &$cfg, string $path): void {
    $segs = explode('.', $path);
    $last = array_pop($segs);
    $ref = &$cfg;
    foreach ($segs as $seg) {
        if (!isset($ref[$seg]) || !is_array($ref[$seg])) return;
        $ref = &$ref[$seg];
    }
    unset($ref[$last]);
}

switch ($cmd) {
    case 'get':
        $cfg = yoo_read();
        $path = $argv[0] ?? null;
        $out = $path === null ? $cfg : yoo_get($cfg, $path);
        WP_CLI::log(json_encode($out, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE));
        break;

    case 'set':
        [$path, $json] = [$argv[0] ?? null, $argv[1] ?? null];
        if ($path === null || $json === null) WP_CLI::error('usage: set <dotted.path> <json-value>');
        $value = json_decode($json, true);
        if ($value === null && strtolower(trim($json)) !== 'null') {
            WP_CLI::error("value is not valid JSON: $json  (strings need quotes: '\"expand\"')");
        }
        $cfg = yoo_read();
        WP_CLI::log('was: ' . json_encode(yoo_get($cfg, $path)));
        yoo_set($cfg, $path, $value);
        yoo_write($cfg, [$path]);
        break;

    case 'unset':
        $path = $argv[0] ?? null;
        if ($path === null) WP_CLI::error('usage: unset <dotted.path>');
        $cfg = yoo_read();
        yoo_unset($cfg, $path);
        yoo_write($cfg, [$path]);
        break;

    case 'backup':
        WP_CLI::success('wrote ' . yoo_backup(yoo_read()));
        break;

    case 'restore':
        $file = $argv[0] ?? null;
        if (!$file || !is_readable($file)) WP_CLI::error('usage: restore <file.json>');
        $cfg = json_decode(file_get_contents($file), true);
        if (!is_array($cfg)) WP_CLI::error('backup file is not valid JSON.');
        yoo_write($cfg, []);
        break;

    default:
        WP_CLI::error("unknown command '$cmd' — get | set | unset | backup | restore");
}
