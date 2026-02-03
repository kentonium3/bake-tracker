---
work_package_id: WP07
title: Unit Converter Updates
lane: "doing"
dependencies: [WP01]
base_branch: 094-core-api-standardization-WP01
base_commit: 4f0333494559e2a44d97431f1ae745eda905680c
created_at: '2026-02-03T17:24:59.897739+00:00'
subtasks:
- T038
- T039
- T040
- T041
phase: Phase 3 - Tuple Elimination
assignee: ''
agent: ''
shell_pid: "13602"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T16:10:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP07 - Unit Converter Updates

## Objectives & Success Criteria

- Convert unit converter functions from tuple returns to exceptions
- Use `ConversionError` exception (created in WP01)
- Return just the converted value on success
- Raise exception with context on failure

## Context & Constraints

- **Depends on WP01**: `ConversionError` exception must be available
- Reference: `src/services/unit_converter.py`
- Reference: `src/services/material_unit_converter.py`
- These functions are used throughout for unit conversions

## Subtasks & Detailed Guidance

### Subtask T038 - Update unit_converter.py functions

**Purpose**: Convert 5 functions from tuple returns to exceptions.

**Functions to update**:
1. `convert_standard_units()` (line 130) - `Tuple[bool, float, str]`
2. `convert_volume_to_volume()` (line 209) - `Tuple[bool, float, str]`
3. `convert_weight_to_weight()` (line 258) - `Tuple[bool, float, str]`
4. `convert_count_to_count()` (line 307) - `Tuple[bool, float, str]`
5. `convert_with_density()` (line 359) - `Tuple[bool, float, str]`
6. `validate_quantity()` (line 402) - `Tuple[bool, str]`

**Current Pattern**:
```python
def convert_standard_units(value: float, from_unit: str, to_unit: str) -> Tuple[bool, float, str]:
    # ... conversion logic
    if not can_convert:
        return False, 0.0, f"Cannot convert from {from_unit} to {to_unit}"
    return True, converted_value, ""
```

**Target Pattern**:
```python
def convert_standard_units(value: float, from_unit: str, to_unit: str) -> float:
    """
    Convert value between standard units.

    Returns:
        Converted value

    Raises:
        ConversionError: If conversion is not possible
    """
    # ... conversion logic
    if not can_convert:
        raise ConversionError(
            f"Cannot convert from {from_unit} to {to_unit}",
            from_unit=from_unit,
            to_unit=to_unit,
            value=value
        )
    return converted_value
```

**Steps**:
1. Import `ConversionError` from services.exceptions
2. Change return type from `Tuple[bool, float, str]` to `float`
3. Replace `return False, 0.0, "error"` with `raise ConversionError(...)`
4. Replace `return True, value, ""` with `return value`
5. Update docstring

**Files**: `src/services/unit_converter.py`

### Subtask T039 - Update material_unit_converter.py functions

**Purpose**: Convert 4 functions from tuple returns to exceptions.

**Functions to update**:
1. `validate_unit_compatibility()` (line 74) - `Tuple[bool, Optional[str]]`
2. `convert_to_base_unit()` (line 123) - `Tuple[bool, Optional[Decimal], Optional[str]]`
3. `convert_from_base_unit()` (line 175) - `Tuple[bool, Optional[Decimal], Optional[str]]`
4. `convert_units()` (line 227) - `Tuple[bool, Optional[Decimal], Optional[str]]`

**Current Pattern**:
```python
def convert_to_base_unit(
    value: Decimal, unit: str, unit_type: str
) -> Tuple[bool, Optional[Decimal], Optional[str]]:
    # ... conversion logic
    if error:
        return False, None, error_message
    return True, converted_value, None
```

**Target Pattern**:
```python
def convert_to_base_unit(
    value: Decimal, unit: str, unit_type: str
) -> Decimal:
    """
    Convert value to base unit.

    Returns:
        Converted value in base unit

    Raises:
        ConversionError: If conversion fails
    """
    # ... conversion logic
    if error:
        raise ConversionError(error_message, from_unit=unit)
    return converted_value
```

**Files**: `src/services/material_unit_converter.py`

### Subtask T040 - Update calling code for converters

**Purpose**: Remove tuple unpacking from all converter call sites.

**Steps**:
1. Find all call sites:
   ```bash
   grep -r "convert_standard_units\|convert_volume_to_volume\|convert_weight_to_weight" src/
   grep -r "convert_to_base_unit\|convert_from_base_unit\|convert_units" src/
   ```

2. Update call sites:

**Current Pattern**:
```python
success, converted, error = convert_standard_units(value, from_unit, to_unit)
if not success:
    show_error(error)
    return
# Use converted value
```

**Target Pattern**:
```python
try:
    converted = convert_standard_units(value, from_unit, to_unit)
    # Use converted value
except ConversionError as e:
    show_error(str(e))
    return
```

**Files**: Multiple files in `src/ui/`, `src/services/`

### Subtask T041 - Update converter tests

**Purpose**: Tests should expect exceptions instead of tuple returns.

**Steps**:
1. Find tests for unit converters
2. Update tests to use `pytest.raises(ConversionError)`

**Example**:
```python
# Before:
def test_convert_invalid_units():
    success, value, error = convert_standard_units(1.0, "kg", "liters")
    assert not success
    assert "Cannot convert" in error

# After:
def test_convert_invalid_units():
    with pytest.raises(ConversionError) as exc:
        convert_standard_units(1.0, "kg", "liters")
    assert exc.value.from_unit == "kg"
    assert exc.value.to_unit == "liters"
```

**Files**:
- `src/tests/services/test_unit_converter.py`
- `src/tests/services/test_material_unit_converter.py`

## Test Strategy

Run converter tests:
```bash
./run-tests.sh src/tests/services/test_unit_converter.py -v
./run-tests.sh src/tests/services/test_material_unit_converter.py -v
```

## Risks & Mitigations

- **Many call sites**: Converters used throughout codebase
- **UI integration**: Test UI dialogs that do unit conversion
- **Decimal precision**: Ensure Decimal handling is preserved

## Definition of Done Checklist

- [ ] All unit_converter.py functions return value directly
- [ ] All material_unit_converter.py functions return value directly
- [ ] No functions return `Tuple[bool, ...]` pattern
- [ ] ConversionError includes context (from_unit, to_unit, value)
- [ ] All calling code updated
- [ ] Tests updated
- [ ] All tests pass

## Review Guidance

- Verify ConversionError includes useful debugging context
- Check Decimal handling is preserved
- Test UI conversion dialogs

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
