# Netdust Core — business, ops & memory

You are working in a Netdust project. The stack varies — WordPress, Statamic, Bun/Node, plain HTML — but the conventions, voice, memory pattern, and operational discipline are shared. This is the always-on layer; stack-specific plugins (netdust-wp, netdust-statamic, etc.) layer on top.

This plugin is **not** a coding/build harness. The coding/build harness (gates, craft skills, reviewer agents, TDD/threat-model/shake-out, `/integration` + `/shakeout`) lives in the **netdust-agent** plugin — load that for any non-trivial coding work.

## What this plugin provides

- **Memory + observability** — per-project `memory/STATE.md` + `lessons.md`, a SessionStart hook that loads project memory, and a deterministic Stop-hook tag scanner that captures `DECISION:`/`RISK:`/`LESSON:`/`TODO:` into memory. Every fire logs to `~/.claude/logs/memory-hook.log`.
- **Destructive-command guard** — a `PreToolUse` hook (`hooks/pretooluse-guard.py`) that intercepts dangerous shell commands before they run.
- **Content + marketing** — `brand-voice` (Stefan/Netdust voice as artifact), `marketing` (SEO + copy structure + meta/schema), `market-research` (audiences/competitors/pricing), `research` (technical + business investigation).
- **Ops + infra** — `dev-stack` (DDEV, git branching staging/feature/hotfix, Makefile verbs, `.env` discipline), `secure-server` (harden a fresh Hetzner+Ploi VPS), `ploi` (full server/site lifecycle: MCP + CLI + UI). The `ploi` MCP is auto-loaded.
- **Deploy + knowledge commands** — `/deploy` (9-method dispatcher), `/memory-audit` (staleness report on STATE/lessons/todo), `/pattern-miner` (mine cross-project memory for promotable patterns).
- **MCP** — the `ploi` MCP server (server + site management via the Ploi API).

## Coding work lives in netdust-agent

For anything beyond a trivial one-file edit — features, refactors, bug fixes, security-boundary changes — load the **netdust-agent** plugin. It owns `harnessed-development` (the full design → plan → execute → shake-out → finish sequencer), the gate skills (threat-modeling, architecture-invariants, feature-acceptance, testing-workflow, test-effectiveness, shake-out, compounding, code-audit), the reviewer agents, and the harness commands (`/integration`, `/shakeout`, `/test-effectiveness`, etc.). Core no longer carries any of that.

Engineering discipline itself (brainstorming, planning, TDD, systematic debugging, code review, finishing branches, verification before completion) comes from `obra/superpowers`. **For coding, use netdust-agent + superpowers** — core does not redefine those.

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

The SessionStart hook (`hooks/session-start.sh`) injects `memory/STATE.md`, `memory/lessons.md`, `tasks/todo.md`, the harness-level `memory/GLOBAL.md`, and the site.yml summary into the initial context. It also injects a **"Memory discipline" prompt block** (only when `memory/` exists in the project) that tells Claude exactly when to update STATE, lessons, CLAUDE, and site.yml — and what *not* to write. That prompt is the difference between "Claude reads memory" and "Claude *maintains* memory."

The Stop hook (`hooks/session-stop.py`) then captures memory (logs to `~/.claude/logs/memory-hook.log` every fire):

**Track A — tagged capture (always on, deterministic, zero cost)**
When you write any of these tags in your responses during a session, the Stop hook lifts them into memory automatically:

- `DECISION: <text>` → `memory/STATE.md`
- `RISK: <text>` → `memory/STATE.md`
- `LESSON: <text>` → `memory/lessons.md`
- `TODO: <text>` → `tasks/todo.md`

Use these tags liberally when something important happens. The hook captures them deterministically — no AI guessing involved.

**Track B — Haiku summary (opt-in)**
If `ANTHROPIC_API_KEY` is set in env, the hook also calls Haiku for a PM-level state summary at session end. Falls back silently if no key — Track A still runs.

## Stack-specific plugins (layer on top)

If you're working on a WordPress project, the `netdust-wp` plugin adds WP-specific skills (wp-security, wp-database, wp-frontend, wp-testing, bedrock-composer, wp-infra) + the `ntdst-*` framework skills (architecture, data, patterns) + WP-specific commands (`/wp-new-project`, `/scaffold-plugin`, `/sync-db`, `/setup-tests`). The `netdust-statamic` plugin adds Statamic + Peak skills and commands.

The `netdust-agent` plugin layers on the coding/build harness (see above). Each layers cleanly — core stays always-on.

## Non-negotiables

See `RULES.md`. Universal rules apply to every project regardless of stack.

## Voice

See `SOUL.md`. Pushback over flattery, surface trade-offs, no sycophancy, no unnecessary abstractions. Stefan has 25 years of PHP/WordPress — match that energy. The voice is the same across stacks.
