# Quickstart: Production & Inventory Tracking

**Feature**: 013-production-inventory-tracking
**Date**: 2025-12-09

## Quick Reference

### New Files to Create

| File | Purpose |
|------|---------|
| `src/models/production_run.py` | ProductionRun model |
| `src/models/production_consumption.py` | ProductionConsumption ledger model |
| `src/models/assembly_run.py` | AssemblyRun model |
| `src/models/assembly_finished_unit_consumption.py` | FinishedUnit consumption ledger |
| `src/models/assembly_packaging_consumption.py` | Packaging consumption ledger |
| `src/services/batch_production_service.py` | Batch production business logic |
| `src/services/assembly_service.py` | Assembly business logic |
| `src/tests/test_batch_production_service.py` | Unit tests for batch production |
| `src/tests/test_assembly_service.py` | Unit tests for assembly |

### Files to Modify

| File | Change |
|------|--------|
| `src/models/__init__.py` | Export new models |
| `src/services/__init__.py` | Export new services |

---

## Model Patterns

All models inherit from `BaseModel` which provides:
- `id` (Integer primary key)
- `uuid` (String(36) unique identifier)
- `created_at`, `updated_at` (DateTime)
- `to_dict()` method

### Example Model Structure

```python
"""ProductionRun model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Column, Integer, Numeric, Text, DateTime, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import relationship

from .base import BaseModel


class ProductionRun(BaseModel):
    __tablename__ = "production_runs"

    # Foreign keys
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="RESTRICT"), nullable=False)
    finished_unit_id = Column(Integer, ForeignKey("finished_units.id", ondelete="RESTRICT"), nullable=False)

    # Production data
    num_batches = Column(Integer, nullable=False)
    expected_yield = Column(Integer, nullable=False)
    actual_yield = Column(Integer, nullable=False)
    produced_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)

    # Cost tracking
    total_ingredient_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))
    per_unit_cost = Column(Numeric(10, 4), nullable=False, default=Decimal("0.0000"))

    # Relationships
    recipe = relationship("Recipe", back_populates="production_runs")
    finished_unit = relationship("FinishedUnit")
    consumptions = relationship("ProductionConsumption", back_populates="production_run", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_production_run_recipe", "recipe_id"),
        Index("idx_production_run_finished_unit", "finished_unit_id"),
        Index("idx_production_run_produced_at", "produced_at"),
        CheckConstraint("num_batches > 0", name="ck_production_run_batches_positive"),
        CheckConstraint("expected_yield >= 0", name="ck_production_run_expected_non_negative"),
        CheckConstraint("actual_yield >= 0", name="ck_production_run_actual_non_negative"),
        CheckConstraint("total_ingredient_cost >= 0", name="ck_production_run_cost_non_negative"),
    )
```

---

## Service Patterns

### Using session_scope

```python
from src.services.database import session_scope

def record_batch_production(...) -> ProductionResult:
    with session_scope() as session:
        # All operations atomic within this block
        # Automatic commit on success, rollback on exception
        pass
```

### Calling consume_fifo

```python
from src.services import inventory_item_service

# Availability check (dry run)
result = inventory_item_service.consume_fifo(
    ingredient_slug="flour",
    quantity_needed=Decimal("4.0"),
    dry_run=True
)
# Returns: {consumed, breakdown, shortfall, satisfied, total_cost}

# Actual consumption
result = inventory_item_service.consume_fifo(
    ingredient_slug="flour",
    quantity_needed=Decimal("4.0"),
    dry_run=False  # Actually deducts inventory
)
```

### Getting aggregated ingredients

```python
from src.services.recipe_service import get_aggregated_ingredients

# Returns flattened ingredients from all nesting levels
ingredients = get_aggregated_ingredients(recipe_id)
# Returns: List[{ingredient_slug, quantity, unit}]
```

---

## Test Patterns

### Fixture Setup

```python
import pytest
from decimal import Decimal
from src.models import Recipe, FinishedUnit, Ingredient, Product, InventoryItem
from src.services.database import session_scope


@pytest.fixture
def recipe_with_inventory(db_session):
    """Create recipe with ingredients in inventory."""
    # Create ingredient
    ingredient = Ingredient(name="Flour", slug="flour", recipe_unit="cups")
    db_session.add(ingredient)

    # Create product for inventory
    product = Product(name="Gold Medal Flour", ingredient=ingredient, ...)
    db_session.add(product)

    # Create inventory item
    inv = InventoryItem(product=product, quantity=Decimal("10.0"), ...)
    db_session.add(inv)

    # Create recipe with ingredient
    recipe = Recipe(name="Cookies", ...)
    db_session.add(recipe)

    # Create finished unit
    fu = FinishedUnit(recipe=recipe, display_name="Cookie", inventory_count=0, ...)
    db_session.add(fu)

    db_session.commit()
    return recipe, fu
```

### Testing Atomic Operations

```python
def test_production_rolls_back_on_failure(recipe_with_inventory):
    recipe, fu = recipe_with_inventory

    # Get initial inventory state
    initial_count = fu.inventory_count

    # Try production with insufficient ingredients
    with pytest.raises(InsufficientInventoryError):
        batch_production_service.record_batch_production(
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            num_batches=1000,  # Way too many
            actual_yield=48000
        )

    # Verify nothing changed
    with session_scope() as session:
        fu_after = session.get(FinishedUnit, fu.id)
        assert fu_after.inventory_count == initial_count
```

---

## Acceptance Criteria Quick Check

### Batch Production (P1)
- [ ] `check_can_produce()` returns accurate availability
- [ ] `record_batch_production()` deducts ingredients via FIFO
- [ ] `record_batch_production()` increments FinishedUnit.inventory_count
- [ ] ProductionRun and ProductionConsumption records created
- [ ] Per-unit cost = total_cost / actual_yield
- [ ] Nested recipes handled via get_aggregated_ingredients()
- [ ] Insufficient inventory returns clear error with details

### Assembly (P2)
- [ ] `check_can_assemble()` returns accurate availability
- [ ] `record_assembly()` decrements FinishedUnit.inventory_count
- [ ] `record_assembly()` deducts packaging via FIFO
- [ ] `record_assembly()` increments FinishedGood.inventory_count
- [ ] AssemblyRun and consumption records created
- [ ] Nested FinishedGood assemblies handled

### History (P3)
- [ ] Production history queryable with filters
- [ ] Assembly history queryable with filters
- [ ] Full audit trail with consumption details

---

## Common Pitfalls

1. **Forgetting to use session parameter**: When nesting service calls, pass the session to maintain transaction boundary

2. **Decimal precision**: Use `Decimal` for all quantities and costs, not `float`

3. **Unit conversion**: Always use `convert_any_units()` from unit_converter when units don't match

4. **Yield mode handling**: FinishedUnit has `yield_mode` - handle both DISCRETE_COUNT and BATCH_PORTION

5. **Transaction isolation**: All mutations must be in single transaction - don't commit intermediate states
