# Golden Path — Admin settings page (register → render → save → store)

**Read this before planning any admin settings/options page.** Build to it; name any deviation in the plan.

**Extracted from** Stride's `StrideSettingsService` (`Stride\Admin\StrideSettingsService`). Verified drift-clean. Genericised `Stride` → `{Project}`.

This is the framework way: a single service owns page registration, asset enqueue, render, and save. The save goes through the **same `ntdst/api_data` AJAX path** as every other write (so the four pillars apply identically — see the form-data-flow golden path), *not* the WP Settings API. That is a deliberate, named choice (Alpine tabbed UI + per-tab save), not drift.

---

## File inventory of the slice

| File | Layer | Responsibility (one line) |
|---|---|---|
| `Admin/{Project}SettingsService.php` | Settings service | `add_submenu_page` + asset enqueue + `renderSettingsPage` + `ntdst/api_data/{action}` save handler + option storage |
| `templates/admin/settings.php` | Page shell | Alpine `x-data` shell + tab nav; `include`s each tab partial |
| `templates/admin/settings/tab-*.php` | Tab partials | One form per tab (Alpine `x-model` bound) |
| `assets/js/admin/settings.js` | Frontend | Alpine component; `ntdstAPI.call()` per-tab save |
| `assets/css/admin/settings.css` | Style | Page layout |

