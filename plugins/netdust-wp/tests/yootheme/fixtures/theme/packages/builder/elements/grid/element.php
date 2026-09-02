<?php
namespace YOOtheme;
return [
    'name' => 'grid',
    'title' => 'grid',
    'container' => true, 'defaults' => ['show_title' => true, 'show_meta' => true, 'show_content' => true, 'show_image' => true, 'show_link' => true, 'grid_default' => '1', 'grid_medium' => '3'],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'show_image' => [], 'show_title' => [], 'show_meta' => [], 'show_content' => [], 'show_link' => [], 'grid_default' => [], 'grid_small' => [], 'grid_medium' => [], 'grid_large' => [],
        'grid_column_gap' => [], 'grid_row_gap' => [], 'grid_divider' => [], 'panel_style' => [], 'panel_padding' => [], 'panel_link' => ['enable' => 'show_link'], 'panel_match' => [], 'content_align' => [],
        'title_element' => [], 'title_style' => [], 'meta_style' => [], 'meta_align' => [], 'image_width' => [], 'image_height' => [], 'image_align' => [], 'link_style' => [], 'link_text' => [], 'title_margin_auto' => [],
        'margin_top' => '${builder.margin_top}', 'margin_bottom' => '${builder.margin_bottom}', 'advanced' => '${builder.advanced}'
    ],
];
