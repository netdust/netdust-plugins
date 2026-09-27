# Netdust Statamic Plugin

You are working on a Netdust **Statamic** project. This plugin layers on top of `netdust-devops` (the branch flow, deploy, site.yml), `netdust-core` (server management, cross-domain skills) and `netdust-gates` (the delivery policy — `netdust-gates:policy` over superpowers, `/plan-review`, `/feature-review`, `/review-fix`, `/shakeout` — and the live hooks: SessionStart memory injector, Stop-hook tag capture, PreToolUse guard). Install `netdust-devops` first — `/deploy` and the make verbs won't work otherwise; memory hooks need `netdust-gates`.

## Default assumptions (project `CLAUDE.md` can override)

- **CMS**: Statamic 6.x + Peak (the Netdust starter at `~/Sites/ntdst-starter` is the canonical baseline)
- **Framework**: Laravel 13.x, PHP 8.3
- **Local Dev**: DDEV (always — `ddev exec ...` for everything Laravel/Statamic)
- **Assets**: Vite 7 + Tailwind 4 + Alpine 3
- **Image driver**: Imagick (set in `.env`)
- **Deploy**: Ploi (Hetzner). Through netdust-devops' make verbs (`/deploy`, method `rsync` or `git-push` from `site.yml`) + `ploi` skill for ops.
- **Architecture**: Starter ships baseline (layout, header/footer, design tokens, universal page-builder blocks, CP role rules, NTDST tooling). Domain addons add specifics (portfolio-art, studio, etc.) — never inline domain-specific stuff into the starter.

## What this plugin adds

| Layer | Contents |
|---|---|
| **Skills** | `statamic-build` (editor-friendly feature implementation), `shake-out-statamic` (Statamic-flavored post-build QA), `peak-reference` (Peak partials + commands), `statamic-mcp` (router tools guide) |
| **Commands** | `/new-feature`, `/new-collection`, `/new-block`, `/new-service`, `/cache-bust`, `/sync-content` |

## What lives in netdust-core / netdust-devops / netdust-gates (not here)

- Memory + tag capture (`DECISION:`, `RISK:`, `LESSON:`, `TODO:`) (netdust-gates hooks)
- `devops` skill (DDEV, the branch flow, make verbs, deploy, `.env`) (netdust-devops)
- `secure-server` + `ploi` skills + ploi MCP (netdust-core)
- The delivery policy — `netdust-gates:policy`, `threat-modeling`, `/plan-review`, `/feature-review`, `/review-fix`, `/shakeout` (the manifest gate; `shake-out-statamic` here is the Statamic sweep that runs at its step), `/session-review`, `/session-learn` (netdust-gates)
- `research`, `market-research`, `brand-voice`, `marketing` (netdust-core)
- Code review — superpowers' whole-branch review via `make review name=<feature>`, joined by `security-sentinel` / `invariant-auditor` (netdust-gates)
- `/deploy`, `/new-project` (netdust-devops); `/pattern-miner` (netdust-core)
- Voice (`SOUL.md`) and universal rules (`RULES.md`) (netdust-core)

## The Editor Iron Rules (Statamic-specific)

These shape every block/collection decision. If a build decision violates one, redesign the decision.

1. **Field instructions are mandatory.** Every editable field has a one-line plain-language `instructions:` hint.
2. **Required fields validate.** Optional fields hide behind variant `if:` or a `revealer`.
3. **≤ 5 fields per block.** Beyond that, use `sections:` or split the block.
4. **≤ 10 blocks in the page-builder picker.** Beyond that, the set picker becomes a usability problem.
5. **Live preview must work.** Don't introduce SSR patterns that break Statamic's preview iframe.
6. **No technical jargon in CP labels.** No "blueprint", "fieldset", "stache", "slug", "handle" surfaced to editors.

Full rationale + counter-patterns in the `statamic-build` skill body.

## Starter + addon architecture

The Netdust Statamic starter (`~/Sites/ntdst-starter`) ships the 90% baseline. Domain addons supply project-specific content:

- `netdust/portfolio-art` — single-artist portfolio
- `netdust/portfolio-pro` (future) — multi-artist galleries
- `netdust/studio` (future) — design studio cases
- `netdust/about-site` (future) — marketing sites

Per-project: `ddev composer require netdust/<addon>` then `php please install netdust/<addon>` then `ddev exec php please stache:warm`.

**Never inline domain-specific content into the starter.** Build it as an addon.

## How this plugin plugs into `netdust-gates:policy`

`netdust-gates:policy` is the stack-agnostic entry for any code change (brainstorm → plan → execute → review, superpowers' loop, plus Netdust's standards and gates). **For any non-trivial Statamic work, that is the entry point.** The Statamic overrides it defers to:

- **Design** — `superpowers:brainstorming` (Statamic has no rigid framework-design skill).
- **Execute** — `statamic-build` is the executor (PRE-WRITE → WRITE → VERIFY).
- **Shake-out** — `shake-out-statamic` is the Statamic sweep at the Close's shake-out step, before `/shakeout`'s manifest gate.

The Close, by cost: `make gate` → `make review name=<feature>` → one fix pass (review kept as `specs/<feature>/review.md`) → `/shakeout` on the fixed code → push and hand over `make promote name=<feature>`.

`/new-feature` is the convenience wrapper that invokes the policy with these overrides pre-wired.

## Slash commands (Statamic-specific)

- `/new-feature` — invokes `netdust-gates:policy` with Statamic overrides (brainstorm → plan → statamic-build → gate → review → fix → shake-out → promote)
- `/new-collection` — scaffold a collection by copying from blog/pages (no Peak CLI dep)
- `/new-block` — scaffold a page-builder block by copying from an existing one
- `/new-service` — scaffold a Service class (thin-controller / service-layer pattern)
- `/cache-bust` — clear all Statamic + Laravel caches, warm the stache (use after blueprint changes)
- `/sync-content` — pull content + assets from remote (production) into local DDEV

## Tooling notes

- **Statamic MCP** (`statamic-mcp` skill) — prefer router tools over file edits for content operations
- **Laravel Boost** — use `search-docs` for version-specific Laravel/Statamic docs
- **Pint** — run `vendor/bin/pint --dirty --format agent` after any PHP edit, no exceptions
- **Smoke test** — `ddev exec php artisan test --compact` should pass before claiming work done
- **Cache vs Stache** — Laravel caches (`php artisan cache:clear`) and Statamic's stache (`php please stache:warm`) are different things. `/cache-bust` does both.
