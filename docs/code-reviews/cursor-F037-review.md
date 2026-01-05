# Cursor Code Review: Feature 037 - Recipe Template & Snapshot System

**Date:** 2026-01-05
**Reviewer:** Cursor (AI Code Review)
**Feature:** 037-recipe-template-snapshot
**Branch/Worktree:** `.worktrees/037-recipe-template-snapshot`

## Summary

Feature 037 successfully implements the **template/snapshot architecture**: immutable `RecipeSnapshot` records are created at production time, **before FIFO consumption**, and production costing is computed from snapshot data rather than mutable recipes. The full test suite is green after addressing SQLite teardown issues introduced by the new FK cycle and restoring a missing `sample_data.json` fixture.

**Overall:** **APPROVED WITH CHANGES** (see Warnings: session-commit behavior when a session is injected; FK-cycle warning mitigation).

## Verification Results

### Module Import Validation
- recipe_snapshot.py: **PASS**
- recipe_snapshot_service.py: **PASS**
- batch_production_service.py: **PASS**
- migrate_production_snapshots.py: **PASS**
- recipe_history_view.py: **PASS**
- record_production_dialog.py: **PASS**

### Test Results
- Snapshot service tests: **22 passed**
- Migration script tests: **7 passed**
- Full test suite: **1525 passed, 14 skipped, 0 failed**

### Code Pattern Validation
- Model layer (WP01): **correct**
- Snapshot service (WP02): **correct** (immutability enforced by API surface; no update/delete methods)
- Production integration (WP03): **correct** (snapshot created prior to FIFO; costs from snapshot JSON)
- Migration script (WP04): **correct** (idempotent, dry-run supported, backfilled flag set)
- Scale factor UI (WP05): **correct** (validated > 0; propagated to service call)
- Variant service & UI (WP06): **correct** (base_recipe_id, variant_name; variant creation supported)
- Production readiness (WP07): **correct** (model flag + UI filter + form checkbox)
- Recipe history view (WP08): **correct** (history list, details, restore action; backfilled badge)

## Findings

### Critical Issues
- None found that block merge (tests are green; primary architecture is sound).

### Warnings
- **Session management: “commit inside service when session is injected”**
  - `src/services/recipe_snapshot_service.py` (`create_recipe_from_snapshot`) calls `session.commit()` inside the `_..._impl` even when a session is provided by the caller.
  - `src/services/recipe_service.py` (`create_recipe_variant`) similarly commits inside the implementation.
  - **Why it matters**: this breaks the repo’s stated “session parameter means caller controls the transaction” pattern and can cause partial commits inside larger workflows.
  - **Recommended fix**: only `commit()` inside the `session_scope()` path; when `session` is passed, `flush()` and return, leaving commit to the caller.

- **SQLite FK cycle warnings are expected but noisy**
  - The schema contains a cycle: `production_runs.recipe_snapshot_id` ↔ `recipe_snapshots.production_run_id`.
  - This causes SAWarnings during `drop_all` in tests. It’s non-blocking, but you may want to consider `use_alter=True` or a schema/relationship adjustment to mark/avoid the cycle for cleaner teardown.

- **UI-layer filtering for production readiness**
  - `src/ui/recipes_tab.py` filters “Production Ready / Experimental” in the UI via list comprehensions.
  - This is light logic, but if you want strict separation (“no business logic in UI”), consider moving readiness filtering into `recipe_service` (or adding a parameter).

### Observations
- **Snapshot fidelity**: snapshot JSON denormalizes ingredient identity (`ingredient_id`, `ingredient_slug`, `ingredient_name`) plus quantity/unit/notes, which is the right tradeoff for historical stability.
- **Backfill transparency**: history view displays “(approximated)” for `is_backfilled=True` snapshots, which correctly communicates the approximation.
- **Scale-factor mechanics**: `expected_yield = base_yield * scale_factor * num_batches` and consumption uses the same multiplier; this is consistent and test-covered.

## Files Reviewed

| File | Status | Notes |
|------|--------|-------|
| src/models/recipe_snapshot.py | PASS | Model contains required fields + JSON helpers |
| src/models/recipe.py | PASS | Variant + production readiness fields present |
| src/models/production_run.py | PASS | `recipe_snapshot_id` FK present |
| src/services/recipe_snapshot_service.py | PASS w/ warning | Unconditional commit when session injected |
| src/services/batch_production_service.py | PASS | Snapshot created before FIFO; costs from snapshot |
| src/services/recipe_service.py | PASS w/ warning | Variant creation commits even if session injected |
| scripts/migrate_production_snapshots.py | PASS | Backfill script + verify + dry-run; now supports injected session for testability |
| src/ui/forms/record_production_dialog.py | PASS | scale_factor UI, validation, and service integration |
| src/ui/views/recipe_history_view.py | PASS | History list + restore; backfilled badge shown |
| src/ui/forms/recipe_form.py | PASS | Production readiness checkbox in recipe create/edit |
| src/tests/services/test_recipe_snapshot_service.py | PASS | 22/22 |
| src/tests/scripts/test_migrate_production_snapshots.py | PASS | 7/7 |

