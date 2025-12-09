---
work_package_id: "WP04"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Service Layer - Cost & Aggregation"
phase: "Phase 2 - Core Features"
lane: "done"
assignee: ""
agent: "claude-reviewer"
shell_pid: "98957"
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2025-12-09T00:00:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Service Layer - Cost & Aggregation

## Objectives & Success Criteria

- Implement `get_aggregated_ingredients()` - collect all ingredients across recipe hierarchy
- Implement `calculate_total_cost_with_components()` - recursive cost calculation
- Update `Recipe.calculate_cost()` or keep separate function for component-aware cost
- Update `get_recipe_with_costs()` to include component cost breakdown
- Add unit tests for aggregation and cost calculation

**Definition of Done**: Shopping lists include all ingredients from hierarchy; costs include all sub-recipe costs.

## Context & Constraints

**Reference Documents**:
- `kitty-specs/012-nested-recipes/contracts/recipe_service.md` - Return value specifications
- `kitty-specs/012-nested-recipes/spec.md` - User Story 2 (Cost) and User Story 3 (Shopping List)

**Architecture Constraints**:
- Aggregation by (ingredient_id, unit) - same ingredient with different units NOT combined
- Cost = direct ingredients + sum(component.quantity × component_recipe.cost)
- Must handle recipes with no cost data (some ingredients missing prices)

**Important Formula**:
```
total_cost = sum(direct_ingredient_costs) + sum(component.quantity * component_recipe.total_cost)
```

## Subtasks & Detailed Guidance

### Subtask T022 – Implement get_aggregated_ingredients()

**Purpose**: Collect all ingredients from a recipe and all sub-recipes for shopping list generation.

**Steps**:
1. Add function in `recipe_service.py`
2. Recursively traverse component tree
3. Multiply quantities by component batch multipliers
4. Aggregate same ingredients (same ingredient_id + unit)
5. Track source recipes for each ingredient

**Files**: `src/services/recipe_service.py`

**Code**:
```python
def get_aggregated_ingredients(
    recipe_id: int,
    multiplier: float = 1.0,
) -> List[Dict]:
    """
    Get all ingredients from a recipe and all sub-recipes with aggregated quantities.

    Args:
        recipe_id: Recipe ID
        multiplier: Scale factor for all quantities (default: 1.0)

    Returns:
        List of aggregated ingredients with structure:
        [
            {
                "ingredient": Ingredient instance,
                "ingredient_id": int,
                "ingredient_name": str,
                "total_quantity": float,
                "unit": str,
                "sources": [{"recipe_name": str, "quantity": float}, ...]
            },
            ...
        ]

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Dictionary to aggregate: key = (ingredient_id, unit)
            aggregated = {}

            def collect_ingredients(r_id: int, mult: float, visited: set = None):
                """Recursively collect ingredients from recipe and components."""
                if visited is None:
                    visited = set()

                if r_id in visited:
                    return  # Prevent infinite loop (shouldn't happen with validation)

                visited.add(r_id)

                # Get recipe
                r = session.query(Recipe).filter_by(id=r_id).first()
                if not r:
                    return

                # Collect direct ingredients
                for ri in r.recipe_ingredients:
                    key = (ri.ingredient_id, ri.unit)
                    qty = ri.quantity * mult

                    if key not in aggregated:
                        aggregated[key] = {
                            "ingredient": ri.ingredient,
                            "ingredient_id": ri.ingredient_id,
                            "ingredient_name": ri.ingredient.display_name if ri.ingredient else "Unknown",
                            "total_quantity": 0.0,
                            "unit": ri.unit,
                            "sources": [],
                        }

                    aggregated[key]["total_quantity"] += qty
                    aggregated[key]["sources"].append({
                        "recipe_name": r.name,
                        "quantity": qty,
                    })

                # Collect from components
                components = (
                    session.query(RecipeComponent)
                    .filter_by(recipe_id=r_id)
                    .all()
                )

                for comp in components:
                    component_mult = mult * comp.quantity
                    collect_ingredients(comp.component_recipe_id, component_mult, visited.copy())

            # Start collection
            collect_ingredients(recipe_id, multiplier)

            # Convert to list and sort by ingredient name
            result = sorted(aggregated.values(), key=lambda x: x["ingredient_name"])

            return result

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to aggregate ingredients for recipe {recipe_id}", e)
```

