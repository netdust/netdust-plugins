# Spec — two sessions

**Repo:** `netdust-plugins` · **Plugins:** `netdust-gates` (rule), `netdust-core` (herdr-orchestration recipe), `netdust-devops` (parallel-work)
**Provenance:** Stefan, 2026-10-18, in the laika session (844fb4e7), during the presskit close and the framework test programme. Designed by sparring with a fresh agent, at his request; the notes are that session's `scratchpad/two-session/spar-1.md`.

## Problem / why

A netdust-gates feature runs in one session today. That session brainstorms, writes the spec and the plan, codes every task, reviews through subagents, and asks Stefan to choose an execution mode at the plan handoff. The session that wrote the code is also the one judging whether the code matches the plan. Stefan answers technical questions he says he cannot judge. And the session stops at a stop the gates already make unnecessary.

Stefan:
- *"in fact, with netdust-gates i always want you to work like this. 2 sessions, talking, brainstorming, 1 does watching, reviewing, 1 session does the coding. netdust-gates is there to make sure quality of code and coding architecture is kept, there are human gates ( the plan ) and testing gates so you should be able to do it on your own if the plan os solid"*
- *"this has to be a rule in netdust-gates yes. i want this for all projects. 2 panes talking to eachoter doing the work, involving me only when needed"*
- *"I don't know enough of this myself, if you have questions or need feedback use a agent to spar and brainstorm with"*

## Requirements

