---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
title: "Unit Converter Updates"
phase: "Phase 2 - Service Layer"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "3015"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Unit Converter Updates

## Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- **Primary Objective**: Update unit converter to use Ingredient object instead of hardcoded density lookup
- **Success Criteria**:
  - `convert_volume_to_weight()` accepts optional `ingredient` parameter
  - `convert_weight_to_volume()` accepts optional `ingredient` parameter
  - `convert_any_units()` accepts optional `ingredient` parameter
  - No import of `get_ingredient_density` from constants
  - User-friendly error messages when density unavailable
  - All unit converter tests pass

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/010-user-friendly-ingredient/spec.md` - FR-005, FR-008
- `kitty-specs/010-user-friendly-ingredient/quickstart.md` - Code examples for updated functions

**Dependencies**:
- **Requires WP01 complete**: Ingredient model must have `get_density_g_per_ml()` method

**Key Constraints**:
- Keep `density_g_per_ml` override parameter for backward compatibility and testing
- Remove `ingredient_name` parameter (no more name-based lookup)
- Use TYPE_CHECKING import to avoid circular dependency
- Error messages must be user-friendly (SC-005)

**Existing Code Reference**:
- `src/services/unit_converter.py:17` - Import of `get_ingredient_density`
- `src/services/unit_converter.py:201-250` - `convert_volume_to_weight()`
- `src/services/unit_converter.py:252-301` - `convert_weight_to_volume()`
- `src/services/unit_converter.py:303-356` - `convert_any_units()`

## Subtasks & Detailed Guidance

### Subtask T008 - Update convert_volume_to_weight()

- **Purpose**: Accept Ingredient object for density lookup instead of name-based lookup
- **Steps**:
  1. Open `src/services/unit_converter.py`
  2. Add TYPE_CHECKING import at top of file:
     ```python
     from typing import Optional, Tuple, TYPE_CHECKING

     if TYPE_CHECKING:
         from src.models.ingredient import Ingredient
     ```
  3. Update function signature (around line 201):
     ```python
     def convert_volume_to_weight(
         volume_value: float,
         volume_unit: str,
         weight_unit: str,
         ingredient: "Ingredient" = None,
         density_g_per_ml: float = None,
     ) -> Tuple[bool, float, str]:
     ```
  4. Update function body to use ingredient:
     ```python
     # Get density from ingredient or override
     density = density_g_per_ml
     if density is None and ingredient is not None:
         density = ingredient.get_density_g_per_ml()

     if density is None or density <= 0:
         ingredient_name = ingredient.name if ingredient else "unknown"
         return (
             False,
             0.0,
             f"Density required for conversion. Edit ingredient '{ingredient_name}' to set density.",
         )

     # Convert volume to ml
     success, ml, error = convert_standard_units(volume_value, volume_unit, "ml")
     if not success:
         return False, 0.0, error

     # Calculate weight in grams using density (g/ml)
     grams = ml * density

     # Convert to target weight unit
     success, weight, error = convert_standard_units(grams, "g", weight_unit)
     if not success:
         return False, 0.0, error

     return True, weight, ""
     ```
  5. Update docstring to document new parameters
- **Files**: `src/services/unit_converter.py`
- **Notes**: Error message includes ingredient name to help user identify which ingredient needs density

### Subtask T009 - Update convert_weight_to_volume()

- **Purpose**: Accept Ingredient object for density lookup
- **Steps**:
  1. Update function signature (around line 252):
     ```python
     def convert_weight_to_volume(
         weight_value: float,
         weight_unit: str,
         volume_unit: str,
         ingredient: "Ingredient" = None,
         density_g_per_ml: float = None,
     ) -> Tuple[bool, float, str]:
     ```
  2. Update function body similarly to T008:
     ```python
     # Get density from ingredient or override
     density = density_g_per_ml
     if density is None and ingredient is not None:
         density = ingredient.get_density_g_per_ml()

     if density is None or density <= 0:
         ingredient_name = ingredient.name if ingredient else "unknown"
         return (
             False,
             0.0,
             f"Density required for conversion. Edit ingredient '{ingredient_name}' to set density.",
         )

     # Convert weight to grams
     success, grams, error = convert_standard_units(weight_value, weight_unit, "g")
     if not success:
         return False, 0.0, error

     # Calculate volume in ml using density (g/ml)
     ml = grams / density

     # Convert to target volume unit
     success, volume, error = convert_standard_units(ml, "ml", volume_unit)
     if not success:
         return False, 0.0, error

     return True, volume, ""
     ```
  3. Update docstring
- **Files**: `src/services/unit_converter.py`
- **Notes**: Same pattern as T008 but division instead of multiplication

### Subtask T010 - Update convert_any_units()

- **Purpose**: Accept Ingredient object and pass to underlying conversion functions
- **Steps**:
  1. Update function signature (around line 303):
     ```python
     def convert_any_units(
         value: float,
         from_unit: str,
         to_unit: str,
         ingredient: "Ingredient" = None,
         density_g_per_ml: Optional[float] = None,
     ) -> Tuple[bool, float, str]:
     ```
  2. Update the cross-type conversion calls:
     ```python
     # Volume to weight conversion
     if from_type == "volume" and to_type == "weight":
         if ingredient is None and density_g_per_ml is None:
             return False, 0.0, "Ingredient or density required for volume-to-weight conversion"
         return convert_volume_to_weight(
             value, from_unit, to_unit, ingredient, density_g_per_ml
         )

     # Weight to volume conversion
     if from_type == "weight" and to_type == "volume":
         if ingredient is None and density_g_per_ml is None:
             return False, 0.0, "Ingredient or density required for weight-to-volume conversion"
         return convert_weight_to_volume(
             value, from_unit, to_unit, ingredient, density_g_per_ml
         )
     ```
  3. Update docstring
- **Files**: `src/services/unit_converter.py`
- **Notes**: This is the high-level function most callers will use

### Subtask T011 - Remove get_ingredient_density Import

- **Purpose**: Clean up now-unused import
- **Steps**:
  1. In `src/services/unit_converter.py`, line ~17
  2. Remove: `from src.utils.constants import get_ingredient_density`
  3. Verify no other references to `get_ingredient_density` remain in file
- **Files**: `src/services/unit_converter.py`
- **Notes**: File should now have no dependency on constants.py density functions

### Subtask T012 - Update Unit Converter Tests

- **Purpose**: Update tests to use new function signatures
- **Steps**:
  1. Open `src/tests/services/test_unit_converter.py`
  2. Add imports for Ingredient model:
     ```python
     from src.models.ingredient import Ingredient
     ```
  3. Update existing density conversion tests to pass Ingredient object:
     ```python
     def test_convert_volume_to_weight_with_ingredient():
         """Test volume to weight conversion using ingredient density."""
         ingredient = Ingredient(
             name="All-Purpose Flour",
             slug="all-purpose-flour",
             category="Flour",
             density_volume_value=1.0,
             density_volume_unit="cup",
             density_weight_value=120.0,
             density_weight_unit="g",
         )
         success, weight, error = convert_volume_to_weight(
             1.0, "cup", "g", ingredient=ingredient
         )
         assert success
         assert abs(weight - 120.0) < 0.1
         assert error == ""

     def test_convert_volume_to_weight_no_density():
         """Test conversion fails gracefully when no density."""
         ingredient = Ingredient(
             name="Mystery Ingredient",
             slug="mystery",
             category="Other",
         )
         success, weight, error = convert_volume_to_weight(
             1.0, "cup", "g", ingredient=ingredient
         )
         assert not success
         assert "Density required" in error

     def test_convert_volume_to_weight_with_override():
         """Test density override still works."""
         success, weight, error = convert_volume_to_weight(
             1.0, "cup", "g", density_g_per_ml=0.5
         )
         assert success
         # 1 cup = 236.588 ml, 0.5 g/ml = 118.294 g
         assert abs(weight - 118.294) < 0.1
     ```
  4. Remove tests that rely on name-based density lookup
  5. Run tests: `pytest src/tests/services/test_unit_converter.py -v`
- **Files**: `src/tests/services/test_unit_converter.py`
- **Notes**: Some existing tests may need updating or removal

## Test Strategy

- **Test Command**: `pytest src/tests/services/test_unit_converter.py -v`
- **Key Scenarios**:
  - Volume→weight with ingredient having density
  - Volume→weight with ingredient lacking density (should fail with message)
  - Weight→volume with ingredient having density
  - Weight→volume with ingredient lacking density
  - Override density parameter (for testing)
  - Same-type conversions (no density needed)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking callers that pass ingredient_name | Remove parameter; callers must update |
| Circular import | Use TYPE_CHECKING for Ingredient import |
| Test failures | Update tests to use new signature |

## Definition of Done Checklist

- [x] T008: `convert_volume_to_weight()` accepts `ingredient` parameter
- [x] T009: `convert_weight_to_volume()` accepts `ingredient` parameter
- [x] T010: `convert_any_units()` accepts `ingredient` parameter
- [x] T011: No import of `get_ingredient_density` in unit_converter.py
- [x] T012: All unit converter tests pass
- [x] Error messages are user-friendly and actionable
- [x] Docstrings updated

## Review Guidance

- Verify TYPE_CHECKING import prevents circular dependency
- Check error messages include ingredient name for user context
- Confirm density_g_per_ml override still works (for testing)
- Verify no remaining references to hardcoded density lookup

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-05T03:09:47Z – claude – shell_pid=3015 – lane=doing – Starting implementation
- 2025-12-05T03:45:00Z – claude – shell_pid=3015 – lane=doing – Completed all subtasks T008-T012; all 75 unit converter tests pass