## Functional Requirements Verification

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FR-001: Immutable snapshot created at production | PASS | `record_batch_production()` creates snapshot before FIFO consumption |
| FR-002: Snapshot contains denormalized recipe/ingredient JSON | PASS | `RecipeSnapshot.recipe_data` / `ingredients_data` |
| FR-003: Snapshots cannot be edited after creation | PASS | Snapshot service exposes create/get only; no update/delete funcs |
| FR-004: Costs calculated from snapshot data | PASS | Production consumption iterates `snapshot["ingredients_data"]` |
| FR-005: scale_factor stored with snapshot | PASS | `RecipeSnapshot.scale_factor` populated |
| FR-006: ProductionRun links to snapshot, not recipe | PASS | `ProductionRun.recipe_snapshot_id` set during production |
| FR-007: num_batches and scale_factor are separate parameters | PASS | Separate args in UI + service |
| FR-008: Expected yield = base x scale x batches | PASS | `expected_yield = int(base_yield * scale_factor * num_batches)` |
| FR-009: Ingredient consumption = base x scale x batches | PASS | `quantity_needed = base_quantity * scale_factor * num_batches` |
| FR-010: base_recipe_id supports variants | PASS | `Recipe.base_recipe_id` + `create_recipe_variant()` |
| FR-014: is_production_ready flag exists | PASS | Model + UI checkbox + filter |
| FR-017: Snapshot history accessible | PASS | `RecipeHistoryView` displays snapshot list |
| FR-018: New recipe can be created from snapshot | PASS | `create_recipe_from_snapshot()` + UI restore button |
| Session management pattern followed | PASS w/ warning | Most functions comply; warnings above re: commit when session injected |
| All existing tests pass (no regressions) | PASS | `1525 passed, 14 skipped, 0 failed` |

## Work Package Verification

| Work Package | Status | Notes |
|--------------|--------|-------|
| WP01: Models Layer | PASS | New snapshot + recipe fields + ProductionRun FK |
| WP02: Snapshot Service | PASS | Create/get APIs; immutability enforced |
| WP03: Production Integration | PASS | Snapshot-first before FIFO; scale_factor supported |
| WP04: Migration Script | PASS | Dry-run + idempotent; backfilled flag set |
| WP05: Scale Factor UI | PASS | UI + validation + propagation |
| WP06: Variant Service & UI | PASS | Variant creation + grouping/filtering support |
| WP07: Production Readiness | PASS | Flag + form toggle + recipes tab filter |
| WP08: Recipe History View | PASS | History UI + restore action + backfilled labeling |

## Code Quality Assessment

### Model Layer (WP01)
| Item | Status | Notes |
|------|--------|-------|
| RecipeSnapshot model exists | Yes | Includes JSON Text fields + helpers |
| JSON helper methods exist | Yes | `get_recipe_data()`, `get_ingredients_data()` |
| is_backfilled flag exists | Yes | Set by migration script |
| ProductionRun.recipe_snapshot_id exists | Yes | Nullable for migration |
| Recipe variant fields exist | Yes | `base_recipe_id`, `variant_name` |
| Recipe readiness flag exists | Yes | `is_production_ready` default False |

### Snapshot Service (WP02)
| Item | Status | Notes |
|------|--------|-------|
| create_recipe_snapshot() exists | Yes | Flushes, returns dict |
| Denormalizes recipe data to JSON | Yes | `recipe_data` |
| Denormalizes ingredients to JSON | Yes | `ingredients_data` |
| get_recipe_snapshots() exists | Yes | Ordered desc |
| get_snapshot_by_production_run() exists | Yes | Returns dict |
| NO update methods exist | Yes | Verified by grep + tests |
| Session management pattern | Yes w/ warning | `create_recipe_from_snapshot()` commits even if session injected |

### Production Integration (WP03)
| Item | Status | Notes |
|------|--------|-------|
| Snapshot created FIRST | Yes | Before FIFO consumption; temp ProductionRun created first to obtain FK id |
| Costs from snapshot data | Yes | Consumption iterates `snapshot["ingredients_data"]` |
| scale_factor parameter added | Yes | UI + service |
| Expected yield calculation correct | Yes | base * scale * batches |
| ProductionRun.recipe_snapshot_id set | Yes | Linked after snapshot creation |

### Migration Script (WP04)
| Item | Status | Notes |
|------|--------|-------|
| Script exists | Yes | `scripts/migrate_production_snapshots.py` |
| dry_run mode works | Yes | Test-covered |
| is_backfilled=True for backfills | Yes | Test-covered |
| Uses produced_at for snapshot_date | Yes | Test-covered |
| Handles deleted recipes | Yes | Skips with warning; test-covered |
| Idempotent | Yes | Test-covered |

### Recipe History View (WP08)
| Item | Status | Notes |
|------|--------|-------|
| RecipeHistoryView exists | Yes | `src/ui/views/recipe_history_view.py` |
| Shows snapshot list | Yes | Newest-first |
| View Details works | Yes | Shows denormalized data |
| Create from snapshot works | Yes | Calls service + confirmation |
| Backfilled badge shown | Yes | “(approximated)” when `is_backfilled` |

## Potential Issues

### Session Management
- See Warnings: avoid `commit()` when `session` is provided by caller.

### Edge Cases
- Snapshot JSON uses `float(...)` for ingredient quantities; if you require high precision, consider preserving Decimals as strings.

### Data Integrity
- FK cycle is intentional for 1:1 relationship but leads to noisy teardown warnings; consider `use_alter=True` or alternate linkage strategy if you want to eliminate the warning.

### FK Cycle Warning
- Known/expected: FK cycle between `production_runs` and `recipe_snapshots` causes teardown warnings under SQLite.

## Conclusion

**APPROVED WITH CHANGES**

Recommended follow-ups:
1. Adjust `create_recipe_from_snapshot()` and `create_recipe_variant()` to avoid committing when a session is injected.
2. Decide whether to keep the FK cycle as-is (acceptable) or implement a schema/DDL strategy (`use_alter=True` or other) to reduce teardown warnings.