---

### Subtask T023 – Implement calculate_total_cost_with_components()

**Purpose**: Calculate total recipe cost including all sub-recipe costs.

**Steps**:
1. Add function in `recipe_service.py`
2. Calculate direct ingredient cost
3. Recursively calculate component costs
4. Return detailed breakdown

**Files**: `src/services/recipe_service.py`

**Code**:
```python
def calculate_total_cost_with_components(recipe_id: int) -> Dict:
    """
    Calculate total recipe cost including all sub-recipe costs.

    Args:
        recipe_id: Recipe ID

    Returns:
        Cost breakdown:
        {
            "recipe_id": int,
            "recipe_name": str,
            "direct_ingredient_cost": float,
            "component_costs": [
                {
                    "component_recipe_id": int,
                    "component_recipe_name": str,
                    "quantity": float,
                    "unit_cost": float,
                    "total_cost": float
                },
                ...
            ],
            "total_component_cost": float,
            "total_cost": float,
            "cost_per_unit": float,
        }

    Raises:
        RecipeNotFound: If recipe doesn't exist
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                raise RecipeNotFound(recipe_id)

            # Calculate direct ingredient cost
            direct_cost = 0.0
            for ri in recipe.recipe_ingredients:
                direct_cost += ri.calculate_cost()

            # Calculate component costs
            component_costs = []
            total_component_cost = 0.0

            components = (
                session.query(RecipeComponent)
                .filter_by(recipe_id=recipe_id)
                .order_by(RecipeComponent.sort_order)
                .all()
            )

            for comp in components:
                # Recursive call to get component's total cost
                comp_result = _calculate_recipe_cost_recursive(comp.component_recipe_id, session)
                unit_cost = comp_result["total_cost"]
                comp_total = unit_cost * comp.quantity

                component_costs.append({
                    "component_recipe_id": comp.component_recipe_id,
                    "component_recipe_name": comp.component_recipe.name if comp.component_recipe else "Unknown",
                    "quantity": comp.quantity,
                    "unit_cost": unit_cost,
                    "total_cost": comp_total,
                })

                total_component_cost += comp_total

            total_cost = direct_cost + total_component_cost
            cost_per_unit = total_cost / recipe.yield_quantity if recipe.yield_quantity > 0 else 0.0

            return {
                "recipe_id": recipe_id,
                "recipe_name": recipe.name,
                "direct_ingredient_cost": direct_cost,
                "component_costs": component_costs,
                "total_component_cost": total_component_cost,
                "total_cost": total_cost,
                "cost_per_unit": cost_per_unit,
            }

    except RecipeNotFound:
        raise
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to calculate cost for recipe {recipe_id}", e)


def _calculate_recipe_cost_recursive(recipe_id: int, session, visited: set = None) -> Dict:
    """
    Internal helper for recursive cost calculation.

    Args:
        recipe_id: Recipe ID
        session: Database session
        visited: Set of visited recipe IDs (cycle protection)

    Returns:
        {"total_cost": float}
    """
    if visited is None:
        visited = set()

    if recipe_id in visited:
        return {"total_cost": 0.0}  # Prevent infinite loop

    visited.add(recipe_id)

    recipe = session.query(Recipe).filter_by(id=recipe_id).first()
    if not recipe:
        return {"total_cost": 0.0}

    # Direct ingredient cost
    direct_cost = 0.0
    for ri in recipe.recipe_ingredients:
        direct_cost += ri.calculate_cost()

    # Component costs
    component_cost = 0.0
    components = session.query(RecipeComponent).filter_by(recipe_id=recipe_id).all()

    for comp in components:
        comp_result = _calculate_recipe_cost_recursive(comp.component_recipe_id, session, visited.copy())
        component_cost += comp.quantity * comp_result["total_cost"]

    return {"total_cost": direct_cost + component_cost}
```

