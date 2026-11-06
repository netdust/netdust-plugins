# feat Implementation Plan

**Goal:** One screen.

**Spec:** `specs/feat/spec.md`

## Test map

| Unit | Seam | Tests: tier · file · command | E2E flows |
|---|---|---|---|
| `ListScreen` | the admin page | e2e · `tests/e2e/list.spec.ts` · `npx playwright test tests/e2e/list.spec.ts` | List shows rows |
| `RowRepository` | `find()` | unit · `tests/Unit/RowRepositoryTest.php` · `composer test:unit` | none |

---

### Task 1: `RowRepository`

- [ ] **Step 1:** the repository.

### Task 2: the `ListScreen`

- [ ] **Step 1:** the page.
