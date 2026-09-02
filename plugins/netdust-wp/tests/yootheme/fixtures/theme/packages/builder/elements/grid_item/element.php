<?php
namespace YOOtheme;
return [
    'name' => 'grid_item',
    'title' => 'grid_item',
    'placeholder' => ['props' => ['title' => 'Title', 'meta' => '', 'content' => '', 'image' => '', 'icon' => '']],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'title' => ['source' => true], 'meta' => ['source' => true], 'content' => ['source' => true], 'image' => ['source' => true], 'image_alt' => [], 'link' => '${builder.link}', 'link_text' => [], 'tags' => [], 'panel_style' => [], 'advanced' => '${builder.advancedItem}'
    ],
];
