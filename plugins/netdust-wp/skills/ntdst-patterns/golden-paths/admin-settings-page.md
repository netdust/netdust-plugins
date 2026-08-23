# Golden Path — Admin settings page (register → render → save → store)

> **Rewritten for ntdst-core 5.0.0** — anchored on `api/Rest.php` (`NTDST_Rest`), `api/Response.php` (`NTDST_Response::html()`). Re-verify with the drift-reviewer grep set when the source moves; `/skill-audit` flags this after 90 days.

**Read this before planning any admin settings/options page.** Build to it; name any deviation in the plan. 5.0.0 removed the old AJAX command dispatcher outright — the save now goes through a capability-gated `ntdst_rest()` route (or the WordPress Settings API), the **same ONE HTTP surface** every write in the project uses.

`NTDST_Response::render()` echoes and exits — right for a routed front-end template, wrong here: `add_submenu_page`'s callback runs inside WordPress's own admin chrome, which still has a footer and scripts to print after your callback returns. This slice uses **`ntdst_response()->html()`**, which returns a string instead of exiting, so the admin page renderer keeps control.

---

## File inventory of the slice

| File | Layer | Responsibility (one line) |
|---|---|---|
| `Admin/{Project}SettingsService.php` | Settings service | `add_submenu_page` + asset enqueue + render + the save route |
| `templates/admin/settings.php` | Page shell | Alpine `x-data` shell + tab nav; `include`s each tab partial |
| `templates/admin/settings/tab-*.php` | Tab partials | One form per tab (Alpine `x-model` bound) |
| `assets/js/admin/settings.js` | Frontend | Alpine component; `wp.apiFetch` per-tab save |

Governing reference: **`ntdst-framework/SKILL.md`** (`## Rest is the one surface`, `## Pages on rewrite rules`), **`netdust-wp:wp-security`**. This doc shows the settings-specific shape those rules produce.

The code below is one worked example (`Acme\Admin\AcmeSettingsService`) so it is real, lintable PHP — rename the namespace and class to your own project's.

---

## The service — `{Project}SettingsService.php`

A **plain class** (not a service that hooks `NTDST_Service_Meta` — unless it also needs its own lifecycle priority) instantiated by its owning module. Option keys are **named constants**, never inline literals.

```php
<?php
declare(strict_types=1);

namespace Acme\Admin;

use WP_Error;
use WP_REST_Request;
use WP_REST_Response;

final class AcmeSettingsService
{
    private const OPTION_COMPANY  = '{project}_company_details';
    private const SETTINGS_SLUG   = '{project}-settings';
    private const CAPABILITY      = 'manage_options';           // ONE capability, referenced everywhere
    private const DEFAULT_COMPANY = ['name' => '', 'vat' => '', 'email' => ''];

    public function __construct()
    {
        $this->init();
    }

    private function init(): void
    {
        add_action('admin_menu', [$this, 'registerSettingsPage'], 20);
        add_action('admin_enqueue_scripts', [$this, 'enqueueAssets']);

        // SAVE — a capability-gated ntdst_rest() route, the same ONE HTTP
        // surface every write in the project goes through.
        ntdst_rest('{project}/v1')->post('/settings', [$this, 'handleSave'], [
            'permission' => self::CAPABILITY,   // internal write — capability, not a posture
        ]);
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
            '{project}-dashboard',
            'Instellingen',
            'Instellingen',
            self::CAPABILITY,                 // capability gates menu visibility
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

        wp_enqueue_script('alpinejs',
            'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js', [], '3', ['strategy' => 'defer']);

        $basePath = dirname(__DIR__);
        $jsFile   = $basePath . '/assets/js/admin/settings.js';

        if (file_exists($jsFile)) {
            // settings.js loads BEFORE Alpine so the component factory exists
            // when Alpine boots. 'wp-api-fetch' is the dependency — the save
            // path uses wp.apiFetch, so no manual nonce plumbing.
            wp_enqueue_script('{project}-settings',
                plugins_url('assets/js/admin/settings.js', $basePath . '/{project}-core.php'),
                ['wp-api-fetch'], (string) filemtime($jsFile), false);
        }

        wp_localize_script('{project}-settings', '{project}Settings', $this->getLocalizedData());
    }

    private function getLocalizedData(): array
    {
        return ['company' => self::getCompanyDetails()];
    }

    // ── RENDER — via html(), never render() ──
    public function renderSettingsPage(): void
    {
        if (!current_user_can(self::CAPABILITY)) {     // re-checked at render (defence in depth)
            return;
        }

        // html() RETURNS a string instead of echoing-and-exiting — render()
        // would exit before WordPress prints the admin footer/scripts.
        echo ntdst_response()
            ->with('tabs', ['general' => 'Algemeen', 'company' => 'Bedrijf'])
            ->html('admin/settings');
    }

    // ── SAVE — behind the capability-gated route above ──
    public function handleSave(WP_REST_Request $request): WP_REST_Response|WP_Error
    {
        if (!current_user_can(self::CAPABILITY)) {     // the ROUTE already checked this; re-checked here on purpose
            return new WP_Error('forbidden', __('Onvoldoende rechten.', '{project}'), ['status' => 403]);
        }

        $tab = sanitize_text_field((string) $request->get_param('tab'));

        return match ($tab) {
            'company' => $this->saveCompanySettings($request),
            default   => new WP_Error('invalid_tab', __('Onbekend tabblad.', '{project}'), ['status' => 422]),
        };
    }

    private function saveCompanySettings(WP_REST_Request $request): WP_REST_Response
    {
        $details = [
            'name'  => sanitize_text_field((string) $request->get_param('name')),
            'vat'   => sanitize_text_field((string) $request->get_param('vat')),
            'email' => sanitize_email((string) $request->get_param('email')),
        ];

        update_option(self::OPTION_COMPANY, $details);

        return new WP_REST_Response(['message' => 'Bedrijfsgegevens opgeslagen.'], 200);
    }
}
```

