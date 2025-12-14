---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "Model & Schema Deletion"
phase: "Phase 1 - Model Changes"
lane: "done"
assignee: "claude"
agent: "claude"
shell_pid: "21650"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-14T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Model & Schema Deletion

## Objectives & Success Criteria

- Delete the `UnitConversion` model file entirely
- Remove `recipe_unit` column from `Ingredient` model
- Remove `conversions` relationship from `Ingredient` model
- Application starts without import errors after changes

**Success Test**: Run `python -c "from src.models import *; print('OK')"` - must succeed.

## Context & Constraints

- **Spec**: `kitty-specs/019-unit-conversion-simplification/spec.md`
- **Plan**: `kitty-specs/019-unit-conversion-simplification/plan.md`
- **Constitution**: `.kittify/memory/constitution.md` (schema changes via export/reset/import)

**Critical**: This is a destructive change to the data model. The database will need to be reset after these changes. Do NOT attempt to run the application against an existing database after making these changes - it will fail.

## Subtasks & Detailed Guidance

### Subtask T001 – Delete unit_conversion.py

- **Purpose**: Remove the vestigial UnitConversion model that is no longer needed.
- **Steps**:
  1. Delete the file `src/models/unit_conversion.py`
  2. Verify the file is gone: `ls src/models/unit_conversion.py` should fail
- **Files**: `src/models/unit_conversion.py` (DELETE)
- **Parallel?**: No - must complete before T002
- **Notes**: This file contains ~230 lines including helper functions. All functionality is replaced by density-based conversion in `unit_converter.py`.

### Subtask T002 – Update models/__init__.py

- **Purpose**: Remove the import and export of UnitConversion from the models package.
- **Steps**:
  1. Open `src/models/__init__.py`
  2. Remove the line: `from .unit_conversion import UnitConversion`
  3. Remove `UnitConversion` from the `__all__` list if present
  4. Remove any helper function imports from unit_conversion (e.g., `get_conversion`, `convert_quantity`)
- **Files**: `src/models/__init__.py` (EDIT)
- **Parallel?**: No - depends on T001
- **Notes**: Search for all references to `unit_conversion` in this file.

### Subtask T003 – Remove recipe_unit column from Ingredient

- **Purpose**: Remove the vestigial `recipe_unit` column that duplicates `RecipeIngredient.unit`.
- **Steps**:
  1. Open `src/models/ingredient.py`
  2. Find and delete the line: `recipe_unit = Column(String(50), nullable=True)` (approximately line 64)
  3. Update the class docstring to remove reference to `recipe_unit` attribute
- **Files**: `src/models/ingredient.py` (EDIT)
- **Parallel?**: No - should be done with T004
- **Notes**: The docstring lists `recipe_unit` in the Attributes section - remove that too.

### Subtask T004 – Remove conversions relationship from Ingredient

- **Purpose**: Remove the relationship to the deleted UnitConversion model.
- **Steps**:
  1. In `src/models/ingredient.py`, find the `conversions` relationship definition
  2. Delete the entire relationship block:
     ```python
     conversions = relationship(
         "UnitConversion", back_populates="ingredient", cascade="all, delete-orphan", lazy="select"
     )
     ```
  3. This should be around lines 100-102
- **Files**: `src/models/ingredient.py` (EDIT)
- **Parallel?**: No - should be done with T003
- **Notes**: The `to_dict()` method may reference `self.conversions` - check and remove if present.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Import errors cascade | Test imports after each file change |
| Missed references | Grep for `UnitConversion` and `recipe_unit` across all models |
| Database incompatibility | Do not run against existing DB - reset required |

## Definition of Done Checklist

- [ ] `src/models/unit_conversion.py` deleted
- [ ] `src/models/__init__.py` has no UnitConversion references
- [ ] `src/models/ingredient.py` has no `recipe_unit` column
- [ ] `src/models/ingredient.py` has no `conversions` relationship
- [ ] `python -c "from src.models import *"` succeeds
- [ ] No remaining references to UnitConversion in `src/models/` directory

## Review Guidance

- Verify all four files are correctly modified
- Check that no import errors occur
- Confirm no leftover references in docstrings or comments
- Note: Application will NOT run against existing database until full migration complete

## Activity Log

- 2025-12-14T12:00:00Z – system – lane=planned – Prompt created.
- 2025-12-14T07:35:14Z – claude – shell_pid=21650 – lane=doing – Started implementation
- 2025-12-14T19:51:14Z – claude – shell_pid=21650 – lane=for_review – Implementation complete, ready for review
- 2025-12-14T19:52:27Z – claude – shell_pid=21650 – lane=done – Code review APPROVED: All DoD items verified - model deleted, references removed, imports work
