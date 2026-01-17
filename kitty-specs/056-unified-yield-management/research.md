# Research: Unified Yield Management

**Feature**: 056-unified-yield-management
**Date**: 2026-01-16

## Research Questions

### 1. Current Recipe Yield Fields

**Decision**: Recipe has three yield fields that will be deprecated.

**Findings** (`src/models/recipe.py`, lines 59-62):
```python
yield_quantity = Column(Float, nullable=False)
yield_unit = Column(String(50), nullable=False)
yield_description = Column(String(200), nullable=True)
```

- `yield_quantity`: Required float (e.g., 24, 36, 1)
- `yield_unit`: Required string (e.g., "cookies", "each", "batch")
- `yield_description`: Optional string (e.g., "2-inch cookies", "9-inch round")

**Rationale**: These fields duplicate what FinishedUnit already captures. Making them nullable first allows gradual migration.

### 2. Current FinishedUnit Model

**Decision**: FinishedUnit has all required fields; only needs validation enhancement.

**Findings** (`src/models/finished_unit.py`, lines 84-98):
```python
yield_mode = Column(Enum(YieldMode), nullable=False, default=YieldMode.DISCRETE_COUNT)
items_per_batch = Column(Integer, nullable=True)
item_unit = Column(String(50), nullable=True)  # Already exists!
batch_percentage = Column(Numeric(5, 2), nullable=True)
portion_description = Column(String(200), nullable=True)
```

**Key Insight**: `item_unit` already exists as nullable. For DISCRETE_COUNT mode, this field needs to be required but the column definition can stay nullable (validation at service layer).

**Rationale**: No schema change needed for item_unit; just add validation.

### 3. YieldTypeRow Widget Structure

**Decision**: Extend existing widget with item_unit field.

**Findings** (`src/ui/forms/recipe_form.py`, lines 390-478):
- Constructor accepts: `finished_unit_id`, `display_name`, `items_per_batch`
- Missing: `item_unit` parameter
- UI has: Name entry, Quantity entry, Remove button
- Missing: Unit entry field

**Current get_data()** returns:
```python
{"id": finished_unit_id, "display_name": name, "items_per_batch": items_per_batch}
```

**Required change**: Add item_unit to both constructor and get_data().

### 4. Import/Export Gap Analysis

**Decision**: Add FinishedUnit to both export and import services.

**Export Gap** (`src/services/coordinated_export_service.py`):
- `DEPENDENCY_ORDER` does not include "finished_units"
- No `_export_finished_units()` function exists
- Recipes are exported with yield fields but no linked FinishedUnits

**Import Gap** (`src/services/catalog_import_service.py`):
- `VALID_ENTITIES` does not include "finished_units"
- No `_import_finished_units_impl()` function exists
- Legacy handling needed for recipes without FinishedUnits

**Rationale**: Full roundtrip requires both export and import support.

### 5. Finished Units Tab Display

**Decision**: Tab already displays correctly; no changes needed.

**Findings** (`src/ui/widgets/data_table.py`, lines 407-447):
- Columns: Name, Recipe, Category, Type, Yield Info
- Yield Info format: `"{items_per_batch} {item_unit}/batch"` for discrete count
- Double-click opens recipe edit dialog

**Note**: The tab already formats `item_unit` in display. Just need to ensure data is populated.

### 6. Transformation Script Location

**Decision**: Standalone script in `scripts/` directory.

**Alternatives Considered**:
- (A) Standalone in `scripts/` - CHOSEN
- (B) CLI command in `src/utils/import_export_cli.py`
- (C) Jupyter notebook

**Rationale**: Transformation is one-time development task, not a permanent feature. Keeping it in `scripts/` makes it clearly temporary and removable after migration.

### 7. Slug Generation Strategy

**Decision**: Pattern `{recipe_slug}_{yield_suffix}` with collision handling.

**Findings**: Existing slugify patterns in codebase use:
- Recipe: `slugify(name)` from `src/utils/helpers.py`
- Ingredient: similar pattern

**Collision Strategy**:
```python
base_slug = f"{recipe_slug}_{yield_suffix}"
if slug_exists(base_slug):
    append _2, _3, etc. until unique
```

**Example outputs**:
- "chocolate_chip_cookie_standard"
- "sugar_cookie_large_sugar_cookie"
- "yellow_cake_9inch_round"

### 8. Validation Timing

**Decision**: Validate at recipe save time in service layer.

**Current Validation** (`src/ui/forms/recipe_form.py`, lines 1343-1406):
- Form allows empty yield type rows (skipped)
- Warning (not error) if no yield types defined
- Partial rows require both name AND quantity

**New Validation Requirements**:
- At least one COMPLETE yield type (display_name + item_unit + items_per_batch)
- Block save if no complete yield types
- Service layer enforces (UI validates first, service is authoritative)

## Summary of Decisions

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Recipe yield fields | Mark nullable, deprecate | Gradual migration |
| FinishedUnit schema | No change needed | item_unit already exists |
| Validation | Service layer | Single source of truth |
| Script location | scripts/ directory | Temporary, removable |
| Slug pattern | recipe_slug + yield_suffix | Unique, readable |
| Export/Import | Add to both services | Full roundtrip support |
| UI changes | Extend YieldTypeRow | Minimal disruption |
