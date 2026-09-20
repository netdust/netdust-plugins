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

- `make feature` / `make hotfix` / `make save` / `make deploy` / `make gate`
  work anywhere. They act on the branch you are standing on.
- `make promote` / `make unpromote` **rebuild staging — they need no
  checkout.** The rebuild happens in a throwaway worktree of its own and
  pushes straight to origin, so two agents can promote different features
  from two different checkouts without either holding `staging`.
- `make ship` **runs from the staging checkout** (or a `hotfix/*` branch) and
  needs the production branch free — not checked out in another worktree. If
  it is, `ship` **refuses by name** and prints the command that works; it does
  not half-run and die on a git error.

So the shape of parallel work is: promote and unpromote from anywhere; ship
from wherever `staging` — or the hotfix — actually lives, once production is
free.

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
