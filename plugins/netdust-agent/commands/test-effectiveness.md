---
description: Audit whether a test suite would actually catch bugs (not just pass) and author the tests that close the gap — walks the seven green-but-blind failure modes (stale fixture, test-world≠real-world, wire-mock leak, unmounted guard, missing-denial, no-coverage, concurrency). Sibling to testing-workflow at audit-time/per-phase altitude.
argument-hint: [audit | <bug-that-shipped-green> | path-to-diff]
allowed-tools: Skill(test-effectiveness)
---

Invoke the `test-effectiveness` skill.

- No argument, or `audit`, or a path/range → situation A: run the seven-mode audit over the phase diff (or current branch diff). For every dangerous path — guard, fixture, wire, mount, timer, migration, DOM contract — name the test that goes RED if it breaks, or record it `blind` and fix it. Emit the `covered`/`blind`/`fixed` manifest.
- A description of a bug that shipped while the suite was green → situation B: classify the escape into one of the seven modes, write the RED-first reproducing test, fix, then sweep for siblings of the same mode.

Context / target: $ARGUMENTS
