#!/usr/bin/env bash
# session-start.sh — netdust-core harness
# Loads project memory + harness GLOBAL into Claude's initial context.
# Logs every fire to ~/.claude/logs/memory-hook.log so you can see it working.

set -u  # don't set -e — we never want a sourced file to abort the session

# Claude Code injects CLAUDE_PLUGIN_ROOT when it fires the hook. Under bare
# invocation (tests, manual runs) it's unbound, which `set -u` turns into a
# fatal abort at first use. Self-resolve from the script's own location —
# this file lives at <plugin_root>/hooks/session-start.sh — so the hook works
# the same whether or not the env var was provided.
: "${CLAUDE_PLUGIN_ROOT:=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

CWD=$(pwd)
LOG="$HOME/.claude/logs/memory-hook.log"
TS=$(date '+%Y-%m-%d %H:%M:%S')
mkdir -p "$(dirname "$LOG")"

OUTPUT=""
FOUND=()
MISSING=()

# load_with_budget <file> <budget_bytes> <label>
#   Loads <file> into OUTPUT, but never more than <budget_bytes>. When the
#   file exceeds the budget, loads whole sections (## / ### headers) from the
#   top until the next section would cross the budget — never cutting a section
#   mid-body — then appends a visible truncation notice naming the file size
#   and the ## headers that were NOT loaded. Updates INJECTED_BYTES.
load_with_budget() {
  local file="$1" budget="$2" label="$3"
  local total_bytes
  total_bytes=$(wc -c <"$file" 2>/dev/null || echo 0)

  if (( total_bytes <= budget )); then
    OUTPUT+="$(cat "$file")\n\n"
    return
  fi

  # Over budget — walk sections, accumulating whole sections until the next
  # one would exceed the budget. A "section" starts at a line matching ^#{2,3}\s
  # (## or ###). Content before the first header is the preamble (always kept,
  # even if it alone exceeds budget — better a clipped preamble than nothing).
  awk -v budget="$budget" -v label="$label" -v total="$total_bytes" '
    function flush_section(  i, n, line) {
      # Decide whether the buffered section fits.
      if (sec_header == "" ) {
        # Preamble (text before the first ## header). Emit whole if it fits;
        # otherwise clip at a LINE boundary up to the budget — bloat that lives
        # in the preamble (Folio: a 100KB blob before any header) must still be
        # capped, or truncation does nothing.
        if (running + sec_len <= budget) {
          printf "%s", sec_buf
          running += sec_len
        } else {
          n = split(sec_buf, plines, "\n")
          for (i = 1; i <= n; i++) {
            line = plines[i]
            if (i < n) line = line "\n"   # split drops the trailing \n
            if (running + length(line) > budget) { truncating = 1; preamble_clipped = 1; break }
            printf "%s", line
            running += length(line)
          }
        }
        return
      }
      if (!truncating && running + sec_len <= budget) {
        printf "%s", sec_buf
        running += sec_len
      } else {
        truncating = 1
        skipped[++nskip] = sec_header
      }
    }
    BEGIN { running = 0; truncating = 0; nskip = 0; sec_buf = ""; sec_len = 0; sec_header = "" }
    /^#{2,3}[[:space:]]/ {
      flush_section()
      sec_buf = ""; sec_len = 0
      # capture the header text (strip leading hashes + space)
      h = $0; sub(/^#{2,3}[[:space:]]+/, "", h)
      sec_header = h
    }
    {
      sec_buf = sec_buf $0 "\n"
      sec_len += length($0) + 1
    }
    END {
      flush_section()
      if (truncating) {
        printf "\n> ⚠️ %s truncated at %d KB (file is %d KB) — run /memory-audit to archive.",
               label, budget/1024, int(total/1024 + 0.5)
        if (preamble_clipped) printf " The opening section alone exceeded the budget and was clipped."
        if (nskip > 0) {
          printf " Sections not loaded:"
          for (i = 1; i <= nskip; i++) printf " %s%s", skipped[i], (i < nskip ? ";" : "")
        }
        printf "\n"
      }
    }
  ' "$file" > /tmp/.netdust-budget-$$.txt

  OUTPUT+="$(cat /tmp/.netdust-budget-$$.txt)\n\n"
  rm -f /tmp/.netdust-budget-$$.txt
}

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
  for plugin in netdust-agent netdust-core netdust-wp netdust-statamic; do
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
  # Hard budget: STATE.md is a SNAPSHOT, not an archive. It loads into EVERY
  # session, so bloat costs context tokens on every turn. Enforce a real 32 KB
  # ceiling — load whole sections from the top until the budget is hit, never
  # mid-section, and name what was skipped. (Was: warn-then-load-everything,
  # which let Folio's 175 KB STATE.md inject ~40K tokens per session start.)
  load_with_budget "$STATE" 32768 "STATE.md"
