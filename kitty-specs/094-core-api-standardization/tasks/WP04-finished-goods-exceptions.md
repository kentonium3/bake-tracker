---
work_package_id: WP04
title: Finished Goods Service Updates
lane: "planned"
dependencies: [WP01]
base_branch: 094-core-api-standardization-WP01
base_commit: 4f0333494559e2a44d97431f1ae745eda905680c
created_at: '2026-02-03T16:36:27.098574+00:00'
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 2 - Core Services
assignee: ''
agent: "codex"
shell_pid: "51956"
review_status: "has_feedback"
reviewed_by: "Kent Gale"
history:
- timestamp: '2026-02-03T16:10:45Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP04 - Finished Goods Service Updates

## Objectives & Success Criteria

- Update `finished_good_service.py` get functions to raise exceptions
- Update `finished_unit_service.py` get functions to raise exceptions
- Handle both class methods and module-level wrappers
- Update all calling code and tests

## Context & Constraints

- **Depends on WP01**: Exception types must be available
- Reference: `src/services/finished_good_service.py`
- Reference: `src/services/finished_unit_service.py`
- Both services have class-based implementations with module-level wrapper functions
- Must update both the class method AND the wrapper

## Subtasks & Detailed Guidance

### Subtask T020 - Update get_finished_good_by_id()

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (finished_good_service.py has class and wrapper):
```python
# Class method (line 86)
def get_finished_good_by_id(finished_good_id: int) -> Optional[FinishedGood]:

# Module wrapper (line 1856)
def get_finished_good_by_id(finished_good_id: int) -> Optional[FinishedGood]:
    return FinishedGoodService.get_finished_good_by_id(finished_good_id)
```

**Steps**:
1. Import `FinishedGoodNotFoundById` from exceptions
2. Update class method to raise exception
3. Update return type on both class method and wrapper
4. Wrapper will automatically propagate exception

**Files**: `src/services/finished_good_service.py`

### Subtask T021 - Update get_finished_good_by_slug()

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (line 125 class, line 1861 wrapper):
```python
def get_finished_good_by_slug(slug: str) -> Optional[FinishedGood]:
```

**Steps**:
1. Import `FinishedGoodNotFoundBySlug` from exceptions
2. Update class method to raise exception
3. Update return types

**Files**: `src/services/finished_good_service.py`

### Subtask T022 - Update get_finished_unit_by_id()

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (finished_unit_service.py line 133 class, line 840 wrapper):
```python
def get_finished_unit_by_id(finished_unit_id: int) -> Optional[FinishedUnit]:
```

**Steps**:
1. Import `FinishedUnitNotFoundById` from exceptions
2. Update class method to raise exception
3. Update return types

**Files**: `src/services/finished_unit_service.py`

### Subtask T023 - Update get_finished_unit_by_slug()

**Purpose**: Convert from Optional return to exception-based error handling.

**Current Pattern** (line 172 class, line 845 wrapper):
```python
def get_finished_unit_by_slug(slug: str) -> Optional[FinishedUnit]:
```

**Steps**:
1. Import `FinishedUnitNotFoundBySlug` from exceptions
2. Update class method to raise exception
3. Update return types

**Files**: `src/services/finished_unit_service.py`

### Subtask T024 - Update calling code for finished goods functions

**Purpose**: All code that calls these functions must handle exceptions.

**Steps**:
1. Find all call sites:
   ```bash
   grep -r "get_finished_good_by_id" src/
   grep -r "get_finished_good_by_slug" src/
   grep -r "get_finished_unit_by_id" src/
   grep -r "get_finished_unit_by_slug" src/
   ```
2. For each call site, wrap in try/except or verify exception handling exists

**Key files to check**:
- `src/ui/` - Finished goods UI components
- `src/services/composition_service.py` - Uses finished goods
- `src/services/assembly_service.py` - Uses finished goods

**Files**: Multiple files

### Subtask T025 - Update finished goods tests

**Purpose**: Tests should expect exceptions for not-found cases.

**Steps**:
1. Find tests for finished_good_service and finished_unit_service
2. Update tests checking for None to use `pytest.raises`

**Files**:
- `src/tests/services/test_finished_good_service.py`
- `src/tests/services/test_finished_unit_service.py`

## Test Strategy

Run affected tests:
```bash
./run-tests.sh src/tests/services/test_finished_good_service.py -v
./run-tests.sh src/tests/services/test_finished_unit_service.py -v
```

## Risks & Mitigations

- **Class/wrapper pattern**: Must update both levels
- **Composition dependencies**: Verify composition service still works
- **Assembly workflows**: Test assembly creation flows

## Definition of Done Checklist

- [ ] `get_finished_good_by_id()` raises `FinishedGoodNotFoundById` (class + wrapper)
- [ ] `get_finished_good_by_slug()` raises `FinishedGoodNotFoundBySlug` (class + wrapper)
- [ ] `get_finished_unit_by_id()` raises `FinishedUnitNotFoundById` (class + wrapper)
- [ ] `get_finished_unit_by_slug()` raises `FinishedUnitNotFoundBySlug` (class + wrapper)
- [ ] Return types updated (no Optional)
- [ ] All calling code updated
- [ ] Tests updated
- [ ] All tests pass

## Review Guidance

- Verify both class methods and wrappers are updated
- Check composition and assembly integrations
- Ensure Finished Goods UI tab works correctly

## Activity Log

- 2026-02-03T16:10:45Z - system - lane=planned - Prompt generated via /spec-kitty.tasks
- 2026-02-03T16:39:01Z – unknown – shell_pid=4550 – lane=for_review – Finished goods and unit service exception handling complete. All 4 get functions now raise domain-specific exceptions for both class methods and wrappers.
- 2026-02-03T22:24:24Z – codex – shell_pid=51956 – lane=doing – Started review via workflow command
- 2026-02-03T22:25:09Z – codex – shell_pid=51956 – lane=planned – Moved to planned
- 2026-02-03T22:28:44Z – claude – shell_pid=31234 – lane=doing – Started implementation via workflow command
- 2026-02-03T22:38:16Z – claude – shell_pid=31234 – lane=for_review – Ready for review: All 4 get functions raise domain-specific exceptions, all 3493 tests pass
- 2026-02-03T22:39:42Z – codex – shell_pid=51956 – lane=doing – Started review via workflow command
- 2026-02-03T22:40:30Z – codex – shell_pid=51956 – lane=planned – Moved to planned
