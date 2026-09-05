---
name: parallel-work
description: Use when more than one thing needs to happen at once in a project and the pieces could fight over the working tree — a bug found in an imported package while your feature is half-done, a production hotfix while the tree is dirty, a long test or gate run that blocks you, a second agent, a review that should not share your context. Answers ONE question — does this need a different checkout? — and the answer decides pane versus worktree. Triggers on "uncommitted changes" blocking a verb, "make hotfix" refusing on a dirty tree, editing anything under vendor/, "run the tests while I keep working", "fix it in a separate window", "second agent", "another pane", "another tab", "workspace", "worktree", "split the pane", "in parallel", "don't lose my work", "I'm mid-feature and prod is broken". Symptoms include a make verb refusing because the tree is not clean, finding a framework bug inside a Composer --prefer-source package, wanting a gate run off your critical path, or two agents about to edit the same directory. For the flow verbs themselves see the devops skill; for terminal syntax run `herdr --skill`.
---

# Parallel work — one question decides it

**Does this need a different checkout?**

That is the whole decision. Everything else follows.

| | Needs a different checkout? | Use | Why |
|---|---|---|---|
| Run the gate, tests, a build, tail a log | no | **pane**, same directory | it reads and executes; it does not edit |
| Read a spec, plan or report while you work | no | **tab**, same workspace | an artifact you look at, not a fourth pane crowding the layout |
| Fix a bug in an imported package | **yes** | **worktree** (in its own workspace) | it is a different repository |
| Hotfix production while your feature is dirty | **yes** | **worktree** | a different base, and `make hotfix` refuses on a dirty tree |
| A second agent that EDITS | **yes** | **worktree** | two agents in one directory edit the same file |
| A second agent that only reads | no | **pane** | nothing to collide over |

The terminal does not isolate anything: two panes in one directory write to the
same files. **The worktree is the isolation.** A workspace is the container that
makes a worktree visible and removable as one unit — it is organisation, not
isolation, and on its own it gives you no separate git state.

Default to a pane. Reach for a worktree only when the table above says the
checkout differs — a second checkout costs a second dependency install, a second
container, and a `site.yml` pointing at the same servers from two places.

---

## The moments this actually comes up

These are the points where the decision is needed and easy to miss. If you are
at one of them, you are in this skill.

### A verb refuses because the tree is not clean

```
❌ You have uncommitted changes
```

`make hotfix` and `make feature` both require a clean tree, deliberately. When
production is broken and your feature is half-done, there are two routes and
only one of them is usually right:

- **Commit or stash here**, then hotfix in this checkout. Fine when the feature
  work is at a natural stopping point.
- **Hotfix in a separate checkout.** Nothing here moves, nothing half-done gets
  committed to look tidy, and both sit side by side until each lands.

The second is the one people forget, and `make save` on unfinished work to
unblock a hotfix is the mistake it prevents.

### A bug in an imported package

Netdust projects install `ntdst-core`, `ntdst-baseline` and `netdust-flow` with
`--prefer-source`, so those are **real git checkouts inside `vendor/`**. Fixing
one there is committing to a different repository from inside this one.

Do not edit it in place and hope. Open that repository in its own checkout, fix
it on its own branch through its own flow, release it, and let Composer bring it
back. What you edit under `vendor/` is not covered by this project's
`deploy.payload` and will be overwritten by the next `composer install`.

### A long gate run

`make gate` on a full suite is minutes. It reads and executes — it edits
nothing — so it is a **pane in the same directory**, on the branch you are
already on. No worktree, no workspace, no change to how you work.

The win is not a faster run. It is that the run happens beside you instead of
in front of you, and its output lands somewhere other than your context.

### A second agent

Reads only — a reviewer, a test runner, a log watcher → **pane**.
Edits anything → **worktree**, always. Two agents in one directory will
silently overwrite each other, and neither will report it.

---

## How the make verbs behave across checkouts

A rung branch can only be checked out in one place at a time, and the promoting
verbs check one out. So:

- `make feature` / `make hotfix` / `make save` / `make deploy` / `make gate`
  work anywhere. They act on the branch you are standing on.
- `make finish` / `make promote` / `make release` need a rung. If that rung is
  checked out in another worktree they **refuse by name** and print the command
  that works — they do not half-run and die on a git error.
- `make finish name=<x>` merges a branch you are **not** standing on. That is
  how the checkout holding the rung finishes work done in another one. It
  refuses if that branch has uncommitted changes wherever it lives.

So the shape of finishing parallel work is: do the work in its own checkout,
then finish it from wherever the rung lives.

### Cleaning up

`make finish` cannot delete a branch that is still checked out somewhere. It
says so rather than leaving you guessing:

```
feature/x kept — it is checked out in a worktree. Remove it with: git worktree remove <path>
```

Remove the worktree, then the branch goes. A stray worktree is a branch you
cannot delete later and a directory that drifts out of date.

---

## Anti-patterns

| Smell | Fix |
|---|---|
| `make save` on half-done work purely to unblock a hotfix | hotfix in a separate checkout; leave this one alone |
| Editing a package under `vendor/` in place | fix it in that repository's own checkout, release, `composer update` |
| A worktree for something that only reads | a pane in the same directory |
| Two agents pointed at one directory | one of them gets a worktree, or it does not edit |
| A workspace created "to be organised" | a workspace with no second checkout in it buys nothing |
| A worktree left behind after its branch landed | `git worktree remove <path>` — otherwise the branch cannot be deleted |
| Raw `git checkout` to move between rungs | the verbs; a rung held elsewhere is exactly what they refuse over |

---

## See also

- `netdust-devops:devops` — the flow verbs, the deploy gate and ledger, `site.yml`
- `herdr --skill` — **the syntax authority** for panes, tabs, workspaces and
  agents. Run it; do not guess flags. `herdr worktree` lists the worktree verbs.
- `netdust-core:herdr-orchestration` — which channel, which topology, and the
  protocol for talking to another session

This skill owns the *decision*. Those own the *syntax*. If the two ever
disagree, the syntax authority wins on syntax and this file wins on whether you
should be creating a second checkout at all.
