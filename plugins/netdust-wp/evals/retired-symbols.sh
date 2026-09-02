#!/usr/bin/env bash
# retired-symbols.sh — the machine half of the ntdst-core 5.0.0 re-anchor.
#
# A skill is only re-anchored when the DEAD SYMBOLS ARE GONE FROM WHAT IT TEACHES.
# Prose can say "ntdst_actions() is retired" in one section and still hand a
# session `ntdst_actions()` in an example three sections later; the eval cases
# catch that qualitatively, this catches it mechanically.
#
# Usage:
#   bash evals/retired-symbols.sh              # every *.md / *.json under plugins/netdust-wp
#   bash evals/retired-symbols.sh FILE...      # only the named files (symbol scan only)
# Exit 0 = clean. Exit 1 = hits, printed one per line as `path:line: symbol`.
#
# WHAT IS NOT SCANNED, and why:
#   - anything between a `^## Retired` heading and the next `^## ` heading. That
#     block's JOB is to name the dead symbols. Lines are BLANKED, not deleted, so
#     the line numbers we print stay the real ones.
#   - `*lessons.md` — a lesson file records what went wrong, quoting the symbol.
#   - everything under `evals/` — the cases quote dead symbols as must_not_contain.
#   - the ALLOW list below: a per-file, per-symbol exemption with a written reason.
#     Each entry is a claim that the mention is a WARNING or a foreign vocabulary,
#     never a use. Adding one is a decision; read the line before you copy it.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2   # plugins/netdust-wp

# The 24 entries are the plan's Interfaces block, verbatim. Substring match by
# design: `ntdst_service_` catches `ntdst_service_{slug}_enabled` and its option
# sibling; `ntdst_model_` catches all six renamed lifecycle hooks.
RETIRED=(
  'ntdst/api_data' 'ntdstAPI' 'ntdst_actions' 'get_nonce'
  'public_fields' 'publicRows' 'getFormattedPosts' 'ntdst_get_formatted_posts'
  'sectors' 'ntdst_service_' 'auto_discover' 'discovery_paths'
  'apiSuccess' 'apiError' '->json(' '->render('
  'ntdst_redirect' 'ntdst_mail' 'ntdst_schedule_recurring' 'ntdst_notify'
  'ntdst_model_' 'mixin(' 'signed_int' 'wysiwyg'
)

# path-glob | symbol | reason
ALLOW=(
  './agents/ntdst-drift-reviewer.md|ntdst_actions|the reviewer GREPS FOR this symbol on a consumer, and names it as retired+fatal; a drift reviewer that cannot spell the drift is useless'
  './skills/ntdst-framework/references/traps.md|ntdst_service_|trap line: the retired ntdst_service_{slug}_enabled filter FAILED OPEN — naming it is the warning'
  './skills/ntdst-framework/references/traps.md|ntdst_model_|trap line: a listener on the renamed hook is silently inert — naming the old spelling is the warning'
  './skills/ntdst-yootheme/*|wysiwyg|YOOtheme/ACF vocabulary, not the NTDST field vocabulary; `wysiwyg` is a live ACF type name'
  './skills/ntdst-framework/references/baseline.md|ntdst/api_data|baseline 2.1.0 MOVED its manual purge door off this action onto a route; naming the door it left is the warning, and ntdst-baseline own README still documents the old one'
)

allowed() {  # $1 = path, $2 = symbol
  local e glob sym
  for e in "${ALLOW[@]}"; do
    glob="${e%%|*}"; sym="${e#*|}"; sym="${sym%%|*}"
    [ "$sym" = "$2" ] || continue
    # shellcheck disable=SC2254
    case "$1" in $glob) return 0 ;; esac
  done
  return 1
}

STRUCTURAL=1
if [ $# -gt 0 ]; then
  FILES=("$@"); STRUCTURAL=0        # explicit targets: scan exactly what was named
else
  mapfile -t FILES < <(find . -type f \( -name '*.md' -o -name '*.json' \) \
                         ! -path './evals/*' ! -name '*lessons.md' | sort)
fi

hits=0
strip="$(mktemp)"; trap 'rm -f "$strip"' EXIT

for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "$f: no such file" >&2; hits=$((hits+1)); continue; }
  # Blank the `## Retired` block; keep every other line at its own number.
  awk '/^## Retired/{r=1} r&&/^## /&&!/^## Retired/{r=0} {print (r ? "" : $0)}' "$f" > "$strip"
  for s in "${RETIRED[@]}"; do
    allowed "$f" "$s" && continue
    while IFS= read -r line; do
      echo "$f:${line%%:*}: $s"
      hits=$((hits+1))
    done < <(grep -nF -- "$s" "$strip")
  done
done

# --- Golden-path structural check (Cluster A gate ruling) -------------------
# A field declaring `show_in_rest` publishes NOTHING unless the TYPE is in REST
# too — WordPress mounts no /wp/v2 route at all. A golden path that shows the
# field flags without the type-level flag teaches a shape that silently fails.
#
# Scoped PER REGISTER BLOCK, never a flat file grep: a flat grep sees the two
# flags anywhere in the file and calls it clean. The block runs from
# `ntdst_data()->register(` to the CLOSING FENCE of its code block, not to the
# `]);` the gate ruling first proposed — content-type-feature.md puts its fields
# in a `getFields()` method AFTER that `]);`, so a `]);` terminator ends the
# block before a single field is seen and the check passes vacuously.
# Inside the block: everything before the `fields` key is the TYPE's args,
# everything after is the field schema.
#
# Two things this got wrong on the first pass, both proven by mutation:
#   - a block may only OPEN INSIDE A CODE FENCE. `content-type-feature.md` names
#     `ntdst_data()->register()` in a prose table 28 lines above the real call.
#   - a mention is not a declaration. Matching the bare word `show_in_rest` let
#     the COMMENT above the flag ("// show_in_rest opens /wp/v2/...") stand in
#     for the flag itself, so deleting the real line still read as present. Only
#     `'show_in_rest' => true` — quoted key, fat arrow, true — counts.
if [ "$STRUCTURAL" = 1 ]; then
  while IFS= read -r gp; do
    bad="$(awk -v F="$gp" '
      /^[[:space:]]*```/ {
        if (inb) {
          if (fieldlvl && !typelvl)
            printf "%s:%d: register() block declares field-level '\''show_in_rest'\'' => true with no type-level '\''show_in_rest'\'' => true — WordPress mounts no /wp/v2 route and every field flag publishes nothing\n", F, start
          inb=0
        }
        infence = !infence
        next
      }
      infence && !inb && /ntdst_data\(\)->register\(/ { inb=1; infields=0; typelvl=0; fieldlvl=0; start=NR; next }
      inb && (/'\''fields'\''[[:space:]]*=>/ || /function[[:space:]]+getFields/) { infields=1 }
      inb && /'\''show_in_rest'\''[[:space:]]*=>[[:space:]]*true/ { if (infields) fieldlvl=1; else typelvl=1 }
    ' "$gp")"
    if [ -n "$bad" ]; then echo "$bad"; hits=$((hits+1)); fi
  done < <(find ./skills -path '*/golden-paths/*.md' -type f | sort)
fi

if [ "$hits" -gt 0 ]; then
  echo "--- $hits retired-symbol hit(s). Each line is a symbol ntdst-core 5.0.0 does not have." >&2
  exit 1
fi
echo "retired-symbols: clean (${#FILES[@]} file(s) scanned)"
exit 0
