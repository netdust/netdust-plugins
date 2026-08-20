# Traps — what the source will not tell you

Every line here cost someone something. They are the things a signature, a
docblock or a failing call does **not** reveal: silent no-ops, fail-open guards,
and defaults that mean the opposite of what they look like.

## Fails open (the dangerous class)

| Trap | Why it bites |
|---|---|
| `ntdst_service_{slug}_enabled` is a **DENY** filter with a `true` default | Misspell the slug and the service you meant to disable **boots**. Nothing reports it. Derive the slug exactly. |
| `verifyOrigin()` returns **true** with no `Origin`, no `Referer` and no auth cookie | It defends a logged-in browser against CSRF. It is not an auth gate — curl omits both headers and is admitted. Public handlers carry their own authorization. |
| `apply_filters('{project}_{slug}_config', …)` | Framework-owned name is `ntdst_service_{slug}_config`. Bootstrap hangs `plugin-config.php`'s `services.overrides.{slug}` on that exact hook — any other name **never receives the override**. |
| `current_user_can('edit_posts')` as a read gate | Means "may edit MY OWN posts" — **Contributors and Authors hold it**. Use `edit_others_posts`, resolved off the type object (`$type->cap->edit_others_posts`), failing closed on empty or non-string. |
| Returning a raw `WP_Post` from a public handler | `find()` populates `->meta` with **every** meta row including `_`-prefixed, and `json_encode` serialises `post_password`. Project an allow-list built from `getSchema()`. |
| Repeater rows on a public payload | Sub-fields are sanitized on write but returned largely as stored. A top-level allow-list does **not** filter sub-keys. |

## Silent no-ops

| Trap | What actually happens |
|---|---|
| `'assets' => [...]` in theme-config.php | **Enqueues nothing.** The config-driven loader was deleted; `validate_config()` does not know the key. Page loads without your CSS. Use `$theme->style()`/`script()`. |
| `'default' => …` on a field | Read by nothing. A `select` shows its first option because that is what `<select>` does. Apply defaults yourself. |
| `'label' => …` on a top-level scalar field | Ignored. The admin label is always `ucwords(str_replace('_',' ',$key))`. Rename the key. (`label` **is** honoured on repeater sub-fields.) |
| A repeater declared with `fields` | The sub-field key is **`sub_fields`**. With `fields` the admin renders no row inputs and every sub-value falls back to `sanitize_text_field`. |
| An unknown option on an `ntdst_rest()` route | The route is **not registered at all** — `_doing_it_wrong` + a log line, absent from the API. It reviews as protected and 404s on the wire. |
| A retired listener name (`netdust_{slug}_*`) | Inert. No shim, no warning. |

## Reversed or non-obvious defaults

- **`register()` is PRIVATE by default.** Opt in with `'public' => true`. It used to be the reverse, which is why non-public CPTs were anonymously enumerable.
- **Reads are publish-only by default** — `find()` *and* `getMeta()`. Pass a status to see drafts. A not-found row and a wrong-status row return the **same** `WP_Error`, so a denial test must first prove the row is reachable.
- **`find($id, true)` throws.** The second argument is a post status now, not the removed `$skipCache` bool.
- **`absint` strips the sign.** A discount, delta or balance declared `integer` silently stores its absolute value. Use **`signed_int`**.
- **Use `post_status`, not `status`** — `status` collides with a meta field of that name.
- **The Data API has its own friendly key vocabulary.** Pass `title` / `content` /
  `excerpt`, never the raw column names `post_title` / `post_content` / `post_excerpt`.
  A raw name is dropped from post-table extraction **and silently re-prefixed into
  meta** — 60 Stride posts ended up carrying an orphan `_ntdst_post_title`, invisible
  because a different read path still rendered them. The canonical map is
  `NTDST_Data_Model::WP_COLUMNS`. **Fingerprint:** `_ntdst_post_*` keys in the meta
  table mean some writer has the vocabulary wrong. `warnUnregisteredKeys()` logs
  unknown keys and drops them — zero warnings in `logs/data-*.log` after a refactor
  is the check.
- **An unknown field type throws at registration.** A typo is loud, not silent — unless the field supplies its own `'sanitizer'`, which bypasses the check.
- **`ntdst_data()->get()` returns a CLONE and registers nothing.** An unknown name yields an unstored empty model, so `get()` answers "yes" for a type nobody registered. Use `isRegistered()` to ask.

