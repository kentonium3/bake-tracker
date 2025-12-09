---
work_package_id: "WP03"
subtasks:
  - "T014"
  - "T015"
  - "T016"
  - "T017"
  - "T018"
  - "T019"
  - "T020"
  - "T021"
title: "Service Layer - Validation"
phase: "Phase 1 - Foundation"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "90381"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP03 – Service Layer - Validation

## Objectives & Success Criteria

- Implement circular reference detection (prevent A→B→A cycles)
- Implement depth limit enforcement (max 3 levels)
- Integrate validation into `add_recipe_component()`
- Modify `delete_recipe()` to prevent deleting recipes used as components
- Add comprehensive unit tests for all validation scenarios

**Definition of Done**: All circular references blocked, depth limit enforced, deletion protected, with passing tests.

## Context & Constraints

**Reference Documents**:
- `kitty-specs/012-nested-recipes/contracts/recipe_service.md` - Validation rules and error messages
- `kitty-specs/012-nested-recipes/data-model.md` - Validation algorithms
- `kitty-specs/012-nested-recipes/spec.md` - Edge cases section

**Architecture Constraints**:
- Tree traversal for cycle detection (BFS or DFS)
- Max depth of 3 levels (Parent → Child → Grandchild)
- Clear error messages per contracts document

**Critical Test Cases**:
- Direct cycle: A→B, then B→A (must block)
- Indirect cycle: A→B→C, then C→A (must block)
- Self-reference: A→A (must block)
- Depth: A→B→C valid, A→B→C→D invalid

## Subtasks & Detailed Guidance

### Subtask T014 – Implement _would_create_cycle()

**Purpose**: Detect if adding a component would create a circular reference.

**Steps**:
1. Add helper function in `recipe_service.py`
2. Use BFS traversal from component to find if path leads back to parent
3. Return True if cycle would be created

**Files**: `src/services/recipe_service.py`

**Algorithm**:
```python
def _would_create_cycle(parent_id: int, component_id: int, session) -> bool:
    """
    Check if adding component_id as child of parent_id would create a cycle.

    Traverses the component tree starting from component_id to see if
    parent_id is reachable (which would mean adding this edge creates a cycle).

    Args:
        parent_id: The recipe that would become the parent
        component_id: The recipe to add as a component
        session: Database session

    Returns:
        True if adding this component would create a circular reference
    """
    # Self-reference check
    if parent_id == component_id:
        return True

    # BFS to find if parent_id is reachable from component_id
    visited = set()
    to_visit = [component_id]

    while to_visit:
        current = to_visit.pop(0)

        if current == parent_id:
            return True  # Found a path back to parent = cycle

        if current in visited:
            continue

        visited.add(current)

        # Get all components of current recipe
        components = (
            session.query(RecipeComponent.component_recipe_id)
            .filter_by(recipe_id=current)
            .all()
        )

        for (comp_id,) in components:
            if comp_id not in visited:
                to_visit.append(comp_id)

    return False
```

---

### Subtask T015 – Implement _get_recipe_depth()

**Purpose**: Calculate the maximum depth of a recipe's component hierarchy.

**Steps**:
1. Add helper function in `recipe_service.py`
2. Recursively calculate max depth of subtree
3. Leaf recipes have depth 1

**Files**: `src/services/recipe_service.py`

**Algorithm**:
```python
def _get_recipe_depth(recipe_id: int, session, _visited: set = None) -> int:
    """
    Get the maximum depth of a recipe's component hierarchy.

    Args:
        recipe_id: Recipe to check
        session: Database session
        _visited: Set of already visited recipe IDs (for cycle protection)

    Returns:
        Depth: 1 = no components, 2 = has components, 3 = has nested components
    """
    if _visited is None:
        _visited = set()

    # Cycle protection (shouldn't happen with valid data, but be safe)
    if recipe_id in _visited:
        return 0

    _visited.add(recipe_id)

    # Get components
    components = (
        session.query(RecipeComponent.component_recipe_id)
        .filter_by(recipe_id=recipe_id)
        .all()
    )

    if not components:
        return 1  # Leaf recipe

    max_child_depth = 0
    for (comp_id,) in components:
        child_depth = _get_recipe_depth(comp_id, session, _visited.copy())
        max_child_depth = max(max_child_depth, child_depth)

    return 1 + max_child_depth
```

