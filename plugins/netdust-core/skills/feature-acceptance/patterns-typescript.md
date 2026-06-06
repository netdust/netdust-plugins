# Feature-acceptance driving patterns — TypeScript

Concrete ways to *drive* an acceptance flow + its edges through the faithful layer. Pick the layer per flow (see SKILL.md `<driving_layers>`); these are the tools.

## UI flow — Playwright (preferred, durable)

When a flow will recur, author a durable spec. Drive the EDGES, not just the happy path.

```ts
// e2e/create-work-item.spec.ts
import { test, expect } from '@playwright/test'

test('create work item — happy + edges', async ({ page, context }) => {
  await page.goto('/w/acme/p/web/work-items')

  // happy path
  await page.getByRole('button', { name: 'New work item' }).click()
  await page.getByPlaceholder('Title').fill('Ship the thing')
  await page.keyboard.press('Enter')
  await expect(page.getByText('Ship the thing')).toBeVisible()   // optimistic
  await page.reload()
  await expect(page.getByText('Ship the thing')).toBeVisible()   // persisted

  // EDGE: empty submit → no row, no crash
  await page.getByRole('button', { name: 'New work item' }).click()
  await page.keyboard.press('Enter')
  await expect(page.getByText('Untitled')).toHaveCount(0)

  // EDGE: double-submit → ONE row not two (the accessible-name collision bug)
  await page.getByRole('button', { name: 'New work item' }).click()
  await page.getByPlaceholder('Title').fill('Once')
  await page.keyboard.press('Enter')
  await page.keyboard.press('Enter')          // fast second press
  await expect(page.getByText('Once')).toHaveCount(1)

  // EDGE: mid-flow failure → optimistic row rolls back + toast
  await context.route('**/api/v1/**', r => r.abort())   // network drops on save
  await page.getByRole('button', { name: 'New work item' }).click()
  await page.getByPlaceholder('Title').fill('Will fail')
  await page.keyboard.press('Enter')
  await expect(page.getByText('Will fail')).toHaveCount(0)   // rolled back
  await expect(page.getByRole('alert')).toContainText(/failed|error/i)
})
```

**Why a real browser, not jsdom:** RTL's `userEvent.type` clears-then-types internally, masking append-vs-replace and focus-race bugs (the InlineEdit pre-select bug stayed green in every jsdom test). Optimistic rollback, real CSS, the actual click target, and double-submit timing only show in the browser.

## UI flow — `use_browser` (one-shot, no Playwright config)

When no spec infra exists and you just need to drive the flow once during shake-out: start the dev server, then drive `superpowers-chrome` `use_browser` (see `superpowers-chrome:browsing`). Navigate, click, type, and read back the rendered DOM (`getBoundingClientRect` / computed styles / visible text) to assert behavior. If the dev server can't start, mark the flow `unverified-no-browser` — never `pass`.

## Backend flow — un-mocked wire (Hono)

Drive the real mounted app, real DB. Assert response + DB state + emitted event — do NOT mock the layer you're verifying.

```ts
import { describe, it, expect } from 'vitest'
import app from '@/app'                      // the real mounted Hono app
import { freshDb, seedUser, tokenFor } from '@/test/helpers'

describe('assign via API — acceptance', () => {
  it('happy + denial + concurrency + malformed', async () => {
    const db = await freshDb()
    const member = await seedUser(db, { role: 'member' })
    const item = await createItem(db, { project: 'web' })

    // happy: real request through the mounted app
    const ok = await app.request(`/api/v1/items/${item.id}`, {
      method: 'PATCH',
      headers: { authorization: `Bearer ${tokenFor(member)}` },
      body: JSON.stringify({ assignee: member.id }),
    })
    expect(ok.status).toBe(200)
    expect(await assigneeOf(db, item.id)).toBe(member.id)
    expect(await lastEvent(db, item.id)).toMatchObject({ type: 'item.updated' })

    // EDGE denied actor: unauthorized token → 403 (drive the FULL chain — route + service defaults)
    const denied = await app.request(`/api/v1/items/${item.id}`, {
      method: 'PATCH',
      headers: { authorization: `Bearer ${tokenFor(await seedUser(db, { role: 'viewer' }))}` },
      body: JSON.stringify({ assignee: member.id }),
    })
    expect(denied.status).toBe(403)

    // EDGE malformed body → 422 (not 500)
    const bad = await app.request(`/api/v1/items/${item.id}`, {
      method: 'PATCH',
      headers: { authorization: `Bearer ${tokenFor(member)}` },
      body: '{ not json',
    })
    expect(bad.status).toBe(422)
  })
})
```

**Concurrency edge:** fire the two racing requests with `Promise.all`, then assert the deterministic outcome (last-write-wins by `updated_at`), and run the test ≥3× (it's `test-effectiveness` mode 7). Do not assert on scheduling luck.

**Mid-flow-failure edge:** force the failure (inject a throw after a partial write) and assert cleanup — on bun-sqlite, remember an awaited throw inside `db.transaction(async …)` does NOT roll back; assert the app-layer cleanup (the manual delete-on-catch), not the rollback.
