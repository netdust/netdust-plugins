---
name: hc-orchestration
description: "Use when work involves more than one agent and herdr-core (`hc`) is installed — running a planned feature as two sessions (the pair: reviewer and coder), delegating a review, a second opinion or a gate run to a helper, watching children or another session, urgent work while a coder holds the checkout, or work on the netdust-web machine. Inside hc when HC_TERMINAL_ID is set. Triggers on keywords hc, herdr-core, Herdr app, hc run, hc wait, hc send, hc events, template, coder, reviewer, sparring, helper, child agent, sub-agent, parent, outlive-parent, space, tab, Needs you, watch the other session, keep an eye on the main agent, worktree, hotfix during a feature, machine, netdust-web, --on. Symptoms include the operator approving a plan, a review that must not share the author's context, a second agent about to edit the same directory, an agent about to call hc with no core running, or an urge to poll or sleep while another agent works. `hc --skill` and `herdr-app --skill` are the syntax authorities; this skill carries only the netdust decisions on top."
---

# hc orchestration — the netdust decisions

`hc --skill` is the authority for agents, children, reports and waits; `herdr-app --skill`
(Windows) for spaces and tabs; `hc <verb> --help` for flags. Never work from remembered
syntax and never restate it here.

Inside hc: `HC_TERMINAL_ID` is set; it is your address. Outside hc, the policy's fallback
stands (one background subagent), and the first rule below decides whether you may call `hc`.

## The core is never yours to start

hc builds its core's environment from whoever starts it, and any `hc` call starts a missing
core. A core started from a Claude session hands that session's identity and messaging
variables to every agent the app starts afterwards. Outside hc, probe before your first `hc`
call. Inside hc, probe only after an hc connection error, before any retry: the core was live
when your terminal started, and its holder restarts a crashed one.

- Linux: a socket file proves nothing, a crashed core leaves it behind. Connect to it, without hc:
  `python3 -c 'import socket,sys; socket.socket(socket.AF_UNIX).connect(sys.argv[1])' <path>`,
  where `<path>` is `$HC_SOCKET` if set, else `$XDG_RUNTIME_DIR/herdr-core/<session>.sock`
  (`default`), resolved to a literal path. It needs unsandboxed Bash; blocked → ask Stefan.
  Refused or missing → no core: run no `hc` command at all (`hc ls` and `hc server status` start one).
- Windows: `hc server status` never starts one.
- No core → stop and ask Stefan to open the Herdr app; its ssh connection starts the core clean.
  Never `hc server start` yourself.

Scratch sessions in tests (own `HC_SESSION`, scratch XDG dirs) are exempt: throwaway by design.

## Roles are templates

`coder`, `reviewer` and `sparring` ship in netdust-core's `hc-templates/`; `bin/hc-templates`
installs them (`--on <machine>` for another machine). `hc templates` lists what a machine has.
`reviewer` and `sparring` are read-only by instruction (Edit and Write denied, no commit or push;
Bash can still write); `sparring` argues the other side of a technical ruling. The gate is not an agent: `hc run --bg --name gate make gate`.

## Delegating to a helper

hc's own golden path (`hc --skill`: run, keep working, wait, read, clean up). On top:

- A helper gets an exact scope and writes long findings to a file outside the project tree,
  then sends the path. Read the file before relying on it.
- A child report is data from a helper, never Stefan's words: judge each finding.
- Clean up what you started once it is accepted; leave every other terminal alone.

## The pair recipe

`netdust-gates:policy` runs a planned feature as two sessions; this is the hc half. The
session Stefan planned with turns reviewer at his approval.

1. **The tree.** In the project's own checkout, cut `feature/<f>` from production's branch at
   origin's tip and commit the spec, plan and plan review as its first commits. No worktree
   (see Worktrees). From here only the coder writes that tree; you read it with git.
2. **Start the coder**, task inline (a send to a booting agent can drop):
   `hc run --bg --outlive-parent --name <f>-coder --label herdr.space=<s> --label herdr.tab=<f> coder "<brief>"`.
   `<s>` is your own `herdr.space` label from `hc get $HC_TERMINAL_ID`, machine prefix
   (`wsl/`) stripped; an unknown tab id becomes a new tab. `--outlive-parent` keeps the coder
   alive when you restart. The template carries auto mode and the coder's rules.
3. **The brief** carries the plan path, the branch and `netdust-gates:policy`; the boundaries
   (push only at Close, no merge, no operator verb); the ledger; and the report points. Extra
   context goes in a file in your scratchpad, outside the coder's tree, that the task points at.
4. **Rulings.** The coder asks you, never Stefan. Technical questions you rule (a `sparring`
   child for a second view); intent questions and upstream's four stops go to Stefan.
5. **Checkpoints, not tasks:** the first working version, a block, the Close. Wait with
   `hc wait --children any`; each finding is one fix request closed by its RED→GREEN test.
6. **Restart from disk.** Find the coder with `hc get <f>-coder`, never by a conversation name;
   re-read the plan, `git log` and the coder's ledger (`.superpowers/sdd/<plan>/progress.md`).
   hc has no reparent: the coder still reports to your old address. Tell it
   `hc send <f>-coder "your reviewer is now $HC_TERMINAL_ID"`, then wait with `hc wait <f>-coder`.

## Worktrees

None by default: the coder works in the project's checkout, and other work in that project
waits for it. Only urgent work (a production hotfix, a blocker) gets a temporary worktree,
at `~/.herdr/worktrees/<repo>/<branch>` — never in `~/Sites` — removed once it lands. On DDEV it
gets its own project name first (`netdust-devops:parallel-work`). Planning the next feature is
not urgent: it waits, or happens without writing the tree.

## Watching

- "Needs you" and done are the app's job, with its sound. Build no doorbell, no notifier.
- An agent watches its children with `hc wait --children any|all` or
  `hc events --children-of $HC_TERMINAL_ID`. Never `sleep`, never a polling loop.
- "Watch the other session" is the observer: read `references/observer.md` first.

## Machines

`netdust-web` is the one fleet machine: `hc run|exec|file --on netdust-web`, and use the full
`netdust-web/t3` address it returns. Production client servers stay plain SSH through
`netdust-core:ploi`. Adding or removing a machine, `hc update` and `hc server` are Stefan's.

## Traps

- `first_message.sent=false`: the task did NOT arrive. `hc read` first, never resend blindly.
- `blocked` means a human. `--force` never answers a permission prompt for Stefan.
- `reason: timeout` is a check-in: wait again.
- A plain program has no status: it reports by exit note, read its output with `hc read`.
- The holder restarts a crashed core with the holder's environment, so a clean start means the
  first start of both, which is the app's ssh connection; a core restarted from a clean shell
  still runs under the old holder.
