# Research: Nested Recipes (Sub-Recipe Components)

**Feature**: 012-nested-recipes
**Date**: 2025-12-09
**Status**: Complete

## Executive Summary

Research confirms that the nested recipes feature can be implemented using existing codebase patterns. The `Composition` model provides a proven junction table pattern with constraints. The `recipe_service.py` has established CRUD and cost calculation patterns to extend.

## Key Decisions

### D1: Junction Table Pattern

**Decision**: Use simple junction table (`RecipeComponent`) linking parent recipe to child recipe.

**Rationale**:
- Follows existing `RecipeIngredient` pattern in codebase
- Simpler than polymorphic approach (unlike `Composition` which handles multiple component types)
- Recipe-to-recipe relationship is single-purpose, not polymorphic

**Alternatives Considered**:
- Extend `Composition` model to include recipes - Rejected: Composition is for FinishedGood/Package assemblies, not recipes
- Add self-referential FK on Recipe - Rejected: Need quantity/notes per component relationship

**Evidence**: `src/models/recipe.py:122-169` shows RecipeIngredient junction pattern; `src/models/composition.py:33-130` shows constraint patterns

---

### D2: Circular Reference Detection

**Decision**: Check on save via tree traversal; no pre-computed depth field.

**Rationale**:
- Single-user desktop app with <100 recipes makes O(n) traversal instant
- Simpler implementation without maintaining computed fields
- User confirmed this approach during planning

**Alternatives Considered**:
- Pre-computed `depth` field - Rejected: Adds complexity of keeping depth updated when hierarchy changes
- Database-level CTE/recursive query - Rejected: SQLite CTE support varies; Python traversal is portable

**Evidence**: Planning interrogation Q1 answer: "A" (check on save)

---

### D3: Quantity Model

**Decision**: Batch multiplier (float) only, not volume/weight units.

**Rationale**:
- User confirmed during planning that batch multipliers are sufficient
- Simpler UI (single number field vs. quantity + unit dropdown)
- Recipes have their own yields; multiplier scales the whole batch

**Alternatives Considered**:
- Flexible units (cups, batches) - Rejected: User explicitly chose simpler batch multiplier approach

**Evidence**: Planning interrogation Q1 answer: "A" (batch multiplier only)

---

### D4: Maximum Nesting Depth

**Decision**: Enforce 3-level maximum (Parent → Child → Grandchild).

**Rationale**:
- User confirmed 3 levels is sufficient for real-world baking scenarios
- Prevents excessive complexity
- Easy to validate during circular reference check

**Alternatives Considered**:
- Unlimited depth - Rejected: Risk of performance issues and user confusion
- Single level only - Rejected: Too limiting for complex recipes

**Evidence**: Planning interrogation Q2 answer: "B, 3 levels"

---

### D5: Import/Export Identifier

**Decision**: Use recipe name (not slug) for component references in export/import.

**Rationale**:
- Recipe model doesn't have a slug field
- Existing import_export_service uses recipe name for recipe imports
- Consistent with current patterns

**Alternatives Considered**:
- Add slug to Recipe model - Rejected: Out of scope; would require migration and changes across codebase
- Use recipe ID - Rejected: IDs are database-specific, not portable

**Evidence**: `src/models/recipe.py` - no slug field present; `src/services/import_export_service.py:276-315` uses recipe name

---

### D6: Cost Calculation Approach

**Decision**: Recursive calculation: `total_cost = sum(ingredient_costs) + sum(component.recipe.calculate_cost() * component.quantity)`

**Rationale**:
- Follows existing `Recipe.calculate_cost()` pattern
- Naturally handles depth via recursion
- Cost always reflects current sub-recipe costs (no stale cached values)

**Alternatives Considered**:
- Cache computed costs - Rejected: Adds staleness risk and cache invalidation complexity
- Iterative with stack - Rejected: Recursion is clearer for tree traversal

**Evidence**: `src/models/recipe.py:76-89` shows existing calculate_cost pattern

---

### D7: Shopping List Aggregation Location

**Decision**: Add method to `recipe_service.py` (not separate service).

**Rationale**:
- User confirmed during planning
- Keeps recipe logic centralized
- Shopping list is a projection of recipe data, not a separate domain

