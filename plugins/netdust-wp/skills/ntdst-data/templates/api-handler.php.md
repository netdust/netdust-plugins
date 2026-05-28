# Template: API Handler

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

    // 7. RETURN success data
    return [
        'success' => true,
        'id' => $id,
        'message' => 'Updated successfully',
    ];
}, 10, 2);
```

## Option 2: Via Theme API (in service)

```php
private function init(): void
{
    $theme = ntdst_get(\NTDST_Theme::class);

    // Protected action (requires login + capability)
    $theme->apiAction('{action_name}', [$this, 'handleAction'], [
        'capability' => 'edit_posts',
    ]);
}

public function handleAction($data, $params)
{
    // Same handler logic as above
}
```

## Make Action Public (if needed)

```php
add_filter('ntdst/api/public_actions', function ($actions) {
    $actions[] = '{action_name}';
    return $actions;
});
```

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

```javascript
try {
    const result = await ntdstAPI.call('{action_name}', {
        id: 123,
        title: 'New Title',
        email: 'user@example.com',
    });
    console.log('Success:', result);
} catch (error) {
    console.error('Error:', error.message);
}
```

## Placeholders

| Placeholder | Replace With |
|-------------|--------------|
| `{action_name}` | lowercase_underscore action name |
| `{post_type}` | Post type slug for Data Manager |
