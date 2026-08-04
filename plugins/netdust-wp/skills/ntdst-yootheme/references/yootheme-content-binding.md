# YOOtheme Dynamic Content — sources, bindings, and template routing

How data reaches a layout **without writing PHP**. This is the half the official
demos are built on: ACF defines the content model, YOOtheme auto-generates a
queryable source from it, layouts bind to that source, and templates decide which
layout renders for which URL.

Write PHP only when this runs out — see `yootheme.md` + SKILL.md for custom
sources. Verified against six official demos and the parent theme's
`packages/builder-*-source` code.

---

## The chain

```
ACF post type / taxonomy / field group
        ↓  auto-registered, no code
Source schema:  matches.customMatches → Match { title, link, field.match_date, … }
        ↓  node.source
Layout node:    grid_item bound to the query, props mapped to fields
        ↓  template.type + template.query
URL:            /matches/  →  archive-match template
```

---

## 1. The content model is ACF

Every CPT, taxonomy and field in the demos is registered through **ACF's own UI**
and stored as posts — `acf-post-type`, `acf-taxonomy`, `acf-field-group`,
`acf-field`. There is no custom plugin and no `register_post_type()` call.
FC Greenfield: 3 post types, 5 taxonomies, 6 field groups, 49 fields. Oakville:
8 post types.

YOOtheme picks them up automatically (`packages/builder-wordpress-acf/`):
`AcfHelper::matchGroup()` maps a field group's **location rules** onto the source
type — `post_type ==` → that CPT, `taxonomy ==` → that taxonomy, plus `user`,
`attachment` and `options_page`.

> **Consequence:** a field only appears in the builder if its group's location
> rule matches. A group scoped to a specific post *template* or *page* will not
> surface as a type-wide field. If a field is missing from the Dynamic Content
> dropdown, check the location rule first.

### ACF field type → what you bind

`packages/builder-wordpress-acf/src/Type/FieldsType.php`:

| ACF type | Source shape | Bind as |
|---|---|---|
| `text`, `textarea`, `wysiwyg` | `String` (+ `limit`, `preserve` filters) | `field.subtitle` |
| any field with `choices` (`select`, `radio`, `checkbox`, `button_group`) | `{ label, value }` | `field.match_type.value` / `field.match_round.label` |
| `image` | Attachment | `field.intro_image.url`, `.alt`, `.caption` |
| `file` | File field | `field.brochure.url` |
| `link` | `{ title, url }` | `field.cta.url`, `field.cta.title` |
| `date_picker`, `date_time_picker`, `time_picker` | `String` + `date` filter | `field.event_start_date` |
| `post_object`, `relationship` | the **related type** (or `listOf` if multiple) | `field.event_place_place.field.place_authority_street` |
| `repeater`, `group`, `flexible_content` (sub_fields) | nested object / `listOf` | `field.images` → bind items |
| `google_map` | `{ coordinates, … }` | `field.place_authority_location.coordinates` |
| multi-value text | `listOf ValueField` → `{ value }` | `field.tags.value` |

Two rules worth memorising:

* **Choice fields are objects, not strings.** `field.match_type` alone gives you
  nothing; you want `.value` (the stored key) or `.label` (the display text).
  This is the single most common "why is my field empty".
