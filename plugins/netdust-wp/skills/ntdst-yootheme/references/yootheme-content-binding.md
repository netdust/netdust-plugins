# YOOtheme Dynamic Content — sources, bindings, and template routing

How data reaches a layout **without writing PHP**: an ntdst-core model declares the
fields, the ntdst-baseline `yootheme` module publishes them as a source, layouts bind to
that source, and templates decide which layout renders for which URL. The official
demos do the first step with ACF instead — read them for the binding and routing
idioms, never for the content model (see the aside in §1).

Verified against six official demos, the parent theme's `packages/builder-*-source`
code (5.0.43) and two live builds (josworld, edushare).

---

## The chain

```
ntdst-core model  (<project>-core, ntdst_data()->register(), meta_prefix set)
        ↓  ntdst-baseline yootheme module — opt-in, no per-project code
Source schema:  verhalen.customVerhalen → Verhaal { title, link, thema, featuredImage, … }
        ↓  node.source
Layout node:    grid_item bound to the query, props mapped to fields
        ↓  template.type + template.query
URL:            /inspirerende-verhalen/  →  archive-verhaal template
```

---

## 1. The content model is an ntdst-core model

Content types, fields and taxonomies are Data Manager models in `<project>-core`. The
ntdst-baseline `yootheme` module (≥ 2.3.0, opt-in by assignment) turns each declared
field into a picker entry; `references/yootheme.md` carries the enable step and the
full type table. What you bind, per declared type:

| ntdst-core type | Bind as |
|---|---|
| `text`, `textarea`, `html`, `email`, `url`, `select`, `date` | `<field>` |
| `int` / `float` / `bool` | `<field>` |
| `image`, `file`, `gallery` | `<field>.url`, `.alt`, `.caption`, `.thumbnail` — an `Attachment` object, never the bare field |
| `relation` | a list of the related type, published only — bind on a repeating item |
| `repeater` | container query `<single>.<field>` (+ a `slice` directive), item `#parent`, sub-fields by name |
| `array`, `json` | not published |

Field names bind by the bare schema key (`bio`, not `_jw_bio`). Only declared fields
exist; a model without a `meta_prefix` is refused whole.

> **Reading a demo package.** The official demos register every CPT and field through
> ACF (`acf-post-type`, `acf-field-group` posts), and YOOtheme's `builder-wordpress-acf`
> package maps the group's location rules onto the source. Choice fields arrive as
> `{ label, value }` objects, relations traverse (`field.event_place.field.street`),
> dates need the `date` filter. Use that knowledge to READ a demo's bindings; never
> propose ACF on a netdust build — it is not an option to weigh.

---

## 2. Source names — the rule, not a guess

From `Helper::getBase()` and the `*QueryType` classes:

```
base  = rest_base (if set and ≠ name), else name + "s";  dashes → underscores
group = camelCase(base)              →  match      → matches      → "matches"
                                        product_cat → product_cats → "productCats"
object type = PascalCase(name)       →  Match, ProductCat
```

Each group is assembled from up to four query types, so a group offers **more
than the `custom*` pair**:

| Contributor | Field | Offered in templates of type |
|---|---|---|
| `SinglePostQueryType` | `single` + PascalCase(name) — **the current item** | `single-<type>` |
| `CustomPostQueryType` | `custom` + PascalCase(name) (one) · `custom` + PascalCase(base) (list) | anywhere |
| `PostArchiveQueryType` (only if `has_archive`, or `post`) | the archive's own result set | `archive-<type>`, `author-archive`, `date-archive` |
| `PostSearchQueryType` (unless `exclude_from_search`) | the search result set | `search`, `_search` |

Taxonomies mirror this (`TaxonomyQueryType` + `TaxonomyArchiveQueryType`, the
latter scoped to `taxonomy-<tax>`).

> Each field carries `metadata.view`, which is why a query only appears in the
> template types it makes sense for. `singlePost` is not offered on an archive
> template — if a query you expect is missing from the dropdown, check you are
> editing the right template *type*.

So `source.query.name` reads `"<group>.<query>"`. Across six demo sites 72% of all
bindings are `#parent` — the repeat/inherit mechanism below is the thing to learn;
`site` (site-wide fields) and `customMenuItems` (a WP menu) are the root-level queries
worth knowing.

Built-in fields on any post type (`PostType.php`): `title`, `content`, `teaser`,
`excerpt`, `date`, `modified`, `metaString`, `categoryString`, `featuredImage`
(→ `.url`, `.alt`), `link`, `author`, `commentCount`, `post_name`, `id`, plus
`parent` / `children` and a field per attached taxonomy. WooCommerce adds
`woocommerce.price` and friends.

---

## 3. Binding a node

```json
{
  "type": "grid_item",
  "source": {
    "query": { "name": "#parent",
               "field": { "name": "announcements",
                          "arguments": { "limit": 1, "order": "date",
                                         "order_direction": "DESC" } } },
    "props": {
      "title": { "name": "title" },
      "link":  { "name": "link" },
      "image": { "name": "field.intro_image.url" },
      "meta":  { "name": "field.event_start_date",
                 "filters": { "date": "D, d.m.y" } }
    }
  }
}
```

