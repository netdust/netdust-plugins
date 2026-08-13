---
name: ntdst-data
description: >
  Use when planning, designing, implementing, or reviewing data models, custom
  post types, taxonomies, field definitions, metaboxes, API actions, database
  queries, or CRUD operations in an NTDST WordPress project. Triggers on
  phrases like "register a CPT", "add a custom post type", "add a taxonomy",
  "add a field to the model", "add a metabox", "add an api_data action", "an
  AJAX endpoint", "expose this publicly", "query the model", "add a repository
  method", "why is this returning WP_Error", "why is this meta key empty", and
  on the keywords `ntdst_data`, `ntdst_api_action`, `NTDST_Data_Model`,
  `NTDST_Data_Manager`, `NTDST_MetaboxGenerator`, `public_fields`,
  `meta_prefix`, `withMeta`, `WP_COLUMNS`, `ntdst/api_data`,
  `ntdst/api/public_actions`. Also use when deciding whether an action may be
  reached anonymously, or what capability should gate it. Activates alongside
  ntdst-architecture for data work.
---

# NTDST Data Layer

**This skill carries decisions and traps, not an API listing.** Method names and signatures live in
`api/Data.php`, `api/Endpoints.php` and `admin/MetaboxGenerator.php`, where they cannot drift. Decide
the case here, build from the golden path, then read source for the exact call.

**`ntdst-core` is a per-project fork with no shared upstream** — see `ntdst-architecture` for the
divergence table. Confirm a method exists in *this project's* copy before calling it. Where this file
says "HEAD", it means daan's copy, which is the most-evolved on Data, Endpoints, Theme and Metabox.

## The mechanical rules are a gate, not prose

