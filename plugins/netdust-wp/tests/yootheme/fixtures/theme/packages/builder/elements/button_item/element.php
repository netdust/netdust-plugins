<?php
namespace YOOtheme;
return [
    'name' => 'button_item',
    'title' => 'button_item',
    'defaults' => ['button_style' => 'default', 'icon_align' => 'left', 'dialog_layout' => 'modal', 'dialog_offcanvas_flip' => true],
    'templates' => ['render' => __DIR__ . '/templates/template.php'],
    'fields' => [
        'content' => ['source' => true], 'link' => '${builder.link}', 'link_target' => [], 'lightbox' => [], 'button_style' => [], 'icon' => [], 'icon_align' => [], 'dialog' => [], 'dialog_layout' => [], 'dialog_offcanvas_flip' => [], 'advanced' => '${builder.advancedItem}'
    ],
];
