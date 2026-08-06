# netdust-react

Stack plugin for **Vite + React 18 + TypeScript + Tailwind**, packaged to iOS and Android with **Capacitor**.

Layers on `netdust-core` (memory, ops, deploy) and `netdust-agent` (the harness). It supplies only the stack layer — the planning/building spines, gates, and reviewer agents all live in `netdust-agent` and are stack-agnostic.

## Contents

| | |
|---|---|
| **Skills** | `react-architecture` — project shape, gate wiring, storage durability, the web/native seam |
| | `capacitor-react` — native feature access from React (vendored from [capawesome-team/skills](https://github.com/capawesome-team/skills), MIT) |
| **Templates** | strict `tsconfig`, `eslint.config.mjs` with feature boundaries, `prettier`, `lefthook`, `knip` |
| **Docs** | `docs/upstream-references.md` — what was lifted, from where, under which licence |

## Design stance: thin by default

This plugin holds what a real build has already needed. It is not a place to pre-author skills for work that has not happened.

That stance is a direct lesson from `netdust-expo`, authored in May 2026: 9 skills, 15 templates, a dedup hook and a bespoke drift-auditor agent, all written before any product code existed. A later stack decision invalidated most of it, and — because it was never registered in the marketplace — none of it ever loaded. Harness built ahead of code gets invalidated by decisions the code has not made yet.

So: **grow this from the build.** When a pattern proves itself twice, harvest it here with a dated entry in the relevant `lessons.md`.

## Status

**0.1.0 — created 2026-08-06. Has not shipped an app yet.** The templates are harvested from `netdust-expo`'s (which were themselves stack-audited in May) but have not been smoke-tested on a live repo. Run the smoke test in `templates/README.md` before trusting the boundary rules.

## Gates

`netdust-agent`'s `standards-gate` and `testing-workflow` run these on this stack:

```
npx vitest run        # tests
npx tsc --noEmit      # typecheck
npx eslint .          # lint
npx knip              # dead code
npx playwright test   # browser E2E
npx cap run ios|android   # the device pass — nothing else substitutes for it
```
