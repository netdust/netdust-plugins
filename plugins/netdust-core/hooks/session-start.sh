#!/usr/bin/env bash
# session-start.sh — netdust-core harness
# Loads project memory + harness GLOBAL into Claude's initial context.
# Logs every fire to ~/.claude/logs/memory-hook.log so you can see it working.

set -u  # don't set -e — we never want a sourced file to abort the session
CWD=$(pwd)
LOG="$HOME/.claude/logs/memory-hook.log"
TS=$(date '+%Y-%m-%d %H:%M:%S')
mkdir -p "$(dirname "$LOG")"

OUTPUT=""
FOUND=()
MISSING=()

note() {
  local key="$1" path="$2"
  if [[ -f "$path" ]]; then
    FOUND+=("$key")
  else
    MISSING+=("$key")
  fi
}

# ── Stable plugin path symlinks ─────────────────────────────────────────────
# Claude Code 2.1+ installs plugins to ~/.claude/plugins/cache/<marketplace>/
#   <plugin>/<version>/ — a versioned path that changes on every update.
# Docs, agents, commands, and templates across all three netdust plugins
# reference each other via the stable user-facing path
#   ~/.claude/plugins/<plugin>/...
# We maintain those as symlinks pointing at the active cache version, refreshed
# on every session start so updates flip automatically. Idempotent.
PLUGIN_CACHE="$HOME/.claude/plugins/cache/netdust-plugins"
if [[ -d "$PLUGIN_CACHE" ]]; then
  for plugin in netdust-core netdust-wp netdust-statamic; do
    plugin_dir="$PLUGIN_CACHE/$plugin"
    [[ -d "$plugin_dir" ]] || continue
    # Pick most recently modified version dir as "active".
    latest_version=$(ls -1t "$plugin_dir" 2>/dev/null | head -1)
    [[ -n "$latest_version" ]] || continue
    ln -sfn "$plugin_dir/$latest_version" "$HOME/.claude/plugins/$plugin"
  done
fi

# ── Harness GLOBAL.md ───────────────────────────────────────────────────────
HARNESS_GLOBAL="${CLAUDE_PLUGIN_ROOT}/memory/GLOBAL.md"
note harness_global "$HARNESS_GLOBAL"
if [[ -f "$HARNESS_GLOBAL" ]]; then
  OUTPUT+="## Netdust harness — GLOBAL\n"
  OUTPUT+="$(cat "$HARNESS_GLOBAL")\n\n"
fi

# ── site.yml (per-project operational config) ───────────────────────────────
SITE_YML="$CWD/site.yml"
note site_yml "$SITE_YML"
if [[ -f "$SITE_YML" ]]; then
  OUTPUT+="## site.yml summary (project operational config)\n"
  # Surface the keys Claude needs to know BEFORE being asked to deploy
  OUTPUT+='```yaml\n'
  OUTPUT+="$(grep -E '^(site|structure|hosting|deploy|local):|^  (name|domain|risk|description|type|webroot|wpcli_path|provider|ssh_staging|ssh_production|method|staging_command|production_command|command|note|ddev_project|url):' "$SITE_YML" 2>/dev/null | head -40)\n"
  OUTPUT+='```\n\n'
fi

# ── Project state ───────────────────────────────────────────────────────────
STATE="$CWD/memory/STATE.md"
note state "$STATE"
if [[ -f "$STATE" ]]; then
  OUTPUT+="## Project State\n"
  OUTPUT+="$(cat "$STATE")\n\n"
fi

# ── Project lessons ─────────────────────────────────────────────────────────
LESSONS="$CWD/memory/lessons.md"
note lessons "$LESSONS"
if [[ -f "$LESSONS" ]]; then
  OUTPUT+="## Project Lessons\n"
  OUTPUT+="$(cat "$LESSONS")\n\n"
fi

# ── Open tasks carried forward ──────────────────────────────────────────────
TODO="$CWD/tasks/todo.md"
note todo "$TODO"
if [[ -f "$TODO" ]]; then
  OUTPUT+="## Open Tasks (carried forward)\n"
  OUTPUT+="$(tail -50 "$TODO")\n\n"
fi

# ── Memory discipline prompt (only if this project has memory scaffolding) ──
# Drop this in when memory/STATE.md OR memory/lessons.md exists, so the
# instructions don't appear in scratch projects without the harness layout.
if [[ -f "$STATE" ]] || [[ -f "$LESSONS" ]]; then
  OUTPUT+="## Memory discipline (read once, follow throughout the session)\n\n"
  OUTPUT+="You have read-write access to this project's \`memory/STATE.md\`, \`memory/lessons.md\`, \`CLAUDE.md\`, and \`site.yml\`. Keep them current as the session unfolds — they are the next session's only context.\n\n"
  OUTPUT+="**Update \`memory/STATE.md\` when** something happens that future-you would need to know cold:\n"
  OUTPUT+="- a decision made (with the *why*)\n"
  OUTPUT+="- a deploy that landed, a thing renamed/moved/deleted, a config that changed\n"
  OUTPUT+="- a known-broken or fragile area discovered\n"
  OUTPUT+="- the answer to \"what state is the project in right now?\"\n\n"
  OUTPUT+="**Append to \`memory/lessons.md\` when**:\n"
  OUTPUT+="- the user corrects you (\"no, not like that\", \"don't do X\") — capture the rule AND the *why* AND \"how to apply\"\n"
  OUTPUT+="- the user confirms a non-obvious approach worked (validated judgment, save it)\n"
  OUTPUT+="- you burn time on a gotcha that would bite again (Chrome flags, env quirks, library footguns)\n"
  OUTPUT+="- you give up on something — be honest about why, no self-serving postmortems\n\n"
  OUTPUT+="**Update \`CLAUDE.md\` / \`site.yml\` when** the project's shape changes — files moved, deploy command changed, a page added/removed, a convention shifted. Anything that contradicts what's currently written.\n\n"
  OUTPUT+="**Style rules:**\n"
  OUTPUT+="- Be specific. Name files, paths, commands. \"Updated styles\" is useless; \"deleted .phase-strip block at site.css L937-1021\" is the bar.\n"
  OUTPUT+="- Lead with the *why*. \"Removed traject.html because\" beats \"removed traject.html\".\n"
  OUTPUT+="- Don't write trivia. A typo fix or one-line tweak doesn't earn a memory entry.\n"
  OUTPUT+="- Don't ask permission to update memory mid-session. Just do it. The user reviews the diff.\n\n"
  OUTPUT+="**Tag shortcuts** (the Stop hook lifts these into memory deterministically — use them when you don't want to interrupt the flow to edit a file): write \`DECISION: ...\`, \`RISK: ...\`, \`LESSON: ...\`, \`TODO: ...\` in your response and they get captured.\n\n"
  OUTPUT+="The goal: a session in 3 months should pick up where this one left off, with no re-explaining.\n\n"
fi

# ── Log every fire ──────────────────────────────────────────────────────────
{
  printf '[%s] session-start cwd=%s found=[%s] missing=[%s]\n' \
    "$TS" "$CWD" "$(IFS=,; echo "${FOUND[*]:-}")" "$(IFS=,; echo "${MISSING[*]:-}")"
} >> "$LOG"

# ── Output context if we have something ─────────────────────────────────────
if [[ -n "$OUTPUT" ]]; then
  printf -- '---\n# Memory loaded for: %s\n\n' "$CWD"
  printf -- '%b\n---\n' "$OUTPUT"
fi
