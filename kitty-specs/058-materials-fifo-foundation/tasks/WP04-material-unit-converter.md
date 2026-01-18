---
work_package_id: "WP04"
subtasks:
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Material Unit Converter"
phase: "Phase 2 - Services"
lane: "done"
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "27987"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-18T18:06:18Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-18T21:30:00Z"
    lane: "done"
    agent: "claude-opus"
    shell_pid: ""
    action: "Review passed: material_unit_converter service with metric base units"
---

# Work Package Prompt: WP04 – Material Unit Converter

## Implementation Command

```bash
spec-kitty implement WP04
```

## Objectives & Success Criteria

Create a unit converter for materials with metric base units (cm for linear/area, count for each).

**Success Criteria**:
- All conversion factors documented and tested
- Convert imperial and metric inputs to cm base units
- Convert back from base units to display units
- Validation rejects incompatible unit type conversions (e.g., feet → square_cm)
- >80% test coverage for converter module

## Context & Constraints

**Reference Documents**:
- `kitty-specs/058-materials-fifo-foundation/plan.md` - Pattern 3: Unit Conversion
- `kitty-specs/058-materials-fifo-foundation/research.md` - Conversion factors

**Key Constraints**:
- Base units: cm (linear), square_cm (area), each (count)
- Must support both imperial (feet, inches, yards) and metric (m, mm, cm)
- Validation must prevent cross-type conversions
- Use Decimal for financial calculations, Float for storage

**Conversion Factors** (to base units):

**Linear (to cm)**:
| Unit | Factor | Source |
|------|--------|--------|
| feet | 30.48 | NIST |
| inches | 2.54 | NIST |
| yards | 91.44 | NIST |
| meters | 100.0 | SI |
| mm | 0.1 | SI |
| cm | 1.0 | Base |

**Area (to square_cm)**:
| Unit | Factor | Source |
|------|--------|--------|
| square_feet | 929.0304 | Derived (30.48²) |
| square_inches | 6.4516 | Derived (2.54²) |
| square_yards | 8361.2736 | Derived (91.44²) |
| square_meters | 10000.0 | SI |
| square_cm | 1.0 | Base |

## Subtasks & Detailed Guidance

### Subtask T012 – Create material_unit_converter.py with conversion dictionaries

**Purpose**: Define the conversion factor dictionaries and unit type mappings.

**Steps**:
1. Create new file `src/services/material_unit_converter.py`
2. Define conversion dictionaries:

```python
"""Material Unit Converter - Imperial/Metric conversion for materials.

Provides conversion functions for material quantities between
imperial and metric units, using metric base units (cm, square_cm).
"""

from decimal import Decimal
from typing import Tuple, Optional

# Linear conversions TO centimeters (base unit for linear materials)
LINEAR_TO_CM = {
    "cm": Decimal("1.0"),
    "mm": Decimal("0.1"),
    "meters": Decimal("100.0"),
    "m": Decimal("100.0"),
    "inches": Decimal("2.54"),
    "in": Decimal("2.54"),
    "feet": Decimal("30.48"),
    "ft": Decimal("30.48"),
    "yards": Decimal("91.44"),
    "yd": Decimal("91.44"),
}

# Area conversions TO square centimeters (base unit for area materials)
AREA_TO_SQCM = {
    "square_cm": Decimal("1.0"),
    "sq_cm": Decimal("1.0"),
    "square_mm": Decimal("0.01"),
    "sq_mm": Decimal("0.01"),
    "square_meters": Decimal("10000.0"),
    "sq_m": Decimal("10000.0"),
    "square_inches": Decimal("6.4516"),
    "sq_in": Decimal("6.4516"),
    "square_feet": Decimal("929.0304"),
    "sq_ft": Decimal("929.0304"),
    "square_yards": Decimal("8361.2736"),
    "sq_yd": Decimal("8361.2736"),
}

# Count units (no conversion needed)
COUNT_UNITS = {"each", "ea", "count", "piece", "pieces", "pk", "pkg"}

# Map unit to its type
def get_unit_type(unit: str) -> Optional[str]:
    """Determine the unit type for a given unit string."""
    unit_lower = unit.lower()
    if unit_lower in LINEAR_TO_CM:
        return "linear_cm"
    elif unit_lower in AREA_TO_SQCM:
        return "square_cm"
    elif unit_lower in COUNT_UNITS:
        return "each"
    return None
```

**Files**:
- Create: `src/services/material_unit_converter.py`

**Parallel?**: Yes (foundation for other subtasks)

### Subtask T013 – Implement convert_to_base_units()

**Purpose**: Convert any supported unit to base units (cm, square_cm, or count).

**Steps**:
1. Add function to `material_unit_converter.py`:

