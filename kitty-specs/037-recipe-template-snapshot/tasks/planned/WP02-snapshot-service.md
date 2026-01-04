---
work_package_id: "WP02"
subtasks:
  - "T006"
  - "T007"
  - "T008"
  - "T009"
title: "Snapshot Service"
phase: "Phase 1 - Core Snapshot System"
lane: "planned"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-03T06:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 - Snapshot Service

## Objectives & Success Criteria

Create the recipe snapshot service with CRUD operations following session management patterns.

**Success Criteria**:
- `create_recipe_snapshot()` denormalizes recipe data to JSON
- `get_recipe_snapshots()` returns history for a recipe
- `get_snapshot_by_production_run()` retrieves snapshot by production run
- No update methods (immutability enforced by design)
- All functions follow session=None pattern from CLAUDE.md
- Unit tests pass with >70% coverage

## Context & Constraints

**Key References**:
- `CLAUDE.md` - Session management patterns (CRITICAL)
- `kitty-specs/037-recipe-template-snapshot/research.md` - Service patterns
- `src/services/recipe_service.py` - Reference for session=None pattern

**Session Management Pattern** (from CLAUDE.md):
```python
def service_function(param, session=None):
    if session is not None:
        return _service_function_impl(param, session)
    with session_scope() as session:
        return _service_function_impl(param, session)
```

**Constraints**:
- NO update methods - snapshots are immutable
- Must handle nested session calls correctly
- JSON serialization must capture complete recipe state

## Subtasks & Detailed Guidance

### Subtask T006 - Create Snapshot Service with create_recipe_snapshot()

**Purpose**: Core function to capture recipe state at production time.

**File**: `src/services/recipe_snapshot_service.py`

**Steps**:
1. Create new service file with standard imports
2. Implement `create_recipe_snapshot(recipe_id, scale_factor, production_run_id, session=None)`
3. Denormalize recipe data to JSON:
   - recipe_data: name, category, source, yield_quantity, yield_unit, yield_description, estimated_time_minutes, notes, variant_name
   - ingredients_data: array of {ingredient_id, ingredient_name, ingredient_slug, quantity, unit, notes}
4. Create RecipeSnapshot record
5. Return snapshot dict

**Implementation**:
```python
"""
Recipe Snapshot Service for F037 Template & Snapshot System.

Provides immutable snapshot creation and retrieval. NO UPDATE METHODS.
"""

import json
from decimal import Decimal
from contextlib import nullcontext

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from src.models import Recipe, RecipeSnapshot, RecipeIngredient
from src.utils.db import session_scope
from src.utils.datetime_utils import utc_now


class SnapshotCreationError(Exception):
    """Raised when snapshot creation fails."""
    pass


def create_recipe_snapshot(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session: Session = None
) -> dict:
    """
    Create an immutable snapshot of recipe state at production time.

    Args:
        recipe_id: Source recipe ID
        scale_factor: Size multiplier for this production (default 1.0)
        production_run_id: The production run this snapshot is for (1:1)
        session: Optional SQLAlchemy session for transaction sharing

    Returns:
        dict with snapshot data including id

    Raises:
        SnapshotCreationError: If recipe not found or creation fails
    """
    if session is not None:
        return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)

    try:
        with session_scope() as session:
            return _create_recipe_snapshot_impl(recipe_id, scale_factor, production_run_id, session)
    except SQLAlchemyError as e:
        raise SnapshotCreationError(f"Database error creating snapshot: {e}")


def _create_recipe_snapshot_impl(
    recipe_id: int,
    scale_factor: float,
    production_run_id: int,
    session: Session
) -> dict:
    """Internal implementation of snapshot creation."""
    # Load recipe with relationships
    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        raise SnapshotCreationError(f"Recipe {recipe_id} not found")

    # Eagerly load ingredients
    _ = recipe.recipe_ingredients
    for ri in recipe.recipe_ingredients:
        _ = ri.ingredient

    # Build recipe_data JSON
    recipe_data = {
        "name": recipe.name,
        "category": recipe.category,
        "source": recipe.source,
        "yield_quantity": recipe.yield_quantity,
        "yield_unit": recipe.yield_unit,
        "yield_description": recipe.yield_description,
        "estimated_time_minutes": recipe.estimated_time_minutes,
        "notes": recipe.notes,
        "variant_name": recipe.variant_name,
    }

    # Build ingredients_data JSON
    ingredients_data = []
    for ri in recipe.recipe_ingredients:
        ing_data = {
            "ingredient_id": ri.ingredient_id,
            "ingredient_name": ri.ingredient.display_name if ri.ingredient else "Unknown",
            "ingredient_slug": ri.ingredient.slug if ri.ingredient else "",
            "quantity": float(ri.quantity),
            "unit": ri.unit,
            "notes": ri.notes,
        }
        ingredients_data.append(ing_data)

    # Create snapshot
    snapshot = RecipeSnapshot(
        recipe_id=recipe_id,
        production_run_id=production_run_id,
        scale_factor=scale_factor,
        snapshot_date=utc_now(),
        recipe_data=json.dumps(recipe_data),
        ingredients_data=json.dumps(ingredients_data),
        is_backfilled=False
    )

    session.add(snapshot)
    session.flush()  # Get ID without committing

    return {
        "id": snapshot.id,
        "recipe_id": snapshot.recipe_id,
        "production_run_id": snapshot.production_run_id,
        "scale_factor": snapshot.scale_factor,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "recipe_data": recipe_data,
        "ingredients_data": ingredients_data,
        "is_backfilled": snapshot.is_backfilled
    }
```

