# TypeScript Test Patterns

Unit test patterns (Vitest) and acceptance test patterns (Playwright).

---

## Triage First: the right COUNT is contract-driven

Before the patterns below, decide the tier (see SKILL.md → *Task risk tier*). The number of tests is **not** a target — a Tier-B task may correctly add **0**, and one sharp Tier-A denial test outranks four happy-path mirrors. The three highest-value shapes:

### Tier B — write NO test, record why

```typescript
// Task: add `cn = (...x) => twMerge(clsx(x))` — a pure pass-through over two typed libs.
// There is no contract of cn's own to assert; any test re-asserts clsx/tailwind-merge.
//   no unit test: Tier B, pure typed pass-through — covered by the libs' suites + TS types.
// Do NOT write `expect(cn('p-2','p-4')).toBe('p-4')` — that asserts tailwind-merge, not cn.
```

### Tier A — RED-first denial test for a guard (one sharp test > four happy mirrors)

```typescript
import { describe, it, expect } from 'vitest';
import { app } from '../src/app'; // exercise the guard through its real handler

describe('config:write scope ceiling', () => {
  // RED first: written against the absent guard, this returned 201 — watched it fail.
  it('DENIES a member escalating to config:write (403)', async () => {
    const res = await app.request('/config', {
      method: 'POST',
      headers: { authorization: `Bearer ${memberToken}` },
      body: JSON.stringify({ scopes: ['config:write'] }),
    });
    expect(res.status).toBe(403);
    expect((await res.json()).error.code).toBe('FORBIDDEN');
  });

  // The companion that stops the guard from over-blocking everyone:
  it('ALLOWS an owner to set config:write (2xx)', async () => {
    const res = await app.request('/config', {
      method: 'POST',
      headers: { authorization: `Bearer ${ownerToken}` },
      body: JSON.stringify({ scopes: ['config:write'] }),
    });
    expect(res.status).toBeLessThan(300);
  });
});
```

A green-only assertion (`status !== 200`) would pass against a guard that 403s *everyone* — assert the denied path AND that the allowed actor still gets through.

### Seam test at the wiring task — cross the un-mocked chain

```typescript
// Task: MOUNT requireResource on /documents/*. resource.test.ts already proves the fn in
// isolation — that test stays GREEN even if the mount is mis-pathed and the guard never fires.
// The delta is the mount; exercise IT, through the real app, no mock of the seam:
describe('requireResource is live on /documents/*', () => {
  it('a project-narrowed agent token gets 403 on another project (real route)', async () => {
    const res = await app.request('/documents/other-project-doc', {
      headers: { authorization: `Bearer ${narrowedAgentToken}` },
    });
    expect(res.status).toBe(403); // not 200 — proves the mount actually enforces
  });
});
```

---

## Unit Test Patterns

### Pure Function / Utility

```typescript
import { describe, it, expect } from 'vitest';
import { calculateScore } from '../src/scoring';

describe('calculateScore', () => {
  it('returns high score for strong confluence', () => {
    const zone = { volumeRatio: 3.5, hasFVG: true, hasBOS: true };
    const score = calculateScore(zone);
    expect(score).toBeGreaterThanOrEqual(8);
  });

  it('returns low score when only volume present', () => {
    const zone = { volumeRatio: 2.0, hasFVG: false, hasBOS: false };
    const score = calculateScore(zone);
    expect(score).toBeLessThan(5);
  });

  it('handles zero volume gracefully', () => {
    const zone = { volumeRatio: 0, hasFVG: true, hasBOS: true };
    const score = calculateScore(zone);
    expect(score).toBeGreaterThanOrEqual(0);
  });

  it('throws for negative volume ratio', () => {
    const zone = { volumeRatio: -1, hasFVG: true, hasBOS: true };
    expect(() => calculateScore(zone)).toThrow('Invalid volume ratio');
  });
});
```

### Data Transformer

