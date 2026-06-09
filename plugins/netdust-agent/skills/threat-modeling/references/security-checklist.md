# Security Control Checklist — Verify Mitigations Against This

The deep, code-checkable control list the threat-modeling GATE points at. When a `## Threat model` section names mitigations (Step 4), this is what you verify them against: each item below is a concrete control a reviewer can confirm is present (`[x]`) or flag as missing (`[ ]`). Keyed to THIS project's real surfaces — BYOK, libsodium, the SSRF + IPv4-mapped-IPv6 class, the untrusted-parsing trigger list — not generic web-app boilerplate.

Source material folded from `addyosmani/agent-skills:security-checklist` (MIT): STRIDE, OWASP Top 10, pre-commit checks. Adapted into this harness's vocabulary.

> The `security-sentinel` agent loads this checklist for its audit — walk each section against the diff, not from memory.

---

## STRIDE — threat-modeling spine (per attack in the model)

For each numbered attack in the plan's `## Threat model`, classify it and confirm the paired mitigation lands the matching control.

| Letter | Threat | Asks | Control to verify |
|---|---|---|---|
| **S** Spoofing | Identity forgery | Can an actor claim to be another (user, agent, service)? | Auth on every state-changing route; token bound to its issuing actor; no trust of client-supplied identity fields |
| **T** Tampering | Data/integrity alteration | Can input/state be modified in transit or at rest? | Validation at the boundary; integrity of the event/audit trail; no client-mutable authority fields |
| **R** Repudiation | "I didn't do that" | Is the action attributable? | `events` row emitted on the same transaction as the write; actor + actor-type recorded |
| **I** Information disclosure | Leak of secrets/PII/cross-tenant data | Can an actor read what they shouldn't? | Scoped queries; redaction at the loader; no secret in logs/errors/responses |
| **D** Denial of service | Exhaustion | Can an actor saturate a resource? | Input size caps; agent-run ceiling; poller re-entrancy latch; pagination |
| **E** Elevation of privilege | Gaining unauthorized capability | Can an actor widen their own scope? | Scope/role check on the widening path; no self-grant; deny-path tested |

- [ ] Every model attack maps to ≥1 STRIDE letter and its control is present in the diff
- [ ] Each control is **code-checkable** (a named function / named call site), not "validate input" vibes

---

## Input validation & untrusted parsing (THIS project's real surfaces)

The trigger list `threat-modeling/SKILL.md` names — frontmatter, AI tool-call args, webhook payloads, file uploads. Each is attacker-supplied JSON/YAML/MD the server will trust.

- [ ] **Zod (or equivalent) schema at the API boundary** before `req.body`/`req.params`/`req.query` lands anywhere
- [ ] **Frontmatter from third-party MD**: YAML parsed with a safe loader (no arbitrary tags/aliases — billion-laughs); no `Object.assign`/merge of untrusted keys onto a config (prototype pollution)
- [ ] **AI tool-call argument JSON**: every `JSON.parse` is try/catch-wrapped; on failure → log + structured `__parse_error` event, never an unhandled throw that aborts the stream
- [ ] **Webhook payloads**: signature/secret verified BEFORE parsing; payload size-capped; one malformed payload can't crash the reactor
- [ ] **File uploads**: filename path-traversal blocked (`../`, absolute paths, NUL); content-type not trusted from the client; decompression-bomb / size ceiling enforced; no symlink-follow on write
- [ ] Untrusted MD rendered with HTML sanitized (no raw `<script>`/event handlers surviving to the DOM)
- [ ] Falsy-zero traps avoided in stream accumulators (`if (delta.tokens)` skips on `0` → use `!= null`)

---

## Auth / session / token

- [ ] **Password hashing**: bcrypt with cost ≥ 12, or argon2id — never a fast/unsalted hash, never SHA-* alone
- [ ] **Session**: opaque, server-side, rotated on privilege change; cookie `HttpOnly` + `Secure` + `SameSite=Lax`
- [ ] **Magic-link / reset tokens**: single-use, short TTL, constant-time compared, invalidated on use
- [ ] **Token scoping**: a token carries the *minimum* scopes; the scope check exists on the route AND its twin (HTTP ↔ MCP, create ↔ update)
- [ ] No privilege self-grant: a write that widens an actor's own scope is gated by a check the actor can't satisfy
- [ ] Deny-path tested: a denied actor (wrong role / second tenant / blocked resource) asserts the refusal — not only the happy 200

---

