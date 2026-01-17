# Implementation Plan: Unified Yield Management

**Branch**: `056-unified-yield-management` | **Date**: 2026-01-16 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification consolidating redundant yield data into unified FinishedUnit-based yield types

## Summary

This feature eliminates redundant yield tracking by deprecating Recipe-level `yield_quantity`, `yield_unit`, and `yield_description` fields in favor of FinishedUnit as the single source of truth. Each recipe must have at least one complete FinishedUnit with `display_name`, `item_unit`, and `items_per_batch`. A standalone transformation script converts existing recipe data during the export/transform/import cycle.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (Windows, macOS, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Instant UI responsiveness; import/export handles 100+ recipes
**Constraints**: Single-user desktop; no in-app migration per Constitution VI
**Scale/Scope**: ~50 recipes, 1 user

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | ✅ PASS | Unified UI eliminates confusion; intuitive 3-field row |
| II. Data Integrity & FIFO | ✅ PASS | Export/transform/import preserves 100% of yield data |
| III. Future-Proof Schema | ✅ PASS | FinishedUnit already has item_unit (nullable); will become required |
| IV. Test-Driven Development | ✅ PASS | Validation logic, transformation script, import service all testable |
| V. Layered Architecture | ✅ PASS | UI → Services → Models; no layer violations |
| VI. Schema Change Strategy | ✅ PASS | Using export/transform/import cycle; standalone script in scripts/ |
| VII. Pragmatic Aspiration | ✅ PASS | Desktop phase; service layer UI-independent; supports web migration |

**No violations. No Complexity Tracking required.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/056-unified-yield-management/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity changes documentation
├── checklists/          # Quality checklists
└── tasks.md             # Phase 2 output (NOT created by /spec-kitty.plan)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── recipe.py           # Deprecate yield_quantity, yield_unit, yield_description
│   └── finished_unit.py    # item_unit required for DISCRETE_COUNT mode
├── services/
│   ├── recipe_service.py              # Add at-least-one-FinishedUnit validation
│   ├── finished_unit_service.py       # Existing; minor updates
│   ├── coordinated_export_service.py  # Export FinishedUnits; update recipe export
│   └── catalog_import_service.py      # Import FinishedUnits; legacy yield handling
├── ui/
│   ├── forms/
│   │   └── recipe_form.py  # Remove legacy yield fields; add item_unit to YieldTypeRow
│   └── finished_units_tab.py  # Verify columns show item_unit
└── tests/
    ├── test_recipe_service.py
    ├── test_finished_unit_service.py
    ├── services/
    │   └── test_coordinated_export.py
    └── integration/
        └── test_import_export_roundtrip.py

scripts/
└── transform_yield_data.py  # Standalone transformation script (temporary)

test_data/
├── sample_data_min.json     # Must be transformed
└── sample_data_all.json     # Must be transformed
```

**Structure Decision**: Single project with new `scripts/` directory for transformation script.

## Implementation Phases

### Phase 1: Data Model & Validation (Foundation)

**Objective**: Establish the data foundation without breaking existing functionality.

1. **Recipe Model Updates** (`src/models/recipe.py`)
   - Mark `yield_quantity`, `yield_unit`, `yield_description` as nullable
   - Add deprecation comments

2. **FinishedUnit Model Updates** (`src/models/finished_unit.py`)
   - Add validation: `item_unit` required when `yield_mode` is DISCRETE_COUNT
   - Existing `items_per_batch` and `display_name` already present

3. **Service Layer Validation** (`src/services/recipe_service.py`)
   - Add `validate_recipe_has_finished_unit()` function
   - Enforce at least one complete FinishedUnit per recipe on save
   - Return validation errors for incomplete yield types

4. **Tests**
   - Unit tests for new validation logic
   - Test that incomplete FinishedUnits are rejected
   - Test that recipes without FinishedUnits are rejected

### Phase 2: Transformation Script

**Objective**: Create standalone script to convert legacy data.

1. **Script**: `scripts/transform_yield_data.py`
   - Read JSON export files
   - For each recipe: create FinishedUnit entry from yield fields
   - Generate unique slugs with collision handling
   - Write transformed JSON
   - Process `sample_data_min.json` and `sample_data_all.json`

2. **Slug Generation Strategy**
   - Pattern: `{recipe_slug}_{yield_suffix}`
   - Suffix: slugify(yield_description) or "standard"
   - Collision: append _2, _3, etc.

3. **Tests**
   - Test transformation with yield_description present
   - Test transformation without yield_description (default generation)
   - Test slug collision handling

### Phase 3: Import/Export Service Updates

**Objective**: Enable import/export of FinishedUnits and handle legacy data.

1. **Export Service** (`src/services/coordinated_export_service.py`)
   - Add `_export_finished_units()` function
   - Add "finished_units" to `DEPENDENCY_ORDER`
   - Include all FinishedUnit fields: slug, display_name, item_unit, items_per_batch, etc.

2. **Import Service** (`src/services/catalog_import_service.py`)
   - Add "finished_units" to `VALID_ENTITIES`
   - Add `_import_finished_units_impl()` function
   - Handle legacy recipes: if recipe has yield fields but no FinishedUnits, create one
   - Generate display_name: use yield_description or "Standard {recipe_name}"

3. **Tests**
   - Export roundtrip test with FinishedUnits
   - Import legacy recipe creates FinishedUnit
   - Import with explicit FinishedUnits preserves them

### Phase 4: UI Updates

**Objective**: Unify the yield editing experience.

1. **YieldTypeRow Widget** (`src/ui/forms/recipe_form.py`)
   - Add `item_unit` field (text entry or combo box)
   - Update `get_data()` to include item_unit
   - Update `__init__()` to accept item_unit parameter

2. **Recipe Form** (`src/ui/forms/recipe_form.py`)
   - Remove top-level yield_quantity and yield_unit fields
   - Ensure at least one yield type row is required
   - Update validation to require complete yield type
   - Disable "Remove" button when only one row exists

3. **Finished Units Tab** (`src/ui/finished_units_tab.py`)
   - Verify columns display item_unit correctly
   - Verify double-click navigation works

4. **Tests**
   - Visual verification (manual)
   - Test form data extraction includes item_unit

### Phase 5: Integration & Cleanup

**Objective**: End-to-end validation and data migration.

1. **Transform Test Data**
   - Run transformation script on sample_data_min.json
   - Run transformation script on sample_data_all.json
   - Verify import of transformed data
   - Verify Finished Units tab displays all records

2. **Full Workflow Test**
   - Export current database
   - Run transformation
   - Import transformed data
   - Create new recipe with yield types
   - Edit existing recipe yield types
   - Verify batch calculation still works

3. **Documentation**
   - Update user documentation if exists
   - Add migration notes for future reference

## Dependencies & Risks

### Dependencies
- Existing FinishedUnit model structure (already has required fields)
- Existing YieldTypeRow widget pattern (already supports dynamic rows)
- Import/Export service patterns (well-established)

### Risks
| Risk | Mitigation |
|------|------------|
| Data loss during transformation | Script validates output; backup before transform |
| Incomplete yield types in existing data | Default generation creates sensible display_name |
| UI confusion during transition | Clear validation messages guide user |

## Files Modified (Summary)

| File | Changes |
|------|---------|
| `src/models/recipe.py` | Make yield fields nullable |
| `src/models/finished_unit.py` | Add item_unit validation |
| `src/services/recipe_service.py` | Add FinishedUnit validation |
| `src/services/coordinated_export_service.py` | Add FinishedUnit export |
| `src/services/catalog_import_service.py` | Add FinishedUnit import, legacy handling |
| `src/ui/forms/recipe_form.py` | Remove legacy yield fields, add item_unit |
| `scripts/transform_yield_data.py` | NEW: Standalone transformation script |
| `test_data/sample_data_min.json` | Transformed |
| `test_data/sample_data_all.json` | Transformed |
