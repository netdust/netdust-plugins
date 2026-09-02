<?php
namespace YOOtheme;
return [
    'name' => 'section',
    'title' => 'section',
    'container' => true, 'defaults' => ['style' => 'default', 'width' => 'default', 'vertical_align' => 'middle', 'title_position' => 'top-left', 'title_rotation' => 'left', 'title_breakpoint' => 'xl', 'image_position' => 'center-center'],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'image' => ['type' => 'image', 'source' => true], 'video' => ['type' => 'video'], '_media' => ['type' => 'button-panel'],
        'title' => [], 'style' => ['type' => 'select'], 'background_color' => ['type' => 'gradient', 'internal' => 'background_color_gradient', 'enable' => '!style'],
        'text_color' => [], 'width' => [], 'padding_top' => [], 'padding_bottom' => [], 'height' => [], 'height_viewport' => [],
        'header_transparent' => [], 'sticky' => [], 'preserve_color' => [], 'image_size' => [], 'image_width' => [], 'image_height' => [],
        'media_overlay' => [], 'animation' => '${builder.animation}', 'advanced' => '${builder.advanced}'
    ],
];