```python
def convert_to_base_units(
    quantity: Decimal,
    from_unit: str,
    base_unit_type: str,
) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    """
    Convert quantity from source unit to base units.

    Args:
        quantity: Amount to convert
        from_unit: Source unit (e.g., 'feet', 'square_inches')
        base_unit_type: Target base type ('linear_cm', 'square_cm', 'each')

    Returns:
        Tuple of (success, converted_quantity, error_message)
        - success: True if conversion succeeded
        - converted_quantity: Result in base units (None if failed)
        - error_message: Error description (None if succeeded)

    Example:
        >>> convert_to_base_units(Decimal("100"), "feet", "linear_cm")
        (True, Decimal("3048.0"), None)
    """
    from_unit_lower = from_unit.lower()
    detected_type = get_unit_type(from_unit_lower)

    # Validate unit compatibility
    if detected_type is None:
        return (False, None, f"Unknown unit: {from_unit}")

    if detected_type != base_unit_type:
        return (
            False,
            None,
            f"Cannot convert {from_unit} ({detected_type}) to {base_unit_type}",
        )

    # Perform conversion
    if base_unit_type == "linear_cm":
        factor = LINEAR_TO_CM.get(from_unit_lower, Decimal("1"))
        return (True, quantity * factor, None)

    elif base_unit_type == "square_cm":
        factor = AREA_TO_SQCM.get(from_unit_lower, Decimal("1"))
        return (True, quantity * factor, None)

    elif base_unit_type == "each":
        # Count units don't need conversion
        return (True, quantity, None)

    return (False, None, f"Unknown base_unit_type: {base_unit_type}")
```

**Files**:
- Edit: `src/services/material_unit_converter.py`

**Parallel?**: Yes

### Subtask T014 – Implement convert_from_base_units()

**Purpose**: Convert from base units back to display units.

**Steps**:
1. Add function to `material_unit_converter.py`:

```python
def convert_from_base_units(
    quantity: Decimal,
    to_unit: str,
    base_unit_type: str,
) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    """
    Convert quantity from base units to target unit.

    Args:
        quantity: Amount in base units
        to_unit: Target unit (e.g., 'feet', 'square_inches')
        base_unit_type: Source base type ('linear_cm', 'square_cm', 'each')

    Returns:
        Tuple of (success, converted_quantity, error_message)

    Example:
        >>> convert_from_base_units(Decimal("3048"), "feet", "linear_cm")
        (True, Decimal("100.0"), None)
    """
    to_unit_lower = to_unit.lower()
    detected_type = get_unit_type(to_unit_lower)

    # Validate unit compatibility
    if detected_type is None:
        return (False, None, f"Unknown unit: {to_unit}")

    if detected_type != base_unit_type:
        return (
            False,
            None,
            f"Cannot convert {base_unit_type} to {to_unit} ({detected_type})",
        )

    # Perform conversion (divide by factor)
    if base_unit_type == "linear_cm":
        factor = LINEAR_TO_CM.get(to_unit_lower, Decimal("1"))
        return (True, quantity / factor, None)

    elif base_unit_type == "square_cm":
        factor = AREA_TO_SQCM.get(to_unit_lower, Decimal("1"))
        return (True, quantity / factor, None)

    elif base_unit_type == "each":
        return (True, quantity, None)

    return (False, None, f"Unknown base_unit_type: {base_unit_type}")
```

**Files**:
- Edit: `src/services/material_unit_converter.py`

**Parallel?**: Yes

### Subtask T015 – Implement validate_unit_compatibility()

**Purpose**: Validate that a package_unit can be converted to a material's base_unit_type.

**Steps**:
1. Add function to `material_unit_converter.py`:

```python
def validate_unit_compatibility(
    package_unit: str,
    base_unit_type: str,
) -> Tuple[bool, Optional[str]]:
    """
    Validate that package_unit can be converted to base_unit_type.

    Args:
        package_unit: Unit from package (e.g., 'feet', 'square_inches')
        base_unit_type: Material's base unit type

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if conversion is possible
        - error_message: Explanation if invalid, None if valid

    Examples:
        >>> validate_unit_compatibility("feet", "linear_cm")
        (True, None)
        >>> validate_unit_compatibility("feet", "square_cm")
        (False, "Cannot convert feet (linear_cm) to square_cm")
    """
    detected_type = get_unit_type(package_unit.lower())

    if detected_type is None:
        return (False, f"Unknown unit: {package_unit}")

    if detected_type != base_unit_type:
        return (
            False,
            f"Cannot convert {package_unit} ({detected_type}) to {base_unit_type}",
        )

    return (True, None)
```

**Files**:
- Edit: `src/services/material_unit_converter.py`

**Parallel?**: Yes

### Subtask T016 – Create unit converter tests

**Purpose**: Comprehensive tests for all conversion functions.

**Steps**:
1. Create `src/tests/test_material_unit_converter.py`:

