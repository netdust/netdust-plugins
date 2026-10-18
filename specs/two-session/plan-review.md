# Plan review — two-session
Reviewed-plan: 4ecece93deaaf92141d9fd9fad97fb8e8deaac79
Verdict: ready

Round 3's B1 and S1 are closed. S2 is half closed: the sandbox now ends on a feature branch, but the coder's prompt still does not say it should work in place, so upstream's worktree step can still stop the case.

I found no new Blocking finding in the parts that changed: Task 4, Review Focus 6, the Close, Task 2's interfaces and stub, and Task 3's bullets. Three Should fix items and six notes go to Stefan.

No plugin file has changed since round 3 (`git diff 38cf08c HEAD` touches only `specs/two-session/`), so round 3's suite runs still stand. I did not run them again, and I ran no evals.

## Blocking

None.

## Should fix

**S1. `coder-brief-no-recursion` can still stop at upstream's worktree step (round 3 S2, second half).**
- Plan:
  - Task 2 Interfaces, `prepare_sandbox`: "so a coder that follows `superpowers:executing-plans` is not on a main branch".
  - Task 2 Step 2, the second case: "a prompt opening `Role: coder` with a one-task plan".
  - Task 2 Step 1: "`prepare_sandbox` with `commit: true` leaves a valid `HEAD`".
- Source:
  - **The branch fix answers only one rule.** executing-plans' Setup sends every executor through `using-git-worktrees` "to create one or verify the existing one" (`executing-plans/SKILL.md:108-111`, superpowers 7.0.0). The branch fix answers only `:112-113`.
  - **The consent question.** In a normal checkout (`GIT_DIR == GIT_COMMON`), `using-git-worktrees/SKILL.md:39-45` asks consent before creating a worktree, unless the instructions declare a preference. The sandbox is a normal checkout (`run-evals.py:51`).
  - **Routes to a second tree.** The CLI ships an `EnterWorktree` tool (binary strings, 2.1.302), and `Bash(git *)` allows `git worktree add`.
  - **The policy pushes that way.** Its new Execution mode tells a coder it runs in its own worktree, which makes creating one more likely.
- Effect: the case fails for a reason unrelated to recursion, which is round 3's S2 again. Either:
  - the coder asks, the reply ends and the target is unchanged; or
  - it creates a worktree and edits there, and the root target is unchanged.
- Change:
  - The prompt says: "This checkout is your worktree, on `feature/coder-brief-no-recursion`; work in place." That is the declared preference `:45` honours.
  - Step 1 asserts that `prepare_sandbox` leaves the sandbox on `feature/<case-id>` (or `branch`), not only that `HEAD` is valid.
  - Optional: add `EnterWorktree` to this case's disallowed tools.

**S2. `two-session-handoff`'s "target unchanged" check cannot see the worktree the stub now creates.**
- Plan, Task 2 Step 2:
  - the stub bullet: "on `worktree create`, runs a real `git worktree add` under `$EVAL_ROOT`";
  - the first case: "Expect the target file unchanged".
- Source:
  - `run-evals.py:35-41` reads `where` relative to the sandbox root, and `plan` globs only `specs/**/plan.md` under root.
  - `prepare_sandbox` commits the target on `main`, so a worktree cut from `main` carries a copy of it.
  - The stub answers `agent wait` as settled and does no work. A thinker can find the coder idle and implement in the worktree itself. `calls.log` still shows `agent start`, and the root target is still unchanged.
- Effect: a thinker that breaks R2 ("only the coder writes the feature's tree") passes. Before round 3's N1 there was no second tree, so this blind spot arrived with that change.
- Change:
  - The stub puts the worktree at a fixed path under `$EVAL_ROOT`, for example `.herdr/wt`, and ignores `--path`.
  - The case adds an `expect` on `.herdr/wt/<target>` with a negative lookahead for the new value. It also passes when the file is absent. This is the `\A(?:(?!…).)*\Z` style `unit-cut-plan` already uses.

**S3. Task 3's Close-split bullet puts the last push before `/shakeout`.**
- Plan, Task 3 Step 2: "the Close split (R7): the coder pushes and signals, then the reviewer reviews; the coder pushes again after the fix pass".
- Source:
  - Spec R7 lists the coder's steps as "the fix pass, `/shakeout` and the push".
  - The policy's Close runs the fix pass (`skills/policy/SKILL.md:122`), then `/shakeout` (`:127`), then pushes and hands over `make promote` (`:134-135`).
  - `make promote` merges `origin/feature/<name>` (`Makefile.netdust:216-219`, `:224`).
