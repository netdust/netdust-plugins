# Template: API Handler

> **`api_data` is a fast-AJAX read layer, not a general public API.** An action added to
> `public_actions` is reachable by anyone with caller-supplied params, and
> `verifyOrigin()` does **not** save you: it returns true when there is no `Origin`, no
> `Referer` and no auth cookie. It fails open. Treat every public handler as
> internet-facing.

## Option 1: Via Filter (anywhere)

```php
add_filter('ntdst/api_data/{action_name}', function ($data, $params) {
    // 1. SANITIZE all input
    $id = absint($params['id'] ?? 0);
    $title = sanitize_text_field($params['title'] ?? '');
    $email = sanitize_email($params['email'] ?? '');
    $content = wp_kses_post($params['content'] ?? '');

    // 2. VALIDATE required fields
    if (!$id) {
        return new \WP_Error('invalid_input', 'ID is required', ['status' => 400]);
    }

    if (!is_email($email)) {
        return new \WP_Error('invalid_email', 'Valid email required', ['status' => 400]);
    }

    // 3. CHECK PERMISSIONS (for protected actions)
    if (!current_user_can('edit_post', $id)) {
        return new \WP_Error('forbidden', 'Permission denied', ['status' => 403]);
    }

    // 4. USE DATA MANAGER for database operations
    $model = ntdst_data()->get('{post_type}');
    $result = $model->update($id, [
        'title' => $title,
        'email' => $email,
    ]);

    // 5. HANDLE errors
    if (is_wp_error($result)) {
        return $result;
    }

    // 6. LOG important actions
    ntdst_log()->info('Item updated', [
        'id' => $id,
        'user' => get_current_user_id(),
    ]);

    // 7. RETURN success data.
    //    Return the PAYLOAD only — handle_action wraps it in
    //    {"success": true, "data": …} itself. Putting your own `success` key in
    //    here produces {"success":true,"data":{"success":…}}, which is how a
    //    rejected request once read as a successful one client-side.
    //    Signal failure with WP_Error, never with a `success => false` array.
    return [
        'id' => $id,
        'message' => 'Updated successfully',
    ];
}, 10, 2);
```

An empty array is a legitimate **success** (zero search hits), not an error:
`handle_action` distinguishes "no handler registered" (`has_filter()` false →
`unknown_action`) from "handler returned nothing".

## Option 2: Via Theme API (in service)

```php
private function init(): void
{
    $theme = ntdst_get(\NTDST_Theme::class);

    // Protected action (requires login + capability).
    // apiAction() wraps the callback: a failed capability check returns
    // WP_Error('forbidden', …, ['status' => 403]), which handle_action turns
    // into a proper error response.
    $theme->apiAction('{action_name}', [$this, 'handleAction'], [
        'capability' => 'edit_others_posts',  // see the READ-gate warning below
        'priority'   => 10,
    ]);
}

public function handleAction($data, $params)
{
    // Same handler logic as above
}
```

## Template: a READ handler that returns other people's rows

Three rules, each learned the hard way. Copy this shape rather than reinventing it.

