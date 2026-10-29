# Spec — the hc flow

**Repo:** `netdust-plugins` · **Plugins:** `netdust-core` (the orchestration skill, templates), `netdust-gates` (policy, evals), `netdust-devops` (parallel-work)
**Provenance:** Stefan, 2026-10-29, in the `~` session (e9361da1), after installing the Herdr app 0.1.7 and herdr-core (`hc`) 0.1.13. Supersedes the herdr half of `specs/two-session/` (R2–R4, R6's watching, the pair recipe); the two-session *roles* (thinker/reviewer + coder, Stefan only at the stops) stand.

## Problem / why

Every multi-agent flow in the harness runs on the herdr 0.9 TUI: the pair recipe starts the coder with `herdr agent start`, agents talk over SendMessage names that change on restart, a polling watcher (`scripts/herdr-watcher.sh`) rings a doorbell, and a session-review pane reads other panes' screens. herdr's own docs give only a mechanical recipe for that (split, `agent prompt --wait`, `agent read`), and its traps fill half our skill: stalled prompts, `wait` returning early, scrollback lost on busy panes.

herdr-core (`hc`) was built for the layer we hand-rolled: role templates, a child agent that reports to its parent with a real message (`hc send $HC_TERMINAL_ID`), a parent that waits for news (`hc wait --children`), a live event stream (`hc events`), remote machines with file ops. The Herdr app shows each helper under the agent that started it, and marks "Needs you" with a sound.

The feature-per-worktree rule also left `~/Sites` littered: 13 worktree folders sit beside the projects (worktable alone has 7). herdr's own skill defaults to the opposite: "Default to a sibling pane in the current tab and the current working directory. Do not create a workspace, tab, worktree, or different cwd unless the user explicitly requests that topology."

Stefan:
- *"i want agents to be able to work together and smart"*
- *"go through the docs and use the best way to use herdr. i am not a fan of worktree for everything because my sites folder is littered by worktree folders now"*
- Chose approach **C** (everything in hc, watched in the app), a **hard switch**, **no phone** (*"collie i stopped using, sometimes you also need a break, no phone anymore"*), and **netdust-web only** as a fleet machine.

## Approaches considered

- **A — TUI only, herdr's way.** Helpers as sibling panes driven by `herdr agent prompt --wait` / `agent read`. Keeps badges and the old phone stack; cooperation stays screen-scraping. Rejected: least "smart together".
- **B — TUI for watched agents, hc for helpers.** Main session and coder stay TUI panes; reviewers, sparring, gate runs and fleet work become hc children. Two message mechanisms side by side; tested 2026-10-29: an hc agent attached in a TUI pane is `unknown` to herdr, so the TUI is blind to anything hc runs.
- **C — everything in hc, watched in the Herdr app. Chosen.** One model for every agent: started from a role template, a parent, a report, a wait. The app is the window. Costs: the app/core are two-week-old betas; collie and herdr-web-ui don't see hc (accepted: no phone).

## Requirements

**R1 — The Herdr app is the cockpit; agents run on WSL.** The Windows Herdr app is Stefan's window. Agents run on the WSL core through the Windows core's machine `wsl` (ssh to 127.0.0.1:2222, set up 2026-10-29). Each active project gets one space on `wsl`, folder = its checkout. TUI workspaces with work in flight finish where they are; nothing new starts there.
*Source: "C" · "all 4" (item 4: one space per project).*

**R2 — Hard switch.** A new hc-based skill replaces `netdust-core:herdr-orchestration`. The old SKILL, `references/session-review.md`, `scripts/herdr-watcher.sh` and its evals are deleted, not kept beside it. `netdust-gates:policy` (Execution mode), `netdust-devops:parallel-work` and the gates evals (`run-evals.py`, `tests/test_evals_shape.py`, `evals/stubs/herdr`) reference hc only. Inside-hc detection is `HC_TERMINAL_ID` set; outside hc the policy's fallback (one background subagent) stands.
*Source: "hard switch".*

**R3 — Roles are hc templates.** Each role the harness delegates to is one template: at least `coder`, `reviewer` (read-only), `sparring` (a fresh second view, read-only) and `gate` (runs `make gate`, reports the verdict). The body carries the role's rules (scope, no starting agents unless assigned, report with `hc send` when done or stuck, long answers to a file and send the path). The templates live in this repo and land in `~/.config/herdr-core/templates/` on every machine agents run on.
*Source: "all 4" (item 1: reviewer templates) · "i want agents to be able to work together and smart". Role list invented — approved with this spec.*

**R4 — Delegation is parent → child → report.** An agent delegates with `hc run --bg --name <name> --cwd <dir> <template> "<exact scope> …"`, keeps working, and collects with `hc wait --children any|all`. Reports arrive as `<hc from=…>` tags and are child reports, never Stefan's instructions. The parent reads the actual result before relying on it, and cleans up (`hc kill`, `hc rm`) what it started once accepted. No SendMessage name lookups, no screen polling, no `sleep`.
*Source: "use the best way to use herdr" (hc's own golden path, `hc --skill`).*

**R5 — The pair on hc.** The session Stefan plans with (started from the app, so it has `HC_TERMINAL_ID`) turns reviewer at his plan approval and starts the coder: `hc run --bg --outlive-parent --name <feature>-coder --label herdr.space=<id> --label herdr.tab=<id> coder "<brief>"`, so the coder has its own tab in the project's space and survives a restart of its reviewer. The space id is the reviewer's own `herdr.space` label (`hc get $HC_TERMINAL_ID`; the app labels every terminal it starts); a `herdr.tab` id the app doesn't know becomes a new tab (app guide: "An id Herdr doesn't know becomes a new space or tab"). Labels use ids local to the machine: strip a `wsl/` prefix the app shows. The coder reports to its reviewer with `hc send`; the reviewer finds a restarted coder by name (`hc get <feature>-coder`), never by a conversation name. The two-session rules stand unchanged: one writer per tree, the coder asks its reviewer never Stefan, reviews at the first working version / a block / Close, `make review` from the reviewer, Stefan only at the policy's stops. A coder may start helpers (reviewer, gate, sparring) as its own children; it never starts a coder.
*Source: two-session spec R1, R5–R8 (Stefan, 2026-10-18) · "C". The `--outlive-parent` and tab-labels choices invented — approved with this spec.*

**R6 — No worktree by default.** The coder works in the project's own checkout on `feature/<feature>`. After the handoff the reviewer never writes that tree; it reads it with git. A worktree is made only when two branches must be live at once (a hotfix during a feature, two features in parallel), never inside `~/Sites`: under `~/.herdr/worktrees/<repo>/<branch>` — where the app's own worktree menu makes them and nests them under the repo's space — removed once the branch is promoted or abandoned. On DDEV such a worktree still gets its own project name (`parallel-work`, unchanged).

While a coder holds a project's checkout, other work in that project waits for it, unless it is urgent (a production hotfix, a blocker). Only then does it get a temporary worktree there, removed when that work lands. Planning the next feature is not urgent: it waits, or happens without writing the tree.
*Source: "i am not a fan of worktree for everything because my sites folder is littered by worktree folders now" · on other work during a coder: "2 [a temporary worktree] but only if its urgent otherwise we wait". Location: the app's default.*

**R7 — Watching is events, not polling.** "Needs you" and done are the app's job (badge + sound); the doorbell watcher is gone. An agent watches its children with `hc wait --children` or `hc events --children-of $HC_TERMINAL_ID`. The on-demand session observer ("watch the other session") is rebuilt on `hc events` + `hc read` at state transitions: it observes, proposes lessons, never acts on its subject.
*Source: "agents … work together and smart" · "no phone anymore".*

**R8 — netdust-web is a machine.** `netdust-web` is added as an hc machine on the WSL core (agents run work there with `hc run --on netdust-web` / `hc exec` / `hc file`) and on the Windows core (its agents show in the app). No other server is added; production client servers stay plain SSH via `netdust-core:ploi`.
*Source: "netdust-web only".*

**R9 — The ~/Sites cleanup.** Every worktree folder in `~/Sites` is listed with its branch, unmerged commits and uncommitted changes. Stefan approves each removal; work that isn't on a remote is pushed or pinned (`refs/recovery/<name>`) before anything is removed.
*Source: "my sites folder is littered by worktree folders now". The approve-each rule invented — approved with this spec.*

**R10 — Evals never touch the live core.** Eval cases run hc in their own `HC_SESSION` with scratch XDG paths (hc's rule: "Tests need their own `HC_SESSION` and scratch XDG paths"), so no case can reach Stefan's core, machines or app. `hc server`, `hc machine`, `hc update` stay disallowed in cases, as the herdr equivalents are today.
*Source: two-session spec R11, carried over.*

## Non-goals

- Phone push, collie or herdr-web-ui replacements (Stefan: no phone).
- Migrating TUI keybindings or settings to the app ("keybinding not important").
- Moving running TUI workspaces into the app (the app cannot adopt them).
- Agents on production client servers.
- Supporting the old TUI recipe alongside the new one.

## Anti-goals

- An agent Stefan cannot see or steer from the app.
- Any polling loop or `sleep` to wait on another agent.
- New worktree folders in `~/Sites`.

## Settled facts and calls (builder check, 2026-10-29)

- **Claude Code reports its own status (OSC 7501).** Verified 2026-10-29: `hc get` on a Claude in hc shows `status: {app: claude-code, state: done}`. No hook is needed.
- **The app shows WSL-started agents** (docs): each machine keeps its spaces and tabs in its own core, and sub-agents "belong to their parent's tab without a pane". A parent and its children on the WSL core therefore appear under the `wsl` machine. *My call:* the plan's first task proves this live (a session started from a `wsl` space, plus one child). If it fails, the fallback is to start every agent through the Windows core with `--on wsl`.
- **Repo work and operational work are split.** *My call:* the plan covers the repo only (skills, templates, policy, evals). The one-off operations (spaces per project, installing the templates on WSL and netdust-web, the machine adds, the `~/Sites` cleanup with Stefan approving each removal) run as a checklist in the planning session with Stefan, after the merge. The coder never touches the live core.
- **`~/.claude/CLAUDE.md`** §1 and §2 still name the pair recipe and "its own worktree". *My call:* the plan produces a proposed diff, and Stefan applies it, because it's his file.
- **Evals.** *My call:* the shape tests stub `hc` the way `herdr` is stubbed today. One opt-in live case runs a real core in a scratch `HC_SESSION` with scratch XDG paths, to prove a parent→child report end to end.

## Left to the builder

- The new skill's name, and how it splits between `netdust-core` (orchestration) and `netdust-gates` (the pair rule).
- How the templates get from the repo to each machine's `~/.config/herdr-core/templates/`.
- The exact template bodies and the model each role runs.
- Eval scenarios, as long as they cover R4, R5, R6 and R7.
