# Two sessions — the sparring draft (§7 of the design sparring, 2026-10-18)

A starting point for Task 1 Step 2 and Task 3 Step 2, not the text. Copied from the laika session's scratchpad (`two-session/spar-1.md`) so it survives a reboot.

## 7. Recommended rule text (replaces policy lines 96–110; 148 lines total)

```markdown
## Execution mode

A planned feature runs as two sessions; a change with no plan file stays in this one. **This session
turns reviewer; a coder session executes, and from the handoff only the coder writes the feature's
tree.** Spec, plan and plan review are the first commits of `feature/<feature>`, in its own worktree
cut from production's branch, whose `make gate` tests that tree and not the main checkout. Start the
coder by `netdust-core:herdr-orchestration`'s pair recipe in herdr, else as one background subagent
there. Its brief opens `Role: coder`: a coder skips Intake and the plan, never starts a coder, and runs
every step that writes the tree (tasks, `make gate`, fix pass, `/shakeout`, push). In it, **Native** by
default; **subagent-driven** only for a security-boundary unit or a plan that outlives one context
(upstream's per-task TDD undoes the unit cut); name the rule that fired. The reviewer reads the first
working version and runs `make review name=<feature>`; a finding is one fix request closed by its test.

## Stops

Upstream's four stops stand. Netdust names the ones that occur: the plan approval; the shake-out
screenshot yield (Close, step 4); the flow list a shake-out proposes for a branch with no spec; and
every devops verb that belongs to the operator — `promote`, `unpromote`, `ship`, deploy — which Stefan
runs or confirms by typing. A coder asks its reviewer, never Stefan. Everything else you decide and
ledger as `Ruling: <what> — <why> — <cost if wrong>`, and list in the final message. A shake-out
exception Stefan accepts is `Accepted-by-human:` in the manifest, never `Ruling:`; only he writes it.
```

Close step 3's "(a finding that is a decision goes to Stefan)" stays. Read it as a decision about
intent. The reviewer rules on technical findings.

### The recipe outline for herdr-orchestration ("Recipe — the thinker/coder pair", about 30 lines)
1. **Before the spec.** `herdr session list`. Create a worktree workspace from the production branch
   (`scripts/site environments.production.branch`), with `--branch feature/<f> --no-focus`. On DDEV:
   `.ddev/config.local.yaml` `name: <project>-<f>`, `ddev start`, install, seed. The laika-planning
   precedent shows this works. Then write and commit the spec, plan and plan-review there, and open the
   plan in a tab for Stefan.
2. **After approval.** `agent start <f>-coder --kind claude` in that workspace, **in the reviewer's
   permission mode**. Its first prompt is the brief:
   - `Role: coder`;
   - the plan path and branch;
   - the entry `netdust-gates:policy`;
   - the mode and the rule that fired;
   - the reviewer's ListAgents name;
   - boundaries: this tree only, no merge, push `feature/<f>` only at Close, no operator verbs, the
     surfaces that are hot elsewhere;
   - the report line;
   - the ledger path;
   - intent questions go to the reviewer; the four stops mean stop and say so.

   Environment notes are hints (the existing recipe rule).
3. **Watch.** Background `agent wait` plus `notify_when_idle`, the doorbell watcher for Stefan, and a
   viewport read only at `blocked`.
4. **Review.** Read `<wt>/.superpowers/sdd/plan/progress.md` and a `review-package` file. Never edit
   the tree. Send one fix request per finding, which the coder ledgers.
5. **Restart.** Re-start from branch + ledger, and find the peer again by `cwd`.
6. **Close.** The coder pushes. The reviewer runs `make review`. The coder runs the fix pass (copying
   the review into `specs/<f>/review.md`), then `/shakeout`. The reviewer gives Stefan the screenshots
   and `make promote name=<f>`. Then `herdr worktree remove`, and remove the throwaway DDEV project
   (destructive: ask).
7. **Outside herdr.** The fallback in §4.

