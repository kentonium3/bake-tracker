# Cursor Code Review: Feature 035 - Ingredient Auto-Slug & Deletion Protection

**Date:** 2026-01-02
**Reviewer:** Cursor (AI Code Review)
**Feature:** 035-ingredient-auto-slug
**Branch/Worktree:** `.worktrees/035-ingredient-auto-slug`

## Summary

Feature 035 is implemented cleanly and aligns with the prompt’s required patterns: safe ingredient deletion is blocked when referenced by products/recipes/children, snapshot records are denormalized (names + hierarchy) and FK-nullified before deletion, and slug generation/conflict resolution is covered by tests. All verification commands and the full test suite are green.

## Verification Results

### Module Import Validation
- inventory_snapshot.py: **PASS**
- ingredient_alias.py: **PASS**
- ingredient_crosswalk.py: **PASS**
- ingredient_service.py: **PASS**
- exceptions.py: **PASS**
- ingredients_tab.py: **PASS**
- test_ingredient_service.py: **PASS**

### Test Results
- Deletion/Slug tests (9): **9 passed, 0 failed**
- Full ingredient service tests (50): **50 passed, 0 failed**
- Full test suite: **1469 passed, 14 skipped, 0 failed**

### Code Pattern Validation
- Schema changes (WP01): **correct**
- Cascade delete config (WP02): **correct**
- Deletion protection service (WP03): **correct**
- Field normalization (WP04): **correct**
- UI integration (WP05): **correct**
- Tests (WP06): **correct**

## Findings

### Critical Issues

- None found.

### Warnings

- **Snapshot value semantics after deletion**: `SnapshotIngredient.calculate_value()` returns `0.0` when `ingredient` relationship is `None`. After F035 deletion, snapshots preserve names but intentionally nullify `ingredient_id`, so any later value calculations based on the relationship will drop to `0.0`. If snapshot value reporting is important, consider snapshotting cost-related fields or computing/storing snapshot totals at snapshot time.

- **Remaining legacy `name` fallback in UI dialog**: `IngredientFormDialog._delete()` uses `ingredient.get("name") or ingredient.get("display_name")`. This is consistent with the prompt’s WP04 normalization/backward-compat intent, but if the long-term goal is strict `display_name` only, this is a follow-up cleanup candidate.

### Observations

- CASCADE deletes are correctly delegated to the DB via FK `ondelete="CASCADE"` plus `passive_deletes="all"` on the ORM relationships.
- SQLite FK enforcement is explicitly enabled in tests via `PRAGMA foreign_keys=ON`, which is required for CASCADE behavior to be exercised in unit tests.
- Full suite shows several SQLAlchemy `LegacyAPIWarning` warnings (e.g. `Query.get()`); these are unrelated to F035 and can be addressed separately.

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/inventory_snapshot.py | Reviewed | `ingredient_id` uses `SET NULL` + nullable; added denormalized snapshot name fields |
| src/models/ingredient_alias.py | Reviewed | `ondelete="CASCADE"` and `passive_deletes="all"` present |
| src/models/ingredient_crosswalk.py | Reviewed | `ondelete="CASCADE"` and `passive_deletes="all"` present |
| src/services/ingredient_service.py | Reviewed | `can_delete_ingredient`, `_denormalize_snapshot_ingredients`, `delete_ingredient_safe` follow session pattern |
| src/services/exceptions.py | Reviewed | `IngredientInUse` exposes `details` dict for UI |
| src/ui/ingredients_tab.py | Reviewed | Tab + dialog use `delete_ingredient_safe` and show detailed blocked-deletion message |
| src/tests/services/test_ingredient_service.py | Reviewed | `TestDeletionProtectionAndSlug` added (9 tests) |
| src/tests/conftest.py | Reviewed | SQLite FK pragma enabled so CASCADE works in tests |

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: SnapshotIngredient FK allows NULL | **PASS** | `ForeignKey("ingredients.id", ondelete="SET NULL"), nullable=True` |
| FR-002: Denormalization columns exist | **PASS** | `ingredient_name_snapshot`, `parent_l1_name_snapshot`, `parent_l0_name_snapshot` present |
| FR-003: Alias cascade delete works | **PASS** | `IngredientAlias.ingredient_id` uses `ondelete="CASCADE"` + tests pass |
| FR-004: Crosswalk cascade delete works | **PASS** | `IngredientCrosswalk.ingredient_id` uses `ondelete="CASCADE"` + tests pass |
| FR-005: Products block deletion | **PASS** | `can_delete_ingredient()` counts products; test `test_delete_blocked_by_products` passes |
| FR-006: Recipes block deletion | **PASS** | `can_delete_ingredient()` counts recipes; test `test_delete_blocked_by_recipes` passes |
| FR-007: Children block deletion | **PASS** | `can_delete_ingredient()` checks child count; test `test_delete_blocked_by_children` passes |
| FR-008: Snapshots denormalized before deletion | **PASS** | `_denormalize_snapshot_ingredients()` copies names + nullifies FK; test `test_delete_with_snapshots_denormalizes` passes |
| FR-009: Error messages include counts | **PASS** | UI formats counts for products/recipes/children with pluralization |
| FR-010: UI shows detailed error on blocked deletion | **PASS** | `_show_deletion_blocked_message` and dialog variant invoked on `IngredientInUse` |
| FR-011: Field normalization works (name -> display_name) | **PASS** | Normalization in `create_ingredient`; test `test_field_name_normalization` passes |
| FR-012: Session management pattern followed | **PASS** | `session` optional with inner implementation + `session_scope()` fallback |
| FR-013: All existing tests pass (no regressions) | **PASS** | `1469 passed, 14 skipped, 0 failed` |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Schema & Denormalization Fields | **PASS** | FK `SET NULL` + nullable and denormalized name columns present |
| WP02: Cascade Delete Configuration | **PASS** | Alias/Crosswalk CASCADE + `passive_deletes="all"` present; FK pragma enabled in tests |
| WP03: Deletion Protection Service | **PASS** | Blocking checks + denormalize-then-nullify + safe delete flow implemented |
| WP04: Slug Field Mapping Fix | **PASS** | Slug generation/conflict tests pass; normalization supports `display_name` |
| WP05: UI Delete Handler Integration | **PASS** | Tab + dialog call `delete_ingredient_safe` and show user-friendly blocked message |
| WP06: Deletion & Slug Tests | **PASS** | 9/9 new tests pass; full service tests pass |

