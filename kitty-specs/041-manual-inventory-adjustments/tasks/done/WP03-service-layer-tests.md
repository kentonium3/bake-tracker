---
work_package_id: "WP03"
subtasks:
  - "T010"
  - "T011"
  - "T012"
  - "T013"
  - "T014"
  - "T015"
  - "T016"
title: "Service Layer Tests"
phase: "Phase 1 - Service Layer (Claude)"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "49789"
history:
  - timestamp: "2026-01-07T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 - Service Layer Tests

## Objectives & Success Criteria

- Create comprehensive unit tests for manual_adjustment() and get_depletion_history()
- Cover all validation scenarios from spec.md
- Test cost calculation accuracy
- Achieve >70% coverage per Constitution Principle IV

**Success**: `pytest src/tests/test_inventory_adjustment.py -v` passes with all tests green.

## Context & Constraints

**Reference Documents**:
- Spec: `kitty-specs/041-manual-inventory-adjustments/spec.md` (acceptance scenarios)
- Constitution: `.kittify/memory/constitution.md` (Principle IV: Test-Driven Development)
- Existing tests: `src/tests/` (follow established patterns)

**Constraints**:
- Use pytest fixtures for test data
- Tests must be isolated (no shared state between tests)
- Follow existing test patterns in the codebase

**Dependencies**:
- WP02 must be complete (service methods must exist)

## Subtasks & Detailed Guidance

### Subtask T010 - Create test file [P]

**Purpose**: Establish test file structure with fixtures.

**Steps**:
1. Create `src/tests/test_inventory_adjustment.py`
2. Add imports and fixtures:

```python
"""
Unit tests for manual inventory adjustment functionality.

Tests the manual_adjustment() and get_depletion_history() service methods.
"""

import pytest
from decimal import Decimal
from datetime import date

from src.models import InventoryItem, Product, Ingredient, InventoryDepletion
from src.models.enums import DepletionReason
from src.services.database import session_scope
from src.services.inventory_item_service import manual_adjustment, get_depletion_history
from src.services.exceptions import ValidationError as ServiceValidationError, InventoryItemNotFound


@pytest.fixture
def test_ingredient(test_session):
    """Create a test ingredient."""
    ingredient = Ingredient(
        display_name="Test Flour",
        slug="test_flour",
        category="Baking",
        recipe_unit="cup",
    )
    test_session.add(ingredient)
    test_session.flush()
    return ingredient


@pytest.fixture
def test_product(test_session, test_ingredient):
    """Create a test product."""
    product = Product(
        display_name="Test Brand Flour 5lb",
        ingredient_id=test_ingredient.id,
        package_unit="cup",
        package_unit_quantity=20,
    )
    test_session.add(product)
    test_session.flush()
    return product


@pytest.fixture
def test_inventory_item(test_session, test_product):
    """Create a test inventory item with 10 cups at $0.50/cup."""
    item = InventoryItem(
        product_id=test_product.id,
        quantity=10.0,
        unit_cost=0.50,
        purchase_date=date(2026, 1, 1),
    )
    test_session.add(item)
    test_session.flush()
    return item
```

**Files**: `src/tests/test_inventory_adjustment.py` (NEW)
**Parallel?**: Yes - establishes structure for T011-T016

### Subtask T011 - Test happy path [P]

**Purpose**: Verify basic depletion works correctly.

