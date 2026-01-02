---
work_package_id: "WP06"
subtasks:
  - "T024"
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "Deletion & Slug Tests"
phase: "Phase 4 - Testing"
lane: "for_review"
assignee: ""
agent: "gemini"
shell_pid: "15513"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-02T12:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 - Deletion & Slug Tests

## Review Feedback

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## Objectives & Success Criteria

**Objective**: Create comprehensive test coverage for deletion protection and slug generation features to ensure >70% service layer coverage per constitution requirements.

**Success Criteria**:
- All deletion blocking scenarios tested (products, recipes, children)
- Snapshot denormalization tested
- Cascade delete for Alias and Crosswalk tested
- Slug auto-generation and conflict resolution tested
- Field name normalization tested
- All tests pass with no regressions

## Context & Constraints

**Related Documents**:
- Spec: `kitty-specs/035-ingredient-auto-slug/spec.md` (all FRs)
- Plan: `kitty-specs/035-ingredient-auto-slug/plan.md` (Phase 6)
- Constitution: `.kittify/memory/constitution.md` (>70% coverage requirement)

**Key Constraints**:
- Follow existing test patterns in `src/tests/services/test_ingredient_service.py`
- Use pytest fixtures for test data setup/teardown
- Tests must be isolated - no test pollution between runs
- Each test should verify ONE behavior

**Dependencies**:
- WP01-WP05 must be complete (all functionality implemented)

## Subtasks & Detailed Guidance

### Subtask T024 - Test Blocked by Products

**Purpose**: Verify deletion is blocked when Products reference the ingredient.

**Steps**:
1. Create or open `src/tests/services/test_ingredient_service.py`
2. Add test class or method:

```python
def test_delete_blocked_by_products(session):
    """Verify deletion blocked when products reference ingredient."""
    # Arrange
    ingredient = create_test_ingredient(session, display_name="Test Flour")
    product = create_test_product(session, ingredient_id=ingredient.id)

    # Act
    can_delete, reason, details = can_delete_ingredient(ingredient.id, session=session)

    # Assert
    assert can_delete is False
    assert "1 products" in reason or "1 product" in reason
    assert details["products"] == 1

    # Also verify delete_ingredient_safe raises
    with pytest.raises(IngredientInUse) as exc_info:
        delete_ingredient_safe(ingredient.id, session=session)
    assert exc_info.value.details["products"] == 1
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes - can write in parallel with other tests

### Subtask T025 - Test Blocked by Recipes

**Purpose**: Verify deletion is blocked when RecipeIngredient records reference the ingredient.

**Steps**:
```python
def test_delete_blocked_by_recipes(session):
    """Verify deletion blocked when recipes use ingredient."""
    # Arrange
    ingredient = create_test_ingredient(session, display_name="Test Vanilla")
    recipe = create_test_recipe(session)
    recipe_ingredient = RecipeIngredient(
        recipe_id=recipe.id,
        ingredient_id=ingredient.id,
        quantity=1.0,
        unit="tsp"
    )
    session.add(recipe_ingredient)
    session.commit()

    # Act
    can_delete, reason, details = can_delete_ingredient(ingredient.id, session=session)

    # Assert
    assert can_delete is False
    assert "1 recipes" in reason or "1 recipe" in reason
    assert details["recipes"] == 1
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes

### Subtask T026 - Test Blocked by Children

**Purpose**: Verify deletion is blocked when ingredient has child ingredients.

**Steps**:
```python
def test_delete_blocked_by_children(session):
    """Verify deletion blocked when ingredient has children."""
    # Arrange
    parent = create_test_ingredient(session, display_name="Parent Category")
    child = create_test_ingredient(
        session,
        display_name="Child Ingredient",
        parent_ingredient_id=parent.id
    )

    # Act
    can_delete, reason, details = can_delete_ingredient(parent.id, session=session)

    # Assert
    assert can_delete is False
    assert "1 child" in reason
    assert details["children"] == 1
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes

### Subtask T027 - Test Snapshot Denormalization

**Purpose**: Verify historical snapshot records are denormalized before ingredient deletion.

**Steps**:
```python
def test_delete_with_snapshots_denormalizes(session):
    """Verify snapshot records preserve ingredient names on deletion."""
    # Arrange - create hierarchy
    l0 = create_test_ingredient(session, display_name="Baking")
    l1 = create_test_ingredient(session, display_name="Flour", parent_ingredient_id=l0.id)
    l2 = create_test_ingredient(session, display_name="All-Purpose", parent_ingredient_id=l1.id)

    # Create snapshot with ingredient reference
    snapshot = create_test_inventory_snapshot(session)
    snapshot_ingredient = SnapshotIngredient(
        snapshot_id=snapshot.id,
        ingredient_id=l2.id,
        quantity=5.0
    )
    session.add(snapshot_ingredient)
    session.commit()
    snapshot_ingredient_id = snapshot_ingredient.id

    # Act - delete the leaf ingredient (no blocking references)
    delete_ingredient_safe(l2.id, session=session)

    # Assert - snapshot record preserved with denormalized names
    updated = session.query(SnapshotIngredient).filter(
        SnapshotIngredient.id == snapshot_ingredient_id
    ).first()

    assert updated.ingredient_id is None  # FK nullified
    assert updated.ingredient_name_snapshot == "All-Purpose"
    assert updated.parent_l1_name_snapshot == "Flour"
    assert updated.parent_l0_name_snapshot == "Baking"
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: No - complex setup, verify alone

### Subtask T028 - Test Cascade Delete Aliases

**Purpose**: Verify IngredientAlias records are automatically deleted with ingredient.

