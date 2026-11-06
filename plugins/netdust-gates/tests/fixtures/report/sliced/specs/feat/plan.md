# feat Implementation Plan

**Goal:** Two screens over the rows table, and a CSV export.

**Spec:** `specs/feat/spec.md`

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| `ListScreen` | the admin page | e2e · `tests/e2e/list.spec.ts` · `npx playwright test tests/e2e/list.spec.ts` | List shows rows · List filters by type |
| `DetailScreen` | the detail route | e2e · `tests/e2e/detail.spec.ts` · `npx playwright test tests/e2e/detail.spec.ts` | Detail opens |
| `RowRepository` | `find()` | unit · `tests/Unit/RowRepositoryTest.php` · `composer test:unit` | none |
| `Exporter` | the CSV route | wire · `tests/Integration/ExportTest.php` · `composer test:integration` | Export downloads a CSV |

---

### Task 1 · Slice 1: `RowRepository` and the `ListScreen`

- [ ] **Step 1:** the repository, RED then GREEN.

### Task 2 · Slice 1: `ListScreen` filters by type

- [ ] **Step 1:** the filter.

### Task 3 · Slice 2: the `DetailScreen`

- [ ] **Step 1:** the route and the template.