---

### Subtask T016 – Implement _would_exceed_depth()

**Purpose**: Check if adding a component would exceed the 3-level depth limit.

**Steps**:
1. Add helper function in `recipe_service.py`
2. Calculate where parent sits in hierarchy and component's subtree depth
3. Ensure total doesn't exceed 3

**Files**: `src/services/recipe_service.py`

**Algorithm**:
```python
def _would_exceed_depth(parent_id: int, component_id: int, session, max_depth: int = 3) -> bool:
    """
    Check if adding component would exceed maximum nesting depth.

    The depth calculation considers:
    - Where the parent recipe sits in its own hierarchy (could already be nested)
    - The depth of the component's subtree

    Args:
        parent_id: The recipe that would become the parent
        component_id: The recipe to add as a component
        session: Database session
        max_depth: Maximum allowed depth (default: 3)

    Returns:
        True if adding this component would exceed the depth limit
    """
    # Get depth of component's subtree
    component_depth = _get_recipe_depth(component_id, session)

    # Check all paths where parent appears and calculate resulting depth
    # We need to find the deepest position of parent_id in any hierarchy

    def get_max_ancestor_depth(recipe_id: int, visited: set = None) -> int:
        """Find how deep this recipe is as a component in other recipes."""
        if visited is None:
            visited = set()

        if recipe_id in visited:
            return 0

        visited.add(recipe_id)

        # Find recipes that use this as a component
        parents = (
            session.query(RecipeComponent.recipe_id)
            .filter_by(component_recipe_id=recipe_id)
            .all()
        )

        if not parents:
            return 1  # Top-level recipe

        max_depth_above = 0
        for (pid,) in parents:
            depth_above = get_max_ancestor_depth(pid, visited.copy())
            max_depth_above = max(max_depth_above, depth_above)

        return 1 + max_depth_above

    # Parent's position in hierarchy + component's subtree depth
    parent_position = get_max_ancestor_depth(parent_id)
    total_depth = parent_position + component_depth

    return total_depth > max_depth
```

---

### Subtask T017 – Integrate validation into add_recipe_component()

**Purpose**: Add circular reference and depth checks to the add function.

**Steps**:
1. Modify `add_recipe_component()` to call validation helpers
2. Raise ValidationError with appropriate messages
3. Validation should happen before creating the component

**Files**: `src/services/recipe_service.py`

**Code** (add after duplicate check, before creating component):
```python
def add_recipe_component(...):
    # ... existing validation ...

    # Check for circular reference
    if _would_create_cycle(recipe_id, component_recipe_id, session):
        raise ValidationError(
            [f"Cannot add '{component.name}' as component: would create circular reference"]
        )

    # Check depth limit
    if _would_exceed_depth(recipe_id, component_recipe_id, session):
        raise ValidationError(
            [f"Cannot add '{component.name}': would exceed maximum nesting depth of 3 levels"]
        )

    # ... create component ...
```

---

### Subtask T018 – Modify delete_recipe() to check for component usage

**Purpose**: Prevent deleting a recipe that is used as a component in other recipes.

**Steps**:
1. Find existing `delete_recipe()` function
2. Before deleting, check if recipe is used as component anywhere
3. If used, raise ValidationError with list of parent recipe names

**Files**: `src/services/recipe_service.py`

