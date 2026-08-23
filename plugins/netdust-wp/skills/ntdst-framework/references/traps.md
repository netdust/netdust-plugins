# Traps — what the source will not tell you

Every line here cost someone something. They are what a signature, a docblock or a failing call does **not** reveal: values that fail quiet, silent no-ops, and defaults that mean the opposite of what they look like. Anchored on ntdst-core 5.0.0.

Each line names what pins it — a core unit test, or an invariant in `ARCHITECTURE-INVARIANTS.md`. If you change the behaviour, that is the thing that will tell you.

## Fails quiet (the dangerous class)

- **`custom-fields` support is per-TYPE, never per-key.** Declaring one field with `show_in_rest` turns the support on, and WordPress then also emits every key some other code registered globally on that type with `register_meta('post', …, 'show_in_rest' => true)` — plus the editor's Custom Fields panel for `edit_post` holders. Both are widenings your declaration did not ask for. Assert the `.meta` keys EQUAL the declared set, not that yours are present — pinned by DataRegistersRestMetaTest.php.
- **A partially declared repeater reads back `null` on `/wp/v2`, and a legal write wipes the undeclared keys.** All-or-nothing is the rule: one sub-field that does not declare itself makes the whole repeater unpublishable. The public-provenance-with-private-price shape is deliberately not supported — pinned by DataRegistersRestMetaTest.php.
- **`current_user_can('edit_posts')` as a read gate means "may edit MY OWN posts".** Contributors and Authors hold it. Use `edit_others_posts`, resolved off the type object (`$type->cap->edit_others_posts`), failing closed on empty or non-string — pinned by INV-3.
- **A listener on a renamed hook is silently inert.** There is no shim for `ntdst_model_create_before` and its five siblings, nor for the `ntdst_service_{slug}_config` and `netdust_{slug}_config` spellings. The listener registers, is never called, and nothing says so. Grep every consumer before you bump — pinned by DataModelHooksTest.php.
- **The declared origin list is REST-only.** `admin-ajax.php`, `admin-post.php` and the customizer read `allowed_http_origins` too, and `send_origin_headers()` grants credentials to every allowed origin unconditionally. The declaration is scoped to `wp_is_serving_rest_request()` for exactly that reason; do not widen it by adding origins yourself — pinned by NtdstRestCorsTest.php.
- **A route carrying an option core does not know is not registered AT ALL.** One `_doing_it_wrong`, one log line, and the endpoint is absent — it reviews as protected and 404s on the wire. `permission_callback` is not one of the options; `permission` is — pinned by PackageBootIntegrityTest.php.

## Silent no-ops

- **`'default' => …` on a field is read by nothing.** A `select` shows its first option because that is what `<select>` does. Apply defaults yourself — pinned by MetaboxGeneratorRenderTest.php.
- **`'label' => …` on a top-level scalar field is ignored.** The admin label is always `ucwords(str_replace('_', ' ', $key))`. Rename the key. `label` IS honoured on a repeater sub-field — pinned by MetaboxGeneratorRenderTest.php.
- **A repeater declared with `fields` renders no row inputs.** The sub-field key is **`sub_fields`**. With the wrong key every sub-value falls back to a plain text clean — pinned by DataRegistersRestMetaTest.php.
- **A sub-field's own `sanitizer` is refused at `register()`.** Nothing ever ran it: the row walk cleans each cell by its DECLARED TYPE and never looks for a callable. A security declaration that quietly does nothing is worse than none — pinned by DataReadsTheVocabularyTest.php.

## Reversed or non-obvious defaults

- **`int` is SIGNED now.** The unsigned cast left that path, so `-500` stores as `-500` where it used to store `500`. A numeric string past the platform maximum saturates at `PHP_INT_MAX`, a float past it is PHP's undefined cast, and a non-scalar stores `0` — pinned by DataReadsTheVocabularyTest.php.
- **`bool` stores `false` ONLY for the exact string `"false"`.** It is `wp_validate_boolean()`, WordPress's word: `'no'` and `'off'` store as **true**. Find those before you upgrade — `SELECT post_id, meta_key FROM wp_postmeta WHERE meta_value IN ('no','off')` — pinned by MetaboxGeneratorSaveTest.php.
- **A retired type name is a FATAL at `register()`**, and the message names the canonical one to write instead. It is not a warning and not a fallback to text — pinned by FieldTypesTest.php.
- **A `cell = false` type inside `sub_fields` fatals at `register()`.** Those are `html`, `relation`, `gallery` and `repeater`, so a nested repeater is refused too. Before 5.0 the declaration registered and the edit screen white-screened on first render — pinned by DataReadsTheVocabularyTest.php.
- **`register()` is PRIVATE by default.** Opt in with `'public' => true`. It used to be the reverse, which is why non-public CPTs were once anonymously enumerable — pinned by DataDeclaresWordPressReadsTest.php.
- **Reads are publish-only by default** — `find()` *and* `getMeta()`. Pass a status to see drafts. A not-found row and a wrong-status row return the **same** `WP_Error`, so a denial test must first prove the row is reachable — pinned by DataDeclaresWordPressReadsTest.php.
- **Use `post_status`, not `status`** — `status` collides with a meta field of that name — pinned by DataDeclaresWordPressReadsTest.php.
- **The Data API has its own friendly key vocabulary.** Pass `title` / `content` / `excerpt`, never the raw columns `post_title` / `post_content` / `post_excerpt`. A raw name is dropped from post-table extraction **and silently re-prefixed into meta** — 60 Stride posts carried an orphan `_ntdst_post_title`, invisible because another read path still rendered them. The map is `NTDST_Data_Model::WP_COLUMNS`; `_ntdst_post_*` keys in the meta table are the fingerprint, and zero warnings in `logs/data-*.log` is the check — pinned by DataReadsTheVocabularyTest.php.
- **`ntdst_data()->get()` returns a CLONE and registers nothing.** An unknown name yields an unstored empty model, so `get()` answers "yes" for a type nobody registered. Use `isRegistered()` to ask — pinned by DataSurfaceTest.php.

