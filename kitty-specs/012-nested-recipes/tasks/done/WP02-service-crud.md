---
work_package_id: "WP02"
subtasks:
  - "T008"
  - "T009"
  - "T010"
  - "T011"
  - "T012"
  - "T013"
title: "Service Layer - Component CRUD"
phase: "Phase 1 - Foundation"
lane: "done"
assignee: "claude"
agent: "claude-reviewer"
shell_pid: "98749"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP02 – Service Layer - Component CRUD

## Objectives & Success Criteria

- Implement `add_recipe_component()` - add a sub-recipe to a parent recipe
- Implement `remove_recipe_component()` - remove a sub-recipe from a parent recipe
- Implement `update_recipe_component()` - update quantity/notes for existing component
- Implement `get_recipe_components()` - retrieve all components of a recipe
- Implement `get_recipes_using_component()` - find recipes using a given recipe as component
- Add unit tests for all CRUD operations

**Definition of Done**: All CRUD operations work correctly and have passing tests.

## Context & Constraints

**Reference Documents**:
- `kitty-specs/012-nested-recipes/contracts/recipe_service.md` - API contracts
- `src/services/recipe_service.py` - Existing patterns to follow
- `src/models/recipe.py` - RecipeComponent model from WP01

**Architecture Constraints**:
- Use `session_scope()` context manager pattern
- Follow existing validation patterns (check entity exists before operations)
- Use existing exception types: `RecipeNotFound`, `ValidationError`
- Eager load relationships to avoid lazy loading issues outside session

**Note**: Validation (circular refs, depth limit) is deferred to WP03. This WP implements basic CRUD only.

## Subtasks & Detailed Guidance

### Subtask T008 – Implement add_recipe_component()

**Purpose**: Allow adding a sub-recipe to a parent recipe.

**Steps**:
1. Add new section in `recipe_service.py`: `# Recipe Component Management`
2. Implement function per contract signature
3. Validate both recipes exist
4. Validate quantity > 0
5. Check if component already exists in recipe (prevent duplicates)
6. Create RecipeComponent and save
7. Return the created component

**Files**: `src/services/recipe_service.py`

**Code**:
```python
def add_recipe_component(
    recipe_id: int,
    component_recipe_id: int,
    quantity: float = 1.0,
    notes: str = None,
    sort_order: int = None,
) -> RecipeComponent:
    """
    Add a recipe as a component of another recipe.

    Args:
        recipe_id: Parent recipe ID
        component_recipe_id: Child recipe ID to add as component
        quantity: Batch multiplier (default: 1.0)
        notes: Optional notes for this component
        sort_order: Display order (default: append to end)

    Returns:
        Created RecipeComponent instance

    Raises:
        RecipeNotFound: If parent or component recipe doesn't exist
        ValidationError: If quantity <= 0 or component already exists
    """
    if quantity <= 0:
        raise ValidationError(["Batch quantity must be greater than 0"])

    try:
        with session_scope() as session:
            # Verify parent recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Verify component recipe exists
            component = session.query(Recipe).filter_by(id=component_recipe_id).first()
            if not component:
                raise RecipeNotFound(component_recipe_id)

            # Check if already a component
            existing = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id, component_recipe_id=component_recipe_id)
                .first()
            )
            if existing:
                raise ValidationError([f"'{component.name}' is already a component of this recipe"])

            # Determine sort_order if not provided
            if sort_order is None:
                max_order = (
                    session.query(func.max(RecipeComponent.sort_order))
                    .filter_by(recipe_id=recipe_id)
                    .scalar()
                )
                sort_order = (max_order or 0) + 1

            # Create component
            recipe_component = RecipeComponent(
                recipe_id=recipe_id,
                component_recipe_id=component_recipe_id,
                quantity=quantity,
                notes=notes,
                sort_order=sort_order,
            )

            session.add(recipe_component)
            session.flush()
            session.refresh(recipe_component)

            # Eager load relationships
            _ = recipe_component.recipe
            _ = recipe_component.component_recipe

            return recipe_component

    except (RecipeNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to add recipe component", e)
```

**Required Imports** (add to top of file):
```python
from src.models import RecipeComponent
from sqlalchemy import func
```

---

### Subtask T009 – Implement remove_recipe_component()

**Purpose**: Allow removing a sub-recipe from a parent recipe.

**Steps**:
1. Implement function per contract signature
2. Verify parent recipe exists
3. Delete the component relationship
4. Return True if deleted, False if not found

**Files**: `src/services/recipe_service.py`

**Code**:
```python
def remove_recipe_component(recipe_id: int, component_recipe_id: int) -> bool:
    """
    Remove a component recipe from a parent recipe.

    Args:
        recipe_id: Parent recipe ID
        component_recipe_id: Component recipe ID to remove

    Returns:
        True if removed, False if component not found

    Raises:
        RecipeNotFound: If parent recipe doesn't exist
    """
    try:
        with session_scope() as session:
            # Verify parent recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Delete component
            deleted = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id, component_recipe_id=component_recipe_id)
                .delete()
            )

            return deleted > 0

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to remove recipe component", e)
```

