# Golden Path — YOOtheme integration (a model's fields in the builder)

> **Verified against source: 2026-09-02** — edushare `edushare-core.php` (the opt-in),
> `ntdst-baseline` 2.3.0 `services/yootheme/*` (the module), and the live picker on
> `edushare.ddev.site`. Re-verify when ntdst-baseline's yootheme module changes;
> `/skill-audit` flags this after 90 days.

**Read this before planning anything that puts ntdst-core content into a YOOtheme layout.**
The whole slice is two things: enable the module, then bind. A project that writes its
own source service for ntdst-core fields is drift since ntdst-baseline 2.3.0 (the
framework skill's `baseline.md` says so) — the shape below replaces the Rossi-era
Rossi-era per-project source service + theme-level engine pair that used to live here.

---

## File inventory of the slice

| File | Responsibility |
|---|---|
| `<project>-core/<project>-core.php` | the opt-in filter, by assignment |
| `<project>-core/services/content/<Type>Service.php` | the model, declared through `ntdst_data()->register()` with a non-empty `meta_prefix` |
| the `yootheme` option / `post_content` | the layouts that bind — written through `ntdst-yootheme/scripts/yoo-content.php` |

No resolver, no `objectType`, no `source.init` listener.

## 1. Enable — `<project>-core.php`

```php
// Assignment, never `$modules + ['yootheme' => true]`: the union operator keeps the
// existing key, and the module's default IS a key, so the union form changes nothing.
add_filter('ntdst/baseline/modules', static function (array $modules): array {
    $modules['yootheme'] = true;
    return $modules;
});
```

Verify in the builder: any element → Dynamic Content → the model's group is listed,
repeater sub-fields included.

## 2. Bind — a listing and a single

Listing: the list query goes on the ITEM, and the item repeats.

```json
{"type":"grid","props":{"grid_medium":"2","panel_style":"card-default"},
 "children":[{"type":"grid_item",
   "source":{"query":{"name":"verhalen.customVerhalen",
                      "arguments":{"limit":6,"order":"date","order_direction":"DESC"}},
             "props":{"title":{"name":"title"},"link":{"name":"link"},
                      "image":{"name":"featuredImage.url"},
                      "meta":{"name":"themaString"}}}}]}
```

Single (in a `single-verhaal` template): the root binds the current item, never `#parent`.

```json
{"type":"headline","props":{"title_element":"h1","title_style":"h2"},
 "source":{"query":{"name":"verhalen.singleVerhaal"},"props":{"content":{"name":"title"}}}}
```

Query names derive from the post type (`Helper::getBase()`); the four worked examples and
the field table are in `ntdst-yootheme/references/yootheme.md`.

## 3. The escape hatch — only for a query the built-in arguments cannot express

`custom<Base>` already takes offset/limit/order/terms/date ranges. When a curated set is
genuinely needed, register a `queryType` returning the module's type through a top-level
function referenced by its literal name — the code block lives in
`ntdst-yootheme/references/yootheme.md` and is the only PHP this path allows.

---

## How to adapt — what changes per project, what never does

**Changes per project:** the model (fields, prefix), the query names (derived), the layouts.

**Never changes:**
- The opt-in is an assignment on `ntdst/baseline/modules`; pin `netdust/ntdst-baseline ^2.3`.
- No `objectType()`, no per-project source service, no resolver unless the escape hatch applies.
- A `meta_prefix` is declared, or the model is refused whole.
- Bindings use bare schema keys; `featuredImage` and every media field bind through `.url`.
- Layouts are written through `yoo-content.php` and linted with `yoo-lint.php` first.

## Cross-references

- `ntdst-yootheme/references/yootheme.md` — the type table, query naming, the escape hatch.
- `ntdst-yootheme/references/yootheme-content-binding.md` — `#parent`, `_condition`, filters, template routing.
- `ntdst-framework/references/baseline.md` — the module's contract and version floor.
