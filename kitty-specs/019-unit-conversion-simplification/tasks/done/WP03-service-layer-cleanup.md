---
work_package_id: "WP03"
subtasks:
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
title: "Service Layer Cleanup"
phase: "Phase 2 - Service Updates"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: "23019"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Service Layer Cleanup

## Objectives & Success Criteria

- Remove all `recipe_unit` references from service layer
- Remove all `UnitConversion` references from service layer
- Rename parameter in `format_ingredient_conversion()` for clarity
- All services import cleanly with no undefined attribute errors

**Success Test**: `python -c "from src.services import *; print('OK')"` succeeds.

## Context & Constraints

- **Spec**: `kitty-specs/019-unit-conversion-simplification/spec.md`
- **Plan**: `kitty-specs/019-unit-conversion-simplification/plan.md`
- **Research**: `kitty-specs/019-unit-conversion-simplification/research.md` (lists all affected files)
- **Depends on**: WP01, WP02

**Files with recipe_unit references** (from research.md):
- `src/services/unit_converter.py`
- `src/services/ingredient_service.py`
- `src/services/recipe_service.py`
- `src/services/product_service.py`
- `src/services/inventory_item_service.py`
- `src/services/ingredient_crud_service.py`
- `src/services/finished_unit_service.py`
- `src/services/assembly_service.py`

## Subtasks & Detailed Guidance

### Subtask T011 – Rename recipe_unit param in unit_converter.py

- **Purpose**: The `format_ingredient_conversion()` function has a misleading parameter name.
- **Steps**:
  1. Open `src/services/unit_converter.py`
  2. Find `format_ingredient_conversion()` function (~lines 392-410)
  3. Rename parameter `recipe_unit` to `target_unit`
  4. Update the docstring to reflect the new parameter name
  5. Update the format string that uses the parameter
- **Files**: `src/services/unit_converter.py` (EDIT)
- **Parallel?**: No - should be done first
- **Notes**: This is a signature change - check if any callers need updating.

### Subtask T012 – Clean ingredient_service.py

- **Purpose**: Remove UnitConversion and recipe_unit references.
- **Steps**:
  1. Open `src/services/ingredient_service.py`
  2. Grep for `UnitConversion` and `recipe_unit`
  3. Remove any imports of UnitConversion
  4. Remove any code that accesses `ingredient.recipe_unit`
  5. Remove any code that queries or creates UnitConversion records
- **Files**: `src/services/ingredient_service.py` (EDIT)
- **Parallel?**: No
- **Notes**: This service likely has the most UnitConversion interaction.

### Subtask T013 – Clean recipe_service.py

- **Purpose**: Remove recipe_unit references.
- **Steps**:
  1. Open `src/services/recipe_service.py`
  2. Grep for `recipe_unit`
  3. Remove or update any code that references `ingredient.recipe_unit`
  4. Most references are likely in docstrings or comments - update or remove
- **Files**: `src/services/recipe_service.py` (EDIT)
- **Parallel?**: Yes - can be done with T014-T018
- **Notes**: Recipes use `RecipeIngredient.unit`, not `Ingredient.recipe_unit`.

### Subtask T014 – Clean product_service.py

- **Purpose**: Remove recipe_unit references.
- **Steps**:
  1. Open `src/services/product_service.py`
  2. Grep for `recipe_unit`
  3. Remove or update any code that references the field
- **Files**: `src/services/product_service.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: Products have their own units - recipe_unit references may be minimal.

### Subtask T015 – Clean inventory_item_service.py

- **Purpose**: Remove recipe_unit references.
- **Steps**:
  1. Open `src/services/inventory_item_service.py`
  2. Grep for `recipe_unit`
  3. Remove or update any code that references the field
- **Files**: `src/services/inventory_item_service.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: Inventory tracks in purchase units, not recipe units.

### Subtask T016 – Clean ingredient_crud_service.py

- **Purpose**: Remove recipe_unit from CRUD operations.
- **Steps**:
  1. Open `src/services/ingredient_crud_service.py`
  2. Grep for `recipe_unit`
  3. Remove recipe_unit from create/update operations
  4. Remove from any validation or serialization logic
- **Files**: `src/services/ingredient_crud_service.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: This service handles ingredient creation - likely has recipe_unit in parameters.

### Subtask T017 – Clean finished_unit_service.py

- **Purpose**: Remove recipe_unit references.
- **Steps**:
  1. Open `src/services/finished_unit_service.py`
  2. Grep for `recipe_unit`
  3. Remove or update any code that references the field
- **Files**: `src/services/finished_unit_service.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: Finished units relate to recipes - check for indirect references.

### Subtask T018 – Clean assembly_service.py

- **Purpose**: Remove recipe_unit references.
- **Steps**:
  1. Open `src/services/assembly_service.py`
  2. Grep for `recipe_unit`
  3. Remove or update any code that references the field
- **Files**: `src/services/assembly_service.py` (EDIT)
- **Parallel?**: Yes
- **Notes**: Assembly may reference ingredient units - verify logic is preserved.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Hidden dependencies | Full grep of `src/services/` for both terms |
| Logic changes masked as cleanup | Review each change for semantic impact |
| Caller breakage from T011 | Search for callers of `format_ingredient_conversion` |

## Definition of Done Checklist

- [ ] `format_ingredient_conversion()` param renamed to `target_unit`
- [ ] No UnitConversion imports in any service file
- [ ] No `recipe_unit` references in any service file
- [ ] `grep -r "recipe_unit" src/services/` returns only the renamed parameter
- [ ] `grep -r "UnitConversion" src/services/` returns nothing
- [ ] All services import without errors

## Review Guidance

- Verify the parameter rename doesn't break any callers
- Check that no business logic was accidentally removed
- Ensure docstrings are updated where references were removed
- Run `python -c "from src.services import *"` to verify imports

## Activity Log

- 2025-12-14T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-14T07:42:19Z – claude – shell_pid=23019 – lane=doing – Moved to doing
- 2025-12-14T19:51:32Z – claude – shell_pid=23019 – lane=for_review – Implementation complete, ready for review
- 2025-12-14T19:53:13Z – claude – shell_pid=23019 – lane=done – Code review APPROVED: UnitConversion removed from services, consume_fifo uses target_unit
