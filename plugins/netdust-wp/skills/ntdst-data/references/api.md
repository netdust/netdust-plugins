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

The NTDST API provides a high-performance alternative to WordPress AJAX using the REST API with automatic nonce management.

### Key Features

| Feature | Description |
|---------|-------------|
| Auto-nonce management | Client handles nonce lifecycle |
| Rate limiting | 30 requests per 60 seconds |
| CSRF protection | Origin/referer verification |
| Caching | Built-in post cache with auto-invalidation |
| Filter-based | Actions registered via WordPress filters |

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

    // Use Data Manager for all database operations
    $model = ntdst_data()->get('portfolio');
    $item = $model->find($id);

    // find() returns WP_Post or WP_Error — never null/false.
    if (is_wp_error($item)) {
        return $item;
    }

    // Get meta via Data Manager
    $meta = $model->getMeta($id);

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
    // Only runs if user can edit_posts
    return ['admin' => 'data'];
}, ['capability' => 'edit_posts']);
```

### Handler Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `$data` | `array` | Previous filter data (usually empty) |
| `$params` | `array` | Request parameters from JSON body |

### Return Values

| Return | Result |
|--------|--------|
| Array with data | Success response |
| WP_Error | Converted to error response |
| Empty array | "Unknown action" error |

---

## Public vs Protected Actions

### Default Public Actions

These actions allow nonce generation for non-authenticated users:

```php
private array $public_actions = [
    'get_recent_posts',
    'search_posts',
    'search_users',
    'send_magic_link',
];
```

### Making an Action Public

```php
add_filter('ntdst/api/public_actions', function ($actions) {
    $actions[] = 'my_public_action';
    return $actions;
});
```

### Protected Actions

Any action not in the public list requires the user to be logged in to get a nonce.

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

### Helper Methods

```javascript
// Get recent posts
const posts = await ntdstAPI.getRecentPosts('portfolio', 10);

// Search posts
const results = await ntdstAPI.searchPosts('query', ['post', 'page']);

// Get post details
const data = await ntdstAPI.getPostDetails(123);

// Get taxonomy terms
const terms = await ntdstAPI.getTaxonomyTerms('category');
```

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

        const results = await ntdstAPI.searchPosts(input.value);
        displayResults(results);
    }, 300); // 300ms debounce
}

document.getElementById('search')
    .addEventListener('input', (e) => liveSearch(e.target));
```

### Post List Example

```javascript
async function loadPosts() {
    const posts = await ntdstAPI.getRecentPosts('post', 10);

    const html = posts.map(post => `
        <article>
            ${post.thumbnail ? `<img src="${post.thumbnail}">` : ''}
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

- **Limit:** 30 requests per 60 seconds
- **Scope:** Per IP address
- **Storage:** WordPress transients

```php
private const RATE_LIMIT = 30;
private const RATE_WINDOW = 60;
```

### CSRF Protection

Origin/referer validation ensures requests come from the same site:

```php
// Allowed by default:
// - Requests with no origin/referer (same-origin)
// - Requests matching home_url or site_url

// Add custom allowed origins:
add_filter('ntdst/api/allowed_origins', function ($origins) {
    $origins[] = 'https://trusted-domain.com';
    return $origins;
});
```

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

### get_recent_posts

Fetch recent posts of any type.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `post_type` | string | `'post'` | Post type slug |
| `per_page` | int | `10` | Number of posts |
| `use_cache` | bool | `true` | Use cached results |

**Response:**
```json
{
  "posts": [
    {
      "id": 123,
      "title": "Post Title",
      "slug": "post-slug",
      "excerpt": "Post excerpt...",
      "permalink": "https://site.com/post-slug/",
      "thumbnail": "https://site.com/image.jpg",
      "date": "2024-01-15 10:30:00",
      "meta": {...}
    }
  ]
}
```

### search_posts

Search posts by keyword.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search` | string | required | Search term |
| `post_types` | array | `['post', 'page']` | Post types to search |

**Response:**
```json
{
  "results": [
    {
      "id": 123,
      "title": "Matching Post",
      "permalink": "https://site.com/matching-post/"
    }
  ]
}
```

### search_users

Search users by name/email.

**Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search` | string | required | Search term |
| `role` | string | `''` | Filter by role |
| `per_page` | int | `20` | Number of results |

**Response:**
```json
{
  "results": [
    {
      "id": 1,
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
        'title' => sanitize_text_field($params['title']),
        'client_name' => sanitize_text_field($params['client']),
    ]);

    if (is_wp_error($result)) {
        return $result;
    }

    return ['created' => true, 'id' => $result];
}, 10, 2);

// READ
add_filter('ntdst/api_data/get_portfolio', function ($data, $params) {
    $model = ntdst_data()->get('portfolio');
    $item = $model->find(absint($params['id']));

    // find() returns WP_Post or WP_Error — never null/false.
    if (is_wp_error($item)) {
        return $item;
    }

    return ['item' => [
        'id' => $item->ID,
        'title' => $item->post_title,
        'meta' => $model->getMeta($item->ID),
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
