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
  - "T008"
title: "Exception Infrastructure"
phase: "Phase 1 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-02-03T16:10:45Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 - Exception Infrastructure

## Objectives & Success Criteria

- Add all missing exception types needed for FR-1 (exception pattern) and FR-2 (tuple elimination)
- Each exception follows existing patterns in `src/services/exceptions.py`
- All exceptions inherit from `ServiceError` with appropriate `http_status_code`
- Test that all new exceptions can be imported and raised

## Context & Constraints

- Reference: `src/services/exceptions.py` - contains existing exception hierarchy
- Follow patterns established by `IngredientNotFoundBySlug`, `RecipeNotFound`, etc.
- All not-found exceptions use `http_status_code = 404`
- Include `correlation_id` parameter for future tracing support

## Subtasks & Detailed Guidance

### Subtask T001 - Add recipe-related exceptions

**Purpose**: Enable recipe_service.py to raise specific exceptions for not-found cases.

**Steps**:
1. Add `RecipeNotFoundBySlug` exception class:
   ```python
   class RecipeNotFoundBySlug(ServiceError):
       """Raised when recipe cannot be found by slug."""
       http_status_code = 404
       def __init__(self, slug: str, correlation_id: Optional[str] = None):
           self.slug = slug
           super().__init__(
               f"Recipe with slug '{slug}' not found",
               correlation_id=correlation_id,
               slug=slug
           )
   ```
2. Add `RecipeNotFoundByName` exception class (similar pattern)

**Files**: `src/services/exceptions.py`

### Subtask T002 - Add event-related exceptions

**Purpose**: Enable event_service.py to raise specific exceptions.

**Steps**:
1. Add `EventNotFoundById` exception class
2. Add `EventNotFoundByName` exception class

**Files**: `src/services/exceptions.py`

### Subtask T003 - Add finished goods exceptions

**Purpose**: Enable finished_good_service.py and finished_unit_service.py to raise specific exceptions.

**Steps**:
1. Add `FinishedGoodNotFoundById` exception class
2. Add `FinishedGoodNotFoundBySlug` exception class
3. Add `FinishedUnitNotFoundById` exception class
4. Add `FinishedUnitNotFoundBySlug` exception class

**Files**: `src/services/exceptions.py`

### Subtask T004 - Add package exceptions

**Purpose**: Enable package_service.py to raise specific exceptions.

**Steps**:
1. Add `PackageNotFoundById` exception class
2. Add `PackageNotFoundByName` exception class

**Files**: `src/services/exceptions.py`

### Subtask T005 - Add composition/unit exceptions

**Purpose**: Enable composition_service.py and unit_service.py to raise specific exceptions.

**Steps**:
1. Add `CompositionNotFoundById` exception class
2. Add `UnitNotFoundByCode` exception class

**Files**: `src/services/exceptions.py`

### Subtask T006 - Add material catalog exceptions

**Purpose**: Enable material_catalog_service.py to raise specific exceptions.

**Steps**:
1. Add `MaterialCategoryNotFound` exception class
2. Add `MaterialSubcategoryNotFound` exception class
3. Add `MaterialNotFound` exception class
4. Add `MaterialProductNotFound` exception class

**Files**: `src/services/exceptions.py`

### Subtask T007 - Add ConversionError exception

**Purpose**: Enable unit converters to raise exceptions instead of returning tuples.

**Steps**:
1. Add `ConversionError` exception class with context for debugging:
   ```python
   class ConversionError(ServiceError):
       """Raised when unit conversion fails."""
       http_status_code = 400
       def __init__(
           self,
           message: str,
           from_unit: str = None,
           to_unit: str = None,
           value: float = None,
           correlation_id: Optional[str] = None
       ):
           self.from_unit = from_unit
           self.to_unit = to_unit
           self.value = value
           super().__init__(
               message,
               correlation_id=correlation_id,
               from_unit=from_unit,
               to_unit=to_unit,
               value=value
           )
   ```

**Files**: `src/services/exceptions.py`

### Subtask T008 - Update exceptions.py docstring

**Purpose**: Document the updated exception hierarchy.

**Steps**:
1. Update the module docstring at the top of `exceptions.py` to include new exception types in the hierarchy tree
2. Ensure categories are organized logically (NotFound, Validation, Conversion, etc.)

**Files**: `src/services/exceptions.py`

## Test Strategy

Create a simple test to verify all exceptions can be imported and raised:

```python
# src/tests/services/test_exceptions_comprehensive.py
import pytest
from src.services.exceptions import (
    RecipeNotFoundBySlug, RecipeNotFoundByName,
    EventNotFoundById, EventNotFoundByName,
    FinishedGoodNotFoundById, FinishedGoodNotFoundBySlug,
    FinishedUnitNotFoundById, FinishedUnitNotFoundBySlug,
    PackageNotFoundById, PackageNotFoundByName,
    CompositionNotFoundById, UnitNotFoundByCode,
    MaterialCategoryNotFound, MaterialSubcategoryNotFound,
    MaterialNotFound, MaterialProductNotFound,
    ConversionError,
)

def test_recipe_exceptions():
    with pytest.raises(RecipeNotFoundBySlug) as exc:
        raise RecipeNotFoundBySlug("chocolate-cake")
    assert exc.value.slug == "chocolate-cake"
    assert exc.value.http_status_code == 404

# Add similar tests for other exceptions
```

## Risks & Mitigations

- **Too many exception types**: Group logically, use consistent naming
- **Inconsistent patterns**: Follow existing exceptions exactly

## Definition of Done Checklist

- [ ] All exception types added to exceptions.py
- [ ] Module docstring updated with new hierarchy
- [ ] All exceptions can be imported without errors
- [ ] All exceptions have http_status_code set
- [ ] Test file verifies all exceptions work correctly

## Review Guidance

- Verify naming follows `{Entity}NotFoundBy{Field}` pattern
- Verify http_status_code is appropriate (404 for not-found, 400 for conversion errors)
- Verify correlation_id parameter is included

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
