---
work_package_id: "WP03"
subtasks:
  - "T013"
  - "T014"
  - "T015"
  - "T016"
  - "T017"
title: "Ingredient Service Updates"
phase: "Phase 2 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Ingredient Service Updates

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

- **Primary Objective**: Add density field validation and update CRUD operations to handle 4-field density
- **Success Criteria**:
  - `validate_density_fields()` enforces all-or-nothing rule (FR-002)
  - `create_ingredient()` accepts and validates 4 density fields
  - `update_ingredient()` accepts and validates 4 density fields
  - Validation rejects partial density input with clear error message
  - Validation rejects non-positive values
  - Validation rejects invalid units
  - All service tests pass

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/010-user-friendly-ingredient/spec.md` - FR-002, FR-003, FR-004, FR-007
- `kitty-specs/010-user-friendly-ingredient/data-model.md` - Validation rules

**Dependencies**:
- **Requires WP01 complete**: Ingredient model must have 4 density fields
- **Requires WP02 complete**: Unit converter tests should pass

**Key Constraints**:
- Validation error messages must be user-friendly (Constitution Principle IV)
- All-or-nothing: If any density field provided, all 4 must be provided
- Values must be positive (> 0)
- Units must be valid VOLUME_UNITS / WEIGHT_UNITS

**Existing Code Reference**:
- `src/services/ingredient_service.py` - Current create/update functions

## Subtasks & Detailed Guidance

### Subtask T013 - Add validate_density_fields() Function

- **Purpose**: Enforce all-or-nothing validation for density field group
- **Steps**:
  1. Open `src/services/ingredient_service.py`
  2. Add imports:
     ```python
     from typing import Tuple, Optional
     from src.utils.constants import VOLUME_UNITS, WEIGHT_UNITS
     ```
  3. Add validation function:
     ```python
     def validate_density_fields(
         volume_value: Optional[float],
         volume_unit: Optional[str],
         weight_value: Optional[float],
         weight_unit: Optional[str],
     ) -> Tuple[bool, str]:
         """
         Validate density field group (all or nothing).

         Args:
             volume_value: Volume amount (e.g., 1.0)
             volume_unit: Volume unit (e.g., "cup")
             weight_value: Weight amount (e.g., 4.25)
             weight_unit: Weight unit (e.g., "oz")

         Returns:
             Tuple of (is_valid, error_message)
         """
         # Normalize empty strings to None
         fields = [
             volume_value if volume_value not in (None, "", 0) else None,
             volume_unit if volume_unit not in (None, "") else None,
             weight_value if weight_value not in (None, "", 0) else None,
             weight_unit if weight_unit not in (None, "") else None,
         ]

         filled_count = sum(1 for f in fields if f is not None)

         # All empty is valid (no density)
         if filled_count == 0:
             return True, ""

         # Partially filled is invalid
         if filled_count < 4:
             return False, "All density fields must be provided together"

         # Validate positive values
         if volume_value <= 0:
             return False, "Volume value must be greater than zero"

         if weight_value <= 0:
             return False, "Weight value must be greater than zero"

         # Validate unit types
         volume_unit_lower = volume_unit.lower()
         if volume_unit_lower not in [u.lower() for u in VOLUME_UNITS]:
             return False, f"Invalid volume unit: {volume_unit}"

         weight_unit_lower = weight_unit.lower()
         if weight_unit_lower not in [u.lower() for u in WEIGHT_UNITS]:
             return False, f"Invalid weight unit: {weight_unit}"

         return True, ""
     ```
- **Files**: `src/services/ingredient_service.py`
- **Notes**: Empty string treated same as None for validation purposes

### Subtask T014 - Update create_ingredient()

- **Purpose**: Accept and validate 4 density fields when creating ingredients
- **Steps**:
  1. Locate `create_ingredient()` function in `src/services/ingredient_service.py`
  2. Add density parameters to function signature:
     ```python
     def create_ingredient(
         name: str,
         category: str,
         recipe_unit: str = None,
         description: str = None,
         notes: str = None,
         density_volume_value: float = None,
         density_volume_unit: str = None,
         density_weight_value: float = None,
         density_weight_unit: str = None,
     ) -> Ingredient:
     ```
  3. Add validation before creating ingredient:
     ```python
     # Validate density fields
     is_valid, error = validate_density_fields(
         density_volume_value,
         density_volume_unit,
         density_weight_value,
         density_weight_unit,
     )
     if not is_valid:
         raise ValidationError(error)
     ```
  4. Pass density fields to Ingredient constructor:
     ```python
     ingredient = Ingredient(
         name=name,
         slug=generate_slug(name),
         category=category,
         recipe_unit=recipe_unit,
         description=description,
         notes=notes,
         density_volume_value=density_volume_value,
         density_volume_unit=density_volume_unit,
         density_weight_value=density_weight_value,
         density_weight_unit=density_weight_unit,
     )
     ```
  5. Update docstring
- **Files**: `src/services/ingredient_service.py`
- **Notes**: ValidationError should already be imported from exceptions

### Subtask T015 - Update update_ingredient()

- **Purpose**: Accept and validate 4 density fields when updating ingredients
- **Steps**:
  1. Locate `update_ingredient()` function
  2. Add density parameters to function signature (similar to T014)
  3. Add validation before updating:
     ```python
     # Validate density fields if any are being updated
     is_valid, error = validate_density_fields(
         density_volume_value,
         density_volume_unit,
         density_weight_value,
         density_weight_unit,
     )
     if not is_valid:
         raise ValidationError(error)
     ```
  4. Update the ingredient fields:
     ```python
     if density_volume_value is not None:
         ingredient.density_volume_value = density_volume_value
     if density_volume_unit is not None:
         ingredient.density_volume_unit = density_volume_unit
     if density_weight_value is not None:
         ingredient.density_weight_value = density_weight_value
     if density_weight_unit is not None:
         ingredient.density_weight_unit = density_weight_unit
     ```
  5. Update docstring
- **Files**: `src/services/ingredient_service.py`
- **Notes**: Need to handle case where user wants to clear density (pass explicit None for all 4)

### Subtask T016 - Add Density Validation Tests [PARALLEL]

- **Purpose**: Verify density validation works correctly
- **Steps**:
  1. Open/create `src/tests/services/test_ingredient_service.py`
  2. Add test cases:
     ```python
     def test_validate_density_fields_all_empty():
         """Empty density fields are valid."""
         is_valid, error = validate_density_fields(None, None, None, None)
         assert is_valid
         assert error == ""

     def test_validate_density_fields_all_filled():
         """All density fields filled with valid data."""
         is_valid, error = validate_density_fields(1.0, "cup", 4.25, "oz")
         assert is_valid
         assert error == ""

     def test_validate_density_fields_partial():
         """Partial density fields fail validation."""
         is_valid, error = validate_density_fields(1.0, "cup", None, None)
         assert not is_valid
         assert "All density fields must be provided together" in error

     def test_validate_density_fields_zero_volume():
         """Zero volume value fails validation."""
         is_valid, error = validate_density_fields(0, "cup", 4.25, "oz")
         assert not is_valid
         assert "greater than zero" in error

     def test_validate_density_fields_negative_weight():
         """Negative weight value fails validation."""
         is_valid, error = validate_density_fields(1.0, "cup", -1.0, "oz")
         assert not is_valid
         assert "greater than zero" in error

     def test_validate_density_fields_invalid_volume_unit():
         """Invalid volume unit fails validation."""
         is_valid, error = validate_density_fields(1.0, "invalid", 4.25, "oz")
         assert not is_valid
         assert "Invalid volume unit" in error

     def test_validate_density_fields_invalid_weight_unit():
         """Invalid weight unit fails validation."""
         is_valid, error = validate_density_fields(1.0, "cup", 4.25, "invalid")
         assert not is_valid
         assert "Invalid weight unit" in error
     ```
- **Files**: `src/tests/services/test_ingredient_service.py`
- **Parallel?**: Yes - can proceed alongside T017
- **Notes**: Test both happy paths and error cases

### Subtask T017 - Fix Broken Tests [PARALLEL]

- **Purpose**: Update existing tests that reference old density field
- **Steps**:
  1. Run all tests: `pytest src/tests -v`
  2. Identify failing tests that reference `density_g_per_ml`
  3. Update tests to use new 4-field density model
  4. Common fixes:
     - Replace `density_g_per_ml=0.5` with 4 density fields
     - Update assertions that check `density_g_per_ml`
     - Remove tests for `get_ingredient_density()` function
  5. Re-run tests until all pass
- **Files**: Various test files in `src/tests/`
- **Parallel?**: Yes - can proceed alongside T016
- **Notes**: May span multiple test files; fix systematically

## Test Strategy

- **Test Command**: `pytest src/tests/services/test_ingredient_service.py -v`
- **Full Suite**: `pytest src/tests -v` (after T017)
- **Key Scenarios**:
  - Create ingredient with density
  - Create ingredient without density
  - Create ingredient with partial density (should fail)
  - Update ingredient density
  - Clear ingredient density
  - All validation error cases

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing create/update callers | Add parameters with defaults |
| Test failures across codebase | T017 dedicated to fixing |
| Validation edge cases | Thorough test coverage |

## Definition of Done Checklist

- [ ] T013: `validate_density_fields()` function implemented
- [ ] T014: `create_ingredient()` accepts and validates density fields
- [ ] T015: `update_ingredient()` accepts and validates density fields
- [ ] T016: Validation tests pass
- [ ] T017: All broken tests fixed
- [ ] `pytest src/tests -v` passes with no errors
- [ ] Error messages are user-friendly

## Review Guidance

- Verify all-or-nothing validation works correctly
- Check error messages are clear and actionable
- Confirm edge cases handled (0, negative, empty string)
- Verify unit validation uses case-insensitive comparison

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
