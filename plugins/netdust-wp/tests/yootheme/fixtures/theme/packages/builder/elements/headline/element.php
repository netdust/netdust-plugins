<?php
namespace YOOtheme;
return [
    'name' => 'headline',
    'title' => 'headline',
    'defaults' => ['title_element' => 'h2', 'title_style' => '', 'image_align' => 'left', 'image_margin' => 'xsmall'],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'content' => ['source' => true], 'title_element' => [], 'title_style' => [], 'title_color' => [], 'title_decoration' => [], 'text_align' => '${builder.text_align}',
        'image' => '${builder.image}', 'image_align' => [], 'image_margin' => [], 'link' => '${builder.link}', 'maxwidth' => '${builder.maxwidth}', 'block_align' => '${builder.block_align}',
        'margin_top' => '${builder.margin_top}', 'margin_bottom' => '${builder.margin_bottom}', 'animation' => '${builder.animation}', 'visibility' => '${builder.visibility}', 'advanced' => '${builder.advanced}'
    ],
];
