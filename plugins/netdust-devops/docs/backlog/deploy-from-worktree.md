# Backlog — deploy from a worktree, not the checkout

Raised 2026-09-21 in vad-vormingen, after the move to 0.7.0. Not started. Needs
brainstorming → plan before any code: it changes deploy semantics for every
rsync project.

## The ask

`make deploy env=staging` should not require checking out `staging` first. Since
0.7.0 `staging` is rebuilt by `promote` and never committed on, so the checkout
step is ceremony. Chosen direction: **deploy `origin/<branch>` from a throwaway
worktree** (as `rollback` already does) — works from any branch, any tree state,
and ships exactly the pushed commit instead of "whatever the laptop has"
(the rsync-reads-the-working-tree drift, vad-vormingen lessons 2026-09-16).

## Why it cannot ship as-is

Gitignored content inside payload dirs is load-bearing today — the working-tree
deploy is how it reaches servers. Measured across the fleet 2026-09-21:

| Project | Ignored inside payload, not excluded | Worktree deploy would |
|---|---|---|
| citizenne, edushare, josworld | theme `dist/` build output | delete built assets |
| edushare, josworld | `mu-plugins/ntdst-core`, `ntdst-baseline` (composer) | delete the framework |
| edushare | `content/plugins/fluentform` — whole `content/plugins` is payload | delete a third-party plugin |
| vad-vormingen | nothing | work |

vad-website carries only `*.bak` / vendored `.github/` strays (harmless).

## Proposed shape (undecided)

- `deploy.exclude` for server-owned paths (third-party plugins): rsync neither
  copies nor `--delete`s them.
- For build output / composer packages, one of:
  - **(a) `deploy.build`** — commands run inside the worktree (`composer install
    --no-dev`, `npm ci && npm run build`). Commit-exact; slower; needs the
    toolchain outside DDEV (a /tmp worktree is not mounted in the container).
  - **(b) `deploy.carry`** — declared ignored paths copied from the working tree
    into the worktree. Simple; keeps today's drift for those paths only, but
    declared (a `dist/` built on another branch still ships).
- **Guard:** refuse when a payload dir holds ignored files that are neither
  carried, built nor excluded — this is what makes it safe fleet-wide.
- Recommendation at the time: (b) + guard now, (a) per project later.

## Open decisions (Stefan)

1. `carry` + guard first, or straight to `build`?
2. Narrow edushare's `content/plugins` payload to its own plugins as part of
   this? **Live exposure regardless of this change:** with `--delete`, any
   third-party plugin missing from the laptop is deleted from the server on the
   next deploy.

## Proof when done

vad-vormingen `tests/devops/vad-flow-test.sh` + the core's `flow-test.sh` gain a
case: `make deploy env=staging` from a feature branch with a dirty tree deploys
`origin/staging` exactly, and the guard refuses a payload with an undeclared
ignored file.
