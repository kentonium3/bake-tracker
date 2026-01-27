---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Service Unit Tests"
phase: "Phase 1 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: ["WP01"]
history:
  - timestamp: "2026-01-27T15:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Service Unit Tests

## Implementation Command

```bash
spec-kitty implement WP02 --base WP01
```

## Objectives & Success Criteria

Create comprehensive unit tests for `assembly_feasibility_service.py` covering all scenarios.

**Success Criteria**:
- [ ] All tests pass: `./run-tests.sh src/tests/test_assembly_feasibility_service.py -v`
- [ ] Basic feasibility scenario tested
- [ ] Shortfall detection tested
- [ ] Bundle validation tested
- [ ] Edge cases tested (empty event, no decisions)
- [ ] Decision coverage metrics tested

## Context & Constraints

**Reference Documents**:
- `kitty-specs/076-assembly-feasibility-single-screen-planning/plan.md` - Service interface
- `src/tests/test_inventory_gap_service.py` - Fixture patterns to follow
- `src/tests/test_batch_decision_service.py` - More fixture patterns

**Testing from Worktree** (from CLAUDE.md):
```bash
# Use the helper script from anywhere:
./run-tests.sh src/tests/test_assembly_feasibility_service.py -v
```

**Key Model Fields**:
- `Product.product_name` (not `name`)
- `FinishedUnit.items_per_batch`, `FinishedUnit.yield_mode`
- `BatchDecision.batches`, `BatchDecision.finished_unit_id`

## Subtasks & Detailed Guidance

### Subtask T006 – Test Basic Feasibility (Sufficient Production)

**Purpose**: Verify service correctly identifies when production meets requirements.

**Steps**:
1. Create test file `src/tests/test_assembly_feasibility_service.py`
2. Add imports and fixtures:

```python
"""Tests for assembly_feasibility_service (F076)."""

import pytest
from src.services.assembly_feasibility_service import (
    calculate_assembly_feasibility,
    AssemblyFeasibilityResult,
    FGFeasibilityStatus,
    ComponentStatus,
)
from src.services.database import session_scope
from src.models import (
    Event,
    Recipe,
    FinishedUnit,
    FinishedGood,
    FinishedGoodComponent,
    EventFinishedGood,
    BatchDecision,
)
from src.models.finished_unit import YieldMode


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create a fresh test database."""
    from src.services.database import init_db, get_engine

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    engine = get_engine(force_new=True)
    init_db(engine)
    yield engine


@pytest.fixture
def test_event(test_db):
    """Create a test event."""
    with session_scope() as session:
        event = Event(name="Test Event")
        session.add(event)
        session.flush()
        event_id = event.id
    return event_id


@pytest.fixture
def basic_recipe(test_db):
    """Create a basic recipe."""
    with session_scope() as session:
        recipe = Recipe(name="Test Recipe", slug="test-recipe")
        session.add(recipe)
        session.flush()
        recipe_id = recipe.id
    return recipe_id


@pytest.fixture
def basic_finished_unit(test_db, basic_recipe):
    """Create a finished unit that yields 10 items per batch."""
    with session_scope() as session:
        fu = FinishedUnit(
            display_name="Test Cookies",
            slug="test-cookies",
            recipe_id=basic_recipe,
            items_per_batch=10,
            yield_mode=YieldMode.DISCRETE_COUNT,
        )
        session.add(fu)
        session.flush()
        fu_id = fu.id
    return fu_id


@pytest.fixture
def basic_finished_good(test_db, basic_finished_unit):
    """Create a finished good with one FU component."""
    with session_scope() as session:
        fg = FinishedGood(
            name="Cookie Box",
            slug="cookie-box",
        )
        session.add(fg)
        session.flush()

        # Add component
        comp = FinishedGoodComponent(
            finished_good_id=fg.id,
            finished_unit_id=basic_finished_unit,
            component_quantity=1,
        )
        session.add(comp)
        session.flush()
        fg_id = fg.id
    return fg_id


def test_basic_feasibility_sufficient(
    test_db, test_event, basic_finished_good, basic_finished_unit
):
    """Test that sufficient production yields can_assemble=True."""
    with session_scope() as session:
        # Add FG to event (need 5 cookie boxes = 5 cookies)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=5,
        )
        session.add(efg)

        # Add batch decision: 1 batch = 10 cookies (more than 5 needed)
        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=session.query(FinishedUnit).get(basic_finished_unit).recipe_id,
            batches=1,
        )
        session.add(bd)
        session.commit()

    # Calculate feasibility
    result = calculate_assembly_feasibility(test_event)

    assert result.overall_feasible is True
    assert len(result.finished_goods) == 1
    assert result.finished_goods[0].can_assemble is True
    assert result.finished_goods[0].shortfall == 0
```

