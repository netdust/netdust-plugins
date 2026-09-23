# Netdust WordPress Harness

You are working on a Netdust **WordPress** project. This plugin carries the WordPress and
ntdst-core knowledge. The coding loop is `netdust-gates` on superpowers; branches, deploy and
the `make` verbs are `netdust-devops`; memory conventions, servers and cross-domain skills are
`netdust-core`. Install `netdust-devops` first — `/deploy` and the `make` verbs won't work
otherwise.

## Setup — the upstream WordPress skills

Once per box, after `/plugin install`, run `bash bin/wp-upstream-skills.sh`. It installs the
official `WordPress/agent-skills` set this plugin cites instead of restating —
`wp-plugin-development`, `wp-rest-api`, `wp-wpcli-and-ops`, `wp-phpstan` — into
`~/.claude/skills/` at the commit pinned in the script (`PIN`, bumped only by a reviewed
commit here), copied from a local clone so nothing is fetched by tag or branch. `--check`
prints the pin and which of the four are present (exit 1 if any is missing); `--dry-run`
prints the commands and touches nothing.

## Entry — `netdust-gates:policy`, then this plugin's skills

Any code-changing request starts at `netdust-gates:policy`. On a WordPress project it copies
the WordPress pack (`netdust-gates/skills/policy/wordpress.md`) into the plan's
`Global Constraints` — that pack, not this file, is where the WP plan requirements live.

- **Intent vs shape.** Brainstorming and Stefan own intent — what we build and why.
  `ntdst-framework` (services, data, routes, templates) and `ntdst-patterns` (where files live,
  golden paths) own the technical shape. They layer on `superpowers:brainstorming`; there is no
  `ntdst-brainstorm` and there should not be one.
- **Every implementer names `ntdst-framework` + `wp-testing`.** (Stefan, 2026-09-03: six
  approved tasks built plain WordPress on the framework because neither was loaded.)
- **Security.** `netdust-gates:threat-modeling` fires on its triggers; `wp-security` and
  `wp-database` self-trigger on PHP edits and supply the four pillars it checks.
- **Tests.** The close is `make gate`, which runs `commands.gate` from `site.yml` — on a
  gate-stack project that is `composer gate` (Brain Monkey, wp-phpunit through DDEV, Vitest,
  Playwright). Codeception/wp-browser is the legacy stack, Stride family only. Runners and the
  shake-out login recipe are `wp-testing`'s.
- **Drift.** The pack makes `ntdst-drift-reviewer`'s list a plan constraint, so the
  whole-branch review checks the diff against it. `/drift-reviewer <path>` runs the agent on a
  module on demand — before a refactor, a launch, or a core version bump.

## `site.yml` is the operating context — not the entry point

Every Netdust WP project has a `site.yml` in its root. It is the single source of truth for
how that site is built, hosted and deployed. Do not infer these from the tree. Read it before
running anything path-dependent or destructive, at any stage.

| Field | Why it decides your next command |
|---|---|
| `structure.type` | `bedrock` \| `custom-app` \| `custom-site` — sets `wpcli_path`, the webroot, and whether `config/environments/` exists |
| `structure.wpcli_path` | what `--path` every WP-CLI call needs (`web/wp`, `app/wp`, or `.`) |
| `structure.theme_flavour` | `yootheme` \| `custom` \| `tbd` — there is no default theme base on this fleet |
| `site.risk` | `high` means triple-check every destructive operation |
| `hosting.provider` | `ploi` \| `combell` \| other — different SSH shape. A push alone does NOT deploy on Ploi |
| `deploy.method` | `rsync` or `git-push` — the only two. `makefile`, `git-bundle-makefile` and `rsync-staging-prod` are retired |

Then `memory/STATE.md` for where the project actually stands.

## Where a new site comes from

`netdust-wp-manager/scripts/new-site.sh` clones a stack skeleton — `netdust/bedrock` or
`netdust/stackedWP` — then `scaffold_wp_starter` lays the `netdust/wp-starter` payload over
it: the framework loader shims, the theme (plain or yootheme) and the whole gate. The gate has
one home, wp-starter's `gate/` (INV-1 in netdust-wp-manager's `ARCHITECTURE-INVARIANTS.md`):
a gate change lands there, never in a stack skeleton or a single site. It reaches new sites
only; an existing site adopts it by hand (`/setup-tests`).

## Where knowledge lives (three layers, do not conflate)

- **A — atomic recall**: `~/.claude/projects/<slug>/memory/`, injected at session start.
- **B — fleet / business**: `~/Sites/netdust-wp-manager/memory/` — cross-site
  priorities, deals, cross-project rules, `GLOBAL.md`, `projects/<site>/STATE.md`.
  **Written by hand.** Update it only when something *fleet-level* changed, and
  commit from that workspace. The weekly `./scripts/todos` sweep reads it and
  reports any entry still marked DRAFT or gone stale.
- **C — per-project**: `<project>/memory/STATE.md` · `lessons.md` · `tasks/todo.md` — written
  automatically by netdust-gates' Stop hook from `DECISION:`/`RISK:`/`LESSON:`/`TODO:` tags.

A single site's decision is Layer C and lands by itself. Do not hand-write it into B.

`netdust-wp-manager` is the toolbox workspace and the site registry — shared scripts
and the fleet brain. Per-project config and memory live in the project, never there.

## Default assumptions (project `CLAUDE.md` can override)

- **Stack**: Bedrock / Composer / PHP 8.2+ / MariaDB is the common case, not the only
  one — `structure.type` decides.
- **Framework**: ntdst-core **and** ntdst-baseline, both mu-plugins,
  both Composer-managed. See `ntdst-framework`.
- **Local**: DDEV, always.
- **Standards**: WordPress Coding Standards via PHPCS.

## What this plugin ships

- **`ntdst-framework`** — the ntdst-core + ntdst-baseline contract, with
  `references/traps.md` (what the source will not tell you).
- **`ntdst-patterns`** — where files go, plus the golden-path archetypes.
- **`ntdst-yootheme`** — the YOOtheme Pro stack.
- **Discipline** — `wp-security`, `wp-database`, `bedrock-composer`.
- **Reference** — `wp-frontend`, `wp-testing`, `wp-infra`.
- **Drift review** — the `ntdst-drift-reviewer` agent: both packages used consistently — no
  repository bypass, no pass-through, no raw `wp_ajax_*`, nothing re-implementing what an
  ntdst-baseline module already owns.
- **Commands** — `/wp-new-project` (delegates the project layer to netdust-devops, then adds
  the WP harness `CLAUDE.md`), `/scaffold-plugin`, `/setup-tests` (legacy Stride-family stack
  only — gate-stack projects are born gated), `/drift-reviewer`.

WP-specific rules: this plugin's `RULES.md`. Universal rules: netdust-core's `RULES.md`.
