# Implementation Plan: Ingredient Auto-Slug & Deletion Protection

**Branch**: `035-ingredient-auto-slug` | **Date**: 2026-01-02 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/035-ingredient-auto-slug/spec.md`

## Summary

Implement Phase 3 of the ingredient hierarchy enhancement: automatic slug generation during ingredient creation (verify/fix existing implementation), comprehensive deletion protection for catalog entities (Products, Recipes), and historical data preservation through denormalization before ingredient deletion.

**Key Research Findings**:
- Slug generation already exists and is integrated - needs field mapping fix only
- Clear Filters already implemented in F034 - removed from scope
- Deletion protection incomplete - needs Product check and denormalization logic

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter, SQLAlchemy 2.x, SQLite
**Storage**: SQLite with WAL mode (schema auto-recreated)
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS/Windows)
**Project Type**: Single desktop application
**Performance Goals**: N/A (single user)
**Constraints**: Must follow layered architecture (UI → Services → Models)
**Scale/Scope**: Single user, ~100-500 ingredients

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Deletion protection prevents accidental data corruption |
| II. Data Integrity & FIFO | PASS | Preserves referential integrity, historical data |
| III. Future-Proof Schema | PASS | Denormalization fields are nullable, backward compatible |
| IV. Test-Driven Development | PASS | All service methods will have tests |
| V. Layered Architecture | PASS | All logic in services, UI only calls services |
| VI. Schema Change Strategy | PASS | Using export/reset/import cycle, no migrations |
| VII. Pragmatic Aspiration | PASS | Clean service layer enables future web migration |

## Project Structure

### Documentation (this feature)

```
kitty-specs/035-ingredient-auto-slug/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Schema change documentation
├── research/            # Evidence logs
│   ├── evidence-log.csv
│   └── source-register.csv
└── tasks.md             # Phase 2 output (from /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── inventory_snapshot.py  # MODIFY: Add 3 denorm fields, change FK
│   ├── ingredient_alias.py    # VERIFY: Cascade delete config
│   └── ingredient_crosswalk.py # VERIFY: Cascade delete config
├── services/
│   └── ingredient_service.py  # MODIFY: Add deletion protection
└── tests/
    └── services/
        └── test_ingredient_service.py  # ADD: Deletion tests
```

**Structure Decision**: Single project structure with existing layout. Changes confined to models and services layers.

## Complexity Tracking

*No constitution violations - standard implementation within existing patterns.*

## Implementation Phases

### Phase 1: Schema Update (SnapshotIngredient)

**Files**: `src/models/inventory_snapshot.py`

**Changes**:
1. Add `ingredient_name_snapshot` column (String(200), nullable)
2. Add `parent_l1_name_snapshot` column (String(200), nullable)
3. Add `parent_l0_name_snapshot` column (String(200), nullable)
4. Change `ingredient_id` FK from `ondelete="RESTRICT"` to `ondelete="SET NULL"`
5. Make `ingredient_id` nullable

**Schema Migration**: Per constitution, use export/reset/import. Update import/export service to handle new fields.

### Phase 2: Verify Cascade Deletes

**Files**: `src/models/ingredient_alias.py`, `src/models/ingredient_crosswalk.py`

**Verification**:
1. Check current FK configuration
2. Ensure `ondelete="CASCADE"` is set
3. Add if missing

### Phase 3: Enhance Deletion Service

**File**: `src/services/ingredient_service.py`

**New/Modified Functions**:

```python
def can_delete_ingredient(ingredient_id: int, session=None) -> Tuple[bool, str, Dict]:
    """
    Check if ingredient can be deleted.

    Returns:
        Tuple of (can_delete, reason, details)
        - can_delete: True if deletion allowed
        - reason: Error message if blocked
        - details: Dict with counts {products: N, recipes: N, children: N, snapshots: N}
    """

def delete_ingredient_safe(ingredient_id: int, session=None) -> bool:
    """
    Safely delete an ingredient with full protection.

    1. Check can_delete_ingredient()
    2. If blocked, raise IngredientInUse with details
    3. Denormalize SnapshotIngredient records
    4. Nullify SnapshotIngredient.ingredient_id
    5. Delete ingredient (cascades Alias/Crosswalk)
    """

def _denormalize_snapshot_ingredients(ingredient_id: int, session) -> int:
    """
    Copy ingredient names to snapshot records before deletion.

    Returns count of records denormalized.
    """
```

### Phase 4: Field Mapping Fix

**File**: `src/services/ingredient_service.py`

**Change**: Add field normalization at start of `create_ingredient()`:

```python
def create_ingredient(ingredient_data: Dict[str, Any]) -> Ingredient:
    # Normalize field names for backward compatibility
    if "name" in ingredient_data and "display_name" not in ingredient_data:
        ingredient_data["display_name"] = ingredient_data["name"]
    ...
```

### Phase 5: Update UI Delete Handler

**File**: `src/ui/ingredients_tab.py`

**Change**: Update `_delete()` method to use new `delete_ingredient_safe()` and display detailed blocking reasons.

### Phase 6: Tests

**File**: `src/tests/services/test_ingredient_service.py`

**New Test Cases**:
1. `test_delete_blocked_by_products` - Verify deletion blocked when products exist
2. `test_delete_blocked_by_recipes` - Verify deletion blocked when recipes exist
3. `test_delete_blocked_by_children` - Verify deletion blocked when children exist
4. `test_delete_with_snapshots_denormalizes` - Verify denormalization before delete
5. `test_delete_cascades_aliases` - Verify aliases cascade deleted
6. `test_delete_cascades_crosswalks` - Verify crosswalks cascade deleted
7. `test_slug_auto_generation` - Verify slug created from name
8. `test_slug_conflict_resolution` - Verify _1, _2 suffix on conflicts

## Out of Scope (Removed from Original Spec)

Based on research findings:

1. **Clear Filters buttons** - Already implemented in F034
2. **New slug generation utility** - Already exists in `src/utils/slug_utils.py`
3. **Slug integration in service** - Already exists, just needs field mapping fix

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Schema change breaks import | Update import/export service to handle new nullable fields |
| Deletion denormalization fails mid-transaction | Use single atomic transaction, rollback on any failure |
| Cascade delete misconfigured | Verify with explicit tests before merge |

## Dependencies

- **F033 (Phase 1)**: `get_child_count()`, `get_ancestors()` services - AVAILABLE
- **F034 (Phase 2)**: Clear Filters - COMPLETE (removed from our scope)

## Success Metrics

From spec, updated based on research:

- **SC-001**: Slug auto-generation works (verify existing, fix if needed)
- **SC-002**: Zero orphaned Products/Recipes from deletion
- **SC-003**: Historical snapshots preserve ingredient names after deletion
- **SC-005**: Deletion messages show counts of blocking references

**SC-004 (Clear Filters)**: Already complete from F034 - verified.

## Next Steps

1. Run `/spec-kitty.tasks` to generate work packages
2. Implement in order: Schema → Cascade Verify → Service → UI → Tests
3. Run acceptance tests
4. Merge to main
