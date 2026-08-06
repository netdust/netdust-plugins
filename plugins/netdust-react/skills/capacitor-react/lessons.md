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

### 2026-08-06 — Houvast (first build on this plugin; pre-device, WebView reasoning verified at source)

Not yet run on a physical device — everything below was verified in source, in a real browser at 390×844, or against the installed packages. Device-only items are marked.

**`viewport-fit=cover` or every safe-area inset is zero.** Without it in the `<meta name="viewport">`, `env(safe-area-inset-*)` resolves to `0` on iOS and a `fixed bottom-0` tab bar sits under the home indicator. All of a shell's safe-area CSS is dead code without that one attribute, and nothing reveals it until a device build. Houvast's inherited `index.html` did not have it.

**You cannot unit-test the insets — test the meta tag instead.** jsdom silently drops `env()`: setting `el.style.paddingBottom = 'max(0.5rem, env(safe-area-inset-bottom))'` leaves the style attribute `null`. So an assertion on the padding is a *fake test*. Put the regression guard on the meta tag (read `index.html` with `readFileSync`), and put the insets themselves on the device shakeout manifest. Note `import.meta.url` is an `http:` URL under jsdom — resolve from `process.cwd()`.

While you are in that tag: drop `user-scalable=no` / `maximum-scale=1`. It blocks pinch-zoom (WCAG 1.4.4), and Lovable-generated apps ship it by default.

**`localStorage` is origin-partitioned and Capacitor changes the origin.** The packaged app serves from `capacitor://localhost` (iOS) / `https://localhost` (Android); a web or PWA build's data sits under its web origin. **No store install can ever read it.** So a "migrate the old data on first launch" task is worth exactly nothing to every user who arrives through a store — the only mechanism that crosses an origin boundary is an explicit export/import. Establish this before anyone plans a migration; on Houvast it removed a whole work item and answered a question that was blocking the build.

**`react-dom` logs the raw caught error to `console.error` unconditionally — production builds included** (`console.error(b.value)` in the production bundle). In a WebView that goes to Logcat / os_log, which persist and are captured by a sysdiagnose. An error boundary can therefore stop being a *second* source, but cannot stop React. If the app holds sensitive data, the rule has to live at the **throw site**: no screen throws an `Error` whose message interpolates stored data, and no crash reporter ships without a `beforeSend` scrubber. Write it as an invariant — it is not fixable in code.

Related: `errorInfo.componentStack` is component names only and is safe to log. `error.name` is the only part of an `Error` that is safe by construction; `message` and `stack` both carry an interpolated value.

**Error boundary placement, for an app with a safety-critical surface.** Wrap the screen outlet **only** — never the header holding the SOS/crisis UI, or the boundary swallows the thing it exists to protect. Test it so a whole-tree wrap *fails*: assert the safety control is still inside `role="banner"` and the error `alert` is inside `main` and not the banner.

Two follow-ons found the same day:
- **Use `key={pathname}`, not a hand-rolled `resetKey` + `componentDidUpdate`.** The hand-rolled version compares against the *previously committed* props, so navigating into a crashing screen renders it twice and doubles every crash report. React's own remount discards the error state before render instead of after commit, and deletes ~12 lines.
- **A screen boundary does not protect the shell.** A crash in the header, the tab bar or the shell component itself still blanks the app. If a crisis/safety surface must survive *any* crash, it needs a root fallback that renders that surface with no router, no shell and no user data.

**Deletes and enumeration follow the write side, not the read side.** The same locked iOS data-protection class that makes `getItem` throw makes `removeItem` and `key` throw too — but the consequences invert. A swallowed read shows a fallback; a swallowed delete reports an erasure that never happened, and a swallowed `keys()` returns `[]`, which an erasure routine reads as "nothing of ours is stored". If you ship a "delete my data" button (Apple requires one), that path must be loud. See `react-architecture/lessons.md` for the full erasure contract.

**A green jsdom test is not a passing native flow** — the plugin already says this; here is the concrete instance. `expect(link).toHaveAttribute('href', 'tel:106')` proves the attribute, not that a WKWebView hands the URL to the dialer. On a crisis surface that distinction is the whole point. It belongs on the shakeout manifest as a device item.