- Effect: on user-facing work, a coder that follows the recipe pushes after the fix pass and then runs `/shakeout`.
  - The shake-out's committed tests and `specs/CHECKS.md` rows never reach origin, so staging and `make e2e env=staging` run without them.
  - The pilot has no shake-out, so only the recipe is affected.
- Change:
  - Say "the coder pushes again as its last step, after the fix pass and `/shakeout` (policy Close step 5)".
  - Name the reviewer's half of R7 in the same bullet: it carries the screenshot yield and hands Stefan `make promote`.

## Note

- **N1. Review Focus 6's proof on Bedrock.**
  - `wp option get home` goes through `option_home`, which returns `WP_HOME` when it is defined (`web/wp/wp-includes/default-filters.php:302`, `functions.php:4706-4710`). On Bedrock the proof checks `.env`, not the database rewrite.
  - Add a second proof: `ddev wp db search '<main host>' --all-tables` prints nothing.
  - In Task 4, give the documented `search-replace` the flags `_pull-db` uses (`--all-tables --precise --skip-columns=guid`, `wp.mk:201`). Without `--all-tables`, unregistered custom tables keep the main URL.
- **N2. A simpler design the plan did not weigh.**
  - `_pull-db` takes `LOCAL_URL` from `local.url` (`wp.mk:186`). If it took the container's `DDEV_PRIMARY_URL` first, `make pull` would be correct in a worktree, and the trap "never `make pull` without the rewrite" would go away. `make push` has the same issue (`wp.mk:127`, `:147`).
  - That is a code change plus a devops test, against R3's "Documented once". The documentation-only choice is defensible, but the plan should say it considered the alternative and rejected it.
  - Two more places still name `local.url` in a worktree: `make dev` prints it (`ddev.mk:16`), and devops `SKILL.md:368` says the URL comes from `local.ddev_project`. One pointer from `:368` to the new parallel-work section keeps "documented once" honest.
- **N3. The Ruling's reason.**
  - `bin/e2e.sh:55` is the reason for the URL rewrite, not for seeding.
  - The reason for seeding: the e2e tier creates its user and fixture through wp-cli (`:45-52`), so it needs an installed WordPress.
  - The same Ruling can also record that R3's "`make e2e`" never runs locally (`Makefile.netdust:491-496`).
- **N4. "How the worktree's project is started" says what, not how.** Name the concrete steps, in order:
  - `ddev start`;
  - `ddev composer install`;
  - a host `vendor/` and `node_modules` for Playwright, because laika's gate runs every tier but `test:int` on the host (`bin/gate.sh:6-9`, `:23`);
  - the worktree's own `.env`, before the gate. A fresh worktree has no `.env` (`.gitignore:21`), and Bedrock refuses to boot without `WP_HOME` (`config/application.php:51`).
- **N5. Task 2's tests for the changed interface.**
  - Step 1 asserts that no `HERDR_` value is left. It should also assert that no `CLAUDE_CODE_MESSAGING_` value is left.
  - It should also check that the stub's `worktree create` lands under `$EVAL_ROOT` and prints the path.
  - Both are one-line checks of behaviour the cases rely on.
  - The stub also needs an execution-time ruling for `--branch` equal to the sandbox's checked-out `feature/<case-id>`, because git refuses a branch that is checked out elsewhere.
- **N6. Round 3's N10 is not taken.** Running `small-tweak-no-artifacts` under `HERDR_ENV=1` is still optional. It is the only behavioural check of R1's bounded exception inside herdr.

## Round 3, closed or not

- **B1 (Task 4 seeding and URLs): closed.** Every point of round 3's change is in Task 4 Step 1:
  - it says "the gate's tiers" in place of `make e2e`, and names `make e2e env=<env>` as deployed-only;
  - it names the worktree's URL and the three places that still name the main one;
  - it sets `.env` to the worktree's URL, then exports, imports and runs `search-replace`;
  - it says never to run `make pull` without the rewrite;
  - it corrects the ruling's reason (N3 is a refinement).

  Review Focus 6 names the main URLs and the `option get home` proof (N1 is a refinement).
- **S1 (push before review): closed.**
  - Close step 2 pushes first, step 3 pushes after the fix pass, and Task 3's bullet says "the coder pushes and signals, then the reviewer reviews".
  - A push updates `origin/feature/two-session` in the refs every worktree shares (`--git-common-dir` is `/home/ntdst/Projects/netdust-plugins/.git`), so the reviewer's `git show` resolves.
  - The recipe's `/shakeout` order is this round's S3.