```typescript
import { describe, it, expect } from 'vitest';
import { formatZoneForDisplay } from '../src/formatters';

describe('formatZoneForDisplay', () => {
  it('formats a demand zone correctly', () => {
    const zone = { pair: 'BTCUSDT', type: 'demand' as const, price: 42000.50 };
    const result = formatZoneForDisplay(zone);

    expect(result.label).toBe('BTCUSDT Demand');
    expect(result.price).toBe('42,000.50');
  });

  it('returns null label for unknown type', () => {
    const zone = { pair: 'BTCUSDT', type: 'unknown' as any, price: 100 };
    const result = formatZoneForDisplay(zone);
    expect(result.label).toBeNull();
  });

  it('handles empty array input', () => {
    const result = formatZonesForDisplay([]);
    expect(result).toEqual([]);
  });
});
```

### Service Class with Mocked Dependencies

```typescript
import { describe, it, expect, vi } from 'vitest';
import { ZoneScanner } from '../src/scanner';
import type { ExchangeClient } from '../src/types';

describe('ZoneScanner', () => {
  it('detects demand zone from volume spike at swing low', async () => {
    const mockClient: ExchangeClient = {
      getCandles: vi.fn().mockResolvedValue([
        { open: 100, high: 105, low: 95, close: 98, volume: 500 },
        { open: 98, high: 99, low: 90, close: 91, volume: 3000 }, // spike
        { open: 91, high: 102, low: 90, close: 101, volume: 800 },
      ]),
    };

    const scanner = new ZoneScanner(mockClient);
    const zones = await scanner.scan('BTCUSDT', '1h');

    expect(zones).toHaveLength(1);
    expect(zones[0].type).toBe('demand');
    expect(mockClient.getCandles).toHaveBeenCalledWith('BTCUSDT', '1h');
  });

  it('returns empty when no volume anomaly found', async () => {
    const mockClient: ExchangeClient = {
      getCandles: vi.fn().mockResolvedValue([
        { open: 100, high: 101, low: 99, close: 100, volume: 500 },
        { open: 100, high: 101, low: 99, close: 100, volume: 510 },
      ]),
    };

    const scanner = new ZoneScanner(mockClient);
    const zones = await scanner.scan('BTCUSDT', '1h');
    expect(zones).toHaveLength(0);
  });

  it('throws when exchange client fails', async () => {
    const mockClient: ExchangeClient = {
      getCandles: vi.fn().mockRejectedValue(new Error('Rate limited')),
    };

    const scanner = new ZoneScanner(mockClient);
    await expect(scanner.scan('BTCUSDT', '1h')).rejects.toThrow('Rate limited');
  });
});
```

### Validation Logic

```typescript
import { describe, it, expect } from 'vitest';
import { validateConfig } from '../src/config';

describe('validateConfig', () => {
  it('accepts valid configuration', () => {
    const config = { pairs: ['BTCUSDT'], timeframes: ['1h', '4h'], maxZones: 50 };
    const result = validateConfig(config);
    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);
  });

  it('rejects empty pairs array', () => {
    const config = { pairs: [], timeframes: ['1h'], maxZones: 50 };
    const result = validateConfig(config);
    expect(result.valid).toBe(false);
    expect(result.errors).toContain('At least one pair required');
  });

  it('applies defaults for missing optional fields', () => {
    const config = { pairs: ['BTCUSDT'], timeframes: ['1h'] };
    const result = validateConfig(config);
    expect(result.valid).toBe(true);
    expect(result.config.maxZones).toBe(100); // default
  });
});
```

### State Machine / Logic

```typescript
import { describe, it, expect } from 'vitest';
import { TradeState, transition } from '../src/trade-state';

describe('trade state transitions', () => {
  it('moves from pending to active on fill', () => {
    const state = transition(TradeState.Pending, 'fill');
    expect(state).toBe(TradeState.Active);
  });

  it('moves from active to closed on stop loss', () => {
    const state = transition(TradeState.Active, 'stop_loss');
    expect(state).toBe(TradeState.Closed);
  });

  it('throws on invalid transition', () => {
    expect(() => transition(TradeState.Closed, 'fill')).toThrow('Invalid transition');
  });
});
```

