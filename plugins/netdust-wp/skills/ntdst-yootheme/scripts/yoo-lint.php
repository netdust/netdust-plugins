<?php
/**
 * Lint a YOOtheme builder layout against the INSTALLED parent theme's element
 * definitions — before the write, not after the render.
 *
 *   php yoo-lint.php --theme=<parent-theme-dir> [--schema=fields.json] <layout.json>…
 *   wp eval-file yoo-lint.php page <id|slug>
 *   wp eval-file yoo-lint.php template <id>
 *   wp eval-file yoo-lint.php all            # every tree in the DB
 *
 * Under WP-CLI the theme dir defaults to get_template_directory(), and options are
 * plain words (`all`, `schema=fields.json`) because eval-file rejects `--flags` it
 * does not declare. Every finding is
 * `LEVEL code path: message → fix`; exit 1 on any error. Codes:
 *
 *   unknown-type, unknown-prop, no-version, orphan-item, layout-count, grid-over-6,
 *   parent-at-root, binding-args                                   (error)
 *   lone-column, block-align-no-maxwidth, bgcolor-needs-empty-style,
 *   bare-featured-image, row-in-column, list-on-container, unnamed-section,
 *   condition-on-list, unknown-key                                 (warn)
 *
 * Why a script: YOOtheme stores whatever prop it is handed and renders the element
 * default, so an invented name, a missing sibling prop or a mis-scoped binding is
 * invisible in the JSON and looks like a styling bug on screen. Each check here is a
 * trap that cost a session on josworld or edushare (see lessons.md).
 *
 * Vocabulary = element.php `fields` (walked recursively, `${builder.*}` sets expanded
 * from config/builder.php, `child-prop` panels attributed to the child element)
 * + `defaults` + `placeholder.props` + every `{prop}` / `$props['prop']` the element's
 * templates read — because the template renders props the fields list never shows
 * (column `width_*`).
 */

namespace YooLint;

const ITEM_PARENT = ['row' => 'column'];
const ROOT_KEYS   = ['type', 'name', 'props', 'children', 'source', 'version'];
const CONTAINER_PLURAL = ['grid', 'list', 'panel-slider', 'overlay-slider', 'gallery', 'slideshow', 'switcher', 'accordion', 'nav', 'subnav', 'table', 'description_list', 'popover', 'social', 'map', 'button'];

final class Vocab
{
    /** @var array<string, array{props: array<string,bool>, container: bool, item: ?string}> */
    public array $elements = [];
    private array $config = [];

    public function __construct(private string $theme)
    {
        require_once __DIR__ . '/yoo-lint-stubs.php';
        $this->config = $this->loadConfig("$theme/packages/builder/config/builder.php");
        // Props the builder's own transforms read on EVERY node (text_align, maxwidth,
        // position_*, animation, …) — never listed in an element's fields.
        foreach (glob("$theme/packages/builder/src/Builder/*Transform*.php") ?: [] as $tf) {
            $tmp = [];
            $this->collectTemplateProps(file_get_contents($tf), $tmp);
            $this->universal = array_merge($this->universal, array_keys($tmp));
        }
        foreach (glob("$theme/packages/builder*/elements/*/element.php") ?: [] as $file) {
            $pkg = basename(dirname($file, 3));
            $prefix = $pkg === 'builder-wordpress-woocommerce' ? 'woo_' : '';
            try {
                $def = (static fn() => include $file)();
            } catch (\Throwable $e) {
                fwrite(STDERR, "vocab: skipped $file ({$e->getMessage()})\n");
                continue;
            }
            if (!is_array($def) || empty($def['name'])) continue;
            $name = $prefix . $def['name'];
            $props = [];
            $this->collectFields($def['fields'] ?? [], $props, $name);
            foreach (array_keys($def['defaults'] ?? []) as $k) $props[$k] = true;
            foreach (array_keys($def['placeholder']['props'] ?? []) as $k) $props[$k] = true;
            foreach (glob(dirname($file) . '/templates/*.php') ?: [] as $tpl) {
                $this->collectTemplateProps(file_get_contents($tpl), $props);
            }
            foreach ($this->config['advanced']['fields'] ?? [] as $k) $props[$k] = true;
            foreach ($this->universal as $k) $props[$k] = true;
            $this->elements[$name] = ['props' => $props, 'container' => !empty($def['container']), 'item' => null];
            $this->collectChildProps($def['panels'] ?? [], $name);
        }
        foreach ($this->pendingChildProps as $parent => $childProps) {
            $child = ITEM_PARENT[$parent] ?? "{$parent}_item";
            foreach ($childProps as $k) $this->elements[$child]['props'][$k] = true;
        }
        $this->elements['layout']['props']['version'] = true;
    }

