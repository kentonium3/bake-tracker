# Quickstart: Materials UI Rebuild Implementation

**Feature**: 048-materials-ui-rebuild
**Date**: 2026-01-11

## Overview

This guide provides step-by-step implementation instructions for rebuilding the Materials UI to match the Ingredients tab pattern.

## Prerequisites

- Read the reference implementation: `src/ui/ingredients_tab.py` (1741 lines)
- Understand current implementation: `src/ui/materials_tab.py` (981 lines)
- Review existing services in `src/services/material_*.py`

## File to Modify

**Single file replacement**: `src/ui/materials_tab.py`

The entire file will be rewritten. Keep it as a single file with multiple classes (matching the single-file pattern of the current implementation).

## Implementation Order

### Step 1: Create Base Structure

```python
"""
Materials tab for the Seasonal Baking Tracker.

Provides CRUD interface for managing materials catalog, products, and units
using a 3-tab layout matching the Ingredients pattern (Feature 048).
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import date

from src.services import (
    material_catalog_service,
    material_purchase_service,
    material_unit_service,
    supplier_service,
)
from src.services.exceptions import ValidationError, DatabaseError
from src.utils.constants import PADDING_MEDIUM, PADDING_LARGE


class MaterialsTab(ctk.CTkFrame):
    """Materials management with 3-tab layout: Catalog | Products | Units."""

    def __init__(self, parent):
        super().__init__(parent)
        self._data_loaded = False

        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # Title
        self.grid_rowconfigure(1, weight=1)  # Tabview

        # Create UI
        self._create_title()
        self._create_tabview()

        # Grid the frame
        self.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _create_title(self):
        title_label = ctk.CTkLabel(
            self,
            text="Materials",
            font=ctk.CTkFont(size=24, weight="bold"),
        )
        title_label.grid(row=0, column=0, sticky="w",
                        padx=PADDING_LARGE, pady=(PADDING_LARGE, PADDING_MEDIUM))

    def _create_tabview(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew",
                         padx=PADDING_LARGE, pady=PADDING_MEDIUM)

        # Create tabs
        self.tabview.add("Materials Catalog")
        self.tabview.add("Material Products")
        self.tabview.add("Material Units")

        # Create tab content frames
        self.catalog_tab = MaterialsCatalogTab(self.tabview.tab("Materials Catalog"))
        self.products_tab = MaterialProductsTab(self.tabview.tab("Material Products"))
        self.units_tab = MaterialUnitsTab(self.tabview.tab("Material Units"))

    def refresh(self):
        """Refresh all tabs."""
        self.catalog_tab.refresh()
        self.products_tab.refresh()
        self.units_tab.refresh()
        self._data_loaded = True
```

### Step 2: Implement MaterialsCatalogTab

Copy the structure from `IngredientsTab`:

1. **Grid layout**: 5 rows (title removed since parent has it, so 4 rows: filter, buttons, grid, status)
2. **Filter frame**: Search, L0 dropdown, L1 dropdown, Level dropdown, Clear button
3. **Action buttons**: Add Material, Edit (selection-dependent)
4. **Grid**: ttk.Treeview with columns (l0, l1, name, base_unit)
5. **Status bar**: Item count and filter status

Key methods to implement:
- `_create_filter_frame()` - copy from `_create_search_filter()`
- `_create_action_buttons()` - simplified (no tree toggle)
- `_create_grid()` - copy from `_create_ingredient_list()`
- `_create_status_bar()`
- `refresh()` - load all materials
- `_load_filter_data()` - populate L0 dropdown
- `_update_display()` - apply filters and populate grid
- `_apply_filters()` - search, hierarchy, level filters
- `_on_l0_filter_change()` - cascade to L1
- `_on_l1_filter_change()`
- `_on_level_filter_change()`
- `_on_search()`
- `_on_select()`
- `_on_double_click()`
- `_add_material()` - open dialog
- `_edit_material()` - open dialog with data

### Step 3: Implement MaterialProductsTab

Simpler than catalog (no cascading filters):

1. **Filter frame**: Search, Material dropdown, Clear button
2. **Action buttons**: Add Product, Edit, Record Purchase, Adjust Inventory
3. **Grid**: columns (material, name, inventory, unit_cost, supplier)
4. **Status bar**

Key methods:
- `refresh()` - load all products across all materials
- `_load_all_products()` - iterate materials to get products
- `_update_display()` - apply filters
- `_on_material_filter_change()`
- `_on_select()` - enable/disable purchase/adjust buttons
- `_add_product()`
- `_edit_product()`
- `_record_purchase()` - open RecordPurchaseDialog
- `_adjust_inventory()` - open AdjustInventoryDialog

### Step 4: Implement MaterialUnitsTab

Similar to products tab:

1. **Filter frame**: Search, Material dropdown, Clear button
2. **Action buttons**: Add Unit, Edit
3. **Grid**: columns (material, name, qty_per_unit, available, cost)
4. **Status bar**

### Step 5: Implement Dialogs

#### MaterialFormDialog

Copy from `IngredientFormDialog` pattern:

