# Plan review — two-session
Reviewed-plan: fa51a1c52deaa58a0573a30066f11d353396de02
Verdict: not ready

All of round 2's Blocking and Should fix items are closed. I ran the gates suite with `env -u NETDUST_GUARD_ASK`: 20/20 modules green. Without it: 19/20, with 22 FAIL lines. The devops suite is green.

One new Blocking finding, confined to Task 4. The seeding it documents goes through a verb that writes the main checkout's URL into the worktree's database. That brings back the defect R3 exists to prevent. Tasks 1–3 are ready as written.

Two new Should fix findings:
- The pilot's Close reads `origin/feature/two-session` one step before anything pushes it.
- `coder-brief-no-recursion` runs its coder on `master`, where upstream stops before it implements.

## Blocking

**B1. Task 4 seeds the worktree through a verb that points it back at the main checkout.**
- Plan:
  - Task 4 Step 1: "so `make gate`, `make e2e` and `ddev` commands run against its own container".
  - Also Task 4 Step 1: "seeded from the main project's database, through the project's own verb when one exists … because it is what makes `make e2e` meaningful".
  - Review Focus 6.
  - Test map row 4: "none — documentation".
- Source:
  - **The seeding verb.** The only one is `make pull` (`plugins/netdust-devops/dist/mk/wp.mk:70-77`). It pulls from a remote environment, production by default (`:72`), not from the main project's database.
  - **The URL it writes.** Its `_pull-db` rewrites every URL to `site.yml`'s `local.url` (`wp.mk:186`, `:200`). `site.yml` is tracked, so a worktree reads the main project's value. In laika that is `site.yml:135-136`: `ddev_project: laika`, `url: https://laika.ddev.site`. A worktree named `laika-planning` is served at `https://laika-planning.ddev.site`, but its database then names `laika.ddev.site`.
  - **Where the browser tier gets its URLs.** It asks WordPress. Laika's `bin/e2e.sh` takes the base URL from `ddev exec printenv DDEV_PRIMARY_URL` (`:17-21`), but the fixture URL from `wp post list … --field=url` (`:55`).
  - **When that URL is the main host.**
    - On a site whose home URL lives in the database, that fixture URL is the main checkout's host. The run then tests the main checkout's code.
    - On Bedrock, `WP_HOME` and `WP_SITEURL` come from `.env` (laika `config/application.php:51`, `:76-77`), and a `.env` copied from the main checkout names the main host too.
    - I could not read `.env`, so I don't know whether it derives the value from `DDEV_PRIMARY_URL`.
  - **`make e2e`.** It never runs against a local container. It refuses without `env=` and drives `environments.<env>.url` (`plugins/netdust-devops/dist/Makefile.netdust:491-496`). So "`make e2e` … against its own container" is false, and so is the ruling's "what makes `make e2e` meaningful". The local browser tier is `make gate`'s `test:e2e` (laika `bin/gate.sh:15`).
  - **The devops skill.** devops `SKILL.md:368` says the URL is `https://<ddev-project>.ddev.site`, with the name taken from `local.ddev_project`. In a renamed worktree that is no longer true.
- Effect: the first WordPress pair follows the doc and gets a green gate that ran against the main checkout. That is the defect spec R3 names, and row 4 has no test that would see it.
- Change (Task 4 Step 1 and Review Focus 6, a few lines):
  - Say "the gate's tiers" (`test:int` and the e2e tier), not `make e2e`.
  - Say that the worktree's URL is `https://<name>.ddev.site`, and that three things still name the main one:
    - `site.yml`'s `local.url`, which `make pull` rewrites to;
    - the database, after a copy;
    - a Bedrock `.env`'s `WP_HOME`/`WP_SITEURL`.
  - The section then says:
    - set `.env` to the worktree's URL;
    - seed from the main project: `ddev export-db` there, `ddev import-db` here (or `make pull env=staging`);
    - then `ddev wp search-replace <main url> <worktree url>`;
    - never run `make pull` in a worktree without that rewrite.
  - Correct the ruling's rationale to match.
  - Review Focus 6 names its proof for the first pair: in the worktree, `ddev wp option get home` prints the worktree's URL.

## Should fix

**S1. The pilot's Close reads a remote branch one step before anything pushes it.**
- Plan:
  - Close step 2: `git show origin/feature/two-session:plugins/netdust-gates/commands/feature-review.md`.
  - Close step 3: "The coder pushes `feature/two-session`".
  - Task 3 Step 2: "the Close split (R7)".
