---
name: ntdst-data
description: >
  Use when planning, designing, implementing, or reviewing data models, custom
  post types, taxonomies, field definitions, metaboxes, API actions, database
  queries, or CRUD operations in an NTDST WordPress project. Triggers on
  phrases like "register a CPT", "add a custom post type", "add a field to the
  model", "add a metabox", "add an api_data action", "an AJAX endpoint",
  "expose this publicly", "query the model", "add a repository method", "why is
  this returning WP_Error", and on the keywords `ntdst_data`,
  `ntdst_api_action`, `NTDST_Data_Model`, `NTDST_Data_Manager`,
  `NTDST_MetaboxGenerator`, `public_fields`, `meta_prefix`, `publicRows`,
  `WP_COLUMNS`, `ntdst/api_data`, `ntdst/api/public_actions`. Also use when
  deciding whether an action may be reached anonymously or what capability
  should gate it. Activates alongside ntdst-architecture for data work.
---

# NTDST Data Layer

**This skill carries decisions and traps, not an API listing.** Method names and signatures live in
`api/Data.php`, `api/Endpoints.php` and `admin/MetaboxGenerator.php`, where they cannot drift. Decide
the case here, then read source for the exact call.

**`ntdst-core` is a per-project fork with no shared upstream** — see `ntdst-architecture` for the
divergence table. Confirm a method exists in *this project's* copy before calling it. Where this file
says "HEAD", it means daan's copy, which is the most-evolved on Data, Endpoints and Metabox.

## The mechanical rules are a gate, not prose

Everything a grep can decide — raw meta calls, repository bypasses, `ob_start()` rendering, raw
`wp_ajax_*`, direct `register_post_type()`/`register_taxonomy()`, hardcoded meta prefixes, wrong Data
API vocabulary, unprepared `$wpdb`, `permission_callback => __return_true` — is enforced by:

```bash
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py"            # staged files
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py" --since HEAD~1
python3 "$CLAUDE_PLUGIN_ROOT/bin/drift-check.py" path/to/module
```

**Run it before you close a task that touched PHP.** A deliberate exception is annotated on the line,
with a reason, and stays greppable:

```php
// ntdst-allow: raw-meta — batch enrichment for the admin table, N+1 otherwise
```

An allow with no reason is itself a finding. Don't re-argue a gated rule in prose — fix it or
annotate it.

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
| Read a list | `$model->where(...)->limit(...)->get()` → **arrays of arrays** |
| Emit the declared public shape | `->publicRows()` / `->publicRow($id, $status)` |
| Write | `$model->create($data)` / `->update($id, $data)` — friendly keys, check `is_wp_error()` |

The rules below are what decide the cases the recipes don't cover.

## The four rules that do not change

1. **No raw SQL, no direct meta.** All persistence goes through the data layer, and CPT access goes
   through that domain's repository — the single mediator. `ntdst_data()->get('type')` should appear
   in exactly one file per post type.
2. **`WP_Error` on failure, and never swallowed.** Every create/update/delete result is
   `is_wp_error()`-checked. A swallowed error is invisible data loss; that is exactly how a silent
   save bug survived in production.
3. **Friendly key vocabulary, not `wp_posts` column names.** Pass `title`, `content`, `excerpt` —
   not `post_title`. The canonical accepted set is `NTDST_Data_Model::WP_COLUMNS`.
4. **`post_status`, never `status`.** A field literally named `status` is common, and the collision
   silently sends a post-table value into meta.

## Registration decisions

- **Private by default. Silence is not privacy.** Registration defaults to `public => false`,
  `has_archive => false`; a model opts **in** to visibility. The old default merged caller config
  *over* `public => true`, so a model registered without visibility flags was published, archived and
  queryable — which is why every non-public CPT had to state six denials by hand, and why forgetting
  one was a disclosure.
- **A failed registration is returned, never swallowed.** `register_post_type()` returns `WP_Error`
  for an invalid or reserved name. Older code discarded it and built the model anyway, leaving a
  half-registered phantom that reports healthy: `isRegistered()` true while `post_type_exists()`
  false. Fail closed, and loudly.
