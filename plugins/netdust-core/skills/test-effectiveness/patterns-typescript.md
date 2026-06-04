# Test-Effectiveness Patterns — TypeScript (Vitest / Playwright)

Concrete forms of the author-fix for each failure mode. Copy and adapt. These assume Vitest for unit/integration, Playwright for e2e, and a Hono-style mounted app (Folio's stack) — adjust the app-mount idiom for Express/Fastify.

The rule under all of them: **the test must execute the DANGEROUS path** (the denial, the second tenant, the un-mocked wire, the mounted guard, the forced race), not the safe one.

---

## Mode 1 — Stale fixture: assert the NEW shape at a consumer

Don't just round-trip the server. When a canonical form changes, add a test that drives the NEW shape through a real consumer.

```ts
// After author changed from `agent:<slug>` to `agent:<id>`:
// BAD (stale): fixture still uses the old shape, round-trips green
const comment = makeComment({ author: 'agent:my-slug' })   // ← lying fixture

// GOOD: fixture uses the NEW shape, and a consumer test asserts it resolves
const comment = makeComment({ author: `agent:${agentId}` })
it('AuthorDisplay renders the agent slug for an id-form author', () => {
  render(<AuthorDisplay author={`agent:${agentId}`} agents={[{ id: agentId, slug: 'my-slug' }]} />)
  expect(screen.getByText('my-slug')).toBeInTheDocument()   // resolves id → slug
})
it('resolveIsAuthor matches on the id form', () => {
  expect(resolveIsAuthor(`agent:${agentId}`, { agentId })).toBe(true)
})
```

Audit grep before closing the change:
```bash
grep -rn "agent:" apps/ packages/   # every match is a consumer OR a stale fixture
```

---

## Mode 2 — Test-world ≠ real-world: seed from a realistic baseline

The structural fix (migrate-at-boot) lives in app code, not a test. Where a test is right, seed a baseline the real world actually produces.

```ts
// The harness migrates fresh every run — so it can't catch "old DB missing a column".
// Where the contract is "old rows get backfilled", test against a PRE-migration row:
it('backfill migration populates last_touched_at for pre-existing rows', async () => {
  const db = await makeRawDbAtMigration('0004')          // BEFORE 0005
  await db.insert(documents).values({ id, title: 'old', /* no last_touched_at */ })
  await migrateTo(db, '0005')                            // apply the new migration
  const row = await db.select().from(documents).where(eq(documents.id, id)).get()
  expect(row.last_touched_at).not.toBeNull()             // old row got the column populated
})
```

And assert the app self-heals (the real fix): a boot test that runs `migrate()` on a stale DB and confirms the route no longer 500s.

---

## Mode 3 — Wire-mock leak: cross the un-mocked boundary

```ts
// BAD: mocks the server response — proves nothing about the server or the wire
vi.spyOn(client, 'get').mockResolvedValue({ documents: [allowedDoc] })  // ← testing the mock

// GOOD (integration): drive a REAL request through the mounted app, no boundary mock
it('GET /documents only returns the caller-visible set (un-mocked wire)', async () => {
  const app = makeTestApp(db)                            // real router, real handlers
  const res = await app.request(`/w/${ws}/documents`, { headers: tokenFor(projectOnlyUser) })
  const body = await res.json()
  expect(body.documents.map(d => d.id)).toEqual([p1Doc.id])   // NOT p2Doc — the real filter ran
})

// Mode-3 invalidation variant: assert against the BROAD key, not one mocked shape
it('updating a doc invalidates every list variant', async () => {
  const spy = vi.spyOn(queryClient, 'invalidateQueries')
  await updateDocument(doc)
  expect(spy).toHaveBeenCalledWith({ queryKey: [...documentsKeys.all, wslug, pslug, 'list'] })
  // broad prefix → covers sort='title' AND sort='updated_at' lists, not just the one under test
})
```

For a client↔server wire you can't drive in unit-land, add a shake-out crossing (see Playwright below).

---

## Mode 4 — Unmounted / unwired: drive through the mount, act in the target

```ts
// BAD: calls the guard in isolation — a mis-mount is invisible
expect(() => requireScope('agents:write')(ctxWithoutScope)).toThrow()   // guard works...

// GOOD: the guard must fire THROUGH the mounted route (catches "guard not mounted on HTTP twin")
it('POST /documents (type=agent) is denied without agents:write — on the HTTP path', async () => {
  const app = makeTestApp(db)
  const res = await app.request(`/w/${ws}/documents`, {
    method: 'POST',
    headers: tokenFor(memberWithoutAgentsWrite),
    body: JSON.stringify({ type: 'agent', title: 'x' }),
  })
  expect(res.status).toBe(403)                           // guard is actually mounted here
})

// Sibling sweep: the SAME test for every twin
it.each(['POST', 'PATCH', 'DELETE'])('%s agent route denies without scope', async (method) => { /* … */ })

// Wiring/capability task: ACT in the target, don't stop at the seam
it('library operator dispatched into workspace B actually writes in B', async () => {
  const run = await dispatchToolAsAgent(operator, { workspace: 'B', tool: 'write_document', args })
  const written = await db.select().from(documents).where(eq(documents.workspaceId, 'B')).get()
  expect(written).toBeDefined()                          // full chain, not "resolution returned the agent"
})
```

---

## Mode 5 — Happy-path-only: the RED-first denial, across every sibling

```ts
// The happy path is the easy add. Write the DENIAL first and watch it RED.
it('GET /events?project=<blocked> is refused for a project-scoped token', async () => {
  const app = makeTestApp(db)
  const res = await app.request(`/w/${ws}/events?project=${blockedProjectId}`, {
    headers: tokenFor(agentScopedToP1Only),
  })
  expect(res.status).toBe(403)                           // FORBIDDEN_RESOURCE — the traverse is refused
})

// The traverse-clause class is N sibling routes each missing the SAME denial — sweep them:
describe.each(['/events', '/projects', '/runs', '/members'])('%s denies cross-project traverse', (route) => {
  it('refuses a blocked project for a project-only caller', async () => {
    const res = await makeTestApp(db).request(`/w/${ws}${route}?project=${blockedProjectId}`,
      { headers: tokenFor(projectOnlyCaller) })
    expect([403, 404]).toContain(res.status)
    // positive control: the allowed project DOES return
  })
})
```

---

## Mode 6 — No coverage: test the layer the user experiences, defeat the masking helper

```ts
// Masking helper: userEvent.type clears-then-types, hiding append-vs-replace. Drive raw keystrokes:
it('typing immediately after default-focus REPLACES the placeholder, not appends', async () => {
  render(<InlineEdit value="Untitled" defaultEditing />)
  const input = screen.getByRole('textbox')
  // do NOT use userEvent.type (it select-alls first). Fire a keystroke against the focused input:
  fireEvent.keyDown(input, { key: 'F' }); fireEvent.input(input, { target: { value: 'F' } })
  expect(input).toHaveValue('F')                         // not 'UntitledF'
})

// Rendered-DOM contract (not AST): assert what the user sees
it('a GFM task item renders a visible checkbox', () => {
  render(<MilkdownView markdown={'- [x] done'} />)
  const item = document.querySelector('[data-item-type="task"]')
  expect(item).toBeTruthy()
  expect(getComputedStyle(item!, '::before').content).not.toBe('none')   // CSS actually renders a box
})

// Forced-failure contract: the rollback must be exercised by making it throw
it('a thrown handler rolls back the row (no phantom persistence)', async () => {
  await expect(txWithEvents(db, async (tx) => { await tx.insert(documents).values(row); throw new Error('boom') }))
    .rejects.toThrow()
  expect(await db.select().from(documents).where(eq(documents.id, row.id)).get()).toBeUndefined()
})
```

---

## Mode 7 — Concurrency / timing: force the interleaving, run ≥3×

```ts
// Force re-entrancy: make the first callback slow, fire the timer twice, assert the latch held
it('the poller skips re-entry while a prior tick is still running', async () => {
  let active = 0, maxConcurrent = 0
  const slow = async () => { active++; maxConcurrent = Math.max(maxConcurrent, active); await delay(50); active-- }
  const poller = makePoller(slow, { intervalMs: 1 })
  poller.start(); await delay(120); poller.stop()
  expect(maxConcurrent).toBe(1)                          // the latch prevented concurrent re-entry
})
```

Determinism box — the new/changed timing test must be green every run:
```bash
for i in 1 2 3; do npx vitest run src/lib/poller.test.ts || exit 1; done
```

---

## Playwright — the un-mocked crossing for wire + render + timing

When a mode can only be proven against the live wire (Mode 3 oscillation, Mode 6 keystroke race, Mode 7 refetch toggle), a Playwright step is the un-mocked crossing:

```ts
test('editing a doc does not blank on refetch (Mode 3/7 — live React Query)', async ({ page }) => {
  await page.goto(`/w/${ws}/p/${p}/d/${doc}`)
  await page.getByRole('textbox', { name: 'Body' }).fill('my edit')
  await page.waitForTimeout(1500)                        // let a refetch cycle run — the toggle would blank it
  await expect(page.getByRole('textbox', { name: 'Body' })).toHaveValue('my edit')
})
```

Use the e2e crossing sparingly — it's the slow layer. One un-mocked assertion per wire is the goal, not a full e2e suite.
