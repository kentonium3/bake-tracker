---
work_package_id: "WP02"
subtasks:
  - "T002"
  - "T003"
  - "T004"
title: "Service - Name Uniqueness Validation"
phase: "Phase 1 - Parallel Foundation"
lane: "done"
assignee: ""
agent: "claude"
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Service - Name Uniqueness Validation

## Objectives & Success Criteria

**Primary Objective**: Prevent duplicate yield type names within the same recipe.

**Success Criteria**:
- Creating a FinishedUnit with a name that already exists for that recipe raises ValidationError
- Updating a FinishedUnit to a name that already exists for that recipe raises ValidationError
- Same name CAN exist across different recipes (FR-019: uniqueness is per-recipe)
- Error messages are user-friendly and actionable

**Spec Requirement (FR-019)**:
> Yield type name MUST be unique within the same recipe

## Context & Constraints

**Feature**: 044-finished-units-yield-type-management
**File**: `src/services/finished_unit_service.py`
**Research Reference**: [research.md](../research.md) - Service Layer section

**Existing Service Methods**:
- `create_finished_unit(display_name, recipe_id, **kwargs)` - needs uniqueness check
- `update_finished_unit(finished_unit_id, **updates)` - needs uniqueness check for renames
- `get_units_by_recipe(recipe_id)` - can be used to check existing names

**Session Management Pattern** (from CLAUDE.md):
```python
def service_function(..., session=None):
    if session is not None:
        return _service_function_impl(..., session)
    with session_scope() as session:
        return _service_function_impl(..., session)
```

## Subtasks & Detailed Guidance

### Subtask T002 - Add _validate_name_unique_in_recipe Helper Method

**Purpose**: Create a reusable validation method that checks if a display_name already exists for a given recipe.

**Location**: Add inside `FinishedUnitService` class or as module-level function

**Implementation**:
```python
def _validate_name_unique_in_recipe(
    display_name: str,
    recipe_id: int,
    session,
    exclude_id: Optional[int] = None
) -> None:
    """
    Validate that display_name is unique within the recipe.

    Args:
        display_name: The name to check
        recipe_id: The recipe to check within
        session: SQLAlchemy session
        exclude_id: FinishedUnit ID to exclude (for updates)

    Raises:
        ValidationError: If name already exists for this recipe
    """
    from src.models.finished_unit import FinishedUnit

    query = session.query(FinishedUnit).filter(
        FinishedUnit.recipe_id == recipe_id,
        func.lower(FinishedUnit.display_name) == func.lower(display_name.strip())
    )

    if exclude_id is not None:
        query = query.filter(FinishedUnit.id != exclude_id)

    existing = query.first()
    if existing:
        raise ValidationError(
            f"A yield type named '{display_name}' already exists for this recipe"
        )
```

**Notes**:
- Use case-insensitive comparison (`func.lower()`) to prevent "Large Cookie" vs "large cookie" duplicates
- Import `func` from `sqlalchemy` if not already imported
- The `exclude_id` parameter allows updates to keep the same name

### Subtask T003 - Integrate Uniqueness Check into create_finished_unit

**Purpose**: Call the validation helper before creating a new FinishedUnit.

**Location**: Inside `create_finished_unit()` method

**Find the existing method** (likely has signature like):
```python
def create_finished_unit(display_name: str, recipe_id: int, **kwargs):
```

**Add validation call** at the start of the function (after session setup):
```python
def create_finished_unit(display_name: str, recipe_id: int, session=None, **kwargs):
    """Create a new finished unit with name uniqueness validation."""
    if session is not None:
        return _create_finished_unit_impl(display_name, recipe_id, session, **kwargs)
    with session_scope() as session:
        return _create_finished_unit_impl(display_name, recipe_id, session, **kwargs)

def _create_finished_unit_impl(display_name: str, recipe_id: int, session, **kwargs):
    # ADD THIS LINE:
    _validate_name_unique_in_recipe(display_name, recipe_id, session)

    # ... existing creation logic ...
```

**Error Handling**:
- ValidationError will propagate up to the UI layer
- UI will catch and display the error message to user

### Subtask T004 - Integrate Uniqueness Check into update_finished_unit

**Purpose**: Call the validation helper when updating a FinishedUnit's name.

**Location**: Inside `update_finished_unit()` method

**Key Consideration**: Only validate if `display_name` is being changed, and exclude the current record.

**Implementation Pattern**:
```python
def update_finished_unit(finished_unit_id: int, session=None, **updates):
    """Update a finished unit with name uniqueness validation."""
    if session is not None:
        return _update_finished_unit_impl(finished_unit_id, session, **updates)
    with session_scope() as session:
        return _update_finished_unit_impl(finished_unit_id, session, **updates)

def _update_finished_unit_impl(finished_unit_id: int, session, **updates):
    # Fetch the existing record
    finished_unit = session.query(FinishedUnit).get(finished_unit_id)
    if not finished_unit:
        raise NotFoundError(f"FinishedUnit {finished_unit_id} not found")

    # ADD THIS BLOCK:
    if 'display_name' in updates:
        new_name = updates['display_name']
        if new_name != finished_unit.display_name:  # Only validate if name changed
            _validate_name_unique_in_recipe(
                new_name,
                finished_unit.recipe_id,
                session,
                exclude_id=finished_unit_id  # Exclude self from check
            )

    # ... existing update logic ...
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Case sensitivity confusion | Medium | Low | Use case-insensitive comparison |
| Validation skipped on update | Medium | Medium | Check if display_name in updates before validating |
| Session detachment | Low | Medium | Follow session management pattern from CLAUDE.md |

## Definition of Done Checklist

- [ ] T002: Helper method `_validate_name_unique_in_recipe` implemented
- [ ] T003: `create_finished_unit` calls validation helper
- [ ] T004: `update_finished_unit` calls validation helper (only when name changes)
- [ ] Case-insensitive comparison used
- [ ] ValidationError raised with user-friendly message
- [ ] Session management pattern followed

## Review Guidance

**Key Verification Points**:
1. Validation uses case-insensitive comparison
2. Update validation excludes the current record from check
3. Error message is clear and actionable
4. Session parameter properly supported

**Test Scenarios**:
1. Create "Large Cookie" for Recipe A - should succeed
2. Create "Large Cookie" for Recipe A again - should fail with validation error
3. Create "Large Cookie" for Recipe B - should succeed (different recipe)
4. Update existing "Large Cookie" to "Extra Large Cookie" - should succeed
5. Update to name that already exists - should fail

## Activity Log

- 2026-01-09T00:00:00Z - system - lane=planned - Prompt created.
- 2026-01-09T18:11:04Z – unknown – lane=doing – Delegating to Gemini for parallel work
- 2026-01-09T18:15:44Z – unknown – lane=for_review – Added name uniqueness validation with case-insensitive comparison. Integrated into create and update methods.
- 2026-01-09T18:37:34Z – claude – lane=done – Code review complete: Approved. Name uniqueness validation with case-insensitive comparison correctly implemented.
