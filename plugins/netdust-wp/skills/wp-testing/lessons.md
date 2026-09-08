
## The shake-out access recipe is prose until the project template carries it (2026-09-06)

The `### Shake-out access` recipe names `bin/e2e.sh` behaviour (installs the
`wp-cli-login-server` plugin on DDEV, mints the link, saves `storageState` to
`tests/e2e/.auth/`, creates and deletes the per-run application password). That script
lives in the project template (netdust-devops/netdust-wp templates), which does not yet
implement it, and the template's `tests/E2E/` (specs) vs `tests/e2e/.auth/` (ignore rule)
case split is real. Until the template lands the recipe, a scaffolded project's plan may
cite a recipe its `bin/e2e.sh` cannot run — `tasks/todo.md` carries the follow-up.

## An application password over `--ssh` to production has no machine floor (2026-09-06)

`wp login create` fails on production because the server plugin is never in
`deploy.payload`; `wp user application-password create` over `--ssh` to a production host
simply works. The recipe forbids it in words; the floor is a devops verb (`site.yml`
`environments.<env>` + a refusing `make` target), tracked in `tasks/todo.md`.

## A stubbed unit suite proves the code matches the stubs (2026-09-08)

`feature/course-taxonomy-filter` surfaced TEN defects. Not one came from a green unit
suite. They came from ground-truthing the dependency surface, running the artifact
through `wp eval`, a reviewer reading the ROUTE rather than the service, driving a real
browser, and adversarial probing over HTTP. The unit suite passed throughout — 2109
tests green while the feature was invisible in the UI.

Two were invisible BY CONSTRUCTION, and both are worth recognising:

- **Unfalsifiable assertion.** `[12 => 'x']` and `['12' => 'x']` are the SAME PHP array
  (numeric string keys canonicalise to int), so a test asserting "the options map is
  string-keyed" can never fail. The real contract had to be pinned through
  `ConditionTree::validate()` instead — a behaviour test, not a shape test.
- **Vacuous wire test.** An assertion that "no shipped field leaks the `taxonomy` key"
  PASSED before the fix, because the group carrying that key was dropped upstream by a
  stale `GROUP_LABELS` const. The test could not fail while the thing it guarded was
  unreachable. It was closed by a reflection check binding all three copies of the
  stripped-key list together, so they can only drift through a RED.

**Check:** every task claiming a user-visible behaviour owes one assertion through the
real entry point — the route or the rendered page, not the service behind it. And a
test that has never been made to fail is not yet evidence: falsify it by breaking the
production behaviour it claims to pin, watch it go red, restore.
Eval: `evals/stubbed-suite-2026-09-08-cases.json` (`route-tier-assertion`).