**Files**: `src/tests/test_assembly_feasibility_service.py` (new)

**Validation**:
- [ ] Test passes with `./run-tests.sh src/tests/test_assembly_feasibility_service.py::test_basic_feasibility_sufficient -v`

---

### Subtask T007 – Test Shortfall Detection

**Purpose**: Verify service correctly identifies production shortfalls.

**Steps**:
1. Add test for shortfall scenario:

```python
def test_shortfall_detection(
    test_db, test_event, basic_finished_good, basic_finished_unit
):
    """Test that insufficient production yields can_assemble=False with shortfall."""
    with session_scope() as session:
        # Add FG to event (need 15 cookies)
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=15,
        )
        session.add(efg)

        # Add batch decision: 1 batch = 10 cookies (less than 15 needed)
        fu = session.query(FinishedUnit).get(basic_finished_unit)
        bd = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=fu.recipe_id,
            batches=1,
        )
        session.add(bd)
        session.commit()

    result = calculate_assembly_feasibility(test_event)

    assert result.overall_feasible is False
    assert len(result.finished_goods) == 1
    fg_status = result.finished_goods[0]
    assert fg_status.can_assemble is False
    assert fg_status.shortfall > 0  # Should be 5 (15 needed - 10 available)
    assert fg_status.quantity_needed == 15
```

**Files**: `src/tests/test_assembly_feasibility_service.py`

**Validation**:
- [ ] Test passes
- [ ] Shortfall amount is correct

---

### Subtask T008 – Test Bundle Component Validation

**Purpose**: Verify nested bundle FGs are validated correctly.

**Steps**:
1. Create fixtures for a bundle (FG containing another FG or multiple FUs):

```python
@pytest.fixture
def second_finished_unit(test_db, basic_recipe):
    """Create a second FU (e.g., brownies)."""
    with session_scope() as session:
        fu = FinishedUnit(
            display_name="Test Brownies",
            slug="test-brownies",
            recipe_id=basic_recipe,
            items_per_batch=8,
            yield_mode=YieldMode.DISCRETE_COUNT,
        )
        session.add(fu)
        session.flush()
        fu_id = fu.id
    return fu_id


@pytest.fixture
def bundle_finished_good(test_db, basic_finished_unit, second_finished_unit):
    """Create a bundle FG with two FU components."""
    with session_scope() as session:
        fg = FinishedGood(
            name="Assorted Box",
            slug="assorted-box",
        )
        session.add(fg)
        session.flush()

        # Add both FU components
        comp1 = FinishedGoodComponent(
            finished_good_id=fg.id,
            finished_unit_id=basic_finished_unit,
            component_quantity=2,  # 2 cookies per box
        )
        comp2 = FinishedGoodComponent(
            finished_good_id=fg.id,
            finished_unit_id=second_finished_unit,
            component_quantity=2,  # 2 brownies per box
        )
        session.add(comp1)
        session.add(comp2)
        session.flush()
        fg_id = fg.id
    return fg_id


def test_bundle_validation_all_sufficient(
    test_db, test_event, bundle_finished_good, basic_finished_unit, second_finished_unit
):
    """Test bundle where all components are sufficient."""
    with session_scope() as session:
        # Need 3 assorted boxes = 6 cookies + 6 brownies
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=3,
        )
        session.add(efg)

        # 1 batch cookies = 10 (need 6) ✓
        fu1 = session.query(FinishedUnit).get(basic_finished_unit)
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=fu1.recipe_id,
            batches=1,
        )
        session.add(bd1)

        # 1 batch brownies = 8 (need 6) ✓
        fu2 = session.query(FinishedUnit).get(second_finished_unit)
        bd2 = BatchDecision(
            event_id=test_event,
            finished_unit_id=second_finished_unit,
            recipe_id=fu2.recipe_id,
            batches=1,
        )
        session.add(bd2)
        session.commit()

    result = calculate_assembly_feasibility(test_event)

    assert result.overall_feasible is True
    fg_status = result.finished_goods[0]
    assert fg_status.can_assemble is True
    assert len(fg_status.components) == 2


def test_bundle_one_component_short(
    test_db, test_event, bundle_finished_good, basic_finished_unit, second_finished_unit
):
    """Test bundle where one component is insufficient."""
    with session_scope() as session:
        # Need 5 assorted boxes = 10 cookies + 10 brownies
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=5,
        )
        session.add(efg)

        # 1 batch cookies = 10 (need 10) ✓
        fu1 = session.query(FinishedUnit).get(basic_finished_unit)
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=fu1.recipe_id,
            batches=1,
        )
        session.add(bd1)

        # 1 batch brownies = 8 (need 10) ✗
        fu2 = session.query(FinishedUnit).get(second_finished_unit)
        bd2 = BatchDecision(
            event_id=test_event,
            finished_unit_id=second_finished_unit,
            recipe_id=fu2.recipe_id,
            batches=1,
        )
        session.add(bd2)
        session.commit()

    result = calculate_assembly_feasibility(test_event)

    assert result.overall_feasible is False
    fg_status = result.finished_goods[0]
    assert fg_status.can_assemble is False
    # One component is insufficient
    insufficient = [c for c in fg_status.components if not c.is_sufficient]
    assert len(insufficient) == 1
```

