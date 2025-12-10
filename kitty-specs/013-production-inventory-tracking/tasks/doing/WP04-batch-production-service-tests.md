---
work_package_id: "WP04"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
  - "T022"
title: "Batch Production Service - Tests"
phase: "Phase 2 - Core Services"
lane: "doing"
assignee: ""
agent: "claude"
shell_pid: "15592"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T17:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 - Batch Production Service - Tests

## Objectives & Success Criteria

Achieve >70% test coverage for BatchProductionService with comprehensive test scenarios covering:
- Happy path for both check_can_produce and record_batch_production
- Edge cases: nested recipes, yield=0, yield exceeds expected
- Error cases: insufficient inventory, recipe not found, mismatch errors

**Success Criteria**:
- [ ] All tests pass
- [ ] Coverage >= 70% for batch_production_service.py
- [ ] Tests verify FIFO consumption called correctly
- [ ] Tests verify inventory_count changes
- [ ] Tests verify rollback on failure

## Context & Constraints

**Reference Documents**:
- `kitty-specs/013-production-inventory-tracking/spec.md` - Acceptance scenarios
- `kitty-specs/013-production-inventory-tracking/quickstart.md` - Test patterns
- `src/tests/` - Existing test patterns to follow

**Test Requirements from spec.md**:
1. Sufficient inventory -> can_produce=True
2. Insufficient inventory -> can_produce=False with missing details
3. Nested recipe -> aggregated ingredients checked
4. Record production -> FIFO consumption + inventory increment + ledger created
5. Failed batch (yield=0) -> allowed, ingredients still consumed
6. Yield exceeds expected -> allowed, variance tracked
7. Insufficient inventory during record -> rollback, no partial state

## Subtasks & Detailed Guidance

### Subtask T014 - Create test file structure
- **Purpose**: Set up test file with fixtures and imports
- **File**: `src/tests/test_batch_production_service.py`
- **Parallel?**: No (prerequisite for other test subtasks)

**Steps**:
1. Create test file with imports:
   ```python
   import pytest
   from decimal import Decimal
   from datetime import datetime

   from src.models import (
       Recipe, RecipeIngredient, Ingredient, Product, InventoryItem,
       FinishedUnit, ProductionRun, ProductionConsumption
   )
   from src.services import batch_production_service
   from src.services.batch_production_service import (
       RecipeNotFoundError, FinishedUnitNotFoundError,
       FinishedUnitRecipeMismatchError, InsufficientInventoryError
   )
   from src.services.database import session_scope
   ```

2. Create base fixtures:
   ```python
   @pytest.fixture
   def db_session():
       """Provide clean database session for each test."""
       # Use existing test database setup pattern
       pass

   @pytest.fixture
   def ingredient_flour(db_session):
       """Create flour ingredient."""
       ingredient = Ingredient(name="All-Purpose Flour", slug="flour", recipe_unit="cups")
       db_session.add(ingredient)
       db_session.commit()
       return ingredient

   @pytest.fixture
   def product_flour(db_session, ingredient_flour):
       """Create flour product."""
       product = Product(name="Gold Medal Flour", ingredient=ingredient_flour, ...)
       db_session.add(product)
       db_session.commit()
       return product

   @pytest.fixture
   def inventory_flour(db_session, product_flour):
       """Create flour inventory with 10 cups."""
       inv = InventoryItem(product=product_flour, quantity=Decimal("10.0"), ...)
       db_session.add(inv)
       db_session.commit()
       return inv

   @pytest.fixture
   def recipe_cookies(db_session, ingredient_flour):
       """Create simple cookie recipe requiring 2 cups flour per batch."""
       recipe = Recipe(name="Chocolate Chip Cookies", ...)
       db_session.add(recipe)
       # Add recipe ingredient
       ri = RecipeIngredient(recipe=recipe, ingredient=ingredient_flour, quantity=Decimal("2.0"), unit="cups")
       db_session.add(ri)
       db_session.commit()
       return recipe

   @pytest.fixture
   def finished_unit_cookies(db_session, recipe_cookies):
       """Create FinishedUnit for cookies (48 per batch)."""
       fu = FinishedUnit(
           recipe=recipe_cookies,
           display_name="Chocolate Chip Cookie",
           items_per_batch=48,
           inventory_count=0,
           ...
       )
       db_session.add(fu)
       db_session.commit()
       return fu
   ```

