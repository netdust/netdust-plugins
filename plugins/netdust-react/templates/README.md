# netdust-react templates

The thin mechanical layer for a single Vite + React + TypeScript app packaged with Capacitor. Copy into a project root and drop the `.tmpl` suffix.

| Template | Lands as | Install |
|---|---|---|
| `tsconfig.json.tmpl` | `tsconfig.json` | — |
| `eslint.config.mjs.tmpl` | `eslint.config.mjs` | `npm i -D eslint typescript-eslint eslint-plugin-react-hooks eslint-plugin-react-refresh globals @eslint/js` |
| `prettier.config.mjs.tmpl` | `prettier.config.mjs` | `npm i -D prettier prettier-plugin-tailwindcss` |
| `lefthook.yml.tmpl` | `lefthook.yml` | `npm i -D lefthook && npx lefthook install` |
| `knip.config.ts.tmpl` | `knip.config.ts` | `npm i -D knip` |

Add to `package.json`:

```json
{
  "scripts": {
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "format": "prettier --write .",
    "test": "vitest run",
    "knip": "knip",
    "check": "npm run typecheck && npm run lint && npm run test && npm run knip"
  }
}
```

## What is deliberately NOT here

- **`syncpack`, `turbo.json`, `pnpm-workspace.yaml`** — monorepo tooling. One app does not need a build graph.
- **`madge`** — circular-dependency detection. The ESLint boundary rules cover the layering that actually matters at this size; add madge if the app grows past a few dozen modules.
- **CI workflow** — add one when there is somewhere to deploy from. Lefthook covers the local gate until then.

This omission is the point. `netdust-expo` shipped 15 templates before a line of product code existed, and most of them were invalidated by a later stack decision. These five are the ones that pay for themselves on day one.

## Smoke test before trusting any of it

Config that has never fired is a claim, not a gate:

1. Drop the templates in, install, run `npm run check` — expect it to pass on a clean tree.
2. Break one rule on purpose: add `localStorage.getItem('x')` to a component (not a `storage.ts`).
3. `npm run lint` must fail with the rule-12 message. If it does not, the boundary config is not wired to your paths — fix it before relying on it.
