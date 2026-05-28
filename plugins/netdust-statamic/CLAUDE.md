# Netdust Statamic Plugin

You are working on a Netdust **Statamic** project. This plugin layers on top of `netdust-core` (memory, hooks, dev-stack, server management, code review, cross-stack skills). Install `netdust-core` first — `/deploy` and memory hooks won't work otherwise.

## Default assumptions (project `CLAUDE.md` can override)

- **CMS**: Statamic 6.x + Peak (the Netdust starter at `~/Sites/ntdst-starter` is the canonical baseline)
- **Framework**: Laravel 13.x, PHP 8.3
- **Local Dev**: DDEV (always — `ddev exec ...` for everything Laravel/Statamic)
- **Assets**: Vite 7 + Tailwind 4 + Alpine 3
- **Image driver**: Imagick (set in `.env`)
- **Deploy**: Ploi (Hetzner). See core's `/deploy` for the 9 methods + `ploi` skill for ops.
- **Architecture**: Starter ships baseline (layout, header/footer, design tokens, universal page-builder blocks, CP role rules, NTDST tooling). Domain addons add specifics (portfolio-art, studio, etc.) — never inline domain-specific stuff into the starter.

## What this plugin adds

| Layer | Contents |
|---|---|
| **Skills** | `statamic-build` (editor-friendly feature implementation), `shake-out-statamic` (Statamic-flavored post-build QA), `peak-reference` (Peak partials + commands), `statamic-mcp` (router tools guide) |
| **Commands** | `/new-feature`, `/new-collection`, `/new-block`, `/new-service`, `/cache-bust`, `/sync-content` |

## What lives in netdust-core (not here)

- Memory + tag conventions (`DECISION:`, `RISK:`, `LESSON:`, `TODO:`, `SKILL-EDGE:`)
- `dev-stack` skill (DDEV, git branching, Makefile verbs, `.env`)
- `secure-server` + `ploi` skills + ploi MCP
- `code-audit`, `shake-out` (generic; `shake-out-statamic` here is the Statamic-specific override), `testing-workflow`
- `research`, `market-research`, `brand-voice`, `marketing`
- 7 code reviewer agents
- `/deploy`, `/skill-audit`, `/pattern-miner`, `/red-test`
- Voice (`SOUL.md`) and universal rules (`RULES.md`)

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

Per-project: `ddev composer require netdust/<addon>` then `php please install netdust/<addon>` then `make stache-warm`.

**Never inline domain-specific content into the starter.** Build it as an addon.

## Slash commands (Statamic-specific)

- `/new-feature` — full brainstorm → plan → implement → shake-out workflow for a new Statamic feature
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
