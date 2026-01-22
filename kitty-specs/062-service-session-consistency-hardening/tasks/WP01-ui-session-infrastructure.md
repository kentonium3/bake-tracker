---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
title: "UI Session Infrastructure"
phase: "Phase 0 - Foundation"
lane: "done"
assignee: "claude-opus"
agent: "claude-opus"
shell_pid: "74681"
review_status: "approved"
reviewed_by: "Kent Gale"
dependencies: []
history:
  - timestamp: "2026-01-22T15:30:43Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
  - timestamp: "2026-01-22T18:00:00Z"
    lane: "done"
    agent: "claude-opus"
    shell_pid: "74681"
    action: "Review passed, moved to done"
---

# Work Package Prompt: WP01 – UI Session Infrastructure

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Implementation Command

```bash
spec-kitty implement WP01
```

No dependencies - this is the foundation work package.

---

## Objectives & Success Criteria

Create a session context manager utility in the UI layer that enables UI components to manage database session lifecycle. This foundation enables all subsequent service changes to require session parameters.

**Success Criteria**:
- [ ] `ui_session()` context manager exists and yields a SQLAlchemy Session
- [ ] Session commits on successful exit, rolls back on exception
- [ ] Utility is importable from `src.ui.utils`
- [ ] Unit test validates context manager behavior
- [ ] Documentation in docstrings explains usage pattern

---

## Context & Constraints

**References**:
- Plan: `kitty-specs/062-service-session-consistency-hardening/plan.md`
- Research: `kitty-specs/062-service-session-consistency-hardening/research.md` (D2: UI Session Context Manager)
- Constitution: `.kittify/memory/constitution.md` (Principle V: Layered Architecture)

**Architectural Constraints**:
- UI utilities may import from `src.services.database` but NOT from service modules
- This creates a one-way dependency: UI → database (allowed by layered architecture)
- The utility is a thin wrapper - all logic stays in `session_scope()`

**Key Pattern** (from research.md):
```python
from contextlib import contextmanager
from src.services.database import session_scope

@contextmanager
def ui_session():
    """Session context manager for UI operations."""
    with session_scope() as session:
        yield session
```

---

## Subtasks & Detailed Guidance

### Subtask T001 – Create `src/ui/utils/__init__.py`

**Purpose**: Establish the utils subpackage in the UI layer for utility functions.

**Steps**:
1. Check if `src/ui/utils/` directory exists; create if needed
2. Create `src/ui/utils/__init__.py` with re-exports:
   ```python
   """UI utility functions."""
   from src.ui.utils.session_utils import ui_session

   __all__ = ["ui_session"]
   ```

**Files**:
- `src/ui/utils/__init__.py` (new file)

**Parallel?**: No - must exist before T002 imports from it.

**Notes**: Keep `__init__.py` minimal; only re-export public API.

---

### Subtask T002 – Create `src/ui/utils/session_utils.py` with `ui_session()`

**Purpose**: Implement the session context manager that UI components will use.

**Steps**:
1. Create `src/ui/utils/session_utils.py`
2. Import `session_scope` from `src.services.database`
3. Implement `ui_session()` as a generator-based context manager:

```python
"""Session utilities for UI layer.

This module provides session management utilities for UI components
that need to perform transactional database operations.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session

from src.services.database import session_scope


@contextmanager
def ui_session() -> Generator[Session, None, None]:
    """
    Context manager for UI operations requiring database sessions.

    Provides a SQLAlchemy Session that:
    - Commits automatically on successful exit
    - Rolls back automatically on exception
    - Can be passed to service functions requiring session

    Usage:
        from src.ui.utils import ui_session

        def handle_save_click(self):
            with ui_session() as session:
                event_service.create_event(name="My Event", session=session)
                event_service.assign_package(..., session=session)
                # All operations in same transaction

    Yields:
        Session: SQLAlchemy Session for database operations.

    Raises:
        Any exception from the wrapped code block (after rollback).
    """
    with session_scope() as session:
        yield session
```

**Files**:
- `src/ui/utils/session_utils.py` (new file, ~40 lines)

**Parallel?**: No - T001 must complete first.

**Notes**:
- The function is intentionally simple - a thin wrapper
- All transaction logic is in `session_scope()`
- Type hints help IDE autocomplete for users

---

### Subtask T003 – Add type hints and docstrings documenting usage pattern

**Purpose**: Ensure the utility is well-documented for other developers and AI agents.