fi

# ── Project lessons ─────────────────────────────────────────────────────────
LESSONS="$CWD/memory/lessons.md"
note lessons "$LESSONS"
if [[ -f "$LESSONS" ]]; then
  OUTPUT+="## Project Lessons\n"
  # Hard budget: 16 KB. Same section-boundary truncation as STATE.md.
  load_with_budget "$LESSONS" 16384 "lessons.md"
fi

# ── Open tasks carried forward ──────────────────────────────────────────────
TODO="$CWD/tasks/todo.md"
note todo "$TODO"
if [[ -f "$TODO" ]]; then
  OUTPUT+="## Open Tasks (carried forward)\n"
  OUTPUT+="$(tail -50 "$TODO")\n\n"
fi

# ── Auto-memory index (Claude Code's atomic per-project memory) ─────────────
# Claude Code keeps an atomic, frontmatter-per-fact memory at
#   ~/.claude/projects/<cwd-with-slashes-as-dashes>/memory/
# with a one-line-per-atom MEMORY.md index. Claude Code loads MEMORY.md itself,
# so this hook does NOT re-dump it (that would double the tokens). What it adds
# is what the built-in load lacks: (1) a recall affordance — the atom files are
# readable on demand, the index is only a table of contents — and (2) a size
# guard. The index loads with a hard ~24 KB ceiling; past it, entries silently
# drop (observed this session). Surface that BEFORE atoms vanish unnoticed.
AUTOMEM_DIR="$HOME/.claude/projects/$(printf '%s' "$CWD" | sed 's#/#-#g')/memory"
AUTOMEM_INDEX="$AUTOMEM_DIR/MEMORY.md"
note automem "$AUTOMEM_INDEX"
if [[ -f "$AUTOMEM_INDEX" ]]; then
  AUTOMEM_BYTES=$(wc -c <"$AUTOMEM_INDEX" 2>/dev/null || echo 0)
  AUTOMEM_COUNT=$(find "$AUTOMEM_DIR" -maxdepth 1 -name '*.md' ! -name 'MEMORY.md' 2>/dev/null | wc -l | tr -d ' ')
  OUTPUT+="## Auto-memory (atomic recall)\n"
  OUTPUT+="$AUTOMEM_COUNT atomic memory files live in \`$AUTOMEM_DIR/\`. The \`MEMORY.md\` index (already in your context) is a table of contents — when an entry looks relevant to the task, **read the linked atom file for the full fact** instead of acting on the one-line summary.\n\n"
  # 24 KB is the index load ceiling (Claude Code loads MEMORY.md itself, so the
  # hook can't truncate it — but it CAN surface when the ceiling is breached so
  # silently-dropped entries don't go unnoticed). Warn at 90% so it's actionable
  # before drop; name the budget explicitly.
  AUTOMEM_BUDGET=24576
  if (( AUTOMEM_BYTES > AUTOMEM_BUDGET * 9 / 10 )); then
    OUTPUT+="> ⚠️ MEMORY.md is $((AUTOMEM_BYTES/1024)) KB vs the 24 KB index ceiling — entries past 24 KB are silently dropped by the loader. Tighten index lines (move detail into atom files, keep each line < ~200 chars) or archive old atoms so recall stays complete.\n\n"
  fi
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

# ── Total-injection report ──────────────────────────────────────────────────
# Make per-session bloat visible: one line with the byte size of everything
# this hook injects. Measured on the EXPANDED output (printf %b resolves the
# \n escapes), so it reflects real injected size, not the escaped source.
if [[ -n "$OUTPUT" ]]; then
  EXPANDED=$(printf -- '%b' "$OUTPUT")
  INJECTED_BYTES=$(printf '%s' "$EXPANDED" | wc -c | tr -d ' ')
  OUTPUT+="---\n_Total injected by session-start: ${INJECTED_BYTES} bytes (~$((INJECTED_BYTES/1024)) KB)._\n"
fi

# ── Output context if we have something ─────────────────────────────────────
if [[ -n "$OUTPUT" ]]; then
  printf -- '---\n# Memory loaded for: %s\n\n' "$CWD"
  printf -- '%b\n---\n' "$OUTPUT"
fi