---

### Subtask T024 – Modify Recipe.calculate_cost() or add component-aware method

**Purpose**: Decide whether to modify existing method or keep separate function.

**Decision**: Keep existing `Recipe.calculate_cost()` unchanged for backward compatibility. Add a new property or method for component-aware cost.

**Steps**:
1. Add `calculate_cost_with_components()` method to Recipe model (optional)
2. Or rely on service function `calculate_total_cost_with_components()`

**Files**: `src/models/recipe.py` (if adding method)

**Recommendation**: Use service function for complex calculation, keep model method simple.

**Optional Model Enhancement**:
```python
# In Recipe class
def calculate_cost_with_components(self) -> float:
    """
    Calculate total cost including sub-recipe costs.

    Note: This requires all relationships to be loaded.
    For detached instances, use recipe_service.calculate_total_cost_with_components().
    """
    # Direct ingredients
    total = self.calculate_cost()

    # Components
    for comp in self.recipe_components:
        if comp.component_recipe:
            total += comp.quantity * comp.component_recipe.calculate_cost_with_components()

    return total
```

---

### Subtask T025 – Modify get_recipe_with_costs() to include component breakdown

**Purpose**: Extend existing cost breakdown to include components.

**Steps**:
1. Find existing `get_recipe_with_costs()` function
2. Add component cost breakdown to returned dictionary
3. Update total_cost to include components

**Files**: `src/services/recipe_service.py`

**Code** (modifications to existing function):
```python
def get_recipe_with_costs(recipe_id: int) -> Dict:
    """
    Get recipe with detailed cost breakdown.
    ...
    """
    try:
        with session_scope() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()

            if not recipe:
                raise RecipeNotFound(recipe_id)

            # ... existing ingredient cost calculation ...

            # Add component costs
            component_costs = []
            total_component_cost = 0.0

            for comp in recipe.recipe_components:
                # Get component recipe cost recursively
                comp_total_cost = _calculate_recipe_cost_recursive(
                    comp.component_recipe_id, session
                )["total_cost"]

                comp_cost = comp.quantity * comp_total_cost

                component_costs.append({
                    "component_recipe": comp.component_recipe,
                    "quantity": comp.quantity,
                    "notes": comp.notes,
                    "unit_cost": comp_total_cost,
                    "total_cost": comp_cost,
                })

                total_component_cost += comp_cost

            # Update totals
            direct_ingredient_cost = recipe.calculate_cost()
            total_cost = direct_ingredient_cost + total_component_cost
            cost_per_unit = total_cost / recipe.yield_quantity if recipe.yield_quantity > 0 else 0.0

            return {
                "recipe": recipe,
                "total_cost": total_cost,
                "cost_per_unit": cost_per_unit,
                "ingredients": ingredient_costs,  # existing
                "components": component_costs,  # NEW
                "direct_ingredient_cost": direct_ingredient_cost,  # NEW
                "total_component_cost": total_component_cost,  # NEW
            }
    # ... error handling ...
```

---

### Subtask T026 – Add unit tests for ingredient aggregation

**Purpose**: Verify aggregation works correctly across hierarchy.

**Files**: `src/tests/services/test_recipe_service.py`