Everything a grep can decide — raw meta calls, raw post writes, repository bypasses, `ob_start()`
rendering, raw `wp_ajax_*`, raw `ntdst/api_data` filter registration, direct
`register_post_type()`/`register_taxonomy()`, hardcoded meta prefixes, wrong Data API vocabulary,
unprepared `$wpdb`, `permission_callback => __return_true` — is enforced by:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py"            # staged files
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py" --since HEAD~1
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py" path/to/module
```

**Run it before you close a task that touched PHP.** A deliberate exception is annotated on the line,
with a reason, and stays greppable:

```php
// ntdst-allow: raw-meta — DISTINCT meta column for the admin filter dropdown; no Data API terminal
```

An allow with no reason is itself a finding. Don't re-argue a gated rule in prose — fix it or
annotate it. This gate exists because accuracy was never the binding constraint: across 13 consumer
projects, **13 of 13** hand-roll `get_post_meta()`/`get_posts()` with the framework and its docs
sitting right there.

---

## Start here — build to the worked slice

**`golden-paths/model-and-api-action.md`** is the complete vertical slice: a CPT with typed fields, a
taxonomy, an auto-generated metabox, an anonymous read action, and a capability-gated write action.
Open it and build to it rather than assembling from the rules below. It carries a
`Verified against source:` date so staleness is visible instead of silent.

**The recipes**, when you only need the door:

| To do this | Call this |
|---|---|
| Register a CPT with fields | `ntdst_data()->register($name, $config)` — check the return for `WP_Error` |
| Attach a taxonomy | the `taxonomies` key inside that same config, with optional `terms` to seed |
| Get an auto metabox | declare `fields`; it is generated. `'auto_metabox' => false` opts out |
| Register an API action | `ntdst_api_action($action, $handler, $opts)` |
| Make an action reachable logged-out | `$opts = ['public' => true]` |
| Floor an action by capability | `$opts = ['cap_type' => $post_type]` — type-derived, fail-closed |
| Read one record | `$model->find($id)` → `WP_Post`-shaped **object**, or `WP_Error` |
| Read a list | `$model->where(...)->withMeta()->limit(...)->get()` → **arrays of arrays** |
| Emit the declared public shape | `->publicRows()` / `->publicRow($id, $status)` |
| Write | `$model->create($data)` / `->update($id, $data)` — friendly keys, check `is_wp_error()` |
| Check a model exists without creating one | `ntdst_data()->isRegistered($name)` |

The rules below decide the cases the recipes don't cover.

## The four rules that do not change

1. **No raw SQL, no direct meta.** All persistence goes through the data layer, and CPT access goes
   through that domain's repository — the single mediator. `ntdst_data()->get('type')` should appear
   in exactly one file per post type.
2. **`WP_Error` on failure, and never swallowed.** Every create/update/delete result is
   `is_wp_error()`-checked. A swallowed error is invisible data loss; that is exactly how a silent
   save bug survived in production.
3. **Friendly key vocabulary, not `wp_posts` column names.** Pass `title`, `content`, `excerpt` —
   not `post_title`. The canonical accepted set is `NTDST_Data_Model::WP_COLUMNS` (16 columns).
4. **`post_status`, never `status`.** A field literally named `status` is common, and the collision
   silently sends a post-table value into meta.

## What changed on 2026-08-07 / 08 — read this if you are reading older code

Each row is a **narrowing you should not undo**. Older forks still carry the "was" column.

| | now | was |
|---|---|---|
| `->withMeta()` row meta | schema-projected: **unprefixed**, type-cast, declared fields only | raw bag: **prefixed**, every meta row |
| `getMeta($id, …)` | publish-only by default; 4th arg `$status`, same as `find()` | `find($id, 'any')` — read drafts silently |
| public actions shipped by the framework | **none** — the public list is empty | `get_recent_posts`, `search_posts`, `send_magic_link` |
| `search_posts` | retired → `relation_search` on `NTDST_RelationField`, non-public | present, and public |
| `getFormattedPosts()` on a protected post | withholds `content`/`excerpt`, sets `protected` | served the body a post password withholds |
| CPT / taxonomy / API-action registration | `ntdst_data()->register()`, its `taxonomies` key, `ntdst_api_action()` | `$theme->register()` / `->taxonomy()` / `->apiAction()` |
| metabox + relation field | `admin/MetaboxGenerator.php`, `admin/RelationField.php` | `api/MetaboxGenerator.php`, `services/RelationField.php` |
| page rendering | `NTDST_Template_Loader::page()` / `::pageData()`; `ntdst_page_data()` **survives** | `NTDST_Response::page()` / `::pageData()` / `::toRestResponse()` |
| query cache | **deleted** — `$model->cache(N)`, `ntdst_query_cache()`, `ntdst_clear_posts_cache()`, `ntdst_invalidate_post_type()`, `ntdst_get_posts_fast()` all gone | present |

**Still verify against this project's own `api/Data.php` and `api/Endpoints.php` before writing.**
This skill is a map, not the territory — it drifted from the code for six weeks (2026-06-23 →
2026-08-06) describing a deleted API, and the fix is always to read the source.

## Registration decisions

- **Private by default. Silence is not privacy.** Registration merges your config over
  `public => false, has_archive => false`; a model opts **in** to visibility. The old default merged
  caller config *over* `public => true`, so a model registered without visibility flags was
  published, archived and queryable — which is why every non-public CPT had to state six denials by
  hand, and why forgetting one was a disclosure. **Opt IN to public; never opt out of it.**
- **A failed registration is returned, never swallowed.** `register_post_type()` returns `WP_Error`
  for an invalid or reserved name. Older code discarded it and built the model anyway, leaving a
  half-registered phantom that reports healthy: `isRegistered()` true while `post_type_exists()`
  false. Fail closed, and loudly.
- **Taxonomies are declared with the model**, via the `taxonomies` config key, and are registered
  only after the post type succeeds. (`NTDST_Data_Manager::registerTaxonomy()` is the direct door for
  a taxonomy with no owning model.) The `Theme::taxonomy()` wrapper that used to hold these defaults
  is retired — a taxonomy outlives a theme switch, so it was never Theme's job — and its defaults
  were lifted verbatim, so changing them changes every taxonomy that relied on the wrapper.
- **Asking about a model must not create one.** In HEAD, a lookup miss returns an error; it used to
  auto-register a phantom into a *static* array, so a caller-supplied type name on a public endpoint
  could register whatever it liked, and nothing could tell a real model from someone's typo. Use
  `isRegistered()`, never the getter, when iterating post types.
- **A custom `capability_type` grants nothing.** `map_meta_cap` *maps* meta capabilities onto
  primitives; it never *invents* primitives. Giving a type its own capability names produces
  capabilities held by no role at all — administrator included. Grant them on `init`, reading the
  list off the registered post-type object. The golden path has the worked version.
- **Metaboxes are generated from the field definitions**, and they live in `admin/` — admin UI, not
  transport. That directory owns the **write-authorization gate**: whether an actor may write a
  model's fields is decided in the metabox save method, and read access to its error notices is
  gated by the same predicate so read ⊆ write by construction.

## Query and return-shape decisions

- **`find()` returns an object; `get()` returns arrays of arrays. Mixing them is the most common bug
  in this layer.** Array-accessing a `find()` result is a fatal.

  | Method | Returns | Access |
  |---|---|---|
  | `find($id)` | `WP_Post` (with `->meta`, `->fields`) or `WP_Error` | `$post->post_title`, `$post->fields['key']` |
  | `first()` | `WP_Post`, same shape, or `null` | `$post->post_title`, `$post->fields['key']` |
  | `get()` | array of associative arrays; `meta` is **schema-projected** | `$rows[0]['title']`, `$rows[0]['meta']['declared_field']` |
  | `count()` | `int` | — |
  | `paginate()` | `['data' => [...], 'pagination' => [...]]` | — |

- **`find($id, $status = 'publish')` — the second argument is a post status, and publish-only is the
  safe default.** It used to be a `bool $skipCache`; a leftover `find($id, true)` would have quietly
  meant "accept the status `true`", matching nothing and denying every row, so it now **throws**.
  *Fail-closed-but-invisible is the worst shape available* — this is what it looks like when fixed.
  Pass an explicit status when you genuinely want unpublished rows; an admin screen does, a public
  read does not. **Authorization is the caller's job**; the layer applies the status you asked for
  and decides nothing else.
- **A not-found row and a wrong-status row return the same `WP_Error`** — a caller who may not see
  this status learns nothing about whether it exists. Remember it when writing a denial test: assert
  the row is REACHABLE first, or your denial may be passing because the fixture never existed.
- **Batch-loaded meta is schema-projected, so drop the prefix.** `get()` / `all()` / `paginate()`
  project each row's `meta` through the declared schema — **unprefixed, type-cast, declared fields
  only**, the same set `find()->fields` reports. `$row['meta'][$prefix . 'date']` now returns null
  **silently**, and a filter or sort built on it fails OPEN. Read `$row['meta']['date']`. Never
  hardcode `_ntdst_` either way. Older forks still return the raw prefixed bag — check that project's
  `api/Data.php` before porting a reader.
- **Rollback is best-effort, not a transaction.** Create deletes the new post if a meta write fails;
  update snapshots prior post and meta state and restores on failure. This is application-level, not
  a DB transaction — for critical multi-table paths (capacity locks, voucher counts) still wrap the
  business operation in an explicit SQL transaction.
- **`update_post_meta()` returns `false` both for errors and for unchanged values.** The layer treats
  unchanged as success, so re-saving an identical value does not trigger a spurious rollback. Any
  code you write against raw meta must make the same distinction or it will invent failures.
- **There is no query cache in HEAD**, and its absence is a security property. A layer-owned cache is
  one core does not invalidate, so a write that bypassed the model could leave a stale value being
  served — for a revocation flag, a revoked credential still reading as live. WordPress's own post /
  `post_meta` / term caches are the caching, and core invalidates them on any write, whoever
  performed it. **Do not reintroduce a bespoke cache over post meta** without solving that, and do
  not write invalidation hooks for a cache this copy does not have.

### Traps

- **Unknown keys are logged and dropped, not written.** A writer using the wrong vocabulary shows up
  as `_ntdst_post_*` keys in a meta dump and as warnings in the data log. Zero warnings after a
  refactor is the proof the vocabulary is right.
- **An unknown *field type* throws at registration.** It used to fall through to
  `sanitize_text_field` silently, which is how a `wysiwig` typo quietly stripped a field's markup with
  nothing failing. Several types were also *advertised but never sanitised* until this was fixed — a
  helper that accepts a type name and then ignores it is lying about its own vocabulary. Read the
  exception message for the accepted set; it is the authoritative list.
- **Repeater rows are read back largely as stored.** Sub-fields are sanitized on write, but a
  top-level allow-list projection does **not** filter sub-keys. If you project a payload for
  anonymous callers, project the repeater's rows too, or an undeclared sub-key ships.

## API action decisions

- **Register through `ntdst_api_action()`, not a raw filter.** The action hook is an ordinary
  WordPress filter, so a raw `add_filter('ntdst/api_data/…')` works — and forfeits the declared
  capability floor, the public-allowlist entry, and the dispatch-time gate. It puts the whole burden
  on the handler.
- **Default-deny, and the framework never opts a site in.** The public (anonymous) action list ships
  **empty**. Anonymous exposure is a decision only a site can make, because only the site knows what
  its data means, so it is made in one place — the public-actions filter.
  *The list used to ship recent-posts, post-search, user-search and magic-link actions, opting every
  site into an anonymous caller-parameterised query surface it never asked for. Ground-truthing found
  zero consumers for most and an authenticated admin autocomplete for the rest. Retiring it let an
  entire gate stack be **deleted** rather than fixed. Do not reintroduce a generic,
  caller-parameterised query action.*
- **`api_data` is a fast-AJAX read layer, not a general-purpose public API**, and the origin check
  does **not** save you — it returns true when there is no Origin, no Referer and no auth cookie. It
  fails open. Treat every public handler as internet-facing.
- **A declared capability floor bites at dispatch, ahead of the handler** — so it protects even a
  handler that forgot to check. It is defense in depth **alongside** the handler's own per-row check,
  never a replacement for it.
- **Prefer the type-derived floor over a literal capability.** `cap_type` resolves the post type
  object's own `cap->edit_others_posts` and is **fail-closed**: an unresolvable or empty capability
  denies everyone, administrators included. The literal `capability` option is retained only because
  it was reconciled from the retired `Theme::apiAction()` wrapper, and it keeps that wrapper's
  fail-**open**-on-empty semantics.
- **Public wins over any floor.** Marking an action public never floors it — anonymous reachability
  is not conditional on a capability. Setting both is a by-design footgun; don't.
- **The relation autocomplete is the one framework-provided data action, and it is not public.**
  `relation_search` gates on two cheap questions: is the requested type a **declared relation
  target** (an allow-list derived from the registered schemas — every `post_type` named by a
  `relation` field), and does the caller hold that type's own `edit_others_posts`? A type nobody
  points a relation field at is unreachable, and nobody has to remember to exclude it.
- **The JS client has exactly three methods** — `call`, `upload`, `download`
  (`ntdst-core/assets/js/ntdst-api.js`). There are no per-action helper wrappers;
  `getRecentPosts()` / `searchPosts()` / `getPostDetails()` / `getTaxonomyTerms()` were documented for
  years and never existed. Call the action by name, and never `fetch()` the route directly — the
  client carries the nonce, CSRF and rate-limit handling.

### The authorization idiom — three rules, each learned the hard way

**1. `edit_posts` is NOT authorization.** It means "may create and edit MY OWN posts", and
**Contributors and Authors hold it**. Gating a read path on it hands every non-public row to the
lowest content role. This shipped twice, in different files, both times with a comment claiming it
meant "editors only". Use `edit_others_posts` — "may edit posts belonging to someone else" — which is
what a handler returning other people's rows actually implies.

**2. Read the capability OFF THE TYPE, never as a literal.**

```php
// ✓ follows the type; survives a per-type capability map
$type = get_post_type_object('release');
$cap  = ($type instanceof WP_Post_Type && is_string($type->cap->edit_others_posts ?? null))
      ? $type->cap->edit_others_posts : '';
