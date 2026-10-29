---
name: parallel-work
description: Use when more than one thing needs to happen at once in a project and the pieces could fight over the working tree — a bug found in an imported package while your feature is half-done, a production hotfix while the tree is dirty, a long test or gate run that blocks you, a second agent, a review that should not share your context. Answers ONE question — does this need a different checkout? — and the answer decides helper terminal versus worktree. Triggers on "uncommitted changes" blocking a verb, "make hotfix" refusing on a dirty tree, editing anything under vendor/, "run the tests while I keep working", "fix it in a separate window", "second agent", "another pane", "another tab", "workspace", "worktree", "split the pane", "in parallel", "don't lose my work", "I'm mid-feature and prod is broken". Symptoms include a make verb refusing because the tree is not clean, finding a framework bug inside a Composer --prefer-source package, wanting a gate run off your critical path, or two agents about to edit the same directory. For the flow verbs themselves see the devops skill; for agents and terminals run `hc --skill`.
---

# Parallel work — one question decides it

**Does this need a different checkout?**

That is the whole decision. Everything else follows.

| | Needs a different checkout? | Use | Why |
|---|---|---|---|
| Run the gate, tests, a build, tail a log | no | **helper terminal** (`hc run --bg`), same directory | it reads and executes; it does not edit |
| Read a spec, plan or report while you work | no | **tab** in the project's space | an artifact you look at, not another terminal crowding the work |
| Fix a bug in an imported package | **yes** | that repository's own checkout | it is a different repository |
| Hotfix production while your feature is dirty | **yes** | **worktree**, urgent | a different base, and `make hotfix` refuses on a dirty tree |
| A second agent that EDITS while a coder holds the checkout | **yes** | it **waits**; a **worktree** only if urgent | two agents in one directory edit the same file |
| A second agent that only reads | no | **helper terminal**, same directory | nothing to collide over |

The terminal does not isolate anything: two agents in one directory write to the
same files. **The worktree is the isolation**, and it costs a folder: one is made
only for urgent work, under `~/.herdr/worktrees/<repo>/<branch>` — never in `~/Sites` —
and removed once its branch lands.

Default to a helper terminal. Reach for a worktree only when the table above says the
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

Netdust projects install `ntdst-core`, `ntdst-baseline` and `netdust-flow` from
source (`preferred-install` maps `netdust/*` to it), so those are **real git checkouts inside `vendor/`**. Fixing
one there is committing to a different repository from inside this one.

Do not edit it in place and hope. Open that repository in its own checkout, fix
it on its own branch through its own flow, release it, and let Composer bring it
back. What you edit under `vendor/` is not covered by this project's
`deploy.payload` and will be overwritten by the next `composer install`.

### A long gate run

`make gate` on a full suite is minutes. It reads and executes — it edits
nothing — so it is a **helper terminal in the same directory**
(`hc run --bg --name gate make gate`), on the branch you are already on. No
worktree, no change to how you work.

The win is not a faster run. It is that the run happens beside you instead of
in front of you, and its output lands somewhere other than your context.

### A second agent

Reads only — a reviewer, a test runner, a log watcher → **helper terminal**.
Edits anything → it never shares the directory: two agents in one directory will
silently overwrite each other, and neither will report it. While a coder holds the
checkout, other work in that project waits for it, unless it is urgent (a production
hotfix, a blocker): only then a temporary worktree under `~/.herdr/worktrees`, removed
when that work lands. Planning the next feature is not urgent: it waits, or happens
without writing the tree.

### An urgent worktree on a DDEV project

The coder of a planned feature works in the project's checkout (`netdust-gates:policy`);
urgent work beside it gets a worktree. On a DDEV project that worktree must be its own DDEV project, or its
`make gate` tests the wrong code: the gate's integration tier runs `ddev composer`, and a
worktree carries the tracked `.ddev/config.yaml` — the main project's name, so the
main checkout's container. Give it its own name in `.ddev/config.local.yaml`, which
DDEV's own `.ddev/.gitignore` keeps out of git:

```yaml
name: <project>-<feature>      # laika-planning-model runs as name: laika-planning
```

Its container then serves `https://<name>.ddev.site`, and `test:int`, the local e2e tier
inside `make gate` and every `ddev` command run against the worktree's own code.
`make e2e env=<env>` is not one of them: it always drives a deployed environment,
never a local container.

Three things still name the main project's URL: `site.yml`'s `local.url` (tracked —
`make pull` rewrites the database to it), the database once it is copied, and a Bedrock
`.env`'s `WP_HOME` / `WP_SITEURL`. So start the worktree's project in this order:

1. **Its own `.env`**, with `WP_HOME` and `WP_SITEURL` at `https://<name>.ddev.site`. A
   fresh worktree has none (`.env` is ignored), and Bedrock refuses to boot without
   `WP_HOME`.
2. `ddev start`, then `ddev composer install`.
3. **Seed the database** from the main project — `ddev export-db --file=<dump>.sql.gz`
   there, `ddev import-db --file=<dump>.sql.gz` here — then rewrite its URLs:
   `ddev wp search-replace <main url> <worktree url> --all-tables --precise --skip-columns=guid`
   (the flags `make pull` uses). The e2e tier creates its user and fixture through
   wp-cli, so it needs an installed WordPress, and it reads its URLs from WordPress, so
   the rewrite follows the import. Never run `make pull` in a worktree without it.
4. **The host tiers' dependencies** on the host: `composer install` and `npm ci` (and
   Playwright's browsers). The gate runs every tier but `test:int` on the host.

Prove it before the first gate: in the worktree, `ddev wp option get home` prints the
worktree's URL (on Bedrock it reads `WP_HOME` from `.env`), and
`ddev wp db search '<main host>' --all-tables` prints nothing.

When the feature lands, `ddev delete <name>` removes the project and its database —
ask first.

---

## How the make verbs behave across checkouts

- `make feature` / `make hotfix` branch from `origin/main` (the production
  branch), whatever you stand on. `make save` / `make deploy` / `make gate`
  work anywhere and act on the branch you are standing on.
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
| A worktree for something that only reads | a helper terminal in the same directory |
| Two agents pointed at one directory | the second waits for the coder; a worktree only if its work is urgent |
| A worktree in `~/Sites`, or one for work that could wait | wait for the checkout; urgent work goes under `~/.herdr/worktrees` |
| A worktree left behind after its branch landed | `git worktree remove <path>` — otherwise the branch cannot be deleted |
| Raw `git checkout` to move between rungs | the verbs; a rung held elsewhere is exactly what they refuse over |

---

## See also

- `netdust-devops:devops` — the flow verbs, the deploy gate and ledger, `site.yml`
- `hc --skill` — **the syntax authority** for agents, helper terminals and their
  reports. Run it; do not guess flags. `herdr-app --skill` covers spaces and tabs.
- `netdust-core:hc-orchestration` — the pair recipe, delegation, watching, and the
  protocol for talking to another session

This skill owns the *decision*. Those own the *syntax*. If the two ever
disagree, the syntax authority wins on syntax and this file wins on whether you
should be creating a second checkout at all.
