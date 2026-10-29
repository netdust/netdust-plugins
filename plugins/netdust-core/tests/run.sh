#!/usr/bin/env bash
# Every netdust-core test. Each hc test runs its own scratch core, never the default one.
set -uo pipefail
cd "$(dirname "$0")"
RC=0
for t in test-*.sh; do
    printf '\n═══ %s ═══\n' "$t"
    bash "$t" || RC=1
done
printf '\n'
[ $RC -eq 0 ] && echo "netdust-core: all suites passed" || echo "netdust-core: FAILURES above"
exit $RC