**Files**: `src/tests/test_assembly_feasibility_service.py`

**Validation**:
- [ ] Both tests pass
- [ ] Component count is correct

---

### Subtask T009 – Test Empty Event and Missing Decisions

**Purpose**: Verify edge cases are handled gracefully.

**Steps**:
1. Add tests for edge cases:

```python
def test_empty_event_no_fgs(test_db, test_event):
    """Test event with no FG selections returns feasible."""
    result = calculate_assembly_feasibility(test_event)

    assert result.overall_feasible is True
    assert len(result.finished_goods) == 0
    assert result.decided_count == 0
    assert result.total_fu_count == 0


def test_no_batch_decisions(test_db, test_event, basic_finished_good):
    """Test event with FGs but no batch decisions."""
    with session_scope() as session:
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=basic_finished_good,
            quantity=5,
        )
        session.add(efg)
        session.commit()

    result = calculate_assembly_feasibility(test_event)

    assert result.overall_feasible is False  # Can't assemble without decisions
    assert result.decided_count == 0
    assert result.total_fu_count > 0


def test_event_not_found(test_db):
    """Test that non-existent event raises ValidationError."""
    from src.services.exceptions import ValidationError

    with pytest.raises(ValidationError):
        calculate_assembly_feasibility(99999)
```

**Files**: `src/tests/test_assembly_feasibility_service.py`

**Validation**:
- [ ] All edge case tests pass

---

### Subtask T010 – Test Decision Coverage Metrics

**Purpose**: Verify decided_count and total_fu_count are accurate.

**Steps**:
1. Add test for coverage metrics:

```python
def test_decision_coverage_partial(
    test_db, test_event, bundle_finished_good, basic_finished_unit, second_finished_unit
):
    """Test that decision coverage correctly tracks partial decisions."""
    with session_scope() as session:
        # Add bundle that needs 2 FUs
        efg = EventFinishedGood(
            event_id=test_event,
            finished_good_id=bundle_finished_good,
            quantity=1,
        )
        session.add(efg)

        # Only add decision for one FU
        fu1 = session.query(FinishedUnit).get(basic_finished_unit)
        bd1 = BatchDecision(
            event_id=test_event,
            finished_unit_id=basic_finished_unit,
            recipe_id=fu1.recipe_id,
            batches=1,
        )
        session.add(bd1)
        session.commit()

    result = calculate_assembly_feasibility(test_event)

    # Should have 2 FUs needed, but only 1 decision
    assert result.total_fu_count == 2
    assert result.decided_count == 1
```

**Files**: `src/tests/test_assembly_feasibility_service.py`

**Validation**:
- [ ] Test passes
- [ ] Coverage metrics are accurate

## Test Strategy

**Run all tests**:
```bash
./run-tests.sh src/tests/test_assembly_feasibility_service.py -v
```

**Expected result**: All tests pass with no failures.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Fixture complexity | Base on existing test patterns |
| Session issues in tests | Use session_scope() consistently |

## Definition of Done Checklist

- [ ] All tests pass
- [ ] No linting errors in test file
- [ ] Tests cover all major scenarios from plan.md

## Review Guidance

- Verify test fixtures create valid data relationships
- Check that assertions match expected service behavior
- Ensure edge cases are covered

## Activity Log

- 2026-01-27T15:30:00Z – system – lane=planned – Prompt created.