```python
class MaterialFormDialog(ctk.CTkToplevel):
    def __init__(self, parent, material: Optional[dict] = None, title: str = "Add Material"):
        super().__init__(parent)
        self.withdraw()  # Hide while building

        self.material = material
        self.result = None
        self.deleted = False

        # Configure window
        self.title(title)
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)

        # Build UI
        self._create_form()
        self._create_buttons()

        if self.material:
            self._populate_form()

        # Show and make modal
        self.deiconify()
        self.update()
        self.wait_visibility()
        self.grab_set()
        self.lift()
        self.focus_force()
```

Form fields:
- Name (required)
- Category (L0) dropdown - cascading
- Subcategory (L1) dropdown - cascading
- Base Unit dropdown (linear_inches, each, sheets, sq_inches)

#### MaterialProductFormDialog

Form fields:
- Material dropdown (required)
- Product Name (required)
- Package Quantity (required)
- Package Unit
- Supplier dropdown
- SKU
- Notes

#### MaterialUnitFormDialog

Form fields:
- Material dropdown (required, or pre-filled if context)
- Unit Name (required)
- Quantity per Unit (required)
- Description

#### RecordPurchaseDialog

Form fields:
- Supplier dropdown (required)
- Purchase Date (default today)
- Packages Purchased (required)
- Total Price (required)
- Notes

Auto-calculated display:
- Total Units = packages * package_quantity
- Unit Cost = price / total_units

#### AdjustInventoryDialog

Form fields:
- Mode radio buttons: "Set to value" / "Set to percentage"
- Value entry
- Notes

## Code Patterns to Copy

### Cascading Filter Pattern (from ingredients_tab.py:734-765)

```python
def _on_l0_filter_change(self, value: str):
    if self._updating_filters:
        return
    self._updating_filters = True
    try:
        if value == "All Categories":
            self._l1_map = {}
            self.l1_dropdown.configure(values=["All"], state="disabled")
            self.l1_var.set("All")
        elif value in self._l0_map:
            # Get children of selected L0
            l0_id = self._l0_map[value].get("id")
            subcategories = material_catalog_service.list_subcategories(l0_id)
            self._l1_map = {sub.name: {"id": sub.id} for sub in subcategories}
            if self._l1_map:
                l1_values = ["All"] + sorted(self._l1_map.keys())
                self.l1_dropdown.configure(values=l1_values, state="normal")
            else:
                self.l1_dropdown.configure(values=["All"], state="disabled")
            self.l1_var.set("All")
    finally:
        self._updating_filters = False
    self._update_display()
```

### Modal Dialog Pattern (from ingredients_tab.py:1072-1112)

```python
# In __init__:
self.withdraw()  # Hide while building

# ... build UI ...

self.deiconify()
self.update()
try:
    self.wait_visibility()
    self.grab_set()
except Exception:
    if not self.winfo_exists():
        return
self.lift()
self.focus_force()
```

### Grid Column Sort Pattern (from ingredients_tab.py:324-331)

```python
def _on_header_click(self, sort_key: str):
    if self.sort_column == sort_key:
        self.sort_ascending = not self.sort_ascending
    else:
        self.sort_column = sort_key
        self.sort_ascending = True
    self._update_display()
```

## Testing

### Manual Test Checklist

1. **Materials Catalog Tab**
   - [ ] Grid displays all materials with correct L0/L1/Name/Unit columns
   - [ ] Search filters by name
   - [ ] L0 dropdown filters and cascades to L1
   - [ ] L1 dropdown filters
   - [ ] Level dropdown filters (All, L0, L1, L2)
   - [ ] Clear resets all filters
   - [ ] Add Material opens dialog with cascading dropdowns
   - [ ] Edit Material opens pre-populated dialog
   - [ ] Double-click opens edit dialog
   - [ ] Delete prompts and removes material

2. **Material Products Tab**
   - [ ] Grid displays all products
   - [ ] Search filters by product name
   - [ ] Material dropdown filters
   - [ ] Inventory displays with unit (e.g., "4,724 inches")
   - [ ] Unit cost displays as currency
   - [ ] Add Product opens dialog
   - [ ] Edit Product opens pre-populated dialog
   - [ ] Record Purchase opens dialog with calculations
   - [ ] Adjust Inventory opens dialog

3. **Material Units Tab**
   - [ ] Grid displays all units
   - [ ] Available shows computed value
   - [ ] Cost shows computed value
   - [ ] Add Unit opens dialog
   - [ ] Edit Unit opens pre-populated dialog

## Common Pitfalls

1. **Don't forget re-entry guard** for cascading filter updates
2. **Use string IDs** for ttk.Treeview items (convert int to str)
3. **Handle empty states** - show message when no items match filter
4. **Validate before save** - check required fields in dialogs
5. **Refresh after CRUD** - call refresh() after successful operations
6. **Button state management** - disable Edit when nothing selected

## Reference Files

| File | Purpose |
|------|---------|
| `src/ui/ingredients_tab.py` | Primary pattern reference |
| `src/ui/materials_tab.py` | Current implementation (to replace) |
| `src/services/material_catalog_service.py` | Service methods |
| `src/services/material_unit_service.py` | Unit service methods |
| `src/services/material_purchase_service.py` | Purchase/inventory methods |