    private array $pendingChildProps = [];
    private array $universal = [];

    private function loadConfig(string $file): array
    {
        if (!is_file($file)) return [];
        $cfg = (static fn() => include $file)();
        if (!is_array($cfg)) return [];
        if (isset($cfg['@import']) && is_file($cfg['@import'])) {
            $cfg += $this->loadConfig($cfg['@import']);
        }
        return $cfg;
    }

    /** `fields` is a map of prop => def, but entries may be groups (nested `fields`), name lists, or `${builder.set}` refs. */
    private function collectFields($fields, array &$props, string $element): void
    {
        if (!is_array($fields)) return;
        foreach ($fields as $k => $v) {
            if (is_int($k)) {
                if (is_string($v)) { $this->addRef($v, $props); continue; }
                if (!is_array($v)) continue;
                if (isset($v['name']) && is_string($v['name'])) $props[$v['name']] = true;
                if (isset($v['field']['name'])) $props[$v['field']['name']] = true;
                if (isset($v['fields'])) $this->collectFields($v['fields'], $props, $element);
                continue;
            }
            if (str_starts_with($k, '_')) {
                if (is_array($v) && isset($v['fields'])) $this->collectFields($v['fields'], $props, $element);
                continue;
            }
            if (is_string($v) && preg_match('/^\$\{builder\.(\w+)\}$/', $v, $m)) {
                $set = $this->config[$m[1]] ?? null;
                if (is_array($set) && isset($set['fields']) && is_array($set['fields'])) {
                    foreach ($set['fields'] as $n) if (is_string($n)) $this->addRef($n, $props);
                } else {
                    $props[$k] = true;
                }
                continue;
            }
            $props[$k] = true;
            if (is_array($v)) {
                if (isset($v['internal']) && is_string($v['internal'])) $props[$v['internal']] = true;
                if (isset($v['fields'])) $this->collectFields($v['fields'], $props, $element);
            }
        }
    }

    private function addRef(string $name, array &$props): void
    {
        if (preg_match('/^\$\{builder\.(\w+)\}$/', $name, $m)) $name = $m[1];
        $set = $this->config[$name] ?? null;
        if (is_array($set) && isset($set['fields']) && is_array($set['fields'])) {
            foreach ($set['fields'] as $n) if (is_string($n)) $props[$n] = true;
            return;
        }
        $props[$name] = true;
    }

    private function collectChildProps($panels, string $element): void
    {
        if (!is_array($panels)) return;
        $it = new \RecursiveIteratorIterator(new \RecursiveArrayIterator($panels), \RecursiveIteratorIterator::SELF_FIRST);
        foreach ($it as $k => $v) {
            if (is_array($v) && ($v['type'] ?? '') === 'child-prop' && isset($v['field']['name'])) {
                $this->pendingChildProps[$element][] = $v['field']['name'];
            }
        }
    }

    private function collectTemplateProps(string $src, array &$props): void
    {
        preg_match_all('/\{@?!?([a-z][a-z0-9_]*)[:}]/', $src, $m);
        foreach ($m[1] as $p) $props[$p] = true;
        preg_match_all('/\$props\[[\'"]([a-z][a-z0-9_]*)[\'"]\]/', $src, $m);
        foreach ($m[1] as $p) $props[$p] = true;
    }

    /** Nearest declared prop: a prefix match wins (`padding` → `padding_top`), else Levenshtein ≤ 3. */
    public function nearest(string $element, string $prop): ?string
    {
        $cands = array_keys($this->elements[$element]['props'] ?? []);
        $prefixed = array_filter($cands, fn($c) => str_starts_with($c, $prop . '_'));
        if ($prefixed) { usort($prefixed, fn($a, $b) => strlen($a) <=> strlen($b)); return $prefixed[0]; }
        $best = null; $bestD = 4;
        foreach ($cands as $cand) {
            $d = levenshtein($prop, $cand);
            if ($d < $bestD) { $best = $cand; $bestD = $d; }
        }
        return $best;
    }
}

