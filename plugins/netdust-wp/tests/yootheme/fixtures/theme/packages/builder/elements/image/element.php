<?php
namespace YOOtheme;
return [
    'name' => 'image',
    'title' => 'image',
    
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'image' => ['type' => 'image', 'source' => true], 'image_alt' => [], 'image_width' => [], 'image_height' => [], 'image_border' => [], 'image_svg_color' => [], 'image_box_shadow' => [], 'link' => '${builder.link}',
        'maxwidth' => '${builder.maxwidth}', 'block_align' => '${builder.block_align}', 'text_align' => '${builder.text_align}', 'position' => '${builder.position}', 'position_top' => '${builder.position_top}', 'position_left' => '${builder.position_left}',
        'margin_top' => '${builder.margin_top}', 'margin_bottom' => '${builder.margin_bottom}', 'animation' => '${builder.animation}', 'advanced' => '${builder.advanced}'
    ],
];
