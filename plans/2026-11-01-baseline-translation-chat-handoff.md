# Hand-off — chat translation in ntdst-baseline (brief for the spec)

**Date:** 2026-11-01
**Repo for the work:** `ntdst-baseline` — the spec goes to `specs/translation-chat/spec.md` there
(rename if the brainstorm picks a better name). This file is the brief, not the spec.
**Class:** A feature on top of wp-ai-base (`netdust-plugins/specs/wp-ai-base/spec.md`). Security
boundary: it sends post text to an outside model and writes copies, so
`netdust-gates:threat-modeling` runs before the tasks.
**Status:** BRIEF — nothing designed in code, nothing committed in baseline.
**Origin:** cloud session 2026-11-01, Stefan:
- "the translation service will become super easy to use if we can connect WordPress to chatgpt
  or claude chat using MCP"
- "That works, I use the cli to setup a language. Customers connect to chatgpt or claude"
- "if I can use a plugin in the meantime ok. This will seriously help people with translation
  to start with"
- "Translation spec for baseline? Create a hand-off for laptop"

## How to start on the laptop

1. **Plan 6 of wp-ai-base first** (`integration-suite`, baseline half). Plan 2 (`package-gate`)
   is merged in wp-starter (`424274b`), so plan 6 is unblocked. This feature's tests belong in
   that real-WordPress tier: Polylang linking, layout JSON round trips and an ability dispatch
   are what Brain Monkey cannot prove. Plans 5 and 7 can run alongside or later; they do not
   touch baseline.
2. Write the spec in parallel: `netdust-gates:policy` → brainstorm with Stefan on the rulings
   below → `specs/translation-chat/spec.md` in baseline → threat model → plan → `/plan-review`.
3. Add one row to wp-ai-base's cut table (`## The cut`) pointing at this spec as plan 8, after 6.
4. Build after plan 6 is on main.

## The goal in one line

A client opens Claude or ChatGPT, connected to their site, and says "translate the new page into
French" or "improve the Dutch of the contact page". The model reads the source text through one
ability, translates it itself, and writes it back through another. The copy stays a draft with
the review flag set until a human checks it in wp-admin.

Setting up a language stays CLI work (`wp ntdst polylang setup`, `translate`). Chat fills and
improves copies; it never creates one.

## What already exists (ground truth, baseline `main` at `2.23.0`)

The module is `services/polylang/`, config filter `ntdst/baseline/polylang/config`
(`PolylangService::DEFAULTS`). It has no REST routes today; translation is WP-CLI only
(`Cli/Commands.php::translate()`), plus `translate_copies` (off by default) and `Retranslation`.

The seam is already clean. Read these before designing anything:

| Piece | What it does | Why it matters here |
|---|---|---|
| `Translation/TextBundle.php` | `collect($post, $map, $layouts)` gathers every translatable string of a record (title, excerpt, allow-listed YOOtheme layout props, text meta) in one fixed collection order. `strings()` returns that ordered list, `apply($translated)` puts a same-length list back, `hash()` fingerprints the source | This is the whole contract the model needs: an ordered list out, a same-length list in |
| `Translation/TranslatedCopy.php` | `prepare($from, $lang)` collects, translates through `PolylangService::translator()`, then guards: same count, HTML comments copied exactly, `SourceAttributes::kses` per string, the source's layout comments kept. `write($copyId, $prepared)` stores columns and meta, sets `_ntdst_translation_unchecked`, the source hash and the written hash | Chat must go through these same guards and this same write. The provider is resolved inside the private `translate()`, not injected |
| `Translation/TranslatorInterface.php` | `translate(array $strings, string $from, string $to): array`, same order in, same count out | The natural seam: let `prepare()` take an optional provider, and the chat path passes one whose answers are the strings the model sent |
| `Translation/UncheckedReview.php` | List column, list filter, and a box on a flagged copy whose checkbox clears the flag | The human gate. Chat output lands here |
| `Translation/Retranslation.php` | A default-language edit refreshes every copy that is still flagged and still holds exactly what baseline wrote (both hashes) | Interacts with chat writes, see ruling 4 |
| `Cli/Commands.php::translate()` | Refuses a non-draft target without `--force`; a new target is created as a draft | The CLI's own posture on live copies; ruling 3 asks whether chat matches it |

Invariants the design must respect (`ntdst-baseline/ARCHITECTURE-INVARIANTS.md`):

- **INV-8, one create path.** A translation is born only in `Cli/Commands.php::insertTranslation()`.
  Chat therefore fills or refreshes an existing copy, exactly like `PlusTranslation` and
  `Retranslation`. This matches Stefan's "I use the cli to setup a language".
- **INV-2, one configuration door.** The feature is switched by a key in
  `ntdst/baseline/polylang/config`, never an option.
- **INV-6, one bridge into the builder.** Layout strings come from `LayoutTranslator` as today;
  no new YOOtheme access.
- **INV-7, one boot loop.** New classes resolve through `ntdst_get()`.

From core (`ntdst-core` 5.5.0, README `### 5.5.0 — abilities`):

- A route gets an `ability` block and becomes a tool. Declared is exposed; there is no private
  ability, so the config switch is what keeps the routes from existing on a site that did not
  opt in.
- `name`, `label`, `description` required. A write verb also needs `destructive` and `idempotent`.
  An output schema is required, from the route's `schema` or the block.
