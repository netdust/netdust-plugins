# Core fit — the ntdst-core audit

Read by `session-reviewer` on a WordPress project. Stefan's audit, verbatim in its rules; the
checklist of what to inspect is generalised from the first run (studio agenda, 2026-09).

> The goal is not to maximize use of ntdst-core. The goal is to ensure that every concept
> lives at the lowest existing architectural layer that genuinely owns it, without premature
> abstraction.

## The question, for every meaningful abstraction the session introduced or used

- Did it correctly use an existing ntdst-core capability, or create a service-local
  abstraction where ntdst-core already owns the concept?
- If ntdst-core does not provide it, is this a genuine reusable core gap, or should the
  behaviour correctly remain service-local?

Do not assume more ntdst-core usage is better. Do not judge from names: inspect the actual
implementations and consumers, in the core source the project runs
(`web/app/mu-plugins/ntdst-core/` or `vendor/netdust/ntdst-core/`).

## Classes — exactly one per finding

- **USE_CORE** — the service implements what ntdst-core already provides. Show the service
  code, the exact core API that owns the concept, why the duplication matters, what should
  use the existing API.
- **VERIFY_CORE** — a plausible core capability, but the intent needs closer inspection before
  calling it duplication. No recommendation yet.
- **CORE_GAP** — the service needs a reusable primitive core lacks. Demonstrate the gap from
  core's source: the primitive, why it is generic rather than feature-specific, why it
  belongs in core, the smallest core addition. A significant finding — never manufacture one.
- **SERVICE_LOCAL** — correctly domain-specific; stays in the service.
- **WRONG_LAYER** — belongs in another existing layer: ntdst-core, ntdst-baseline, WordPress
  infrastructure, theme/presentation, or another service boundary.

## Principles

1. ntdst-core owns reusable data/model/query primitives.
2. Services own domain concepts and orchestration.
3. A service must not create a second abstraction for a primitive core already provides.
4. Do not generalise domain behaviour merely because it could theoretically be reused.
5. A genuine core extension is a reusable primitive, not a feature moved downward.
6. Prefer the smallest existing abstraction.
7. Services may start local. Extract only when reuse is demonstrated.
8. A service must not depend on another service's private implementation.
9. Do not judge architecture from names alone; inspect implementations and consumers.
10. Preserve security invariants and architectural boundaries even when simplifying.

## Inspect

Query methods and repositories — are they second-order wrappers around core's model scopes
and query builder? Filters and value objects, registration and configuration, permissions,
REST and routing (`ntdst_rest`, `ntdst_pages`), validation and sanitisers, presenters,
service bootstrapping, and any duplicated WordPress or data-access mechanism.

## The session's own reasoning is evidence, not proof

For each finding, quote the implementer's stated reason from the task report and compare it
with the architecture. Name the cases where the brief prescribed a structure that conflicts
with core, where a report says core was deliberately untouched, where a local abstraction may
have been unnecessary — and where the session correctly avoided touching core despite an
apparent similarity. "The brief said so" is not proof the architecture is right.
