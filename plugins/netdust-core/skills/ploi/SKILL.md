---
name: ploi
description: Use when working with Netdust's Hetzner+Ploi server fleet — provisioning new servers, creating sites, managing deploys, viewing logs, restarting services, managing databases/cron/daemons, viewing backups, restoring databases, hardening a freshly provisioned VPS, or anything that touches a Ploi-managed server. Triggers on keywords ploi, hetzner, VPS, server, provision, deploy, restart, daemon, cron, backup, restore, ssh, nginx, php-fpm, redis, mariadb. Symptoms include needing to spin up infrastructure for a new client, debugging a production issue, restarting a service, configuring an SSL certificate, adding a cronjob, restoring data after a bad deploy. Covers three tools: the ploi-mcp-server (operations via MCP), the `ploi` CLI binary, and the secure-server skill (one-time hardening of a fresh VPS).
---

# Ploi + Hetzner — server lifecycle

Netdust's WordPress fleet runs on Hetzner VPS provisioned and managed via Ploi. This skill is the map: which tool for which job, in what order.

## Three tools, one workflow

| Tool | When | How invoked |
|---|---|---|
| **Ploi UI** | First-time server creation (Ploi creates the Hetzner VPS for you via its connected Hetzner account). | https://ploi.io — manual web UI step |
| **`secure-server` skill** | Immediately after Ploi provisions a fresh VPS — before adding any sites. One-time. | Say "harden the new server at `<IP>`" or "secure server". |
| **`ploi-mcp-server` (MCP)** | Day-to-day operations: list servers, trigger deploys, view logs, restart services, manage backups, view sites. AI-conversational, no terminal context-switch. | Auto-loaded via the netdust-wp plugin. Tools: `list_servers`, `restart_service`, `trigger_deployment`, `restore_database_backup`, etc. |
| **`ploi` CLI** (`~/.local/bin/ploi`) | CRUD operations that benefit from explicit scripting — creating cronjobs, databases, network rules, auth users. Also `ploi init` / `ploi deploy` for repo-side deploy config. | `ploi <namespace>:<command>` (Symfony Console style). |

## Standard lifecycle of a new Netdust site

```
1. Ploi UI: create server (or reuse existing)
   - Provider: Hetzner Cloud
   - Type: CPX21 (default for low-medium WP) / CPX31 (LMS / high-traffic)
   - Region: Falkenstein (FSN1) or Nuremberg (NBG1)
   - OS: Ubuntu 22.04 LTS
   - PHP: 8.2 or 8.3
   - DB: MariaDB
   - Webserver: Nginx
   - Wait for Ploi's provisioning to finish (~5-10 min)

2. secure-server skill: harden the fresh VPS
   - Create admin user with sudo + SSH key
   - SSH-hardening (no root login, no password auth, key-only)
   - fail2ban + UFW + unattended-upgrades
   - Optional Tailscale for private mesh
   - Preserves Ploi's `ploi` deploy user untouched

3. Ploi UI or MCP: create the site on the server
   - Domain
   - PHP version
   - SSL (Let's Encrypt — automatic if DNS resolves)
   - Webroot (web/ for Bedrock)
   - Repository (GitHub URL + branch)

4. ploi CLI / MCP: configure cronjobs + daemons
   - WP Cron disable + system cron: `* * * * * wp cron event run --due-now --path=/.../web/wp`
   - Queue daemons if using Action Scheduler

5. /deploy (harness command): trigger first deploy
   - Reads site.yml deploy.method (probably git-push for Ploi auto-deploy)
   - Confirms environment + branch
   - Pushes; Ploi's webhook auto-deploys

6. /wp-new-project (if not done yet): scaffold local project
   - CLAUDE.md, site.yml, memory/, tasks/, Makefile

7. Site is live.
```

## When to use which tool — decision tree

**Need to spin up a NEW server?** → Ploi UI (Hetzner integration creates the VPS). The MCP doesn't currently create servers — only manages existing ones. CLI doesn't either (Ploi reserves provisioning to the UI).

**Server just provisioned, not hardened yet?** → `secure-server` skill. Stop. Don't add sites until hardening is done.

**Need to operate an existing server/site conversationally?** → Ploi MCP. Examples that work naturally:
- "Show me the status of all servers."
- "Restart php-fpm on stridelms-prod."
- "Trigger a deploy of the staging branch on vad-vormingen."
- "What's the latest backup of the netdust database?"
- "Restore yesterday's backup of the kindred site."
- "Show me last 50 lines of the nginx error log on stride-prod."

**Need to script a CRUD operation?** → `ploi` CLI. Examples:
```bash
ploi cronjob:create --server <id> --command "wp cron event run --due-now --path=/var/www/site/current/web/wp" --frequency "* * * * *"
ploi database:create --server <id> --name myapp_prod
ploi env:pull --site <id>  # download .env from the server
ploi env:push --site <id>  # upload .env to the server
ploi network-rule:create --server <id> --port 6379 --source <ip>  # whitelist Redis
ploi auth-user:create --site <id>  # HTTP basic auth for staging
```

**Need to deploy?** → `/deploy` slash command. It dispatches per `site.yml`'s `deploy.method`. For Ploi-hosted sites, that's usually `git-push` (Ploi auto-deploy hook) or `makefile` (with `git push` inside the target). `/deploy` enforces the "never prod without confirm" rule.

**Need to SSH into a server?** → `ploi ssh` or `ssh <alias>`. The aliases live in `~/.ssh/config` and in each project's `site.yml` (`hosting.ssh_staging` / `ssh_production`).

## Tool reference — Ploi MCP

