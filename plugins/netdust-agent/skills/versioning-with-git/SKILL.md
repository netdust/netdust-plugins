---
name: versioning-with-git
description: "CRAFT skill — commit-craft, reached for by harnessed-development Stage 2 (execute — the atomic commit per task) and Stage 3 (finish). It is the primary source for commit hygiene (restated from addyosmani/agent-skills git-workflow-and-versioning, MIT): atomic commits, conventional messages that explain WHY, the ~100-line commit target / split anything over ~1000, the save-point pattern (test → commit on green / revert on red), and pre-commit hygiene (diff review + secret scan + run tests/lint/typecheck), plus archaeology (git bisect / blame / log --grep). It explicitly DEFERS branch-FLOW (which branch to start, staging→main git-flow, make feature/finish/ship, hotfix) to the stack's dev-stack skill, and worktree SETUP to superpowers:using-git-worktrees. Use when committing a finished task or preparing a branch to finish."
---

<objective>
This skill is **commit-craft**: how to turn a finished task into a clean, atomic, reversible commit, and how to read history when you need to. It is reached for at `harnessed-development` Stage 2 (one atomic commit per task) and Stage 3 (finishing the branch). It does NOT decide which branch you are on, the git-flow that moves work to staging/main, or the worktree you isolate in — those are deferred (see below). There is no single superpowers base for commit hygiene, so this skill carries it, restated from `addyosmani/agent-skills:git-workflow-and-versioning` (MIT) with the Netdust spine added.
</objective>

<deferrals>
**Branch-FLOW is NOT here — it lives in the stack's `dev-stack`.** Which branch to start work on, the staging→main git-flow, `make feature` / `make finish` / `make ship`, hotfix branches, deploy-on-merge — all of that is the loaded stack sub-plugin's `dev-stack` skill. Do not duplicate branch policy here; this skill assumes you are already on the right branch and shapes the *commits* on it.

**Worktree SETUP is deferred to `superpowers:using-git-worktrees`.** When a task needs an isolated workspace, that skill owns creating it (native tools or `git worktree` fallback). This skill commits *inside* whatever workspace you are in.
</deferrals>

<atomic_commits>
**One commit = one logical change.** A commit should do a single coherent thing and leave the tree green. Target ~100 lines of real change per commit; **split anything over ~1000 lines** into a sequence — a reviewer (and a `git bisect`) can only reason about a change they can hold in their head. This is the same sizing as the review clusters: an atomic commit per task aligns with the 1f review-cluster boundary, so a cluster review reads as a clean stack of commits, not one boulder.
</atomic_commits>

<conventional_messages>
**Conventional prefix + a body that explains WHY, not what.** Subject: `<type>(<scope>): <imperative summary>` (`feat`, `fix`, `chore`, `docs`, `test`, `refactor`; in phase work, `phase-N: <what>`). The diff already shows *what* changed — the body's job is the *why*: the constraint, the bug class, the decision rationale a future archaeologist (or `log --grep`) needs. Keep the subject under ~72 chars, imperative mood ("add", not "added").
</conventional_messages>

<the_netdust_layer>
The part addy cannot know — why commit-craft lives inside *this* harness:

**1. The commit body carries the testing-workflow evidence.** When the `testing-workflow` gate signs a task off, it produces a STATUS / Test-evidence block (the tier ruling, the RED-first proof or the named deferral). **That block goes into the commit body** — it is where "Tier B: glue, seam test covers the wire" or "Tier A: denial path asserted, run ≥3×" is recorded for the reviewer and for `/code-review`. A task commit with no test-evidence line in its body is missing the gate's output.

**2. Secret-scan before every commit — BYOK keys never get committed.** Pre-commit hygiene is non-negotiable here because this project handles BYOK credentials and a `FOLIO_MASTER_KEY`. Before staging: review the full diff (`git diff --staged`), scan for secrets (API keys, tokens, `.env` values, private URLs), and run the project's tests/lint/typecheck. This ties directly to the `threat-modeling` gate — a committed credential is the cheapest catastrophic leak, and the diff review is the last gate that catches it. Never `git add -A` blind.
</the_netdust_layer>

<save_point_pattern>
**Test, then commit on green / revert on red — the commit is your save-point.** After a task: run the suite; if green, commit immediately (you now have a known-good restore point); if red and you cannot quickly fix, `git checkout -- .` back to the last green commit rather than digging a deeper hole. Never `git stash` to park work mid-flow — stashes silently get lost; commit a `wip:` instead and amend. Commit small and often so every step back is one step.
</save_point_pattern>

<archaeology>
**Read history to locate, not to guess.** When a regression appears or you need the why behind a line:
- `git bisect start / bad / good` — binary-search the commit that introduced a behavior; pairs perfectly with atomic commits (a bisect over boulders tells you nothing).
- `git blame <file>` / `git log -L` — who last touched this line and in what commit (then read that commit's body for the *why* you wrote above).
- `git log --grep=<term>` / `git log -S<string>` — find the commit that added/removed a string or matched a message.
</archaeology>

<success_criteria>
A commit made under this skill:
- Is **atomic** (one logical change, tree green), ~100 lines, with anything >1000 split.
- Has a **conventional subject** and a body that explains **WHY**.
- Carries the **testing-workflow STATUS / Test-evidence block** in its body.
- Passed **pre-commit hygiene**: staged-diff review + **secret scan** (no BYOK key / token / `.env` ever committed) + tests/lint/typecheck green.
- Was the **save-point** of a test→commit cycle (no `git stash` parking; `wip:` + amend instead).
- Left **branch-flow to `dev-stack`** and **worktree setup to `superpowers:using-git-worktrees`** — this skill only shaped the commits.
</success_criteria>

<integration>
- **`harnessed-development` Stage 2 + 3** — the steps that reach for this skill: one atomic commit per executed task, then preparing the branch to finish.
- **`dev-stack` (stack sub-plugin)** — owns branch-FLOW (which branch, staging→main git-flow, `make feature/finish/ship`, hotfix). This skill explicitly defers all branch policy there; it only shapes commits.
- **`superpowers:using-git-worktrees`** — owns worktree SETUP; this skill commits inside whatever workspace exists.
- **`testing-workflow`** — its per-task STATUS / Test-evidence block is what this skill records in the commit body.
- **`threat-modeling`** — the pre-commit secret scan is the last catch for a BYOK credential leak; this is where that gate's concern lands at commit time.
- **`finishing-a-branch`** — the Stage 3 gate that decides merge/PR/cleanup once these commits are clean.
- **Provenance** — commit hygiene + archaeology restated from `addyosmani/agent-skills:git-workflow-and-versioning` (MIT, the primary source since no single superpowers base exists); the test-evidence-in-body, BYOK secret-scan, cluster-aligned atomicity, and the branch-flow/worktree deferrals are the Netdust spine this file adds.
</integration>
