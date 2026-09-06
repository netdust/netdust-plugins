
---
## Carried forward (2026-08-19)
- [ ] configure collie push on netdust-web (`push-keys` → `restart` → subscribe) so the blocked-agent doorbell reaches the phone.

## From artifact-gate compounding (2026-09-06)

- [ ] devops: `tests/test-marketplace.sh` must FAIL on unparseable `marketplace.json` (fails open today; see `skills/devops/lessons.md`)
- [ ] templates: `bin/e2e.sh` implements the `wp-testing` shake-out access recipe (login-server plugin on DDEV, magic link, `tests/e2e/.auth/` storageState, per-run app password create/delete); unify `tests/E2E/` vs `tests/e2e/` casing
- [ ] devops: a floor for `wp user application-password create` over `--ssh` to a production host (`environments.<env>` binding + a refusing `make` verb); today the recipe forbids it in words only
