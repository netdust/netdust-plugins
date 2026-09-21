# WordPress constraints pack

Read by `netdust-gates:policy` when the project is WordPress. **Global Constraints** is copied
into the plan verbatim; **Plan shape** steers the tasks. Each line points at the skill that
owns the rule — read that skill, do not paraphrase it here.

## Global Constraints (copy verbatim)

- Base: ntdst-core is the framework base and its layering applies to every new class —
  `netdust-wp:ntdst-framework`; where files live — `netdust-wp:ntdst-patterns`.
- Golden path: the plan names the slice this feature is built to (`netdust-wp:ntdst-patterns`
  → `golden-paths/`); every departure from it is named and justified, or `none`.
- Security: every data flow (AJAX action, REST route, form post, shortcode attribute,
  settings save, custom query) states its four pillars — validate, sanitize, escape,
  authorize — as `netdust-wp:wp-security` defines them; a pillar that does not apply is
  written `n/a — <why>`, never omitted.
- Drift: nothing `netdust-wp:ntdst-drift-reviewer` reports — the review checks the diff
  against this list, so a departure is a named deviation or a defect.
- Tests: the close is `make gate`. Unit = Brain Monkey, integration = wp-phpunit through
  DDEV, e2e = Playwright; commands and setup are `netdust-wp:wp-testing`'s.
- Local and ship: DDEV always; the Makefile is the only route to a server
  (`netdust-devops:devops`); anything that must ship names its `deploy.payload` path.

## Plan shape

- Each data flow gets a task whose test drives the **denial** — the unauthorized actor
  refused, the missing nonce rejected — not only the happy path.
- A user-facing WP screen is a `browser` flow for the shake-out; its login recipe is
  `netdust-wp:wp-testing`'s. Name the screen in the plan so `/shakeout` finds it.
- Third-party code (plugins, mu-plugins, WP core) is outside `deploy.payload`: a patched file
  there is declared in `health.markers`, or the next update silently reverts it.