## Code Quality Assessment

### Schema Changes (WP01)
| Item | Status | Notes |
|------|--------|-------|
| ingredient_id FK SET NULL | **Yes** | `ForeignKey("ingredients.id", ondelete="SET NULL")` |
| ingredient_id nullable | **Yes** | `nullable=True` |
| ingredient_name_snapshot column | **Yes** | Present on `SnapshotIngredient` |
| parent_l1_name_snapshot column | **Yes** | Present on `SnapshotIngredient` |
| parent_l0_name_snapshot column | **Yes** | Present on `SnapshotIngredient` |

### Cascade Delete (WP02)
| Item | Status | Notes |
|------|--------|-------|
| Alias CASCADE configured | **Yes** | `IngredientAlias.ingredient_id` |
| Crosswalk CASCADE configured | **Yes** | `IngredientCrosswalk.ingredient_id` |
| passive_deletes on relationships | **Yes** | Both models set `passive_deletes="all"` |

### Deletion Protection Service (WP03)
| Item | Status | Notes |
|------|--------|-------|
| can_delete_ingredient() exists | **Yes** | Present in `ingredient_service.py` |
| Checks products | **Yes** | Counts `Product.ingredient_id` |
| Checks recipes | **Yes** | Counts `RecipeIngredient.ingredient_id` |
| Checks children | **Yes** | Uses `get_child_count()` |
| Checks snapshots (info only) | **Yes** | Counts snapshot refs but does not block |
| _denormalize_snapshot_ingredients() exists | **Yes** | Present in `ingredient_service.py` |
| Copies L0/L1/L2 names | **Yes** | Copies ingredient + ancestor names into snapshot columns |
| Nullifies FK | **Yes** | Sets `snapshot.ingredient_id = None` |
| delete_ingredient_safe() exists | **Yes** | Present in `ingredient_service.py` |
| Raises IngredientNotFound | **Yes** | Raises when ingredient id missing |
| Raises IngredientInUse with details | **Yes** | Raises with `details` dict for UI |
| Session management pattern | **Yes** | Optional `session` + `session_scope()` fallback |

### UI Integration (WP05)
| Item | Status | Notes |
|------|--------|-------|
| delete_ingredient_safe imported | **Yes** | `ingredients_tab.py` |
| IngredientNotFound imported | **Yes** | `ingredients_tab.py` |
| IngredientsTab uses safe deletion | **Yes** | Uses `delete_ingredient_safe(ingredient_id)` |
| IngredientFormDialog uses safe deletion | **Yes** | Uses `delete_ingredient_safe(ingredient_id)` |
| Error message shows counts | **Yes** | Products/recipes/children counts included |
| Proper pluralization | **Yes** | `product(s)`, `recipe(s)`, `child ingredient(s)` logic |
| "and" before last item | **Yes** | Grammar logic for 2+ items |

### Tests (WP06)
| Test | Status | Notes |
|------|--------|-------|
| test_delete_blocked_by_products | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_delete_blocked_by_recipes | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_delete_blocked_by_children | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_delete_with_snapshots_denormalizes | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_delete_cascades_aliases | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_delete_cascades_crosswalks | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_slug_auto_generation | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_slug_conflict_resolution | **PASS** | Included in `TestDeletionProtectionAndSlug` |
| test_field_name_normalization | **PASS** | Included in `TestDeletionProtectionAndSlug` |

## Potential Issues

### Session Management
No issues found. New functions accept an optional `session` and correctly fall back to `session_scope()` when none is provided.

### Edge Cases
- Deletion of ingredients that are referenced only by snapshots is allowed (by design) and preserves names/hierarchy; however, see the warning about value calculations if snapshot value is computed later from ORM relationships.

### Data Integrity
Denormalization-then-nullify preserves historical naming data and avoids broken FK references. CASCADE deletes for aliases/crosswalks are DB-enforced and tested.

## Conclusion

**APPROVED**

Implementation meets the prompt’s requirements and is well-covered by tests. Recommended follow-ups are minor (snapshot value semantics and optional cleanup of remaining `name` fallbacks if the project decides to enforce `display_name` exclusively).


