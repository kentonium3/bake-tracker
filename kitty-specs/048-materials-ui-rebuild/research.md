# Research: Materials UI Rebuild

**Feature**: 048-materials-ui-rebuild
**Date**: 2026-01-11

## Research Questions Addressed

### RQ1: Tab Structure for Materials

**Question**: How should MaterialUnits be incorporated into the new UI structure?

**Decision**: Three sub-tabs: Materials Catalog | Material Products | Material Units

**Rationale**:
- User explicitly confirmed third sub-tab approach
- Maintains logical separation between material definitions, purchasable products, and packaging units
- Follows the established pattern of Ingredients/Products separation
- MaterialUnits are a distinct concept from Products (units consume material to create packaging)

**Alternatives Considered**:
1. Integrated into Material Products tab - rejected (different entity with different lifecycle)
2. Removed entirely - rejected (functionality is actively used)
3. Collapsible section within Products - rejected (user preferred tab approach)

### RQ2: View Mode Toggle

**Question**: Should Materials have a Flat/Tree view toggle like Ingredients?

**Decision**: Flat grid views only, no tree toggle

**Rationale**:
- User explicitly confirmed no tree view needed
- Materials hierarchy is simpler (Category > Subcategory > Material)
- Hierarchy is adequately represented via L0/L1 columns in grid
- Simplifies implementation significantly

**Alternatives Considered**:
1. Full tree/flat toggle - rejected by user preference
2. Tree-only view - rejected (doesn't match Ingredients pattern)

### RQ3: Service Layer Compatibility

**Question**: Do existing services provide all needed functionality?

**Decision**: Existing services are sufficient

**Evidence**:
- `material_catalog_service.py` provides:
  - `list_categories()`, `list_subcategories(category_id)`, `list_materials(subcategory_id)`
  - `create_category()`, `create_subcategory()`, `create_material()`
  - `get_category()`, `get_subcategory()`, `get_material()`
  - `update_category()`, `update_subcategory()`, `update_material()`
  - `list_products(material_id)`, `create_product()`
- `material_product_service.py` provides product CRUD
- `material_unit_service.py` provides:
  - `list_units(material_id)`, `create_unit()`
  - `get_available_inventory()`, `get_current_cost()`
- `material_purchase_service.py` provides:
  - `record_purchase()`, `adjust_inventory()`

**Rationale**: Current `materials_tab.py` already uses these services successfully. No service changes needed.

### RQ4: Grid Column Mapping

**Question**: What columns should each grid display?

**Decision**:

| Tab | Columns | Source |
|-----|---------|--------|
| Materials Catalog | Category (L0), Subcategory (L1), Material Name, Default Unit | Matches Ingredients: L0, L1, Name, Density |
| Material Products | Material, Product Name, Inventory, Unit Cost, Supplier | From spec FR-010 |
| Material Units | Material, Unit Name, Qty/Unit, Available, Cost/Unit | From current UI units_tree |

**Rationale**:
- Materials Catalog mirrors Ingredients grid exactly
- Products/Units columns derived from spec requirements and current functionality

### RQ5: Filter Behavior

**Question**: How should filters behave, especially cascading filters?

**Decision**: Follow Ingredients tab cascading filter pattern exactly

**Evidence from `ingredients_tab.py`**:
- L0 dropdown populates from `ingredient_hierarchy_service.get_root_ingredients()`
- L1 dropdown populates from `ingredient_hierarchy_service.get_children(l0_id)` when L0 selected
- L1 disabled when L0 is "All Categories"
- Re-entry guard `_updating_filters` prevents recursive updates
- `_apply_hierarchy_filters()` filters descendants recursively

**Decision for Products/Units tabs**:
- Single "Material" dropdown (not cascading L0/L1)
- Shows all materials in flat list
- Filters products/units by selected material

## Reference Implementation Analysis

### `src/ui/ingredients_tab.py` Structure

```
IngredientsTab (ctk.CTkFrame)
├── __init__()
│   ├── State variables
│   ├── Grid configuration (5 rows)
│   └── UI component creation
├── UI Creation Methods
│   ├── _create_title()
│   ├── _create_search_filter()
│   ├── _create_action_buttons()
│   ├── _create_ingredient_list()  # ttk.Treeview
│   ├── _create_tree_view()        # NOT NEEDED for Materials
│   └── _create_status_bar()
├── Data Methods
│   ├── refresh()
│   ├── _load_filter_data()
│   ├── _update_ingredient_display()
│   ├── _apply_filters()
│   ├── _apply_hierarchy_filters()
│   └── _build_hierarchy_path_cache()
├── Event Handlers
│   ├── _on_search()
│   ├── _on_l0_filter_change()
│   ├── _on_l1_filter_change()
│   ├── _on_level_filter_change()
│   ├── _on_header_click()  # Sorting
│   ├── _on_tree_select()
│   └── _on_double_click()
├── CRUD Methods
│   ├── _add_ingredient()
│   ├── _edit_ingredient()
│   └── _delete_ingredient()
└── Utility Methods
    ├── _enable_selection_buttons()
    ├── _disable_selection_buttons()
    ├── update_status()
    └── select_ingredient()

IngredientFormDialog (ctk.CTkToplevel)
├── __init__()
│   ├── Modal setup (withdraw, transient, grab_set)
│   ├── Form creation
│   └── Button creation
├── Form Methods
│   ├── _create_form()
│   ├── _create_buttons()
│   ├── _populate_form()
│   ├── _build_l0_options()
│   ├── _on_l0_change()
│   ├── _on_l1_change()
│   └── _compute_and_display_level()
├── Validation
│   ├── _validate_density_input()
│   └── _get_density_values()
└── Actions
    ├── _save()
    ├── _cancel()
    └── _delete()
```

### Key Patterns to Copy

1. **Grid Configuration**: `grid_columnconfigure(0, weight=1)`, 5 rows with weights
2. **Treeview Setup**: `ttk.Treeview` with headings, columns, scrollbars
3. **Filter Frame**: `pack(side="left")` for horizontal layout
4. **Modal Dialog**: `withdraw()` -> build UI -> `deiconify()` -> `grab_set()`
5. **Cascading Dropdowns**: `_on_l0_change()` populates L1 values
6. **Selection State**: Track `selected_*_id` or `selected_*_slug`
7. **Button State**: `_enable_selection_buttons()` / `_disable_selection_buttons()`

## Existing `materials_tab.py` Analysis

Current implementation (981 lines) uses:
- Two-panel layout (left hierarchy tree, right details)
- Single `ttk.Treeview` for hierarchy (categories/subcategories/materials)
- Separate trees for products and units
- Dialogs: CategoryDialog, SubcategoryDialog, MaterialDialog, ProductDialog, PurchaseDialog, AdjustInventoryDialog, UnitDialog

**What to Keep**:
- Dialog field definitions (names, units, etc.)
- Service method calls
- Validation logic

**What to Replace**:
- Overall layout (two-panel -> three-tab)
- Hierarchy display (tree -> grid with L0/L1 columns)
- Selection management

## Findings Summary

| Topic | Finding |
|-------|---------|
| Tab Structure | 3 tabs confirmed by user |
| View Mode | Flat only, no tree toggle |
| Services | All existing, no changes needed |
| Grid Pattern | Copy from ingredients_tab.py |
| Filter Pattern | Cascading L0/L1 for catalog, single dropdown for products/units |
| Dialog Pattern | Modal with transient/grab_set, standard button layout |