**Code** (add at start of delete_recipe):
```python
def delete_recipe(recipe_id: int) -> bool:
    """
    Delete a recipe and its ingredients.
    ...
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Check if recipe is used as a component
            parent_components = (
                session.query(RecipeComponent)
                .filter_by(component_recipe_id=recipe_id)
                .all()
            )

            if parent_components:
                parent_names = []
                for comp in parent_components:
                    parent_recipe = session.query(Recipe).filter_by(id=comp.recipe_id).first()
                    if parent_recipe:
                        parent_names.append(parent_recipe.name)

                raise ValidationError(
                    [f"Cannot delete '{recipe.name}': used as component in: {', '.join(parent_names)}"]
                )

            # ... existing delete logic ...
```

---

### Subtask T019 – Add unit tests for circular reference detection

**Purpose**: Ensure cycle detection catches all cases.

**Files**: `src/tests/services/test_recipe_service.py`

**Test Cases**:
```python
def test_add_component_self_reference_blocked():
    """Recipe cannot include itself as a component."""
    recipe = create_test_recipe("Self")

    with pytest.raises(ValidationError) as excinfo:
        add_recipe_component(recipe.id, recipe.id)

    assert "circular reference" in str(excinfo.value).lower()


def test_add_component_direct_cycle_blocked():
    """A→B, then B→A should be blocked."""
    recipe_a = create_test_recipe("Recipe A")
    recipe_b = create_test_recipe("Recipe B")

    # A includes B - OK
    add_recipe_component(recipe_a.id, recipe_b.id)

    # B includes A - should fail (creates cycle)
    with pytest.raises(ValidationError) as excinfo:
        add_recipe_component(recipe_b.id, recipe_a.id)

    assert "circular reference" in str(excinfo.value).lower()


def test_add_component_indirect_cycle_blocked():
    """A→B→C, then C→A should be blocked."""
    recipe_a = create_test_recipe("Recipe A")
    recipe_b = create_test_recipe("Recipe B")
    recipe_c = create_test_recipe("Recipe C")

    # Build chain: A→B→C
    add_recipe_component(recipe_a.id, recipe_b.id)
    add_recipe_component(recipe_b.id, recipe_c.id)

    # C→A should fail (creates cycle through chain)
    with pytest.raises(ValidationError) as excinfo:
        add_recipe_component(recipe_c.id, recipe_a.id)

    assert "circular reference" in str(excinfo.value).lower()


def test_add_component_no_false_positive():
    """Non-circular hierarchies should work."""
    recipe_a = create_test_recipe("Recipe A")
    recipe_b = create_test_recipe("Recipe B")
    recipe_c = create_test_recipe("Recipe C")

    # A→B, A→C (diamond top) - should work
    add_recipe_component(recipe_a.id, recipe_b.id)
    add_recipe_component(recipe_a.id, recipe_c.id)

    # Verify both added
    components = get_recipe_components(recipe_a.id)
    assert len(components) == 2
```

---

### Subtask T020 – Add unit tests for depth limit enforcement

**Purpose**: Ensure 3-level limit is enforced.

**Files**: `src/tests/services/test_recipe_service.py`

**Test Cases**:
```python
def test_add_component_depth_3_allowed():
    """3-level nesting should be allowed."""
    recipe_a = create_test_recipe("Level 1")
    recipe_b = create_test_recipe("Level 2")
    recipe_c = create_test_recipe("Level 3")

    # A→B→C (3 levels)
    add_recipe_component(recipe_a.id, recipe_b.id)
    add_recipe_component(recipe_b.id, recipe_c.id)

    # Verify structure
    assert len(get_recipe_components(recipe_a.id)) == 1
    assert len(get_recipe_components(recipe_b.id)) == 1


def test_add_component_depth_4_blocked():
    """4-level nesting should be blocked."""
    recipe_a = create_test_recipe("Level 1")
    recipe_b = create_test_recipe("Level 2")
    recipe_c = create_test_recipe("Level 3")
    recipe_d = create_test_recipe("Level 4")

    # Build 3-level: A→B→C
    add_recipe_component(recipe_a.id, recipe_b.id)
    add_recipe_component(recipe_b.id, recipe_c.id)

    # Try to add D under C (would make 4 levels)
    with pytest.raises(ValidationError) as excinfo:
        add_recipe_component(recipe_c.id, recipe_d.id)

    assert "depth" in str(excinfo.value).lower()


def test_add_component_depth_with_subtree():
    """Adding a recipe with its own subtree should count total depth."""
    recipe_a = create_test_recipe("Parent")
    recipe_b = create_test_recipe("Sub 1")
    recipe_c = create_test_recipe("Sub 2")
    recipe_d = create_test_recipe("Sub-sub")

    # B→D (2-level subtree)
    add_recipe_component(recipe_b.id, recipe_d.id)

    # A already at level 1, B's subtree is 2 levels = total 3 (OK)
    add_recipe_component(recipe_a.id, recipe_b.id)

    # C→D (2-level subtree)
    add_recipe_component(recipe_c.id, recipe_d.id)

    # Try A→C: A is level 1, C's subtree is 2, but A→B→D already exists
    # This should work since A→C path would only be 3 levels
    add_recipe_component(recipe_a.id, recipe_c.id)
```