### Subtask T015 - Test check_can_produce - sufficient inventory
- **Purpose**: Verify availability check returns true when inventory is sufficient
- **Parallel?**: Yes

**Test**:
```python
def test_check_can_produce_sufficient_inventory(recipe_cookies, inventory_flour):
    """Given sufficient inventory, check_can_produce returns can_produce=True."""
    result = batch_production_service.check_can_produce(
        recipe_id=recipe_cookies.id,
        num_batches=2  # Needs 4 cups, have 10
    )
    assert result["can_produce"] is True
    assert result["missing"] == []
```

### Subtask T016 - Test check_can_produce - insufficient inventory
- **Purpose**: Verify availability check returns details of missing ingredients
- **Parallel?**: Yes

**Test**:
```python
def test_check_can_produce_insufficient_inventory(recipe_cookies, inventory_flour):
    """Given insufficient inventory, check_can_produce returns missing details."""
    result = batch_production_service.check_can_produce(
        recipe_id=recipe_cookies.id,
        num_batches=10  # Needs 20 cups, have 10
    )
    assert result["can_produce"] is False
    assert len(result["missing"]) == 1
    assert result["missing"][0]["ingredient_slug"] == "flour"
    assert result["missing"][0]["needed"] == Decimal("20.0")
    assert result["missing"][0]["available"] == Decimal("10.0")
```

### Subtask T017 - Test check_can_produce - nested recipe
- **Purpose**: Verify nested recipe ingredients are aggregated correctly
- **Parallel?**: Yes

**Additional Fixtures Needed**:
- Create parent recipe with sub-recipe component
- Verify get_aggregated_ingredients is used

### Subtask T018 - Test record_batch_production - happy path
- **Purpose**: Verify full production recording flow
- **Parallel?**: Yes

**Test**:
```python
def test_record_batch_production_happy_path(recipe_cookies, finished_unit_cookies, inventory_flour):
    """Record production: FIFO consumed, inventory incremented, records created."""
    initial_inventory = inventory_flour.quantity
    initial_fu_count = finished_unit_cookies.inventory_count

    result = batch_production_service.record_batch_production(
        recipe_id=recipe_cookies.id,
        finished_unit_id=finished_unit_cookies.id,
        num_batches=2,
        actual_yield=92,
        notes="Test batch"
    )

    # Verify result
    assert result["production_run_id"] is not None
    assert result["actual_yield"] == 92
    assert result["total_ingredient_cost"] > Decimal("0")

    # Verify FinishedUnit inventory incremented
    with session_scope() as session:
        fu = session.get(FinishedUnit, finished_unit_cookies.id)
        assert fu.inventory_count == initial_fu_count + 92

    # Verify ProductionRun created
    with session_scope() as session:
        pr = session.get(ProductionRun, result["production_run_id"])
        assert pr.recipe_id == recipe_cookies.id
        assert pr.actual_yield == 92

    # Verify ProductionConsumption created
    with session_scope() as session:
        consumptions = session.query(ProductionConsumption).filter_by(
            production_run_id=result["production_run_id"]
        ).all()
        assert len(consumptions) == 1  # One ingredient
        assert consumptions[0].ingredient_slug == "flour"
```

### Subtask T019 - Test record_batch_production - actual_yield = 0
- **Purpose**: Verify failed batch is allowed (ingredients consumed, yield=0)
- **Parallel?**: Yes

**Test**:
```python
def test_record_batch_production_zero_yield(recipe_cookies, finished_unit_cookies, inventory_flour):
    """Failed batch: actual_yield=0 allowed, ingredients still consumed."""
    result = batch_production_service.record_batch_production(
        recipe_id=recipe_cookies.id,
        finished_unit_id=finished_unit_cookies.id,
        num_batches=1,
        actual_yield=0,
        notes="Burned batch"
    )

    assert result["actual_yield"] == 0
    assert result["per_unit_cost"] == Decimal("0.0000")  # No division by zero

    # Ingredients still consumed
    with session_scope() as session:
        consumptions = session.query(ProductionConsumption).filter_by(
            production_run_id=result["production_run_id"]
        ).all()
        assert len(consumptions) == 1
```

