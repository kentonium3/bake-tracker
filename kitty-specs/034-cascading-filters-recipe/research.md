# Research: Cascading Filters & Recipe Integration

**Feature**: 034-cascading-filters-recipe
**Date**: 2026-01-02
**Status**: Complete

## Executive Summary

Research into the codebase reveals that cascading filter infrastructure EXISTS in both `products_tab.py` and `inventory_tab.py`, but the gap analysis reported it as broken. Recipe integration is already implemented using `IngredientTreeWidget` with `leaf_only=True`. The "Clear Filters" button exists in `ingredients_tab.py` but not in products/inventory tabs.

---

## Decision Log

### Decision 1: Cascading Filter Approach

**Decision**: Debug/fix existing cascading filter code rather than rewrite

**Rationale**:
- Code structure in `products_tab.py:479-554` and `inventory_tab.py:426-500` appears correct
- Event handlers are bound: `_on_l0_filter_change`, `_on_l1_filter_change`
- Cascading logic populates child dropdowns correctly in code
- Bug is likely subtle (timing, state, or service layer issue)

**Alternatives Considered**:
- Rewrite from scratch: Rejected - existing code is well-structured
- Create shared CascadingFilterWidget: Deferred - fix first, refactor if pattern is identical

### Decision 2: Recipe Integration Verification Only

**Decision**: Verify existing `IngredientTreeWidget` implementation, no new development

**Rationale**:
- Recipe form already uses `IngredientTreeWidget` with `leaf_only=True` (`recipe_form.py:95`)
- Tree browser approach is MORE intuitive than cascading dropdowns for ingredient selection
- Just need to verify L2-only enforcement works correctly

**Alternatives Considered**:
- Replace with cascading dropdowns: Rejected - tree browser is superior UX for selection
- Add cascading filters as supplementary: Rejected - would duplicate functionality

### Decision 3: Add Clear Filters Button

**Decision**: Add "Clear Filters" button to both Products and Inventory tabs

**Rationale**:
- `ingredients_tab.py` already has this pattern (lines 163-170, 582-588)
- User requested this functionality in spec
- Simple UX improvement for filter reset

---

## Code Analysis

### Existing Cascading Filter Implementation

**Location**: `src/ui/products_tab.py:479-554`

```python
def _on_l0_filter_change(self, value: str):
    """Handle L0 (category) filter change - cascade to L1."""
    if value == "All Categories":
        # Reset L1 and L2
        self._l1_map = {}
        self._l2_map = {}
        self.l1_filter_dropdown.configure(values=["All"], state="disabled")
        ...
    elif value in self._l0_map:
        # Populate L1 with children of selected L0
        l0_id = self._l0_map[value].get("id")
        subcategories = ingredient_hierarchy_service.get_children(l0_id)
        self._l1_map = {sub.get("display_name", "?"): sub for sub in subcategories}
        ...
```

**Observation**: Code looks structurally correct. Bug may be in:
1. `ingredient_hierarchy_service.get_children()` returning wrong data
2. Event timing issues
3. State not syncing with UI properly

### Recipe Integration Implementation

**Location**: `src/ui/forms/recipe_form.py:32-100`

```python
class IngredientSelectionDialog(ctk.CTkToplevel):
    """Dialog for selecting an ingredient using the tree widget (Feature 031)."""

    def _create_tree_widget(self):
        from src.ui.widgets.ingredient_tree_widget import IngredientTreeWidget
        self.tree_widget = IngredientTreeWidget(
            tree_frame,
            on_select_callback=self._on_tree_select,
            leaf_only=True,  # Only allow leaf selection for recipes
            ...
        )
```

**Observation**: Already uses tree-based selection with leaf-only enforcement.

### Clear Filters Pattern

**Location**: `src/ui/ingredients_tab.py:163-170, 582-588`

```python
# Button creation
clear_button = ctk.CTkButton(
    filter_frame,
    text="Clear",
    command=self._clear_filters,
    width=60,
)
clear_button.grid(row=0, column=3)

# Handler
def _clear_filters(self):
    """Clear all filters and refresh display."""
    self.search_var.set("")
    self.level_filter_var.set("All Levels")
    ...
```

**Observation**: Products/Inventory tabs missing this button.

---

## Parallelization Strategy

Based on file analysis, work can be safely parallelized:

| Work Package | Agent | Files Modified | Safe to Parallelize |
|--------------|-------|----------------|---------------------|
| WP1: Products tab fix + Clear button | Claude | `products_tab.py` | Yes - independent file |
| WP2: Inventory tab fix + Clear button | Gemini | `inventory_tab.py` | Yes - identical pattern |
| WP3: Recipe verification + tests | Either | `recipe_form.py`, tests | Yes - read-only verification |

**File Boundaries**:
- Claude: `src/ui/products_tab.py` only
- Gemini: `src/ui/inventory_tab.py` only
- Tests: `src/tests/` (either agent, after fixes)

---

## Open Questions

1. **What exactly is broken in cascading filters?** - Gap analysis says "L1 doesn't filter based on L0" but code looks correct. Need manual testing or debugging to identify actual bug.

2. **Is `ingredient_hierarchy_service.get_children()` working correctly?** - May need to add debug logging to verify service returns expected data.

3. **Are there re-entry guards needed?** - Event handler loops are mentioned in spec. Current code may lack guards.

---

## Files to Modify

1. `src/ui/products_tab.py` - Fix cascading, add Clear button
2. `src/ui/inventory_tab.py` - Apply same fixes
3. `src/ui/forms/recipe_form.py` - Verify only (if issues found, fix)
4. `src/tests/ui/test_cascading_filters.py` - New test file (if UI tests exist)

## Files to Verify

1. `src/services/ingredient_hierarchy_service.py` - Verify `get_children()` works
2. `src/ui/widgets/ingredient_tree_widget.py` - Verify `leaf_only` enforcement
