#!/usr/bin/env bash
# Every netdust-wp test. No WordPress, no network.
set -uo pipefail
cd "$(dirname "$0")" || exit 1
RC=0
for t in yootheme/run.sh test-upstream-skills.sh; do
    printf '\n═══ %s ═══\n' "$t"
    bash "$t" || RC=1
done
printf '\n'
[ $RC -eq 0 ] && echo "netdust-wp: all suites passed" || echo "netdust-wp: FAILURES above"
exit $RC
