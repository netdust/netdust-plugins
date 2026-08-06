# react-architecture — lessons from real builds

Append dated entries as projects teach us things. Each entry is a **rule plus the evidence that produced it** — not a war story. Where a lesson invalidates something in `SKILL.md`, `RULES.md` or `templates/`, say so at the top of the entry.

---

## 2026-08-06 — Houvast (Vite + React + Capacitor, device-local Art. 9 data)

First real build on this plugin. Everything below was found by **running** something, not by reading it — which is itself the headline lesson: every defect in this list looked correct on inspection, including to two independent reviewers.

### 🔴 `templates/eslint.config.mjs.tmpl` ships DEAD boundary rules

**The template is currently broken. Fix it before the next project instantiates it.**

ESLint flat config resolves a rule **last-wins by replacing the whole option object** — configs are not deep-merged per rule. The template configures `no-restricted-imports` in four blocks:

| line | scope | purpose |
| ---- | ----- | ------- |
| ~54 | `src/components/ui/**` | primitives may not import features |
| ~66 | `src/lib/**` | lib must stay feature-free |
| ~78 | `src/features/**` | features import through `index.ts` only |
| ~91 | `src/**/*.{ts,tsx}` | persistence: no `@capacitor/preferences` |

The persistence block matches everything the first three match and comes last, so **it silently deletes all three boundary rules**. Verified with `--print-config` on a minimal repro: for a file in `src/lib/**`, the resolved `no-restricted-imports` contains only the persistence entry.

```
$ npx eslint --print-config src/lib/storage/index.ts | jq '.rules["no-restricted-imports"]'
[2, { "paths": [{ "name": "@capacitor/preferences", ... }] }]   ← boundary patterns gone
```

**Rule:** never configure the same rule name in two blocks whose `files` overlap. Either merge them into one block, or express the narrower ones through a *different* rule. On Houvast the fix was moving all persistence restrictions to `no-restricted-syntax`, which freed `no-restricted-imports` for the boundaries alone and revived them.

**Corollary that generalises past ESLint:** a lint rule you have never watched fire is a comment. Both the layering rules and rule 12's enforcement were reported as "wired" in a status update, sat in a config with an explanatory comment above them, and enforced nothing.

### 🔴 Rule 12's enforcement catches ~1 of 9 ways to persist

`no-restricted-globals` matches only an **unqualified identifier**; `no-restricted-properties` matches only the **literal object name** you give it. Measured against a probe file, the template's shape catches bare `localStorage`/`sessionStorage`, `window.localStorage` and `window['localStorage']`, and misses:

`globalThis.localStorage` · `self.localStorage` · `top?.localStorage` · any aliased receiver (`const w = window; w.localStorage`) · `Storage.prototype.getItem.call(…)` · `document.cookie` · `indexedDB` · `caches` · `await import('@capacitor/preferences')`

The load-bearing fix is **omitting `object:` from the property entries** so they match any receiver:

```js
'no-restricted-properties': ['error',
  { property: 'localStorage',   message: MSG },  // no `object:` — ANY receiver
  { property: 'sessionStorage', message: MSG },
  { property: 'indexedDB',      message: MSG },
  { property: 'caches',         message: MSG },
  { object: 'document', property: 'cookie', message: MSG },
],
'no-restricted-syntax': ['error',
  { selector: "Identifier[name='Storage']", message: '…' },   // Storage.prototype
],
```

**`no-restricted-imports` cannot catch a dynamic import at all** — the rule has no `ImportExpression` visitor (`node_modules/eslint/lib/rules/no-restricted-imports.js`), so no `patterns:` config will ever see `await import('…')`. Use `no-restricted-syntax` with an `ImportExpression` selector. Also note `paths:` is exact-specifier only, so `@capacitor/preferences/dist/esm` walks past it; `patterns:` (or a syntax selector) is required.

Known residuals even after all that: `globalThis.document.cookie`, and a `Storage` aliased through a variable. Document them; ESLint cannot close them.

**esquery trap:** an attribute regex terminates at the first `/` and there is **no escape** — `\/` throws `Invalid regular expression` and crashes ESLint on the first file. Use `.` and comment why.

### 🔴 Gate scope must be a DENYLIST, or new code is born ungated

`templates/tsconfig.json.tmpl` is correct (`include: ["src"]`), but the moment a project has inherited code that cannot pass strict mode, the tempting move is to narrow `include` to the rebuilt directories. Don't. An allowlist means a future `src/shared/` or `src/config/` gets **no typecheck and no strict lint, silently**, and nothing announces it.

Invert: `include: ["src"]` plus an `exclude` naming the legacy files, and ESLint `files: ['src/**/*.{ts,tsx}'], ignores: LEGACY`. New code is then gated by construction and the exemption list can only shrink.

**`exclude` is not transitive.** A file still gets typechecked if an included file imports it, so some entries are load-bearing only while nothing gated reaches them. Find the real set by iterating `tsc` to a fixpoint, not by reading the import graph, and comment which entries are there for that reason — otherwise the next person shrinking the list deletes one that matters.

### A bite test for a lint rule must be hermetic

A fixture enumerating deliberate bypasses is deliberately broken code. Committed as a normal file it breaks `check`, `lint` and the pre-commit hook forever, and people learn to ignore a permanently-red gate.

