<?php
namespace YOOtheme;
return [
    'name' => 'button',
    'title' => 'button',
    'container' => true, 'defaults' => ['button_size' => ''],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'button_size' => [], 'grid_column_gap' => [], 'grid_row_gap' => [], 'text_align' => '${builder.text_align}', 'margin_top' => '${builder.margin_top}', 'margin_bottom' => '${builder.margin_bottom}', 'advanced' => '${builder.advanced}'
    ],
];