final class Linter
{
    public array $findings = [];
    public int $nodes = 0;

    public function __construct(private Vocab $vocab, private array $schema = []) {}

    private function add(string $level, string $code, string $path, string $msg, string $fix): void
    {
        $this->findings[] = compact('level', 'code', 'path', 'msg', 'fix');
    }

    public function lint(object $root, string $label): void
    {
        if (($root->type ?? '') === 'layout' && empty($root->version)) {
            $this->add('error', 'no-version', $label, 'root has no `version`',
                'add "version":"<theme version>" (copy it from `page get <id>`) or every element migration runs on save and rewrites props');
        }
        $this->walk($root, null, [], $label, false);
    }

    private function walk(object $node, ?object $parent, array $ancestors, string $path, bool $scoped): void
    {
        $this->nodes++;
        $type = $node->type ?? '';
        $el = $this->vocab->elements[$type] ?? null;
        $label = $type . (isset($node->name) ? " \"{$node->name}\"" : '');
        $here = $path === '' ? $label : "$path > $label";

        foreach (array_keys(get_object_vars($node)) as $k) {
            if (!in_array($k, ROOT_KEYS, true) && !str_starts_with($k, '_')) {
                $this->add('warn', 'unknown-key', $here, "node key `$k` is not part of the grammar", 'use type / name / props / children / source');
            }
        }
        if (!$el) {
            $this->add('error', 'unknown-type', $here, "element type `$type` does not exist in this theme", 'check packages/builder*/elements/ for the type name');
            return;
        }

        $props = (array) ($node->props ?? []);
        foreach ($props as $k => $v) {
            if (!isset($el['props'][$k])) {
                $near = $this->vocab->nearest($type, $k);
                $this->add('error', 'unknown-prop', $here, "`$k` is not a prop of `$type` — it is stored and emits nothing",
                    $near ? "did you mean `$near`?" : 'read packages/builder/elements/' . $type . '/element.php');
            }
        }

        if (str_ends_with($type, '_item')) {
            $want = substr($type, 0, -5);
            $ptype = $parent->type ?? '(root)';
            if ($ptype !== $want) {
                $this->add('error', 'orphan-item', $here, "`$type` sits under `$ptype`; its template receives \$element from a `$want` parent only — a TypeError 500s every page rendering it",
                    "wrap it: {\"type\":\"$want\",\"props\":{},\"children\":[…]}");
            }
        }

        $children = $node->children ?? [];
        if ($type === 'section' && empty($node->name)) {
            $this->add('warn', 'unnamed-section', $here, 'section has no `name`; it lists as a bare SECTION in the builder', 'set "name": "X1 · What it is"');
        }
        if ($type === 'section' && array_key_exists('background_color', $props) && ($props['style'] ?? 'default') !== '') {
            $this->add('warn', 'bgcolor-needs-empty-style', $here, '`background_color` is gated on `{@!style}` and the save re-adds `style: "default"`',
                'set "style": "" explicitly');
        }
        if (array_key_exists('block_align', $props) && empty($props['maxwidth'])) {
            $this->add('warn', 'block-align-no-maxwidth', $here, '`block_align` is enabled only with `maxwidth` — it emits nothing here',
                'set the COLUMN\'s `text_align` instead, or add `maxwidth`');
        }
        if ($type === 'row') {
            $cols = array_filter($children, fn($c) => ($c->type ?? '') === 'column');
            if (!empty($props['layout'])) {
                $groups = explode('|', (string) $props['layout']);
                $count = count(explode(',', end($groups)));
                if ($count !== count($cols)) {
                    $this->add('error', 'layout-count', $here, "`layout` \"{$props['layout']}\" declares $count columns; the row has " . count($cols),
                        'supply the missing column (an empty column is meaningful) or fix `layout`; with a mismatch the row stamps tm-grid-expand and stretches the lone column');
                }
            }
            if (count($cols) === 1 && empty($props['alignment'])) {
                $c = (array) (reset($cols)->props ?? []);
                $narrow = array_filter(['width_default', 'width_small', 'width_medium', 'width_large', 'width_xlarge'], fn($w) => isset($c[$w]) && $c[$w] !== '1-1');
                if ($narrow) {
                    $this->add('warn', 'lone-column', $here, 'one column, no row `alignment` → tm-grid-expand makes it fill the row despite its width',
                        'set "alignment": "center" (or "left") on the row');
                }
            }
        }
        if ($type === 'row' && ($parent->type ?? '') === 'column') {
            $this->add('warn', 'row-in-column', $here, 'a bare `row` inside a `column` renders but shows a broken icon in the builder tree',
                'nest through a `fragment` (Sublayout): column > fragment > row');
        }
        if ($type === 'grid') {
            foreach (['grid_default', 'grid_small', 'grid_medium', 'grid_large'] as $g) {
                if (isset($props[$g]) && ctype_digit((string) $props[$g]) && (int) $props[$g] > 6) {
                    $this->add('error', 'grid-over-6', $here, "`$g`: {$props[$g]} — UIkit child-width stops at 1-6; the grid falls back to the next breakpoint",
                        'use ≤ 6 columns, or a panel-slider with `slider_width: ""` for a marquee');
                }
            }
        }

        // bindings
        $source = $node->source ?? null;
        $q = $source->query ?? null;
        $qname = $q->name ?? null;
        if ($q) {
            if (isset($q->args) || isset($q->field->args)) {
                $this->add('error', 'binding-args', $here, 'the query key is `arguments`, not `args` — `args` is stored and ignored', 'rename to "arguments"');
            }
            if ($qname === '#parent' && !$scoped) {
                $this->add('error', 'parent-at-root', $here, '`#parent` with no bound ancestor resolves to nothing and renders EMPTY',
                    'bind the current item (`<base>.single<Type>`) here; `#parent` only inside an already-bound node');
            }
            // A container-level list query with no `field` sub-query is the listing mistake;
            // with a `field` (a repeater, the slice gate) the container is deliberately scoped.
            if ($qname && $qname !== '#parent' && !empty($el['container']) && count($children) === 1
                && ($children[0]->type ?? '') === "{$type}_item" && (($children[0]->source->query->name ?? '') === '#parent')
                && in_array($type, CONTAINER_PLURAL, true) && !isset($q->field) && !preg_match('/\.single[A-Z]/', $qname)) {
                $this->add('warn', 'list-on-container', $here, "the list query on the `$type` repeats the WHOLE $type once per record (one grid per post)",
                    "for a listing put the query on the `{$type}_item` and drop the container's source; keep this shape only for one $type per group");
            }
        }
        foreach ((array) ($source->props ?? []) as $prop => $bind) {
            $bname = $bind->name ?? '';
            if ($bname === 'featuredImage') {
                $this->add('warn', 'bare-featured-image', "$here [$prop]", '`featuredImage` is an Attachment OBJECT; bound bare it renders nothing', 'bind `featuredImage.url` (and `featuredImage.alt`)');
            }
            if ($prop === '_condition' && $this->schema) {
                $leaf = substr(strrchr('.' . $bname, '.'), 1);
                $ftype = $this->schema[$leaf] ?? null;
                if (in_array($ftype, ['repeater', 'relation', 'gallery'], true)) {
                    $this->add('warn', 'condition-on-list', $here, "`_condition` on `$bname` ($ftype) — applyCondition runs html_entity_decode on an ARRAY and removes the node on every record",
                        'gate with the source query + a slice directive of limit 1, and keep one _condition on a scalar sub-field');
                }
            }
        }

        $childScoped = $scoped || ($qname !== null && $qname !== '');
        foreach ($children as $i => $child) {
            if (is_object($child)) $this->walk($child, $node, [...$ancestors, $node], "$here > [$i]", $childScoped);
        }
    }
}