Governing reference: **`ntdst-architecture/references/services.md`** (service lifecycle), **`netdust-wp:wp-security`** (the save's four pillars). This doc shows the settings-specific shape.

---

## The service — `{Project}SettingsService.php`

A **plain class** (no `NTDST_Service_Meta`) instantiated by its owning module — Stride's is owned by `EditionService` because the URL slugs it stores affect CPT registration, and static accessors must be callable at registration time. Option keys are **named constants** (no key-soup), each with a default constant.

```php
<?php
declare(strict_types=1);

namespace {Project}\Admin;

use WP_Error;

class {Project}SettingsService
{
    private const OPTION_URL_SLUGS    = '{project}_url_slugs';      // named option keys — never inline literals
    private const OPTION_COMPANY      = '{project}_company_details';
    private const SETTINGS_SLUG       = '{project}-settings';
    private const CAPABILITY          = 'manage_options';           // ONE capability, referenced everywhere
    private const DEFAULT_SLUGS       = ['edition' => 'edities'];
    private const DEFAULT_COMPANY     = ['name' => '', 'vat' => '', 'email' => '', 'logo' => ''];

    public function __construct()
    {
        $this->init();
    }

    private function init(): void
    {
        add_action('admin_menu', [$this, 'registerSettingsPage'], 20);
        add_action('admin_enqueue_scripts', [$this, 'enqueueAssets']);
        // SAVE goes through the framework AJAX path — same edge guarantees (nonce+login) as every flow.
        add_filter('ntdst/api_data/{project}_save_settings', [$this, 'handleSaveSettings'], 10, 2);
    }

    // ── STATIC ACCESSORS — readable at CPT-registration time, before the service boots ──
    public static function getEditionSlug(): string
    {
        $slugs = get_option(self::OPTION_URL_SLUGS, self::DEFAULT_SLUGS);
        return $slugs['edition'] ?? self::DEFAULT_SLUGS['edition'];
    }

    public static function getCompanyDetails(): array
    {
        $details = get_option(self::OPTION_COMPANY, self::DEFAULT_COMPANY);
        return array_merge(self::DEFAULT_COMPANY, is_array($details) ? $details : []);
    }

    // ── REGISTRATION ──
    public function registerSettingsPage(): void
    {
        add_submenu_page(
            '{project}-dashboard',            // parent menu
            'Instellingen',                   // page title
            'Instellingen',                   // menu label
            self::CAPABILITY,                 // PILLAR 2 — capability gates menu visibility
            self::SETTINGS_SLUG,
            [$this, 'renderSettingsPage']
        );
    }

    // ── ASSET ENQUEUE (only on this page) ──
    public function enqueueAssets(string $hook): void
    {
        if (!str_contains($hook, self::SETTINGS_SLUG)) {
            return;   // never enqueue globally — gate on the page hook
        }
        wp_enqueue_media();                   // logo picker
        ntdst_enqueue_api_client();           // window.ntdstAPI

        wp_enqueue_script('alpinejs',
            'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js', [], '3', ['strategy' => 'defer']);

        $basePath = dirname(__DIR__);
        $jsFile = $basePath . '/assets/js/admin/settings.js';
        if (file_exists($jsFile)) {
            // settings.js loads BEFORE Alpine so the component factory is defined when Alpine boots.
            wp_enqueue_script('{project}-settings',
                plugins_url('assets/js/admin/settings.js', $basePath . '/{project}-core.php'),
                ['ntdst-api'], (string) filemtime($jsFile), false /* in <head> */);
        }
        wp_localize_script('{project}-settings', '{project}Settings', $this->getLocalizedData());
    }

    // ── RENDER ──
    public function renderSettingsPage(): void
    {
        if (!current_user_can(self::CAPABILITY)) {     // PILLAR 2 — re-check at render (defence in depth)
            return;
        }
        $templatePath = dirname(__DIR__) . '/templates/admin/settings.php';
        if (file_exists($templatePath)) {
            include $templatePath;          // direct admin-page include — NOT ob_start+include (cat-4 exception)
        }
    }

    // ── SAVE — runs behind the ntdst/api_data edge (nonce+login already verified) ──
    public function handleSaveSettings(mixed $data, array $params): array|WP_Error
    {
        if (!current_user_can(self::CAPABILITY)) {     // PILLAR 2 — the handler re-checks; the edge does NOT know your cap
            return new WP_Error('forbidden', __('Onvoldoende rechten.', '{project}'));
        }
        $tab = sanitize_text_field($params['tab'] ?? '');   // PILLAR 3
        return match ($tab) {
            'general' => $this->saveGeneralSettings($params),
            'company' => $this->saveCompanySettings($params),
            default   => new WP_Error('invalid_tab', __('Onbekend tabblad.', '{project}')),
        };
    }

    private function saveGeneralSettings(array $params): array
    {
        $slugs = [
            'edition' => !empty($params['edition_slug'])
                ? sanitize_title($params['edition_slug'])      // PILLAR 3 — slug-appropriate sanitiser
                : self::DEFAULT_SLUGS['edition'],
        ];
        update_option(self::OPTION_URL_SLUGS, $slugs);          // store under the named constant
        delete_option('rewrite_rules');                         // flush so new slugs take effect
        return ['message' => 'Instellingen opgeslagen.'];
    }

    private function saveCompanySettings(array $params): array
    {
        // PILLAR 3 — sanitiser chosen PER FIELD TYPE: text / email / url.
        $details = [
            'name'  => sanitize_text_field($params['name'] ?? ''),
            'vat'   => sanitize_text_field($params['vat'] ?? ''),
            'email' => sanitize_email($params['email'] ?? ''),
            'logo'  => esc_url_raw($params['logo'] ?? ''),       // URL sanitiser, not text
        ];
        update_option(self::OPTION_COMPANY, $details);
        return ['message' => 'Bedrijfsgegevens opgeslagen.'];
    }
}
```

**`include $templatePath` is the documented cat-4 exception, not drift.** The drift pattern is `ob_start()` + `include` to *capture* markup into a string in a service. This is a top-level admin-page callback whose job is literally to emit the page — there is no buffering and no string capture. `ntdst_response()->render()` is for routed front-end templates, not `add_submenu_page` callbacks.

---

## The page shell — `templates/admin/settings.php`

Alpine `x-data` shell, tab nav, conditional `include` of each tab partial. **PILLAR 4 — every echoed value is escaped** (`esc_attr` for attributes, `esc_html` for text).

```php
<?php
/** Settings shell — loaded by renderSettingsPage(). Data in window.{project}Settings. */
defined('ABSPATH') || exit;

$tabs = [
    'general' => ['label' => 'Algemeen', 'icon' => 'dashicons-admin-generic'],
    'company' => ['label' => 'Bedrijf',  'icon' => 'dashicons-building'],
];
$templateDir = __DIR__ . '/settings';
?>
<div class="wrap" x-data="{project}SettingsApp()" x-cloak>
    <div x-show="message" x-transition.opacity
         :class="messageType === 'error' ? 'notice notice-error' : 'notice notice-success'">
        <p x-text="message"></p>            <!-- x-text, not innerHTML — no XSS sink -->
    </div>
    <nav class="settings__nav">
        <?php foreach ($tabs as $tabKey => $tab): ?>
            <button type="button"
                    :class="{ 'is-active': activeTab === '<?php echo esc_attr($tabKey); ?>' }"
                    @click="switchTab('<?php echo esc_attr($tabKey); ?>')">     <!-- PILLAR 4 -->
                <span class="dashicons <?php echo esc_attr($tab['icon']); ?>"></span>
                <?php echo esc_html($tab['label']); ?>                          <!-- PILLAR 4 -->
            </button>
        <?php endforeach; ?>
    </nav>
    <div class="settings__content">
        <div x-show="activeTab === 'general'">
            <?php if (file_exists($templateDir . '/tab-general.php')) include $templateDir . '/tab-general.php'; ?>
        </div>
        <!-- … one x-show block per tab … -->
    </div>
</div>
```

---

## The frontend — `assets/js/admin/settings.js`

Alpine component factory (defined before Alpine boots, see the enqueue order). Per-tab save via `ntdstAPI.call()` — **never raw `fetch()`**, so the nonce/edge plumbing is handled.

```js
function {project}SettingsApp() {
    return {
        activeTab: 'general',
        message: '',
        ...window.{project}Settings,         // localized initial state
        switchTab(tab) { this.activeTab = tab; },
        async saveTab() {
            const res = await ntdstAPI.call('{project}_save_settings', {
                tab: this.activeTab,
                ...this.fieldsForActiveTab(),
            });
            this.message = res.message;        // x-text bound — safe
        },
    };
}
```

---

## How to adapt — what changes per project, what never does

**Changes per project:**
1. **Option keys** — the `OPTION_*` constants + their `DEFAULT_*` companions.
2. **Capability** — the `CAPABILITY` constant (`manage_options` for site-wide, a custom cap for scoped access).
3. **Menu placement** — parent slug in `add_submenu_page` (top-level vs under your dashboard).
4. **Tabs + fields** — the `$tabs` array, the `match($tab)` arms, and the per-field sanitisers.
5. **Sanitisers** — one per field by type (`sanitize_text_field` / `sanitize_email` / `esc_url_raw` / `sanitize_title` / `sanitize_hex_color`).
6. **Side effects on save** — e.g. `delete_option('rewrite_rules')` after a slug change; whatever your option invalidates.
7. **Owner** — which module instantiates the service (only matters if static accessors are needed at registration time).

**Never changes:**
- Save runs through `ntdst/api_data/{action}`, never raw `wp_ajax_*` or a hand-rolled `admin-post.php` handler.
- Capability checked at **both** render and save (the edge verifies nonce+login, not *your* capability).
- Every field sanitised on input with a type-appropriate function.
- Every echoed value escaped on output (`esc_attr`/`esc_html`).
- Options stored under named constants, never inline string literals.
- Assets enqueued only on the page hook, never globally.
- Frontend uses `ntdstAPI.call()`.

> **Settings-API alternative.** If the page is a simple flat option set with no tabbed/Alpine UI, `register_setting()` + `settings_fields()` + `do_settings_sections()` is also framework-acceptable and gets WP's nonce + sanitise-callback for free. The choice between the two is a **named decision in the plan** — the AJAX-filter path (shown here) is right for multi-tab/dynamic UIs; the Settings API is right for static field lists. Either is fine; an *unnamed* choice is the deviation.

---

## Cross-references

- Governing references: `ntdst-architecture/references/services.md`, `netdust-wp:wp-security` (the save's four pillars), `references/response.md` (when a settings *action* needs a routed template).
- Anti-patterns this slice satisfies: `anti-patterns.md` → *Missing Capability Checks*, *Unsanitized Input*, *Unescaped Output*, *Manual fetch()*, *Echo in Services* (the service delegates rendering to a template, doesn't echo markup itself).
- Drift categories satisfied: **3** (framework AJAX path), **4** (the include is the documented exception, not `ob_start` capture). Maps to `wp-plan-requirements` Blocks 1 + 2.
- The settings *save* is itself a form/data-flow — see `golden-paths/form-data-flow.md` for the pillar-by-pillar AJAX contract this reuses.
