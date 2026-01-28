# Research: Snapshot Export Coverage

**Feature**: F081 Snapshot Export Coverage
**Date**: 2026-01-28
**Status**: Complete

## Executive Summary

This research confirms that adding export/import support for 4 snapshot entity types is straightforward following existing patterns in `coordinated_export_service.py` and `enhanced_import_service.py`.

## Snapshot Model Analysis

### RecipeSnapshot (F037)

**File**: `src/models/recipe_snapshot.py`

| Field | Type | Export Key | Notes |
|-------|------|------------|-------|
| uuid | UUID | uuid | Preserve exactly |
| recipe_id | FK | recipe_slug | Resolve via Recipe.slug |
| recipe_data | JSON Text | recipe_data | Preserve as-is |
| ingredients_data | JSON Text | ingredients_data | Preserve as-is |
| snapshot_date | DateTime | snapshot_date | ISO format |
| scale_factor | Float | scale_factor | |
| is_backfilled | Boolean | is_backfilled | |

**Parent Resolution**: Recipe via `recipe_slug` field (F080 pattern)

### FinishedGoodSnapshot (F064)

**File**: `src/models/finished_good_snapshot.py`

| Field | Type | Export Key | Notes |
|-------|------|------------|-------|
| uuid | UUID | uuid | Preserve exactly |
| finished_good_id | FK | finished_good_slug | Resolve via FinishedGood.slug |
| definition_data | JSON Text | definition_data | Preserve as-is |
| snapshot_date | DateTime | snapshot_date | ISO format |
| is_backfilled | Boolean | is_backfilled | |

**Parent Resolution**: FinishedGood via `finished_good_slug` field

### MaterialUnitSnapshot (F064)

**File**: `src/models/material_unit_snapshot.py`

| Field | Type | Export Key | Notes |
|-------|------|------------|-------|
| uuid | UUID | uuid | Preserve exactly |
| material_unit_id | FK | material_unit_slug | Resolve via MaterialUnit.slug |
| definition_data | JSON Text | definition_data | Preserve as-is |
| snapshot_date | DateTime | snapshot_date | ISO format |
| is_backfilled | Boolean | is_backfilled | |

**Parent Resolution**: MaterialUnit via `material_unit_slug` field

### FinishedUnitSnapshot (F064)

**File**: `src/models/finished_unit_snapshot.py`

| Field | Type | Export Key | Notes |
|-------|------|------------|-------|
| uuid | UUID | uuid | Preserve exactly |
| finished_unit_id | FK | finished_unit_slug | Resolve via FinishedUnit.slug |
| definition_data | JSON Text | definition_data | Preserve as-is |
| snapshot_date | DateTime | snapshot_date | ISO format |
| is_backfilled | Boolean | is_backfilled | |

**Parent Resolution**: FinishedUnit via `finished_unit_slug` field

## Existing Patterns

### Export Pattern (coordinated_export_service.py)

```python
def _export_finished_units(output_dir: Path, session: Session) -> FileEntry:
    """Export all finished units to JSON file with FK resolution."""
    units = session.query(FinishedUnit).options(joinedload(FinishedUnit.recipe)).all()

    records = []
    for fu in units:
        records.append({
            "uuid": str(fu.uuid) if fu.uuid else None,
            "slug": fu.slug,
            # FK resolved by slug
            "recipe_slug": fu.recipe.slug if fu.recipe else None,
            # ... other fields
        })

    return _write_entity_file(output_dir, "finished_units", records)
```

### Import Pattern (coordinated_export_service.py)

```python
elif entity_type == "finished_units":
    # Resolve recipe FK by slug (with fallback)
    recipe_slug = record.get("recipe_slug")
    recipe_name = record.get("recipe_name")

    recipe_id = _resolve_recipe(recipe_slug, recipe_name, session, context="FinishedUnit")

    if not recipe_id:
        continue  # Skip if recipe not found

    obj = FinishedUnit(
        recipe_id=recipe_id,
        # ... other fields from record
    )
    session.add(obj)
    imported_count += 1
```

### Dependency Order Pattern

```python
DEPENDENCY_ORDER = {
    "recipes": (4, ["ingredients"]),
    "finished_units": (5, ["recipes"]),  # After recipes
    # ...
}
```

## Design Decisions

### Decision 1: Export Chronological Order

**Chosen**: Export snapshots ordered by `snapshot_date` (oldest first)

**Rationale**:
- Maintains audit trail integrity
- Natural for understanding cost history progression
- Matches functional spec requirement FR-015

### Decision 2: Skip Missing Parents on Import

**Chosen**: Skip snapshots with unresolvable parent slugs, log warning

**Rationale**:
- Matches existing behavior (see `_import_entity_records` patterns)
- Partial imports should continue, not fail entirely
- Warning log allows administrator to identify issues

### Decision 3: UUID Preservation

**Chosen**: Use exact UUIDs from export (no regeneration)

**Rationale**:
- Ensures referential integrity across export-import cycles
- Matches FR-010 requirement
- Existing BaseModel includes UUID field

### Decision 4: JSON Data Preservation

**Chosen**: Copy `recipe_data`, `ingredients_data`, `definition_data` exactly

**Rationale**:
- No transformation or validation of JSON content
- Historical snapshots must be exact replicas
- Matches FR-012 requirement

### Decision 5: Dependency Order

**Chosen**: Snapshots import AFTER their parent entities

**Rationale**:
- FK resolution requires parent to exist
- Matches existing dependency patterns in DEPENDENCY_ORDER

**Import Order** (additions):
- recipe_snapshots: (19, ["recipes"])
- finished_good_snapshots: (20, ["finished_goods"])
- material_unit_snapshots: (21, ["material_units"])
- finished_unit_snapshots: (22, ["finished_units"])

## Implementation Approach

### Phase 1: Export Functions

1. Add 4 export functions following `_export_finished_units()` pattern
2. Register in DEPENDENCY_ORDER
3. Call from `_export_complete_impl()` after parent entities
4. Update manifest with snapshot file counts

### Phase 2: Import Functions

1. Add 4 entity_type handlers in `_import_entity_records()`
2. Resolve parent FK via slug lookup
3. Skip with warning if parent not found
4. Preserve UUID, timestamps, and JSON data exactly

### Phase 3: Tests

1. Unit tests for each export function
2. Unit tests for each import handler
3. Round-trip integration test
4. Missing parent handling test

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Parent not found on import | Medium | Low | Skip with warning, continue import |
| JSON malformed | Low | Low | Preserve as-is per FR-012 |
| Circular dependencies | None | N/A | Snapshots don't reference each other |
| Performance with large snapshot counts | Low | Medium | Order by timestamp, batch if needed |

## Conclusion

The implementation is straightforward:
- Follow existing export/import patterns
- Add 4 export functions + 4 import handlers
- Register in dependency order
- Test round-trip integrity

No architectural changes or new patterns required.