* `source.query` — *what data*. `name` plus optional `arguments`, plus an
  optional `field` for a sub-query (with its own `arguments` and GraphQL-style
  `directives`, e.g. `{"name":"slice","arguments":{"offset":0,"limit":1}}`).
* `source.props` — *which field feeds which prop*. Keys are the element's own
  prop names; each maps to `{ name, filters }`.
* The argument key is **`arguments`**, never `args` — `SourceQuery::queryField` reads
  `$field->arguments`; an `args` key is stored and ignored (`yoo-lint.php`: `binding-args`).

Anything the element declares with `'source' => true` in its `element.php` can be
bound — including `image`, `video`, `link` and `style` on a section.

### The repeat pattern (`#parent`) — and which node carries the list

`SourceTransform::repeatSource` clones WHICHEVER node carries a list query. That gives
two shapes, and picking the wrong one counts correctly and arranges wrongly:

```
LISTING (one grid, one card per post — the common case)
grid                                            ← styling only, no source
  └─ grid_item  source.query = verhalen.customVerhalen     ← the list; the item repeats
                source.props = { title, link, image: featuredImage.url }

A GRID PER GROUP (the demos' "newest announcement per category")
grid            source.query = announcementCats.customAnnouncementCats   ← repeats the GRID
  └─ grid_item  source.query.name = "#parent"                            ← one item of it
                source.query.field = { name: "announcements", arguments: { limit: 1 } }
```

A list query on the `grid` produces one whole `<div class="uk-grid">` per post — four
single-card grids stacked vertically, every `uk-child-width-1-2@m` present and every
count assertion green (edushare, 2026-09-02). For a listing, **bind the item.**

`#parent` means "the current item of the enclosing scope". It works on non-repeating
elements too — a `headline` inside a bound column reads the current item — and sub-queries
nest: an item bound to `#parent` can pull a `field` off that item.

> **⚠ `#parent` at a template ROOT resolves to nothing, silently.** There is no
> enclosing scope, so the element renders **empty** — no error, no log line. At the root
> of a `single-<type>` template use the current-item query (`verhalen.singleVerhaal`,
> `posts.singlePost`); `#parent` is only for descendants of an already-bound node. An
> empty element is the symptom of a mis-scoped binding — check the query name before
> suspecting the data. `yoo-lint.php` reports it as `parent-at-root`.

### Conditional display — the `_condition` pseudo-prop

```json
"source": { "query": { "name": "#parent" },
            "props": { "_condition": { "name": "field.event_street",
                                       "filters": { "condition": "!" } } } }
```

`_condition` is not a real prop — a falsy result **removes the whole element**.
Wrap several elements in a `fragment` and condition the fragment to hide a block.

**It cannot gate a repeater or a relation.** `applyCondition` runs `html_entity_decode()`
on the value, so an ARRAY kills the node on every record, populated ones included. The
empty-state gate for a list field is the SOURCE QUERY: `resolveSource` drops any node
whose query resolves empty, so give the container the list query with a `slice` of
limit 1 and it repeats once when there is data and never when there is none — and keep
one `_condition` in `props`, because a source with a `query` and no `props` is inert:

```json
"source": {"query": {"name": "verhalen.singleVerhaal",
                     "field": {"name": "handige_links",
                               "directives": [{"name": "slice", "arguments": {"offset": 0, "limit": 1}}]}},
           "props": {"_condition": {"name": "label", "filters": {"condition": "!!"}}}}
```

Operators (`SourceFilter::applyCondition`), used with `condition_value`:

`!` empty · `!!` not empty · `=` · `!=` · `<` · `>` · `~=` contains ·
`!~=` · `^=` starts-with · `!^=` · `$=` ends-with · `!$=` · `regex`

### Filters

`packages/builder-source/src/Source/SourceFilter.php` registers exactly seven:

| Filter | Companion | Effect |
|---|---|---|
| `date` | — | PHP date format — `"d.m.Y"`, `"G:i A"`, `"D, d.m.y"` |
| `limit` | `preserve` | truncate to N chars; `preserve` keeps whole words |
| `search` | `replace` | `str_replace`, or **regex if the value starts with `/`** — `{"search":"/(wo)?men$/i","replace":""}` |
| `before` / `after` | — | prepend/append literal text — `{"before":"– "}`, `{"after":"&nbsp;"}` |
| `transform` | — | `mb_convert_case` mode (int) |
| `condition` | `condition_value` | see above |

`before`/`after` only apply when the value is non-empty, which makes them the
clean way to render `"– {subtitle}"` without a stray dash on empty records.

Three idioms worth stealing, straight from the demos:

```json
{"name": "field.phone",  "filters": {"before": "tel:"}}          // build a tel: link from a plain number
{"name": "field.email",  "filters": {"before": "mailto:"}}       // same for mail
{"name": "field.website","filters": {"search": "/https?:\\/\\/(www\\.)?/", "replace": ""}}
                                                                  // display a URL without its protocol
```

### Query arguments

List queries take a rich argument set (`CustomPostQueryType.php`):

```json
{ "offset": 0, "limit": 5,
  "order": "field:event_start_date", "order_direction": "ASC",
  "order_alphanum": false,
  "terms": [], "event_cat_operator": "IN", "event_cat_include_children": "include",
  "users": [], "users_operator": "IN",
  "date_range": "fixed",            // or "relative" / "custom"
  "date_column": "field:event_end_date",
  "date_start": "2025-01-01T00:00:00.000Z", "date_end": "2025-01-31T23:59:00.000Z",
  "date_relative": "next", "date_relative_unit": "day" }
```

Note `order: "field:<name>"` and `date_column: "field:<name>"` — sort and date-filter on a
custom field with no code. On ntdst-core models the value is the STORED meta key
(`_edushare_in_de_kijker`), because `Helper.php` passes it to `meta_key` verbatim.

---

## 4. Templates — routing a URL to a layout

Templates live in the `yootheme` option (see `yootheme-site-model.md`). Each has
`type`, `name`, `layout`, optional `query`, `status`, `params`.

### Types

| Type | Matches |
|---|---|
| `single-<post_type>` | a single post of that type |
| `archive-<post_type>` | the post type archive |
| `taxonomy-<taxonomy>` | a term archive |
| `date-archive` | date archives (`query.archive`: `day`\|`month`\|`year`\|`time`) |
| `author-archive` | author archives |
| `search` | the search results page |
| `_search` | **live search** results (the header dropdown, rendered via AJAX) |
| `error-404` | 404 |

### Matching — first hit wins

`packages/builder-templates/src/TemplateHelper.php`:

```php
foreach ($this->templates as $id => $template) {
    if (($template['status'] ?? '') === 'disabled') continue;
    if (empty($template['type']) || $template['type'] !== $view['type']) continue;
    if (isset($view['query']) && !static::matchQuery($template, $view['query'])) continue;
    return ['id' => $id] + $template;      // ← FIRST match, then stop
}
```

and `matchQuery` treats an **empty condition as a wildcard**:

```php
foreach ($query as $key => $value) {
    if (empty($template['query'][$key])) continue;              // not constrained
    if (!array_intersect((array) $value, (array) $template['query'][$key])) return false;
}
```

Three rules follow, and they are the whole game:

1. **Order is priority.** Templates are matched in stored order. The Customizer's
   template list is drag-sortable (`POST /builder/template/reorder`) — that
   ordering *is* the routing table.
2. **A template with `query: []` is the catch-all** for its type. It must sit
   **after** every specific one, or it swallows them. Woolberry stores three
   category-specific `single-post` templates at indexes 0, 5 and 7, and the
   generic "Post" at index 9.
3. **`status: "disabled"` parks a template** without deleting it.

### Query conditions

```json
{ "terms": [20] }                                        // only these term IDs
{ "terms": [23,43,61], "include_children": "only" }      // only child terms of these
{ "category_include_children": "include" }               // per-taxonomy variant
{ "terms_filter": [76] }                                 // matches a filter term
{ "pages": "first" }  /  { "pages": "except_first" }     // paginated archives
```

`pages` is how FC Greenfield gives page 1 of the blog a hero and pages 2+ a plain
grid — two `archive-post` templates, same type, split on `pages`.

### `params`

Per-template query overrides. In practice `posts_per_page`:

```json
"params": { "posts_per_page": 14 }
```

Woolberry sets 12 for product archives, 14 for curated collections, 20 for
search, 50 for live search. This is the supported way to change archive page
size per template — not `pre_get_posts`.

---

## 5. Design guidance

**Templates scale, pages don't** — "a page for each X" is one CPT, one `archive-` and one
`single-` template, plus specific templates layered in front for categories that differ.
**Variants are templates, not conditionals**: several templates of one type ordered by
specificity, with `_condition` reserved for field-level presence. Nothing validates the
order — after adding a template, re-check that the catch-all is still last.

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Write a source service for a model's fields | Enable the baseline `yootheme` module; the fields appear |
| Bind `featuredImage` or an `image` field bare | `.url` — media fields are `Attachment` objects |
| Put the list query on the `grid` for a listing | Bind the `grid_item`; the container repeats only when you want a grid per group |
| Add a catch-all template and leave it first | Catch-all (`query: []`) goes last; order is the routing table |
| `pre_get_posts` to change archive page size | `params.posts_per_page` on the template |
| One template + a wall of `_condition` | Several templates ordered by specificity |
| Hand-format dates in the field | `filters.date` on the binding |
| Concatenate a separator into a field | `filters.before` / `after` — they no-op when empty |
| Gate a repeater/relation with `_condition` | The source query + a `slice` directive is the gate |
| Delete a template you might want back | `status: "disabled"` |