---

### Subtask T007 - Add get_recipe_snapshots()

**Purpose**: Retrieve snapshot history for a recipe.

**Steps**:
1. Query all snapshots for recipe_id
2. Order by snapshot_date DESC (newest first)
3. Return list of snapshot dicts

**Implementation**:
```python
def get_recipe_snapshots(recipe_id: int, session: Session = None) -> list:
    """
    Get all snapshots for a recipe, ordered by date (newest first).

    Args:
        recipe_id: Recipe to get history for
        session: Optional session

    Returns:
        List of snapshot dicts
    """
    if session is not None:
        return _get_recipe_snapshots_impl(recipe_id, session)

    with session_scope() as session:
        return _get_recipe_snapshots_impl(recipe_id, session)


def _get_recipe_snapshots_impl(recipe_id: int, session: Session) -> list:
    snapshots = (
        session.query(RecipeSnapshot)
        .filter_by(recipe_id=recipe_id)
        .order_by(RecipeSnapshot.snapshot_date.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "recipe_id": s.recipe_id,
            "production_run_id": s.production_run_id,
            "scale_factor": s.scale_factor,
            "snapshot_date": s.snapshot_date.isoformat(),
            "recipe_data": s.get_recipe_data(),
            "ingredients_data": s.get_ingredients_data(),
            "is_backfilled": s.is_backfilled
        }
        for s in snapshots
    ]
```

---

### Subtask T008 - Add get_snapshot_by_production_run()

**Purpose**: Retrieve snapshot linked to a specific production run.

**Implementation**:
```python
def get_snapshot_by_production_run(production_run_id: int, session: Session = None) -> dict | None:
    """
    Get the snapshot associated with a production run.

    Args:
        production_run_id: Production run ID
        session: Optional session

    Returns:
        Snapshot dict or None if not found
    """
    if session is not None:
        return _get_snapshot_by_production_run_impl(production_run_id, session)

    with session_scope() as session:
        return _get_snapshot_by_production_run_impl(production_run_id, session)


def _get_snapshot_by_production_run_impl(production_run_id: int, session: Session) -> dict | None:
    snapshot = (
        session.query(RecipeSnapshot)
        .filter_by(production_run_id=production_run_id)
        .first()
    )

    if not snapshot:
        return None

    return {
        "id": snapshot.id,
        "recipe_id": snapshot.recipe_id,
        "production_run_id": snapshot.production_run_id,
        "scale_factor": snapshot.scale_factor,
        "snapshot_date": snapshot.snapshot_date.isoformat(),
        "recipe_data": snapshot.get_recipe_data(),
        "ingredients_data": snapshot.get_ingredients_data(),
        "is_backfilled": snapshot.is_backfilled
    }
```

---

### Subtask T009 - Create Unit Tests

**Purpose**: Verify service functions work correctly.

**File**: `src/tests/services/test_recipe_snapshot_service.py`

**Tests to Write**:
1. `test_create_snapshot_success` - Basic creation with valid recipe
2. `test_create_snapshot_recipe_not_found` - Error handling
3. `test_create_snapshot_denormalizes_data` - Verify JSON contains expected fields
4. `test_get_recipe_snapshots_empty` - No snapshots returns empty list
5. `test_get_recipe_snapshots_ordered` - Multiple snapshots ordered by date DESC
6. `test_get_snapshot_by_production_run_found` - Returns correct snapshot
7. `test_get_snapshot_by_production_run_not_found` - Returns None
8. `test_snapshot_session_parameter` - Verify session is passed correctly

## Test Strategy

- Run: `pytest src/tests/services/test_recipe_snapshot_service.py -v`
- Use test fixtures from existing recipe/production tests
- Mock session_scope for session parameter tests

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Session detachment | Strict adherence to session=None pattern |
| JSON serialization errors | Validate all fields before json.dumps |
| Missing ingredient data | Handle None values gracefully |

## Definition of Done Checklist

- [ ] create_recipe_snapshot() implemented with session=None pattern
- [ ] get_recipe_snapshots() implemented
- [ ] get_snapshot_by_production_run() implemented
- [ ] NO update methods exist (immutability)
- [ ] Unit tests pass (8 test cases)
- [ ] >70% code coverage

## Review Guidance

- Verify session parameter is passed through correctly
- Check JSON serialization handles edge cases (None, empty lists)
- Confirm no update/delete methods exist

## Activity Log

- 2026-01-03T06:30:00Z - system - lane=planned - Prompt created.
