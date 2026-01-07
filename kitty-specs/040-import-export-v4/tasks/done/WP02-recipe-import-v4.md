---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
  - "T011"
title: "Recipe Import v4.0"
phase: "Phase 1 - Core Schema Upgrade"
lane: "done"
assignee: ""
agent: "claude-reviewer"
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

# Work Package Prompt: WP02 - Recipe Import v4.0

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Update recipe import to handle F037 fields with proper dependency ordering
- Import base recipes before variants (resolve base_recipe_slug to base_recipe_id)
- Import variant_name, is_production_ready fields
- Import linked finished_units[] with yield_mode
- Validate all references exist before creating records

**Success Criteria**:
- Import a JSON file with variant recipes, verify database contains correct relationships
- Base recipe exists before variant is imported
- FinishedUnits created with correct yield_mode

## Context & Constraints

**Related Documents**:
- `kitty-specs/040-import-export-v4/spec.md` - User Story 1 acceptance criteria
- `kitty-specs/040-import-export-v4/data-model.md` - Recipe import schema
- `kitty-specs/040-import-export-v4/research.md` - Key decision D1

**Key Constraints**:
- Must import base recipes before variants to resolve base_recipe_slug
- All ingredient_slugs must reference existing ingredients
- FinishedUnit creation requires recipe to exist first
- Follow session management pattern from CLAUDE.md

**File to Modify**: `src/services/import_export_service.py`

**Dependencies**: WP01 must be complete (export needed for round-trip testing)

## Subtasks & Detailed Guidance

### Subtask T006 - Sort recipes for import order

**Purpose**: Ensure base recipes are imported before variants that reference them.

**Steps**:
1. In recipe import function, before iterating recipes:
2. Partition recipes into two groups:
   - Base recipes: where `base_recipe_slug` is None or empty
   - Variant recipes: where `base_recipe_slug` has a value
3. Process base recipes first, then variant recipes

**Code Pattern**:
```python
recipes_data = data.get("recipes", [])
base_recipes = [r for r in recipes_data if not r.get("base_recipe_slug")]
variant_recipes = [r for r in recipes_data if r.get("base_recipe_slug")]

# Import base recipes first
for recipe_data in base_recipes:
    _import_single_recipe(recipe_data, session, result)

# Then import variants
for recipe_data in variant_recipes:
    _import_single_recipe(recipe_data, session, result)
```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - foundational for import logic

### Subtask T007 - Resolve base_recipe_slug to base_recipe_id

**Purpose**: Convert human-readable slug back to FK during import.

**Steps**:
1. In `_import_single_recipe()` or equivalent:
2. If `recipe_data.get("base_recipe_slug")`:
   - Query `Recipe.slug == base_recipe_slug`
   - If found: set `recipe.base_recipe_id = base_recipe.id`
   - If not found: add error to result, skip this recipe

**Code Pattern**:
```python
base_recipe_slug = recipe_data.get("base_recipe_slug")
if base_recipe_slug:
    base_recipe = session.query(Recipe).filter_by(slug=base_recipe_slug).first()
    if not base_recipe:
        result.add_error("recipe", recipe_data.get("name"),
            f"Base recipe not found: {base_recipe_slug}")
        continue
    recipe.base_recipe_id = base_recipe.id
```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - sequential logic

### Subtask T008 - Import variant_name, is_production_ready

**Purpose**: Import the F037 fields from JSON to model.

**Steps**:
1. Add field mappings in recipe import:
   ```python
   recipe.variant_name = recipe_data.get("variant_name")
   recipe.is_production_ready = recipe_data.get("is_production_ready", False)
   ```
2. Default is_production_ready to False if not present (matches model default)

**Files**: `src/services/import_export_service.py`
**Parallel?**: Yes - can be done alongside T007

### Subtask T009 - Import finished_units[] with yield_mode

**Purpose**: Create FinishedUnit records linked to imported recipe.

**Steps**:
1. After recipe is created and flushed (has ID):
2. Iterate `recipe_data.get("finished_units", [])`:
   - Check if FinishedUnit with slug already exists (for merge mode)
   - Create new FinishedUnit with:
     - `recipe_id = recipe.id`
     - `slug`, `name`, `unit_yield_quantity`, `unit_yield_unit`
     - `yield_mode` - convert string to enum

