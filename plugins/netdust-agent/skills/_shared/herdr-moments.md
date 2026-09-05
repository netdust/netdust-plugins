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
| **Parallel dispatch** (`[P]` siblings, a contract-lane split pair, any second code-editing agent) | a worktree workspace per agent, unfocused, based on the integration branch read from `site.yml` (devops owns the base — the `--base master` in herdr-orchestration's example is a framework-fix example, not the rule); result read from git in that worktree, never from the pane | sequential behaviour-lane work stays in the main pane as subagents — no topology for work that needs no isolation |
| **Stage 2 overview** | one `status` tab per feature, unfocused, watching `bin/loop-check.py <feature>` and `git status --short` together | not per cluster, not per task; one tab for the run |
| **Unattended run** (`/loop` armed) | the doorbell: `scripts/herdr-watcher.sh` from herdr-orchestration on the working pane, in the background | an attended run needs no doorbell; the operator is the doorbell |
| **The branch review** (Stage 3) | the reviewer as a herdr agent in its own pane, its report opened in a `review` tab; the pane stays after the report so the operator can question it | contract-lane cluster panels stay subagents — cheaper, and their findings go to the ledger, not the operator |
| **A flow verb refuses on a dirty tree** (`make hotfix` mid-feature: production is broken and the feature is half-done) | a worktree workspace off `origin/<production branch>`, unfocused; hotfix there, then `make finish name=<x>` from wherever the rung lives | when the feature work is at a natural stopping point — commit it and hotfix in this checkout. Never `make save` on unfinished work purely to unblock the hotfix |
| **A bug in an imported package** (`ntdst-core`, `ntdst-baseline`, `netdust-flow` — `--prefer-source` puts real git checkouts under `vendor/`) | a workspace on THAT repository's own checkout; fix it on its own branch through its own flow, release, then `composer update` here | never edit it in place: `vendor/` is outside this project's `deploy.payload`, so the fix never deploys, and the next `composer install` overwrites it |
| **A long gate or test run** | a sibling pane, same cwd, same branch — it reads and executes, it edits nothing | never a worktree or workspace: no second checkout means no second dependency install and no second container. The win is the run being beside you, not a faster run |
| **Spec-close** (`compounding`) | read `memory/session-review/*-proposals.md` from the session-review pane and fold them into the manifest | never write a skill from the pane's proposals without the operator's approval — same rule as compounding itself |

## The two recipes, verified against herdr v0.8.2 on 2026-09-04

Syntax elsewhere in this file defers to `herdr --skill`. These two were run and
their output read, so they are written out — correct them here if herdr moves.

**A gate or suite beside you.** `wait-output` blocks until a sentinel appears
AND returns the pane text in the same result, so there is no second read call:

```bash
id=$(herdr pane split --current --direction right --cwd "$PWD" --no-focus \
     | jq -r .result.pane.pane_id)                       # → "w9:p2", workspace-qualified
herdr pane run "$id" 'make gate; echo GATE-EXIT=$?'
herdr pane wait-output "$id" --regex '^GATE-EXIT=[0-9]+' --timeout 900000 \
     | jq -r '.result.read.text' | tail -60              # blocks, then the tail only
```

**ANCHOR the sentinel.** The pane's text includes the command line itself, so
`--match 'GATE-EXIT='` matches the ECHO of the command that will produce it and
returns before the gate has run. `^` distinguishes them: the command line starts
with a shell prompt, the output line starts with the sentinel. Verified — a bare
`--match` returned `matched_line` pointing at the command, not the result.

`pane read` on a fresh pane needs no `--source`: the default (`visible`) carries
the content, while `--source recent-unwrapped` returns EMPTY until there is
scrollback beyond the viewport. Prefer the text `wait-output` already gives you.

**A different checkout.** `herdr worktree` (flags confirmed from `herdr worktree`):

```bash
herdr worktree create --cwd <repo> --base <ref> --branch <name> --label <name> --no-focus
herdr worktree list [--workspace ID | --cwd PATH]
herdr worktree remove --workspace ID [--force]
```

Removal is by WORKSPACE id, so the worktree and the workspace holding it go
together — which is why a worktree gets its own workspace rather than a tab.

**Whether a moment needs a different checkout at all is `netdust-devops:parallel-work`'s
question, not this file's.** It owns the decision (pane vs worktree, and why); this table
says which primitive the answer maps to. If the two disagree, the decision is upstream.

Two rules from herdr-orchestration that bite the harness specifically:

- **`herdr session list` first** — the project's topology lives in the project's session;
  a tab or workspace built in the wrong session cannot be moved.
- **Never a second agent on a tree another agent edits.** The 2026-08-09 building lesson
  (two implementers, one working tree, 14 and 17 phantom failures) is exactly this; the
  worktree is the isolation, and using it safely stays a git decision devops owns.
