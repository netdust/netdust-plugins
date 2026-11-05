# Plan review — exposure-probe (plan 1 of the security-checks set), round 2
Reviewed-plan: dfa71655ddb17a965ce52f5afe23579c5c75cbdb /home/ntdst/Projects/netdust-plugins/specs/exposure-probe/plan.md
Verdict: ready with fixes

Round 1 (1 Blocking, 5 Should fix, 5 Note; kept in git at commit 11d9f3e) is replaced by this round.

Round 1's eleven findings are all answered, and each answer holds in source (list at the end). What this round adds is three things the fixes introduced or exposed, verified by running them rather than reading them: the first `make health` end-to-end test can hang the suite, the unreachable fixture address does not refuse on this host, and one claimed test does not exist. None is a false premise about the codebase, so nothing is Blocking.

## Blocking

None.

## Should fix

**S1 — Task 2 Step 1: the `ssh` stub shape decides whether `make health` end to end terminates.** The step says "Drift is not exercised: it would need `rsync` stubbed too". Drift IS exercised: `health` runs every section unconditionally (`plugins/netdust-devops/dist/Makefile.netdust:686-707`), the fixture's `deploy.payload: [app/plugins/p]` is committed (`tests/test-makefile.sh:191,204`), so `git archive` finds the directory and real `rsync -e "ssh -q"` runs against the stub. Measured here: a stub whose default branch reads stdin (the shape of the suite's `$CLI/bin/ssh`, `test-makefile.sh:543`) hangs rsync — `timeout 15` fired, rc 124; a stub that opens with `exec < /dev/null` (the disk test's shape, `test-makefile.sh:1216`) returns in 0 s with rc 12 and Drift prints `clean`. The suite's own comment at `test-makefile.sh:534-537` documents exactly this hazard. Smallest change: the step names the stub's first line `exec < /dev/null`, wraps the `make health` call in `timeout 60` (the suite already does `timeout 20 make ship`, line 228), and drops the "not exercised" parenthetical — Drift runs and prints `clean`.

**S2 — Task 1 Step 1 `testUnreachableIsYellowNotGreen` / Step 3's per-environment loop: `http://127.0.0.1:1` does not refuse on this machine.** WSL2 forwards loopback ports, so curl waits the full `--max-time`: measured 8.0 s, exit 28, `000` (`127.0.0.2:1` refuses in 0 ms). With the loop as written — control, then eight defaults, no short-circuit — the test costs 9 × 8 s = 72 s per unreachable environment (144 s if both are at `:1`), and a real `make health` against a site that is down costs (9 + up to 20) × 8 s on the Exposure section alone, against R1's "the timeout is short" and the suite's own standard, "a dead host must answer unreachable, never hang health" (`test-makefile.sh:1232`). Smallest change: in Step 3, when the control answers `000`, print `<env>  unreachable` and move to the next environment (one line per environment, as `_health-disk` prints one per host), so an unreachable environment costs one timeout; optionally also `--connect-timeout 3` on the curl call. The short-circuit narrows R1's "one HEAD request per path" for the unreachable case only — Stefan's ruling, but the test should not go in at 72 s either way.

**S3 — Threat model mitigation 1 is half-driven.** It covers `url` and a path; `testHostilePathsAreSkipped` sends hostile paths only. No test sends a hostile `url` through `valid_url()`. Smallest change: one more environment in the same fixture copy, `url: "http://127.0.0.1:1/;touch $WORK/exposure/pwned-url"`, asserting a skipped line naming the environment, no request, and the file absent.

**S4 — Global Constraints "Release: … `dist/VERSION`, agreeing (`tests/test-marketplace.sh`)" and Test map row 3: the test does not read `dist/VERSION`.** `test-marketplace.sh:24-36` compares each plugin.json with its marketplace entry; a grep over `tests/` for `VERSION` finds nothing. `dist/VERSION` is what `devops-version` compares the stamp with (`dist/scripts/devops-version:69,113`): a forgotten bump makes every project report "current" and never prompts `make devops-update` — the same shape as round-1's B1, the release reaches no project. Smallest change: one assertion in the structure section of `test-makefile.sh` (or in `test-marketplace.sh`): `dist/VERSION` equals the version in `plugins/netdust-devops/.claude-plugin/plugin.json`.

## Note

**N1 — Task 1 Step 1, the port parse.** Holds (verified: `php -S 127.0.0.1:0` prints `PHP 8.3.6 Development Server (http://127.0.0.1:45167) started` as its first stderr line), but the step must wait for the line before parsing it — poll the log file, not a bare read after the `&`.

**N2 — Task 2's fix hint names `location ^~ /app/logs/` literally and the test pins it.** A `custom-site`/stackedWP project serving `/wp-content/logs/index.html` is told to deny `/app/logs/`. The script knows the served path; the hint can say "deny the directory that was served, e.g. …". Not a spec gap — R3 asks for "the ^~ deny rule" — but the one-size rule will mislead the half of the fleet it does not match.

**N3 — `[::1]:1` is not an option for S2.** The url regex `^https?://[A-Za-z0-9._:/@%~-]+$` rejects brackets; `127.0.0.2:1` passes it and refuses instantly on Linux (all of 127/8 is on `lo`; on macOS only `.1` is).

**N4 — Simplest design.** The paragraph is now honest (round-1 N1): `_health-disk` is tested directly (`test-makefile.sh:1222`); the reasons left — `$$`-escaped readability, a standalone runnable for the first working version — hold. No simpler design was missed.

**N5 — Eval coverage.** `plugins/netdust-gates/tests/test_evals_shape.py` validates only gates' own `evals/`; nothing validates a devops eval file's shape. The Test map row 3 does not claim it does, so this is only a heads-up: the new case is checked by eye.

## Premises checked

- "closed `MANAGED` array, lines 23-39; `cmd_update` copies only what is listed" → `dist/scripts/devops-version:23-39,115-122`; stamp lists `sum  file` at 124-128 → holds
- "`bin/new-project` scaffolds through the same `--update`" → `bin/new-project` (`NETDUST_DEVOPS_DIST="$DIST" scripts/devops-version --update`, ~line 202) → holds
- "`tests/test-makefile.sh` asserts no backticks in recipe lines" → `test-makefile.sh:16-23` → holds
- "`_health-disk` is tested directly" → `test-makefile.sh:1222` → holds
- "line 140 guards php with a named skip" → `test-makefile.sh:140` → holds
- "the suite has one cleanup trap, so a second `trap … EXIT` replaces it" → `test-makefile.sh:186`, the only `trap` in the file → holds
- "`── vendoring ──` near line 507" → 507 → holds
- "new section before `── first bring-up ──`" → 1250; cwd is `$P` there (`cd "$P"` at 1207; the D2 run at 1243 is a subshell) → holds
- "`scripts/site` prints one list item per line; exits 1 on a missing key" → `dist/scripts/site:8-9,31-33,43-45`; also exits 1 on an empty value (36-37) → holds
- "`SITE` is a make variable, not exported; the recipe passes it" → `Makefile.netdust:69`; the allowlist refuses `SITE=` on make's command line only (`test-makefile.sh:598-612`), an env assignment to `bash` on a recipe line is not that → holds
- "colours red/green/yellow as the Makefile's" → `Makefile.netdust:85-89` → holds
- "the `health` line in `help`" → `Makefile.netdust:130` → holds
- "`health` ends with `_health-disk`; every other section exits 0" → 749; each recipe line's last command is an `if`/`for`/`echo` returning 0, `git fetch … || true` → holds
- "a new `_health-exposure` target after `_health-disk`" → 753-767 → holds
- "`php -S 127.0.0.1:0` picks a port and logs it" → run live, PHP 8.3.6 → holds
- "`curl … -w '%{http_code}'` prints `000` when it fails" → run live → holds
- "a router answering 405 on HEAD and 200 on GET" → run live through `-I` then plain → holds
- "`http://127.0.0.1:1` is unreachable" → `000`, but after 8 s not 0 ms on this WSL2 host → holds as a class, does not hold as "short" (S2)
- "Drift is not exercised in `make health`" (Task 2 Step 1) → `Makefile.netdust:686-707` runs unconditionally; measured hang with a stdin-reading stub → does not hold (S1)
- "`tests/test-marketplace.sh` (versions agree)" for `dist/VERSION` → `test-marketplace.sh:24-36` reads plugin.json and marketplace only → does not hold for VERSION (S4)
- "the `devops` skill's health paragraph near line 140" → `skills/devops/SKILL.md:140-143` → holds
- "`site.yml.tmpl`: a commented example beside `health.markers`" → `templates/site.yml.tmpl:124-128` → holds
- "`wp-infra`'s Logs paragraph; the `^~` fix already on `main`, unreleased" → `plugins/netdust-wp/skills/wp-infra/SKILL.md:54-70`; commit 926d41e is after the 1.4.0 release 4c55e92 → holds, 1.4.1 is right
- "eval shape `id`, `skill`, `skill_path`, `query`, `signature`" → `evals/devops-agent-staging-verbs-2026-10-27-cases.json` → holds
- "0.13.0 → 0.14.0 in three places; wp 1.4.0 → 1.4.1 in two" → `plugin.json`, `marketplace.json`, `dist/VERSION` all 0.13.0; wp both 1.4.0 → holds
- "the description texts differ today, so each is edited on its own" → devops 10081 vs 13205 chars, wp 4622 vs 4428 → holds
- "`~/Sites/netdust` has `scripts/site` and a `site.yml` with urls" (Step 5) → both present, staging and production urls set → holds
- "the template sweep's forbidden strings" are `BR_INTEG`/`make release` (`test-makefile.sh:51`) → a `health.deny_paths` comment is clear of them → holds

Round-1 fixes, ground-truthed: B1 (MANAGED) → Task 1 Files + `testANewScriptIsVendoredAndChecksummed`, holds. S1 (no existing stub) → own stub, holds but see S1 above. S2 (trap) → re-armed, holds. S3 (fixture urls) → all 127.0.0.1, holds but see S2 above. S4 (no body) → marker assertion, holds. S5 (classifier default) → `*) not conclusive`, holds. N1–N5 → all landed, each verified above.

## The cut

- `exposure-probe` → **one feature**. Shares no file with `core-lint-gate` (ntdst-core, R5–R8, unwritten); buildable and testable on its own branch; R1–R4 owned here and nowhere else, R5–R8 owned there and nowhere else, no requirement double-owned, none orphaned. netdust-wp's 1.4.1 rides in the same repo and branch, which is right: R4 names the wp-infra pointer.

## Applied after the review (by the planning session, not the reviewer)

No Blocking finding, so no re-review was run; the plan's blob moved from `dfa71655ddb17a965ce52f5afe23579c5c75cbdb` to `75a7b8db7a5c7a4d52b1ee0eb9b17eb45a5fa60c`. All four Should fix items and the notes that change the plan were applied:

- S1: Task 2's end-to-end test brings an `ssh` stub whose first line is `exec < /dev/null`, wraps `make health` in `timeout 60`, and expects Drift `clean` and Patch-gone red.
- S2: the control request answering `000` ends an environment at one line, `unreachable`; `--connect-timeout 3`; the unreachable fixture is `http://127.0.0.2:1`. This narrows R1's "one request per path" for the unreachable case only (a site that is down costs one timeout, not nine); it is named in the plan's Global Constraints for Stefan.
- S3: a hostile-`url` environment and `testHostileUrlIsSkipped`.
- S4: an assertion that `dist/VERSION` equals `plugin.json`'s version, written first in Task 3 (Step 2a), and Test map row 3 corrected.
- N1: the port is read by polling the log file. N2: the fix hint says to deny the directory that was served, with `/app/logs/` as the example. N3: noted in the threat model (no IPv6 literal). N5: the eval file is checked by eye; nothing validates a devops eval's shape.