## Routing

- **A route callback returning `null` EXITS the request.** Forget a `return` and you get a blank page from a route that looks like it "isn't running".
- **An `NTDST_Response` with status >= 400 REFUSES**: the status is sent, WordPress's not-found state is left intact and **its own 404 template renders** — your template is dropped, whether or not the Response names one. That is the route saying "no" through the output class. Do not hand-roll `status_header()` in the callback; that is the shape the split exists to remove.
- **`url()` silently drops** params that match no `:placeholder`. They are not appended as a query string.
- **Template paths are read LIVE** on every `locate()`. There is no path cache and no `clearPathCache()`. Resolved *files* are cached, positive hits only.

## The api_data / REST surfaces

- **Gate order: registration → AUTH → rate limit → nonce.** Auth moved ahead of the limiter so an anonymous caller cannot make the site write transients by asking. The **CSRF check deliberately stays below** the limiter — a caller who fails it already passed auth, so a CSRF flood is exactly what a throttle should charge.
- **`NTDST_Rest` wraps the PERMISSION, not the handler.** There is no automatic `{success,data}` envelope and no `toRestResponse()`. Use `NTDST_Response::apiSuccessResponse()` / `apiErrorResponse()`.
- **`permission` is required and must be callable**, or the route is refused. There is no implicit `__return_true`.
- **Preflights are charged** into a bucket of their own. An over-budget `OPTIONS` gets a 429 — which is *not* the 415 trap: never refuse *every* preflight, that breaks CORS outright.
- **Only the ACTION axis of a rate-limit key is bounded.** A public action lets an anonymous caller create one bucket per client IP — that is what a per-IP throttle *is*, not a leak.

## The rate limiter has three verbs, and the wrong one is a bug

| Call | Does | For |
|---|---|---|
| `attempt()` | spend **and** decide | a request budget — every question IS a request |
| `exceeded()` | ask, spend nothing | a failure counter — asked far more than incremented |
| `reset()` | forgive | the caller succeeded |

**Never check a lockout with `attempt()`.** It spends per call, so the check causes
the lockout it is checking for — a login gate consulted twice per attempt locks out
a user typing the correct password. The `>= $limit` boundary lives inside
`exceeded()`; do not restate it at the call site. A limit `<= 0` is switched off and
can never be exceeded.

## Admin fields

`image` and `file` render a media-picker cell and store a plain attachment-ID int.
`html`/`content`, `person` and `post_relation` sanitize correctly but have **no
control** — they fall to a text input; use `wysiwyg` for the editor. `number` is a
repeater **sub-field** type only; at top level it falls to text.

### `required` — three separate things, and none of them is a layer-wide invariant

1. **Omitted vs explicitly emptied.** A required field *left out* of an update keeps
   its value; one *supplied* as `''`/`null`/`[]` is **refused, on create and update
   alike**. The discriminator is `array_key_exists`, not `isset` — `isset` reports
   false for an explicit `null` and would misclassify a blanking instruction as an
   omission. Do not "simplify" this back to gating the whole update path on
   `!$isUpdate`: that was the bug (it silently blanked un-emptyable fields on every
   site), and removing the guard entirely breaks every single-field write.
2. **`validateData()` runs BEFORE `sanitizeData()`.** So a required value that is
   non-empty raw but *sanitizes away* still lands empty — an unparseable `date`
   (`→ ''`), invalid `json` (`→ []`), a `relation` given `['']` (`→ []`). The
   metabox path is protected because its own sanitizer collapses these first; a
   programmatic caller or a crafted POST is not.
3. **`updateMeta()` and `updateMetaBatch()` never call `validateData()` at all.**
   `$model->updateMeta($id, 'venue_city', '')` blanks a required field, quietly.

**`false`, `0`, `0.0` and `'0'` are NOT empty** — a required boolean may be `false`
and a required integer may be `0`. The metabox posts a hidden `value="0"` ahead of
each checkbox for exactly this reason.

At render, `required` also shows as a `*` marker plus native `required`/`aria-required`
— withheld for `readonly` and for boolean/wysiwyg/relation/gallery/repeater/image/file,
which the browser cannot usefully validate.

### `select` sanitizes but does not VALIDATE

`options` is a UI list, not a closed set. Any string is storable. A closed vocabulary
needs an explicit `validate` closure, on create **and** update.
