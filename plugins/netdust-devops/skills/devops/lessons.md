# Lessons — devops

Append-only. After any correction, the rule that prevents the repeat.

## A recipe comment is still shell

A `: "..."` line in a Makefile recipe is still a shell command. A backtick
inside it is command substitution, not punctuation — a comment mentioning the
verb it documented re-invoked make and recursed until the process table gave
out (make[90], no output, hangs on parse).
Recipe comments use single quotes and no backticks. `tests/test-makefile.sh`
asserts no recipe line contains one (2026-09-04).

## The terminal check goes first, not last

`make ship` originally checked for a terminal inside `_deploy-confirm`, after
the gate and both backups. A piped ship therefore took a production database
dump and a payload tarball before discovering it could never read the
confirmation. Any check that can refuse the whole verb belongs before the
first step that touches a server (2026-09-04).