**Steps**:
```python
class TestManualAdjustmentHappyPath:
    """Tests for successful manual adjustments."""

    def test_deplete_with_spoilage_reason(self, test_session, test_inventory_item):
        """Depletion with SPOILAGE reason creates record and updates quantity."""
        initial_qty = test_inventory_item.quantity

        depletion = manual_adjustment(
            inventory_item_id=test_inventory_item.id,
            quantity_to_deplete=Decimal("3.0"),
            reason=DepletionReason.SPOILAGE,
            notes="Weevils discovered",
            session=test_session,
        )

        # Verify depletion record
        assert depletion.quantity_depleted == Decimal("3.0")
        assert depletion.depletion_reason == "spoilage"
        assert depletion.notes == "Weevils discovered"
        assert depletion.created_by == "desktop-user"

        # Verify inventory updated
        test_session.refresh(test_inventory_item)
        assert test_inventory_item.quantity == initial_qty - 3.0

    def test_deplete_all_reasons(self, test_session, test_inventory_item):
        """All manual depletion reasons work correctly."""
        reasons = [
            DepletionReason.SPOILAGE,
            DepletionReason.GIFT,
            DepletionReason.CORRECTION,
            DepletionReason.AD_HOC_USAGE,
        ]
        for reason in reasons:
            depletion = manual_adjustment(
                inventory_item_id=test_inventory_item.id,
                quantity_to_deplete=Decimal("0.5"),
                reason=reason,
                session=test_session,
            )
            assert depletion.depletion_reason == reason.value
```

**Files**: `src/tests/test_inventory_adjustment.py`
**Parallel?**: Yes - independent test case

### Subtask T012 - Test quantity > current fails [P]

**Purpose**: Verify validation prevents depleting more than available.

**Steps**:
```python
class TestManualAdjustmentValidation:
    """Tests for validation rules."""

    def test_cannot_deplete_more_than_available(self, test_session, test_inventory_item):
        """Depleting more than available raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc_info:
            manual_adjustment(
                inventory_item_id=test_inventory_item.id,
                quantity_to_deplete=Decimal("15.0"),  # Only 10 available
                reason=DepletionReason.SPOILAGE,
                session=test_session,
            )
        assert "only" in str(exc_info.value).lower()
        assert "10" in str(exc_info.value)
```

**Files**: `src/tests/test_inventory_adjustment.py`
**Parallel?**: Yes - independent test case

### Subtask T013 - Test quantity <= 0 fails [P]

**Purpose**: Verify validation prevents zero or negative quantities.

**Steps**:
```python
    def test_quantity_must_be_positive(self, test_session, test_inventory_item):
        """Zero or negative quantity raises ValidationError."""
        with pytest.raises(ServiceValidationError):
            manual_adjustment(
                inventory_item_id=test_inventory_item.id,
                quantity_to_deplete=Decimal("0"),
                reason=DepletionReason.SPOILAGE,
                session=test_session,
            )

        with pytest.raises(ServiceValidationError):
            manual_adjustment(
                inventory_item_id=test_inventory_item.id,
                quantity_to_deplete=Decimal("-1.0"),
                reason=DepletionReason.SPOILAGE,
                session=test_session,
            )
```

**Files**: `src/tests/test_inventory_adjustment.py`
**Parallel?**: Yes - independent test case

### Subtask T014 - Test notes required for OTHER [P]

**Purpose**: Verify OTHER reason requires notes.

**Steps**:
```python
    def test_other_reason_requires_notes(self, test_session, test_inventory_item):
        """OTHER reason without notes raises ValidationError."""
        with pytest.raises(ServiceValidationError) as exc_info:
            manual_adjustment(
                inventory_item_id=test_inventory_item.id,
                quantity_to_deplete=Decimal("1.0"),
                reason=DepletionReason.OTHER,
                notes=None,  # Missing notes
                session=test_session,
            )
        assert "notes" in str(exc_info.value).lower()

    def test_other_reason_with_notes_succeeds(self, test_session, test_inventory_item):
        """OTHER reason with notes succeeds."""
        depletion = manual_adjustment(
            inventory_item_id=test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.OTHER,
            notes="Custom reason explained here",
            session=test_session,
        )
        assert depletion.notes == "Custom reason explained here"
```

**Files**: `src/tests/test_inventory_adjustment.py`
**Parallel?**: Yes - independent test case

### Subtask T015 - Test cost calculation [P]

**Purpose**: Verify cost is calculated correctly.

