# Data Model: F098 Auto-Generation of Finished Goods

**Feature**: 098-auto-generation-finished-goods
**Date**: 2026-02-08

## Schema Changes

**No new tables or columns required.** All existing models support the feature:

### Existing Entities (No Changes)

#### FinishedGood (`src/models/finished_good.py`)
- `assembly_type`: Already has `AssemblyType.BARE` and `AssemblyType.BUNDLE`
- `display_name`, `slug`, `description`, `notes`: Inherited from FU at auto-creation
- No new fields needed

#### FinishedUnit (`src/models/finished_unit.py`)
- `display_name`, `recipe_id`, `yield_type`, `category`: Source fields for auto-generation
- No new fields needed

#### Composition (`src/models/composition.py`)
- `assembly_id` → FK to FinishedGood (the bare FG)
- `finished_unit_id` → FK to FinishedUnit (the source FU)
- `component_quantity`: Always 1 for bare FGs
- 4-way XOR constraint already enforces single component type
- `create_unit_composition()` factory method already exists

### AssemblyType Enum (`src/models/assembly_type.py`)
- `BARE = "bare"` — Already exists with metadata: min=1, max=1, recommended=1
- `BUNDLE = "bundle"` — User-built assemblies

## Relationship Diagram

```
Recipe (1) ──has-many──> FinishedUnit (*)
                              │
                              │ auto-generates (1:1, bare only)
                              ▼
                         Composition ──links-to──> FinishedGood (assembly_type=BARE)
                              │
                              │ (bare FG can be component of assembled FG)
                              ▼
                         Composition ──links-to──> FinishedGood (assembly_type=BUNDLE)
```

## Key Queries

### Find bare FG for a given FU
```
Composition WHERE finished_unit_id = :fu_id
  JOIN FinishedGood ON FinishedGood.id = Composition.assembly_id
  WHERE FinishedGood.assembly_type = 'bare'
```

### Find all assembly references to a bare FG
```
Composition WHERE finished_good_id = :bare_fg_id
```
(If count > 0, bare FG cannot be deleted)

### List all bare FGs (auto-managed)
```
FinishedGood WHERE assembly_type = 'bare'
```

### List all assembled FGs (user-managed)
```
FinishedGood WHERE assembly_type = 'bundle'
```

## Service Layer Changes

### New Functions

#### `recipe_service.save_recipe_with_yields()`
Orchestrates the entire recipe save atomically:
1. Create/update Recipe
2. Reconcile FinishedUnits (create new, update existing, delete removed)
3. For each created/updated FU: auto-create/update bare FG + Composition
4. For each deleted FU: cascade-delete bare FG (with assembly protection check)
5. All in single session

#### `finished_good_service.auto_create_bare_finished_good()`
Creates a bare FG + single Composition for a given FU. Accepts session parameter.

#### `finished_good_service.sync_bare_finished_good()`
Updates bare FG name/category when source FU changes. Accepts session parameter.

#### `finished_good_service.find_bare_fg_for_unit()`
Looks up the bare FG linked to a given FU via Composition query.

### Modified Functions

#### `finished_unit_service.create_finished_unit()`
Add `session: Optional[Session] = None` parameter.

#### `finished_unit_service.update_finished_unit()`
Add `session: Optional[Session] = None` parameter.

#### `finished_unit_service.delete_finished_unit()`
Add `session: Optional[Session] = None` parameter.

### UI Changes

#### `recipes_tab.py`
- Remove `_save_yield_types()` method
- Replace with single call to `recipe_service.save_recipe_with_yields()`
- UI passes yield type data; service handles all orchestration

## Validation Rules

1. **Uniqueness**: One bare FG per FU (enforced by checking existing Composition before creation)
2. **Assembly protection**: Cannot delete bare FG if referenced by any assembly (check `Composition.finished_good_id`)
3. **Name propagation**: FU name change → bare FG name change (same transaction)
4. **Category propagation**: FU category change → bare FG category change (same transaction)