function read_layout(string $file): object
{
    $raw = file_get_contents($file);
    if ($raw === false) fail("cannot read $file");
    $d = json_decode($raw);   // never assoc: {} must stay {}
    if (!is_object($d)) fail("$file is not a JSON object");
    if (isset($d->layout) && is_object($d->layout) && !isset($d->children)) $d = $d->layout;   // a template envelope
    return $d;
}

function fail(string $msg): never
{
    fwrite(STDERR, "yoo-lint: $msg\n");
    exit(2);
}

function report(Linter $l, string $what): int
{
    $errors = 0; $warns = 0;
    foreach ($l->findings as $f) {
        $f['level'] === 'error' ? $errors++ : $warns++;
        printf("%-5s %-26s %s: %s → %s\n", $f['level'], $f['code'], $f['path'], $f['msg'], $f['fix']);
    }
    printf("yoo-lint: %d errors, %d warnings in %d nodes (%s)\n", $errors, $warns, $l->nodes, $what);
    return $errors ? 1 : 0;
}

// ---------------------------------------------------------------- arguments
if (defined('YOO_LINT_LIBRARY')) return;   // yoo-content.php includes the classes only
$argvIn = defined('WP_CLI') && WP_CLI ? ($args ?? []) : array_slice($_SERVER['argv'], 1);
$theme = null; $schemaFile = null; $files = []; $mode = null; $modeArg = null;
foreach ($argvIn as $i => $a) {
    $a = ltrim($a, '-');   // WP-CLI eval-file rejects --flags; accept the bare word too
    if (str_starts_with($a, 'theme=')) { $theme = substr($a, 6); continue; }
    if (str_starts_with($a, 'schema=')) { $schemaFile = substr($a, 7); continue; }
    if ($a === 'all') { $mode = 'all'; continue; }
    if (in_array($a, ['page', 'template'], true)) { $mode = $a; $modeArg = $argvIn[$i + 1] ?? null; continue; }
    if ($mode && $modeArg === $a) continue;
    $files[] = $a;
}
if ($theme === null && function_exists('get_template_directory')) $theme = get_template_directory();
if ($theme === null || !is_dir("$theme/packages/builder/elements")) fail('--theme=<parent theme dir> is required (a dir holding packages/builder/elements)');
$schema = $schemaFile ? (json_decode((string) file_get_contents($schemaFile), true) ?: []) : [];

