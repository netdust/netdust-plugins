<?php
// Fixture — the shared field sets of 5.0.43's packages/builder/config/builder.php, trimmed.
return [
    'advanced' => ['title' => 'Advanced', 'fields' => ['name', 'status', 'source', 'id', 'class', 'attributes', 'css', 'transform']],
    'advancedItem' => ['title' => 'Advanced', 'fields' => ['name', 'status', 'source', 'id', 'class', 'attributes', 'css']],
    'name' => ['label' => 'Name'], 'status' => ['type' => 'checkbox'], 'id' => ['label' => 'ID'],
    'cls' => ['label' => 'Classes'], 'attrs' => ['type' => 'editor'], 'transform' => ['type' => 'button'], 'source' => ['type' => 'source'],
    'margin_top' => ['type' => 'select'], 'margin_bottom' => ['type' => 'select'],
    'maxwidth' => ['type' => 'select'], 'maxwidth_breakpoint' => ['type' => 'select'],
    'block_align' => ['type' => 'select', 'enable' => "position != 'absolute' && maxwidth"],
    'block_align_fallback' => ['type' => 'select'], 'block_align_breakpoint' => ['type' => 'select'],
    'text_align' => ['type' => 'select'], 'text_align_breakpoint' => ['type' => 'select'], 'text_align_fallback' => ['type' => 'select'],
    'position' => ['type' => 'select'], 'position_top' => [], 'position_left' => [], 'position_z_index' => [],
    'visibility' => ['type' => 'select'], 'animation' => ['type' => 'select'], 'blend' => ['type' => 'checkbox'],
    'link' => ['type' => 'link'], 'image' => ['type' => 'image'], 'image_alt' => [],
    'column_width_options' => ['-' => '', '1/2' => '1-2'], 'column_width_options_default' => ['-' => ''], 'column_order_first_options' => [],
];
