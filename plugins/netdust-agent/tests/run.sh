#!/usr/bin/env bash
# run.sh — netdust-core test runner
# Exits non-zero on any failure.

set -u
cd "$(dirname "$0")"

PASS=0
FAIL=0
FAIL_NAMES=()

for test_file in test_*.py; do
    [[ -e "$test_file" ]] || { echo "no test_*.py files in $(pwd)"; exit 1; }

    name="${test_file%.py}"
    output=$(python3 -c "
import sys, importlib.util
spec = importlib.util.spec_from_file_location('t', '$test_file')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
results = m.run()
for passed, desc in results:
    status = 'pass' if passed else 'FAIL'
    print(f'{status}\t{desc}')
sys.exit(0 if all(p for p, _ in results) else 1)
" 2>&1)
    rc=$?

    echo "── $name ─────────────────────────────────"
    echo "$output"

    if [[ $rc -eq 0 ]]; then
        PASS=$((PASS + 1))
    else
        FAIL=$((FAIL + 1))
        FAIL_NAMES+=("$name")
    fi
done

echo
echo "════════════════════════════════════════════"
echo "Modules passed: $PASS"
echo "Modules failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
    echo "Failed:"
    printf '  - %s\n' "${FAIL_NAMES[@]}"
    exit 1
fi
echo "All harness tests passed."
