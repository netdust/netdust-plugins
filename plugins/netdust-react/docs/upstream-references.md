# Upstream references — netdust-react

**We reference, and vendor only under a clear licence.** When lifting a pattern, record the source in the skill's `lessons.md` with a dated entry, confirm the licence, and mark Netdust deviations explicitly.

## Vendored

### capawesome-team/skills — `capacitor-react`
- **URL:** https://github.com/capawesome-team/skills/tree/main/skills/capacitor-react
- **Licence:** MIT — `Copyright (c) 2026 Capawesome`. Copy retained at `skills/capacitor-react/LICENSE.capawesome`.
- **Vendored:** 2026-08-06, at clone HEAD. `SKILL.md` + `references/plugin-usage-patterns.md` + `references/custom-hooks.md`, unmodified.
- **Why vendored rather than referenced:** it is the single best public description of React↔Capacitor patterns, the licence is unambiguous, and the harness needs it loadable offline as a skill rather than as a link.
- **Netdust deviations:** recorded in `skills/capacitor-react/lessons.md`. Do not edit `SKILL.md` in place — additions go in `lessons.md` so the upstream diff stays readable when we re-sync.

## Referenced, not vendored

### Cap-go/capgo-skills
- **URL:** https://github.com/cap-go/capgo-skills
- **Licence:** unclear at time of writing — **do not lift text** until confirmed.
- **Caveat:** authored by the vendor of a commercial Capacitor OTA-update product; guidance leans toward their product. Read for coverage, paraphrase, and strip the bias.

### capawesome-team/skills — the rest of the pack
- `capacitor-plugins`, `capacitor-push-notifications`, `capacitor-platforms`, `capacitor-app-upgrades` are all MIT and directly relevant. **Not vendored yet** — pull one in when a project actually needs it, per this plugin's thin-by-default rule.

### Capacitor official docs
- **URL:** https://capacitorjs.com/docs
- Authoritative on iOS/Android configuration, permissions, and plugin APIs. Prefer over any skill text when the two disagree, and correct the skill when that happens.

## Related Netdust plugins

### netdust-expo
- Lives at `~/.claude/plugins/netdust-expo` (loose directory — **never registered in the marketplace, so it has never loaded**).
- Expo + React Native + EAS + NativeWind. **Different stack**: its `metro`, `babel`, `nativewind`, `eas-deploy`, and `rn-frontend` content does not apply here.
- Its `tsconfig.base.json`, `eslint.config.mjs`, `prettier.config.mjs`, `lefthook.yml`, and `hooks/pre-write-dedup.sh` are stack-agnostic TypeScript tooling. This plugin's templates are harvested from those, de-monorepo'd and de-Expo'd.
- If an Expo project ever materialises, that plugin needs registering and smoke-testing before it can be trusted — it has never run.
