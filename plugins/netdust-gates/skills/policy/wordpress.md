# WordPress constraints pack

Read by `netdust-gates:policy` when the project is WordPress. **Global Constraints** — the
lines and the red flags — is copied into the plan verbatim; **Plan shape** steers the tasks.
Each line names the skill that owns the rule and the evidence that proves it; read that
skill, do not paraphrase it here.

## Global Constraints (copy verbatim, red flags included)

- Evidence: no task claims a line below without its evidence in the task report — the
  command as run with its output quoted, or the review that owns the line. No quote, not met.
- Base: ntdst-core is the framework base and its layering applies to every new class —
  `netdust-wp:ntdst-framework`; where files live — `netdust-wp:ntdst-patterns`. Owned by the
  whole-branch review, joined on WordPress by `netdust-wp:ntdst-drift-reviewer` on the changed
  paths (Part 1 runs core's invariants live); its `## Findings:` header is quoted.
- Golden path: the plan names the slice this feature is built to (`netdust-wp:ntdst-patterns`
  → `golden-paths/`); every departure from it is named and justified, or `none`. Judged, not
  grepped: `/plan-review` checks the slice is named, the whole-branch review that code keeps it.
- Security: every data flow (AJAX action, REST route, form post, shortcode attribute,
  settings save, custom query) states its four pillars — validate, sanitize, escape,
  authorize — as `netdust-wp:wp-security` defines them; a pillar that does not apply is
  written `n/a — <why>`, never omitted. Evidence per flow: each pillar cited `file:line`; the
  output of `grep -nE "current_user_can|wp_verify_nonce|check_ajax_referer|check_admin_referer|permission_callback" <changed files>`;
  the denial test's name, RED then GREEN. `security-sentinel` owns the review when the plan
  carries a threat model.
- Drift: nothing `netdust-wp:ntdst-drift-reviewer` reports — a Critical or Drift finding is
  fixed or is a deviation the plan names; the review quotes the agent's findings, never "looks clean".
- Tests: the close is `make gate`. Unit = Brain Monkey, integration = wp-phpunit through
  DDEV, e2e = Playwright; commands and setup are `netdust-wp:wp-testing`'s. Evidence: the exit
  code and the summary lines of a run after the task's last edit. A tier that did not run is
  reported as not run, never as a pass.
- Local and ship: DDEV always; the Makefile is the only route to a server
  (`netdust-devops:devops`); anything that must ship names its `deploy.payload` path, and
  `make deploy-test env=staging` output listing it is quoted. An rsync, scp or SFTP to a server
  outside the Makefile is a defect the review reports.

| Red flag — the excuse | The answer |
|---|---|
| "Admin-only screen, so no nonce" | Capability says who; the nonce says they meant it. Both. |
| "The value comes from the database" | Stored input is input. Escape it on output. |
| "The reviewer will catch it" | The reviewer checks the evidence you quoted. No quote, not met. |
| "`make gate` was green earlier" | Earlier is not after your last edit. Run it, quote it. |
| "The integration tier needs DDEV; skip it" | `ddev start`. A tier not run is not a pass. |
| "Plain WordPress is simpler here" | On ntdst-core that is drift. Use the framework's door or name the deviation. |
| "Too small for the golden path" | Then the departure is `none` or one named line. Silence is the defect. |
| "The denial is obvious, no test needed" | Obvious is untested. Write it RED first. |
| "Just rsync this one file" | A hand-deploy is drift nobody sees. The Makefile, or nothing. |

## Plan shape

- Each data flow gets a task whose test drives the **denial** — the unauthorized actor
  refused, the missing nonce rejected — not only the happy path.
- A user-facing WP screen is a `browser` flow for the shake-out; its login recipe is
  `netdust-wp:wp-testing`'s. Name the screen in the plan so `/shakeout` finds it;
  `bin/shakeout-check.py` exiting 0 is its evidence.
- Third-party code (plugins, mu-plugins, WP core) is outside `deploy.payload`: a patched file
  there is declared in `health.markers`, or the next update silently reverts it. `make health`
  finding the marker on each environment is its evidence.