Auto-loaded by the netdust-wp plugin. Available tool names (partial):

**Server management**: `list_servers`, `get_server`, `get_server_health`, `restart_server`, `restart_service` (nginx | php | mariadb | redis | supervisor), `get_server_logs`, `diagnose_server`

**Site management**: `list_sites`, `get_site`, `get_site_deployment_log`, `trigger_deployment`, `get_ssl_status`

**Backups**: `list_database_backups`, `list_file_backups`, `list_backup_files`, `trigger_backup`, `restore_database_backup`, `get_backup_overview`

**Daemons + cron**: `list_daemons`, `manage_daemon`, `list_cron_jobs`, `manage_cron_job`

**Utility**: `manage_opcache`, `get_server_insights`, `run_saved_script`

(For canonical names + args, the MCP introspects itself — Claude can just call `mcp__ploi__*` and it knows.)

Auth: `PLOI_API_TOKEN` env var (NOT `PLOI_TOKEN` — the server checks `PLOI_API_TOKEN`). The netdust-core `plugin.json` forwards `${PLOI_API_TOKEN}` into the MCP's env, so the simplest setup is to export it from your shell rc:

```bash
# add to ~/.bashrc or ~/.zshrc
export PLOI_API_TOKEN="<token from https://ploi.io/panel/user/api-keys>"
```

Restart Claude Code afterwards so the MCP picks it up. If the MCP fails to start, check `~/mcp/ploi-mcp-server/ploi-mcp-server/node_modules/` exists (run `npm ci` in that folder if not).

## Tool reference — `ploi` CLI

`ploi <namespace>:<command>` style (Symfony Console). `ploi list` shows everything.

Most useful namespaces:
- **Deploy-side** (in a project repo): `ploi init`, `ploi deploy`, `ploi token` (auth)
- **Server CRUD**: `cronjob:*`, `daemon:*`, `database:*`, `network-rule:*`, `auth-user:*`
- **Site CRUD**: `alias:*`, `env:pull`, `env:push`
- **Logs**: `logs:stream <site>` (tails deploy logs in real time)

CLI auth: `ploi token` once per machine.

## Server stack — Netdust defaults

| Component | Choice | Why |
|---|---|---|
| Provider | Hetzner Cloud | EU-located, GDPR-friendly, lower cost than AWS for VPS workload |
| Region | Falkenstein (FSN1) primary, Nuremberg (NBG1) fallback | Both DE, same network zone, low latency from Brussels |
| Instance | CPX21 (3 vCPU / 4GB) default · CPX31 (4 vCPU / 8GB) for LMS | LearnDash + LMS data grows fast; default CPX21 is fine for marketing sites |
| OS | Ubuntu 22.04 LTS | Long support, Ploi's primary target |
| Webserver | Nginx | Ploi default; fastcgi cache for static content |
| PHP | 8.2 or 8.3 | Match `composer.json` `php` constraint per project |
| Database | MariaDB | Ploi default; mostly drop-in MySQL-compatible |
| Cache | Redis (object cache) | Required by some plugins (FluentCRM); object-cache.php drop-in |
| SSL | Let's Encrypt via Ploi | Auto-renew enabled |
| Backups | Hetzner Object Storage (S3-compatible) | Ploi pushes to it; weekly retention configured per-server |
| Monitoring | Ploi's built-in + ploi-mcp-server `diagnose_server` | No external APM unless client requires |
| Private mesh | Tailscale (optional) | If managing >3 servers; gives dashed-IP private network |

## Hardening checklist — what `secure-server` actually does

(Full body in `~/.claude/plugins/netdust-wp/skills/secure-server/SKILL.md` — invoke that skill for the workflow.)

1. `apt update && apt upgrade` baseline
2. Create admin user (`useradd`, sudo group, adm group for log access)
3. SSH key into `/home/<user>/.ssh/authorized_keys`
4. Passwordless sudo via `/etc/sudoers.d/<user>`
5. SSH hardening (`/etc/ssh/sshd_config`): no root login, no password auth, `AllowUsers ploi <user>`
6. fail2ban with sshd jail
7. UFW: deny incoming default, allow OpenSSH + 80/443
8. unattended-upgrades for security patches
9. Optional Tailscale install + auth

**Preserves Ploi's `ploi` deploy user**. Do not remove it or the deploy webhook breaks.

## Failure modes to watch

- **Locking yourself out**: keep the original SSH session open until `secure-server` step 7 verifies. Ploi web console is the only recovery.
- **MCP not loading**: check `~/mcp/ploi-mcp-server/dist/index.js` exists (`npm run build`). Token in env.
- **Deploy hook silent fail**: Ploi's deploy script needs `composer install` to succeed. Check the deploy log via MCP `get_site_deployment_log` or `ploi logs:stream`.
- **`wp cron` not firing on a hardened server**: system cron exists (`crontab -l` as the `ploi` user) but the WP-CLI path is wrong. Bedrock: `--path=<webroot>/web/wp`.
- **Provisioning a CPX21 for an LMS**: out of memory under load. Stride / VAD need CPX31 minimum.

## See also

- `secure-server` — the 9-step VPS hardening workflow (invoked after provisioning)
- `dev-stack` (core) — broader deploy + DDEV environment patterns
- `wp-infra` (netdust-wp) — WP-CLI + Bedrock-specific deploy variants
- `bedrock-composer` — what gets deployed
- `memory/deploy-patterns.md` — the 9 deploy methods catalog
- `/deploy` — slash command that dispatches deploys per `site.yml`
- `~/mcp/ploi-mcp-server/README.md` — MCP setup + auth
- `ploi` CLI: `ploi list` for all commands
