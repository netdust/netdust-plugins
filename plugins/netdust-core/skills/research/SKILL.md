---
name: research
description: Use when investigating a technical question, hook, plugin behavior, function signature, framework convention, or unfamiliar codebase — before writing code. Triggers when the agent doesn't know how something works (a hook, a plugin API, a WP function's edge cases, a Composer package, a Statamic addon, a third-party service's auth flow). Activates on keywords how does X work, what's the API for, where is X defined, why does Y do Z, plugin source, hook reference, codex, developer.wp.org, context7. Symptoms include needing to call an unfamiliar function, debugging a third-party plugin's behavior, choosing between two libraries, deciding how to integrate with a service. Do not skip when "I think I know how it works" — verify before relying on memory.
---

# Research before code

A confident wrong answer costs more than an honest unknown. This skill says how to investigate technical questions before relying on assumptions.

## Order of operations

1. **Read the source.** If it's in the project (a plugin, a vendor package), open it. WordPress is mostly readable PHP. Most "magic" is just badly-named hooks.
2. **Check the docs.** developer.wordpress.org for core, WPackagist for plugin metadata, the plugin's own docs for behavior. Use `context7` MCP for current library docs — better than guessing from training data.
3. **Search the project.** `grep` for the function/hook name. Existing usages teach the conventions.
4. **Read recent git history.** `git log -p -S '<symbol>'` shows when and why something was introduced.
5. **Ask, don't guess.** If the project owner (Stefan) knows the answer, asking is faster than reverse-engineering.

## When to spike vs read

- **Read first** for: API signatures, framework conventions, hook semantics, plugin behavior with documentation.
- **Spike (write throwaway code)** for: timing-dependent behavior, race conditions, performance characteristics, things the docs gloss over.
- A spike is `dd($foo); exit;` in a one-line plugin file, observed via Query Monitor or the browser. Throw it away after.

## WordPress-specific research moves

| Question | Where to look |
|---|---|
| What does this hook do? | developer.wordpress.org/reference/hooks/<hook-name> — has every plugin/theme that fires it |
| When does this hook fire (ordering)? | Search core source: `grep -rn 'do_action.*<hook>' web/wp/` |
| What capabilities does this admin page require? | The page's `add_menu_page` / `add_submenu_page` call — capability is arg #3 |
| How does this plugin store its data? | `wp_options` rows + custom tables — `wp db query "SHOW TABLES LIKE 'wp_%<plugin>%';"` |
| What hooks does this plugin emit? | `grep -rn 'do_action\|apply_filters' web/app/plugins/<plugin>/` |
| What does this LearnDash function actually return? | Read `web/app/plugins/sfwd-lms/` — LearnDash's source is its only reliable doc |

## Third-party services

- Read the API reference first. If pricing/quotas matter, check that page too.
- Look for an official SDK (Composer or npm) before writing HTTP calls by hand.
- Check the service's status page if behavior is intermittent.
- For OAuth flows: read the auth spec, then verify your understanding with curl against their token endpoint before integrating with PHP.

## Context7 (for library docs)

Use `context7` MCP for current docs of any library/framework — even well-known ones (React, Next.js, Composer packages). Your training data is months/years old; library APIs drift. Prefer context7 over web search for library reference.

Do NOT use context7 for:
- Domain logic / business decisions
- WordPress core specifics (use developer.wordpress.org)
- Debugging the current project's code (read the project's source)

## When research is "done"

You can answer:
- What does this do?
- What does it NOT do?
- What edge cases does it not handle?
- What does the project already do similar to this?

If you can't answer those, keep researching. Don't write code yet.

## Cost of skipping research

- Wrong assumptions about a hook's timing → 2-hour debugging session.
- Wrong assumptions about a function's return type → silent type juggling → bug in prod.
- Copy-paste from Stack Overflow without checking the WP version → deprecated API call.

## See also

- `market-research` — for non-technical research (audiences, competitors)
- `netdust-agent:reviewer` (agent) — for systematic review of existing code (the coding harness owns code review now)
- `superpowers:systematic-debugging` — when research is debugging something already broken