* **Relations traverse.** A `post_object` field resolves to the related type, so
  you can chain: `field.event_place_place.field.place_authority_street`. Oakville
  does this to print a venue's address on an event. Set ACF's `bidirectional` on
  the field if you need the reverse too (FC Greenfield's match↔team).

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

So `source.query.name` reads `"<group>.<query>"`. Counts from the six demos
(1,781 bound nodes total):

| Seen in demos | Count | Means |
|---|--:|---|
| `#parent` | 1274 | **the item from the enclosing repeat scope** |
| `posts.singlePost` | 79 | the post being viewed (in a `single-post` template) |
| `matchCats.customMatchCat` | 33 | one specific `match_cat` term |
| `events.customEvents` | 32 | a configured list of `event` posts |
| `customMenuItems` / `customMenuItem` | 21 / 18 | WP nav-menu items (root-level query) |
| `search` | 21 | the search result set |
| `teams.singleTeam`, `products.singleProduct` | 18 / 16 | current item in their `single-*` templates |
| `site` | 12 | site-wide fields (name, URL, …) |

77 distinct queries appear across the six sites. **`#parent` is 72% of all
bindings** — the repeat/inherit mechanism below is the thing to learn.

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

Anything the element declares with `'source' => true` in its `element.php` can be
bound — including `image`, `video`, `link` and `style` on a section.

### The repeat pattern (`#parent`)

This is how every dynamic listing in the demos works:

```
grid            source.query = announcementCats.customAnnouncementCats   ← the LIST
  └─ grid_item  source.query.name = "#parent"                            ← one ITEM
                source.props = { title: …, link: … }
```

The **container** carries the list query and repeats its single child. The
**child** binds to `#parent`, meaning "the current item of the enclosing scope".
Style the container, bind the item. Sub-queries nest: an item bound to `#parent`
can pull a `field` off that item (as above — the newest announcement *within*
each category).

`#parent` also works on non-repeating elements — a `headline` inside a bound
column just reads the current item.

> **⚠ `#parent` at a template ROOT resolves to nothing, silently.** There is no
> enclosing scope to inherit, so the element renders **empty** — no error, no
> warning, no log line. At the root of a `single-<type>` template use the current-item
> query (`posts.singlePost`, `products.singleProduct`, …); `#parent` is only for
> descendants of an already-bound node. Verified on a live install: a root
> `headline` bound to `#parent` produced no output at all, and swapping it to
> `posts.singlePost` rendered immediately. **An empty element is the symptom of a
> mis-scoped binding** — check the query name before suspecting the data.

### Conditional display — the `_condition` pseudo-prop

```json
"source": { "query": { "name": "#parent" },
            "props": { "_condition": { "name": "field.event_street",
                                       "filters": { "condition": "!" } } } }
```

`_condition` is not a real prop — a falsy result **removes the whole element**.
Wrap several elements in a `fragment` and condition the fragment to hide a block.

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

By frequency across the six sites: `condition` 455 uses, `before`/`after` ~150,
`date` ~120, `search` ~60. Conditional display is the single most-used filter —
see `_condition` above.

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

Note `order: "field:<acf_field>"` and `date_column: "field:<acf_field>"` — you can
sort and date-filter on ACF fields, which is what makes an events listing work
without code.

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

## 5. Design guidance from the demos

**Templates scale, pages don't.** Oakville renders a municipal portal from
5 pages + 35 templates; Glowbar is a brochure with 13 pages + 4 templates. When
a request sounds like "a page for each X", the shape is usually one CPT, one
`archive-` template, one `single-` template — plus specific templates layered in
front for the categories that need to look different.

**Variants are templates, not conditionals.** Rather than one template full of
`_condition` blocks, the demos ship several templates of the same type ordered
by specificity — "Post 2 Columns" / "Post Gallery" / "Post Sections" / "Post".
Reserve `_condition` for field-level presence checks (hide the address line when
there's no address), not for whole-layout branching.

**Order-by-specificity is fragile by construction.** Nothing validates it. After
adding a template, re-check that the catch-all is still last.

---

## Anti-patterns

| ❌ Don't | ✅ Do |
|---|---|
| Write PHP for a CPT the client will edit | ACF post type + field group; YOOtheme picks it up |
| Bind `field.my_select` | `.value` (key) or `.label` (display) — choice fields are objects |
| Bind the `grid` when you meant each card | List query on the container, `#parent` on the `_item` |
| Add a catch-all template and leave it first | Catch-all (`query: []`) goes last; order is the routing table |
| `pre_get_posts` to change archive page size | `params.posts_per_page` on the template |
| One template + a wall of `_condition` | Several templates ordered by specificity |
| Hand-format dates in the field | `filters.date` on the binding |
| Concatenate a separator into a field | `filters.before` / `after` — they no-op when empty |
| Assume a field group appears everywhere | It surfaces only where its ACF **location rule** matches |
| Delete a template you might want back | `status: "disabled"` |