**Steps**:
```python
class TestCostCalculation:
    """Tests for cost impact calculation."""

    def test_cost_equals_quantity_times_unit_cost(self, test_session, test_inventory_item):
        """Cost is calculated as quantity * unit_cost."""
        # item has unit_cost = 0.50
        depletion = manual_adjustment(
            inventory_item_id=test_inventory_item.id,
            quantity_to_deplete=Decimal("4.0"),
            reason=DepletionReason.SPOILAGE,
            session=test_session,
        )

        expected_cost = Decimal("4.0") * Decimal("0.50")  # $2.00
        assert depletion.cost == expected_cost

    def test_cost_with_decimal_quantity(self, test_session, test_inventory_item):
        """Cost calculation handles decimal quantities."""
        depletion = manual_adjustment(
            inventory_item_id=test_inventory_item.id,
            quantity_to_deplete=Decimal("2.5"),
            reason=DepletionReason.SPOILAGE,
            session=test_session,
        )

        expected_cost = Decimal("2.5") * Decimal("0.50")  # $1.25
        assert depletion.cost == expected_cost
```

**Files**: `src/tests/test_inventory_adjustment.py`
**Parallel?**: Yes - independent test case

### Subtask T016 - Test history DESC order [P]

**Purpose**: Verify get_depletion_history returns records in correct order.

**Steps**:
```python
class TestDepletionHistory:
    """Tests for depletion history retrieval."""

    def test_history_ordered_by_date_desc(self, test_session, test_inventory_item):
        """History returns records newest first."""
        # Create multiple depletions
        manual_adjustment(
            inventory_item_id=test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.SPOILAGE,
            notes="First",
            session=test_session,
        )
        manual_adjustment(
            inventory_item_id=test_inventory_item.id,
            quantity_to_deplete=Decimal("1.0"),
            reason=DepletionReason.GIFT,
            notes="Second",
            session=test_session,
        )

        history = get_depletion_history(
            inventory_item_id=test_inventory_item.id,
            session=test_session,
        )

        assert len(history) == 2
        # Newest should be first
        assert history[0].notes == "Second"
        assert history[1].notes == "First"

    def test_history_empty_for_new_item(self, test_session, test_inventory_item):
        """New item has empty history."""
        history = get_depletion_history(
            inventory_item_id=test_inventory_item.id,
            session=test_session,
        )
        assert history == []
```

**Files**: `src/tests/test_inventory_adjustment.py`
**Parallel?**: Yes - independent test case

## Test Strategy

Run tests with:
```bash
# All adjustment tests
pytest src/tests/test_inventory_adjustment.py -v

# With coverage
pytest src/tests/test_inventory_adjustment.py -v --cov=src/services/inventory_item_service

# Single test class
pytest src/tests/test_inventory_adjustment.py::TestManualAdjustmentValidation -v
```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Test database pollution | Flaky tests | Use session rollback in fixtures |
| Missing edge cases | Bugs in production | Cover all spec acceptance scenarios |
| Slow tests | Developer friction | Keep tests focused and fast |

## Definition of Done Checklist

- [ ] Test file created with proper fixtures
- [ ] Happy path tests pass (all reasons work)
- [ ] Validation: quantity > current fails
- [ ] Validation: quantity <= 0 fails
- [ ] Validation: notes required for OTHER
- [ ] Cost calculation verified accurate
- [ ] History returns DESC order
- [ ] All tests pass: `pytest src/tests/test_inventory_adjustment.py -v`

## Review Guidance

- Verify all acceptance scenarios from spec.md are covered
- Check test isolation (no shared state)
- Ensure error messages in tests match service implementation

## Activity Log

- 2026-01-07T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-07T16:58:03Z – claude – shell_pid= – lane=doing – Moved to doing
- 2026-01-07T17:10:29Z – claude – shell_pid= – lane=for_review – Moved to for_review
- 2026-01-07T20:28:36Z – claude-reviewer – shell_pid=49789 – lane=done – Code review approved: 23 comprehensive tests pass - covers all validation, cost calculation, history ordering, and audit trail requirements