- Source:
  - `git branch -a` shows no `origin/feature/two-session`, so step 2 fails with an invalid-object error.
  - `/feature-review` (`commands/feature-review.md:12`) and `make review` (`Makefile.netdust:534`) both try `origin/feature/<name>` first, then the local branch.
  - The local branch is shared by every worktree of this repo (`git rev-parse --git-common-dir` is `/home/ntdst/Projects/netdust-plugins/.git`).
  - R7 says the reviewer "resolves `origin/feature/<feature>`", which assumes the coder has pushed. The spar's recipe outline (§7, step 6) has the same order: "The coder pushes. The reviewer runs `make review`."
  - Once one push has happened, a later review without a fresh push reviews a stale head.
- Change:
  - Close: the coder pushes before step 2, and again after the fix pass. Or step 2 names `feature/two-session`.
  - Task 3 Step 2's Close-split bullet: the coder pushes and signals, then the reviewer reviews.

**S2. `coder-brief-no-recursion` can fail for a reason unrelated to recursion.**
- Plan:
  - Task 2 Step 2, the second case: "`commit: true` … Expect the target changed".
  - Interfaces: `prepare_sandbox`.
  - Review Focus 2.
- Source:
  - `run-evals.py:51` runs `git init`, and `git config --global init.defaultBranch` is unset. So the one commit lands on `master`.
  - The coder follows the policy into `superpowers:executing-plans`. Its Setup says "Never start implementation on a main/master branch without your human partner's explicit consent" (`executing-plans/SKILL.md:112-113`).
  - `using-git-worktrees/SKILL.md:41` asks for consent before creating a worktree in a normal checkout. If a worktree is created anyway, the edit lands under `.worktrees/`.
- Effect: either way the root target is unchanged and the case fails. That loses the only behavioural evidence for Review Focus 2.
- Change:
  - With `commit: true`, `prepare_sandbox` commits on a `feature/<case-id>` branch (from a `branch` key, or from the case id).
  - The prompt names that branch and says this checkout is the coder's worktree: work in place.

## Note

- **N1. Stub fidelity.** Round 2's N2 is half open: `agent wait` now settles, but the rest stands.
  - `worktree create` prints JSON with no path. A session that falls back to `git worktree add`, which `Bash(git *)` allows, may create a worktree outside the `TemporaryDirectory`. That worktree outlives the run.
  - Let the stub run a real `git worktree add` under `$EVAL_ROOT` and print the path.
  - Match `Role: coder` anywhere in `calls.log`. A brief can travel as `-- AGENT_ARG` on `agent start` (`herdr agent start --help`), not only through `agent prompt`.
- **N2. The shadow probe is a proxy.** `run_case`'s `bash -lc` probe stands in for the Bash tool's shell; it is not that shell. The real proof that the stub shadows is `two-session-handoff`'s `calls.log`.
  - Count the pair as passed only when that log shows the stub in the same run.
  - Otherwise no-recursion's absence check can pass vacuously.
- **N3. Routes `child_env` leaves open.**
  - The 0.9.5 client also reads `HERDR_SESSION` and `HERDR_CLIENT_SOCKET_PATH` (binary strings). Both are stripped from the inherited environment, but an inline `HERDR_SESSION=<name> herdr …` is a fourth route beside the three flags.
  - Children also inherit `CLAUDE_CODE_MESSAGING_SOCKET` and `CLAUDE_CODE_MESSAGING_TOKEN`. The CLI carries cross-session messaging (`notify_when_idle`, `cross_session_notify_idle` in the binary), and herdr-orchestration `SKILL.md:18-20` sends task briefs over SendMessage.
  - I did not verify whether a `claude -p` child can reach a live session that way.
  - Cheap insurance: drop `CLAUDE_CODE_MESSAGING_*` in `child_env`, and disallow `SendMessage` and `ListAgents` in the two herdr cases.
- **N4. Two pins to keep clear of.**
  - Task 1 Step 1's Stops assertion ("names no execution-mode choice") trips if R8's own sentence, "The execution-mode choice is no longer a stop", lands in Stops. Put that sentence in Execution mode, or pin the offer rather than the noun.
  - `commands/plan-review.md` is checked against `test_close_wiring.py:8-9`'s STALE list, so the `:42` rewrite must not say "implementer".
