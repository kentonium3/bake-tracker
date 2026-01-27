---
work_package_id: "WP01"
subtasks:
  - "T001"
  - "T002"
  - "T003"
  - "T004"
  - "T005"
title: "Service Foundation & Single-Recipe Aggregation"
phase: "Phase 0 - Foundation"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
dependencies: []
history:
  - timestamp: "2026-01-27T20:19:43Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP01 – Service Foundation & Single-Recipe Aggregation

## Implementation Command

```bash
spec-kitty implement WP01
```

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately.
- **You must address all feedback** before your work is complete.

---

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

Create the ingredient aggregation service with:
1. `IngredientTotal` dataclass for structured return values
2. Service file following CLAUDE.md session management pattern
3. Function to scale recipe ingredients by batch count
4. Function to aggregate ingredients for an event (single-recipe case)
5. Unit tests covering single-recipe aggregation

**Success Criteria:**
- [ ] Service file exists at `src/services/ingredient_aggregation_service.py`
- [ ] All public functions accept `session=None` parameter
- [ ] Single recipe with 3 batches correctly triples ingredient quantities
- [ ] Return type is `Dict[Tuple[int, str], IngredientTotal]`
- [ ] All tests pass

## Context & Constraints

**Reference Documents:**
- `CLAUDE.md` - Session management pattern (CRITICAL)
- `kitty-specs/074-ingredient-aggregation/plan.md` - API design
- `kitty-specs/074-ingredient-aggregation/spec.md` - Requirements

**Key Constraints:**
- Pure calculation service - NO database writes
- Follow existing patterns in `src/services/planning_service.py`
- Use existing models: BatchDecision, Recipe, RecipeIngredient, FinishedUnit, Ingredient

**Architecture:**
```
BatchDecision (event_id, finished_unit_id, batches)
    │
    ▼
FinishedUnit → Recipe → RecipeIngredient[]
    │                        │
    │                        ▼
    │             (ingredient_id, quantity, unit)
    │
    ▼
scaled_qty = quantity × batches
    │
    ▼
Dict[(ingredient_id, unit)] → IngredientTotal
```

## Subtasks & Detailed Guidance

### Subtask T001 – Create IngredientTotal Dataclass

**Purpose**: Define the return type for aggregated ingredient data.

**Steps**:
1. Create `src/services/ingredient_aggregation_service.py`
2. Add imports: `from dataclasses import dataclass` and `from typing import Dict, Tuple, List`
3. Define dataclass:

```python
@dataclass
class IngredientTotal:
    """Aggregated ingredient total for shopping list generation."""
    ingredient_id: int
    ingredient_name: str
    unit: str
    total_quantity: float  # Rounded to 3 decimal places
```

**Files**: `src/services/ingredient_aggregation_service.py` (new file)
**Parallel?**: No - must be created first

### Subtask T002 – Create Service File Structure with Session Pattern

**Purpose**: Establish service file following CLAUDE.md session management pattern.

**Steps**:
1. Add module docstring explaining F074 purpose
2. Add required imports:

```python
"""
Ingredient Aggregation Service for F074.

Aggregates recipe ingredients across batch decisions for shopping list generation.
Converts batch decisions (from F073) into total ingredient quantities keyed by
(ingredient_id, unit) tuple.

Session Management Pattern (from CLAUDE.md):
- All public functions accept session=None parameter
- If session provided, use it directly
- If session is None, create a new session via session_scope()
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional

from sqlalchemy.orm import Session

from src.models import BatchDecision, Recipe, Ingredient
from src.services.database import session_scope
from src.services.exceptions import ValidationError
```

3. Add type alias for clarity:
```python
IngredientKey = Tuple[int, str]  # (ingredient_id, unit)
```

**Files**: `src/services/ingredient_aggregation_service.py`
**Parallel?**: No - follows T001

### Subtask T003 – Implement `_scale_recipe_ingredients()` Helper

**Purpose**: Scale a single recipe's ingredients by batch count.

**Steps**:
1. Create internal helper function (not public API):

```python
def _scale_recipe_ingredients(
    recipe: Recipe,
    batches: int,
) -> List[Tuple[int, str, str, float]]:
    """
    Scale a recipe's ingredients by batch count.

    Args:
        recipe: Recipe with recipe_ingredients relationship loaded
        batches: Number of batches to make

    Returns:
        List of (ingredient_id, ingredient_name, unit, scaled_quantity) tuples
    """
    results = []
    for ri in recipe.recipe_ingredients:
        if ri.ingredient is None:
            continue  # Skip orphaned recipe ingredients

        scaled_qty = ri.quantity * batches
        results.append((
            ri.ingredient_id,
            ri.ingredient.name,
            ri.unit,
            scaled_qty,
        ))
    return results
```

