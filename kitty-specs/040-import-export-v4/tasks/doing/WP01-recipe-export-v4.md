---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Recipe Export v4.0"
phase: "Phase 1 - Core Schema Upgrade"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "89028"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-06T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Recipe Export v4.0

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Update `export_recipes_to_json()` to include F037 fields: `base_recipe_slug`, `variant_name`, `is_production_ready`
- Export linked `finished_units[]` array with `yield_mode` for each recipe
- Maintain backward compatibility in export format (existing fields unchanged)
- Unit tests verify all new fields are correctly exported

**Success Criteria**:
- Export a database with variant recipes and verify JSON contains all new fields
- Export a recipe with multiple FinishedUnits and verify yield_mode is present for each

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - User Story 1 acceptance criteria
- `kitty-specs/040-import-export-v4/plan.md` - Technical context
- `kitty-specs/040-import-export-v4/data-model.md` - Recipe export schema
- `kitty-specs/040-import-export-v4/research.md` - Key decision D1

**Key Constraints**:
- Recipe model has `base_recipe_id` (FK), must convert to `base_recipe_slug` for export
- FinishedUnit has `yield_mode` enum with values: DISCRETE_COUNT, BATCH_PORTION, WEIGHT_BASED
- Follow session management pattern from CLAUDE.md (pass session to inner functions)

**File to Modify**: `src/services/import_export_service.py`

## Subtasks & Detailed Guidance

### Subtask T001 - Export base_recipe_slug

**Purpose**: Convert base_recipe_id FK to human-readable slug for portability.

**Steps**:
1. In `export_recipes_to_json()`, after building the recipe dict
2. If `recipe.base_recipe_id` is not None:
   - Query `Recipe` by ID to get the base recipe
   - Add `recipe_dict["base_recipe_slug"] = base_recipe.slug`
3. If `recipe.base_recipe_id` is None:
   - Add `recipe_dict["base_recipe_slug"] = None`

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes - can be done alongside T002, T003

**Code Pattern**:
```python
recipe_dict["base_recipe_slug"] = None
if recipe.base_recipe_id:
    base_recipe = session.query(Recipe).filter_by(id=recipe.base_recipe_id).first()
    if base_recipe:
        recipe_dict["base_recipe_slug"] = base_recipe.slug
```

### Subtask T002 - Export variant_name

**Purpose**: Include the variant name field added by F037.

**Steps**:
1. Add `recipe_dict["variant_name"] = recipe.variant_name` to export dict
2. Field can be None for non-variant recipes

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes

### Subtask T003 - Export is_production_ready

**Purpose**: Include the production readiness flag added by F037.

**Steps**:
1. Add `recipe_dict["is_production_ready"] = recipe.is_production_ready` to export dict
2. Default value is False for new recipes

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes

### Subtask T004 - Export finished_units[] with yield_mode

**Purpose**: Include all FinishedUnits related to the recipe with their yield_mode.

**Steps**:
1. Access `recipe.finished_units` relationship (already joined via lazy="joined")
2. Build finished_units array with each unit's key fields:
   ```python
   recipe_dict["finished_units"] = [
       {
           "slug": fu.slug,
           "name": fu.name,
           "yield_mode": fu.yield_mode.value if fu.yield_mode else None,
           "unit_yield_quantity": fu.unit_yield_quantity,
           "unit_yield_unit": fu.unit_yield_unit,
       }
       for fu in recipe.finished_units
   ]
   ```
3. If no finished_units, export empty array `[]`

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - depends on understanding full export structure

**Notes**:
- `yield_mode` is an enum, must call `.value` to get string
- Check if FinishedUnit model has other required fields (review `src/models/finished_unit.py`)

### Subtask T005 - Unit tests for recipe export v4.0

**Purpose**: Verify all new export fields work correctly.

**Steps**:
1. Create test class `TestRecipeExportV4` in `src/tests/services/test_import_export_service.py`
2. Test cases:
   - `test_export_recipe_with_variant_fields`: Create recipe with variant_name, is_production_ready, verify export
   - `test_export_recipe_with_base_recipe`: Create base and variant recipes, verify base_recipe_slug exported
   - `test_export_recipe_with_finished_units`: Create recipe with FinishedUnits, verify yield_mode exported
   - `test_export_recipe_without_variant`: Non-variant recipe exports null for base_recipe_slug, variant_name

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: No - tests should be written after implementation

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/services/test_import_export_service.py::TestRecipeExportV4 -v
```

**Test Data Setup**:
- Create Recipe with base_recipe_id pointing to another Recipe
- Create Recipe with variant_name and is_production_ready=True
- Create FinishedUnit with yield_mode=YieldMode.DISCRETE_COUNT linked to recipe

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Performance with many recipes | Use joinedload for finished_units (already configured) |
| Missing base_recipe (orphan FK) | Handle gracefully - export null if not found |
| Enum serialization | Call `.value` on yield_mode enum |

## Definition of Done Checklist

- [ ] T001: base_recipe_slug exported correctly
- [ ] T002: variant_name exported correctly
- [ ] T003: is_production_ready exported correctly
- [ ] T004: finished_units[] array with yield_mode exported
- [ ] T005: All unit tests pass
- [ ] Export file can be parsed as valid JSON
- [ ] Existing fields unchanged (backward compatible)

## Review Guidance

- Verify export JSON matches schema in `data-model.md`
- Check null handling for optional fields
- Confirm enum values are strings, not Python objects
- Test with real sample data export

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T02:51:32Z – claude – shell_pid=89028 – lane=doing – Started implementation
