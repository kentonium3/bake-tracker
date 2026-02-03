---
work_package_id: WP02
title: Recipe & Ingredient Service Updates
lane: "doing"
dependencies: [WP01]
base_branch: 094-core-api-standardization-WP01
base_commit: 4f0333494559e2a44d97431f1ae745eda905680c
created_at: '2026-02-03T16:24:36.019494+00:00'
subtasks:
- T009
- T010
- T011
- T012
- T013
phase: Phase 2 - Core Services
assignee: ''
agent: ''
shell_pid: "1324"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T16:10:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP02 - Recipe & Ingredient Service Updates

## Objectives & Success Criteria

- Update `recipe_service.py` functions to raise exceptions instead of returning None
- Update all calling code to handle exceptions
- Update tests to expect exceptions
- Remove `Optional` from return types where exceptions are now raised

## Context & Constraints

- **Depends on WP01**: Exception types must be available
- Reference: `src/services/recipe_service.py`
- Reference: `src/services/ingredient_service.py` (already uses exceptions - model to follow)
- `get_ingredient()` in ingredient_service.py already raises `IngredientNotFoundBySlug` - use as pattern

## Subtasks & Detailed Guidance

### Subtask T009 - Update get_recipe_by_slug() to raise exception

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (src/services/recipe_service.py:189):
```python
def get_recipe_by_slug(
    slug: str, session: Optional[Session] = None
) -> Optional[Recipe]:
    # ... returns None if not found
```

**Target Pattern**:
```python
def get_recipe_by_slug(
    slug: str, session: Optional[Session] = None
) -> Recipe:
    """
    Get recipe by slug.

    Raises:
        RecipeNotFoundBySlug: If recipe doesn't exist
    """
    # ... raise RecipeNotFoundBySlug(slug) if not found
```

**Steps**:
1. Import `RecipeNotFoundBySlug` from exceptions
2. Change return type from `Optional[Recipe]` to `Recipe`
3. After query, check if result is None and raise exception
4. Update docstring to document exception

**Files**: `src/services/recipe_service.py`

### Subtask T010 - Update get_recipe_by_name() to raise exception

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (src/services/recipe_service.py:487):
```python
def get_recipe_by_name(name: str) -> Optional[Recipe]:
```

**Steps**:
1. Import `RecipeNotFoundByName` from exceptions
2. Change return type from `Optional[Recipe]` to `Recipe`
3. After query, check if result is None and raise exception
4. Update docstring

**Files**: `src/services/recipe_service.py`

### Subtask T011 - Update calling code for recipe functions

**Purpose**: All code that calls these functions must handle exceptions.

**Steps**:
1. Find all call sites with grep:
   ```bash
   grep -r "get_recipe_by_slug" src/
   grep -r "get_recipe_by_name" src/
   ```
2. For each call site:
   - If code checked for None before, replace with try/except
   - If code assumed result was always valid, wrap in try/except and handle error

**Common patterns to update**:
```python
# Before:
recipe = get_recipe_by_slug(slug)
if recipe is None:
    show_error("Not found")
    return
# Use recipe...

# After:
try:
    recipe = get_recipe_by_slug(slug)
    # Use recipe...
except RecipeNotFoundBySlug:
    show_error("Not found")
    return
```

**Files**: Multiple files in `src/ui/`, `src/services/`

### Subtask T012 - Update recipe tests

**Purpose**: Tests should expect exceptions for not-found cases.

**Steps**:
1. Find existing tests for `get_recipe_by_slug` and `get_recipe_by_name`
2. Update tests that check for None return to use `pytest.raises`

**Example**:
```python
# Before:
def test_get_recipe_by_slug_not_found():
    result = get_recipe_by_slug("nonexistent")
    assert result is None

# After:
def test_get_recipe_by_slug_not_found():
    with pytest.raises(RecipeNotFoundBySlug) as exc:
        get_recipe_by_slug("nonexistent")
    assert exc.value.slug == "nonexistent"
```

**Files**: `src/tests/services/test_recipe_service.py`

### Subtask T013 - Review ingredient_service.py consistency

**Purpose**: Verify ingredient_service.py already follows the exception pattern.

**Steps**:
1. Read `src/services/ingredient_service.py`
2. Verify `get_ingredient()` raises `IngredientNotFoundBySlug`
3. Check if any other functions return Optional that should raise
4. Document findings - this is the pattern other services should follow

**Files**: `src/services/ingredient_service.py` (review only, likely no changes)
**Parallel?**: Yes - can be done while T009-T012 are in progress

## Test Strategy

Run the recipe service tests after changes:
```bash
./run-tests.sh src/tests/services/test_recipe_service.py -v
```

Verify no regressions:
```bash
./run-tests.sh -v
```

## Risks & Mitigations

- **Breaking UI**: Test UI flows that use recipe lookup
- **Missing call sites**: Use grep comprehensively before changing function
- **Session handling**: Ensure exception is raised before session closes

## Definition of Done Checklist

- [ ] `get_recipe_by_slug()` raises `RecipeNotFoundBySlug`
- [ ] `get_recipe_by_name()` raises `RecipeNotFoundByName`
- [ ] Return types updated (no Optional)
- [ ] All calling code updated to handle exceptions
- [ ] Tests updated to expect exceptions
- [ ] All tests pass

## Review Guidance

- Check all call sites were updated
- Verify exception includes meaningful context (slug/name)
- Ensure UI error handling still works

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
