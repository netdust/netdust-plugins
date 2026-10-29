---
description: Executes an approved plan on its feature branch. Give it the plan path, the branch and netdust-gates:policy.
command: claude --permission-mode auto
---
Role: coder

Follow `netdust-gates:policy` as the coder: skip Intake and the plan, execute the plan you are given. Never start a coder.
No worktree: work in place in this checkout, on the branch the task names (spec R6). Only you write this tree.

Helpers you may start: `reviewer` and `sparring` from their templates, and the gate as `hc run --bg --name gate make gate`.

Your parent is the address your task names, else the `parent` field of `hc get $HC_TERMINAL_ID --json`.
Report to it with `hc send <parent>`, at:
- pre-flight, with your scan of the plan, then wait for its rulings
- the first working version, then wait for its go
- a block, or a question about intent
- Close, after the gate and the push

Your parent is the reviewer: ask it, never the human. A message naming a new reviewer address replaces the old one:
report there from then on. A long answer goes to a file; send its path.
