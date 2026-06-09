# Finding convergence points — per-stack grep recipes

The core move (skill Step 1): you don't GUESS the convergence point, you find it by asking "what do all the consumers of this property import or call?" If they all call one thing → that's the convergence point. If they each do it differently → there ISN'T one (record a gap).

These are starting greps. Adapt to the project. The OUTPUT you want for each property: the actual `file:symbol` that is the single decision point, plus the count of consumers (high consumer count on one symbol = a strong, real convergence point).

---

## Authorization — "where is 'may this actor do this?' decided?"

**Bun/Hono/TS:**
```
grep -rln "requireScope\|requireResource\|requireUser\|executeTool\|can(" src --include="*.ts" | grep -v test
```
Then read the routes: do they ALL go through the same guard, or do some check perms inline? A handler that reads `token.scopes`/role directly instead of calling the guard is a bypass.

**WordPress:**
```
grep -rn "current_user_can\|check_ajax_referer\|wp_verify_nonce\|->capability" --include="*.php"
```
Convergence = a capability check at a known seam (a base controller, a permission_callback). Scattered `current_user_can` with different caps per handler and no shared map = not converged.

**Statamic/Laravel:**
```
grep -rn "Gate::\|->authorize(\|can:\|Policy" --include="*.php"
```
Convergence = policies + a base controller `authorize`. Inline `if ($user->...)` checks = drift.

---

## Authentication identity — "the ONE primitive every request carries"

```
# Bun: what shape lands in context? grep the middleware that sets it.
grep -rn "c.set('user'\|c.set('token'\|AuthContext\|getUser(c)\|getToken(c)" src --include="*.ts" | grep -v test
# WP: current user + caps is the primitive (built-in). Check nothing re-derives identity from raw cookies.
grep -rn "wp_get_current_user\|get_current_user_id\|wp_validate_auth_cookie"
```
The invariant is usually "all identity flows from <primitive>; nothing parses the raw credential a second time." The Folio bug class: a stray `Authorization` header re-deriving a weaker identity than the session — closed by reading ONLY the context primitive.

---

## Data access — "the ONE path to read/write the store"

```
# Bun/Drizzle: is there one client/repository, or scattered db calls?
grep -rln "from './client\|drizzle(\|db\.\(query\|insert\|update\|delete\)" src --include="*.ts" | grep -v test
# Query-key convention (client side):
grep -rn "Keys = {\|queryKey:" src --include="*.ts" --include="*.tsx" | head
# WP: repository vs raw $wpdb
grep -rn "\$wpdb->\(get_\|query\|prepare\|insert\|update\)" --include="*.php"
```
Convergence = one ORM/repository facade + a structured key convention. Raw `$wpdb` or bare `fetch` scattered across files = not converged (and a security surface — see wp-database skill).

---

## Live updates / events — "how server changes reach consumers, and the source of truth"

```
grep -rln "EventSource\|eventBus\|/events\|SSE\|invalidateQueries\|setQueryData\|do_action\|wp.hooks" src --include="*.ts" --include="*.tsx" --include="*.php" | grep -v test
```
The load-bearing invariant is almost always: **the event teaches WHEN to refetch; it is NEVER the source of truth.** A consumer that builds UI state directly from event payloads (instead of invalidating + refetching the canonical query) is the bypass — it can desync. Note legitimate exceptions (broadcast-only data with no GET endpoint) in Deliberate exceptions.

---

## Error handling — "how a failure becomes user-facing, uniformly"

```
# Bun: one envelope + one formatter?
grep -rn "HTTPError\|{ error:\|formatApiError\|toast.error" src --include="*.ts" --include="*.tsx" | grep -v test | head
# WP: WP_Error never swallowed
grep -rn "new WP_Error\|is_wp_error\|return false;" --include="*.php" | head
```
Convergence = `throw <standard error>` → one client formatter → one toast/notice. A handler that returns a bespoke error shape, or swallows (`catch {}` / `return false` discarding a `WP_Error`), is the bypass.

---

## Entity modeling / extensibility — "new types/fields without schema churn"

Read the schema, don't grep. The question: is there a schemaless seam (a JSON column, post meta, a blueprint) that new fields ride, or does every new field require a migration / new table?

- Folio: `documents` has 3 typed columns + a `frontmatter` JSON blob. New fields = data, zero migrations. Agents/skills/memory are documents, not tables. THAT is the extensibility invariant.
- WP: custom fields / post meta is the seam; a new CPT for every concept is the anti-pattern.

The invariant: "new entity types are data (frontmatter/meta/blueprint) before they are tables." The bypass: a migration adding a column for something that's clearly an attribute of one type.

---

## Reading the result

- **One symbol, many consumers** → real convergence point. Write the invariant.
- **Many symbols, no shared call** → NOT converged. Record an Open gap. Don't invent an invariant.
- **One symbol, but one consumer skips it** → that skip is exactly the bug class the invariant exists to catch. Name it in the invariant's "bypass" clause.
