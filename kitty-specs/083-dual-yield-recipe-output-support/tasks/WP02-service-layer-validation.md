---
work_package_id: WP02
title: Service Layer – yield_type Validation
lane: "for_review"
dependencies: [WP01]
base_branch: 083-dual-yield-recipe-output-support-WP01
base_commit: ab69e594ec263da2dfdb1bfb5a310aebe407727f
created_at: '2026-01-29T17:08:15.481563+00:00'
subtasks:
- T006
- T007
- T008
- T009
phase: Phase 1 - Foundation
assignee: ''
agent: ''
shell_pid: "68797"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-29T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 – Service Layer – yield_type Validation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you begin addressing feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
# Depends on WP01 - branch from WP01 completion
spec-kitty implement WP02 --base WP01
```

---

## Objectives & Success Criteria

Add service-layer validation for yield_type during FinishedUnit CRUD operations:

- [ ] `VALID_YIELD_TYPES` constant defined
- [ ] `validate_yield_type()` function returns error list for invalid values
- [ ] `create_finished_unit()` accepts and validates yield_type parameter
- [ ] `update_finished_unit()` validates yield_type changes
- [ ] Unit tests verify all validation scenarios

**Success metrics**:
- Service rejects yield_type='INVALID' with clear error message
- Service accepts yield_type='EA' and yield_type='SERVING'
- Backward compatibility: yield_type defaults to 'SERVING' if not provided

---

## Context & Constraints

**Reference documents**:
- `kitty-specs/083-dual-yield-recipe-output-support/research.md` - Validation patterns (Q4)
- `kitty-specs/083-dual-yield-recipe-output-support/data-model.md` - Validation rules
- `.kittify/memory/constitution.md` - TDD requirements

**Existing validation pattern** (from research.md):
```python
def validate_recipe_has_finished_unit(recipe_id: int, session=None) -> List[str]:
    """Returns List[str] of error messages (empty if valid)."""
    # Pattern: Query, validate, return error list
