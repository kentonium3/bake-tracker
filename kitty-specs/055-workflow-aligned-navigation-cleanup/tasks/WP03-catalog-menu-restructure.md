---
id: WP03
title: Catalog Menu Restructure
lane: "done"
agent: null
review_status: null
created_at: 2026-01-15
---

# WP03: Catalog Menu Restructure

**Feature**: 055-workflow-aligned-navigation-cleanup
**Phase**: 3 | **Risk**: Medium
**FR Coverage**: FR-004, FR-005, FR-007, FR-008, FR-009, FR-010
**Depends On**: WP01 (modes must be registered first)

---

## Objective

Restructure Catalog mode from 7 flat tabs into 4 logical groups with nested sub-tabs, following the Materials tab pattern.

---

## Context

### Current State (catalog_mode.py)
Flat CTkTabview with 7 tabs:
- Ingredients
- Products
- Recipes
- Finished Units
- Finished Goods (placeholder)
- Packages
- Materials

### Target State
4 top-level groups with nested tabs:
1. **Ingredients**: Ingredient Catalog, Food Products
2. **Materials**: Material Catalog, Material Units, Material Products (existing)
3. **Recipes**: Recipes Catalog, Finished Units
4. **Packaging**: Finished Goods (Food Only), Finished Goods (Bundles), Packages

### Pattern Reference
Copy `src/ui/materials_tab.py` structure - nested CTkTabview with internal tabs.

---

## Subtasks

- [ ] T007: Create ingredients_group_tab.py
- [ ] T008: Create recipes_group_tab.py
- [ ] T009: Create packaging_group_tab.py with Finished Goods filtering
- [ ] T010: Update catalog_mode.py to use 4 group tabs
- [ ] T011: Update activate() and refresh_all_tabs() methods
- [ ] T012: Verify Finished Goods Food/Bundle filtering

---

## Implementation Details

### T007: Create ingredients_group_tab.py

Create `src/ui/tabs/ingredients_group_tab.py`:

```python
"""Ingredients group tab with nested sub-tabs."""
import customtkinter as ctk
from src.ui.ingredients_tab import IngredientsTab
from src.ui.products_tab import ProductsTab


class IngredientsGroupTab(ctk.CTkFrame):
    """Container for Ingredients and Products tabs."""

    def __init__(self, parent, mode=None):
        super().__init__(parent)
        self.mode = mode
        self._create_tabview()

    def _create_tabview(self):
        """Create nested tabview with sub-tabs."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add sub-tabs
        self.tabview.add("Ingredient Catalog")
        self.tabview.add("Food Products")

        # Create tab widgets
        ingredient_frame = self.tabview.tab("Ingredient Catalog")
        self.ingredients_tab = IngredientsTab(ingredient_frame)
        self.ingredients_tab.pack(fill="both", expand=True)

        product_frame = self.tabview.tab("Food Products")
        self.products_tab = ProductsTab(product_frame)
        self.products_tab.pack(fill="both", expand=True)

    def refresh(self):
        """Refresh all sub-tabs."""
        if hasattr(self, 'ingredients_tab'):
            self.ingredients_tab.refresh()
        if hasattr(self, 'products_tab'):
            self.products_tab.refresh()
```

### T008: Create recipes_group_tab.py

Create `src/ui/tabs/recipes_group_tab.py`:

```python
"""Recipes group tab with nested sub-tabs."""
import customtkinter as ctk
from src.ui.recipes_tab import RecipesTab
from src.ui.finished_units_tab import FinishedUnitsTab


class RecipesGroupTab(ctk.CTkFrame):
    """Container for Recipes and Finished Units tabs."""

    def __init__(self, parent, mode=None):
        super().__init__(parent)
        self.mode = mode
        self._create_tabview()

    def _create_tabview(self):
        """Create nested tabview with sub-tabs."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add sub-tabs
        self.tabview.add("Recipes Catalog")
        self.tabview.add("Finished Units")

        # Create tab widgets
        recipes_frame = self.tabview.tab("Recipes Catalog")
        self.recipes_tab = RecipesTab(recipes_frame)
        self.recipes_tab.pack(fill="both", expand=True)

        units_frame = self.tabview.tab("Finished Units")
        self.finished_units_tab = FinishedUnitsTab(units_frame)
        self.finished_units_tab.pack(fill="both", expand=True)

    def refresh(self):
        """Refresh all sub-tabs."""
        if hasattr(self, 'recipes_tab'):
            self.recipes_tab.refresh()
        if hasattr(self, 'finished_units_tab'):
            self.finished_units_tab.refresh()
```

### T009: Create packaging_group_tab.py

Create `src/ui/tabs/packaging_group_tab.py`:

```python
"""Packaging group tab with nested sub-tabs."""
import customtkinter as ctk
from src.ui.finished_goods_tab import FinishedGoodsTab
from src.ui.packages_tab import PackagesTab


class PackagingGroupTab(ctk.CTkFrame):
    """Container for Finished Goods and Packages tabs."""

    def __init__(self, parent, mode=None):
        super().__init__(parent)
        self.mode = mode
        self._create_tabview()

    def _create_tabview(self):
        """Create nested tabview with sub-tabs."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Add sub-tabs
        self.tabview.add("Finished Goods (Food Only)")
        self.tabview.add("Finished Goods (Bundles)")
        self.tabview.add("Packages")

        # Create tab widgets with filtering
        food_frame = self.tabview.tab("Finished Goods (Food Only)")
        self.food_goods_tab = FinishedGoodsTab(food_frame, filter_bundles=False)
        self.food_goods_tab.pack(fill="both", expand=True)

        bundles_frame = self.tabview.tab("Finished Goods (Bundles)")
        self.bundles_tab = FinishedGoodsTab(bundles_frame, filter_bundles=True)
        self.bundles_tab.pack(fill="both", expand=True)

        packages_frame = self.tabview.tab("Packages")
        self.packages_tab = PackagesTab(packages_frame)
        self.packages_tab.pack(fill="both", expand=True)

    def refresh(self):
        """Refresh all sub-tabs."""
        if hasattr(self, 'food_goods_tab'):
            self.food_goods_tab.refresh()
        if hasattr(self, 'bundles_tab'):
            self.bundles_tab.refresh()
        if hasattr(self, 'packages_tab'):
            self.packages_tab.refresh()
```

**Note**: T009 requires adding a `filter_bundles` parameter to FinishedGoodsTab. Research the model to determine how bundles are identified (likely `is_bundle` flag or similar).

### T010: Update catalog_mode.py

Replace flat tabs with 4 group tabs:

```python
from src.ui.tabs.ingredients_group_tab import IngredientsGroupTab
from src.ui.tabs.recipes_group_tab import RecipesGroupTab
from src.ui.tabs.packaging_group_tab import PackagingGroupTab
from src.ui.materials_tab import MaterialsTab

def setup_tabs(self):
    """Set up catalog mode tabs with logical grouping."""
    self.tabview = ctk.CTkTabview(self.content_frame)
    self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

    # Add 4 group tabs
    self.tabview.add("Ingredients")
    self.tabview.add("Materials")
    self.tabview.add("Recipes")
    self.tabview.add("Packaging")

    # Create group tab widgets
    ingredients_frame = self.tabview.tab("Ingredients")
    self.ingredients_group = IngredientsGroupTab(ingredients_frame, mode=self)
    self.ingredients_group.pack(fill="both", expand=True)

    materials_frame = self.tabview.tab("Materials")
    self.materials_tab = MaterialsTab(materials_frame, mode=self)
    self.materials_tab.pack(fill="both", expand=True)

    recipes_frame = self.tabview.tab("Recipes")
    self.recipes_group = RecipesGroupTab(recipes_frame, mode=self)
    self.recipes_group.pack(fill="both", expand=True)

    packaging_frame = self.tabview.tab("Packaging")
    self.packaging_group = PackagingGroupTab(packaging_frame, mode=self)
    self.packaging_group.pack(fill="both", expand=True)
```

### T011: Update activate() and refresh_all_tabs()

Update methods to work with group tabs:

```python
def refresh_all_tabs(self):
    """Refresh all group tabs."""
    if hasattr(self, 'ingredients_group'):
        self.ingredients_group.refresh()
    if hasattr(self, 'materials_tab'):
        self.materials_tab.refresh()
    if hasattr(self, 'recipes_group'):
        self.recipes_group.refresh()
    if hasattr(self, 'packaging_group'):
        self.packaging_group.refresh()
```

### T012: Finished Goods Filtering Research

Before implementing, research how to distinguish bundles from food items:

1. Check `src/models/finished_good.py` for `is_bundle` or similar flag
2. Check `FinishedGoodsTab` constructor for existing filter parameters
3. Implement filtering based on findings

---

## Files to Modify/Create

| File | Action |
|------|--------|
| `src/ui/tabs/ingredients_group_tab.py` | NEW |
| `src/ui/tabs/recipes_group_tab.py` | NEW |
| `src/ui/tabs/packaging_group_tab.py` | NEW |
| `src/ui/modes/catalog_mode.py` | MODIFY |
| `src/ui/finished_goods_tab.py` | MODIFY (add filter param) |

---

## Acceptance Criteria

- [ ] Catalog shows 4 groups: Ingredients, Materials, Recipes, Packaging
- [ ] Ingredients group has: Ingredient Catalog, Food Products
- [ ] Materials group has: Material Catalog, Material Units, Material Products
- [ ] Recipes group has: Recipes Catalog, Finished Units
- [ ] Packaging group has: Finished Goods (Food Only), Finished Goods (Bundles), Packages
- [ ] Finished Goods (Food Only) shows only food items
- [ ] Finished Goods (Bundles) shows only bundles
- [ ] All existing functionality preserved
- [ ] Tab switching works at both group and sub-tab levels

---

## Testing

```bash
# Run app and verify:
# 1. Switch to Catalog mode
# 2. Verify 4 group tabs visible
# 3. Click each group - verify sub-tabs appear
# 4. Test CRUD on each sub-tab
# 5. Verify Finished Goods filtering works
```

## Activity Log

- 2026-01-16T02:41:02Z – null – lane=doing – Started implementation via workflow command
- 2026-01-16T02:44:50Z – null – lane=for_review – Completed catalog restructure: 4 groups (Ingredients, Materials, Recipes, Packaging) with nested sub-tabs. Food/Bundle split deferred - model doesn't have that distinction.
- 2026-01-16T04:30:51Z – null – lane=doing – Started review
- 2026-01-16T04:31:14Z – null – lane=done – Review passed: 4 groups implemented with nested tabs. Food/Bundle split correctly deferred per FR-009/FR-010.
