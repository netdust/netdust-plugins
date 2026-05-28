# Netdust Plugins

Claude Code plugin monorepo. Three plugins published as a single marketplace.

## Plugins

| Plugin | Role |
|--------|------|
| `netdust-core` | Cross-stack discipline (hooks, memory, skills, agents, MCP). Stack-agnostic. |
| `netdust-wp` | WordPress framework knowledge (NTDST/Bedrock). Layers on core. |
| `netdust-statamic` | Statamic 6 + Peak. Layers on core. |

## Install

Add the marketplace once:

```bash
claude plugin marketplace add netdust/netdust-plugins
```

Install the plugins you want:

```bash
claude plugin install netdust-core@netdust-plugins
claude plugin install netdust-wp@netdust-plugins     # only on WP machines
claude plugin install netdust-statamic@netdust-plugins  # only on Statamic machines
```

Restart Claude Code to pick up newly-installed plugins.

## Update

```bash
claude plugin update netdust-core
```

(Restart required to apply.)

## Develop

This repo IS the source of truth. Edit in `plugins/<name>/` and commit. To
test changes locally before pushing:

```bash
claude plugin marketplace add ./   # if not already added from a local clone
# then re-install from the local path
```

Releases are tagged per-plugin via `claude plugin tag plugins/<name>` which
creates a `<name>--v<version>` git tag (validated against plugin.json).

## Open follow-ups

### Cross-plugin imports in user-project CLAUDE.md

The `wp-new-project` command historically emitted `@~/.claude/plugins/netdust-wp/CLAUDE.md`
into generated project `CLAUDE.md` files. With the marketplace install, plugins
live at versioned cache paths (`~/.claude/plugins/cache/netdust-plugins/netdust-wp/<version>/CLAUDE.md`),
which would break on every plugin update.

**Resolution (2026-05-28):** dropped the `@import` from the template. Skills are
the long-term answer — they're invoked explicitly when needed and don't depend
on a stable filesystem path. If future-us decides we DO need always-on context
in project CLAUDE.md from the plugin, options to revisit:

1. Have plugin install/post-install create a stable symlink at
   `~/.claude/plugins/netdust-wp` → currently-installed cache version.
2. Replace `@import` with a slash-command snippet (`/netdust-wp:context`) that
   loads the same content on demand.
3. Move always-on context into a top-level skill that auto-activates on
   project-dir match.

This note exists so the question gets revisited deliberately.