**Key Details**:
- Recipe has `recipe_ingredients` relationship (eager loaded)
- RecipeIngredient has `ingredient_id`, `quantity`, `unit`, and `ingredient` relationship
- Handle None ingredient gracefully (data integrity edge case)

**Files**: `src/services/ingredient_aggregation_service.py`
**Parallel?**: No - needed by T004

### Subtask T004 – Implement `aggregate_ingredients_for_event()` Public API

**Purpose**: Main public function following session management pattern.

**Steps**:
1. Create public function with session pattern:

```python
def aggregate_ingredients_for_event(
    event_id: int,
    session: Session = None,
) -> Dict[IngredientKey, IngredientTotal]:
    """
    Aggregate ingredients across all batch decisions for an event.

    Queries BatchDecision records, scales recipe ingredients by batch count,
    and aggregates same (ingredient_id, unit) pairs into totals.

    Args:
        event_id: Event to aggregate for
        session: Optional session for transaction sharing

    Returns:
        Dict keyed by (ingredient_id, unit) with IngredientTotal values

    Raises:
        ValidationError: If event not found
    """
    if session is not None:
        return _aggregate_ingredients_impl(event_id, session)
    with session_scope() as session:
        return _aggregate_ingredients_impl(event_id, session)
```

2. Create implementation function:

```python
def _aggregate_ingredients_impl(
    event_id: int,
    session: Session,
) -> Dict[IngredientKey, IngredientTotal]:
    """Internal implementation of aggregate_ingredients_for_event."""
    from src.models import Event  # Import here to avoid circular

    # Validate event exists
    event = session.query(Event).filter(Event.id == event_id).first()
    if event is None:
        raise ValidationError([f"Event {event_id} not found"])

    # Query batch decisions for this event
    batch_decisions = (
        session.query(BatchDecision)
        .filter(BatchDecision.event_id == event_id)
        .all()
    )

    # Handle empty event
    if not batch_decisions:
        return {}

    # Aggregate ingredients
    totals: Dict[IngredientKey, float] = {}
    names: Dict[int, str] = {}  # ingredient_id -> name cache

    for bd in batch_decisions:
        # Get recipe via FinishedUnit
        fu = bd.finished_unit
        if fu is None or fu.recipe is None:
            continue

        recipe = fu.recipe
        scaled_ingredients = _scale_recipe_ingredients(recipe, bd.batches)

        for ing_id, ing_name, unit, qty in scaled_ingredients:
            key = (ing_id, unit)
            totals[key] = totals.get(key, 0.0) + qty
            names[ing_id] = ing_name

    # Build result with IngredientTotal objects
    result: Dict[IngredientKey, IngredientTotal] = {}
    for (ing_id, unit), total_qty in totals.items():
        result[(ing_id, unit)] = IngredientTotal(
            ingredient_id=ing_id,
            ingredient_name=names[ing_id],
            unit=unit,
            total_quantity=round(total_qty, 3),
        )

    return result
```

**Key Details**:
- BatchDecision has `finished_unit` relationship → FinishedUnit has `recipe` relationship
- Accumulate in plain dict, convert to IngredientTotal at end
- Round to 3 decimals only at final output

**Files**: `src/services/ingredient_aggregation_service.py`
**Parallel?**: No - core implementation

### Subtask T005 – Write Unit Tests for Single-Recipe Aggregation

**Purpose**: Verify single-recipe aggregation works correctly.

**Steps**:
1. Create test file `src/tests/test_ingredient_aggregation_service.py`
2. Import test fixtures and service:

```python
"""Unit tests for ingredient aggregation service (F074)."""

import pytest
from datetime import date

from src.models import (
    Event, Recipe, Ingredient, RecipeIngredient,
    FinishedUnit, BatchDecision,
)
from src.models.finished_unit import YieldMode
from src.services.ingredient_aggregation_service import (
    aggregate_ingredients_for_event,
    IngredientTotal,
)
from src.services.database import session_scope
```

3. Create test fixtures:

```python
@pytest.fixture
def sample_event(session):
    """Create a test event."""
    event = Event(name="Test Event", event_date=date(2026, 1, 1), year=2026)
    session.add(event)
    session.flush()
    return event


@pytest.fixture
def sample_recipe_with_ingredients(session):
    """Create a recipe with 2 ingredients."""
    # Create ingredients
    flour = Ingredient(name="Flour", category="Dry")
    sugar = Ingredient(name="Sugar", category="Dry")
    session.add_all([flour, sugar])
    session.flush()

    # Create recipe
    recipe = Recipe(name="Test Cookies", category="Cookies")
    session.add(recipe)
    session.flush()

    # Add recipe ingredients
    ri_flour = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=flour.id,
        quantity=2.0,
        unit="cups",
    )
    ri_sugar = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=sugar.id,
        quantity=1.0,
        unit="cups",
    )
    session.add_all([ri_flour, ri_sugar])
    session.flush()

    return recipe, flour, sugar


@pytest.fixture
def sample_finished_unit(session, sample_recipe_with_ingredients):
    """Create a FinishedUnit linked to the recipe."""
    recipe, _, _ = sample_recipe_with_ingredients
    fu = FinishedUnit(
        slug="test-cookies",
        display_name="Test Cookies",
        recipe_id=recipe.id,
        yield_mode=YieldMode.DISCRETE_COUNT,
        items_per_batch=24,
        item_unit="cookie",
    )
    session.add(fu)
    session.flush()
    return fu
```

4. Write test cases:

```python
class TestSingleRecipeAggregation:
    """Tests for single-recipe ingredient aggregation."""

    def test_single_recipe_single_batch(
        self, session, sample_event, sample_recipe_with_ingredients, sample_finished_unit
    ):
        """Single batch should return base ingredient quantities."""
        recipe, flour, sugar = sample_recipe_with_ingredients
        fu = sample_finished_unit
        event = sample_event

        # Create batch decision: 1 batch
        bd = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=1,
        )
        session.add(bd)
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)

        assert len(result) == 2
        assert result[(flour.id, "cups")].total_quantity == 2.0
        assert result[(sugar.id, "cups")].total_quantity == 1.0

    def test_single_recipe_multiple_batches(
        self, session, sample_event, sample_recipe_with_ingredients, sample_finished_unit
    ):
        """Multiple batches should multiply ingredient quantities."""
        recipe, flour, sugar = sample_recipe_with_ingredients
        fu = sample_finished_unit
        event = sample_event

        # Create batch decision: 3 batches
        bd = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=3,
        )
        session.add(bd)
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)

        assert len(result) == 2
        assert result[(flour.id, "cups")].total_quantity == 6.0  # 2 × 3
        assert result[(sugar.id, "cups")].total_quantity == 3.0  # 1 × 3

    def test_ingredient_total_dataclass_fields(
        self, session, sample_event, sample_recipe_with_ingredients, sample_finished_unit
    ):
        """IngredientTotal should have all expected fields."""
        recipe, flour, _ = sample_recipe_with_ingredients
        fu = sample_finished_unit
        event = sample_event

        bd = BatchDecision(
            event_id=event.id,
            recipe_id=recipe.id,
            finished_unit_id=fu.id,
            batches=1,
        )
        session.add(bd)
        session.flush()

        result = aggregate_ingredients_for_event(event.id, session=session)
        flour_total = result[(flour.id, "cups")]

        assert flour_total.ingredient_id == flour.id
        assert flour_total.ingredient_name == "Flour"
        assert flour_total.unit == "cups"
        assert flour_total.total_quantity == 2.0

    def test_event_not_found_raises_error(self, session):
        """Non-existent event should raise ValidationError."""
        from src.services.exceptions import ValidationError

        with pytest.raises(ValidationError):
            aggregate_ingredients_for_event(99999, session=session)
```

**Files**: `src/tests/test_ingredient_aggregation_service.py` (new file)
**Parallel?**: No - tests depend on implementation

## Test Strategy

**Run tests with:**
```bash
./run-tests.sh src/tests/test_ingredient_aggregation_service.py -v
```

**Expected results:**
- 4 tests pass for single-recipe scenarios
- Tests use session fixture from conftest.py

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Follow CLAUDE.md pattern strictly - pass session through |
| Model relationships not loaded | Use existing eager loading on Recipe.recipe_ingredients |
| Circular import | Import Event inside function if needed |

## Definition of Done Checklist

- [ ] `src/services/ingredient_aggregation_service.py` created
- [ ] `IngredientTotal` dataclass defined with all fields
- [ ] `aggregate_ingredients_for_event()` accepts `session=None`
- [ ] Single-recipe aggregation works correctly
- [ ] All 4+ unit tests pass
- [ ] Code follows existing service patterns

## Review Guidance

**Key checkpoints:**
1. Session management pattern matches CLAUDE.md exactly
2. IngredientTotal has correct field types (int, str, str, float)
3. Tests cover base case and batch multiplication
4. No database writes in service (read-only)

## Activity Log

- 2026-01-27T20:19:43Z – system – lane=planned – Prompt created.
