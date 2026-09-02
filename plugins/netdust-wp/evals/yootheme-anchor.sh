#!/usr/bin/env bash
# yootheme-anchor.sh — the ntdst-yootheme skill must not carry a retired claim.
#
# Each pattern below is a thing the skill used to teach and the fleet retired:
# the theme-level source engine (ntdst-baseline's yootheme module replaced it in
# 2.3.0), ACF as the content model, the container-repeat rule for listings, the
# "a human must save the Customizer" note, the bare-array template claim, and
# the 5.0.38 anchor. Exit 1 on any hit, with a per-pattern count.
set -u
cd "$(dirname "$0")/.."   # plugins/netdust-wp

SCOPE=(skills/ntdst-yootheme skills/ntdst-patterns/golden-paths/yootheme-integration.md)
PATTERNS=(
  'YOOthemeDynamicContentService'
  'attach_post_meta'
  'SourcesService implements'
  '__NAMESPACE__'
  'ACF post type \+ field group'
  'container carries the list query'
  'A human must open the Customizer'
  'Template layouts are BARE ARRAYS'
  'theme 5\.0\.38\)'
  '5\.0\.38 \+ Polylang\)'
  'container carries the list query'
  'carries the list query and repeats'
  '`permalink`'
  '`featured_image`'
)

total=0
for p in "${PATTERNS[@]}"; do
  n=$(grep -rnE -- "$p" "${SCOPE[@]}" 2>/dev/null | grep -v 'evals/' | wc -l)
  if [ "$n" -gt 0 ]; then
    printf '%4d  %s\n' "$n" "$p"
    grep -rnE -- "$p" "${SCOPE[@]}" | head -3 | sed 's/^/        /'
    total=$((total + n))
  fi
done
echo "yootheme-anchor: $total hits"
[ "$total" -eq 0 ]