**Test Cases**:
```python
def test_get_aggregated_ingredients_single_recipe():
    """Aggregation of recipe with no components."""
    recipe = create_test_recipe_with_ingredients("Simple", [
        ("Flour", 2.0, "cups"),
        ("Sugar", 1.0, "cups"),
    ])

    result = get_aggregated_ingredients(recipe.id)

    assert len(result) == 2
    flour = next(i for i in result if i["ingredient_name"] == "Flour")
    assert flour["total_quantity"] == 2.0
    assert flour["unit"] == "cups"


def test_get_aggregated_ingredients_with_component():
    """Aggregation includes component ingredients."""
    child = create_test_recipe_with_ingredients("Child", [
        ("Butter", 0.5, "cups"),
    ])
    parent = create_test_recipe_with_ingredients("Parent", [
        ("Flour", 2.0, "cups"),
    ])
    add_recipe_component(parent.id, child.id, quantity=2.0)

    result = get_aggregated_ingredients(parent.id)

    # Should have Flour (2 cups) and Butter (0.5 * 2 = 1 cup)
    assert len(result) == 2
    butter = next(i for i in result if i["ingredient_name"] == "Butter")
    assert butter["total_quantity"] == 1.0  # 0.5 * 2


def test_get_aggregated_ingredients_same_ingredient_combined():
    """Same ingredient from parent and child should combine."""
    child = create_test_recipe_with_ingredients("Child", [
        ("Flour", 1.0, "cups"),
    ])
    parent = create_test_recipe_with_ingredients("Parent", [
        ("Flour", 2.0, "cups"),
    ])
    add_recipe_component(parent.id, child.id, quantity=1.0)

    result = get_aggregated_ingredients(parent.id)

    # Should have Flour 3 cups (2 + 1)
    assert len(result) == 1
    flour = result[0]
    assert flour["total_quantity"] == 3.0
    assert len(flour["sources"]) == 2


def test_get_aggregated_ingredients_3_levels():
    """Aggregation works across 3 levels."""
    grandchild = create_test_recipe_with_ingredients("Grandchild", [
        ("Salt", 1.0, "tsp"),
    ])
    child = create_test_recipe_with_ingredients("Child", [
        ("Butter", 1.0, "cups"),
    ])
    parent = create_test_recipe_with_ingredients("Parent", [
        ("Flour", 2.0, "cups"),
    ])

    add_recipe_component(child.id, grandchild.id, quantity=2.0)
    add_recipe_component(parent.id, child.id, quantity=3.0)

    result = get_aggregated_ingredients(parent.id)

    # Flour: 2 cups (direct)
    # Butter: 1 * 3 = 3 cups
    # Salt: 1 * 2 * 3 = 6 tsp
    salt = next(i for i in result if i["ingredient_name"] == "Salt")
    assert salt["total_quantity"] == 6.0


def test_get_aggregated_ingredients_with_multiplier():
    """Multiplier scales all quantities."""
    recipe = create_test_recipe_with_ingredients("Simple", [
        ("Flour", 2.0, "cups"),
    ])

    result = get_aggregated_ingredients(recipe.id, multiplier=2.0)

    flour = result[0]
    assert flour["total_quantity"] == 4.0  # 2 * 2
```

---

### Subtask T027 – Add unit tests for cost calculation with 1, 2, 3 level hierarchies

**Purpose**: Verify cost calculation is correct at each level.

**Files**: `src/tests/services/test_recipe_service.py`