---

### Subtask T021 – Add unit tests for deletion protection

**Purpose**: Ensure recipes used as components cannot be deleted.

**Files**: `src/tests/services/test_recipe_service.py`

**Test Cases**:
```python
def test_delete_recipe_used_as_component_blocked():
    """Cannot delete a recipe that is used as a component."""
    recipe_parent = create_test_recipe("Parent")
    recipe_child = create_test_recipe("Child")

    add_recipe_component(recipe_parent.id, recipe_child.id)

    with pytest.raises(ValidationError) as excinfo:
        delete_recipe(recipe_child.id)

    assert "used as component" in str(excinfo.value).lower()
    assert recipe_parent.name in str(excinfo.value)


def test_delete_recipe_after_removing_component():
    """Can delete recipe after removing it from all parents."""
    recipe_parent = create_test_recipe("Parent")
    recipe_child = create_test_recipe("Child")

    add_recipe_component(recipe_parent.id, recipe_child.id)
    remove_recipe_component(recipe_parent.id, recipe_child.id)

    # Now deletion should work
    result = delete_recipe(recipe_child.id)
    assert result is True


def test_delete_recipe_with_no_parents():
    """Recipe not used as component can be deleted."""
    recipe = create_test_recipe("Standalone")

    result = delete_recipe(recipe.id)
    assert result is True


def test_delete_parent_cascades_components():
    """Deleting parent recipe removes component relationships."""
    recipe_parent = create_test_recipe("Parent")
    recipe_child = create_test_recipe("Child")

    add_recipe_component(recipe_parent.id, recipe_child.id)

    # Delete parent
    delete_recipe(recipe_parent.id)

    # Child should now be deletable
    result = delete_recipe(recipe_child.id)
    assert result is True
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Cycle detection misses edge case | Comprehensive test suite with various cycle patterns |
| Depth calculation error | Test with known hierarchies, verify counts |
| Performance on large hierarchies | Max depth 3 limits recursion; <100 recipes total |

## Definition of Done Checklist

- [ ] `_would_create_cycle()` detects all cycle types
- [ ] `_get_recipe_depth()` correctly calculates depth
- [ ] `_would_exceed_depth()` enforces 3-level limit
- [ ] `add_recipe_component()` validates before adding
- [ ] `delete_recipe()` blocks deletion of used components
- [ ] All validation tests passing
- [ ] Error messages match contract specification

## Review Guidance

- Test circular reference detection with complex scenarios
- Verify depth calculation with diagrams
- Check error messages are user-friendly
- Ensure validation runs before any database modification

## Activity Log

- 2025-12-09T00:00:00Z – system – lane=planned – Prompt created.
- 2025-12-09T13:34:19Z – claude – shell_pid=89783 – lane=doing – Started implementation
- 2025-12-09T13:38:24Z – claude – shell_pid=90381 – lane=for_review – Completed implementation - 13 new tests, all 524 pass