### Subtask T020 - Test record_batch_production - yield exceeds expected
- **Purpose**: Verify yield variance is tracked when actual > expected
- **Parallel?**: Yes

**Test**:
```python
def test_record_batch_production_yield_exceeds_expected(recipe_cookies, finished_unit_cookies, inventory_flour):
    """Yield exceeds expected: allowed and tracked."""
    result = batch_production_service.record_batch_production(
        recipe_id=recipe_cookies.id,
        finished_unit_id=finished_unit_cookies.id,
        num_batches=1,
        actual_yield=60  # Expected 48
    )

    assert result["actual_yield"] == 60
    # Variance would be expected_yield - actual_yield = -12
```

### Subtask T021 - Test record_batch_production - insufficient inventory rollback
- **Purpose**: Verify no partial state on failure
- **Parallel?**: Yes

**Test**:
```python
def test_record_batch_production_rollback_on_insufficient(recipe_cookies, finished_unit_cookies, inventory_flour):
    """Insufficient inventory: entire operation rolls back."""
    initial_fu_count = finished_unit_cookies.inventory_count

    with pytest.raises(InsufficientInventoryError):
        batch_production_service.record_batch_production(
            recipe_id=recipe_cookies.id,
            finished_unit_id=finished_unit_cookies.id,
            num_batches=100,  # Way more than available
            actual_yield=4800
        )

    # Verify no state changed
    with session_scope() as session:
        fu = session.get(FinishedUnit, finished_unit_cookies.id)
        assert fu.inventory_count == initial_fu_count

        # No ProductionRun created
        runs = session.query(ProductionRun).filter_by(recipe_id=recipe_cookies.id).all()
        assert len(runs) == 0
```

### Subtask T022 - Test record_batch_production - FinishedUnit-Recipe mismatch
- **Purpose**: Verify validation that FinishedUnit belongs to Recipe
- **Parallel?**: Yes

**Test**:
```python
def test_record_batch_production_mismatch_error(recipe_cookies, inventory_flour, db_session):
    """FinishedUnit from different recipe raises error."""
    # Create different recipe and its FinishedUnit
    other_recipe = Recipe(name="Sugar Cookies", ...)
    db_session.add(other_recipe)
    other_fu = FinishedUnit(recipe=other_recipe, display_name="Sugar Cookie", ...)
    db_session.add(other_fu)
    db_session.commit()

    with pytest.raises(FinishedUnitRecipeMismatchError):
        batch_production_service.record_batch_production(
            recipe_id=recipe_cookies.id,
            finished_unit_id=other_fu.id,  # Wrong recipe!
            num_batches=1,
            actual_yield=48
        )
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Shared state between tests | Use fresh DB session per test with proper teardown |
| Fixture complexity | Build fixtures incrementally, document dependencies |
| Mock vs real FIFO | Use real consume_fifo to ensure integration works |

## Definition of Done Checklist

- [ ] T014: Test file structure created with base fixtures
- [ ] T015-T022: All test scenarios implemented
- [ ] All tests pass: `pytest src/tests/test_batch_production_service.py -v`
- [ ] Coverage check: `pytest src/tests/test_batch_production_service.py --cov=src/services/batch_production_service`
- [ ] Coverage >= 70%
- [ ] `tasks.md` updated with status change

## Review Guidance

**Reviewer Checklist**:
- [ ] Each acceptance scenario from spec.md has a corresponding test
- [ ] Tests verify both function return values AND database state
- [ ] Rollback tests confirm no partial state
- [ ] Fixtures are well-documented and reusable

## Activity Log

- 2025-12-09T17:30:00Z - system - lane=planned - Prompt created.
- 2025-12-10T03:48:19Z – claude – shell_pid=15592 – lane=doing – Implementation complete - 26 tests for batch_production_service
