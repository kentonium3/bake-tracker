---
work_package_id: "WP02"
subtasks:
  - "T007"
  - "T008"
  - "T009"
  - "T010"
title: "Core Production Recording Service"
phase: "Phase 2 - Service Layer"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-04T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Core Production Recording Service

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

- Implement `record_production()` - the core function that records batches and consumes pantry via FIFO
- Capture actual ingredient costs at time of production (not estimates)
- Create custom exceptions for production errors
- Achieve >70% test coverage for this service function
- This is the **MVP milestone** - production recording is the core feature

## Context & Constraints

**Reference Documents**:
- Constitution: `.kittify/memory/constitution.md` (Principle III: FIFO Accuracy, Principle V: TDD)
- Service Contract: `kitty-specs/008-production-tracking/contracts/production_service.md`
- Research: `kitty-specs/008-production-tracking/research.md`
- Quickstart: `kitty-specs/008-production-tracking/quickstart.md`

**Key Dependencies**:
- `pantry_service.consume_fifo(slug, qty, dry_run=False)` at `src/services/pantry_service.py:226`
- `event_service.get_recipe_needs(event_id)` at `src/services/event_service.py:777`
- Existing Recipe model and RecipeIngredient relationships

**Architecture Constraints**:
- Service layer must NOT import UI components
- Follow existing service pattern: module-level functions with `session_scope()`
- All business logic in service layer, not models

---

## Subtasks & Detailed Guidance

### Subtask T007 - Create Custom Exceptions

**Purpose**: Define clear exception types for production errors.

**Steps**:
1. Create new file `src/services/production_service.py`
2. Add module docstring
3. Define exceptions:

```python
"""
Production Service - Business logic for production tracking.

This service provides:
- Recording recipe production with FIFO inventory consumption
- Package status management
- Production progress tracking and dashboard data
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import joinedload
from sqlalchemy import func

from src.models import (
    ProductionRecord,
    Event,
    EventRecipientPackage,
    Recipe,
    RecipeIngredient,
    PackageStatus,
)
from src.services.database import session_scope
from src.services.exceptions import DatabaseError, ValidationError
from src.services import pantry_service, event_service


class InsufficientInventoryError(Exception):
    """Raised when pantry doesn't have enough ingredients."""
    def __init__(self, ingredient_slug: str, needed: Decimal, available: Decimal):
        self.ingredient_slug = ingredient_slug
        self.needed = needed
        self.available = available
        super().__init__(
            f"Insufficient inventory for {ingredient_slug}: need {needed}, have {available}"
        )


class ProductionExceedsPlannedError(Exception):
    """Warning when production would exceed planned batches."""
    def __init__(self, recipe_id: int, planned: int, would_produce: int):
        self.recipe_id = recipe_id
        self.planned = planned
        self.would_produce = would_produce
        super().__init__(
            f"Production would exceed planned: {would_produce} vs {planned} planned"
        )
```

**Files**: `src/services/production_service.py` (NEW)

---

### Subtask T008 - Implement record_production()

**Purpose**: Core function to record production, consume inventory, capture costs.

**Steps**:
1. Add function signature per service contract
2. Implement validation (event exists, recipe exists, batches > 0)
3. Check for over-production (warn but continue)
4. For each ingredient in recipe:
   - Calculate quantity needed (ingredient qty * batches)
   - Call `pantry_service.consume_fifo()` with `dry_run=False`
   - Accumulate actual cost
   - If insufficient inventory, raise InsufficientInventoryError
5. Create ProductionRecord with actual_cost
6. Commit and return record

**Algorithm**:
```python
def record_production(
    event_id: int,
    recipe_id: int,
    batches: int,
    notes: Optional[str] = None
) -> ProductionRecord:
    """
    Record batches of a recipe as produced for an event.

    Consumes pantry inventory via FIFO and captures actual costs.

    Args:
        event_id: Event to record production for
        recipe_id: Recipe that was produced
        batches: Number of batches produced (must be > 0)
        notes: Optional production notes

    Returns:
        ProductionRecord with actual FIFO cost

    Raises:
        ValidationError: If batches <= 0
        EventNotFoundError: If event doesn't exist
        RecipeNotFoundError: If recipe doesn't exist
        InsufficientInventoryError: If pantry lacks ingredients
    """
    # Validation
    if batches <= 0:
        raise ValidationError(["Batches must be greater than 0"])

    try:
        with session_scope() as session:
            # Verify event exists
            event = session.query(Event).filter(Event.id == event_id).first()
            if not event:
                raise EventNotFoundError(event_id)

            # Verify recipe exists and load ingredients
            recipe = (
                session.query(Recipe)
                .options(joinedload(Recipe.recipe_ingredients).joinedload(RecipeIngredient.ingredient))
                .filter(Recipe.id == recipe_id)
                .first()
            )
            if not recipe:
                raise RecipeNotFoundError(recipe_id)

            # Calculate and consume ingredients
            total_actual_cost = Decimal("0.0000")

            for ri in recipe.recipe_ingredients:
                if not ri.ingredient:
                    continue

                # Calculate quantity for N batches
                qty_needed = Decimal(str(ri.quantity)) * Decimal(str(batches))

                # Consume via FIFO (actual consumption, not dry run)
                result = pantry_service.consume_fifo(
                    ingredient_slug=ri.ingredient.slug,
                    quantity_needed=qty_needed,
                    dry_run=False
                )

                if not result["satisfied"]:
                    raise InsufficientInventoryError(
                        ingredient_slug=ri.ingredient.slug,
                        needed=qty_needed,
                        available=result["consumed"]
                    )

                total_actual_cost += result["total_cost"]

            # Create production record
            record = ProductionRecord(
                event_id=event_id,
                recipe_id=recipe_id,
                batches=batches,
                actual_cost=total_actual_cost,
                produced_at=datetime.utcnow(),
                notes=notes
            )
            session.add(record)
            session.flush()

            # Reload to ensure all fields populated
            session.refresh(record)
            return record

    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to record production: {str(e)}")
```