**Test Cases**:
```python
def test_calculate_cost_single_recipe():
    """Cost of recipe with no components."""
    # Setup recipe with known ingredient costs
    recipe = create_test_recipe_with_priced_ingredients("Simple", [
        # (ingredient_name, qty, unit, cost_per_unit)
        ("Flour", 2.0, "cups", 0.50),  # $1.00
        ("Sugar", 1.0, "cups", 0.75),  # $0.75
    ])

    result = calculate_total_cost_with_components(recipe.id)

    assert result["direct_ingredient_cost"] == pytest.approx(1.75, 0.01)
    assert result["total_component_cost"] == 0.0
    assert result["total_cost"] == pytest.approx(1.75, 0.01)


def test_calculate_cost_with_component():
    """Cost includes component cost × quantity."""
    child = create_test_recipe_with_priced_ingredients("Child", [
        ("Butter", 1.0, "cups", 2.00),  # $2.00
    ])
    parent = create_test_recipe_with_priced_ingredients("Parent", [
        ("Flour", 2.0, "cups", 0.50),  # $1.00
    ])

    add_recipe_component(parent.id, child.id, quantity=2.0)

    result = calculate_total_cost_with_components(parent.id)

    # Direct: $1.00, Components: $2.00 * 2 = $4.00, Total: $5.00
    assert result["direct_ingredient_cost"] == pytest.approx(1.00, 0.01)
    assert result["total_component_cost"] == pytest.approx(4.00, 0.01)
    assert result["total_cost"] == pytest.approx(5.00, 0.01)
    assert len(result["component_costs"]) == 1
    assert result["component_costs"][0]["quantity"] == 2.0


def test_calculate_cost_3_levels():
    """Cost calculation works across 3 levels."""
    grandchild = create_test_recipe_with_priced_ingredients("Grandchild", [
        ("Salt", 1.0, "tsp", 0.10),  # $0.10
    ])
    child = create_test_recipe_with_priced_ingredients("Child", [
        ("Butter", 1.0, "cups", 2.00),  # $2.00
    ])
    parent = create_test_recipe_with_priced_ingredients("Parent", [
        ("Flour", 1.0, "cups", 0.50),  # $0.50
    ])

    add_recipe_component(child.id, grandchild.id, quantity=1.0)
    add_recipe_component(parent.id, child.id, quantity=2.0)

    result = calculate_total_cost_with_components(parent.id)

    # Child cost: $2.00 + $0.10 = $2.10
    # Parent cost: $0.50 + ($2.10 * 2) = $0.50 + $4.20 = $4.70
    assert result["total_cost"] == pytest.approx(4.70, 0.01)


def test_calculate_cost_per_unit():
    """Cost per unit is total / yield."""
    recipe = create_test_recipe_with_priced_ingredients(
        "Cookies",
        [("Flour", 2.0, "cups", 0.50)],  # $1.00 total
        yield_quantity=24,
        yield_unit="cookies"
    )

    result = calculate_total_cost_with_components(recipe.id)

    # $1.00 / 24 cookies ≈ $0.042 per cookie
    assert result["cost_per_unit"] == pytest.approx(1.00 / 24, 0.001)


def test_calculate_cost_missing_prices():
    """Recipe with missing prices returns partial cost."""
    # Ingredient without purchase history returns 0 cost
    recipe = create_test_recipe_with_ingredients("NoPrice", [
        ("Mystery Ingredient", 1.0, "cups"),  # No price data
    ])

    result = calculate_total_cost_with_components(recipe.id)

    # Should not error, just return 0
    assert result["total_cost"] == 0.0
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Infinite recursion | Visited set prevents re-processing same recipe |
| Cost inaccurate | Tests with known costs verify calculations |
| Unit mismatch | Aggregation key includes unit; no cross-unit combining |

## Definition of Done Checklist

- [ ] `get_aggregated_ingredients()` collects all ingredients recursively
- [ ] `calculate_total_cost_with_components()` returns correct costs
- [ ] `get_recipe_with_costs()` includes component breakdown
- [ ] Aggregation multiplies by batch quantities correctly
- [ ] All tests passing for 1, 2, and 3 level hierarchies
- [ ] Missing price data handled gracefully

## Review Guidance

- Verify multiplication chain for deep hierarchies
- Check aggregation combines same (ingredient, unit) pairs
- Confirm cost breakdown structure matches contract
- Test with real recipes via UI after integration

## Activity Log

- 2025-12-09T00:00:00Z – system – lane=planned – Prompt created.
- 2025-12-09T13:41:48Z – claude – shell_pid=90571 – lane=doing – Started implementation
- 2025-12-09T13:53:03Z – claude – shell_pid=91798 – lane=for_review – Completed implementation - 14 new tests, all 537 pass
- 2025-12-09T17:55:30Z – claude-reviewer – shell_pid=98957 – lane=done – Code review: APPROVED - Cost calculation and ingredient aggregation implemented with tests
