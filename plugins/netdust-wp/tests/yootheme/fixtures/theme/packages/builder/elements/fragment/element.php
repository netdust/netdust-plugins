<?php
namespace YOOtheme;
return [
    'name' => 'fragment',
    'title' => 'fragment',
    'container' => true, 'fragment' => true, 'defaults' => ['margin_top' => 'default', 'margin_bottom' => 'default'],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'margin_top' => '${builder.margin_top}', 'margin_bottom' => '${builder.margin_bottom}', 'advanced' => '${builder.advanced}'
    ],
];
