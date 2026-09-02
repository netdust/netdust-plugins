<?php
/**
 * Seed sample posts so a listing has something to bind to, and take them out again.
 *
 *   wp --user=1 eval-file yoo-seed.php <post_type> from=<items.json>   # create
 *   wp --user=1 eval-file yoo-seed.php <post_type> purge                # delete every stamped post
 *
 * items.json: [{"title": "…", "content": "<p>…</p>", "meta": {"client": "…"}, "thumbnail_id": 86,
 *               "terms": {"thema": ["gender"]}}, …]
 *
 * Every post is stamped `_ntdst_sample = 1`, so the whole set comes back out with `purge`
 * (or `wp post delete $(wp post list --post_type=<t> --meta_key=_ntdst_sample --format=ids) --force`).
 * Meta keys are the DECLARED field names; the model's meta_prefix is applied here, because
 * writing `client` where the model reads `_jw_client` stores a key nothing renders.
 * Idempotent on title: an existing stamped post with the same title is updated, not doubled.
 */

if (!defined('WP_CLI') || !WP_CLI) {
    exit("Run via: wp --user=1 eval-file yoo-seed.php <post_type> from=<items.json>|purge\n");
}

$argv = $args ?? [];
$type = array_shift($argv) ?: '';
$op = array_shift($argv) ?: '';
if (!$type || !post_type_exists($type)) WP_CLI::error("post type '$type' is not registered");

if ($op === 'purge') {
    $ids = get_posts(['post_type' => $type, 'posts_per_page' => -1, 'post_status' => 'any', 'fields' => 'ids',
                      'meta_key' => '_ntdst_sample', 'meta_value' => '1']);
    foreach ($ids as $id) wp_delete_post($id, true);
    WP_CLI::success(count($ids) . " sample $type post(s) deleted");
    return;
}

if (!str_starts_with($op, 'from=')) WP_CLI::error('usage: <post_type> from=<items.json> | purge');
$items = json_decode((string) file_get_contents(substr($op, 5)), true);
if (!is_array($items)) WP_CLI::error('items file is not a JSON array');

$prefix = '';
if (function_exists('ntdst_data')) {
    try { $prefix = (string) ntdst_data()->get($type)->getMetaPrefix(); } catch (\Throwable $e) { $prefix = ''; }
}
if ($prefix === '') WP_CLI::warning("no meta_prefix found for '$type' — meta keys are written bare");

$n = 0;
foreach ($items as $i => $item) {
    $title = (string) ($item['title'] ?? "Sample $type " . ($i + 1));
    $existing = get_posts(['post_type' => $type, 'title' => $title, 'post_status' => 'any', 'posts_per_page' => 1,
                           'meta_key' => '_ntdst_sample', 'meta_value' => '1', 'fields' => 'ids']);
    $data = ['post_type' => $type, 'post_status' => 'publish', 'post_title' => $title,
             'post_content' => (string) ($item['content'] ?? ''),
             'post_date' => date('Y-m-d H:i:s', strtotime("-$i days"))];   // spread dates so order:date is stable
    $id = $existing ? wp_update_post(['ID' => $existing[0]] + $data, true) : wp_insert_post($data, true);
    if (is_wp_error($id)) WP_CLI::error($id->get_error_message());
    update_post_meta($id, '_ntdst_sample', '1');
    foreach ((array) ($item['meta'] ?? []) as $k => $v) update_post_meta($id, $prefix . $k, $v);
    if (!empty($item['thumbnail_id'])) set_post_thumbnail($id, (int) $item['thumbnail_id']);
    foreach ((array) ($item['terms'] ?? []) as $tax => $terms) wp_set_object_terms($id, $terms, $tax);
    WP_CLI::log(sprintf('#%d %s', $id, $title));
    $n++;
}
WP_CLI::success("$n sample $type post(s) seeded (stamp _ntdst_sample=1)");
