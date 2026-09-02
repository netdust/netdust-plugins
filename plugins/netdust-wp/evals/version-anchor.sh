#!/usr/bin/env bash
# version-anchor.sh — the skill's declared anchor against the version that shipped.
#
# retired-symbols.sh proves the DEAD symbols are gone. Nothing proved the skill was
# anchored on the CURRENT release: on 2026-09-02 ntdst-framework declared ntdst-core
# 4.2.0 while the framework shipped 5.2.0, and every WP session read the stale one.
#
# Usage:
#   bash evals/version-anchor.sh                    # resolve packages from ~/Sites
#   NTDST_CORE_DIR=/path bash evals/version-anchor.sh
# Exit 0 = anchors current. Exit 1 = drift. Exit 2 = cannot verify (package absent).
#
# The package version is read from the plugin header FIRST, the newest git tag
# second. Neither source is reliable alone: ntdst-core's 5.x line shipped untagged
# with the truth in the header, and ntdst-baseline is the inverse — tagged v2.3.0
# with no Version: line in the header at all.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2   # plugins/netdust-wp

SKILL="skills/ntdst-framework/SKILL.md"

# package | default source dir | the `**<name>** (X.Y.Z)` line in SKILL.md
PACKAGES=(
  "ntdst-core|${NTDST_CORE_DIR:-$HOME/Sites/ntdst-core}"
  "ntdst-baseline|${NTDST_BASELINE_DIR:-$HOME/Sites/ntdst-baseline}"
)

header_version() {
  grep -m1 -oE '^[[:space:]]*\*?[[:space:]]*Version:[[:space:]]*[0-9]+\.[0-9]+\.[0-9]+' "$1" 2>/dev/null \
    | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'
}

tag_version() {
  git -C "$1" tag --sort=-v:refname 2>/dev/null \
    | grep -m1 -oE '[0-9]+\.[0-9]+\.[0-9]+'
}

shipped_version() {
  local dir="$1" name="$2" v
  v="$(header_version "$dir/$name.php")"
  [ -n "$v" ] || v="$(tag_version "$dir")"
  printf '%s' "$v"
}

claimed_version() {
  grep -m1 -oE "\*\*$1\*\* \([0-9]+\.[0-9]+\.[0-9]+\)" "$SKILL" 2>/dev/null \
    | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'
}

hits=0
unverifiable=0
for entry in "${PACKAGES[@]}"; do
  name="${entry%%|*}"
  dir="${entry##*|}"

  claimed="$(claimed_version "$name")"
  if [ -z "$claimed" ]; then
    echo "$SKILL: no '**$name** (X.Y.Z)' anchor line found" >&2
    hits=$((hits + 1))
    continue
  fi

  shipped="$(shipped_version "$dir" "$name")"
  if [ -z "$shipped" ]; then
    echo "$name: no Version: header in $dir/$name.php and no version tag — not checked" >&2
    unverifiable=$((unverifiable + 1))
    continue
  fi

  if [ "$claimed" != "$shipped" ]; then
    line="$(grep -n -m1 -E "\*\*$name\*\* \([0-9]" "$SKILL" | cut -d: -f1)"
    echo "$SKILL:${line}: anchors $name $claimed, but $name ships $shipped"
    hits=$((hits + 1))
  fi
done

if [ "$hits" -gt 0 ]; then
  echo "--- $hits stale anchor(s). Re-anchor the skill on what shipped, or correct the claim." >&2
  exit 1
fi
[ "$unverifiable" -gt 0 ] && exit 2
echo "version-anchor: clean (${#PACKAGES[@]} package(s) checked)"
exit 0