```python
"""Tests for material unit converter."""

import pytest
from decimal import Decimal

from src.services.material_unit_converter import (
    get_unit_type,
    convert_to_base_units,
    convert_from_base_units,
    validate_unit_compatibility,
)


class TestGetUnitType:
    """Tests for get_unit_type function."""

    def test_linear_units(self):
        assert get_unit_type("feet") == "linear_cm"
        assert get_unit_type("ft") == "linear_cm"
        assert get_unit_type("inches") == "linear_cm"
        assert get_unit_type("yards") == "linear_cm"
        assert get_unit_type("meters") == "linear_cm"
        assert get_unit_type("cm") == "linear_cm"

    def test_area_units(self):
        assert get_unit_type("square_feet") == "square_cm"
        assert get_unit_type("sq_ft") == "square_cm"
        assert get_unit_type("square_inches") == "square_cm"
        assert get_unit_type("square_meters") == "square_cm"

    def test_count_units(self):
        assert get_unit_type("each") == "each"
        assert get_unit_type("piece") == "each"
        assert get_unit_type("count") == "each"

    def test_unknown_unit(self):
        assert get_unit_type("unknown") is None


class TestConvertToBaseUnits:
    """Tests for convert_to_base_units function."""

    def test_feet_to_cm(self):
        success, result, error = convert_to_base_units(
            Decimal("100"), "feet", "linear_cm"
        )
        assert success
        assert result == Decimal("3048.0")
        assert error is None

    def test_inches_to_cm(self):
        success, result, error = convert_to_base_units(
            Decimal("12"), "inches", "linear_cm"
        )
        assert success
        assert result == Decimal("30.48")

    def test_square_feet_to_square_cm(self):
        success, result, error = convert_to_base_units(
            Decimal("1"), "square_feet", "square_cm"
        )
        assert success
        assert result == Decimal("929.0304")

    def test_incompatible_conversion(self):
        success, result, error = convert_to_base_units(
            Decimal("100"), "feet", "square_cm"
        )
        assert not success
        assert result is None
        assert "Cannot convert" in error

    def test_unknown_unit(self):
        success, result, error = convert_to_base_units(
            Decimal("100"), "unknown_unit", "linear_cm"
        )
        assert not success
        assert "Unknown unit" in error


class TestConvertFromBaseUnits:
    """Tests for convert_from_base_units function."""

    def test_cm_to_feet(self):
        success, result, error = convert_from_base_units(
            Decimal("3048"), "feet", "linear_cm"
        )
        assert success
        assert result == Decimal("100")

    def test_square_cm_to_square_feet(self):
        success, result, error = convert_from_base_units(
            Decimal("929.0304"), "square_feet", "square_cm"
        )
        assert success
        assert result == Decimal("1")


class TestValidateUnitCompatibility:
    """Tests for validate_unit_compatibility function."""

    def test_valid_linear(self):
        is_valid, error = validate_unit_compatibility("feet", "linear_cm")
        assert is_valid
        assert error is None

    def test_valid_area(self):
        is_valid, error = validate_unit_compatibility("square_feet", "square_cm")
        assert is_valid
        assert error is None

    def test_invalid_cross_type(self):
        is_valid, error = validate_unit_compatibility("feet", "square_cm")
        assert not is_valid
        assert "Cannot convert" in error
```

**Files**:
- Create: `src/tests/test_material_unit_converter.py`

**Parallel?**: Yes (can be written alongside functions)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Precision loss | Use Decimal for calculations |
| Missing unit aliases | Include common abbreviations (ft, in, yd, etc.) |
| Case sensitivity | Convert to lowercase before lookup |

## Definition of Done Checklist

- [ ] `material_unit_converter.py` created with all functions
- [ ] LINEAR_TO_CM dictionary with all units
- [ ] AREA_TO_SQCM dictionary with all units
- [ ] `get_unit_type()` function works correctly
- [ ] `convert_to_base_units()` function works correctly
- [ ] `convert_from_base_units()` function works correctly
- [ ] `validate_unit_compatibility()` function works correctly
- [ ] Test file created with comprehensive tests
- [ ] All tests pass
- [ ] >80% test coverage for module

## Review Guidance

**Key acceptance checkpoints**:
1. Verify conversion factors match NIST/SI standards
2. Verify both imperial and metric units supported
3. Verify cross-type conversions are rejected with clear error
4. Verify case-insensitive unit matching
5. Verify edge cases (zero quantity, very large quantities)

## Activity Log

- 2026-01-18T18:06:18Z – system – lane=planned – Prompt created.
- 2026-01-18T18:36:53Z – gemini-cli – lane=for_review – Ready for review: Material unit converter with 56 passing tests. All conversions (linear, area, each) implemented per FR-011 to FR-014.
- 2026-01-18T20:07:06Z – claude-opus – lane=done – Review passed: material_unit_converter service with metric base units
- 2026-01-18T21:32:59Z – claude-opus – shell_pid=27987 – lane=doing – Started review via workflow command
- 2026-01-18T21:33:32Z – claude-opus – shell_pid=27987 – lane=done – Review passed: Unit converter with all linear/area conversions, validation, 56 tests passing