- The route's permission is the ability's permission and runs twice per execution; path
  parameters reach it, so a per-object `edit_post` check works.
- **Baseline requires `netdust/ntdst-core: ^5.4` today.** On core below 5.5.0 a route with an
  `ability` block is not registered at all. Bump the requirement to `^5.5` in the same change.
- Baseline's existing route namespace is `ntdst-baseline/v1` (the cache purge), so the abilities
  are named `ntdst-baseline-v1/<name>` unless the spec picks its own namespace and category.

## A starting design to brainstorm against

Three abilities. All names are placeholders.

| Ability | Verb | Does |
|---|---|---|
| `list-unchecked-translations` | GET | Flagged copies, optionally per language: copy id, title, language, source id, modified date |
| `get-translation` | GET `/translations/(?P<id>\d+)` | For one copy: the source's strings, the copy's current strings in the same order, both languages, and the source hash |
| `save-translation` | POST `/translations/(?P<id>\d+)` | Takes the translated list and the source hash from the read. Refuses when the source changed since the read (hash differs) or the count is wrong. Otherwise runs the same guards and `write()`; the copy stays flagged |

Notes on that design:

- **The stale-read guard is the hash.** The model may take minutes between read and write; the
  source can change meanwhile. Sending `TextBundle::hash()` back makes the write optimistic and
  refuses a misaligned list instead of corrupting a layout.
- **One write path.** Refactor `prepare()` to accept an optional `TranslatorInterface`; the chat
  route passes a provider that returns the model's list. Every guard and the flag come for free,
  and there is no second writer to drift.
- **No "mark checked" ability.** The flag is the human gate; clearing it stays in wp-admin.

## Rulings Stefan has to make (the brainstorm)

| # | Question | Recommendation |
|---|---|---|
| 1 | Which site pilots it? It must run the polylang module and have a client who wants this | Stefan names it; the threat model names its data |
| 2 | Does baseline register a chat role, or does each site? | Baseline registers one role and one capability (for example `ntdst_translate`), off unless the chat switch is on. Every Polylang site wants the same thing, and the role is the limit of what chat can do |
| 3 | May chat write to a published copy? | No. Drafts and pending only, matching the CLI's refusal without `--force`. A published copy changes only through wp-admin |
| 4 | After chat writes a copy, may `Retranslation` overwrite it with DeepL when the source changes? | No. Chat output is closer to a human edit than a machine pass: either do not store a written hash for chat writes, or mark the source of the write so `Retranslation` skips it. The spec decides how |
| 5 | Should reads include the copy's current text, so the model can improve rather than replace? | Yes, already in the design above |
| 6 | Text meta on ntdst models: in scope from day one, or titles, excerpts and layouts first? | Same scope as the CLI: whatever `TextBundle` collects. It is one bundle |
| 7 | Rate limit on the write | Yes, through the route's `rate_limit`; core charges once per execution |

## The interim connection until WordPress ships OAuth (targeted for 7.3)

- **Plugin:** Enable Abilities for MCP (wordpress.org, free, open source, 5,000+ installs, tested
  to 7.1.4). It runs on the official MCP Adapter, exposes other code's abilities with a switch
  per ability, and gives claude.ai an OAuth 2.1 connector with only a URL. ChatGPT is beta and
  needs developer mode on a paid plan. Each OAuth session is stored as a WordPress application
  password named "MCP OAuth…", acting as the user who consented.
- **Consequences for this spec:**
  - Baseline's `security` switch `application_passwords_capability` (default `manage_options`)
    must point at the chat role's capability, or the client consents and then nothing works.
  - Switch off every built-in tool of the plugin; expose only the three translation abilities.
    Its changelog fixed two serious authorization bugs in those built-in tools (2.13.3, 2.13.7).
  - `revoke_sessions_after_reset` already deletes application passwords on a password reset,
    which ends the OAuth sessions too. Keep it on.
- **This is site configuration, not baseline code.** Document it in the README; do not add the
  plugin to baseline's `composer.json`. At 7.3 the plugin is deactivated, its sessions end, and
  the adapter and abilities stay.
- **Until then, for Stefan himself:** Claude Code or Claude Desktop with an application password
  works without the plugin.

## For the threat model

- **Asset:** page text, including drafts not yet public, sent to Anthropic or OpenAI under the
  client's own account. Name it in the pilot site's documentation; the client decides.
- **Prompt injection through content.** The model reads page text that anyone with edit rights
  wrote. Mitigation in the design: the abilities can only read flagged copies and write strings
  into one draft copy, through guards that refuse new HTML comments and run kses.
- **Object-level access.** Permission is the chat capability plus `edit_post` on the copy id.
  The 2.13.3 bug in the interim plugin was exactly a missing object-level check.
- **Path smuggling.** Core already `rawurlencode`s path parameters into the dispatch (core
  threat model T5).
- **Output schema on a write.** WordPress validates the output after the write committed. Keep
  `save-translation` idempotent so a retry after `ability_invalid_output` is harmless (core
  review M3).
- **Audit.** `ntdst-audit` lives inside Stride only. "Was it the chat?" is answerable later
  through application-password authentication and the 7.1 `wp_ability_invoked` action, once
  ntdst-audit is packaged (separate work, not this spec).

## Not in this spec

- Creating copies or adding languages from chat (INV-8; CLI stays the door).
- Publishing, or clearing the review flag, from chat.
- Packaging `ntdst-audit` for other sites.
- Any OAuth code of our own.