**Alternatives Considered**:
- Dedicated `shopping_list_service.py` - Rejected: User preferred recipe_service; can refactor later if needed

**Evidence**: Planning interrogation Q2 answer: "A" (recipe service)

---

### D8: UI Layout

**Decision**: Single scrollable form with two sections (Ingredients, then Sub-Recipes).

**Rationale**:
- User confirmed this matches existing UI patterns
- Simpler than tabbed interface
- Clear visual separation between ingredient types

**Alternatives Considered**:
- Tabbed interface - Rejected: User chose single scrollable form
- Collapsible sections - Rejected: User chose single scrollable form

**Evidence**: Planning interrogation Q3 answer: "B" (single scrollable form)

---

## Codebase Patterns Identified

### Pattern 1: Junction Table with Relationships

**Location**: `src/models/recipe.py:122-169`

```python
class RecipeIngredient(BaseModel):
    __tablename__ = "recipe_ingredients"
    recipe_id = Column(Integer, ForeignKey("recipes.id", ondelete="CASCADE"))
    ingredient_id = Column(Integer, ForeignKey("ingredients.id", ondelete="RESTRICT"))
    quantity = Column(Float, nullable=False)
    unit = Column(String(50), nullable=False)
    notes = Column(String(500), nullable=True)

    recipe = relationship("Recipe", back_populates="recipe_ingredients")
    ingredient = relationship("Ingredient", back_populates="recipe_ingredients")
```

**Applicability**: RecipeComponent will follow this pattern with recipe-to-recipe FK.

---

### Pattern 2: Constraint Checking

**Location**: `src/models/composition.py:94-129`

```python
__table_args__ = (
    CheckConstraint("component_quantity > 0", name="ck_composition_component_quantity_positive"),
    CheckConstraint("assembly_id != finished_good_id", name="ck_composition_no_self_reference"),
    UniqueConstraint("assembly_id", "finished_good_id", name="uq_composition_assembly_good"),
)
```

**Applicability**: RecipeComponent needs:
- `component_quantity > 0` constraint
- `recipe_id != component_recipe_id` constraint (no self-reference)
- Unique constraint on `(recipe_id, component_recipe_id)`

---

### Pattern 3: Cascade Delete

**Location**: `src/models/recipe.py:57-62`

```python
recipe_ingredients = relationship(
    "RecipeIngredient",
    back_populates="recipe",
    cascade="all, delete-orphan",
)
```

**Applicability**: RecipeComponent should cascade delete when parent recipe deleted, but RESTRICT when component recipe would be deleted (prevents orphaning).

---

### Pattern 4: Service CRUD Pattern

**Location**: `src/services/recipe_service.py:319-377`

```python
def add_ingredient_to_recipe(recipe_id, ingredient_id, quantity, unit, notes=None):
    # Validation
    if quantity <= 0:
        raise ValidationError(["Quantity must be positive"])
    # Verify entities exist
    with session_scope() as session:
        recipe = session.query(Recipe).filter_by(id=recipe_id).first()
        if not recipe:
            raise RecipeNotFound(recipe_id)
        # Create junction record
        ...
```

**Applicability**: `add_recipe_component()` will follow this pattern with additional circular reference validation.

---

## Open Questions

None - all questions resolved during planning interrogation.

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Circular reference edge cases | HIGH | Comprehensive test suite covering direct, indirect, and deep cycles |
| Recursive cost calculation stack overflow | LOW | 3-level limit prevents deep recursion; Python default recursion limit is 1000 |
| Import/export ordering | MEDIUM | Import sub-recipes before parent recipes; detect and skip missing references |

## Sources

| ID | Source | Type | Location |
|----|--------|------|----------|
| S1 | Recipe model | Code | `src/models/recipe.py` |
| S2 | Composition model | Code | `src/models/composition.py` |
| S3 | Recipe service | Code | `src/services/recipe_service.py` |
| S4 | Import/export service | Code | `src/services/import_export_service.py` |
| S5 | Planning interrogation | User input | Confirmed decisions D2-D4, D7-D8 |
| S6 | Feature spec | Document | `kitty-specs/012-nested-recipes/spec.md` |