Shape that works (`bin/gate-bite.sh` on Houvast, wired as the last step of `npm run check`): write the fixtures, run the **real** config against them, assert **one error per form**, remove them — with the cleanup on the failure path too, verified under `kill -INT`.

Five traps, all of which make a bite test pass while proving nothing. The first three were caught by the author writing it; **the last two survived into a green 23/23 board and were caught only at review, by deleting rule entries and re-running.** Assume your bite test has them until you have tried.

1. **Attribution.** Count an error only when its `ruleId` is one of the restriction rules **and** its message names your seam. Otherwise a stray `no-unused-vars` greens a fixture.
2. **`@ts-nocheck` in a fixture** trips `@typescript-eslint/ban-ts-comment` and hands every fixture a spare error to be mistaken for a catch.
3. **One form per fixture.** A `Storage.prototype.getItem.call(localStorage, …)` probe reported CAUGHT — on the bare `localStorage` in its own arguments, not on `Storage`.
4. **A type annotation is a second match.** The fix for (3) was written `(s: Storage) => Storage.prototype.getItem.call(s, …)` — and `Identifier[name='Storage']` matches the *annotation* too. Narrowing the rule to type-positions only left the bypass fully open with the board still green. **The tell was visible and ignored: that row reported `2 error(s)` where every other reported `1`.** If a fixture's count is not exactly 1, it is matching something you did not intend.
5. **One fixture per CELL, not per mechanism.** The bypass space is *mechanism × receiver* — `{localStorage, sessionStorage, indexedDB, caches, cookie} × {bare, window., globalThis., self., alias}`. Covering every receiver for one mechanism and only the bare form for the rest means three `no-restricted-properties` entries can be **deleted** with the board still green, because the bare forms are caught by `no-restricted-globals` — a different rule entirely.

And assert the **inverse**: a fixture that uses the seam correctly and must be **clean**. Note one allow-fixture is weak — a rule that errored on everything *except* files importing your seam would still pass it. A second allow-fixture of ordinary code touching no storage at all makes the discrimination check real.

**The verification that actually proves a bite test: delete each rule entry in turn and confirm the corresponding row goes RED.** Not "does the board pass" — "does the board fail for the right reason". A green board is evidence about the fixtures, not about the rules.

### Zod in a persistence seam

**`ZodType<T>` already constrains Input to Output.** Zod 3.x declares `ZodType<Output = any, Def = ZodTypeDef, Input = Output>`, so the frequently-prescribed "constrain it to `ZodType<T, ZodTypeDef, T>`" is a **no-op** — clean diff, green typecheck, finding closed, bug still shipping. Check the declaration before believing that advice.

**Transforms corrupt a storage round-trip and must be banned, not typed away.** `set()` writes `parsed.data` (the transform's *output*) and `get()` re-parses it as *input*, applying the transform again: wrote 5 → read 20 → saved → read 80, doubling on every load-modify-save cycle. A *type-changing* transform is already a compile error; a *same-type* one compiles clean, which means **every transform that compiles against a persistence seam is a corrupting one** — so rejecting them costs no legitimate use case. There is no type-level discriminator (`.refine()` and `.transform()` both yield `ZodEffects` whose `_def.effect` is a union), and a runtime check is shallow — `z.object({ n: z.number().transform(…) })` is a `ZodObject`. **A lint rule banning `.transform()` in storage schemas is the real gate.** `.refine()` stays legal.

**`safeParse` does not catch throws from `.refine()`/`.superRefine()`/`.transform()` bodies** — they propagate. If the seam's contract is "reads never throw", wrap the parse. Give a crashed schema its own diagnostic reason: "the data is from an older build" (→ write a migration) and "the schema is broken on this input" (→ fix the code) are different facts, and filing the second under the first sends someone to write a migration for data that was never wrong.

**Zod embeds received values verbatim** in `invalid_enum_value` and `invalid_literal` issues, and `ZodError.message` is a JSON dump of all issues. Never pass a `ZodError` as an error `cause` in an app holding sensitive data — build a fresh `Error` naming the issue **paths** only. Paths tell you where the bug is; values tell you what the user did. And that redaction has a precondition worth writing down: it holds only while every path segment is schema-defined, so a `z.record()` with user-typed keys puts user data back into the path.

### The storage seam's erasure contract

Written for Houvast's GDPR/App Store obligations, generalises to any app with a "delete my data" button:

- **Loud.** Reads may degrade silently to a fallback; **deletes may not.** A backend that swallows a throw makes `clear()` resolve successfully having deleted nothing — on iOS a locked data-protection class makes `removeItem` *and* `key` throw, so a swallowed `keys()` returns `[]`, which reads as "nothing of ours is stored" and erases nothing while reporting success.
- **Complete, and derived.** Every key the app ever wrote, namespaced or not. Build that list by **scanning the codebase**, never by hand — the first hand-copied list on Houvast was transcribed from the plan, and the test independently re-spelled it from the same plan, so the test agreed with the spec rather than the device and both missed the same fifth key.
- **Verified, not inferred.** Survivorship from promise status trusts the backend and races a concurrent write. Re-enumerate after the fan-out; anything still owned survived, whatever its promise said.
- **Bounded.** Leave keys the app did not write — but state the premise. Sparing a session key is right only while your users are unauthenticated.
- **Scope, by construction.** `clear()` reaches web storage only. Cookies, Cache Storage and a PWA's workbox IndexedDB are outside it.