## Routing

- **A `path()` pattern whose FIRST segment is a placeholder is refused** with `_doing_it_wrong`, and adds no rule. `/:slug` would shadow every URL on the site, so rules go in at `top` only behind a literal first segment — pinned by INV-6.
- **A callback returns a path, `null` or `false` — it never exits.** `false` is the refusal and calls `$wp_query->set_404()`, so WordPress's own 404 renders. Nothing un-404s a request and nothing filters `redirect_canonical` — pinned by INV-6.
- **Rewrite rules flush only when their hash changes.** Add a route and the first request after deploy re-registers them; a route that 404s forever usually means the hash never moved — pinned by INV-6.
- **`url()` silently drops params that match no `:placeholder`.** They are not appended as a query string — pinned by NtdstPagesTest.php.
- **Template paths are read LIVE on every `locate()`.** There is no path cache and no `clearPathCache()`. Resolved *files* are cached, positive hits only — pinned by TemplateLoaderTest.php.

## Rest

- **A write verb that names only a posture does not register.** Reads are `GET`, `HEAD`, `OPTIONS`; every other verb is a write, custom ones included, because `PURGE` empties a cache and a proxy will route it. `->public()` and `'logged_in'` are both refused on a write — pinned by NtdstRestDefaultsTest.php.
- **A near-miss spelling of `public` is a CAPABILITY, not an opening.** Every unrecognised string is asked as `current_user_can()`, so `'Public'` and `' public '` deny everyone rather than being normalised back into an opening — pinned by NtdstRestDefaultsTest.php.
- **`->public()` marks only the declaration its verb just returned.** It does not latch onto the next route, and it cannot reach across modules to publish a pending one — pinned by RestInternalByDefaultTest.php.
- **A rate-limited route registers a CLOSURE as its `permission_callback`, `->public()` or not** — the limiter has to run. So `permission_callback === '__return_true'` cannot answer for it. Never settle a route by the TYPE of its callback; read what it declared — pinned by RestInternalByDefaultTest.php.
- **There is no envelope.** A handler returns `WP_REST_Response` or `WP_Error` and WordPress builds the body, so a client that read `response.data.thing` reads `response.thing` — pinned by INV-2.

## The rate limiter has three verbs

- **`attempt()` spends AND decides** — for a request budget, where every question IS a request — pinned by RateLimiterTest.php.
- **`exceeded()` asks and spends nothing** — for a failure counter, asked far more often than incremented. **Never check a lockout with `attempt()`**: it spends per call, so the check causes the lockout it is checking for, and a login gate consulted twice per attempt locks out a user typing the correct password — pinned by RateLimiterTest.php.
- **`reset()` forgives** — call it when the caller succeeded. The `>= $limit` boundary lives inside `exceeded()`; do not restate it at the call site, and note a limit `<= 0` is switched off and can never be exceeded — pinned by RateLimiterWindowTest.php.

## Admin fields

- **`image` and `file` render a media-picker cell and store a plain attachment-ID int.** An id that resolves to no attachment stores as `0`, and an attachment deleted after the write is not noticed on read — pinned by MetaboxGeneratorSaveTest.php.
- **Every one of the 17 types draws its own control**, and an unknown control is a loud fault, never a silent fall-back to a text box — pinned by MetaboxGeneratorRenderTest.php.
- **`required` is three separate things, and none is a layer-wide invariant.** (1) A required field *left out* of an update keeps its value; one *supplied* as `''`/`null`/`[]` is refused, on create and update alike — the discriminator is `array_key_exists`, not `isset`. (2) Validation runs BEFORE sanitization, so a value that is non-empty raw but sanitizes away still lands empty: an unparseable `date` (`→ ''`), invalid `json` (`→ []`), a `relation` given `['']` (`→ []`). (3) `updateMeta()` and `updateMetaBatch()` never validate at all, so `$model->updateMeta($id, 'venue_city', '')` blanks a required field quietly — pinned by MetaboxGeneratorSaveTest.php.
- **`required`, `min`, `max` and `validate` are the MODEL's rules, not storage rules.** A REST write goes through `register_post_meta()` and never reaches them — pinned by DataRegistersRestMetaTest.php.
- **`false`, `0`, `0.0` and `'0'` are NOT empty** — a required boolean may be `false` and a required integer may be `0`. The metabox posts a hidden `value="0"` ahead of each checkbox for exactly this reason, and a repeater row whose only answer is `'0'` is kept — pinned by MetaboxGeneratorSaveTest.php.
- **`select` sanitizes but does not VALIDATE.** `options` is a UI list, not a closed set: any string is storable. A closed vocabulary needs an explicit `validate` closure, on create **and** update — pinned by FieldTypesTest.php.