**Steps**:
1. Verify type hints are complete (`-> Generator[Session, None, None]`)
2. Verify docstring includes:
   - Purpose description
   - Usage example showing multi-service transaction
   - Yields documentation
   - Raises documentation
3. Add module-level docstring explaining the purpose of session_utils.py

**Files**:
- `src/ui/utils/session_utils.py` (update from T002 if needed)

**Parallel?**: Can run alongside T002.

**Notes**: Documentation should help future agents understand the pattern without reading CLAUDE.md.

---

### Subtask T004 – Create unit test for `ui_session()`

**Purpose**: Verify the context manager behaves correctly in success and failure scenarios.

**Steps**:
1. Create `src/tests/test_ui_session_utils.py`
2. Implement tests:

```python
"""Tests for UI session utilities."""

import pytest
from sqlalchemy.orm import Session

from src.ui.utils import ui_session
from src.models import Event  # Or any simple model


class TestUISession:
    """Tests for ui_session context manager."""

    def test_ui_session_yields_session(self):
        """ui_session should yield a SQLAlchemy Session."""
        with ui_session() as session:
            assert isinstance(session, Session)

    def test_ui_session_commits_on_success(self):
        """Changes should persist after successful context exit."""
        # Create something in a session
        with ui_session() as session:
            # Query to verify session works (read-only test)
            result = session.execute("SELECT 1").scalar()
            assert result == 1

    def test_ui_session_rolls_back_on_exception(self):
        """Changes should roll back if exception raised."""
        try:
            with ui_session() as session:
                # Start some operation
                session.execute("SELECT 1")
                # Simulate error
                raise ValueError("Simulated error")
        except ValueError:
            pass  # Expected

        # Verify we can still use sessions (no corruption)
        with ui_session() as session:
            result = session.execute("SELECT 1").scalar()
            assert result == 1

    def test_ui_session_allows_nested_queries(self):
        """Session should support multiple queries."""
        with ui_session() as session:
            r1 = session.execute("SELECT 1").scalar()
            r2 = session.execute("SELECT 2").scalar()
            assert r1 == 1
            assert r2 == 2
```

**Files**:
- `src/tests/test_ui_session_utils.py` (new file, ~50 lines)

**Parallel?**: Can run after T002.

**Notes**:
- Tests are deliberately simple - we're testing the wrapper, not session_scope
- Use raw SQL for tests to avoid model dependencies
- Real integration tests will come when services use required sessions

---

## Test Strategy

**Run tests with**:
```bash
./run-tests.sh src/tests/test_ui_session_utils.py -v
```

**Expected results**:
- All 4 tests pass
- No warnings about session leaks

**Fixtures**: None required - `ui_session()` manages its own session.

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Import cycle ui ↔ services | Low | High | Only import from `src.services.database`, not service modules |
| Session not properly cleaned up | Low | High | `session_scope` handles cleanup; our wrapper just yields |
| Tests flaky due to database state | Low | Medium | Use read-only queries or clean up in tests |

---

## Definition of Done Checklist

- [ ] `src/ui/utils/__init__.py` exists with re-exports
- [ ] `src/ui/utils/session_utils.py` exists with `ui_session()` function
- [ ] Type hints complete (`-> Generator[Session, None, None]`)
- [ ] Docstring includes usage example
- [ ] Unit tests pass (`test_ui_session_utils.py`)
- [ ] No import cycles introduced
- [ ] Can import with `from src.ui.utils import ui_session`

---

## Review Guidance

**Reviewers should verify**:
1. Import path is correct: `from src.ui.utils import ui_session`
2. Type hints enable IDE autocomplete for Session methods
3. Docstring example is copy-pasteable and correct
4. Tests cover success and failure paths
5. No import of service modules (only `src.services.database`)

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

- 2026-01-22T15:30:43Z – system – lane=planned – Prompt created.
- 2026-01-22T15:51:10Z – claude-opus – shell_pid=72362 – lane=doing – Started implementation via workflow command
- 2026-01-22T15:57:46Z – claude-opus – shell_pid=72362 – lane=for_review – Ready for review: UI session infrastructure complete. Created ui_session() context manager, re-export in __init__.py, and 5 passing unit tests.
- 2026-01-22T16:00:45Z – claude-opus – shell_pid=74681 – lane=doing – Started review via workflow command
- 2026-01-22T16:01:39Z – claude-opus – shell_pid=74681 – lane=done – Review passed: All DoD criteria met. Clean implementation with proper type hints, docstrings, and 5 passing tests. No import cycles.
