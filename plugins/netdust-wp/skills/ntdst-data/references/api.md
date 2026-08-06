# API Endpoints Reference

Complete guide to the NTDST REST API system for fast, secure database access.

---

## Table of Contents

1. [Overview](#overview)
2. [REST Endpoints](#rest-endpoints)
3. [Registering Actions](#registering-actions)
4. [Public vs Protected Actions](#public-vs-protected-actions)
5. [JavaScript Client](#javascript-client)
6. [Security Features](#security-features)
7. [Response Format](#response-format)
8. [Built-in Actions](#built-in-actions)
9. [Anti-Patterns](#anti-patterns)

---

## Overview

The NTDST API is a **fast-AJAX read layer** — same-origin, nonce-gated, in-page JS
talking to its own site. It is a high-performance alternative to `wp_ajax_*`, **not a
general-purpose public API**. That is a legitimate design, but it means an action added
to `public_actions` is reachable by anyone with caller-supplied params. Read
[Public vs Protected Actions](#public-vs-protected-actions) before adding one.

For a cross-origin / headless / third-party client, this is the wrong tool: an anonymous
WP nonce is a shared, non-origin-bound token that authenticates nothing for a cookie-less
request. Use `ntdst_router()->rest()` + `NTDST_Cors_Policy` instead.

### Key Features

| Feature | Description |
|---------|-------------|
| Auto-nonce management | Client handles nonce lifecycle, retries once on `invalid_nonce` |
| Rate limiting | 30 requests per 60 seconds, per-action, filterable |
| CSRF protection | Origin/referer verification — **fails open with no Origin, no Referer and no auth cookie** |
| Auth gate | Anonymous callers may only dispatch actions in `public_actions` |
| Post-type gate | `canQueryPostType()` decides which types a caller may query at all |
| Filter-based | Actions registered via WordPress filters |

> **No caching.** The endpoints layer registers no cache-invalidation hooks and owns no
> cache; `NTDST_Query_Cache` and `ntdst_endpoints()->clear_post_cache()` are gone. Core
> invalidates its post / `post_meta` / term entries on save, delete and trash by itself.

### Architecture

```
JavaScript Client (ntdstAPI)
        ↓
/wp-json/ntdst/v1/get_nonce  →  Get nonce for action
        ↓
/wp-json/ntdst/v1/action     →  Execute action with nonce
        ↓
Filter: ntdst/api_data/{action}  →  Handler returns data
        ↓
JSON Response
```

---

## REST Endpoints

### Get Nonce

**Endpoint:** `POST /wp-json/ntdst/v1/get_nonce`

**Request:**
```json
{
  "action": "my_action"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "nonce": "abc123def456"
  }
}
```

### Execute Action

**Endpoint:** `POST /wp-json/ntdst/v1/action`

**Request:**
```json
{
  "action": "get_recent_posts",
  "nonce": "abc123def456",
  "post_type": "portfolio",
  "per_page": 10
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "posts": [...]
  }
}
```

---

## Registering Actions

### Via Filter

```php
add_filter('ntdst/api_data/get_portfolio', function ($data, $params) {
    $id = absint($params['id'] ?? 0);

    if (!$id) {
        return new WP_Error('missing_id', 'ID required');
    }

    // Use Data Manager for all database operations.
    // find() is PUBLISH-ONLY by default; pass an explicit status only when the
    // caller's capability justifies it.
    $model = ntdst_data()->get('portfolio');
    $item = $model->find($id);

    // find() returns WP_Post or WP_Error — never null/false.
    if (is_wp_error($item)) {
        return $item;
    }

    // find() already attached ->fields; prefer it. NOTE: getMeta() internally
    // calls find($id, 'any') — it is a RAW ACCESSOR, not a visibility decision,
    // so it happily reads a draft's meta. Never let it be the only gate.
    $meta = $item->fields;

    return [
        'item' => [
            'id' => $item->ID,
            'title' => $item->post_title,
            'client' => $meta['client_name'] ?? '',
            'year' => $meta['project_year'] ?? '',
        ],
    ];
}, 10, 2);
```

### Via Theme Helper

```php
$theme->apiAction('my_action', function ($data, $params) {
    // Handler code using Data Manager
    $items = ntdst_data()->get('portfolio')
        ->where('featured', true)
        ->limit(10)
        ->get();

    return ['items' => $items];
});
```

### With Capability Check

```php
$theme->apiAction('admin_action', function ($data, $params) {
    // Only runs if the capability check passed; otherwise apiAction() returns
    // WP_Error('forbidden', …, ['status' => 403]) before your callback runs.
    return ['admin' => 'data'];
}, ['capability' => 'edit_others_posts']);
```

> **Do not use `edit_posts` here as a read gate.** It means "may create and edit MY OWN
> posts" and **Contributors and Authors hold it**. See
> [Authorization idiom](#authorization-idiom--three-rules).

### Handler Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `$data` | `array` | Previous filter data (usually empty) |
| `$params` | `array` | Request parameters from the JSON body or form-data. Uploaded files arrive under the reserved `_files` key — never pass `_files` as data. |

### Return Values

| Return | Result |
|--------|--------|
| Array with data | Success response — wrapped in `{"success": true, "data": …}` by `handle_action` |
| `WP_Error` | Converted to an error response |
| Empty array | **A legitimate success** (e.g. zero search hits) |
| No handler registered at all | `unknown_action` error |

`handle_action` distinguishes "no handler registered" (`has_filter()` is false) from
"handler returned nothing", so an empty result is no longer a 404.

**Return the payload only.** Never build your own `['success' => false, …]` array: it
gets wrapped, producing `{"success":true,"data":{"success":false,…}}`, and a client doing
the obvious `if (response.success)` reads a rejected request as a successful one. That
shipped once. `WP_Error` is the shape `handle_action` unwraps.

---

## Public vs Protected Actions

### Default Public Actions

```php
private array $public_actions = [
    'get_recent_posts',
    'search_posts',
    'send_magic_link',
];
```

**`search_users` is NOT public** — it is cap-gated in-handler with
`current_user_can('list_users')`, because listing users by email/login is a PII leak.

### What "public" actually costs you

Being in this list means an anonymous caller may both **mint a nonce for the action** and
**dispatch it**. Both gates are symmetric: `check_nonce_permission()` and
`check_action_permission()` each consult the filtered list, so a handler that forgot its
own login check is no longer an exposed surface merely because a nonce leaked.

`verifyOrigin()` does **not** make up the difference: it returns `true` when there is no
`Origin`, no `Referer` and no auth cookie. **It fails open.** Treat every public handler
as internet-facing, with caller-supplied params.

### The post-type gate — do not route around it

`canQueryPostType()` in `api/Endpoints.php` is the convergence point deciding whether a
caller may query a type at all. `get_recent_posts` and `search_posts` take the type name
straight from an unauthenticated request body, so no registry flag governs anything on
this surface unless *this* gate reads it.

- Admits a type that is `public === true` **AND** `exclude_from_search === false`
  outright. Not `public` alone: `public => true, exclude_from_search => true` is
  WordPress's standard "reachable by its own URL, never surfaced by search" idiom — an
  embargoed press kit — and short-circuiting on `public` served every row of such a type
  to anonymous callers.
- Otherwise requires **both** the type's own `edit_posts` **and** `edit_others_posts`,
  read off the type object, failing closed on an empty or non-string capability.
- Anonymous callers therefore get zero rows from non-public types.
- Attachments whose parent is not publicly viewable are excluded from the query args, so
  draft-attached media is not enumerable.
- Filterable via `ntdst/api/queryable_post_type` — opening a non-public type here exposes
  every row of it to anonymous callers.
- **Refuse the request when the allowed list is empty**; never query first and filter
  after. Core's `post-queries` cache keys on the args and the SQL, never on who asked, so
  a post-hoc filter hands the next anonymous caller an editor's cached rows.

`publicly_queryable` and `show_in_rest` are deliberately **not** consulted — they govern
the front-end query var and the wp-json controller, and this router goes through neither.

### Making an Action Public

```php
add_filter('ntdst/api/public_actions', function ($actions) {
    $actions[] = 'my_public_action';
    return $actions;
});
```

### Protected Actions

Any action not in the public list requires the user to be logged in — both to get a nonce
and to dispatch. Being logged in is **not** authorization, though: a Subscriber is no
more entitled to a non-public type than an anonymous caller. Add your own capability
check.

```php
// This action requires authentication
add_filter('ntdst/api_data/update_profile', function ($data, $params) {
    $user_id = get_current_user_id();

    if (!$user_id) {
        return new WP_Error('not_authenticated', 'Login required');
    }

    // Use Data Manager for updates
    $model = ntdst_data()->get('artist_profile');
    $result = $model->update($params['profile_id'], [
        'bio' => sanitize_textarea_field($params['bio'] ?? ''),
    ]);

    if (is_wp_error($result)) {
        return $result;
    }

    return ['updated' => true];
}, 10, 2);
```

---

## JavaScript Client

The `ntdstAPI` client is automatically available and handles all nonce management.

### Basic Usage

```javascript
// Call any action
const result = await ntdstAPI.call('my_action', {
    param1: 'value1',
    param2: 'value2',
});
```

### The client's actual surface

`assets/js/ntdst-api.js` exposes exactly three methods. **There are no
`getRecentPosts()` / `searchPosts()` / `getPostDetails()` / `getTaxonomyTerms()`
convenience wrappers** — call the actions by name through `call()`.

```javascript
await ntdstAPI.call(action, params);        // JSON body, returns the unwrapped `data`
await ntdstAPI.upload(action, formData);    // multipart/form-data; files reach the
                                            // handler as $params['_files']
await ntdstAPI.download(action, params);    // returns a Blob; throws on !response.ok

// The built-in actions, called by name:
const { posts }   = await ntdstAPI.call('get_recent_posts', { post_type: 'portfolio', per_page: 10 });
const { results } = await ntdstAPI.call('search_posts', { search: 'query', post_types: ['post', 'page'] });
```

The client requires `window.ntdstAPIConfig.restNonce` (a `wp_rest` cookie nonce),
localized by `ntdst_enqueue_api_client()`. It self-skips if `window.ntdstAPI` is already
defined, so loading it alongside a theme bundle that inlines its own copy is a no-op.

### Error Handling

```javascript
try {
    const data = await ntdstAPI.call('my_action', params);
    // Success
} catch (error) {
    // Handle error
    console.error('API error:', error.message);
}
```

### Nonce Caching

Nonces are automatically cached per action. If a nonce expires, the client automatically:
1. Detects "invalid_nonce" error
2. Clears cached nonce
3. Retries the request with a fresh nonce

### Live Search Example

```javascript
let searchTimeout;

function liveSearch(input) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
        if (input.value.length < 3) return;

        const { results } = await ntdstAPI.call('search_posts', { search: input.value });
        displayResults(results);
    }, 300); // 300ms debounce
}

document.getElementById('search')
    .addEventListener('input', (e) => liveSearch(e.target));
```

### Post List Example

```javascript
async function loadPosts() {
    const { posts } = await ntdstAPI.call('get_recent_posts', { post_type: 'post', per_page: 10 });

    // NOTE: `thumbnail` is an object ({id, url, full}) or null — not a URL string.
    const html = posts.map(post => `
        <article>
            ${post.thumbnail ? `<img src="${post.thumbnail.url}">` : ''}
            <h3><a href="${post.permalink}">${post.title}</a></h3>
            <p>${post.excerpt}</p>
            <time>${post.date}</time>
        </article>
    `).join('');

    document.getElementById('posts').innerHTML = html;
}
```

---

## Security Features

### Rate Limiting

- **Limit:** 30 requests per 60 seconds, **per action**
- **Scope:** per `(user_id, action)` when logged in, per `(ip, action)` when anonymous.
  User-id keying stops users behind shared NAT (offices, schools, carriers) from sharing
  a bucket.
- **Storage:** WordPress transients
- **Filterable per action:** `ntdst/api/rate_limit/{action}` and
  `ntdst/api/rate_window/{action}`. A limit of `0` disables it for that action.
- `X-Forwarded-For` is honoured **only** when `REMOTE_ADDR` is in the trusted-proxy list
  (`netdust_trusted_proxies` — a historical filter name; don't propagate the prefix).

```php
// Magic-link send: 3 per hour. Without this an attacker POSTs it 30x/minute
// to spam a victim's inbox and exhaust the SMTP quota.
add_filter('ntdst/api/rate_limit/send_magic_link', fn() => 3);
add_filter('ntdst/api/rate_window/send_magic_link', fn() => 3600);
```

### CSRF Protection — and where it fails open

```php
// Accepted:
// - Origin host === home_url/site_url host
// - Referer starting with home_url('/') or site_url('/')  (trailing slash, so
//   https://example.com.evil.com/ does NOT prefix-match https://example.com)
// - Origin in the ntdst/api/allowed_origins list
// - NO Origin AND NO Referer AND NO auth cookie  ← returns true

add_filter('ntdst/api/allowed_origins', function ($origins) {
    $origins[] = 'https://trusted-domain.com';
    return $origins;
});
```

That last branch is the one to internalise: **a request with no headers and no session
passes.** The control protects a *logged-in* user's browser from cross-site
request-forgery; it is not an authentication gate and never was. A non-browser client
(curl, a script) simply omits both headers and is admitted. Public actions must therefore
carry their own authorization — see the post-type gate above.

This filter widens the **same-origin** allow-list. It does not turn `Endpoints` into a
cross-origin JSON API; that is `ntdst_router()->rest()` + `NTDST_Cors_Policy`.

### Nonce Verification

Every action request requires a valid nonce:

```php
if (!wp_verify_nonce($nonce, $action)) {
    return $this->error('Invalid or expired nonce', 'invalid_nonce');
}
```

### Input Sanitization

Always sanitize input parameters:

```php
add_filter('ntdst/api_data/my_action', function ($data, $params) {
    // Sanitize all input
    $id = absint($params['id'] ?? 0);
    $title = sanitize_text_field($params['title'] ?? '');
    $content = wp_kses_post($params['content'] ?? '');
    $email = sanitize_email($params['email'] ?? '');

    // Validate
    if (!$id) {
        return new WP_Error('invalid_input', 'Invalid ID');
    }

    // Use Data Manager for database operations
    $model = ntdst_data()->get('my_type');
    // ...
}, 10, 2);
```

### Capability Checks

Verify user permissions for sensitive actions:

```php
add_filter('ntdst/api_data/admin_action', function ($data, $params) {
    if (!current_user_can('manage_options')) {
        return new WP_Error('forbidden', 'Permission denied');
    }

    // Admin-only logic using Data Manager...
}, 10, 2);
```

### Authorization idiom — three rules

Each of these was learned the hard way; two of them shipped live disclosures.

**1. `edit_posts` is NOT authorization.** It means "may create and edit MY OWN posts",
and **Contributors and Authors hold it**. Gating a read path on it hands every non-public
row to the lowest content role. This shipped twice, in different files, both times with a
comment claiming it meant "editors only". A handler that returns *everyone's* rows
implies `edit_others_posts` — "may edit posts belonging to someone else".

**2. Read the capability OFF THE TYPE OBJECT, never as a literal.**

```php
// ✓ follows the type; survives a per-type capability map
$type = get_post_type_object('release');
$cap  = ($type instanceof WP_Post_Type && is_string($type->cap->edit_others_posts ?? null))
      ? $type->cap->edit_others_posts : '';
$mayReadOthers = $cap !== '' && current_user_can($cap);

// ✗ correct only while capability_type === 'post'
if (!current_user_can('edit_others_posts')) { ... }
```

The literal and the mapped answer coincide for a `capability_type => 'post'` type — and
stop coinciding the moment anyone gives that type its own capability type, which is a
standard hardening. The literal then silently admits every generic Editor to a type that
no longer means to grant them anything. **Resolve and validate BEFORE calling
`current_user_can()`** — a non-string capability must deny, not be passed in.

**3. Defence in depth: gate the FETCH as well as the response.**

```php
$release = $model->find($id, $mayReadOthers ? 'any' : ['publish']);
// ... then the handler's own gate STAYS, as an independent second control
```

An unprivileged caller's embargoed row is then never loaded at all, so a later mistake in
the gate has nothing left to leak.

### Never return a raw `WP_Post` from a public handler

`find()` populates `->meta` with **every** meta row including protected `_`-prefixed
keys, and `json_encode` serialises all of `WP_Post`'s public properties — `post_password`
among them. Nothing downstream filters. Project an explicit **allow-list**, built by
iterating the declared schema rather than by filtering `->fields`:

```php
$declared = [];
foreach (array_keys($model->getSchema()) as $field) {
    $declared[$field] = ($post->fields[$field] ?? null);
}
return array_merge($declared, [
    'id' => (int) $post->ID, 'title' => $post->post_title,
    'excerpt' => $post->post_excerpt, 'permalink' => get_permalink($post->ID),
]);
```

Iterating the schema makes the projection the contract in both directions: a declared
field can never go missing, and an undeclared one can never leak even if the layer later
hands back more than it was asked for. A denylist of known-bad keys fails the moment
someone adds a field. Note that a top-level projection does **not** filter repeater
sub-keys — project those rows too.

---

## Response Format

### Success Response

```json
{
  "success": true,
  "data": {
    // Your response data
  }
}
```

### Error Response

```json
{
  "success": false,
  "data": {
    "message": "Human-readable error message",
    "code": "error_code"
  }
}
```

### Standard Error Codes

| Code | Description |
|------|-------------|
| `missing_params` | Required parameters missing |
| `missing_action` | No action specified |
| `invalid_nonce` | Nonce expired or invalid |
| `unknown_action` | No handler for action |
| `not_found` | Resource not found |
| `forbidden` | Permission denied |
| `empty_search` | Empty search term |
| `forbidden_post_type` | The caller may not query any of the requested post types |

### Returning Errors from Handlers

Always use WP_Error for errors:

```php
// Return WP_Error (recommended)
return new WP_Error('my_error', 'Something went wrong');

// WP_Error with additional data
return new WP_Error('validation_failed', 'Invalid email', ['field' => 'email']);
```

---

## Built-in Actions

All three run their caller-supplied post-type / user input through the gates described in
[Public vs Protected Actions](#public-vs-protected-actions) before querying.

### get_recent_posts

Fetch recent posts of any type. **Public.**

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `post_type` | string or array | `'post'` | Post type slug(s). Non-string elements are dropped, not coerced. |
| `per_page` | int | `10` | Number of posts (floored at 1) |

Returns `WP_Error('forbidden_post_type')` when **none** of the requested types is
queryable by this caller. There is no `use_cache` parameter — there is no cache.

**Response** — every row is the standard formatted shape:
```json
{
  "posts": [
    {
      "id": 123,
      "title": "Post Title",
      "slug": "post-slug",
      "content": "…",
      "excerpt": "Post excerpt…",
      "permalink": "https://site.com/post-slug/",
      "date": "2024-01-15T10:30:00+00:00",
      "modified": "2024-01-16T09:00:00+00:00",
      "author": { "id": 1, "name": "Jane" },
      "thumbnail": { "id": 45, "url": "…-300x200.jpg", "full": "….jpg" }
    }
  ]
}
```

`date` / `modified` are **ISO 8601**, not raw MySQL datetimes. `thumbnail` is an object
or `null`. `meta` / `terms` appear only when the handler passes `include_meta` /
`include_terms` — the built-in handler does not.

### search_posts

Search posts by keyword. **Public.**

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search` | string | required | Search term; empty returns `WP_Error('empty_search')` |
| `post_types` | array | `['post', 'page']` | Post types to search |

A **mixed** list keeps its allowed half rather than erroring out — refusing the whole
request because one named type is non-public would turn an authorization gate into an
availability regression on a public endpoint. Only an entirely-disallowed list returns
`forbidden_post_type`.

When `attachment` is among the allowed types, `post_status` widens to
`['publish', 'inherit']` (attachments are never `publish`, so an attachment-scoped
relation autocomplete would otherwise always return nothing). For callers without both
attachment `edit_posts` and `edit_others_posts`, non-viewable parents are excluded via
`post_parent__not_in` — in the **query args**, so the two caller classes can never share
a cache entry.

**Response:** `{ "results": [ …same formatted rows as above… ] }`

### search_users

Search users by name/email. **NOT public** — requires
`current_user_can('list_users')`, because listing users by email/login is a PII leak.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search` | string | required | Search term (wrapped in `*…*`) |
| `role` | string | `''` | Filter by role |
| `per_page` | int | `20` | Number of results |

**Response** — note each row carries both casings, for legacy callers:
```json
{
  "results": [
    {
      "ID": 1,
      "id": 1,
      "post_title": "Display Name",
      "title": "Display Name",
      "user_email": "user@example.com",
      "user_login": "username"
    }
  ]
}
```

---

## Anti-Patterns

### Manual fetch() Calls

```javascript
// WRONG - Bypasses security features
fetch('/wp-json/ntdst/v1/action', {
    method: 'POST',
    body: JSON.stringify({ action: 'my_action' })
});
```

**Fix:** Use the ntdstAPI client:

```javascript
// CORRECT
await ntdstAPI.call('my_action', params);
```

### Direct Database Access

```php
// WRONG - Bypasses ORM validation and hooks
add_filter('ntdst/api_data/save', function ($data, $params) {
    update_post_meta($params['id'], 'field', $params['value']);
    return ['saved' => true];
}, 10, 2);
```

**Fix:** Use Data Manager:

```php
// CORRECT
add_filter('ntdst/api_data/save', function ($data, $params) {
    $model = ntdst_data()->get('my_type');
    $result = $model->update($params['id'], [
        'field' => $params['value'],
    ]);

    if (is_wp_error($result)) {
        return $result;
    }

    return ['saved' => true];
}, 10, 2);
```

### Missing Input Sanitization

```php
// WRONG - Security vulnerability
add_filter('ntdst/api_data/save', function ($data, $params) {
    $title = $params['title'];  // Unsanitized!
    // ...
}, 10, 2);
```

**Fix:** Always sanitize:

```php
// CORRECT
$title = sanitize_text_field($params['title'] ?? '');
```

### Returning null/false on Error

```php
// WRONG - Unclear error
add_filter('ntdst/api_data/my_action', function ($data, $params) {
    if (!$valid) {
        return null;  // What happened?
    }
}, 10, 2);
```

**Fix:** Return WP_Error:

```php
// CORRECT
if (!$valid) {
    return new WP_Error('invalid_data', 'Validation failed');
}
```

### Skipping Capability Checks

```php
// WRONG - Anyone can call this
add_filter('ntdst/api_data/delete_item', function ($data, $params) {
    $model = ntdst_data()->get('portfolio');
    $model->delete($params['id']);
    return ['deleted' => true];
}, 10, 2);
```

**Fix:** Check permissions:

```php
// CORRECT
add_filter('ntdst/api_data/delete_item', function ($data, $params) {
    $id = absint($params['id'] ?? 0);

    if (!current_user_can('delete_post', $id)) {
        return new WP_Error('forbidden', 'Cannot delete this item');
    }

    $model = ntdst_data()->get('portfolio');
    $result = $model->delete($id);

    if (is_wp_error($result)) {
        return $result;
    }

    return ['deleted' => true];
}, 10, 2);
```

### Not Handling Async Errors

```javascript
// WRONG - Unhandled promise rejection
ntdstAPI.call('my_action', params);
```

**Fix:** Use try/catch:

```javascript
// CORRECT
try {
    const data = await ntdstAPI.call('my_action', params);
} catch (error) {
    showError(error.message);
}
```

---

## Quick Reference

### Register a Public Action

```php
// 1. Add to public actions list
add_filter('ntdst/api/public_actions', function ($actions) {
    $actions[] = 'my_public_action';
    return $actions;
});

// 2. Register handler
add_filter('ntdst/api_data/my_public_action', function ($data, $params) {
    $model = ntdst_data()->get('portfolio');
    $items = $model->where('featured', true)->limit(10)->get();

    return ['items' => $items];
}, 10, 2);
```

### Register a Protected Action

```php
add_filter('ntdst/api_data/my_protected_action', function ($data, $params) {
    if (!is_user_logged_in()) {
        return new WP_Error('unauthorized', 'Login required');
    }

    $model = ntdst_data()->get('user_data');
    $data = $model->where('user_id', get_current_user_id())->first();

    return ['user_data' => $data];
}, 10, 2);
```

### JavaScript Call Pattern

```javascript
async function doAction() {
    try {
        const data = await ntdstAPI.call('action_name', {
            param1: 'value1',
        });
        handleSuccess(data);
    } catch (error) {
        handleError(error);
    }
}
```

### Full Handler Template

```php
add_filter('ntdst/api_data/update_portfolio', function ($data, $params) {
    // 1. Sanitize input
    $id = absint($params['id'] ?? 0);
    $title = sanitize_text_field($params['title'] ?? '');
    $client = sanitize_text_field($params['client'] ?? '');

    // 2. Validate
    if (!$id || empty($title)) {
        return new WP_Error('invalid_input', 'ID and title required');
    }

    // 3. Check permissions
    if (!current_user_can('edit_post', $id)) {
        return new WP_Error('forbidden', 'Cannot edit this item');
    }

    // 4. Use Data Manager for database operations
    $model = ntdst_data()->get('portfolio');
    $result = $model->update($id, [
        'title' => $title,
        'client_name' => $client,
    ]);

    // 5. Handle errors
    if (is_wp_error($result)) {
        return $result;
    }

    // 6. Return success
    return [
        'updated' => true,
        'id' => $id,
    ];
}, 10, 2);
```

### CRUD Operations via API

```php
// CREATE
add_filter('ntdst/api_data/create_portfolio', function ($data, $params) {
    if (!current_user_can('edit_posts')) {
        return new WP_Error('forbidden', 'Cannot create items');
    }

    $model = ntdst_data()->get('portfolio');
    $result = $model->create([
        'title' => sanitize_text_field($params['title'] ?? ''),
        'client_name' => sanitize_text_field($params['client'] ?? ''),
    ]);

    if (is_wp_error($result)) {
        return $result;
    }

    // create() returns the created WP_Post, not an id.
    return ['created' => true, 'id' => (int) $result->ID];
}, 10, 2);

// READ
add_filter('ntdst/api_data/get_portfolio', function ($data, $params) {
    $model = ntdst_data()->get('portfolio');

    // find() is PUBLISH-ONLY by default. Pass 'any' / a status array only when
    // the caller's capability says so — see "Authorization idiom" above.
    $item = $model->find(absint($params['id'] ?? 0));

    // find() returns WP_Post or WP_Error — never null/false. Not-found and
    // wrong-status return the SAME error, deliberately.
    if (is_wp_error($item)) {
        return $item;
    }

    // Never return $item itself — project an allow-list from the schema.
    return ['item' => [
        'id' => (int) $item->ID,
        'title' => $item->post_title,
        'client_name' => $item->fields['client_name'] ?? null,
    ]];
}, 10, 2);

// UPDATE
add_filter('ntdst/api_data/update_portfolio', function ($data, $params) {
    $id = absint($params['id']);

    if (!current_user_can('edit_post', $id)) {
        return new WP_Error('forbidden', 'Cannot edit');
    }

    $model = ntdst_data()->get('portfolio');
    $result = $model->update($id, [
        'title' => sanitize_text_field($params['title']),
    ]);

    return is_wp_error($result) ? $result : ['updated' => true];
}, 10, 2);

// DELETE
add_filter('ntdst/api_data/delete_portfolio', function ($data, $params) {
    $id = absint($params['id']);

    if (!current_user_can('delete_post', $id)) {
        return new WP_Error('forbidden', 'Cannot delete');
    }

    $model = ntdst_data()->get('portfolio');
    $result = $model->delete($id);

    return is_wp_error($result) ? $result : ['deleted' => true];
}, 10, 2);
```