```php
add_filter('ntdst/api_data/get_{post_type}', function ($data, $params) {
    $id = absint($params['id'] ?? 0);
    if (!$id) {
        return new \WP_Error('invalid_input', 'ID is required', ['status' => 400]);
    }

    // 1. `edit_posts` is NOT authorization. It means "may create and edit MY OWN
    //    posts", and Contributors and Authors hold it. A handler that returns
    //    EVERY row of a type implies `edit_others_posts`.
    // 2. Read the capability OFF THE TYPE OBJECT, never as a string literal — the
    //    literal and the mapped answer only coincide while capability_type is
    //    'post', and diverge the moment anyone hardens the type with its own map.
    //    Resolve and validate BEFORE calling current_user_can(); a non-string
    //    capability must deny, not be passed in.
    $type = get_post_type_object('{post_type}');
    $cap  = ($type instanceof \WP_Post_Type && is_string($type->cap->edit_others_posts ?? null))
        ? $type->cap->edit_others_posts
        : '';
    $mayReadOthers = $cap !== '' && current_user_can($cap);

    // 3. Defence in depth: gate the FETCH as well as the response, so an
    //    unprivileged caller's embargoed row is never loaded at all.
    $model = ntdst_data()->get('{post_type}');
    $post  = $model->find($id, $mayReadOthers ? 'any' : ['publish']);

    if (is_wp_error($post)) {
        return $post;  // not-found and wrong-status are the SAME error, by design
    }

    // Never return a raw WP_Post from a public handler: find() populates ->meta
    // with every meta row including protected `_`-prefixed keys, and json_encode
    // serialises all of WP_Post's public properties — post_password among them.
    // Build the allow-list by ITERATING THE DECLARED SCHEMA, so a declared field
    // can never go missing and an undeclared one can never leak.
    $formatted = $post->fields ?? [];
    $projected = [];
    foreach (array_keys($model->getSchema()) as $field) {
        $projected[$field] = $formatted[$field] ?? null;
    }

    return array_merge($projected, [
        'id'        => (int) $post->ID,
        'title'     => $post->post_title,
        'excerpt'   => $post->post_excerpt,
        'permalink' => get_permalink($post->ID),
    ]);
}, 10, 2);
```

**Repeater caveat:** a top-level allow-list does **not** filter repeater sub-keys —
rows are read back through `formatRepeaterField()` largely as stored. If you project a
payload for anonymous callers, project the repeater's rows too.

## Make Action Public (if needed)

```php
add_filter('ntdst/api/public_actions', function ($actions) {
    $actions[] = '{action_name}';
    return $actions;
});
```

Adding an action here means an **anonymous** caller may both mint a nonce for it and
dispatch it. Anything the handler can reach is then internet-reachable.

**Do not take the post type from the caller at all.** There is no framework gate left to
lean on: `canQueryPostType()`, `filterQueryablePostTypes()`, `canQueryUnpublishedMedia()`
and `nonViewableMediaParentIds()` were all DELETED in the v2.4/3.0 sweep, together with
the framework-shipped actions that needed them. Core ships **no data actions**, so a
caller-parameterised query action is now entirely yours to defend, in the handler.

Pin the type in the handler. If a caller genuinely must choose, resolve it against a
closed allow-list you own and **refuse the request when nothing requested is
queryable**, rather than querying first and filtering the rows afterwards: core's
`post-queries` cache keys on the query args and the generated SQL, never on who asked,
so a post-hoc filter lets one actor's answer be served to another. Where a capability
decides, read it OFF THE TYPE OBJECT (`$type->cap->edit_others_posts`) and fail closed
on an empty or non-string value — never a literal.

## Sanitization Reference

| Input Type | Function |
|------------|----------|
| Integer | `absint($params['id'] ?? 0)` |
| Text | `sanitize_text_field($params['text'] ?? '')` |
| Email | `sanitize_email($params['email'] ?? '')` |
| URL | `esc_url_raw($params['url'] ?? '')` |
| HTML | `wp_kses_post($params['content'] ?? '')` |
| Array of text | `array_map('sanitize_text_field', $params['items'] ?? [])` |
| Array of IDs | `array_map('absint', $params['ids'] ?? [])` |
| Boolean | `filter_var($params['flag'] ?? false, FILTER_VALIDATE_BOOLEAN)` |

## JavaScript Usage

The shipped client (`assets/js/ntdst-api.js`) exposes exactly three methods —
`call(action, params)`, `upload(action, formData)`, `download(action, params)` — plus
automatic nonce caching with one transparent retry on `invalid_nonce`. There are no
`getRecentPosts()` / `searchPosts()` convenience wrappers; call the actions by name.

```javascript
try {
    const result = await ntdstAPI.call('{action_name}', {
        id: 123,
        title: 'New Title',
        email: 'user@example.com',
    });
    console.log('Success:', result);   // already unwrapped from the `data` envelope
} catch (error) {
    console.error('Error:', error.message);
}
```

## Placeholders

| Placeholder | Replace With |
|-------------|--------------|
| `{action_name}` | lowercase_underscore action name |
| `{post_type}` | Post type slug for Data Manager |