**Files**: `src/services/production_service.py` (ADD to existing)

**Critical Notes**:
- `dry_run=False` is essential - this actually consumes inventory
- Sum `total_cost` from each consume_fifo result
- Transaction ensures all-or-nothing: if any ingredient fails, nothing is consumed

---

### Subtask T009 - Write Tests for record_production()

**Purpose**: TDD tests ensuring FIFO accuracy and cost capture.

**Steps**:
1. Create `src/tests/services/test_production_service.py`
2. Write test cases:

```python
"""Tests for production_service module."""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from src.services import production_service
from src.services.production_service import (
    record_production,
    InsufficientInventoryError,
)
from src.services.exceptions import ValidationError


class TestRecordProduction:
    """Tests for record_production() function."""

    def test_record_production_success(self, test_db):
        """Test: Recording production consumes inventory and captures cost."""
        # Setup: Create event, recipe with ingredients, pantry items
        # ... fixture setup ...

        # Act
        record = record_production(
            event_id=event.id,
            recipe_id=recipe.id,
            batches=2,
            notes="Test production"
        )

        # Assert
        assert record.batches == 2
        assert record.actual_cost > Decimal("0")
        assert record.event_id == event.id
        assert record.recipe_id == recipe.id

    def test_record_production_invalid_batches(self, test_db):
        """Test: Zero or negative batches raises ValidationError."""
        with pytest.raises(ValidationError):
            record_production(event_id=1, recipe_id=1, batches=0)

        with pytest.raises(ValidationError):
            record_production(event_id=1, recipe_id=1, batches=-1)

    def test_record_production_insufficient_inventory(self, test_db):
        """Test: Insufficient pantry raises InsufficientInventoryError."""
        # Setup: Recipe needs 10 cups flour, pantry has 1 cup
        # ...

        with pytest.raises(InsufficientInventoryError) as exc_info:
            record_production(event_id=event.id, recipe_id=recipe.id, batches=5)

        assert "flour" in exc_info.value.ingredient_slug

    def test_record_production_fifo_cost_accuracy(self, test_db):
        """Test: Actual cost matches FIFO consumption (not estimates)."""
        # Setup: Two flour lots at different prices
        # Lot 1: $2/lb (older)
        # Lot 2: $3/lb (newer)
        # Recipe needs 1 lb flour
        # ...

        record = record_production(event_id=event.id, recipe_id=recipe.id, batches=1)

        # Should use older $2/lb lot first (FIFO)
        assert record.actual_cost == Decimal("2.00")

    def test_record_production_event_not_found(self, test_db):
        """Test: Non-existent event raises error."""
        # ... test implementation

    def test_record_production_recipe_not_found(self, test_db):
        """Test: Non-existent recipe raises error."""
        # ... test implementation
```

**Files**: `src/tests/services/test_production_service.py` (NEW)

**Test Coverage Goals**:
- Happy path with actual cost capture
- Validation errors (batches <= 0)
- Event/recipe not found
- Insufficient inventory
- FIFO accuracy verification

---

### Subtask T010 - Export production_service

**Purpose**: Make service importable from `src.services`.

**Steps**:
1. Open `src/services/__init__.py`
2. Add import: `from . import production_service`
3. Or add specific functions to exports

**Files**: `src/services/__init__.py` (MODIFY)

---

## Test Strategy

Run tests with:
```bash
pytest src/tests/services/test_production_service.py -v
pytest src/tests/services/test_production_service.py -v --cov=src/services/production_service
```

**Required Coverage**: >70% on `production_service.py`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| FIFO consumption is destructive | Transaction rollback on any error |
| Ingredient relationship loading | Use joinedload for eager loading |
| Decimal precision loss | Use Decimal throughout, not float |

---

## Definition of Done Checklist

- [ ] Custom exceptions defined (InsufficientInventoryError, etc.)
- [ ] record_production() implemented per contract specification
- [ ] FIFO consumption uses dry_run=False (actual consumption)
- [ ] Actual cost captured from FIFO results (not estimates)
- [ ] Tests written and passing (>70% coverage)
- [ ] Service exported from __init__.py
- [ ] Manual test: record production, verify pantry depleted
- [ ] `tasks.md` updated with completion status

---

## Review Guidance

- Verify `dry_run=False` in consume_fifo calls
- Verify actual_cost comes from FIFO result, not recipe estimate
- Verify transaction rolls back if any ingredient consumption fails
- Check test coverage meets 70% threshold

---

## Activity Log

- 2025-12-04T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
