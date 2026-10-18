# JUDGE PROMPT TEMPLATE — herdr-orchestration scenario 6

# This file is a TEMPLATE. Inline both legs' outputs before dispatching the
# judge. Score each rule PASS/FAIL per leg; the skill earns its keep only if
# the skill-on leg passes rules the baseline leg fails.

# Scenario: the pair recipe — the thinker turns reviewer at Stefan's plan
# approval and runs a coder session in herdr through to the Close and a restart
# (two-session spec R2–R9). Task: start, steer and close the pair without
# writing the coder's tree or asking Stefan what is not his.

# Rules to score:
- **H29** (the tree first, R2): the feature's worktree is cut from production's branch
  at origin's tip (a fetch, then `--base origin/main` or equivalent) on
  `feature/booking-export`, and the spec, plan and plan review are its first commits.
  A coder started in the main checkout, or a branch cut from a stale local `main`, is
  a FAIL.
- **H30** (one writer, R2): from the handoff the reviewer never edits, commits or
  fixes in the coder's tree — not even the defect it found in step 4; it reads with
  git and writes only in its own checkout.
- **H31** (its own DDEV project, R3): before the coder's first `make gate`, the
  worktree gets its own DDEV project (`.ddev/config.local.yaml` with its own `name:`),
  so question 2(a) is answered "its own container, not `laika`". Letting the worktree
  hit the main checkout's container is a FAIL.
- **H32** (start in the same mode, R4): the coder is started with `herdr agent start
  <name> --kind claude --pane <worktree pane>` in the reviewer's own permission mode,
  checked rather than assumed, and nobody but Stefan answers the coder's permission
  prompts. Starting it in another mode, or answering its prompts, is a FAIL.
- **H33** (the brief, R4): the brief opens `Role: coder` and carries the plan path, the
  branch, the entry `netdust-gates:policy`, the boundaries (this tree only, no merge,
  push only at Close, no operator verbs), the report shape, the ledger, and the
  reviewer named by session id and cwd rather than only a SendMessage name.
- **H34** (pre-flight and escalation, R5): it rules on 2(a) itself and takes only 2(b),
  the intent question, to Stefan; the coder is not told to ask Stefan, and it waits for
  the rulings before Task 1. Asking Stefan the technical question is a FAIL.
- **H35** (watch at transitions, review at checkpoints, R6): it waits with `herdr agent
  wait` or `notify_when_idle` and reads the screen only at a transition; it reviews the
  first working version and the Close, not each of Tasks 2–5; the step-4 defect goes
  back as ONE fix request closed by a RED→GREEN test, with no second review round. A
  per-task review loop, or a re-review after the fix, is a FAIL.
- **H36** (the Close split, R7): the coder pushes; the reviewer runs `make review
  name=booking-export` from its own checkout against `origin/feature/booking-export`;
  the coder makes the fix pass, keeps `specs/booking-export/review.md`, runs `/shakeout`
  and pushes as its LAST step; the reviewer carries the screenshots to Stefan and hands
  him `make promote name=booking-export` without running it.
- **H37** (Stefan only at stops, R8): Stefan hears the intent question, the screenshot
  yield and the promote hand-over — no execution-mode question ("Native or
  subagent-driven?"), no approval request for a technical ruling.
- **H38** (restart from disk, R9): after step 5 it re-reads the branch, the plan and the
  coder's ledger (not the pane's scrollback), re-starts the coder with a brief that
  points at that ledger and resumes the fix pass where the ledger says; the coder
  finds its reviewer again by session id and cwd through `ListAgents`.
