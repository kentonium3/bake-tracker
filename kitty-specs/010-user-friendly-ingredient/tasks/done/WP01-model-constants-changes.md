---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
  - "T006"
  - "T007"
title: "Model & Constants Changes"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "13066"
review_status: "approved"
reviewed_by: "claude-reviewer"
history:
  - timestamp: "2025-12-04T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Model & Constants Changes

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

- **Primary Objective**: Replace `density_g_per_ml` field with 4-field density model on Ingredient; remove hardcoded density fallback
- **Success Criteria**:
  - `density_g_per_ml` column removed from Ingredient model
  - Four new nullable columns added: `density_volume_value`, `density_volume_unit`, `density_weight_value`, `density_weight_unit`
  - `get_density_g_per_ml()` method calculates correct density from 4 fields
  - `INGREDIENT_DENSITIES` dict and `get_ingredient_density()` function removed from constants.py
  - Tests pass for the new density calculation method

## Context & Constraints

**Prerequisite Documents**:
- `kitty-specs/010-user-friendly-ingredient/spec.md` - FR-001, FR-005, FR-007, FR-009
- `kitty-specs/010-user-friendly-ingredient/data-model.md` - Schema details
- `kitty-specs/010-user-friendly-ingredient/quickstart.md` - Code examples

**Key Constraints**:
- Use local import in `get_density_g_per_ml()` to avoid circular dependency
- All 4 density fields must be nullable (ingredients can have no density)
- `density_volume_unit` uses `String(20)` to match existing unit field sizes
- This is a breaking schema change - database will be deleted and recreated

**Existing Code Reference**:
- `src/models/ingredient.py:70` - Current `density_g_per_ml` field
- `src/utils/constants.py:370-476` - `INGREDIENT_DENSITIES` dict and lookup function

## Subtasks & Detailed Guidance

### Subtask T001 - Remove density_g_per_ml Field

- **Purpose**: Remove the old technical density field to make room for the 4-field model
- **Steps**:
  1. Open `src/models/ingredient.py`
  2. Locate line ~70: `density_g_per_ml = Column(Float, nullable=True)`
  3. Delete this line
  4. Update the docstring to remove reference to `density_g_per_ml`
- **Files**: `src/models/ingredient.py`
- **Notes**: This will cause immediate breakage in tests/code that reference this field - expected and will be fixed

### Subtask T002 - Add 4 Density Fields

- **Purpose**: Add user-friendly density specification fields
- **Steps**:
  1. In `src/models/ingredient.py`, in the "Physical properties" section (around line 69)
  2. Add the following columns:
     ```python
     # User-friendly density specification (4-field model)
     # Example: "1 cup = 4.25 oz" stored as (1.0, "cup", 4.25, "oz")
     density_volume_value = Column(Float, nullable=True)
     density_volume_unit = Column(String(20), nullable=True)
     density_weight_value = Column(Float, nullable=True)
     density_weight_unit = Column(String(20), nullable=True)
     ```
  3. Update docstring to document new fields
- **Files**: `src/models/ingredient.py`
- **Notes**: All fields nullable to allow ingredients without density specification

### Subtask T003 - Add get_density_g_per_ml() Method

- **Purpose**: Calculate internal density from user-friendly 4-field input
- **Steps**:
  1. Add method to Ingredient class:
     ```python
     def get_density_g_per_ml(self) -> Optional[float]:
         """
         Calculate density in g/ml from the 4-field specification.

         Returns:
             Density in grams per milliliter, or None if density not specified.
         """
         if not all([
             self.density_volume_value,
             self.density_volume_unit,
             self.density_weight_value,
             self.density_weight_unit
         ]):
             return None

         # Local import to avoid circular dependency
         from src.services.unit_converter import convert_standard_units

         # Convert volume to ml
         success, ml, _ = convert_standard_units(
             self.density_volume_value,
             self.density_volume_unit,
             "ml"
         )
         if not success or ml <= 0:
             return None

         # Convert weight to grams
         success, grams, _ = convert_standard_units(
             self.density_weight_value,
             self.density_weight_unit,
             "g"
         )
         if not success or grams <= 0:
             return None

         return grams / ml
     ```
  2. Add `Optional` to imports if not present: `from typing import Optional`
- **Files**: `src/models/ingredient.py`
- **Notes**: Returns None for invalid/incomplete data rather than raising exceptions

### Subtask T004 - Add format_density_display() Method

- **Purpose**: Format density for user-friendly display in UI
- **Steps**:
  1. Add method to Ingredient class:
     ```python
     def format_density_display(self) -> str:
         """Format density for UI display."""
         if not self.get_density_g_per_ml():
             return "Not set"
         return (
             f"{self.density_volume_value:g} {self.density_volume_unit} = "
             f"{self.density_weight_value:g} {self.density_weight_unit}"
         )
     ```
- **Files**: `src/models/ingredient.py`
- **Notes**: Uses `:g` format to strip trailing zeros (1.0 → "1")

### Subtask T005 - Remove INGREDIENT_DENSITIES Dict [PARALLEL]

