# threat-modeling — lessons learned

Calibration notes from real plan-writing runs. Each entry: short trigger → observation → recommendation → severity.

---

### 2026-05-28 — Retrospective threat modeling works but costs N rounds of /code-review first

- **Source:** Folio Phase 3 Sub-phase B (2026-05-28), surfaced by `/code-review` rounds 1 + 2 that found ~30 security-class findings across 7 tasks of BYOK + provider-URL code.
- **Observation:** the plan had functional requirements ("BYOK is libsodium-encrypted") but no threat model. Each `/code-review` round independently re-discovered the attack surface, finding a different subset each time. Round 2 caught CRITICAL-class items round 1 missed (SSRF IPv4-mapped IPv6 bypass, credential exfiltration via baseUrl, persistence-path validation gap). The cap-of-15 on medium-effort reviews compounded — long-tail findings stayed below the threshold across multiple rounds without ever surfacing.
- **Recommendation:** the skill exists to PREVENT this — invoke proactively during plan-writing for surfaces named in `<when_to_use>`. If you DO end up retrospectively writing one (as Folio did mid-Sub-phase B), accept the cost: rounds 1+2 won't be wasted but they ARE a sunk cost the next plan-writer can avoid.
- **Severity:** high — prevention is ~15 minutes; remediation is hours of review-fix loops.

---

### 2026-05-28 — Cap-of-15 on /code-review medium effort interacts badly with security-rich surfaces

- **Source:** Folio Phase 3 Sub-phase B, same incident.
- **Observation:** when the actual defect surface is 20-30 findings and the medium-effort cap shows 15, the dropped findings can include critical-class items. Multi-round iteration at medium effort does NOT guarantee escape — the same long-tail findings can stay below the cap across multiple rounds.
- **Recommendation for threat-modeled plans:** the threat model collapses N rounds into 1 by providing an explicit convergence target. `/code-review` checks against the named mitigations instead of free-form bug hunting, so cap-vs-defect-surface drift doesn't matter — every numbered mitigation either is or isn't implemented.
- **Recommendation for non-threat-modeled security-rich plans:** the FIRST `/code-review` round should use `--effort=high` or `ultra`, not medium. Subsequent rounds can drop to medium once the threat surface is mapped.
- **Severity:** medium — the threat-modeling skill mostly obviates this, but it's worth knowing when the skill wasn't run upstream.

---

### 2026-05-28 — Plans for features that touch user-controlled URLs MUST trigger this skill

- **Source:** Folio Phase 3 Sub-phase B (same incident).
- **Observation:** the original plan author didn't recognize that "BYOK + arbitrary baseUrl + four provider SDKs" was a security-rich surface deserving a threat model. The keywords "BYOK," "libsodium-encrypted," and "API key" felt like security context already covered. They weren't — they covered storage-at-rest but not the URL + outbound-request + cross-route consistency surface.
- **Recommendation:** the trigger list in `<when_to_use>` enumerates user-controlled URLs FIRST because this is the most common miss. Whenever a plan describes a feature where the server makes requests to URLs the user supplied (test endpoints, webhooks, BYOK providers, OAuth callbacks, embed sources), this skill is required. No exceptions.
- **Severity:** high — false negatives on the trigger are expensive.
