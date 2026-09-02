<?php
namespace YOOtheme;
return [
    'name' => 'column',
    'title' => 'column',
    'container' => true, 'defaults' => ['position_sticky_breakpoint' => 'm', 'image_position' => 'center-center'],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'image' => ['type' => 'image'], 'vertical_align' => ['type' => 'select'], 'style' => ['type' => 'select'], 'preserve_color' => [],
        'background_color' => ['type' => 'gradient', 'internal' => 'background_color_gradient', 'enable' => '!style'], 'border' => ['type' => 'checkbox'],
        'text_color' => [], 'padding' => [], 'padding_remove_top' => [], 'position_sticky' => [], 'position_sticky_breakpoint' => [],
        'text_align' => '${builder.text_align}', 'advanced' => '${builder.advanced}'
    ],
];