## SSRF & user-controlled URLs (Folio attack #1)

The `baseUrl` / webhook / OAuth-redirect surface. The server makes an outbound request to a URL the user supplied — the canonical Folio SSRF class, including the IPv4-mapped-IPv6 bypass.

- [ ] **One shared validator** all user-URL paths route through (test-key AND persist-and-reuse) — validation is NOT on one route while the persisted path skips it
- [ ] Scheme allow-listed (`https` only, or an explicit narrow set)
- [ ] Resolved IP rejected if in: RFC1918 private, loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16`), cloud metadata (`169.254.169.254`)
- [ ] **IPv4-mapped IPv6 blocked** (`::ffff:127.0.0.1`, `::ffff:10.x`) — the bypass that shipped past green in Phase 3
- [ ] Provider-narrowed allow-list where applicable (a BYOK provider's baseUrl constrained to that provider's hosts)
- [ ] Resolution cached for the request lifetime (mitigates the trivial DNS-rebinding window; full rebinding defense documented as deferred)
- [ ] No `Authorization`/secret header attached to a request bound for a user-controlled URL
- [ ] If the URL is returned to the client (redirect), open-redirect is blocked
- [ ] Use `127.0.0.1` not `localhost` for loopback services (Bun fetch has no IPv6→v4 fallback — known trap)

---

## Secrets & BYOK

- [ ] BYOK keys **libsodium-encrypted at rest** (`ai_keys.encrypted_key`), decrypted only with `FOLIO_MASTER_KEY` from env
- [ ] The server holds **no default AI key** — keyless workspace hides AI features gracefully
- [ ] Key never logged (server logs, telemetry, exception traces, debug dumps)
- [ ] Key never returned in an API response — even partially/masked-but-reversible
- [ ] Key never persisted unencrypted (no transient plaintext file, no unencrypted backup)
- [ ] Encryption key not reused for an unrelated purpose
- [ ] Redaction at the **shared loader/serializer**, not per-handler (every consumer — HTTP + MCP + internal — inherits it; `system_prompt` leaked 3× from per-handler redaction)
- [ ] Pre-commit / grep sweep for committed secrets (`grep -rn "sk-\|api[_-]key\|BEGIN.*PRIVATE"` over the diff)

---

## Error handling

- [ ] No stack trace / internal path / SQL / library version in any response body
- [ ] Errors thrown as `HTTPException` → `{ error: { code, message } }`; message is safe-for-client, details go to the server log only
- [ ] A failed outbound request to a user URL does not echo the resolved internal address back to the caller
- [ ] No verbose framework error page in production

---

## OWASP Top 10 quick table (prevention this project applies)

| ID | Name | Prevention here |
|---|---|---|
| A01 | Broken Access Control | Converge visibility in `lib/access.ts`; scope check on route + twin; deny-path test |
| A02 | Cryptographic Failures | libsodium at rest; bcrypt≥12/argon2; `FOLIO_MASTER_KEY` from env, never committed |
| A03 | Injection | Drizzle parameterized queries (no string-concat SQL); Zod at boundary; HTML sanitized |
| A04 | Insecure Design | The `## Threat model` section itself — design-time, before tasks |
| A05 | Security Misconfiguration | No default key; CORS allow-list (not `*` with credentials); secure cookie flags |
| A06 | Vulnerable Components | Lockfile pinned; dependency audit on bump |
| A07 | Auth Failures | Single-use short-TTL tokens; session rotation; rate-limit auth routes |
| A08 | Data Integrity Failures | Webhook signature verified before parse; event emitted on the write txn |
| A09 | Logging/Monitoring Failures | `events` row per write; secrets redacted from logs |
| A10 | SSRF | The shared URL validator above — Folio attack #1 |

---

## Pre-commit / pre-merge sweep

- [ ] No secret in the diff (grep above)
- [ ] CORS not `Access-Control-Allow-Origin: *` alongside `Allow-Credentials: true`
- [ ] Every new route has auth + scope + a deny-path test
- [ ] Every new `JSON.parse` on untrusted input is wrapped
- [ ] Every new user-URL path routes through the shared validator
- [ ] Mitigations named in the plan's `## Threat model` are all present (or moved to the deferrals list with rationale)

---

Using this list: walk the diff section-by-section against the plan's threat model. A model mitigation with no matching `[x]` here is a finding; a `[ ]` with no corresponding model attack is either an unmodeled surface (extend the threat model) or out-of-scope (add it to the deferrals list so it inherits forward).
