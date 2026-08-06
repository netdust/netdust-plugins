# Netdust React Plugin

You are working on a Netdust **React** project — a Vite + React + TypeScript web app, packaged to iOS and Android with Capacitor. This plugin layers on `netdust-core` (memory conventions, ops, deploy) and `netdust-agent` (the coding harness — `harnessed-development`, the planning/building spines, `testing-workflow`, `standards-gate`, the reviewer agents, and the live hooks). Install both first.

## Default assumptions (project `CLAUDE.md` can override)

- **Build tool**: Vite 5+
- **UI**: React 18 + TypeScript 5, function components only
- **Styling**: Tailwind 3 + shadcn/ui (Radix primitives)
- **Native shell**: Capacitor 6+ — iOS and Android from the same web build
- **Forms / validation**: react-hook-form + Zod
- **Server state**: TanStack Query (only where there IS server state)
- **Tests**: Vitest + Testing Library (unit/component), Playwright (browser E2E)
- **Package manager**: npm unless the project says otherwise — **exactly one lockfile**

**This plugin is deliberately thin.** It holds what more than one project has already needed. When a pattern proves itself in a real build, harvest it here; do not author skills ahead of the code that would use them.

## The gate wiring netdust-agent reads

`netdust-agent`'s `standards-gate` and `testing-workflow` auto-detect the stack's runners. On this stack they are:

| Gate | Command |
|---|---|
| Tests | `npx vitest run` |
| Typecheck | `npx tsc --noEmit` |
| Lint | `npx eslint .` |
| Format | `npx prettier --check .` |
| Dead code | `npx knip` |
| E2E (browser) | `npx playwright test` |

A task close that touches `.ts`/`.tsx` runs tests + typecheck + lint. Typecheck is not optional here — it is the cheapest gate on the stack and catches the largest class of React refactor breakage.

## What this plugin adds

| Layer | Contents |
|---|---|
| **Skills** | `react-architecture` (project shape, gate wiring, storage durability, the Capacitor seam), `capacitor-react` (native feature access from React — lifted from capawesome-team/skills, MIT) |
| **Templates** | `tsconfig.json`, `eslint.config.mjs`, `prettier.config.mjs`, `lefthook.yml`, `knip.config.ts` — the thin mechanical layer, single-app (not monorepo) |

## What lives in netdust-core / netdust-agent (not here)

- Memory + tag conventions (`DECISION:`, `RISK:`, `LESSON:`, `TODO:`) — netdust-core
- `ploi`, `secure-server`, `dev-stack`, `/deploy` — netdust-core
- The harness — `harnessed-development`, `planning`, `building`, `testing-workflow`, `standards-gate`, `threat-modeling`, `architecture-invariants`, `feature-acceptance`, `test-effectiveness`, `shake-out`, `compounding` — netdust-agent
- The reviewer agents (`reviewer`, `security-sentinel`, `performance-oracle`, `code-simplicity-reviewer`, `invariant-auditor`, `shakeout-qa`) — netdust-agent
- Generic frontend craft — `netdust-agent:building-frontend` and the `frontend-design` plugin

## How this plugs into `harnessed-development`

`netdust-agent:harnessed-development` is the entry point for any code-changing work. It routes by class; this plugin supplies the stack layer it defers to:

- **Plan (Stage 1)** — `react-architecture` for project shape and the Capacitor seam. No React-specific plan-requirements gate exists yet (unlike `netdust-wp:wp-plan-requirements`); if one earns its place, author it here.
- **Execute (Stage 2)** — `capacitor-react` when the task touches native features; `netdust-agent:building-frontend` for UI craft. Gates as per the table above.
- **Shake-out (Stage 3)** — the generic `netdust-agent:shake-out`. A device pass on real iOS and Android hardware is part of it; a passing browser E2E run is **not** a passing native run.

## The Capacitor seam — the rule that matters most

The web build and the native app are not the same environment. Everything that works in the browser can still fail in a WKWebView or an Android WebView.

**Browser-only APIs are the failure mode.** `window.localStorage`, `navigator.geolocation`, `Notification`, the File API — these all *exist* in the WebView, so they compile, they pass Vitest, they pass Playwright, and they behave differently or lose data on device.

- **`localStorage` is not durable storage on iOS.** WKWebView data lives in a cache the OS may evict under storage pressure, and it does not survive an uninstall/reinstall. For anything a user would be upset to lose, use `@capacitor/preferences` (small values) or SQLite (larger sets) — see `react-architecture`.
- Guard native-only calls with `Capacitor.isNativePlatform()`.
- After any dependency or config change: `npm run build && npx cap sync` before `npx cap run ios|android`.

## Tooling notes

- **Exactly one lockfile.** A repo carrying `package-lock.json` *and* `bun.lock` installs differently on two machines. Pick one, delete the others, commit the decision.
- **`.env` is never committed** — see `netdust-core/RULES.md`. Vite inlines every `VITE_`-prefixed variable into the client bundle: treat all of them as public, and never put a secret behind that prefix.
- **Knip earns its keep on shadcn projects.** The scaffold drops ~50 UI primitives in; most go unused. Run it before claiming a codebase is clean.