**R1 — A planned feature runs as two sessions.** The session Stefan talked to keeps the thinking: Intake, spec, plan and `/plan-review`. After his plan approval it turns reviewer, and a second session, the coder, executes the plan. A change with no plan file (the bounded path's chat design) stays in one session.
*Source: "2 sessions, talking, brainstorming, 1 does watching, reviewing, 1 session does the coding" · "i want this for all projects".*

**R2 — One writer per tree.** The spec, plan and plan review are the first commits of `feature/<feature>`, in the coder's own git worktree cut from production's branch. From the handoff, only the coder writes the feature's tree. The reviewer reads that tree, and writes only in its own checkout.
*Source: Stefan, 2026-10-18, asked "Is a worktree per feature, with its own DDEV project, OK now?": "Yes, worktree per feature (Recommended)".*

**R3 — On a DDEV project the coder's worktree is its own DDEV project.** A `.ddev/config.local.yaml` gives it its own project name, so its `make gate` and `make e2e` run against its own code, never the main checkout's container. Documented once, in `netdust-devops:parallel-work`. laika-planning-model's `name: laika-planning` is the proven form.
*Source: the same answer ("with its own DDEV name"). The defect it prevents: laika's `bin/gate.sh` runs `ddev composer run-script test:int`, which lands in whichever container carries the project's name.*

**R4 — Starting the coder.**
- **Inside herdr** (`HERDR_ENV=1`): the coder is a full session in a herdr pane, started by the pair recipe in `netdust-core:herdr-orchestration`.
- **Outside herdr:** the coder is one background subagent running Native in the worktree, continued over SendMessage.
- **The brief** opens with `Role: coder`. A coder skips Intake and the plan, and never starts a coder.
- **Same permission mode:** both sessions run in the same mode, so a message between them is never held for Stefan's approval.
*Source: "2 panes talking to eachoter" — invented in the details (the role line, the fallback, the same mode); approved with this spec.*

**R5 — The two sessions talk; Stefan is involved only at the stops.**
- **Pre-flight:** the coder sends its pre-flight scan of the plan, and the reviewer rules before Task 1.
- **Escalation:** a technical question the coder cannot settle goes to the reviewer, who rules, sparring with a fresh agent when it needs a second view. An intent question goes to Stefan, since a `Source:` line needs his words.
- **A coder asks its reviewer, never Stefan.**
*Source: "talking, brainstorming" · "involving me only when needed" · "if you have questions or need feedback use a agent to spar and brainstorm with".*

**R6 — The review cadence.**
- **When the reviewer reads the coder's work:** at the first working version, at a block or an intent question, and at Close (`make review name=<feature>`), not after every task. Inside the coder, subagent-driven's own task reviews stand when that mode's rule fires; the reviewer does not stack a third review on them.
- **A finding is one fix request, closed by its test.** There are no review rounds.
- **Watching** means `herdr agent wait` / `notify_when_idle`, reading the coder's screen only at a transition. It is not the session-review pane, which stays a separate, on-demand observer.
*Source: "1 does watching, reviewing" — the cadence is invented, against the per-task review loop Stefan called endless; approved with this spec.*

**R7 — The Close, split by who writes.**
- **The coder:** every step that writes the tree. That covers the tasks, `make gate`, the fix pass, `/shakeout` and the push.
- **The reviewer:** `make review name=<feature>` from its own checkout (it resolves `origin/feature/<feature>`). It also carries the screenshot yield to Stefan and hands him `make promote`.
*Source: "there are human gates ( the plan ) and testing gates so you should be able to do it on your own".*

**R8 — Stefan's moments.** These stops stand, and only these:
- the plan approval;
- the shake-out screenshot yield;
- the flow list for a spec-less branch;
- every operator verb (`promote`, `unpromote`, `ship`, deploy, and pushing a package's `main`);
- upstream's four stops;
- a review finding that is an intent decision;
- the coder's permission prompts, which nobody answers for him.

The execution-mode choice is no longer a stop. Inside the coder, Native is the default, and subagent-driven applies only for a security-boundary unit or a plan that outlives one context.
*Source: "involving me only when needed" · "you should be able to do it on your own if the plan os solid".*

**R9 — Either session is replaceable from disk.** The coder's ledger records every exchange with the reviewer: brief, rulings, fix requests and their closing tests. A restart of either session re-reads the branch, the plan and that ledger, never a pane's scrollback.
*Source: invented — herdr's own rule ("a dispatch's durable artifact is the branch, never the pane"); approved with this spec.*

**R10 — The boundary stays honest.** netdust-gates' `CLAUDE.md` says why a coder session is not the implementer/reviewer agents it bans: a coder session is a topology. It runs upstream's executor unchanged, and gates ships no implementer prompt, no reviewer rubric and no review rounds.
*Source: the plugin's own boundary ("Not here, and not to be re-added: … implementer / test-author / reviewer agents").*

**R11 — Evals that cannot drive the live herdr server.**
- **The runner:** `run-evals.py` strips `HERDR_*` from every case. It accepts a per-case `env`, a `stub_bin` put first on `PATH`, and `commit: true`, which makes a first commit so a worktree can exist.
- **Case `two-session-handoff`:** an approved one-task plan with `HERDR_ENV=1` and a stub `herdr`. It expects:
  - an `agent start` and a prompt carrying `Role: coder`, the plan path and `netdust-gates:policy`;
  - the target file unchanged;
  - no execution-mode question.
- **Case `coder-brief-no-recursion`:** a prompt opening `Role: coder`. It expects the target changed and no `agent start`.
- **herdr-orchestration** gets a judged paper scenario for the recipe in its own eval format.
*Source: invented — the sandbox inherits the caller's environment, and this pane runs `HERDR_ENV=1`; approved with this spec.*

**R12 — Stefan's global instructions follow.** His `~/.claude/CLAUDE.md` §2 line "I choose the execution mode at the plan handoff…" is replaced by the two-session sentence. The replacement text goes to Stefan to apply; the file is his.
*Source: "i want this for all projects".*

## Out of scope

- A machine-wide `flock` on the heavy test tiers in wp-starter's `gate/`, so pairs and other projects stop booking the box by message. Follow-up.
- `make feature name=x worktree=<path>` in netdust-devops. Follow-up. Until it lands, the brief names the base: production's branch at origin's tip.
- The session-review pane (herdr-orchestration's observer role). It is unchanged and stays on demand.

## Pilot

This change is the first pair, on netdust-plugins, which has no DDEV. The WordPress rollout rides on R3 and R11, both inside this change.
