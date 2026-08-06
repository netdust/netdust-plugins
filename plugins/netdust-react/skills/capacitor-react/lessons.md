# capacitor-react — Netdust lessons & deviations

`SKILL.md` and `references/` are vendored **unmodified** from [capawesome-team/skills](https://github.com/capawesome-team/skills/tree/main/skills/capacitor-react) (MIT, © 2026 Capawesome), on 2026-08-06. Keep them that way so a future re-sync is a readable diff. Everything Netdust-specific goes here.

## Deviations from upstream

### 1. Project structure — we use `features/`, upstream uses `services/`

Upstream's Step 2 shows `src/services/` for Capacitor plugin calls. Netdust colocates by feature instead — see `react-architecture` §1. Where the upstream skill says "put it in `src/services/`", read "put it in the feature that needs it, or `src/lib/` if genuinely shared."

Upstream's own instruction covers this: *"If the project does not follow this structure, adapt all guidance to the project's actual directory layout."*

### 2. Storage — upstream mentions the trap in passing; we make it a rule

Upstream's Error Handling section says:

> **Build works on web but fails on native**: Check for browser-only APIs (`window.localStorage`, `navigator.geolocation`) used without Capacitor alternatives.

That is correct but understated, and it is filed under errors rather than design. The failure it describes is usually not a build failure — it is **silent data loss months later**, because `localStorage` works fine in the WebView right up until iOS evicts it or the user reinstalls.

Netdust treats this as an architectural rule, not an error-handling note: `RULES.md` rule 2 and `react-architecture` §3. Persistence converges on a feature's `storage.ts`, and the ESLint config makes a direct `localStorage` reference outside that module a lint error.

### 3. State management — same conclusion, stated harder

Upstream: *"Do not recommend adding a state management library unless the user's requirements justify it."* We agree and go further — see `react-architecture` §5 for the default assignment of each kind of state. On a device-local app, TanStack Query + `useState` + a storage module is usually the whole answer.

## Not yet vendored from the same pack (all MIT)

Pull one in when a project actually needs it — thin by default:

- `capacitor-plugins` — installing/configuring plugins
- `capacitor-push-notifications` — FCM setup
- `capacitor-platforms` — iOS/Android platform config
- `capacitor-app-upgrades` — major-version upgrades

## Lessons from real builds

*(Append dated entries as projects teach us things. Empty is honest — this plugin was created 2026-08-06 and has not shipped an app yet.)*
