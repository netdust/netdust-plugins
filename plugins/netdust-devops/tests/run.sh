#!/usr/bin/env bash
# Every netdust-devops test. Contacts no server.
set -uo pipefail
cd "$(dirname "$0")"
RC=0
for t in test-makefile.sh test-work-audit.sh; do
    printf '\n═══ %s ═══\n' "$t"
    bash "$t" || RC=1
done
printf '\n'
[ $RC -eq 0 ] && echo "netdust-devops: all suites passed" || echo "netdust-devops: FAILURES above"
exit $RC
