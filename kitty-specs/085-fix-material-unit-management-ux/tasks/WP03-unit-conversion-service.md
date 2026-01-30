---
work_package_id: WP03
title: Create Unit Conversion Service
lane: "for_review"
dependencies: []
base_branch: main
base_commit: 527cc40cbd4164ef113901a1abb11301bc54c24a
created_at: '2026-01-30T23:03:36.944381+00:00'
subtasks:
- T006
- T007
- T008
phase: Phase 2 - Enhancement
assignee: ''
agent: ''
shell_pid: "78063"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-30T22:39:29Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP03 – Create Unit Conversion Service

## Implementation Command

```bash
spec-kitty implement WP03
```

No dependencies - this WP starts fresh from main.

---

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged` in the frontmatter.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create a service module for linear unit conversions that UI components can use to convert user-friendly measurements (inches, feet, yards, meters) to centimeters.

**Success Criteria**:
- [ ] `unit_conversion_service.py` exists in `src/services/`
- [ ] `convert_to_cm()` correctly converts all supported units
- [ ] `get_linear_unit_options()` returns dropdown options
- [ ] All conversion tests pass with >90% coverage
- [ ] Service follows layered architecture principle (no UI imports)

---

## Context & Constraints

**Background**: Currently, the MaterialUnit dialog requires users to enter quantities in centimeters. For linear products like ribbon, users want to enter "8 inches" or "1 yard" and have the system convert automatically. This service provides the conversion logic.

**Related Documents**:
- Spec: `kitty-specs/085-fix-material-unit-management-ux/spec.md` (FR-003, FR-004)
- Plan: `kitty-specs/085-fix-material-unit-management-ux/plan.md` (Issue 3)
- Constitution: `.kittify/memory/constitution.md` (Principle IV: TDD, Principle V: Layered Architecture)

**Conversion Factors** (from spec):
| Unit | Symbol | cm Equivalent |
|------|--------|---------------|
| Centimeter | cm | 1.0 |
| Inch | in | 2.54 |
| Foot | ft | 30.48 |
| Yard | yd | 91.44 |
| Meter | m | 100.0 |

**Constraints**:
- Service must NOT import any UI components
- Use exact conversion factors (not approximations)
- Return values suitable for database storage (float)
- Tests required per Constitution Principle IV

---

## Subtasks & Detailed Guidance

### Subtask T006 – Create unit_conversion_service.py

**Purpose**: Create the service file with the `LINEAR_UNITS` dictionary containing conversion factors.

**Steps**:
1. Create new file `src/services/unit_conversion_service.py`
2. Add module docstring explaining purpose
3. Define the `LINEAR_UNITS` dictionary:
   ```python
   """
   Unit conversion service for linear measurements.

   Provides conversion between user-friendly linear units (inches, feet, yards, meters)
   and the base unit (centimeters) used for database storage.

   Part of Feature 085: MaterialUnit Management UX.
   """

   from typing import List, Tuple

   # Conversion factors: 1 unit = X centimeters
   LINEAR_UNITS: dict[str, float] = {
       "cm": 1.0,        # Base unit
       "in": 2.54,       # 1 inch = 2.54 cm
       "ft": 30.48,      # 1 foot = 30.48 cm
       "yd": 91.44,      # 1 yard = 91.44 cm
       "m": 100.0,       # 1 meter = 100 cm
   }

   # Display names for dropdown
   LINEAR_UNIT_NAMES: dict[str, str] = {
       "cm": "Centimeters (cm)",
       "in": "Inches (in)",
       "ft": "Feet (ft)",
       "yd": "Yards (yd)",
       "m": "Meters (m)",
   }
   ```
4. Verify no imports from `src.ui` or `src.models` (pure utility module)

**Files**:
- `src/services/unit_conversion_service.py` (new file)

**Notes**:
- Keep the module focused on conversion only
- Use type hints for clarity
- Dictionary keys match common abbreviations

---

### Subtask T007 – Implement Conversion Functions

**Purpose**: Implement the conversion and utility functions.

**Steps**:
1. Implement `convert_to_cm()`:
   ```python
   def convert_to_cm(value: float, from_unit: str) -> float:
       """
       Convert a linear measurement to centimeters.

       Args:
           value: The quantity to convert
           from_unit: The source unit code ('cm', 'in', 'ft', 'yd', 'm')

       Returns:
           The equivalent value in centimeters

       Raises:
           ValueError: If from_unit is not a valid unit code
           ValueError: If value is negative

       Examples:
           >>> convert_to_cm(8, 'in')
           20.32
           >>> convert_to_cm(1, 'yd')
           91.44
       """
       if value < 0:
           raise ValueError(f"Value must be non-negative, got {value}")

       from_unit = from_unit.lower()
       if from_unit not in LINEAR_UNITS:
           raise ValueError(
               f"Unknown unit '{from_unit}'. Valid units: {list(LINEAR_UNITS.keys())}"
           )

       return value * LINEAR_UNITS[from_unit]
   ```

2. Implement `get_linear_unit_options()`:
   ```python
   def get_linear_unit_options() -> List[Tuple[str, str]]:
       """
       Return list of (code, display_name) tuples for dropdown population.

       Returns:
           List of tuples like [('cm', 'Centimeters (cm)'), ('in', 'Inches (in)'), ...]
           Ordered by: cm first (default), then alphabetically by code
       """
       options = []
       # cm first as it's the default/base unit
       options.append(("cm", LINEAR_UNIT_NAMES["cm"]))
       # Add others alphabetically
       for code in sorted(LINEAR_UNITS.keys()):
           if code != "cm":
               options.append((code, LINEAR_UNIT_NAMES[code]))
       return options
   ```

3. Optionally add `convert_from_cm()` for display purposes:
   ```python
   def convert_from_cm(value: float, to_unit: str) -> float:
       """
       Convert centimeters to another linear unit (for display).

       Args:
           value: The value in centimeters
           to_unit: The target unit code

       Returns:
           The equivalent value in the target unit
       """
       to_unit = to_unit.lower()
       if to_unit not in LINEAR_UNITS:
           raise ValueError(f"Unknown unit '{to_unit}'")

       return value / LINEAR_UNITS[to_unit]
   ```

**Files**:
- `src/services/unit_conversion_service.py`

**Notes**:
- Handle case-insensitive unit codes
- Raise clear ValueError for invalid inputs
- Include docstring examples for documentation

---

### Subtask T008 – Write Comprehensive Tests

**Purpose**: Create tests covering all conversion scenarios, edge cases, and error conditions.

**Steps**:
1. Create test file `src/tests/test_unit_conversion.py`:
   ```python
   """
   Tests for unit_conversion_service.

   Part of Feature 085: MaterialUnit Management UX.
   """

   import pytest
   from src.services.unit_conversion_service import (
       convert_to_cm,
       convert_from_cm,
       get_linear_unit_options,
       LINEAR_UNITS,
   )


   class TestConvertToCm:
       """Tests for convert_to_cm function."""

       def test_convert_inches_to_cm(self):
           """8 inches should convert to 20.32 cm."""
           result = convert_to_cm(8, "in")
           assert result == pytest.approx(20.32)

       def test_convert_feet_to_cm(self):
           """1 foot should convert to 30.48 cm."""
           result = convert_to_cm(1, "ft")
           assert result == pytest.approx(30.48)

       def test_convert_yards_to_cm(self):
           """1 yard should convert to 91.44 cm."""
           result = convert_to_cm(1, "yd")
           assert result == pytest.approx(91.44)

       def test_convert_meters_to_cm(self):
           """1 meter should convert to 100 cm."""
           result = convert_to_cm(1, "m")
           assert result == pytest.approx(100.0)

       def test_convert_cm_to_cm(self):
           """cm to cm should return same value."""
           result = convert_to_cm(50, "cm")
           assert result == pytest.approx(50.0)

       def test_convert_zero(self):
           """Zero should convert to zero."""
           result = convert_to_cm(0, "in")
           assert result == 0.0

       def test_convert_fractional(self):
           """Fractional values should work."""
           result = convert_to_cm(0.5, "in")
           assert result == pytest.approx(1.27)

       def test_case_insensitive(self):
           """Unit codes should be case-insensitive."""
           assert convert_to_cm(1, "IN") == convert_to_cm(1, "in")
           assert convert_to_cm(1, "Ft") == convert_to_cm(1, "ft")

       def test_invalid_unit_raises(self):
           """Invalid unit should raise ValueError."""
           with pytest.raises(ValueError, match="Unknown unit"):
               convert_to_cm(10, "miles")

       def test_negative_value_raises(self):
           """Negative value should raise ValueError."""
           with pytest.raises(ValueError, match="non-negative"):
               convert_to_cm(-5, "in")


   class TestConvertFromCm:
       """Tests for convert_from_cm function."""

       def test_convert_cm_to_inches(self):
           """20.32 cm should convert to 8 inches."""
           result = convert_from_cm(20.32, "in")
           assert result == pytest.approx(8.0)

       def test_convert_cm_to_yards(self):
           """91.44 cm should convert to 1 yard."""
           result = convert_from_cm(91.44, "yd")
           assert result == pytest.approx(1.0)


   class TestGetLinearUnitOptions:
       """Tests for get_linear_unit_options function."""

       def test_returns_all_units(self):
           """Should return all defined units."""
           options = get_linear_unit_options()
           codes = [code for code, _ in options]
           assert len(codes) == len(LINEAR_UNITS)
           for unit in LINEAR_UNITS:
               assert unit in codes

       def test_cm_is_first(self):
           """cm should be the first option (default)."""
           options = get_linear_unit_options()
           assert options[0][0] == "cm"

       def test_returns_tuples(self):
           """Should return (code, display_name) tuples."""
           options = get_linear_unit_options()
           for code, name in options:
               assert isinstance(code, str)
               assert isinstance(name, str)
               assert "(" in name  # e.g., "Inches (in)"
   ```

2. Run tests to verify:
   ```bash
   pytest src/tests/test_unit_conversion.py -v
   ```

3. Check coverage:
   ```bash
   pytest src/tests/test_unit_conversion.py -v --cov=src/services/unit_conversion_service
   ```

**Files**:
- `src/tests/test_unit_conversion.py` (new file)

**Notes**:
- Use `pytest.approx()` for floating point comparisons
- Test both happy path and error conditions
- Ensure >90% coverage of the service module

---

## Test Strategy

**Automated Tests Required**:
- Run: `pytest src/tests/test_unit_conversion.py -v`
- Expected: All tests pass
- Coverage target: >90% on `unit_conversion_service.py`

**Test Coverage**:
| Function | Test Cases |
|----------|------------|
| `convert_to_cm()` | All units, zero, fractions, case-insensitive, invalid unit, negative |
| `convert_from_cm()` | Reverse conversion for display |
| `get_linear_unit_options()` | Returns all units, cm first, proper format |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Floating point precision | Use `pytest.approx()` in tests; exact factors in code |
| Conversion factor errors | Verify against authoritative sources; tests catch errors |
| Service imported incorrectly | Test import statement in tests |

---

## Definition of Done Checklist

- [ ] T006: `unit_conversion_service.py` created with `LINEAR_UNITS` dict
- [ ] T007: `convert_to_cm()` implemented with validation
- [ ] T007: `get_linear_unit_options()` implemented
- [ ] T007: `convert_from_cm()` implemented (optional but useful)
- [ ] T008: All tests written and passing
- [ ] T008: Test coverage >90%
- [ ] No UI or model imports in service
- [ ] Clear docstrings with examples

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. Run `pytest src/tests/test_unit_conversion.py -v` - all pass
2. Run coverage check - >90% on service file
3. Verify conversion factors match spec
4. Verify no UI imports in service

**Code Review Focus**:
- Correct conversion factors
- Proper error handling (ValueError with clear messages)
- Type hints present
- Docstrings with examples

---

## Activity Log

- 2026-01-30T22:39:29Z – system – lane=planned – Prompt created.
- 2026-01-30T23:06:36Z – unknown – shell_pid=78063 – lane=for_review – Added dropdown helpers and simple wrappers to existing material_unit_converter.py - all 77 tests pass