```

**Service layer rules**:
- Functions accept optional `session=None` parameter for transaction sharing
- Return `List[str]` of error messages (empty if valid)
- Validate at service layer BEFORE database operation

---

## Subtasks & Detailed Guidance

### Subtask T006 – Add VALID_YIELD_TYPES constant and validate_yield_type function

**Purpose**: Centralize yield_type validation logic.

**Steps**:
1. Open `src/services/finished_unit_service.py`
2. Add constant near top of file (after imports):

```python
# Valid yield type values
VALID_YIELD_TYPES = {"EA", "SERVING"}
```

3. Add validation function:

```python
def validate_yield_type(yield_type: str) -> List[str]:
    """Validate yield_type value.

    Args:
        yield_type: The yield type to validate ('EA' or 'SERVING')

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    if not yield_type:
        errors.append("yield_type is required")
    elif yield_type not in VALID_YIELD_TYPES:
        errors.append(f"yield_type must be 'EA' or 'SERVING', got '{yield_type}'")
    return errors
```

**Files**: `src/services/finished_unit_service.py`

**Notes**:
- Use a set for O(1) membership testing
- Return list (not raise exception) to match existing patterns
- Include the invalid value in error message for debugging

---

### Subtask T007 – Update create_finished_unit to accept and validate yield_type

**Purpose**: Enable creating FinishedUnits with explicit yield_type.

**Steps**:
1. Locate `create_finished_unit()` function in `src/services/finished_unit_service.py`
2. Add `yield_type` parameter with default value:

```python
def create_finished_unit(
    display_name: str,
    recipe_id: int,
    item_unit: str = None,
    items_per_batch: int = None,
    yield_type: str = "SERVING",  # NEW PARAMETER
    # ... other existing parameters ...
    session=None,
) -> FinishedUnit:
```

3. Add validation before creating the model:

```python
# Validate yield_type
yield_type_errors = validate_yield_type(yield_type)
if yield_type_errors:
    raise ValueError(f"Invalid yield_type: {'; '.join(yield_type_errors)}")
```

4. Pass yield_type to FinishedUnit constructor:

```python
fu = FinishedUnit(
    # ... existing fields ...
    yield_type=yield_type,
)
```

**Files**: `src/services/finished_unit_service.py`

**Notes**:
- Default to 'SERVING' for backward compatibility
- Validate before database operation to provide clear error messages
- Raise ValueError for invalid input (matches existing pattern)

---

### Subtask T008 – Update update_finished_unit to validate yield_type changes

**Purpose**: Ensure yield_type remains valid during updates.

**Steps**:
1. Locate `update_finished_unit()` function in `src/services/finished_unit_service.py`
2. Add `yield_type` to accepted parameters:

```python
def update_finished_unit(
    finished_unit_id: int,
    display_name: str = None,
    item_unit: str = None,
    items_per_batch: int = None,
    yield_type: str = None,  # NEW PARAMETER
    # ... other existing parameters ...
    session=None,
) -> FinishedUnit:
```

3. Add validation if yield_type is being updated:

```python
# Validate yield_type if provided
if yield_type is not None:
    yield_type_errors = validate_yield_type(yield_type)
    if yield_type_errors:
        raise ValueError(f"Invalid yield_type: {'; '.join(yield_type_errors)}")
    fu.yield_type = yield_type
```

**Files**: `src/services/finished_unit_service.py`

**Notes**:
- Only validate if yield_type is explicitly provided (not None)
- This allows updating other fields without touching yield_type

---

### Subtask T009 – Write service-level unit tests

**Purpose**: Verify validation logic works correctly.

**Steps**:
1. Create `src/tests/services/test_finished_unit_yield_type.py`
2. Write comprehensive tests:

```python
"""Tests for FinishedUnit yield_type service layer validation."""
import pytest

from src.services import finished_unit_service
from src.services.finished_unit_service import (
    VALID_YIELD_TYPES,
    validate_yield_type,
)
from src.models.recipe import Recipe
from src.utils.db import session_scope


class TestValidateYieldType:
    """Test validate_yield_type function."""

    def test_valid_yield_types_constant(self):
        """VALID_YIELD_TYPES contains expected values."""
        assert VALID_YIELD_TYPES == {"EA", "SERVING"}

    def test_validate_ea_returns_empty_list(self):
        """'EA' is valid and returns no errors."""
        errors = validate_yield_type("EA")
        assert errors == []

    def test_validate_serving_returns_empty_list(self):
        """'SERVING' is valid and returns no errors."""
        errors = validate_yield_type("SERVING")
        assert errors == []

    def test_validate_empty_returns_error(self):
        """Empty string returns error."""
        errors = validate_yield_type("")
        assert len(errors) == 1
        assert "required" in errors[0]

    def test_validate_none_returns_error(self):
        """None returns error."""
        errors = validate_yield_type(None)
        assert len(errors) == 1
        assert "required" in errors[0]

    def test_validate_invalid_returns_error_with_value(self):
        """Invalid value returns error containing the bad value."""
        errors = validate_yield_type("INVALID")
        assert len(errors) == 1
        assert "INVALID" in errors[0]
        assert "EA" in errors[0]
        assert "SERVING" in errors[0]


class TestCreateFinishedUnitYieldType:
    """Test create_finished_unit with yield_type."""

    def test_create_with_default_yield_type(self, test_db):
        """FinishedUnit created without yield_type defaults to SERVING."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = finished_unit_service.create_finished_unit(
                display_name="Test Cookies",
                recipe_id=recipe.id,
                item_unit="cookie",
                items_per_batch=24,
                session=session,
            )

            assert fu.yield_type == "SERVING"

    def test_create_with_explicit_ea(self, test_db):
        """FinishedUnit can be created with yield_type='EA'."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = finished_unit_service.create_finished_unit(
                display_name="Test Cake",
                recipe_id=recipe.id,
                item_unit="cake",
                items_per_batch=1,
                yield_type="EA",
                session=session,
            )

            assert fu.yield_type == "EA"

    def test_create_with_invalid_yield_type_raises(self, test_db):
        """Creating with invalid yield_type raises ValueError."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            with pytest.raises(ValueError) as exc_info:
                finished_unit_service.create_finished_unit(
                    display_name="Test",
                    recipe_id=recipe.id,
                    item_unit="item",
                    items_per_batch=1,
                    yield_type="INVALID",
                    session=session,
                )

            assert "INVALID" in str(exc_info.value)