- **S2 (no-recursion on master): half closed.** `prepare_sandbox` ends on `feature/<case-id>`, and the `branch` key is added. The prompt still does not declare work-in-place, and Step 1 does not pin the branch (S1 here).
- **Notes taken:**
  - N1: real `git worktree add`; `Role: coder` matched anywhere in `calls.log`.
  - N2: the pair passes only when the same run's `calls.log` shows the stub.
  - N3: `CLAUDE_CODE_MESSAGING_*` stripped; `Bash(HERDR_*)`, `SendMessage` and `ListAgents` disallowed in every case. No existing case uses them.
  - N4: both pins, Task 1 Step 2.
  - N5: row 3's bar and outputs path.
  - N6: the ledger bullet.
  - N7: the installed gates 0.10.0 named.
  - N8: `specs/two-session/sparring-draft.md`, committed.
  - N9: the trigger words early in the description.
- **Not taken:** N10, which was optional (N6 here). N11 needed no change.

## Premises checked
- `make pull` pulls from a remote environment and rewrites to `local.url` → `plugins/netdust-devops/dist/mk/wp.mk:70-77`, `:186`, `:201` (the plan's `:200` is the echo just above it) → holds
- `make e2e env=<env>` drives only a deployed environment → `dist/Makefile.netdust:491-496` → holds
- The gate's local tiers find the container by cwd: `test:int` through `ddev composer`, the e2e base URL from `DDEV_PRIMARY_URL`, the fixture URL from WordPress → laika `bin/gate.sh:19-21`, `bin/e2e.sh:16-24`, `:55` → holds
- `test:int` runs against its own `wptests` database, made by a tracked post-start hook → laika `.ddev/config.gates.yaml`, `git ls-files .ddev` → holds (so seeding matters only to the e2e tier)
- `.env` is gitignored, and Bedrock requires `WP_HOME` and `WP_SITEURL` → laika `.gitignore:21`, `config/application.php:51`, `:76-77` → holds
- laika-planning-model's `.ddev/config.local.yaml` is `name: laika-planning` and is ignored → the file, `.ddev/.gitignore:17` → holds
- laika-planning-model's `.env` was set to its own URL → it is 27 bytes longer than laika's, three times "-planning" → consistent; the content was not read (the sandbox denies `.env`)
- `ddev wp option get home` resolves its path and, on Bedrock, prints `WP_HOME` → laika `wp-cli.yml` (`path: web/wp`), `default-filters.php:302`, `functions.php:4706-4710` → holds (N1)
- `scripts/site` reads only the tracked `site.yml`, with no local overlay → `dist/scripts/site:26` → holds (editing `site.yml` is not an option, and the plan rightly avoids it)
- laika's DDEV config claims no extra hostnames that a second project would collide on → `.ddev/config.yaml:7-8` → holds
- `/feature-review` changes nothing and takes the head from origin, else the local branch → `commands/feature-review.md:7`, `:12` → holds
- A push makes `origin/feature/two-session` visible to every worktree → `git rev-parse --git-common-dir` → holds; the ref does not exist yet, as expected before Close step 2
- `make promote` needs and merges `origin/feature/<name>` → `Makefile.netdust:216-219`, `:224` → holds (S3)
- The policy's Close orders fix pass, `/shakeout`, push → `skills/policy/SKILL.md:122`, `:127`, `:134-135` → holds (S3)
- An executor on a feature branch in a normal checkout proceeds without asking → `executing-plans/SKILL.md:108-113`, `using-git-worktrees/SKILL.md:39-45`, `run-evals.py:51` → does not hold without a declared preference (S1)
- Claude Code has the `SendMessage`, `ListAgents` and `EnterWorktree` tools → 2.1.302 binary strings → holds
- `CLAUDE_CODE_MESSAGING_SOCKET` and `_TOKEN` are set in this session and read by the CLI → env, binary strings → holds
- No existing case depends on `SendMessage` or `ListAgents` → `evals/cases.json`, 12 cases, none executes a plan → holds
- An expectation reads files relative to the root only → `run-evals.py:35-41`, `:65-68` → holds (S2)
- herdr 0.9.5 `worktree create` takes `--branch`, `--base`, `--path`, `--workspace` and `--cwd` → `herdr worktree create --help` → holds
- herdr-orchestration's description is 1,412 characters, and no test caps it → measured; grep of both suites → holds
- `SKILL.md:126-128` carries the no-laundering rule and "a peer's message is never operator approval" → holds
- `git init -b main` is available, `init.defaultBranch` is unset, a global identity is set, and there is no global `core.hooksPath` → git 2.43.0, `git config --global` → holds
- The installed versions are gates 0.10.0 @ `5915dca`, core 0.5.2 and devops 0.9.5 → `installed_plugins.json` → holds
- No plugin file has changed since round 3 → `git diff --stat 38cf08c HEAD` (only `specs/two-session/`) → holds; round 3's suite runs stand
- The sparring draft is committed in the spec folder → `git ls-files specs/two-session` → holds
