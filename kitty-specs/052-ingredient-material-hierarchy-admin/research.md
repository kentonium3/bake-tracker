# Research: Ingredient & Material Hierarchy Admin

**Feature**: 052-ingredient-material-hierarchy-admin
**Date**: 2026-01-14

## Research Questions

### RQ1: How is the ingredient hierarchy currently implemented?

**Decision**: Self-referential 3-level hierarchy with `parent_ingredient_id` and `hierarchy_level` fields.

**Rationale**: Feature 031 implemented ingredient hierarchy with:
- `parent_ingredient_id`: FK to parent ingredient (NULL for L0 roots)
- `hierarchy_level`: 0=root, 1=mid-tier, 2=leaf (usable in recipes)
- `children` relationship: dynamic lazy-loaded query for child ingredients
- `get_ancestors()`: method to get path to root
- `is_leaf` property: returns True if hierarchy_level == 2

**Alternatives considered**: None - using existing implementation.

**Source**: `src/models/ingredient.py` lines 76-84, 131-136, 244-287

---

### RQ2: How is the material hierarchy currently implemented?

**Decision**: Separate models for each level with FK relationships (MaterialCategory → MaterialSubcategory → Material).

**Rationale**: Feature 047 implemented materials with three distinct models:
- `MaterialCategory`: Top-level (e.g., "Ribbons", "Boxes")
- `MaterialSubcategory`: Mid-level, FK to category (e.g., "Satin", "Window Boxes")
- `Material`: Leaf-level, FK to subcategory (e.g., "Red Satin 1-inch")

Unlike ingredients (self-referential), materials use explicit junction models.

**Alternatives considered**: None - using existing implementation.

**Source**: `src/models/material.py`, `src/models/material_category.py`, `src/models/material_subcategory.py`

---

### RQ3: What existing services can be extended?

**Decision**: Extend existing hierarchy validation patterns; create new services for admin operations.

**Rationale**: Existing services provide patterns:
- `ingredient_service.py`: CRUD operations, can add hierarchy admin methods
- `material_service.py`: Basic CRUD, needs hierarchy query methods
- Validation patterns exist for uniqueness, FK constraints

New services needed:
- `ingredient_hierarchy_service.py`: L2-only queries, parent resolution, add/rename/reparent
- `material_hierarchy_service.py`: Material-only queries, parent resolution, add/rename/reparent
- `hierarchy_admin_service.py`: Shared logic (usage counts, cycle detection)

**Alternatives considered**: Single unified hierarchy service - rejected because Ingredient and Material models differ significantly (self-referential vs explicit junction tables).

---

### RQ4: What UI widget for tree display?

**Decision**: Use CustomTkinter CTkTreeview or standard tkinter.ttk.Treeview.

**Rationale**:
- `ttk.Treeview` is the standard tree widget in Tkinter
- CustomTkinter wraps ttk widgets with modern styling
- Supports expand/collapse, selection, scrolling
- Existing pattern in `ingredients_tab.py` uses CTkScrollableFrame for lists

**Best practices**:
- Load tree data lazily (expand on demand) for performance
- Cache usage counts to avoid repeated queries
- Use tag-based styling for different node types

**Source**: CustomTkinter documentation, existing UI patterns

---

### RQ5: How to handle rename propagation?

**Decision**: FK relationships automatically propagate display changes; no additional work needed.

**Rationale**:
- Products reference ingredients via `ingredient_id` FK
- Recipes reference ingredients via FK
- Renaming updates the `display_name` field; FK unchanged
- All displays dynamically resolve via FK → name is always current
- Historical snapshots (RecipeSnapshot) store denormalized names and are unaffected

**Alternatives considered**: None - FK-based design handles this inherently.

---

### RQ6: How to prevent hierarchy cycles during reparent?

**Decision**: Validate that new parent is not a descendant of the item being moved.

**Rationale**:
- Before reparenting, check `get_descendants()` of the item
- If proposed new parent is in descendants list, reject
- For Materials, cycle is impossible (fixed 3-level structure)

**Implementation**:
```python
def can_reparent(item, new_parent):
    descendants = item.get_descendants()
    return new_parent not in descendants
```

---

## Summary

All research questions resolved. Key findings:
1. Ingredient hierarchy uses self-referential model; Material hierarchy uses explicit models
2. Both share 3-level structure but different implementations → separate services needed
3. UI can use standard ttk.Treeview with CustomTkinter styling
4. FK-based design handles rename propagation automatically
5. Cycle detection implemented via descendant check
