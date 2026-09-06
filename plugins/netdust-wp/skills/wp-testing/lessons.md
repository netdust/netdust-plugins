
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