---

### Subtask T010 – Implement update_recipe_component()

**Purpose**: Allow updating quantity or notes for an existing component.

**Steps**:
1. Implement function per contract signature
2. Verify parent recipe exists
3. Find the component
4. Update provided fields
5. Return updated component

**Files**: `src/services/recipe_service.py`

**Code**:
```python
def update_recipe_component(
    recipe_id: int,
    component_recipe_id: int,
    quantity: float = None,
    notes: str = None,
    sort_order: int = None,
) -> RecipeComponent:
    """
    Update quantity or notes for an existing recipe component.

    Args:
        recipe_id: Parent recipe ID
        component_recipe_id: Component recipe ID
        quantity: New batch multiplier (if provided)
        notes: New notes (if provided, use empty string to clear)
        sort_order: New display order (if provided)

    Returns:
        Updated RecipeComponent instance

    Raises:
        RecipeNotFound: If parent recipe doesn't exist
        ValidationError: If component not found or quantity <= 0
    """
    if quantity is not None and quantity <= 0:
        raise ValidationError(["Batch quantity must be greater than 0"])

    try:
        with session_scope() as session:
            # Verify parent recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Find component
            component = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id, component_recipe_id=component_recipe_id)
                .first()
            )
            if not component:
                raise ValidationError(["Component recipe not found in this recipe"])

            # Update fields if provided
            if quantity is not None:
                component.quantity = quantity
            if notes is not None:
                component.notes = notes if notes else None
            if sort_order is not None:
                component.sort_order = sort_order

            session.flush()
            session.refresh(component)

            # Eager load relationships
            _ = component.recipe
            _ = component.component_recipe

            return component

    except (RecipeNotFound, ValidationError):
        raise
    except SQLAlchemyError as e:
        raise DatabaseError("Failed to update recipe component", e)
```

---

### Subtask T011 – Implement get_recipe_components()

**Purpose**: Retrieve all sub-recipes for a given recipe.

**Steps**:
1. Implement function per contract signature
2. Verify recipe exists
3. Query components ordered by sort_order
4. Eager load related recipes

**Files**: `src/services/recipe_service.py`

**Code**:
```python
def get_recipe_components(recipe_id: int) -> List[RecipeComponent]:
    """
    Get all component recipes for a recipe.

    Args:
        recipe_id: Recipe ID

    Returns:
        List of RecipeComponent instances, ordered by sort_order

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    try:
        with session_scope() as session:
            # Verify recipe exists
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Get components ordered by sort_order
            components = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id)
                .order_by(RecipeComponent.sort_order)
                .all()
            )

            # Eager load relationships
            for comp in components:
                _ = comp.recipe
                _ = comp.component_recipe

            return components

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipe components for {recipe_id}", e)
```

---

### Subtask T012 – Implement get_recipes_using_component()

**Purpose**: Find all recipes that use a given recipe as a component.

**Steps**:
1. Implement function per contract signature
2. Verify the component recipe exists
3. Query for all RecipeComponents referencing this recipe
4. Return the parent recipes

**Files**: `src/services/recipe_service.py`

**Code**:
```python
def get_recipes_using_component(component_recipe_id: int) -> List[Recipe]:
    """
    Get all recipes that use a given recipe as a component.

    Args:
        component_recipe_id: Recipe ID to check

    Returns:
        List of Recipe instances that use this as a component

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    try:
        with session_scope() as session:
            # Verify recipe exists
            recipe = session.query(Recipe).filter_by(id=component_recipe_id).first()
            if not recipe:
                raise RecipeNotFound(component_recipe_id)

            # Find parent recipes
            parent_recipes = (
                session.query(Recipe)
                .join(RecipeComponent, Recipe.id == RecipeComponent.recipe_id)
                .filter(RecipeComponent.component_recipe_id == component_recipe_id)
                .order_by(Recipe.name)
                .all()
            )

            # Eager load relationships
            for r in parent_recipes:
                _ = r.recipe_ingredients
                for ri in r.recipe_ingredients:
                    _ = ri.ingredient

            return parent_recipes

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to get recipes using component {component_recipe_id}", e)
```

---

### Subtask T013 – Add unit tests for all CRUD operations

**Purpose**: Ensure CRUD operations work correctly and handle edge cases.

**Steps**:
1. Create test file or add to existing `src/tests/services/test_recipe_service.py`
2. Add tests for each function
3. Cover happy path, validation errors, and edge cases

**Files**: `src/tests/services/test_recipe_service.py`

