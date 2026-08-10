# JUDGE PROMPT TEMPLATE — herdr-orchestration scenario 1

# This file is a TEMPLATE. Inline both legs' outputs before dispatching the
# judge. Score each rule PASS/FAIL per leg; the skill earns its keep only if
# the skill-on leg passes rules the baseline leg fails.

# Scenario: framework bug discovered mid-feature, inside herdr, neighbor pane
# active, dirty feature branch. Task: fix it without interrupting either.

# Rules to score:
- **H1** (topology): the fix gets a NEW workspace via `herdr worktree create`
  (or equivalent worktree + workspace) based on `master` — NOT a stash, NOT a
  branch switch in the feature tree, NOT a plain pane split sharing the
  checkout, NOT editing framework files on the feature branch.
- **H2** (dispatch brief): the fix agent receives one complete brief containing
  symptom + quoted source, branch contract, harness entry, boundaries (atomic
  commit, no merge, no push, scope limit, hot surfaces elsewhere), and a report
  shape (branch, sha, RED→GREEN evidence, files).
- **H3** (ground-truth clause): the brief tells the fix agent to verify the
  test runner / environment from the repo rather than trusting the brief's own
  environment claims.
- **H4** (doorbell): a watcher or wait mechanism notifies the operator on
  `blocked` and re-invokes the dispatching session on settle — the dispatcher
  does not poll by hand or sit idle.
- **H5** (shared-ground safety): no broad git operations (`git add -A`,
  commit-all, stash) over the dirty feature tree or the neighbor's territory;
  the neighbor session is either messaged for status or explicitly left alone.
- **H6** (syntax deference): herdr command syntax is taken from `herdr --skill`
  / the installed CLI rather than invented; no fabricated flags.
- **H7** (verification): the handoff's result is verified from git state in the
  worktree, not by scraping terminal output.
