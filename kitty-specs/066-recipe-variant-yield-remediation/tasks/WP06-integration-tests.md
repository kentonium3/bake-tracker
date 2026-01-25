---
work_package_id: WP06
title: Integration Tests
lane: planned
dependencies:
- WP02
subtasks:
- T016
- T017
- T018
phase: Phase 4 - Validation
assignee: ''
agent: ''
shell_pid: ''
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-01-25T03:23:15Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
---

# Work Package Prompt: WP06 – Integration Tests

## Objectives & Success Criteria

**Goal**: Add integration tests verifying that planning_service and batch_calculation use the `get_finished_units()` primitive correctly.

**Success Criteria**:
- [ ] Integration test verifies planning_service calls `get_finished_units()`
- [ ] Integration test verifies batch_calculation calls `get_finished_units()`
- [ ] All existing primitive tests pass with updated docstrings
- [ ] No regressions in existing test suite

**Implementation Command**:
```bash
# Step 1: Create worktree based on WP02 branch
# Note: WP06 depends on both WP02 and WP03. Use WP02 as base, then merge WP03 if needed.
spec-kitty implement WP06 --base WP02

# Step 2: Change to worktree directory
cd .worktrees/066-recipe-variant-yield-remediation-WP06

# Step 3 (if WP03 changes needed): Merge WP03 into WP06 branch
# git merge 066-recipe-variant-yield-remediation-WP03
```

**Note**: The `--base WP02` flag creates the worktree from WP02's branch. If WP03 is also complete, you may need to merge it manually since `--base` only accepts one WP.

## Context & Constraints

**Background**:
WP02 and WP03 decoupled the planning and batch calculation services from direct model access. This WP adds integration tests to verify that the decoupling is correct and that the services call the primitive instead of accessing `recipe.finished_units` directly.

**Testing Approach**:
Use `unittest.mock.patch` to:
1. Mock `recipe_service.get_finished_units`
2. Call the service function
3. Assert that the mock was called with correct arguments

**Key Documents**:
- Spec: `kitty-specs/066-recipe-variant-yield-remediation/spec.md`
- Plan: `kitty-specs/066-recipe-variant-yield-remediation/plan.md`

**Existing Test File**: `src/tests/test_recipe_yield_primitives.py` (for T018)

## Subtasks & Detailed Guidance

### Subtask T016 – Create Integration Test for Planning Service

**Purpose**: Verify planning_service uses `get_finished_units()` primitive.

**Location**: New test file or add to existing: `src/tests/integration/test_service_decoupling.py`

**Test Approach**:
```python
"""Integration tests for service decoupling (F066)."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.base import Base
from src.models import Recipe, Event, EventProductionTarget
from src.services.planning import planning_service
from src.services import database


@pytest.fixture(scope="function")
def db_session():
    """Create in-memory test database."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)

    original_get_session = database.get_session
    database._session_factory = Session

    def patched_get_session():
        return Session()

    database.get_session = patched_get_session
    session = Session()

    yield session

    session.close()
    database.get_session = original_get_session


class TestPlanningServiceDecoupling:
    """Verify planning_service uses get_finished_units() primitive."""

    @patch('src.services.planning.planning_service.recipe_service.get_finished_units')
    def test_bulk_count_requirements_uses_primitive(self, mock_get_fus, db_session):
        """
        Planning service should call get_finished_units() instead of
        accessing recipe.finished_units directly.
        """
        # Setup: Create minimal test data
        recipe = Recipe(name="Test Recipe", category="Test")
        db_session.add(recipe)
        db_session.flush()

        event = Event(name="Test Event")
        db_session.add(event)
        db_session.flush()

        target = EventProductionTarget(
            event_id=event.id,
            recipe_id=recipe.id,
            target_batches=2,
        )
        db_session.add(target)
        db_session.commit()

        # Configure mock to return yield data
        mock_get_fus.return_value = [
            {
                "id": 1,
                "slug": "test-cookie",
                "display_name": "Test Cookie",
                "items_per_batch": 24,
                "item_unit": "cookie",
                "yield_mode": "discrete_count",
            }
        ]

        # Call the function that should use the primitive
        # Note: Adjust this to match actual function signature
        # This is a conceptual example - verify actual function names
        try:
            # The actual function may vary - check planning_service for correct entry point
            planning_service._calculate_bulk_count_requirements(event, db_session)
        except Exception:
            pass  # Function may not exist exactly as named; adjust as needed

        # Verify the primitive was called
        mock_get_fus.assert_called()
        # Optionally verify call arguments
        # mock_get_fus.assert_called_with(recipe.id, session=db_session)
```