- **N5. Test map row 3.**
  - "Passes rules the baseline fails" is the existing format's bar, but it lets skill-on fail an R-rule. State the bar: skill-on passes every rule from H29 on, and the baseline fails at least one.
  - `RUNBOOK.md:28-30` saves outputs to `~/.claude/plugins/netdust-core/evals/outputs/`, which is a symlink into the 0.5.2 cache. Writing there contradicts "never the plugin cache". Keep the outputs in the scratchpad or the report.
- **N6. R9's ledger in the recipe.** Round 2's N9 is half closed. The fallback now keeps "the same ledger of every exchange", but Task 3 Step 2 still names the ledger only for the restart. Add a bullet: the ledger holds the brief, the rulings, the fix requests and their closing tests.
- **N7. Reading an eval failure.** If `--plugin-dir` does not shadow the installed gates 0.10.0 (`installed_plugins.json`), the old Execution mode text also competes in the eval. I did not verify which one takes precedence. Name it beside core 0.5.2 and §2.
- **N8. The sparring draft lives in /tmp.** Task 1 Step 2 points at `spar-1.md` §7, which sits in a `/tmp` session scratchpad that a reboot loses. Copy §7 into `specs/two-session/`, or drop the pointer.
- **N9. Trigger words.** herdr-orchestration's description is already 1,412 characters. Put "coder session", "two sessions" and "pair" early, not at the tail.
- **N10. R1's bounded exception has no eval under herdr.** Optional: give `small-tweak-no-artifacts` `env: {"HERDR_ENV": "1"}`, the stub, and `absent: [".herdr/agent-start"]`.
- **N11. Simplest design.** It is stated honestly, and its four holes hold against source: `run-evals.py:54-57`, `feature-review.md:25`, laika `bin/gate.sh:19-20`, and recursion by construction. I found no simpler design.

## Round 2, closed or not

- **B1 (red suite):** closed.
  - `env -u NETDUST_GUARD_ASK` is in Test map rows 1–2, Task 1 Steps 1 and 4, Task 2 Steps 1 and 3, and Close 1, and there is a Global Constraint for it.
  - My run: 20/20 green with it; without it, 19/20 with 22 FAIL lines.
- **S1 (no-recursion cannot fail):** closed. The case has the env and the stub, and only the stub writes `agent-start`. A new defect in the same case is this round's S2.
- **S2 (named sessions):** closed.
  - `run_case` runs the probe.
  - `--disallowedTools` covers the three flags.
  - Review Focus 1 names the socket path.
  - The dead socket is confirmed by probe.
  - The proxy caveat is N2 here; the remaining routes are N3.
- **S3 (pilot review without the plan):** closed in substance. The review runs the branch's text and checks the "plan or none" line. The ref it names does not exist yet (this round's S1).
- **Notes:**
  - N1 and N3–N8: closed.
  - N2 and N9: half closed (N1 and N6 here).
  - N10: acknowledged in Task 1 Interfaces.
  - N11: still stands.

