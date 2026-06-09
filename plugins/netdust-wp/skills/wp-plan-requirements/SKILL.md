---
name: wp-plan-requirements
description: Use when WRITING A PLAN OR SPEC for any non-trivial WordPress feature in a Netdust project — fired by netdust-agent:harnessed-development Stage 1 on WP projects, the way threat-modeling and architecture-invariants fire. Injects mandatory plan sections so WP-security (the four pillars) and ntdst-core framework patterns (the drift categories) are REQUIREMENTS IN THE PLAN, gated per-task, not just findings a reviewer catches at the end. Triggers when designing a feature that adds AJAX/REST handlers, form processors, admin pages, shortcodes, custom queries, Services/Repositories/Handlers, CPTs, or any module under mu-plugins. Activates on keywords plan, spec, task breakdown, WordPress feature, ntdst-core module, Service, Repository, AJAX, REST endpoint. Symptoms include "write a plan for the X feature", being at the plan stage of harnessed-development on a WP project, or about to break a WP feature into tasks. Do NOT skip because "the reviewers will catch it" — the whole point is to move the requirement UPSTREAM into the plan so review converges in one round.
---

# WP Plan Requirements

**The reviewer is the last line, not the first. This skill makes WP-security and ntdst-core patterns a plan-time requirement, so the code is built right — not just caught wrong.**

This is the WordPress sibling of `netdust-agent:threat-modeling`. Threat-modeling injects a `## Threat model` section into the plan before task breakdown; this skill injects WP-specific requirement sections into the plan before task breakdown. Same mechanism (fired from `harnessed-development` Stage 1 by the stack-override rule), same payoff: the requirement is named in the plan, so `/code-review` and `ntdst-drift-reviewer` verify against a named list instead of hunting free-form — converging in one round instead of probabilistically over many.

It does NOT replace the review-time checks. It **front-loads** them so the same list is enforced at both ends.

## When this fires

`harnessed-development` Stage 1, on a WordPress project, for any feature that touches a user-facing data flow OR adds framework classes. If the feature is a trivial copy/content change with no PHP logic, skip — there is nothing to require.

## What to inject into the plan

Add these three blocks to the plan **before task breakdown is finalized**. They change what tasks the plan contains.

### Block 1 — `## WP security requirements (per data-flow)`

Enumerate every user-facing data flow the feature introduces (each AJAX action, REST route, form post, shortcode attr, admin-settings save, custom query). For each, write one line naming the **four pillars** it must satisfy. The pillars and the exact sanitize/escape/authorize functions are defined in **`netdust-wp:wp-security`** — reference it, do not restate the tables here. The plan line names *which* pillars apply to *that* flow.

Shape (one line per flow):

```
## WP security requirements (per data-flow)
- [ ] AJAX `save_order`: nonce (check_ajax_referer) + current_user_can('edit_shop_orders')
      + sanitize ($_POST→wp_unslash→sanitize_text_field/absint) + $wpdb->prepare on the write
      + esc_html on any echoed result
- [ ] REST GET `/v1/orders`: permission_callback (not __return_true) + absint on id param
      + esc_url_raw on any stored URL
- [ ] Shortcode `[order_status]`: escape on output (esc_html) + validate the id attr
```

Every flow MUST account for all four pillars (validate / sanitize / escape / authorize) — if one doesn't apply, say so explicitly (`escape: n/a — no output`), never silently omit it. A missing pillar in the plan is the bug, pre-shipped.

### Block 2 — `## ntdst-core layering requirements`

List the framework-pattern obligations the feature's new classes must meet. This list is the **same nine drift categories** the `ntdst-drift-reviewer` agent checks — so plan-requirement and review-check are one list fired at two ends. The canonical category definitions live in `netdust-wp:ntdst-architecture` (`references/anti-patterns.md`) and the drift-reviewer agent; reference them, don't restate.

```
## ntdst-core layering requirements
- [ ] Data access goes through a Repository — no direct `ntdst_data()->get(...)` outside *Repository.php
- [ ] No pure pass-through Service methods (Service adds validation/transformation/events, or callers use the repo)
- [ ] No raw `wp_ajax_*` handlers — register through the framework's AJAX/Handler layer
- [ ] No `ob_start()+include` rendering — use the framework's templating
- [ ] No swallowed `WP_Error` — propagate or handle explicitly
- [ ] Data API vocabulary is registered (WP_COLUMNS) — no unregistered keys
- [ ] No hardcoded meta prefix — use `$this->repository->getMetaPrefix()`
- [ ] Correct module layering (Modules / Handlers / Admin / Integrations / Contracts / Domain / Infrastructure)
- [ ] Service lifecycle / DI per NTDST_Service_Meta (see ntdst-architecture)
```

Keep only the rows that apply to what the feature actually builds; delete the rest so the list is real, not boilerplate.

### Block 3 — per-task acceptance line

Every module-touching task in the breakdown gets this acceptance criterion, so the drift categories gate **task close**, not only shake-out:

```
Acceptance: drift pre-check clean — `/drift-reviewer <touched path>` returns no findings
(the nine categories), and the per-flow security line above is satisfied in the diff.
```

## The convergence contract

State this in the plan once, under the blocks:

> These three blocks are the convergence target for `/code-review` and the
> `ntdst-drift-reviewer` at shake-out. Reviewers verify the diff against the
> named pillars + categories above, not free-form — a gap is a one-line finding
> keyed to a named item, not a re-discovery.

That sentence is what earns the one-round convergence. Without a named target, review reverts to probabilistic hunting.

## What this skill is NOT

- Not a restatement of `wp-security` or the drift categories — it **references** them so they stay single-source. If you find yourself pasting the sanitize/escape table, stop and link instead.
- Not a review step — it runs at plan-time. The review step is `ntdst-drift-reviewer` + WP `/code-review` at Stage 3.
- Not for trivial/no-PHP changes — skip when there is no data flow and no new framework class.

## Integration

| Skill / agent | Relationship |
|---|---|
| `netdust-agent:harnessed-development` | Fires this at Stage 1 on WP projects via the stack-override rule (sibling to threat-modeling). |
| `netdust-agent:threat-modeling` | The general-purpose twin; this is the WP-specific plan injector. Both run at Stage 1; they compose. |
| `netdust-wp:wp-security` | Canonical source for the four pillars + sanitize/escape/authorize functions. Block 1 references it. |
| `netdust-wp:ntdst-architecture` / `ntdst-data` / `ntdst-patterns` | Canonical source for the layering/Data-API/Service-lifecycle rules. Block 2 references them. |
| `ntdst-drift-reviewer` (agent) | The review-time enforcer of the same nine categories Block 2 names. Plan-requirement ↔ review-check are one list. |