**Files**: `src/tests/integration/test_service_decoupling.py` (new or existing)

**Parallel**: Yes - can develop alongside T017

---

### Subtask T017 – Create Integration Test for Batch Calculation

**Purpose**: Verify batch_calculation uses `get_finished_units()` primitive.

**Location**: Same file as T016: `src/tests/integration/test_service_decoupling.py`

**Test Approach**:
```python
class TestBatchCalculationDecoupling:
    """Verify batch_calculation uses get_finished_units() primitive."""

    @patch('src.services.planning.batch_calculation.recipe_service.get_finished_units')
    def test_calculate_batches_uses_primitive(self, mock_get_fus, db_session):
        """
        Batch calculation should call get_finished_units() instead of
        accessing recipe.finished_units directly.
        """
        # Setup: Create minimal test data
        recipe = Recipe(name="Test Recipe", category="Test")
        db_session.add(recipe)
        db_session.flush()
        db_session.commit()

        # Configure mock
        mock_get_fus.return_value = [
            {
                "id": 1,
                "slug": "test-item",
                "display_name": "Test Item",
                "items_per_batch": 12,
                "item_unit": "item",
                "yield_mode": "discrete_count",
            }
        ]

        # Call batch calculation function
        from src.services.planning.batch_calculation import calculate_batches_from_targets
        # Note: Adjust function name to match actual API

        try:
            # Create appropriate test inputs for batch calculation
            # This is conceptual - verify actual function signatures
            pass
        except Exception:
            pass

        # Verify primitive was called
        mock_get_fus.assert_called()
```

**Files**: `src/tests/integration/test_service_decoupling.py`

**Parallel**: Yes - can develop alongside T016

---

### Subtask T018 – Verify Existing Primitive Tests Pass

**Purpose**: Confirm that docstring updates in WP01 didn't break existing tests.

**Location**: Existing file: `src/tests/test_recipe_yield_primitives.py`

**Steps**:
1. Run existing primitive tests
2. Verify all pass
3. Review test assertions match updated behavior (copied yields, not NULL)

**Command**:
```bash
./run-tests.sh src/tests/test_recipe_yield_primitives.py -v
```

**Expected Result**:
- All 11 tests pass (6 for `get_base_yield_structure`, 5 for `get_finished_units`)
- Tests correctly expect copied yield values for variants (Phase 1 fix verified this)

**If Tests Fail**: Investigate whether:
1. Docstring changes accidentally modified code (shouldn't happen in WP01)
2. Test expectations were wrong (unlikely - fixed during Phase 1)
3. Environment issue (run tests multiple times)

**Files**: `src/tests/test_recipe_yield_primitives.py` (verification only, no changes expected)

## Test Strategy

**Run Full Test Suite**:
```bash
./run-tests.sh src/tests/ -v
```

**Run Specific Integration Tests**:
```bash
./run-tests.sh src/tests/integration/test_service_decoupling.py -v
```

**Run Primitive Tests**:
```bash
./run-tests.sh src/tests/test_recipe_yield_primitives.py -v
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Mocking complexity | Start with simple assertions; add detail incrementally |
| Wrong patch path | Use full import path matching actual imports |
| Flaky tests | Use deterministic test data; avoid timing dependencies |

## Definition of Done Checklist

- [ ] T016: Planning service integration test created and passes
- [ ] T017: Batch calculation integration test created and passes
- [ ] T018: All existing primitive tests pass
- [ ] Full test suite passes
- [ ] Tests are documented with clear assertions
- [ ] Changes committed with clear message

## Review Guidance

- Verify patch paths match actual import paths in services
- Verify mock assertions are meaningful (not just "was called")
- Verify test names clearly describe what they're testing
- Run tests multiple times to ensure they're not flaky

## Activity Log

- 2026-01-25T03:23:15Z – system – lane=planned – Prompt created.