- **Purpose**: Remove hardcoded density fallback data
- **Steps**:
  1. Open `src/utils/constants.py`
  2. Delete the entire section from line ~364-450:
     ```python
     # ============================================================================
     # Ingredient Density Data (for volume-to-weight conversions)
     # ============================================================================

     # Standard densities in grams per cup
     INGREDIENT_DENSITIES: Dict[str, float] = {
         ...
     }
     ```
  3. Remove `Dict` from typing imports if no longer needed
- **Files**: `src/utils/constants.py`
- **Parallel?**: Yes - can proceed alongside T006
- **Notes**: ~80 lines of hardcoded data being removed

### Subtask T006 - Remove get_ingredient_density() Function [PARALLEL]

- **Purpose**: Remove the lookup function that uses hardcoded densities
- **Steps**:
  1. In `src/utils/constants.py`, delete the function (lines ~453-476):
     ```python
     def get_ingredient_density(ingredient_name: str) -> float:
         ...
     ```
- **Files**: `src/utils/constants.py`
- **Parallel?**: Yes - can proceed alongside T005
- **Notes**: This will break unit_converter.py - to be fixed in WP02

### Subtask T007 - Add Tests for get_density_g_per_ml()

- **Purpose**: Verify density calculation works correctly
- **Steps**:
  1. Create or update `src/tests/models/test_ingredient.py`
  2. Add test cases:
     ```python
     def test_get_density_g_per_ml_with_valid_fields():
         """Test density calculation with all fields set."""
         ingredient = Ingredient(
             name="Test Flour",
             slug="test-flour",
             category="Flour",
             density_volume_value=1.0,
             density_volume_unit="cup",
             density_weight_value=4.25,
             density_weight_unit="oz",
         )
         density = ingredient.get_density_g_per_ml()
         assert density is not None
         # 1 cup = 236.588 ml, 4.25 oz = 120.49 g
         # Expected: ~0.509 g/ml
         assert abs(density - 0.509) < 0.01

     def test_get_density_g_per_ml_without_fields():
         """Test that missing density fields return None."""
         ingredient = Ingredient(
             name="Test",
             slug="test",
             category="Flour",
         )
         assert ingredient.get_density_g_per_ml() is None

     def test_get_density_g_per_ml_partial_fields():
         """Test that partial density fields return None."""
         ingredient = Ingredient(
             name="Test",
             slug="test",
             category="Flour",
             density_volume_value=1.0,
             density_volume_unit="cup",
             # weight fields missing
         )
         assert ingredient.get_density_g_per_ml() is None

     def test_format_density_display():
         """Test user-friendly density formatting."""
         ingredient = Ingredient(
             name="Test",
             slug="test",
             category="Flour",
             density_volume_value=1.0,
             density_volume_unit="cup",
             density_weight_value=4.25,
             density_weight_unit="oz",
         )
         assert ingredient.format_density_display() == "1 cup = 4.25 oz"

     def test_format_density_display_not_set():
         """Test format when density not set."""
         ingredient = Ingredient(name="Test", slug="test", category="Flour")
         assert ingredient.format_density_display() == "Not set"
     ```
- **Files**: `src/tests/models/test_ingredient.py`
- **Notes**: Tests should run standalone; may need fixture setup

## Test Strategy

- **Test Command**: `pytest src/tests/models/test_ingredient.py -v`
- **Coverage**: 5 test cases covering:
  - Valid density calculation
  - No density fields
  - Partial density fields
  - Display formatting (with density)
  - Display formatting (no density)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Circular import (ingredient → converter) | Use local import inside method |
| Breaking existing tests | Expected; will be fixed in subsequent WPs |
| Database schema change | Using delete+reimport migration strategy |

## Definition of Done Checklist

- [x] T001: `density_g_per_ml` field removed from Ingredient model
- [x] T002: 4 density fields added to Ingredient model
- [x] T003: `get_density_g_per_ml()` method implemented
- [x] T004: `format_density_display()` method implemented
- [x] T005: `INGREDIENT_DENSITIES` dict removed from constants.py
- [x] T006: `get_ingredient_density()` function removed from constants.py
- [x] T007: Tests pass for density calculation method
- [x] Docstrings updated for changed/new code

## Review Guidance

- Verify field types match data-model.md specification
- Check method handles edge cases (None, 0, negative values)
- Confirm local import pattern avoids circular dependency
- Verify INGREDIENT_DENSITIES completely removed (no remnants)

## Activity Log

- 2025-12-04T00:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2025-12-05T03:02:53Z – claude – shell_pid=3015 – lane=doing – Started implementation
- 2025-12-05T03:30:00Z – claude – shell_pid=3015 – lane=doing – Completed all subtasks T001-T007; all tests pass
- 2025-12-05T03:09:32Z – claude – shell_pid=3015 – lane=for_review – All subtasks T001-T007 complete, tests pass
- 2025-12-05T04:11:17Z – claude-reviewer – shell_pid=13066 – lane=done – Code review: APPROVED - All 11 tests pass, model correctly implements 4-field density
