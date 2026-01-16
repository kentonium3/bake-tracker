# Research: Workflow-Aligned Navigation Cleanup

**Feature**: 055-workflow-aligned-navigation-cleanup
**Date**: 2026-01-15

---

## Codebase Analysis

### 1. Mode Navigation System

**Files**: `src/ui/mode_manager.py`, `src/ui/main_window.py`

**Current State**:
- `MODE_ORDER = ["CATALOG", "PLAN", "PURCHASE", "MAKE", "OBSERVE"]`
- Keyboard shortcuts mapped by index: Ctrl+1 = CATALOG, Ctrl+5 = OBSERVE
- Mode bar buttons created in `main_window.py` lines 136-155 via `mode_configs` list
- Default mode is OBSERVE (correct)

**Changes Required**:
- Update MODE_ORDER to `["OBSERVE", "CATALOG", "PLAN", "PURCHASE", "MAKE", "DELIVER"]`
- Update `mode_configs` list in main_window.py
- Add mode_tab_state entry for "DELIVER"
- Add DELIVER mode class with placeholder content
- Update grid columns from 5 to 6 in mode_bar

**Key Code Locations**:
- `mode_manager.py:35` - MODE_ORDER constant
- `mode_manager.py:41-47` - mode_tab_state initialization
- `main_window.py:132-133` - mode_bar grid columns (currently 5)
- `main_window.py:136-142` - mode_configs list

---

### 2. Catalog Mode Structure

**File**: `src/ui/modes/catalog_mode.py`

**Current State**:
- Flat CTkTabview with 7 tabs: Ingredients, Products, Recipes, Finished Units, Finished Goods (placeholder), Packages, Materials
- Each tab contains a single widget

**Target State** (from spec):
- 4 top-level groups with nested sub-tabs
- Pattern: Copy MaterialsTab approach (internal CTkTabview)

**Implementation Approach**:

Option A (Recommended): Create wrapper tabs with internal sub-tabs
- Create IngredientsGroupTab containing: Ingredient Catalog, Food Products
- Keep MaterialsTab as-is (already has internal structure)
- Create RecipesGroupTab containing: Recipes Catalog, Finished Units
- Create PackagingGroupTab containing: Finished Goods (Food), Finished Goods (Bundles), Packages

Option B: Use CTkSegmentedButton for group navigation
- More complex, not matching existing Materials pattern

**Decision**: Use Option A - matches MaterialsTab pattern for consistency

---

### 3. Materials Tab Pattern (Template for Other Groups)

**File**: `src/ui/materials_tab.py`

**Pattern**:
```python
class MaterialsTab(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self._create_title()
        self._create_tabview()

    def _create_tabview(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", ...)

        # Add sub-tabs
        self.tabview.add("Materials Catalog")
        self.tabview.add("Material Products")
        self.tabview.add("Material Units")

        # Create inner tab widgets
        catalog_tab = self.tabview.tab("Materials Catalog")
        self.catalog_tab = MaterialsCatalogTab(catalog_tab, self)
```

**Apply to**:
1. IngredientsGroupTab - wraps IngredientsTab + ProductsTab
2. RecipesGroupTab - wraps RecipesTab + FinishedUnitsTab
3. PackagingGroupTab - wraps FinishedGoodsTab (filtered) + PackagesTab

---

### 4. Purchase Mode Tabs

**File**: `src/ui/modes/purchase_mode.py`

**Current Order** (lines 59-80):
1. Shopping Lists (line 60)
2. Purchases (line 68)
3. Inventory (line 76)

**Target Order**:
1. Inventory
2. Purchases
3. Shopping Lists

**Changes Required**:
- Reorder `tabview.add()` calls in `setup_tabs()`
- Update lazy loading order in `activate()`

---

### 5. Tree View in Ingredients Tab

**File**: `src/ui/ingredients_tab.py`

**Current State**:
- View toggle between "Flat" and "Tree" modes (lines 87, 418-449)
- `IngredientTreeWidget` for hierarchical navigation
- Tree container at row 3, hidden by default

**Spec Requirement**: "Remove tree view from Catalog/Inventory"

**Analysis**:
- F052 added Hierarchy Admin window for managing hierarchies
- Tree view in ingredients tab is redundant with Hierarchy Admin
- Removing tree toggle simplifies UI

**Changes Required**:
- Remove `_view_mode` variable and related logic
- Remove `_create_tree_view()` method
- Remove view toggle from filter bar
- Remove `tree_container` and `ingredient_tree` widget
- Remove tree-related event handlers

---

### 6. Top Section / Dashboard

**Files**: `src/ui/dashboards/base_dashboard.py`, `src/ui/dashboards/catalog_dashboard.py`

**Current State** (post-F042):
- Header is 40px height (1-2 lines)
- Shows mode name + inline stats: "CATALOG  413 ingredients - 153 products - 87 recipes"
- Vertical stat widgets were removed by F042

**Spec Requirement**: "Remove broken top section showing CATALOG 0 Ingredients..."

**Analysis**:
- F042 already compacted headers from 13-17 lines to 1-2 lines
- The "0 counts" issue may have been a refresh timing problem
- Current header is minimal (40px)

**Recommendation**:
- Verify current state - if header is already compact, mark FR-4 as already satisfied by F042
- If still wasting space, consider removing dashboard header entirely
- Focus testing on whether counts display correctly

---

### 7. Finished Goods Filtering

**Requirement**: Split into "Finished Goods (Food Only)" and "Finished Goods (Bundles)"

**Analysis**:
- Need to identify how to distinguish food items from bundles
- Check FinishedGood model for `is_bundle` or similar flag

**Research Needed**: Check finished_goods model/service for bundle distinction

---

## Decisions Summary

| Topic | Decision | Rationale |
|-------|----------|-----------|
| Mode order | OBSERVE, CATALOG, PLAN, PURCHASE, MAKE, DELIVER | Matches workflow progression |
| Catalog structure | Nested tabs using Materials pattern | Consistency with existing code |
| Tree view removal | Remove from ingredients_tab | F052 Hierarchy Admin replaces this |
| Top section | Verify F042 fix is sufficient | May already be resolved |
| Finished Goods split | Filter by bundle flag | TBD - need to verify model |

---

## Files to Modify

### Mode Navigation
- `src/ui/mode_manager.py` - MODE_ORDER, mode_tab_state
- `src/ui/main_window.py` - mode_configs, mode_bar grid

### New Files
- `src/ui/modes/deliver_mode.py` - placeholder mode
- `src/ui/tabs/ingredients_group_tab.py` - wrapper for Ingredients + Products
- `src/ui/tabs/recipes_group_tab.py` - wrapper for Recipes + Finished Units
- `src/ui/tabs/packaging_group_tab.py` - wrapper for Finished Goods + Packages

### Modified Files
- `src/ui/modes/catalog_mode.py` - restructure tabs into groups
- `src/ui/modes/purchase_mode.py` - reorder tabs
- `src/ui/ingredients_tab.py` - remove tree view toggle

### Potentially Unchanged
- `src/ui/dashboards/base_dashboard.py` - verify F042 fix is sufficient
- `src/ui/materials_tab.py` - use as reference only