**Test Cases**:
```python
# Test add_recipe_component
def test_add_recipe_component_success(session):
    """Test adding a component to a recipe."""
    # Create two recipes
    recipe1 = create_test_recipe("Parent Recipe")
    recipe2 = create_test_recipe("Child Recipe")

    component = add_recipe_component(recipe1.id, recipe2.id, quantity=2.0, notes="Test")

    assert component.recipe_id == recipe1.id
    assert component.component_recipe_id == recipe2.id
    assert component.quantity == 2.0
    assert component.notes == "Test"


def test_add_recipe_component_invalid_quantity():
    """Test that quantity <= 0 raises ValidationError."""
    recipe1 = create_test_recipe("Parent")
    recipe2 = create_test_recipe("Child")

    with pytest.raises(ValidationError):
        add_recipe_component(recipe1.id, recipe2.id, quantity=0)


def test_add_recipe_component_duplicate():
    """Test that adding same component twice raises ValidationError."""
    recipe1 = create_test_recipe("Parent")
    recipe2 = create_test_recipe("Child")

    add_recipe_component(recipe1.id, recipe2.id)

    with pytest.raises(ValidationError):
        add_recipe_component(recipe1.id, recipe2.id)


def test_add_recipe_component_nonexistent_recipe():
    """Test that nonexistent recipe raises RecipeNotFound."""
    recipe1 = create_test_recipe("Parent")

    with pytest.raises(RecipeNotFound):
        add_recipe_component(recipe1.id, 99999)


# Test remove_recipe_component
def test_remove_recipe_component_success():
    """Test removing a component."""
    recipe1 = create_test_recipe("Parent")
    recipe2 = create_test_recipe("Child")
    add_recipe_component(recipe1.id, recipe2.id)

    result = remove_recipe_component(recipe1.id, recipe2.id)
    assert result is True

    # Verify removed
    components = get_recipe_components(recipe1.id)
    assert len(components) == 0


def test_remove_recipe_component_not_found():
    """Test removing nonexistent component returns False."""
    recipe1 = create_test_recipe("Parent")
    recipe2 = create_test_recipe("Child")

    result = remove_recipe_component(recipe1.id, recipe2.id)
    assert result is False


# Test update_recipe_component
def test_update_recipe_component_success():
    """Test updating component quantity and notes."""
    recipe1 = create_test_recipe("Parent")
    recipe2 = create_test_recipe("Child")
    add_recipe_component(recipe1.id, recipe2.id, quantity=1.0)

    updated = update_recipe_component(recipe1.id, recipe2.id, quantity=3.0, notes="Updated")

    assert updated.quantity == 3.0
    assert updated.notes == "Updated"


# Test get_recipe_components
def test_get_recipe_components_ordered():
    """Test components returned in sort_order."""
    recipe1 = create_test_recipe("Parent")
    recipe2 = create_test_recipe("Child1")
    recipe3 = create_test_recipe("Child2")

    add_recipe_component(recipe1.id, recipe3.id, sort_order=2)
    add_recipe_component(recipe1.id, recipe2.id, sort_order=1)

    components = get_recipe_components(recipe1.id)
    assert len(components) == 2
    assert components[0].component_recipe_id == recipe2.id
    assert components[1].component_recipe_id == recipe3.id


# Test get_recipes_using_component
def test_get_recipes_using_component():
    """Test finding recipes that use a component."""
    recipe1 = create_test_recipe("Parent1")
    recipe2 = create_test_recipe("Parent2")
    recipe3 = create_test_recipe("Shared Child")

    add_recipe_component(recipe1.id, recipe3.id)
    add_recipe_component(recipe2.id, recipe3.id)

    parents = get_recipes_using_component(recipe3.id)
    assert len(parents) == 2
    parent_ids = [p.id for p in parents]
    assert recipe1.id in parent_ids
    assert recipe2.id in parent_ids
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Lazy loading outside session | Explicitly access relationships before returning |
| sort_order gaps after removal | Accept gaps; re-sort on read not required |
| Concurrent modifications | Single-user app; not a concern |

## Definition of Done Checklist

- [ ] `add_recipe_component()` implemented and working
- [ ] `remove_recipe_component()` implemented and working
- [ ] `update_recipe_component()` implemented and working
- [ ] `get_recipe_components()` implemented and working
- [ ] `get_recipes_using_component()` implemented and working
- [ ] All unit tests passing
- [ ] Existing recipe tests still pass

## Review Guidance

- Verify error handling matches contract specification
- Check eager loading prevents DetachedInstanceError
- Confirm sort_order auto-increment works correctly
- Test with real recipes via manual testing

## Activity Log

- 2025-12-09T00:00:00Z – system – lane=planned – Prompt created.
- 2025-12-09T13:28:28Z – claude – shell_pid=88867 – lane=doing – Started implementation
- 2025-12-09T13:33:29Z – claude – shell_pid=89508 – lane=for_review – Completed implementation - 23 new tests, all 511 pass
- 2025-12-09T17:54:39Z – claude-reviewer – shell_pid=98749 – lane=done – Code review: APPROVED - All CRUD functions with 20+ tests
