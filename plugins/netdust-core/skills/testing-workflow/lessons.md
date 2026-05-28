# testing-workflow — lessons learned

Calibration notes from real harness runs. Each entry: short trigger → observation → recommendation → severity.

---

### 2026-05-28 — Drizzle `migrate()` is journal-idempotent; don't call it twice in a test

- **Source:** Folio Phase 3 Sub-phase A (Task A-3), surfaced by `/evaluate` retro at `docs/superpowers/retros/2026-05-28-phase-3-sub-phase-A-retro.md`.
- **Observation:** A migration test was written assuming `migrate(db, { migrationsFolder })` could be called once to apply all prior migrations, then again to apply a newly-added migration against seeded data. **Drizzle's migrator is idempotent at the journal level** — once a migration's tag is in `__drizzle_migrations`, the second `migrate()` call is a no-op. The seeded rows are never touched, the test fails, and the failure mode is hard to debug because the migration *file* exists and the migrator *runs* — it just runs zero new migrations.
- **Recommendation for tests that need to apply a single migration's UPDATE against pre-seeded rows:**

  ```ts
  import { readFileSync } from 'node:fs';
  import { resolve } from 'node:path';

  // Step 1: run all prior migrations to a clean DB.
  migrate(db, { migrationsFolder: MIGRATIONS_FOLDER });

  // Step 2: seed pre-migration state (rows the new migration will UPDATE).
  sqlite.run(`INSERT INTO ... VALUES (...)`);

  // Step 3: exec the new migration's SQL directly, bypassing the journal.
  const sql = readFileSync(
    resolve(MIGRATIONS_FOLDER, '0012a_flip_runner_builtins_to_enabled.sql'),
    'utf-8'
  );
  sqlite.exec(sql);

  // Step 4: assert the migration's effect on the seeded rows.
  ```

  The trick is that `sqlite.exec()` doesn't consult `__drizzle_migrations`. The migration's SQL runs against whatever state the test set up, regardless of whether the migrator thinks it has already shipped.

- **Severity:** **medium** — wastes 10-20 minutes of debugging the first time a migration test is written this way. Once internalized, costs nothing.
- **Applies to:** any Drizzle-based project (Folio, future Bun/TS projects). NOT WordPress (different test runner + migration story).

---
