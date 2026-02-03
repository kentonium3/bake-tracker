---
work_package_id: WP08
title: Type Hints Completion
lane: "for_review"
dependencies: []
subtasks:
- T042
- T043
- T044
- T045
- T046
phase: Phase 4 - Type Hints
assignee: ''
agent: "claude"
shell_pid: "17496"
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-02-03T16:10:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP08 - Type Hints Completion

## Objectives & Success Criteria

- Add complete type hints to all public service functions
- Fix `session=None` parameters to use `Optional[Session]`
- Update return types to remove Optional where exceptions are now raised
- Run mypy and fix all type errors
- Verify IDE autocomplete works

## Context & Constraints

- **Depends on WP02-WP07**: Return types change as functions are updated
- Many functions already have type hints - focus on gaps
- Use `from typing import Optional, List, Dict, Any`
- Session parameter pattern: `session: Optional[Session] = None`

## Subtasks & Detailed Guidance

### Subtask T042 - Add type hints to functions missing them

**Purpose**: Ensure all public service functions have parameter and return type hints.

**Steps**:
1. Run mypy to identify missing type hints:
   ```bash
   mypy src/services/ --ignore-missing-imports 2>&1 | grep "missing"
   ```

2. For each function missing hints, add them following patterns:

**Common patterns**:
```python
# ORM object returns
def get_item(item_id: int) -> Item:

# List returns
def get_all_items() -> List[Item]:

# Dict returns
def get_summary() -> Dict[str, Any]:

# Optional parameters
def search(query: Optional[str] = None) -> List[Item]:

# Session parameter (standard pattern)
def operation(..., session: Optional[Session] = None) -> ReturnType:
```

**Files**: Multiple files in `src/services/`

### Subtask T043 - Fix session=None parameters

**Purpose**: Ensure all `session=None` parameters use proper type hint.

**Steps**:
1. Find functions with `session=None`:
   ```bash
   grep -r "session=None" src/services/ | grep "def "
   ```

2. Update each to use `Optional[Session]`:

**Before**:
```python
def get_ingredient(slug: str, session=None) -> Ingredient:
```

**After**:
```python
def get_ingredient(slug: str, session: Optional[Session] = None) -> Ingredient:
```

3. Add import if missing:
   ```python
   from typing import Optional
   from sqlalchemy.orm import Session
   ```

**Files**: Multiple files in `src/services/`

### Subtask T044 - Update return types to remove Optional

**Purpose**: After WP02-WP07, functions that now raise exceptions should not return Optional.

**Steps**:
1. Review all functions updated in WP02-WP07
2. Ensure return type is not Optional (e.g., `Recipe` not `Optional[Recipe]`)
3. This should already be done during those WPs, but verify

**Files**: All service files updated in WP02-WP07

### Subtask T045 - Run mypy and fix errors

**Purpose**: Ensure type hints are complete and correct.

**Steps**:
1. Run mypy on services:
   ```bash
   mypy src/services/ --ignore-missing-imports
   ```

2. Fix any errors:
   - Missing type hints → add them
   - Type mismatches → fix the code or hint
   - Import errors → add missing imports

3. Run again until no errors

**Common fixes**:
```python
# Dict without type args
data: dict  # Bad
data: Dict[str, Any]  # Good

# List without type args
items: list  # Bad
items: List[Item]  # Good

# Missing return type
def func():  # Bad
def func() -> None:  # Good
```

**Files**: `src/services/`

### Subtask T046 - Verify IDE autocomplete works

**Purpose**: Confirm type hints enable IDE features.

**Steps**:
1. Open VS Code (or preferred IDE)
2. Open a service file (e.g., `recipe_service.py`)
3. Test autocomplete on function calls:
   - Type `get_recipe_by_slug(` and verify parameter hints appear
   - Type `recipe.` after getting a recipe and verify attribute hints appear

4. Document any issues found

**Files**: Manual verification, no code changes

## Test Strategy

Run mypy:
```bash
mypy src/services/ --ignore-missing-imports
```

Run all tests to ensure type changes didn't break anything:
```bash
./run-tests.sh -v
```

## Risks & Mitigations

- **mypy errors cascade**: Fix one at a time
- **Breaking changes**: Run tests after each batch of fixes
- **Complex generic types**: Use `Any` where appropriate for dynamic dicts

## Definition of Done Checklist

- [ ] All public service functions have parameter type hints
- [ ] All public service functions have return type hints
- [ ] All `session=None` parameters typed as `Optional[Session]`
- [ ] Return types reflect exception-raising behavior (no Optional)
- [ ] `mypy src/services/` passes with no errors
- [ ] IDE autocomplete verified working
- [ ] All tests pass

## Review Guidance

- Verify type hints are accurate (not just added to pass mypy)
- Check Session import is from sqlalchemy.orm
- Ensure Generic types use proper parameters (List[T], Dict[K, V])

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-02-03T17:48:04Z – claude – shell_pid=17496 – lane=doing – Started implementation via workflow command
- 2026-02-03T22:26:42Z – claude – shell_pid=17496 – lane=for_review – Ready for review: Added Optional[Session] to ~40 session parameters across 15+ service files, fixed implicit Optional issues, fixed type annotation errors