$mayReadOthers = $cap !== '' && current_user_can($cap);

// ✗ correct only while capability_type === 'post'
if (!current_user_can('edit_others_posts')) { ... }
```

The literal and the mapped answer coincide for a `capability_type => 'post'` type — and stop
coinciding the moment anyone gives that type its own capability type, which is a standard hardening.
Then the literal silently admits every generic Editor to a type that no longer means to grant them
anything. **Resolve and validate BEFORE calling `current_user_can()`** — a non-string capability must
deny, not be passed in. This is exactly what `cap_type` does for you at dispatch.

**3. Gate the FETCH as well as the response.** Decide the capability first, then let it choose the
status you fetch:

```php
$release = $model->find($id, $mayReadOthers ? 'any' : ['publish']);
// ... then the handler gate STAYS, as an independent second control
```

An unprivileged caller's embargoed row is then never loaded at all, so a later mistake in the gate
has nothing left to leak.

### Never return a raw `WP_Post` from a public handler

`find()` populates `->meta` with **every** meta row including protected `_`-prefixed keys, and
`json_encode` serialises all of `WP_Post`'s public properties — `post_password` among them. Nothing
downstream filters. Declare `public_fields` on the model and emit `->publicRows()` / `->publicRow()`,
or project an explicit allow-list **built by iterating the declared schema**:

```php
$declared = [];
foreach (array_keys($this->getFields()) as $field) {
    $declared[$field] = $formatted[$field] ?? null;
}
return array_merge($declared, [
    'id' => (int) $post->ID, 'title' => $post->post_title,
    'excerpt' => $post->post_excerpt, 'permalink' => get_permalink($post->ID),
]);
```

Iterating the schema makes the projection the contract in both directions: a declared field can never
go missing, and an undeclared one can never leak even if the layer later hands back more than it was
asked for. A denylist of known-bad keys fails the moment someone adds a field.

---

## Judgment — when a raw call is legitimate, and the excuses that aren't

The mechanical rules are gated (above). What a grep *cannot* decide is whether a particular raw read
is the justified exception. That judgment is here.

**A raw meta or post read is legitimate in exactly two situations:**

1. **A batch path where the Data API has no terminal for the query.** The corpus-wide example is a
   `DISTINCT` meta-column read for an admin filter dropdown — there is no `distinctMeta()`, so
   `$wpdb` with `prepare()` is the honest answer. This is a **framework gap**, so file it as one.
2. **Inside that domain's repository**, which is where the raw call is supposed to live.

Everything else is drift. The excuses, and what is actually true:

| The excuse | The reality |
|---|---|
| *"It's faster to write `get_post_meta()` than to read the docs."* | It is faster **once**. It then costs every reader who must work out whether this field is sanitised, prefixed, or validated — and it silently skips the sanitiser the schema declares. The golden path is a copy-paste away and is shorter than the raw version. |
| *"It's just one field, a repository is overkill."* | One field is how every one of the 13 started. The repository is ~10 lines and it is the seam that makes the next reader's change safe. |
| *"It's read-only, so nothing can break."* | A read that bypasses the model bypasses the meta prefix. Change `meta_prefix` and every raw reader breaks silently, returning empty rather than erroring. |
| *"I'll batch it myself with `withMeta()` and add the prefix."* | The prefix is no longer in the projected bag. That read returns null **silently**, and a filter built on it fails open — two live sites were found that way. Read the declared field name. |
| *"It's an internal admin screen, not public-facing."* | Admin is where capabilities are weakest relative to what's on screen, and `is_admin()` is a **context flag, not authorization**. Escaping and capability checks are not a public-facing concern. |
| *"It's a prototype / we're demoing it today."* | Prototypes are what ship. Name it in the plan as a deliberate exception with a removal date, or write it correctly — those are the two honest options. |
| *"The neighbouring file does it this way."* | The neighbour may be drifted; that is the measured base rate here. Build to the golden path, not to the sibling. |
| *"The Data API doesn't support what I need."* | Sometimes **true** — and then it is a framework gap worth reporting, not a silent workaround. Say which terminal is missing. A gap named once gets fixed for 13 sites; a gap worked around gets re-worked-around 13 times. |

**Red flags — stop and re-check if you catch yourself:**

- typing `get_post_meta`, `get_posts`, `wp_insert_post` or `$wpdb` anywhere outside a `*Repository.php`
- typing a literal `_ntdst_` or any meta-key prefix, or concatenating `getMetaPrefix()` onto a
  `$row['meta']` read
- writing `ob_start()` to build markup
- reaching for `add_action('wp_ajax_…')` because "it's just a quick endpoint"
- registering a post type or taxonomy with a raw WordPress call
- returning `$post` (or `['data' => $post]`) from a handler anyone unauthenticated can reach
- about to justify any of the above with a sentence from the left column above

## Anti-patterns — the drift vocabulary reviewers key off

| Smell | Fix |
|---|---|
| `$wpdb->query(...)` for CPT data | the repository for that post type |
| `get_post_meta()` / `update_post_meta()` in a service | the model's field accessors |
| array access on a `find()` result | it is a `WP_Post` object |
| `find($id, true)` | throws — the 2nd arg is a status; pass `'any'` or a status array |
| `$row['meta'][$prefix . 'x']` after `withMeta()` | `$row['meta']['x']` — the bag is schema-projected |
| `return false` on error | `return new WP_Error(...)` |
| no `is_wp_error()` check on a write | always check; log if you can't propagate |
| raw `add_action('wp_ajax_*')` or raw `add_filter('ntdst/api_data/…')` | `ntdst_api_action()` |
| `fetch('/wp-json/…')` in JS | `ntdstAPI.call()` / `.upload()` / `.download()` |
| `posts_per_page => -1` | a real limit, or paginate |
| meta read inside a `foreach` | batch it with `->withMeta()` |
| missing `absint()` / `sanitize_*()` on API input | sanitize **all** input |
| missing capability check on a write action | declare `cap_type` **and** check the row |
| `current_user_can('edit_posts')` as a READ gate | Contributors hold it — use `edit_others_posts`, read off the type object |
| `current_user_can('edit_others_posts')` as a literal | resolve `$type->cap->edit_others_posts`; fail closed on empty/non-string |
| `'status' => 'publish'` | `'post_status' => 'publish'` |
| `'data' => $post` from a public handler | `publicRows()`, or a schema-derived allow-list |
| hardcoded `_ntdst_` prefix | read the prefix from the model — or, in a projected bag, don't read a prefix at all |
| several single-field meta writes in a row | `updateMetaBatch()` (one cache clear) |
| `$model->cache(N)`, `ntdst_query_cache()`, `ntdst_get_posts_fast()` | deleted — chain API, or `ntdst_get_formatted_posts()` |
| `register()` with no `public` key, expecting private | it IS private now — say `'public' => false` anyway if privacy is load-bearing |
| `public => true, exclude_from_search => true` | the "reachable by URL, hidden from search" idiom — needs an explicit review, not silence |

## See also

- `golden-paths/model-and-api-action.md` — the worked slice
- `ntdst-architecture` — service lifecycle, DI, the fork/divergence table, `references/framework-map.md`
- `ntdst-patterns` — where files live
- `lessons.md` — the incidents these rules came from