- **Taxonomies are declared with the model**, via the `taxonomies` config key, and are registered only
  after the post type succeeds. This is the one implementation of taxonomy registration; the
  `Theme::taxonomy()` wrapper that used to hold these defaults is retired (a taxonomy outlives a theme
  switch, so it was never Theme's job). Its defaults were lifted verbatim — changing them changes
  every taxonomy that relied on the wrapper.
- **Asking about a model must not create one.** In HEAD, a lookup miss returns an error; it used to
  auto-register a phantom into a *static* array, so a caller-supplied type name on a public endpoint
  could register whatever it liked, and nothing could tell a real model from someone's typo. On a copy
  that still auto-creates, use the registration check, never the getter, when iterating post types.
- **Metaboxes are generated from the field definitions**, and they live in `admin/` — admin UI, not
  transport. That directory owns the **write-authorization gate**: whether an actor may write a
  model's fields is decided in the metabox save method, and read access to its error notices is
  gated by the same predicate so read ⊆ write by construction.

## Query and return-shape decisions

- **`find()` and the array-returning list query have different shapes, and mixing them is the most
  common bug in this layer.** Record lookups return a `WP_Post` object (with fields attached) or
  `WP_Error`; list queries return arrays of associative arrays. Treating a lookup result as an array
  is a fatal.
- **Rollback is best-effort, not a transaction.** Create deletes the new post if a meta write fails;
  update snapshots prior post and meta state and restores on failure. This is application-level, not
  a DB transaction — for critical multi-table paths (capacity locks, voucher counts) still wrap the
  business operation in an explicit SQL transaction.
- **`update_post_meta()` returns `false` both for errors and for unchanged values.** The layer treats
  unchanged as success, so re-saving an identical value does not trigger a spurious rollback. Any
  code you write against raw meta must make the same distinction or it will invent failures.
- **Never hardcode the meta prefix.** Batch-loaded results (`withMeta()`-style envelopes) expose raw
  prefixed keys — that is the framework's design, the alternative being N+1. Read the prefix from the
  model. A hardcoded `_ntdst_` literal is drift even in a path where prefix-awareness is justified.
- **There is no query cache in HEAD.** It was deleted along with its invalidation hooks, because the
  layer keeps no cache of its own and WordPress core already invalidates post, post_meta and
  object-term entries on save and delete. Most other copies still carry one. Do not write
  cache-invalidation hooks for a cache this copy does not have, and do not assume a cache exists.

### Traps

- **A boolean second argument to the record lookup used to mean "skip the cache".** That cache is
  gone and a post-status parameter took its position, so a leftover call would have silently meant
  "accept the status `true`" — matching nothing and denying every row. HEAD **throws** on a boolean
  rather than failing invisibly. On an older copy the same call silently skips the cache instead.
  Fail-closed-but-invisible is the worst shape available; this is what it looks like when it is fixed.
- **Unknown keys are logged and dropped, not written.** A writer using the wrong vocabulary shows up
  as `_ntdst_post_*` keys in a meta dump and as warnings in the data log. Zero warnings after a
  refactor is the proof the vocabulary is right.
- **An unknown *field type* throws at registration.** It used to fall through to
  `sanitize_text_field` silently, which is how a `wysiwig` typo quietly stripped a field's markup with
  nothing failing. Several types were also *advertised but never sanitised* until this was fixed —
  a helper that accepts a type name and then ignores it is lying about its own vocabulary. Read the
  exception message for the accepted set; it is the authoritative list.

## API action decisions

- **Default-deny, and the framework never opts a site in.** The public (anonymous) action list ships
  **empty**. Anonymous exposure is a decision only a site can make, because only the site knows what
  its data means, so it is made in one place — the public-actions filter.
  *The list used to ship recent-posts, post-search, user-search and magic-link actions, opting every
  site into an anonymous caller-parameterised query surface it never asked for. Ground-truthing found
  zero consumers for most and an authenticated admin autocomplete for the rest. Retiring it let an
  entire gate stack be **deleted** rather than fixed.*
- **Register through the framework helper, not a raw filter.** The action hook is an ordinary
  WordPress filter, so a raw `add_filter()` works — and forfeits everything: the declared capability
  floor, the public-allowlist entry, and the dispatch-time gate. It puts the whole burden on the
  handler. Prefer the helper; if you must use the raw filter, say why and gate it yourself.
- **A declared capability floor bites at dispatch, ahead of the handler** — so it protects even a
  handler that forgot to check. It is defense in depth **alongside** the handler's own per-row check,
  never a replacement for it.
- **Prefer the type-derived floor over a literal capability.** The type-derived form resolves the
  post type's own capability and is **fail-closed**: an unresolvable or empty capability denies
  everyone, administrators included. The literal form is retained only because it was reconciled from
  the retired `Theme::apiAction()` wrapper, and it keeps that wrapper's fail-**open**-on-empty
  semantics.
- **Public wins over any floor.** Marking an action public never floors it — anonymous reachability
  is not conditional on a capability. Setting both is a by-design footgun; don't.
- **A handler still does the four pillars itself**: sanitize every input, validate, authorize the
  specific row, escape on output. The floor is a second line, not the first.

---

## Judgment — when a raw call is legitimate, and the excuses that aren't

The mechanical rules are gated (above). What a grep *cannot* decide is whether a particular raw read
is the justified exception. That judgment is here, and it is needed because **the drift is real**:
across 13 consumer projects, **13 of 13** hand-roll `get_post_meta()`/`get_posts()`, with the
framework and its docs sitting right there.

**A raw meta or post read is legitimate in exactly two situations:**

1. **A batch path where the Data API has no terminal for the query.** The corpus-wide example is a
   `DISTINCT` meta-column read for an admin filter dropdown — there is no `distinctMeta()`, so
   `$wpdb` with `prepare()` is the honest answer. This is a **framework gap**, so file it as one.
2. **Inside that domain's repository**, which is where the raw call is supposed to live. Batch
   envelopes expose prefixed keys by design; read the prefix from the model.

Everything else is drift. The excuses, and what is actually true:

| The excuse | The reality |
|---|---|
| *"It's faster to write `get_post_meta()` than to read the docs."* | It is faster **once**. It then costs every reader who must work out whether this field is sanitised, prefixed, or validated — and it silently skips the sanitiser the schema declares. The golden path is a copy-paste away and is shorter than the raw version. |
| *"It's just one field, a repository is overkill."* | One field is how every one of the 13 started. The repository is ~10 lines and it is the seam that makes the next reader's change safe. |
| *"It's read-only, so nothing can break."* | A read that bypasses the model bypasses the meta prefix. Change `meta_prefix` and every raw reader breaks silently, returning empty rather than erroring. |
| *"It's an internal admin screen, not public-facing."* | Admin is where capabilities are weakest relative to what's on screen, and `is_admin()` is a **context flag, not authorization**. Escaping and capability checks are not a public-facing concern. |
| *"It's a prototype / we're demoing it today."* | Prototypes are what ship. Name it in the plan as a deliberate exception with a removal date, or write it correctly — those are the two honest options. |
| *"The neighbouring file does it this way."* | The neighbour may be drifted; that is the measured base rate here. Build to the golden path, not to the sibling. |
| *"The Data API doesn't support what I need."* | Sometimes **true** — and then it is a framework gap worth reporting, not a silent workaround. Say which terminal is missing. A gap named once gets fixed for 13 sites; a gap worked around gets re-worked-around 13 times. |

**Red flags — stop and re-check if you catch yourself:**

- typing `get_post_meta`, `get_posts`, `wp_insert_post` or `$wpdb` anywhere outside a `*Repository.php`
- typing a literal `_ntdst_` or any meta-key prefix
- writing `ob_start()` to build markup
- reaching for `add_action('wp_ajax_…')` because "it's just a quick endpoint"
- registering a post type or taxonomy with a raw WordPress call
- about to justify any of the above with a sentence from the left column above

## Anti-patterns — the drift vocabulary reviewers key off

| Smell | Fix |
|---|---|
| `$wpdb->query(...)` for CPT data | the repository for that post type |
| `get_post_meta()` / `update_post_meta()` in a service | the model's field accessors |
| array access on a record-lookup result | it is a `WP_Post` object |
| `return false` on error | `return new WP_Error(...)` |
| no `is_wp_error()` check on a write | always check; log if you can't propagate |
| raw `add_action('wp_ajax_*')` | the framework's API action registration |
| `fetch('/wp-json/…')` in JS | the framework's JS API client (auto-nonce, CSRF, rate limit) |
| `posts_per_page => -1` | a real limit, or paginate |
| meta read inside a `foreach` | batch it — prime the meta cache or use the batching query |
| missing `absint()` / `sanitize_*()` on API input | sanitize **all** input |
| missing capability check on a write action | declare the type-derived floor **and** check the row |
| `'status' => 'publish'` | `'post_status' => 'publish'` |
| hardcoded `_ntdst_` prefix | read the prefix from the model |
| several single-field meta writes in a row | the batch write (one cache clear) |

## See also

- `ntdst-architecture` — service lifecycle, DI, the fork/divergence table, `references/framework-map.md`
- `ntdst-patterns` — where files live
- `lessons.md` — the incidents these rules came from
