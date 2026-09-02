<?php
namespace YOOtheme;
return [
    'name' => 'text',
    'title' => 'text',
    'defaults' => ['column_breakpoint' => 'm'],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'content' => ['source' => true], 'text_style' => [], 'text_color' => [], 'text_align' => '${builder.text_align}', 'column_breakpoint' => [], 'dropcap' => [],
        'maxwidth' => '${builder.maxwidth}', 'block_align' => '${builder.block_align}', 'margin_top' => '${builder.margin_top}', 'margin_bottom' => '${builder.margin_bottom}', 'visibility' => '${builder.visibility}', 'advanced' => '${builder.advanced}'
    ],
];
