<?php
namespace YOOtheme;
return [
    'name' => 'row',
    'title' => 'row',
    'container' => true, 'defaults' => ['column_gap' => '', 'row_gap' => ''],
    'panels' => ['builder-row-layout' => ['fields' => [['type' => 'group', 'fields' => [
        ['type' => 'child-prop', 'index' => 0, 'field' => ['name' => 'width_default', 'type' => 'select']],
        ['type' => 'child-prop', 'index' => 0, 'field' => ['name' => 'width_small', 'type' => 'select']],
        ['type' => 'child-prop', 'index' => 0, 'field' => ['name' => 'width_large', 'type' => 'select']],
        ['type' => 'child-prop', 'index' => 0, 'field' => ['name' => 'width_xlarge', 'type' => 'select']],
        ['type' => 'child-prop', 'index' => 0, 'field' => ['name' => 'order_first', 'type' => 'select']],
    ]]]]],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'layout' => ['type' => 'layout'], 'alignment' => ['type' => 'select'], 'column_gap' => [], 'row_gap' => [], 'width' => [], 'width_expand' => [],
        'divider' => [], 'match' => [], 'breakpoint' => [], 'margin_top' => '${builder.margin_top}', 'margin_bottom' => '${builder.margin_bottom}', 'advanced' => '${builder.advanced}'
    ],
];
