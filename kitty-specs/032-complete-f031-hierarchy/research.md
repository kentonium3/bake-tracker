# Research: Complete F031 Hierarchy UI Implementation

**Feature**: 032-complete-f031-hierarchy
**Date**: 2025-12-31
**Status**: Complete

## Summary

This feature completes the UI implementation for F031 Ingredient Hierarchy. The backend (schema, services, import/export) is already complete. This research documents the existing patterns and available service functions for the UI implementation.

---

## Decision 1: Cascading Dropdown Pattern

**Decision**: Use the same withdraw/deiconify pattern from `add_product_dialog.py` for modal dialogs with cascading dropdowns.

**Rationale**: The Product edit form already handles cascading dropdowns for hierarchy selection. The pattern includes:
- `withdraw()` to hide window during UI construction
- Build all UI elements while hidden
- `deiconify()` after UI is complete
- `wait_visibility()` with try/except for race conditions
- `grab_release()` on parent before opening child dialogs

**Alternatives Considered**:
- Direct show/grab pattern: Causes modal conflicts and unresponsive dialogs
- Custom dialog framework: Over-engineering for this use case

**Evidence**: Previous session debugging confirmed this pattern resolves modal dialog issues.

---

## Decision 2: Service Functions to Use

**Decision**: Use existing `ingredient_hierarchy_service.py` functions.

**Available Functions**:
| Function | Purpose | Use Case |
|----------|---------|----------|
| `get_root_ingredients()` | Get all L0 categories | Populate L0 dropdown |
| `get_children(parent_id)` | Get direct children | Cascade L1 from L0, L2 from L1 |
| `get_ancestors(ingredient_id)` | Get parent chain | Pre-populate dropdowns when editing |
| `get_ingredients_by_level(level)` | Filter by level | Hierarchy level filter |
| `get_leaf_ingredients()` | Get L2 only | Validate product/recipe assignments |
| `get_ingredient_by_id(id)` | Get single ingredient | Lookup for display |

**Rationale**: These functions are already tested and working per F031 specification.

**Evidence**: Grep of `src/services/ingredient_hierarchy_service.py` confirms all functions exist with proper session handling.

---

## Decision 3: Grid Column Layout

**Decision**: Replace single "Category" column with three columns: "Root (L0)", "Subcategory (L1)", "Name".

**Rationale**:
- Matches the three-tier hierarchy structure
- Allows sorting by any level
- Provides clear visual representation of taxonomy

**Implementation Notes**:
- Use `get_ancestors()` to populate L0/L1 columns for each ingredient
- Cache ancestors during display refresh to avoid N+1 queries
- Show dash ("—") for empty columns (e.g., L0 ingredients have no parent columns)

---

## Decision 4: Hierarchy Level Filter

**Decision**: Use simple level filter dropdown with options: All Levels, Root Categories (L0), Subcategories (L1), Leaf Ingredients (L2).

**Rationale**:
- Simpler than cascading filter dropdowns
- Recommended in bug spec as "Option B" for Phase 1
- Can upgrade to cascading filters in future enhancement

**Alternatives Considered**:
- Cascading hierarchy filters (L0 → L1 → L2): More complex, deferred to future enhancement
- Tree view only: Loses flat view benefits for quick scanning

---

## Decision 5: Leaf-Only Validation

**Decision**: Product and recipe ingredient selectors should only show L2 (leaf) ingredients.

**Rationale**:
- Products must link to specific ingredients, not categories
- Recipes use specific ingredients for accurate costing
- Service layer already has `get_leaf_ingredients()` function

**Implementation Notes**:
- Replace `get_all_ingredients()` with `get_leaf_ingredients()` in product/recipe forms
- Add validation error if somehow a non-leaf is selected

---

## Files to Modify

### High Priority (P1 User Stories)

| File | Changes Needed |
|------|----------------|
| `src/ui/ingredients_tab.py` | Replace category column with L0/L1/Name columns; replace category filter with level filter; update `_update_ingredient_display()` to show hierarchy |
| `src/ui/ingredients_tab.py` (IngredientFormDialog) | Replace category dropdown with cascading L0/L1 dropdowns; add level selection for new ingredients |

### Medium Priority (P2 User Stories)

| File | Changes Needed |
|------|----------------|
| `src/ui/products_tab.py` | Replace category filter with hierarchy filters; show ingredient path in grid |
| `src/ui/inventory_tab.py` | Replace category column/filter with hierarchy; show ingredient path |
| `src/ui/forms/inventory_form.py` or similar | Show read-only hierarchy labels |

### Already Complete

| File | Status |
|------|--------|
| `src/ui/forms/add_product_dialog.py` | Uses cascading hierarchy selection (reference implementation) |
| `src/services/ingredient_hierarchy_service.py` | All hierarchy functions implemented |

---

## Open Questions / Risks

1. **Performance**: Building hierarchy cache for 400+ ingredients on every display refresh could be slow. Mitigation: Cache at tab level, invalidate on ingredient changes.

2. **Edit form complexity**: Supporting creation of L0, L1, and L2 ingredients in one form requires conditional UI logic. Mitigation: Use radio button for "ingredient type" with appropriate dropdown visibility.

3. **Backward compatibility**: Legacy `category` field still populated but ignored. Mitigation: UI ignores it; field remains for potential rollback.

---

## References

- Bug Specification: `docs/bugs/BUG_F031_incomplete_hierarchy_ui.md`
- Original F031 Spec: `docs/design/F031_ingredient_hierarchy.md`
- Reference Implementation: `src/ui/forms/add_product_dialog.py`
- Hierarchy Service: `src/services/ingredient_hierarchy_service.py`