## Premises checked
- The gates suite is green with `env -u NETDUST_GUARD_ASK` and red without → `run.sh` (20/20; 19/20 with 22 FAIL), `tests/test_pretooluse_guard.py:66`, `hooks/pretooluse-guard.py:431-436`, session env `NETDUST_GUARD_ASK=off` → holds
- The devops suite is green → `plugins/netdust-devops/tests/run.sh` → holds
- The policy is 142 lines and the cap is `< 150` → wc, `tests/test_policy_skill.py:42` → holds
- "Stefan chooses at the plan handoff" and "execution-mode choice" → `skills/policy/SKILL.md:98`, `:106` → holds
- Other tests pin Stops tokens → `test_close_wiring.py:60`, `:70`; `test_policy_skill.py:28` → holds
- A command test reads `feature-review.md`, and no test pins prose → `test_close_wiring.py:55-58`; `test_session_commands.py:7` → holds
- `/feature-review` takes the head from origin, else the local branch; the plan comes from the working tree; the summary has a "plan or none" line → `commands/feature-review.md:12-13`, `:25`, `:38` → holds
- `plan-review.md` offers the execution mode → `commands/plan-review.md:42` → holds
- The stale-offer grep's hits today → `SKILL.md:96`, `:98`, `:106`; `plan-review.md:42`; none in core or devops → holds
- The gates boundary bans implementer / test-author / reviewer agents → `plugins/netdust-gates/CLAUDE.md:22-24` → holds
- Gates spec R3 is at `:68` and R5 at `:81`; the precedent `5c01115` sits under R1 → `specs/netdust-gates/spec.md`, `git show 5c01115` → holds
- Versions are gates 0.10.0, core 0.5.3, devops 0.9.5, in both manifests; drift fails both suites → `plugin.json`, `.claude-plugin/marketplace.json`, `test_plugin_manifest.py:22-24`, `test-marketplace.sh:33-42` → holds
- The main checkout's uncommitted core `plugin.json` claims 0.5.4 → `git diff` there → holds
- The branch is cut from `origin/main`, and the main checkout has no `specs/two-session/` → merge-base `1c2c402`, `ls` → holds
- The cache holds gates 0.10.0 @ `5915dca` and core 0.5.2 → `installed_plugins.json`, `~/.claude/plugins/*` symlinks → holds
- `origin/feature/two-session` exists for Close step 2 → `git branch -a` → does not hold (S1)
- Every worktree of this repo shares its refs → `git rev-parse --git-common-dir` → holds
- The runner inherits the caller's environment, runs only `git init`, hardcodes `--max-turns 25`, and `timeout` is an existing key → `run-evals.py:51-57`, `cases.json` (two cases carry `timeout`) → holds
- `run-evals.py` imports without running → `__main__` guard at `:85` → holds
- The existing keys can express negative checks → `run-evals.py:35-41`, `:65-68`; negative lookaheads in `review-fix-no-report` and `unit-cut-plan` → holds
- The coder in `coder-brief-no-recursion` edits the target in place → `init.defaultBranch` unset, `executing-plans/SKILL.md:112-113`, `using-git-worktrees/SKILL.md:41` → does not hold (S2)
- herdr 0.9.5 syntax: `agent start <NAME> --kind --pane [-- AGENT_ARG…]`, `agent prompt <TARGET> <TEXT>`, `agent wait <TARGET>` → `--help` → holds
- `--session`, `--machine` and `--remote` are global flags; 20 named sessions exist → `herdr --help`, `~/.config/herdr/sessions/` → holds
- `herdr --skill` does not document `HERDR_SOCKET_PATH`; the binary reads it, along with `HERDR_SESSION` and `HERDR_CLIENT_SOCKET_PATH` → grep of `--skill`, binary strings → holds (N3)
- `notify_when_idle` is a real mechanism → Claude CLI binary (uds-messaging), not herdr → holds
- `~/.profile:25-26` prepends `~/.local/bin` → not re-read (the sandbox denied it); carried from round 2
- herdr-orchestration's detection, experiments-on-own-session and no-laundering rules → `SKILL.md:13`, `:102-103`, `:126-128` → holds
- The scenario format, rules H1–H28, and skill-on reading the repo-relative `SKILL.md` → `evals/scenario-1..5-*` → holds
- The leg and judge procedure → `plugins/netdust-core/evals/RUNBOOK.md:17-38` → holds; its outputs path resolves into the cache (N5)
- parallel-work has no DDEV section → `parallel-work/SKILL.md` (127 lines) → holds
- laika-planning-model's `.ddev/config.local.yaml` is `name: laika-planning`, and git ignores it → the file, `.ddev/.gitignore:17` → holds
- laika's gate runs `test:int` in the container → `bin/gate.sh:19-20` → holds
- The DDEV name alone sends the gate's browser tier to the worktree → `bin/e2e.sh:17-21`, `:55`; `config/application.php:51`, `:76-77` → holds for `test:int`; for e2e, only if the URLs are rewritten (B1)
- Seeding "through the project's own verb" gives the worktree a database of its own → `wp.mk:70-77`, `:186`, `:200`; laika `site.yml:135-136` → does not hold (B1)
- `make e2e` runs against a local container → `Makefile.netdust:491-496` → does not hold (B1)
- Upstream `writing-plans` asks the execution question unless a method was supplied → superpowers 7.0.0 `writing-plans/SKILL.md:181-186` → holds
- Upstream's ledger lives in the worktree and is deleted after the final review → `executing-plans/SKILL.md:103-104`, `:121-131` → holds
- Stefan's global `CLAUDE.md` §2 carries the execution-mode line → holds
- The repo has no `ARCHITECTURE-INVARIANTS.md`, and netdust-core has no `tests/` → `find`, `ls` → holds
- The sparring draft exists → session scratchpad `two-session/spar-1.md` §7 → holds, but it is ephemeral (N8)
