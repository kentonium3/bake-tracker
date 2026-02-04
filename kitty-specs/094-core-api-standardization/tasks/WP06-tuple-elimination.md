---
work_package_id: "WP06"
subtasks:
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
title: "Tuple Return Elimination"
phase: "Phase 3 - Tuple Elimination"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "51023"
review_status: "has_feedback"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-02-03T16:10:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Tuple Return Elimination

## Objectives & Success Criteria

- Convert validation functions from `Tuple[bool, str/list]` returns to exceptions
- Use existing `ValidationError` exception
- Simplify calling code (remove tuple unpacking)
- Functions return None on success, raise exception on failure

## Context & Constraints

- `ValidationError` already exists in `src/services/exceptions.py`
- ValidationError accepts a list of error messages
- No new exception types needed
- This WP has no dependencies on WP01-WP05

## Subtasks & Detailed Guidance

### Subtask T033 - Update utils/validators.py validation functions

**Purpose**: Convert 9 validation functions from tuple returns to exceptions.

**Functions to update** (src/utils/validators.py):
1. `validate_required_string()` (line 45) - `Tuple[bool, str]`
2. `validate_string_length()` (line 63) - `Tuple[bool, str]`
3. `validate_positive_number()` (line 80) - `Tuple[bool, str]`
4. `validate_non_negative_number()` (line 100) - `Tuple[bool, str]`
5. `validate_optional_positive_number()` (line 122) - `Tuple[bool, str]`
6. `validate_unit()` (line 144) - `Tuple[bool, str]`
7. `validate_ingredient_category()` (line 192) - `Tuple[bool, str]`
8. `validate_recipe_category()` (line 220) - `Tuple[bool, str]`
9. `validate_ingredient_data()` (line 248) - `Tuple[bool, list]`
10. `validate_recipe_data()` (line 320) - `Tuple[bool, list]`
11. `validate_product_data()` (line 430) - `Tuple[bool, list]`

**Current Pattern**:
```python
def validate_required_string(value: Optional[str], field_name: str = "Field") -> Tuple[bool, str]:
    if not value or not value.strip():
        return False, f"{field_name} is required"
    return True, ""
```

**Target Pattern**:
```python
def validate_required_string(value: Optional[str], field_name: str = "Field") -> None:
    """
    Validate that a string is not empty.

    Raises:
        ValidationError: If value is empty or whitespace
    """
    if not value or not value.strip():
        raise ValidationError([f"{field_name} is required"])
```

**Steps**:
1. Import `ValidationError` from services.exceptions
2. Change return type from `Tuple[bool, str]` to `None`
3. Replace `return False, "error"` with `raise ValidationError(["error"])`
4. Replace `return True, ""` with `return None` (or just `return`)
5. Update docstring

**Files**: `src/utils/validators.py`

### Subtask T034 - Update calling code for validators

**Purpose**: Remove tuple unpacking from all validator call sites.

**Steps**:
1. Find all call sites:
   ```bash
   grep -r "validate_required_string\|validate_string_length\|validate_positive_number" src/
   grep -r "validate_ingredient_data\|validate_recipe_data\|validate_product_data" src/
   ```

2. Update call sites:

**Current Pattern**:
```python
is_valid, error = validate_required_string(name, "Name")
if not is_valid:
    errors.append(error)
```

**Target Pattern**:
```python
try:
    validate_required_string(name, "Name")
except ValidationError as e:
    errors.extend(e.errors)
```

**Or simpler if collecting multiple validations**:
```python
# Let validation functions collect errors internally
errors = []
try:
    validate_ingredient_data(data)
except ValidationError as e:
    errors.extend(e.errors)
```

**Files**: Multiple files in `src/ui/`, `src/services/`

### Subtask T035 - Update ingredient_service.py tuple-returning functions

**Purpose**: Convert ingredient service validation functions.

**Functions to update**:
- Line 67: Returns `Tuple[bool, str]`
- `can_delete_ingredient()` (line 547): Returns `Tuple[bool, str, Dict[str, int]]`

**Note**: `can_delete_ingredient` returns 3 values - may need special handling or different pattern.

**Steps**:
1. Analyze each function's usage
2. For `can_delete_ingredient`, consider returning just the dict and raising exception on failure
3. Update calling code

**Files**: `src/services/ingredient_service.py`

### Subtask T036 - Update purchase_service.py tuple-returning functions

**Purpose**: Convert purchase service validation functions.

**Functions to update** (all return `Tuple[bool, str]`):
- Line 1103: validation function
- Line 1148: validation function
- Line 1193: validation function
- Line 1235: validation function

**Steps**:
1. Analyze each function's purpose
2. Convert to raise ValidationError on failure
3. Update calling code

**Files**: `src/services/purchase_service.py`

### Subtask T037 - Update tests for all converted functions

**Purpose**: Tests should expect exceptions instead of tuple returns.

**Steps**:
1. Find tests for validators.py
2. Update tests to use `pytest.raises(ValidationError)`

**Example**:
```python
# Before:
def test_validate_required_string_empty():
    is_valid, error = validate_required_string("")
    assert not is_valid
    assert "required" in error

# After:
def test_validate_required_string_empty():
    with pytest.raises(ValidationError) as exc:
        validate_required_string("")
    assert "required" in exc.value.errors[0]
```

**Files**:
- `src/tests/utils/test_validators.py`
- `src/tests/services/test_ingredient_service.py`
- `src/tests/services/test_purchase_service.py`

## Test Strategy

Run validator tests:
```bash
./run-tests.sh src/tests/utils/test_validators.py -v
./run-tests.sh src/tests/services/test_ingredient_service.py -v
./run-tests.sh src/tests/services/test_purchase_service.py -v
```

## Risks & Mitigations

- **Many call sites**: Use grep comprehensively
- **Tuple unpacking errors**: Python will fail fast if call site not updated
- **Complex tuple returns**: `can_delete_ingredient` needs special attention

## Definition of Done Checklist

- [ ] All validators.py functions converted to raise ValidationError
- [ ] All ingredient_service.py tuple functions converted
- [ ] All purchase_service.py tuple functions converted
- [ ] No functions return `Tuple[bool, ...]` pattern
- [ ] All calling code updated (no tuple unpacking)
- [ ] Tests updated
- [ ] All tests pass

## Review Guidance

- Verify no tuple unpacking remains at call sites
- Check ValidationError includes meaningful error messages
- Ensure errors list is not empty when raising

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-02-03T16:56:18Z – claude – shell_pid=9362 – lane=doing – Started implementation via workflow command
- 2026-02-03T17:24:32Z – claude – shell_pid=9362 – lane=for_review – T033-T037 complete: Eliminated tuple returns from validators.py, ingredient_service.py, purchase_service.py. All 3493 tests pass.
- 2026-02-03T22:35:36Z – codex – shell_pid=51956 – lane=doing – Started review via workflow command
- 2026-02-03T22:36:59Z – codex – shell_pid=51956 – lane=planned – Moved to planned
- 2026-02-03T22:47:52Z – claude – shell_pid=36763 – lane=doing – Started implementation via workflow command
- 2026-02-03T22:56:05Z – claude – shell_pid=36763 – lane=for_review – Ready for review: Tuple return types eliminated from validation functions, all 3493 tests pass
- 2026-02-04T02:58:05Z – claude – shell_pid=51023 – lane=doing – Started review via workflow command
