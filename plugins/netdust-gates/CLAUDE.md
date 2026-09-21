# netdust-gates

Stefan's software-delivery policy over superpowers, and nothing else. Superpowers runs the
loop in its own plan format; this plugin does three things:

1. **Inject** — Netdust standards go into the slots superpowers already carries to every
   implementer and reviewer (`Global Constraints`, `Review Focus`): `skills/policy/`.
2. **Verify** — by executables: the project's `make gate`, and `bin/shakeout-check.py`.
3. **Authorize** — hooks for what only Stefan can grant: `hooks/`.

The spec is `specs/netdust-gates/spec.md`; it is the authority.

## The growth rule

An incident lands as **a gate tier in the project**, **a line in a constraints pack or the
edge-class catalog**, or **an eval case**. Never as a new plan field or a new check on plan
grammar. netdust-agent went 0.18 → 0.28 in six weeks by doing the opposite.

## Boundaries

- Enable this or `netdust-agent` in a project, never both — both would fire their hooks.
- Not here, and not to be re-added: gate-check, lanes, tiers, clusters, placement, the model
  ladder, /loop, implementer / test-author / reviewer agents, compounding, convergence,
  run-score / run-trace / verify-budget.
- The policy skill stays under 150 lines; past that it is restating superpowers.

## Tests

`bash tests/run.sh` (all) · `bash tests/run.sh test_<name>.py` (one). Each `tests/test_*.py`
exposes `run()`. `python3 evals/run-evals.py` runs the three behavioural cases; it needs the
`claude` CLI and is not part of `run.sh`.
