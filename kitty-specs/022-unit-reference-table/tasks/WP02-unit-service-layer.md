---
work_package_id: WP02
title: Unit Service Layer
lane: done
history:
- timestamp: '2025-12-16T16:56:32Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
agent: claude
assignee: claude
phase: Phase 1 - Foundation
review_status: approved without changes
reviewed_by: claude-reviewer
shell_pid: claude-session
subtasks:
- T007
- T008
- T009
- T010
- T011
---

# Work Package Prompt: WP02 - Unit Service Layer

## Review Feedback

**Status**: **APPROVED**

**Review Summary**:
All acceptance criteria met. Service functions follow CLAUDE.md session management patterns correctly.

**Verification Performed**:
1. All required functions implemented: get_all_units, get_units_by_category, get_units_for_dropdown
2. Bonus helpers added: get_unit_by_code, is_valid_unit
3. All functions accept optional session parameter
4. All 28 tests pass
5. Full test suite passes (812 passed)

**Tests Executed**:
- `pytest src/tests/test_unit_service.py -v` - 28/28 passed

---

## Objectives & Success Criteria

**Goal**: Create helper functions for querying units by category and formatting for dropdowns.

**Success Criteria**:
- `unit_service.py` created with all helper functions
- `get_all_units()` returns all 27 units
- `get_units_by_category(category)` filters correctly
- `get_units_for_dropdown(categories)` returns formatted list with category headers
- Functions follow session management patterns from CLAUDE.md
- All tests pass

## Context & Constraints

**Reference Documents**:
- `kitty-specs/022-unit-reference-table/plan.md` - Service layer requirements
- `CLAUDE.md` - Session management patterns (CRITICAL)

**Architectural Constraints**:
- Service functions MUST accept optional `session=None` parameter
- Follow existing service patterns in `src/services/`
- No UI dependencies in service layer

**Dropdown Format**:
```python
# Example output of get_units_for_dropdown(['weight', 'volume'])
[
    "-- Weight --",
    "oz",
    "lb",
    "g",
    "kg",
    "-- Volume --",
    "tsp",
    "tbsp",
    "cup",
    ...
]
```

## Subtasks & Detailed Guidance

### Subtask T007 - Create `src/services/unit_service.py` with query functions

**Purpose**: Establish the service file with proper imports and structure.

**Steps**:
1. Create `src/services/unit_service.py`
2. Add imports:
   ```python
   from typing import List, Optional
   from sqlalchemy.orm import Session
   from ..models.unit import Unit
   from .database import session_scope
   ```
3. Add module docstring explaining purpose

**Files**: `src/services/unit_service.py` (create)

**Parallel?**: No - foundational

---

### Subtask T008 - Implement `get_all_units()` function

**Purpose**: Return all units ordered by category and sort_order.

**Steps**:
1. Create function with signature:
   ```python
   def get_all_units(session: Optional[Session] = None) -> List[Unit]:
   ```
2. Follow session pattern from CLAUDE.md:
   - If session provided, use it directly
   - If not, use session_scope() context manager
3. Query: `session.query(Unit).order_by(Unit.category, Unit.sort_order).all()`
4. Return list of Unit objects

**Files**: `src/services/unit_service.py` (modify)

**Example**:
```python
def get_all_units(session: Optional[Session] = None) -> List[Unit]:
    """Get all units ordered by category and sort_order."""
    def _impl(sess: Session) -> List[Unit]:
        return sess.query(Unit).order_by(Unit.category, Unit.sort_order).all()

    if session is not None:
        return _impl(session)
    with session_scope() as sess:
        return _impl(sess)
```

**Parallel?**: No - depends on T007

---

### Subtask T009 - Implement `get_units_by_category(category)` function

**Purpose**: Return units filtered by a specific category.

**Steps**:
1. Create function with signature:
   ```python
   def get_units_by_category(category: str, session: Optional[Session] = None) -> List[Unit]:
   ```
2. Follow same session pattern
3. Query: `session.query(Unit).filter(Unit.category == category).order_by(Unit.sort_order).all()`
4. Return filtered list

**Files**: `src/services/unit_service.py` (modify)

**Parallel?**: No - depends on T007

---

### Subtask T010 - Implement `get_units_for_dropdown(categories)` with category headers

**Purpose**: Return formatted list for CTkComboBox with category headers.

**Steps**:
1. Create function with signature:
   ```python
   def get_units_for_dropdown(categories: List[str], session: Optional[Session] = None) -> List[str]:
   ```
2. For each category in categories:
   - Add category header: `f"-- {category.title()} --"`
   - Add unit codes for that category
3. Return list of strings suitable for CTkComboBox values

**Files**: `src/services/unit_service.py` (modify)

**Example Output**:
```python
get_units_for_dropdown(['weight', 'volume'])
# Returns:
# ["-- Weight --", "oz", "lb", "g", "kg", "-- Volume --", "tsp", "tbsp", ...]
```

**Note**: Category headers start with "--" which UI will use to detect non-selectable items.

**Parallel?**: No - depends on T009

---

### Subtask T011 - Write tests for unit_service in `src/tests/test_unit_service.py`

**Purpose**: Verify all service functions work correctly.

**Steps**:
1. Create `src/tests/test_unit_service.py`
2. Test cases:
   - `get_all_units()` returns 27 units
   - `get_all_units()` returns units ordered by category, sort_order
   - `get_units_by_category('weight')` returns 4 units
   - `get_units_by_category('volume')` returns 9 units
   - `get_units_by_category('count')` returns 4 units
   - `get_units_by_category('package')` returns 10 units
   - `get_units_for_dropdown(['weight'])` starts with "-- Weight --"
   - `get_units_for_dropdown(['weight', 'volume'])` has 2 category headers
   - `get_units_for_dropdown()` returns unit codes (not Unit objects)

**Files**: `src/tests/test_unit_service.py` (create)

**Parallel?**: Yes - can use TDD approach

---

## Test Strategy

**Required Tests**:
- `src/tests/test_unit_service.py` - Service function validation

**Run Command**:
```bash
pytest src/tests/test_unit_service.py -v
```

**Fixtures Needed**:
- Database with seeded units (use existing test fixtures or create fresh)

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Session management issues | Medium | Follow CLAUDE.md patterns exactly |
| Order inconsistency | Low | Use explicit ORDER BY in queries |

---

## Definition of Done Checklist

- [ ] `src/services/unit_service.py` created
- [ ] `get_all_units()` implemented and tested
- [ ] `get_units_by_category()` implemented and tested
- [ ] `get_units_for_dropdown()` implemented and tested
- [ ] All functions accept optional session parameter
- [ ] `src/tests/test_unit_service.py` written and passing
- [ ] All existing tests still pass

---

## Review Guidance

**Acceptance Checkpoints**:
1. Verify session parameter handling matches CLAUDE.md patterns
2. Verify `get_units_for_dropdown()` output format matches expected
3. Run `pytest src/tests/test_unit_service.py -v` - all pass

---

## Activity Log

- 2025-12-16T16:56:32Z - system - lane=planned - Prompt created.
- 2025-12-16T17:35:30Z – system – shell_pid= – lane=doing – Starting implementation of Unit Service Layer
- 2025-12-16T17:40:00Z – system – shell_pid= – lane=for_review – Implementation complete: All 28 service tests passing
- 2025-12-16T17:55:40Z – system – shell_pid= – lane=done – Code review APPROVED: All 28 tests pass, session management follows CLAUDE.md patterns
