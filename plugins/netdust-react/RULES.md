# Netdust React Rules

**React + Capacitor-specific rules.** Universal rules (no `.env` commits, no direct-to-`main`, etc.) live in `netdust-core/RULES.md` — they apply here too.

**Violating the letter of these rules is violating the spirit of these rules.**

## The Capacitor seam

1. **A green browser test is not a passing native run.** Vitest and Playwright both run in a browser engine that is not the WebView on the device. Any task touching storage, permissions, notifications, files, or the back button closes on a real iOS *and* Android device — or it does not close.
2. **`localStorage` is not durable on iOS.** WKWebView storage can be evicted by the OS and does not survive reinstall. Anything the user would grieve losing goes in `@capacitor/preferences` or SQLite. If a project deliberately accepts localStorage for v1, that acceptance is written down in the project's `memory/STATE.md` with the data-loss consequence stated.
3. **Guard native-only calls** with `Capacitor.isNativePlatform()` or `Capacitor.getPlatform()`. Never assume a plugin has a web implementation.
4. **Always clean up Capacitor listeners** in the `useEffect` return. React 18 strict mode double-mounts in dev — that is the check working, not a bug to suppress.
5. **`npx cap sync` after every dependency or config change.** A missing sync presents as "plugin not found at runtime" and wastes an afternoon.

## TypeScript

6. **`strict: true` plus the extended flags** from `templates/tsconfig.json.tmpl` (`noUncheckedIndexedAccess`, `noImplicitReturns`, `noFallthroughCasesInSwitch`). Not negotiable per-project; a project that cannot compile under them has a defect, not a config problem.
7. **`any` needs a comment naming what is unknown and what would remove it.** `unknown` plus narrowing is almost always the honest version.
8. **`npx tsc --noEmit` is a task-close gate.** The cheapest gate on this stack.

## Code

9. **Function components only.** No class components in new code.
10. **Colocate by feature, not by file type.** A feature owns its components, hooks, schema, and storage access. Shared UI primitives live in `src/components/ui/`; genuinely shared logic in `src/lib/`. Do not grow a global `hooks/` bucket of unrelated hooks.
11. **One source of truth per piece of state.** Server state in TanStack Query, form state in react-hook-form, persistent state behind one storage module. State that lives in two places diverges — that is not a maybe.
12. **All persistent reads/writes go through one storage module per feature.** Never scatter raw `localStorage.getItem` across components: it makes the eventual migration to Preferences/SQLite a rewrite instead of an edit. This is the convergence point an `ARCHITECTURE-INVARIANTS.md` should name.
13. **Zod at every trust boundary** — anything read back from storage, a URL, or the network is parsed, not cast. Persisted data written by an older build is untrusted input.
14. **No dead shadcn primitives.** `npx knip` before claiming clean.

## Hygiene

15. **Exactly one lockfile per repo.**
16. **No secret behind a `VITE_` prefix.** Vite inlines it into the client bundle. Every `VITE_` value is public by construction.
17. **ESLint + Prettier on every commit**, via `templates/lefthook.yml.tmpl`.
