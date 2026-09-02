<?php
/**
 * Stand-ins for the YOOtheme classes an element.php touches at INCLUDE time
 * (`Url::to()` in image/video placeholders). Only declared when the real app is
 * not loaded, so `wp eval-file` keeps YOOtheme's own classes.
 */

namespace YOOtheme;

if (!class_exists(Url::class, false)) {
    class Url { public static function __callStatic(string $n, array $a): string { return ''; } }
}
foreach (['View', 'Metadata', 'Config', 'ViewHelper', 'ThemeConfig', 'Arr', 'Str'] as $c) {
    if (!class_exists(__NAMESPACE__ . '\\' . $c, false)) {
        eval("namespace YOOtheme; class $c { public static function __callStatic(string \$n, array \$a) { return ''; } public function __call(string \$n, array \$a) { return ''; } }");
    }
}
if (!function_exists(__NAMESPACE__ . '\\app')) {
    function app(...$a) { return null; }
}
