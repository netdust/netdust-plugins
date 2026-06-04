# Netdust Core Harness

You are working in a Netdust project. The stack varies — WordPress, Statamic, Bun/Node, plain HTML — but the conventions, voice, memory pattern, and operational discipline are shared. This is the always-on layer; stack-specific plugins (netdust-wp, netdust-bun-react, etc.) layer on top.

## What this plugin provides

- **Memory + observability** — per-project `memory/STATE.md` + `lessons.md`, hooks that log every fire, deterministic tag scanner.
- **Dev-stack conventions** — DDEV, git branching (staging/feature/hotfix), Makefile verbs (dev/save/feature/finish/deploy/ship), `.env` discipline. See `dev-stack` skill.
- **Server management** — `secure-server` (harden fresh Hetzner+Ploi VPS) + `ploi` (full lifecycle: MCP + CLI + UI). The `ploi` MCP is auto-loaded.
- **Cross-stack workflow** — `harnessed-development` is the single entry point: it sequences the full harness (design → plan + threat-modeling + architecture-invariants → execute + per-task testing-workflow + Step 2.5 → shake-out → finish) so no gate is skippable, and defers to the loaded stack sub-plugin for stack-specific tools. Supporting skills: `code-audit`, `shake-out`, `testing-workflow`, `test-effectiveness`. (`ntdst-execute-with-tests` was the execution-only predecessor — now deleted; `harnessed-development` fully absorbed it. The name resolves to nothing; older handoff docs that say "execute the plan" route to `harnessed-development` by its own triggers.) A `SubagentStop` hook (`hooks/subagent-stop.py`) backstops the testing gate by blocking subagent stops that edited code without invoking testing-workflow.
- **Cross-domain skills** — `research` (technical investigation), `market-research` (audiences/competitors), `brand-voice` (Stefan/Netdust voice as artifact), `marketing` (SEO + copy structure).
- **Code review agents** — 7 specialized reviewers (architecture, security, performance, simplicity, API design, accessibility, frontend).
- **Slash commands** — `/deploy` (9-method dispatcher), `/skill-audit`, `/pattern-miner`, `/red-test`.

## Engineering process — defer to superpowers

Engineering discipline (brainstorming, planning, TDD, systematic debugging, code review, finishing branches, verification before completion) comes from `obra/superpowers`. This harness does **not** redefine those — when superpowers and netdust-core would say similar things, follow superpowers.

## Per-project memory

Every Netdust project has:

```
<project>/
├── memory/
│   ├── STATE.md     ← current state, decisions, risks. Updated by Stop hook.
│   └── lessons.md   ← project gotchas. Append-only.
├── tasks/todo.md    ← carried-forward tasks.
└── site.yml         ← operational config: deploy method, SSH, hosting, paths.
```

**Read `site.yml` before any operational command.** It is the single source of truth for hosting, SSH, remote paths, deploy method, domains, project structure.

The SessionStart hook injects `memory/STATE.md`, `memory/lessons.md`, `tasks/todo.md`, and the site.yml summary into the initial context. It also injects a **"Memory discipline" prompt block** (only when `memory/` exists in the project) that tells Claude exactly when to update STATE, lessons, CLAUDE, and site.yml — and what *not* to write. That prompt is the difference between "Claude reads memory" and "Claude *maintains* memory."

The Stop hook then captures memory in two tracks (logs to `~/.claude/logs/memory-hook.log` every fire):

**Track A — tagged capture (always on, deterministic, zero cost)**
When you write any of these tags in your responses during a session, the Stop hook lifts them into memory automatically:

- `DECISION: <text>` → `memory/STATE.md`
- `RISK: <text>` → `memory/STATE.md`
- `LESSON: <text>` → `memory/lessons.md`
- `TODO: <text>` → `tasks/todo.md`
- `SKILL-EDGE: <skill-name>: <text>` → `skills/.../<skill-name>/lessons.md`

Use these tags liberally when something important happens. The hook captures them deterministically — no AI guessing involved.

**Track B — Haiku summary (opt-in)**
If `ANTHROPIC_API_KEY` is set in env, the hook also calls Haiku for a PM-level state summary at session end. Falls back silently if no key — Track A still runs.

## Stack-specific plugins (layer on top)

If you're working on a WordPress project, the `netdust-wp` plugin adds WP-specific skills (wp-security, wp-database, wp-frontend, wp-testing, bedrock-composer, wp-infra) + the `ntdst-*` framework skills (architecture, data, patterns, yootheme) + WP-specific commands (`/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests`).

Other stack plugins (future): `netdust-bun-react` (Folio-style single-binary Bun apps), `netdust-statamic` (Statamic + Peak), etc. Each layers cleanly — core stays always-on.

## Non-negotiables

See `RULES.md`. Universal rules apply to every project regardless of stack.

## Voice

See `SOUL.md`. Pushback over flattery, surface trade-offs, no sycophancy, no unnecessary abstractions. Stefan has 25 years of PHP/WordPress — match that energy. The voice is the same across stacks.