$vocab = new Vocab(rtrim($theme, '/'));
$linter = new Linter($vocab, $schema);

if ($mode && !(defined('WP_CLI') && WP_CLI)) fail("`$mode` needs WordPress: run it as `wp eval-file yoo-lint.php $mode …`");

if ($mode === 'page' || $mode === 'all') {
    $rows = $GLOBALS['wpdb']->get_results("SELECT ID, post_name, post_content FROM {$GLOBALS['wpdb']->posts}
        WHERE post_status NOT IN ('auto-draft','inherit','trash') AND post_type NOT IN ('revision','nav_menu_item','attachment')");
    foreach ($rows as $r) {
        if ($mode === 'page' && (string) $r->ID !== (string) $modeArg && $r->post_name !== $modeArg) continue;
        if (preg_match('/<!--\s?(\{.*})\s?-->/s', (string) $r->post_content, $m) && ($lay = json_decode($m[1])) && is_object($lay)) {
            $linter->lint($lay, "page:{$r->post_name}#{$r->ID}");
        }
    }
}
if ($mode === 'template' || $mode === 'all') {
    $opt = json_decode((string) get_option('yootheme'), false);
    foreach ((array) ($opt->templates ?? []) as $id => $t) {
        if ($mode === 'template' && $id !== $modeArg) continue;
        if (isset($t->layout) && is_object($t->layout)) $linter->lint($t->layout, "template:$id " . ($t->name ?? ''));
    }
    if ($mode === 'all') {
        foreach ((array) ($opt->library ?? []) as $id => $lib) {
            if (isset($lib->layout) && is_object($lib->layout)) $linter->lint($lib->layout, "library:$id " . ($lib->name ?? ''));
        }
        $cfg = json_decode((string) get_theme_mod('config'), false);
        if (isset($cfg->footer->content) && is_object($cfg->footer->content)) $linter->lint($cfg->footer->content, 'footer');
        foreach ((array) ($cfg->menu->items ?? []) as $mid => $item) {
            if (isset($item->content) && is_object($item->content)) $linter->lint($item->content, "menu-item:$mid");
        }
        foreach ((array) get_option('widget_builderwidget', []) as $wid => $w) {
            if (!is_array($w) || empty($w['content'])) continue;
            $lay = is_string($w['content']) ? json_decode($w['content']) : json_decode(json_encode($w['content']));
            if (is_object($lay)) $linter->lint($lay, "widget:builderwidget-$wid " . ($w['title'] ?? ''));
        }
    }
}
foreach ($files as $f) $linter->lint(read_layout($f), basename($f));

$rc = report($linter, $mode ?: implode(', ', array_map('basename', $files)));
if (defined('WP_CLI') && WP_CLI) { if ($rc) \WP_CLI::halt(1); } else { exit($rc); }
