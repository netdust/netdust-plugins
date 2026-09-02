# Data reaches the builder — the ntdst-baseline `yootheme` module

On this fleet a content type is an ntdst-core Data Manager model in the project's
`<project>-core` mu-plugin. YOOtheme cannot see its fields on its own: the parent
discovers post meta through its ACF package only. The bridge is the **`yootheme` module
of `netdust/ntdst-baseline` (≥ 2.3.0)** — it registers every model as a builder source, so
binding a field is layout work, not PHP. Authoritative description:
`netdust-wp:ntdst-framework` → `references/baseline.md` § "The yootheme module". This
file adds only the builder-side facts.

## Enable it — one filter, by assignment

```php
add_filter('ntdst/baseline/modules', static function (array $modules): array {
    $modules['yootheme'] = true;   // never `$modules + ['yootheme' => true]`
    return $modules;
});
```

The module is the one baseline module that is OFF by default. The union operator keeps
the existing key, and the default IS a key — so `+ [...]` reads as "enable" and changes
nothing. Pin `^2.3`: 2.2.0 booted after models registered and collected nothing; 2.2.1
wrote `name`/`resolve` where YOOtheme reads `label`/`func`.

**Verify the opt-in in the builder, not in code**: open any element's Dynamic Content
picker and look for the model's group. Stefan confirms it there (edushare, 2026-09-01).

## What a declared field becomes

| ntdst-core type | In the picker | Bind as |
|---|---|---|
| `text`, `textarea`, `html`, `email`, `url`, `select`, `date`, … | `String` | `<field>` |
| `int`, `float`, `bool` | `Int` / `Float` / `Boolean` | `<field>` |
| `repeater` | `listOf` of an emitted row type | container query `<single>.<field>` → item `#parent`, sub-fields by name |
| `relation` | `listOf` of the related post type, **published posts only** | `<field>` as a list; drafts never surface |
| `image`, `file`, `gallery` | YOOtheme's own `Attachment` (+ `thumbnail`/`medium`/`large`) | `<field>.url`, `.alt`, `.caption`, `.thumbnail` |
| `array`, `json` | **not mapped — dropped** | a missing field is a question an editor asks; "Array" on a page is one a visitor sees |

Two boundaries the module enforces: only DECLARED fields are exposed (undeclared meta is
unreachable), and a model whose `meta_prefix` is empty is refused whole. Field names bind
by their bare schema key (`bio`, `email`) — never the stored `_prefix_` key. The one
exception today: `order: "field:<name>"` in a query argument reaches `meta_key` verbatim,
so it needs the STORED key (`_edushare_in_de_kijker`); a bridge for that is an
ntdst-baseline gap, not something to work around in a template.

## Query names are derived, not chosen

`Helper::getBase()` in `builder-wordpress-source`: the group is `rest_base`, unless it is
empty or equal to the post type name — then `name . 's'`. Dashes become underscores, the
group is camelCased, the type is PascalCased.

| post type | `rest_base` | list query | single (in `single-<type>` templates) |
|---|---|---|---|
| `case` | `cases` | `cases.customCases` | `cases.singleCase` |
| `team` | `team` (= name) | `teams.customTeams` | `teams.singleTeam` |
| `tool` | — | `tools.customTools` | `tools.singleTool` |
| `verhaal` | `verhalen` | `verhalen.customVerhalen` | `verhalen.singleVerhaal` |

Read the live schema rather than inferring when in doubt:

```bash
wp eval 'print_r(array_keys(\YOOtheme\app(\YOOtheme\Builder\Source::class)->getSchema()->getType("Verhaal")->getFields()));'
```

Built-in fields on every post type (`PostType.php`): `title`, `content`, `teaser`,
`excerpt`, `date`, `modified`, `link`, `author`, `id`, `post_name`, `featuredImage`
(an `Attachment` OBJECT — bind `featuredImage.url` and `featuredImage.alt`; the bare
object renders nothing), `<taxonomy>String` (a LINKED term list, see lessons), `parent`,
`children`.

## The escape hatch — a curated query, when the built-in list is not enough

The built-in `custom<Base>` query already takes `offset`, `limit`, `order`,
`order_direction`, `terms`, date ranges. Write PHP only for a query those arguments cannot
express (a computed set, a cross-type union). Register a `queryType` that returns the
type the module already made — never an `objectType` of your own — and reference the
resolver as a top-level function by its literal namespaced name (YOOtheme stores the
callable NAME in its serialized schema; closures and methods white-screen the Customizer):

```php
namespace edushare\core;

add_action('after_setup_theme', static function (): void {
    if (!function_exists('YOOtheme\app')) {
        return;                                            // parent theme absent → inert
    }
    \YOOtheme\Event::on('source.init', static function ($source): void {
        $source->queryType(['fields' => [
            'featuredVerhalen' => [
                'type'       => ['listOf' => 'Verhaal'],          // the module's type
                'metadata'   => ['label' => 'Uitgelichte verhalen', 'group' => 'Verhalen',
                                 'fields' => ['limit' => ['label' => 'Limit', 'type' => 'number', 'default' => 3]]],
                'extensions' => ['call' => ['func' => 'edushare\\core\\resolve_featured_verhalen']],
            ],
        ]]);
    }, -10);                                               // krsort: -10 runs AFTER the module's types
}, 30);

function resolve_featured_verhalen($root, array $args): array
{
    return ntdst_data()->get('verhaal')->where('in_de_kijker', true)
        ->orderBy('date', 'DESC')->limit((int) ($args['limit'] ?? 3))->getRaw();
}
```

`metadata.label` / `metadata.group` nest under `metadata` — a top-level `label` is
ignored and the picker shows the raw key. Registering an `objectType` under a name the
module already uses MERGES into it (`SchemaBuilder::objectType()` reuses the type), so a
computed field can also ride on the built-in `single<Type>` query with no query of its own.

## Asset control — YOOtheme ignores `wp_dequeue_*`

The parent enqueues through its own Metadata system. To strip one of its assets, hook
`wp_head` / `admin_print_scripts` at priority 5 and remove it there (Rossi's
`YOOthemeAssetControlService` is the reference). A `wp_dequeue_script` call does nothing.