**Why the handler re-checks `current_user_can()` even though the route already declared `'permission' => self::CAPABILITY`:** the route's permission answers "may this request reach the handler at all" for the WHOLE route; a handler that branches on `$tab` and grows a second, looser-gated tab later keeps its own check so the two can never drift apart silently. Defence in depth, not redundancy.

---

## The page shell — `templates/admin/settings.php`

Alpine `x-data` shell, tab nav, conditional `include` of each tab partial. Every echoed value is escaped (`esc_attr` for attributes, `esc_html` for text).

```php
<?php
/** Settings shell — returned as a string by renderSettingsPage()'s html() call. */
defined('ABSPATH') || exit;

$templateDir = __DIR__ . '/settings';
?>
<div class="wrap" x-data="{project}SettingsApp()" x-cloak>
    <div x-show="message" x-transition.opacity
         :class="messageType === 'error' ? 'notice notice-error' : 'notice notice-success'">
        <p x-text="message"></p>            <!-- x-text, not innerHTML — no XSS sink -->
    </div>
    <nav class="settings__nav">
        <?php foreach ($tabs as $tabKey => $label): ?>
            <button type="button"
                    :class="{ 'is-active': activeTab === '<?php echo esc_attr($tabKey); ?>' }"
                    @click="switchTab('<?php echo esc_attr($tabKey); ?>')">
                <?php echo esc_html($label); ?>
            </button>
        <?php endforeach; ?>
    </nav>
    <div class="settings__content">
        <div x-show="activeTab === 'company'">
            <?php if (file_exists($templateDir . '/tab-company.php')) include $templateDir . '/tab-company.php'; ?>
        </div>
    </div>
</div>
```

---

## The frontend — `assets/js/admin/settings.js`

Alpine component factory. Per-tab save via `wp.apiFetch` — never raw `fetch()`, so nonce/credentials plumbing is handled.

```js
function {project}SettingsApp() {
    return {
        activeTab: 'general',
        message: '',
        ...window.{project}Settings,         // localized initial state
        switchTab(tab) { this.activeTab = tab; },
        async saveTab() {
            const res = await wp.apiFetch({
                path: '/{project}/v1/settings',
                method: 'POST',
                data: { tab: this.activeTab, ...this.fieldsForActiveTab() },
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
3. **Menu placement** — parent slug in `add_submenu_page`.
4. **Tabs + fields** — the tabs array, the `match($tab)` arms, and the per-field sanitisers.
5. **Sanitisers** — one per field by type (`sanitize_text_field` / `sanitize_email` / `esc_url_raw` / `sanitize_title`).

**Never changes:**
- Save runs through a capability-gated `ntdst_rest()` route — never the retired AJAX dispatcher, never a hand-rolled `admin-post.php` handler.
- Capability checked at **both** the route declaration and inside the handler.
- The page renders through `ntdst_response()->html()` — never `render()`, which exits before WordPress's admin chrome finishes.
- Every field sanitised on input; every echoed value escaped on output.
- Options stored under named constants.
- Assets enqueued only on the page hook.
- Frontend uses `wp.apiFetch`.

> **Settings-API alternative.** If the page is a simple flat option set with no tabbed/Alpine UI, `register_setting()` + `settings_fields()` + `do_settings_sections()` is also framework-acceptable and gets WordPress's own nonce + sanitize-callback for free. The choice is a **named decision in the plan** — an `ntdst_rest()` route is right for a multi-tab/dynamic UI, the Settings API for a static field list. Either is fine; an *unnamed* choice is the deviation.

---

## Cross-references

- Governing references: `ntdst-framework/SKILL.md` (`## Rest is the one surface`), `netdust-wp:wp-security`.
- The save is itself a form/data-flow write route — see `golden-paths/form-data-flow.md` for the full internal-write shape this reuses.
- The CPT this settings page configures (if any) is its own slice — see `golden-paths/content-type-feature.md`.
