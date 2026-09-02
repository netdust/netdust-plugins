# herdr moments — where the harness reaches for the multiplexer

**The single home** of netdust-agent's herdr usage. Detection is `HERDR_ENV=1` (your own
address: `$HERDR_PANE_ID` / `$HERDR_TAB_ID` / `$HERDR_WORKSPACE_ID`); outside herdr every
row below is a no-op and the spine reads exactly as written. Syntax is never stated
here — run `herdr --skill` for the contract. Channels (SendMessage vs the CLI),
topology-per-working-tree, the remote-box rule, the dispatch-brief recipe and the traps
all live in `netdust-core:herdr-orchestration`; this file only maps harness MOMENTS onto
the primitives that skill already decided.

| Harness moment | Primitive | When NOT to |
|---|---|---|
| **The seam** (`planning` stops) | one `spec` tab in the project's workspace, unfocused, paging `plan.md` + `tasks.md` + the gate verdict (the `bat` recipe in herdr-orchestration, "an artifact the operator READS"); then say the tab exists | never a fourth pane in the work layout; never focus it |
| **Parallel dispatch** (`[P]` siblings, a contract-lane split pair, any second code-editing agent) | a worktree workspace per agent, unfocused, based on the integration branch read from `site.yml` (dev-stack owns the base — the `--base master` in herdr-orchestration's example is a framework-fix example, not the rule); result read from git in that worktree, never from the pane | sequential behaviour-lane work stays in the main pane as subagents — no topology for work that needs no isolation |
| **Stage 2 overview** | one `status` tab per feature, unfocused, watching `bin/loop-check.py <feature>` and `git status --short` together | not per cluster, not per task; one tab for the run |
| **Unattended run** (`/loop` armed) | the doorbell: `scripts/herdr-watcher.sh` from herdr-orchestration on the working pane, in the background | an attended run needs no doorbell; the operator is the doorbell |
| **The branch review** (Stage 3) | the reviewer as a herdr agent in its own pane, its report opened in a `review` tab; the pane stays after the report so the operator can question it | contract-lane cluster panels stay subagents — cheaper, and their findings go to the ledger, not the operator |
| **Spec-close** (`compounding`) | read `memory/session-review/*-proposals.md` from the session-review pane and fold them into the manifest | never write a skill from the pane's proposals without the operator's approval — same rule as compounding itself |

Two rules from herdr-orchestration that bite the harness specifically:

- **`herdr session list` first** — the project's topology lives in the project's session;
  a tab or workspace built in the wrong session cannot be moved.
- **Never a second agent on a tree another agent edits.** The 2026-08-09 building lesson
  (two implementers, one working tree, 14 and 17 phantom failures) is exactly this; the
  worktree is the isolation, and using it safely stays a git decision dev-stack owns.
