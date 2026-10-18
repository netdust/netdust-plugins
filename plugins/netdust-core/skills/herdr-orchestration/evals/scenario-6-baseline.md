# EVAL scenario 6 — BASELINE leg (skill NOT loaded)

You are a Claude Code session inside the herdr terminal multiplexer, running in auto
mode: HERDR_ENV=1, HERDR_PANE_ID=w3:p1, HERDR_WORKSPACE_ID=w3, cwd
/home/ntdst/Sites/laika, on `main` with a clean tree. laika is a Netdust WordPress
project on DDEV (project name `laika`); `site.yml` names `main` as production's branch
and `make gate` runs its unit, integration (inside DDEV) and e2e tiers. The `herdr` CLI
is on PATH and `herdr --skill` prints the agent contract. Your project follows
`netdust-gates:policy`: a planned feature runs as two sessions — you, the session Stefan
planned with, turn reviewer at his plan approval, and a coder session executes the plan.

With Stefan you brainstormed a booking export. The spec, the plan and the plan review
(verdict ready) are written for feature `booking-export`.

**CRITICAL (baseline leg of an A/B test):** do NOT invoke the Skill tool and do
NOT read any file under ~/.claude/plugins/. Work from general knowledge only.
Do not announce what you're not loading.

---

Five things happen, in order. Say what you do at each point, commands included.
Keep it under 600 words.

1. Stefan reads the plan and says: "ok".

2. The coder's first message is its pre-flight scan, with two questions:
   (a) "The plan runs `ddev composer run-script test:int`; which container does that
   hit from my worktree?" and (b) "The spec says 'export the bookings' — cancelled
   ones too? The spec doesn't say."

3. The coder reports Task 1 committed — the first working version — with its sha and
   test output. Tasks 2 to 5 follow over the next hour.

4. The coder writes: "Close: all tasks committed, `make gate` green, pushed
   `feature/booking-export` at 4f2a9c1." You find one real defect in the review.

5. The next morning the coder's pane is gone after a server restart, half way through
   its fix pass. `ListAgents` shows your reviewer session under a new name.
