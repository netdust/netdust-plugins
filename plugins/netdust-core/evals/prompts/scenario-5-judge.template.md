# JUDGE PROMPT TEMPLATE — scenario 5

# This file is a TEMPLATE. Before dispatching the judge subagent:
# 1. Ensure outputs/scenario-5-baseline.md and outputs/scenario-5-skill-on.md exist.
# 2. Run: python3 run-eval.py --build-judge 5
#    This writes prompts/scenario-5-judge.md with both outputs inlined.

# Scenario prompt:
You're working on Stride. Set up a new `Notifications` module that:

1. Registers a new custom post type `stride_notification` (statuses: `unread`, `read`, `archived` — use post_status). Title required, content optional. Author = the user being notified.
2. Exposes a top-level `NotificationService` (public API: `notifyUser(int $user_id, string $message): WP_Post|WP_Error`).
3. Owns an internal `NotificationDispatcher` (handles the actual delivery — email, web push later). This is NOT a top-level service — it's an internal implementation detail of NotificationService and shouldn't be discoverable on its own.
4. Wires the module into stride-core's bootstrap.

Write all the files (file path + content for each). Mention where each file lives in the project tree.

# Rules to score:
- **E1** (canonical): Modules live at `mu-plugins/{project}-core/Modules/<Name>/`. Folder structure NOT fixed — modules organize by concern
- **E3** (canonical): Services listed in `plugin-config.php`'s `'services'` array; NTDST Bootstrap auto-instantiates + resolves constructor DI
- **E4** (canonical): CPT registration lives in dedicated `*CPT` class (e.g., `EditionCPT`), called from owning service's `init()`. Class exposes `POST_TYPE` constant. **Registration MUST use `ntdst_data()->register()`, NOT raw `register_post_type()`.**
- **A1** (canonical): Implements `NTDST_Service_Meta` (directly or via `AbstractService`)
- **A2** (canonical): Static `metadata()` returning `{name, description, priority, admin_only?, enabled?}`
- **A3** (canonical): Hooks registered ONLY in `init()` or a provider's `boot()` — never in `__construct()`
- **A4** (canonical): Constructor DI uses `readonly` properties (PHP 8.1+)
- **A6** (canonical): Sub-services owned by parent registered as singletons inside parent's `init()` via `ntdst_set()`
- **A7** (canonical): Admin controllers NOT registered as Services. Instantiated with `new` inside owning service's `init()`
- **A11** (canonical): Priority convention: `<10 = critical/early`, `10–15 = standard`, `20+ = late`
- **X1** (canonical): PHP 8.1+ features throughout: readonly properties, enums, typed properties, named arguments where useful
- **X2** (canonical): No `add_action`/`add_filter` outside `init()` / `boot()` lifecycle methods
- **X3** (canonical): Type hints required (return + parameter). `mixed` is rare and intentional.
- **EX1** (canonical): `declare(strict_types=1);` as first line of every PHP file