**Steps**:
```python
def test_delete_cascades_aliases(session):
    """Verify ingredient aliases are cascade-deleted."""
    # Arrange
    ingredient = create_test_ingredient(session, display_name="Powdered Sugar")
    alias = IngredientAlias(
        ingredient_id=ingredient.id,
        alias_name="Confectioner's Sugar"
    )
    session.add(alias)
    session.commit()
    alias_id = alias.id

    # Act
    delete_ingredient_safe(ingredient.id, session=session)

    # Assert - alias should be gone
    remaining = session.query(IngredientAlias).filter(
        IngredientAlias.id == alias_id
    ).first()
    assert remaining is None
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes

### Subtask T029 - Test Cascade Delete Crosswalks

**Purpose**: Verify IngredientCrosswalk records are automatically deleted with ingredient.

**Steps**:
```python
def test_delete_cascades_crosswalks(session):
    """Verify ingredient crosswalks are cascade-deleted."""
    # Arrange
    ingredient = create_test_ingredient(session, display_name="Honey")
    crosswalk = IngredientCrosswalk(
        ingredient_id=ingredient.id,
        external_system="FoodOn",
        external_id="FOODON_12345"
    )
    session.add(crosswalk)
    session.commit()
    crosswalk_id = crosswalk.id

    # Act
    delete_ingredient_safe(ingredient.id, session=session)

    # Assert - crosswalk should be gone
    remaining = session.query(IngredientCrosswalk).filter(
        IngredientCrosswalk.id == crosswalk_id
    ).first()
    assert remaining is None
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes

### Subtask T030 - Test Slug Auto-Generation

**Purpose**: Verify slugs are automatically generated from display_name.

**Steps**:
```python
def test_slug_auto_generation(session):
    """Verify slug is auto-generated from display_name."""
    # Arrange & Act
    ingredient = create_ingredient({
        "display_name": "Brown Sugar",
        "parent_ingredient_id": None
    }, session=session)

    # Assert
    assert ingredient.slug is not None
    assert ingredient.slug == "brown_sugar"  # underscores per project convention
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes

### Subtask T031 - Test Slug Conflict Resolution

**Purpose**: Verify slugs are uniquified with numeric suffixes when conflicts exist.

**Steps**:
```python
def test_slug_conflict_resolution(session):
    """Verify slug conflicts resolved with numeric suffix."""
    # Arrange - create first ingredient
    first = create_ingredient({
        "display_name": "Vanilla",
        "parent_ingredient_id": None
    }, session=session)
    assert first.slug == "vanilla"

    # Act - create second with same name
    second = create_ingredient({
        "display_name": "Vanilla",
        "parent_ingredient_id": None
    }, session=session)

    # Assert - should have suffix
    assert second.slug == "vanilla_1"

    # Act - create third
    third = create_ingredient({
        "display_name": "Vanilla",
        "parent_ingredient_id": None
    }, session=session)

    # Assert
    assert third.slug == "vanilla_2"
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes

### Subtask T032 - Test Field Name Normalization

**Purpose**: Verify "name" field is normalized to "display_name".

**Steps**:
```python
def test_field_name_normalization(session):
    """Verify 'name' field is normalized to 'display_name'."""
    # Arrange & Act - use "name" instead of "display_name"
    ingredient = create_ingredient({
        "name": "Cinnamon",  # UI-style field name
        "parent_ingredient_id": None
    }, session=session)

    # Assert
    assert ingredient.display_name == "Cinnamon"
    assert ingredient.slug == "cinnamon"
```

**Files**: `src/tests/services/test_ingredient_service.py`
**Parallel?**: Yes

## Test Fixtures Needed

You may need to create these helper functions if they don't exist:

```python
@pytest.fixture
def session():
    """Provide a clean database session for each test."""
    # Setup and teardown logic
    ...

def create_test_ingredient(session, display_name, parent_ingredient_id=None):
    """Helper to create test ingredient."""
    ...

def create_test_product(session, ingredient_id):
    """Helper to create test product."""
    ...

def create_test_recipe(session):
    """Helper to create test recipe."""
    ...

def create_test_inventory_snapshot(session):
    """Helper to create test snapshot."""
    ...
```

## Test Strategy

**Run all tests**:
```bash
pytest src/tests/services/test_ingredient_service.py -v
```

**Run with coverage**:
```bash
pytest src/tests/services/test_ingredient_service.py -v --cov=src/services/ingredient_service
```

**Target**: >70% coverage for ingredient_service module

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Test pollution | Use session fixtures with proper cleanup |
| Missing model imports | Import all needed models at test module top |
| Fixture conflicts | Use unique names for each test's data |

## Definition of Done Checklist

- [ ] T024: `test_delete_blocked_by_products` passes
- [ ] T025: `test_delete_blocked_by_recipes` passes
- [ ] T026: `test_delete_blocked_by_children` passes
- [ ] T027: `test_delete_with_snapshots_denormalizes` passes
- [ ] T028: `test_delete_cascades_aliases` passes
- [ ] T029: `test_delete_cascades_crosswalks` passes
- [ ] T030: `test_slug_auto_generation` passes
- [ ] T031: `test_slug_conflict_resolution` passes
- [ ] T032: `test_field_name_normalization` passes
- [ ] All existing tests still pass
- [ ] Coverage meets >70% threshold

## Review Guidance

- Verify each test tests ONE behavior
- Check test isolation (no shared state)
- Verify assertions are meaningful
- Check fixture usage is correct

## Activity Log

- 2026-01-02T12:00:00Z - system - lane=planned - Prompt created via /spec-kitty.tasks
- 2026-01-02T19:48:38Z – gemini – shell_pid=15513 – lane=doing – Starting Wave 4 test implementation
- 2026-01-02T20:02:02Z – gemini – shell_pid=15513 – lane=for_review – Ready for review - T024-T032 complete, all 50 tests passing