class TestUpdateFinishedUnitYieldType:
    """Test update_finished_unit with yield_type."""

    def test_update_yield_type_to_ea(self, test_db):
        """yield_type can be updated from SERVING to EA."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = finished_unit_service.create_finished_unit(
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="item",
                items_per_batch=1,
                yield_type="SERVING",
                session=session,
            )
            fu_id = fu.id
            session.commit()

        with session_scope() as session:
            updated = finished_unit_service.update_finished_unit(
                fu_id,
                yield_type="EA",
                session=session,
            )

            assert updated.yield_type == "EA"

    def test_update_other_fields_preserves_yield_type(self, test_db):
        """Updating other fields without yield_type preserves existing value."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = finished_unit_service.create_finished_unit(
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="item",
                items_per_batch=1,
                yield_type="EA",
                session=session,
            )
            fu_id = fu.id
            session.commit()

        with session_scope() as session:
            updated = finished_unit_service.update_finished_unit(
                fu_id,
                display_name="Updated Name",
                session=session,
            )

            assert updated.yield_type == "EA"  # Preserved

    def test_update_with_invalid_yield_type_raises(self, test_db):
        """Updating with invalid yield_type raises ValueError."""
        with session_scope() as session:
            recipe = Recipe(name="Test Recipe", slug="test-recipe", category="Test")
            session.add(recipe)
            session.flush()

            fu = finished_unit_service.create_finished_unit(
                display_name="Test",
                recipe_id=recipe.id,
                item_unit="item",
                items_per_batch=1,
                session=session,
            )
            fu_id = fu.id
            session.commit()

        with session_scope() as session:
            with pytest.raises(ValueError) as exc_info:
                finished_unit_service.update_finished_unit(
                    fu_id,
                    yield_type="BOGUS",
                    session=session,
                )

            assert "BOGUS" in str(exc_info.value)
```

**Files**: `src/tests/services/test_finished_unit_yield_type.py` (new file)

**Notes**:
- Test both the validation function directly and via create/update
- Verify backward compatibility (default to SERVING)
- Test error messages contain useful information

---

## Test Strategy

**Required tests** (T009):
- `TestValidateYieldType` - Direct validation function tests
- `TestCreateFinishedUnitYieldType` - Create with/without yield_type
- `TestUpdateFinishedUnitYieldType` - Update scenarios

**Run tests**:
```bash
./run-tests.sh src/tests/services/test_finished_unit_yield_type.py -v
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking change to function signatures | yield_type parameter is optional with default='SERVING' |
| Existing callers don't pass yield_type | Default value ensures backward compatibility |

---

## Definition of Done Checklist

- [ ] T006: VALID_YIELD_TYPES constant and validate_yield_type function added
- [ ] T007: create_finished_unit accepts and validates yield_type
- [ ] T008: update_finished_unit validates yield_type changes
- [ ] T009: All unit tests pass
- [ ] Backward compatibility maintained (existing callers still work)
- [ ] Error messages are clear and actionable

---

## Review Guidance

**Reviewers should verify**:
1. Validation function returns list (not raises exception)
2. Default value is 'SERVING' for backward compatibility
3. Error messages include the invalid value for debugging
4. Tests cover both valid and invalid scenarios

---

## Activity Log

- 2026-01-29T00:00:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks
- 2026-01-29T17:20:01Z – unknown – shell_pid=68797 – lane=for_review – Ready for review: Added yield_type validation to service layer