**Code Pattern**:
```python
from src.models.finished_unit import YieldMode

for fu_data in recipe_data.get("finished_units", []):
    existing = session.query(FinishedUnit).filter_by(slug=fu_data.get("slug")).first()
    if existing and mode == "merge":
        continue  # Skip existing in merge mode

    yield_mode_str = fu_data.get("yield_mode")
    yield_mode = YieldMode(yield_mode_str) if yield_mode_str else YieldMode.DISCRETE_COUNT

    finished_unit = FinishedUnit(
        recipe_id=recipe.id,
        slug=fu_data.get("slug"),
        name=fu_data.get("name"),
        yield_mode=yield_mode,
        unit_yield_quantity=fu_data.get("unit_yield_quantity"),
        unit_yield_unit=fu_data.get("unit_yield_unit"),
    )
    session.add(finished_unit)
```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - requires recipe to exist first

**Notes**:
- Check FinishedUnit model for all required fields
- Handle yield_mode enum conversion carefully

### Subtask T010 - Validation for recipe import

**Purpose**: Ensure data integrity before creating records.

**Steps**:
1. Validate base_recipe_slug exists (if provided) - covered in T007
2. Validate all ingredient_slugs in recipe.ingredients reference existing ingredients
3. Validate yield_mode is valid enum value
4. Add clear error messages for each validation failure

**Code Pattern**:
```python
# Validate ingredients
for ing_data in recipe_data.get("ingredients", []):
    slug = ing_data.get("ingredient_slug")
    if not session.query(Ingredient).filter_by(slug=slug).first():
        result.add_error("recipe", recipe_data.get("name"),
            f"Ingredient not found: {slug}")
        return  # Skip this recipe

# Validate yield_mode
for fu_data in recipe_data.get("finished_units", []):
    yield_mode_str = fu_data.get("yield_mode")
    if yield_mode_str and yield_mode_str not in [e.value for e in YieldMode]:
        result.add_error("recipe", recipe_data.get("name"),
            f"Invalid yield_mode: {yield_mode_str}")
```

**Files**: `src/services/import_export_service.py`
**Parallel?**: No - validation logic

### Subtask T011 - Unit tests for recipe import v4.0

**Purpose**: Verify all import scenarios work correctly.

**Steps**:
1. Create test class `TestRecipeImportV4` in test file
2. Test cases:
   - `test_import_base_recipe_with_f037_fields`: Import recipe with variant_name, is_production_ready
   - `test_import_variant_recipe`: Import variant with base_recipe_slug, verify FK set
   - `test_import_recipe_with_finished_units`: Import recipe with finished_units, verify yield_mode
   - `test_import_variant_before_base_fails`: Import JSON with variant first, verify error
   - `test_import_invalid_base_recipe_slug`: Reference non-existent base, verify error
   - `test_import_recipe_roundtrip`: Export then import, verify identical

**Files**: `src/tests/services/test_import_export_service.py`
**Parallel?**: No - tests after implementation

## Test Strategy

**Required Tests**:
```bash
pytest src/tests/services/test_import_export_service.py::TestRecipeImportV4 -v
```

**Test Data**:
- Create JSON fixture with base recipe and variant recipe
- Create JSON fixture with FinishedUnits containing different yield_modes

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular variant references | Sorting by base_recipe_slug handles simple cases |
| Duplicate slug conflict | Check existing before insert, handle merge mode |
| Invalid yield_mode enum | Validate before creating FinishedUnit |

## Definition of Done Checklist

- [x] T006: Recipes sorted before import (base before variants)
- [x] T007: base_recipe_slug resolves to base_recipe_id
- [x] T008: variant_name, is_production_ready imported
- [x] T009: finished_units[] created with yield_mode
- [x] T010: Validation errors are clear and actionable
- [x] T011: All unit tests pass
- [x] Round-trip export -> import preserves all data

## Review Guidance

- Test import ordering with complex variant chains
- Verify merge mode doesn't duplicate FinishedUnits
- Check error messages are user-friendly
- Confirm FK relationships are correct after import

## Activity Log

- 2026-01-06T12:00:00Z - system - lane=planned - Prompt created.
- 2026-01-07T03:01:52Z – claude – shell_pid=89028 – lane=doing – Started implementation
- 2026-01-07T03:45:00Z – claude – shell_pid=89028 – lane=doing – Completed T006-T011: Added recipe sorting (base before variants), base_recipe_slug resolution, F037 field imports, finished_units import with yield_mode, validation, and 6 unit tests. All tests passing.
- 2026-01-07T03:10:33Z – claude – shell_pid=89028 – lane=for_review – Moved to for_review
- 2026-01-07T05:43:51Z – claude-reviewer – shell_pid=89028 – lane=done – Approved: Tests pass, code follows spec patterns
