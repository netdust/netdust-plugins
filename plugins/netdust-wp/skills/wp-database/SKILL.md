---
name: wp-database
description: Use when WordPress code touches the database with dynamic values — $wpdb->query / $wpdb->get_results / $wpdb->get_var / $wpdb->get_row / $wpdb->insert / $wpdb->update / $wpdb->delete with any variable in the SQL, OR custom tables, OR transients, OR wp_cache_get / wp_cache_set, OR post meta queries with meta_query, OR migration scripts. Triggers on PHP file edits in plugins, themes, mu-plugins. Activates on keywords $wpdb, prepare, get_results, get_var, sql, query, meta_query, IN(, LIKE, ORDER BY $, dbDelta, transient, wp_cache. Symptoms include writing PHP that runs SQL with any variable interpolated into the query string, building meta queries with user input, deciding between post meta vs custom table, caching expensive computations. Do not skip when "the value is hardcoded except one ID", when "it's an internal admin tool", when "we already absint'd it", when "the LIKE pattern is just a constant prefix".
---

# WordPress Database

**Violating the letter of these rules is violating the spirit of these rules.**

Every dynamic value in a SQL statement is a vulnerability vector. WordPress provides `$wpdb->prepare()` for one reason: there is no safe way to interpolate values into SQL by hand. Sanitization is not a substitute. `absint()` is not a substitute. Type casts are not a substitute.

## Core rule

**Any dynamic value in a query → `$wpdb->prepare()`. Always.**

This includes:

- Integers (even `absint()`-clean ones — `prepare` adds the right quoting for the SQL context).
- Strings, even constants computed at runtime.
- Identifiers via `%i` (placeholder available since WP 6.2).
- Values inside `LIKE` patterns — `prepare` handles `%` escaping correctly via `$wpdb->esc_like()`.
- Values inside `IN(...)` lists — use a placeholder per value, not a joined string.
- ORDER BY column names — whitelist against a known set, do NOT interpolate user input.

## Quick reference

### Placeholder cheatsheet

| Placeholder | Use for |
|---|---|
| `%d` | Integers |
| `%f` | Floats |
| `%s` | Strings (auto-quoted) |
| `%i` | Identifiers (table names, column names) — WP 6.2+ |

### LIKE patterns

```php
$like = '%' . $wpdb->esc_like( $needle ) . '%';
$wpdb->prepare( "SELECT * FROM {$wpdb->posts} WHERE post_content LIKE %s", $like );
```

### IN() lists

```php
$ids = array( 1, 2, 3 );
$placeholders = implode( ', ', array_fill( 0, count( $ids ), '%d' ) );
$wpdb->prepare(
    "SELECT * FROM {$wpdb->posts} WHERE ID IN ($placeholders)",
    ...$ids
);
```

### ORDER BY (column whitelist)

```php
$allowed = array( 'post_date', 'post_title', 'menu_order' );
$order_by = in_array( $requested, $allowed, true ) ? $requested : 'post_date';
$wpdb->prepare(
    "SELECT * FROM {$wpdb->posts} ORDER BY {$order_by} %s",
    $direction === 'ASC' ? 'ASC' : 'DESC'
);
```

(The `%s` placeholder for direction with a hard-coded ternary — never interpolate `$direction` raw, even though it "looks simple".)

### Custom tables vs post meta

| Choose post meta | Choose custom table |
|---|---|
| Default case | High write volume (>100/sec sustained) |
| <10k rows per post type | Relational integrity required (FK, indexes) |
| Standard CRUD via WP APIs | Complex queries that post meta cannot serve |
| Search via `meta_query` works | Need composite indexes |

If custom table: register via `dbDelta()` in an upgrade routine, add `$wpdb->charset_collate`, and version the schema (store version in `wp_options`, run upgrades on plugin load).

### Transients vs object cache

| Use transient | Use wp_cache |
|---|---|
| Across requests (DB-backed unless object cache is installed) | Within one request |
| Has expiry | Process-lifetime |
| Network/aggregation results | Repeated computation within a single page load |

### Migrations

- Local: WP-CLI command or admin-triggered button.
- Staging: same WP-CLI command, verified before prod.
- Production: **never** manual `mysql` on prod. Always a script or migration plugin.
- Rollback plan written BEFORE migration.

## One excellent example

A custom table query with whitelisted ORDER BY, prepared LIKE, prepared IN list, and a transient cache:

```php
function netdust_search_orders( string $needle, array $status_ids, string $order_by = 'created_at' ): array {
    global $wpdb;

    $cache_key = 'netdust_orders_' . md5( $needle . wp_json_encode( $status_ids ) . $order_by );
    $cached    = get_transient( $cache_key );
    if ( $cached !== false ) {
        return $cached;
    }

    if ( empty( $status_ids ) ) {
        return array();
    }

    // ORDER BY whitelist — never interpolate user-provided column names.
    $allowed_order = array( 'created_at', 'total', 'customer_name' );
    if ( ! in_array( $order_by, $allowed_order, true ) ) {
        $order_by = 'created_at';
    }

    $table = $wpdb->prefix . 'netdust_orders';
    $like  = '%' . $wpdb->esc_like( $needle ) . '%';

    $placeholders = implode( ', ', array_fill( 0, count( $status_ids ), '%d' ) );

    // `%i` for identifier (WP 6.2+); plain `{$order_by}` is safe because of the whitelist above.
    $sql = $wpdb->prepare(
        "SELECT * FROM %i
         WHERE customer_name LIKE %s
           AND status_id IN ($placeholders)
         ORDER BY {$order_by} DESC
         LIMIT 50",
        $table, $like, ...$status_ids
    );

    $results = $wpdb->get_results( $sql );

    set_transient( $cache_key, $results, 5 * MINUTE_IN_SECONDS );

    return $results;
}
```

Notice: every dynamic value goes through `prepare`. The only thing interpolated raw is `$order_by`, and only because it was whitelist-validated three lines above. The table name uses `%i`. The `IN()` list uses N placeholders, not a joined string.

## Rationalization table

| Excuse | Reality |
|---|---|
| "The value is hardcoded except one ID" | Then `prepare` it with one placeholder. The overhead is zero. |
| "It's already `absint()`'d" | `absint` makes it a non-negative integer. `prepare` adds the SQL quoting AND prevents future drift if the upstream value type changes. Both. |
| "It's just my internal admin tool" | Admin pages get XSSed, sessions get hijacked, attackers reach your SQL. Internal-only is not a security boundary. |
| "The LIKE pattern is a constant prefix" | Then `prepare` it. If you ever concatenate user input later, you've already done it wrong by then. |
| "`(int)` is the same as `%d`" | `(int)` casts. `%d` casts AND adds SQL-context safety. Use `%d`. |
| "I built the SQL with `sprintf`" | `sprintf` does not escape SQL. `prepare` does. Different things. |
| "I'm using `$wpdb->insert()`, no SQL string" | True — `$wpdb->insert/update/delete` auto-prepare based on the format array. But you MUST pass the format array (`%d`, `%s`, etc.), not omit it. |
| "It's a SELECT, no injection risk" | SELECT injection leaks data (UNION attacks). Same severity as INSERT injection — different exploit shape. |
| "WordPress core doesn't use prepare for X" | You are not WordPress core. The core authors have read the SQL by hand. You won't, six months from now. |
| "I'll add prepare later if it becomes a problem" | Later = "after the security report". Cost now: 2 minutes. Cost later: incident response + patches + apologies. |
| "Following the spirit not the letter" | The letter is the spirit. Every dynamic value, every query, always. |

## Loophole closures

- **"I'll use `esc_sql()` instead of `prepare`"** → No. `esc_sql()` only escapes for string context; it does not validate type. `prepare` does both. `esc_sql` is a last resort for places `prepare` can't reach (very rare).
- **"`$wpdb->prepare( "SELECT ... WHERE id = $id" )`"** → No. `$id` is interpolated by PHP BEFORE `prepare` sees the string. `prepare` is now a no-op for that value. Use the placeholder.
- **"`$wpdb->prepare( "SELECT ... %d", absint( $id ) )` is overkill"** → It is not. Belt-and-braces is the price of being right.
- **"`get_results()` doesn't need prepare because it's SELECT-only"** → `get_results` runs whatever SQL you hand it. Prepare the SQL first.
- **"I can ORDER BY user input as long as I `esc_sql()` it"** → No. Whitelist. ORDER BY is identifier context; escaping is for string context.
- **"meta_query is safe because WP_Query handles it"** → WP_Query passes meta_query values through prepare for the value, but the meta_key is NOT validated against your schema. Whitelist meta keys against a known set if they come from user input.

## Common mistakes

- Using `$wpdb->prepare()` with no placeholder in the format string — `prepare` emits a notice and returns the string unmodified. If your format has no `%d/%s/%f/%i`, you don't need prepare for that string (but then you also have no dynamic value, which is the only reason to use prepare).
- Forgetting `array_fill` + `array_map` for `IN()` lists; instead joining ints with `implode(',', $ids)`. The joined string is interpolated raw — even if all values are integers, you've defeated `prepare`.
- Using `%s` for a numeric value. Works, but `%d` is the right placeholder — it guarantees integer.
- `dbDelta()` parsed silently — its SQL parser is strict (single space between PRIMARY KEY and `(`, etc.). Test the upgrade in a fresh DB before shipping.
- Custom table without a `$charset_collate` clause → silent UTF-8 vs latin1 mismatches with the core tables.
- Transient name longer than 172 chars → silently truncated. Use `md5()` to compress long cache keys.

## When in doubt — three questions

1. **Is any value in this SQL string a variable?** → if yes, `prepare`.
2. **Is the value an identifier (table/column name)?** → `%i` (WP 6.2+) or whitelist.
3. **Will this query be run more than once per request?** → cache (transient or wp_cache).

## See also

- `wp-security` for the broader four-pillar framework (this skill is the database pillar).
- `ntdst-data` for the Data Manager pattern that wraps `$wpdb` with type safety.
- `red-tests.md` in this skill folder — pressure scenarios.
- WordPress codex: [Data Validation](https://developer.wordpress.org/apis/security/data-validation/).