### Async / Event Handling

```typescript
import { describe, it, expect, vi } from 'vitest';
import { EventBus } from '../src/events';

describe('EventBus', () => {
  it('calls subscriber when event emitted', () => {
    const bus = new EventBus();
    const handler = vi.fn();

    bus.on('zone:detected', handler);
    bus.emit('zone:detected', { pair: 'BTCUSDT' });

    expect(handler).toHaveBeenCalledWith({ pair: 'BTCUSDT' });
  });

  it('does not call unsubscribed handler', () => {
    const bus = new EventBus();
    const handler = vi.fn();

    const unsub = bus.on('zone:detected', handler);
    unsub();
    bus.emit('zone:detected', { pair: 'BTCUSDT' });

    expect(handler).not.toHaveBeenCalled();
  });
});
```

---

## Acceptance Test Patterns

### Form Submission

```typescript
test('form submits successfully', async ({ page }) => {
  await page.goto('/contact');
  await page.fill('#name', 'Test User');
  await page.fill('#email', 'test@example.com');
  await page.click('button[type="submit"]');

  await expect(page.locator('.success-message')).toBeVisible();
});
```

### Form Validation

```typescript
test('form shows validation errors', async ({ page }) => {
  await page.goto('/contact');
  await page.click('button[type="submit"]'); // Submit empty

  await expect(page.locator('.error-message')).toBeVisible();
  await expect(page.locator('.success-message')).not.toBeVisible();
});
```

### Navigation and Routing

```typescript
test('navigation works correctly', async ({ page }) => {
  await page.goto('/');
  await page.click('a[href="/dashboard"]');

  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('h1')).toContainText('Dashboard');
});
```

### Authentication Flow

```typescript
test('login redirects to dashboard', async ({ page }) => {
  await page.goto('/login');
  await page.fill('#email', 'user@example.com');
  await page.fill('#password', 'password');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL('/dashboard');
});

test('protected route redirects to login', async ({ page }) => {
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/.*login.*/);
});
```

### API Data Loading

```typescript
test('data loads from API', async ({ page }) => {
  await page.goto('/users');

  await expect(page.locator('.user-list')).toBeVisible();
  const items = page.locator('.user-item');
  await expect(items).not.toHaveCount(0);
  await expect(page.locator('.error')).not.toBeVisible();
});
```

### Modal / Dialog

```typescript
test('modal opens and closes', async ({ page }) => {
  await page.goto('/');
  await page.click('#open-modal');

  await expect(page.locator('.modal')).toBeVisible();
  await page.click('.modal-close');
  await expect(page.locator('.modal')).not.toBeVisible();
});
```

### Console Error Check

```typescript
test('page has no console errors', async ({ page }) => {
  const errors: string[] = [];
  page.on('console', msg => {
    if (msg.type() === 'error') errors.push(msg.text());
  });

  await page.goto('/');
  await page.waitForLoadState('networkidle');

  expect(errors).toHaveLength(0);
});
```

### File Upload

```typescript
test('file upload works', async ({ page }) => {
  await page.goto('/upload');

  await page.setInputFiles('input[type="file"]', 'test-file.pdf');
  await page.click('button[type="submit"]');

  await expect(page.locator('.upload-success')).toBeVisible();
});
```

### Responsive Behavior

```typescript
test('mobile menu works', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await page.goto('/');

  await expect(page.locator('.mobile-menu')).not.toBeVisible();
  await page.click('.hamburger');
  await expect(page.locator('.mobile-menu')).toBeVisible();
});
```

---

## Wait Patterns

**Never use fixed waits.** Use condition-based waits.

```typescript
// ❌ BAD
await page.waitForTimeout(5000);

// ✅ GOOD
await page.waitForSelector('.element');
await expect(page.locator('.element')).toBeVisible();
await page.waitForLoadState('networkidle');
await page.waitForResponse(resp => resp.url().includes('/api/'));
```
