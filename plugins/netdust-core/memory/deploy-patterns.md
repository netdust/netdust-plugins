# Deploy patterns across the Netdust fleet

Catalog of deploy methods `/deploy` knows about. **Per-site deploy method lives in each project's `site.yml`** — that's the source of truth, not this file. Most Netdust projects use `makefile` (with optional small `rsync` for asset-only updates).

## The 9 methods

| Method | Description | When to use |
|---|---|---|
| `rsync` | The shared Makefile (`netdust-wp/templates/`) moves a closed payload over SSH, behind a gate and a server-side ledger. `make deploy env=<name>` / `make ship`. | WordPress on managed hosts — Combell, custom-app. The default. |
| `git-push` | Push to a remote branch; Ploi auto-deploys. | Bedrock on Ploi when Ploi handles the deploy hook. |
| `rsync` | Direct rsync from local to remote path. | Static sites or simple Combell/Webhosting setups without git. |
| `manual` | No automation — direct edits via Combell file manager or SSH. | Legacy sites, low-touch maintenance, sites scheduled for migration. |
| `ftp` | PhpStorm auto-upload via FTP. | Sites where the host only offers FTP. |
| `autogit` | Combell autogit — symlinks `checkout/master/current/www`. | Combell-specific shared hosting pattern. |
| ~~`rsync-staging-only`~~ | **Retired.** Multiple environments are now `environments:` entries in site.yml, one command for all of them. | Migrate to `rsync`. |
| ~~`git-bundle-makefile`~~ | **Retired 2026-08-26.** Required a `.git` on the deploy target; production usually had none, so the deploy failed or silently never ran — on VAD Vormingen every production change went out by hand for months while `make ship` looked correct. | Migrate to `rsync`. |
| `tbd` | Not yet decided. | New projects pre-launch. |

## Finding the deploy method for a specific site

```bash
grep '^  method:' ~/Sites/<site>/site.yml
```

Per-site mapping is intentionally not tracked here — it changes, and the per-project `site.yml` is always right. To see the fleet-wide distribution:

```bash
grep -h '^  method:' ~/Sites/*/site.yml | sort | uniq -c | sort -rn
```

## Rules for /deploy

- **Always** read `site.yml` first.
- **Always** ask environment (staging / production) explicitly. Never assume.
- **Refuse** production for `risk: high` sites without a second confirmation.
- For `manual` / `ftp` / `autogit`: print what to do, don't act.
- For `makefile` / `git-push` / `rsync`: dry-run preview before executing, then confirm.
