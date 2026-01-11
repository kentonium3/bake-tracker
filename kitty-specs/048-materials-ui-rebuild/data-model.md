# Data Model: Materials UI Components

**Feature**: 048-materials-ui-rebuild
**Date**: 2026-01-11

This document describes the UI component hierarchy, state management, and data flow for the rebuilt Materials UI.

## Component Hierarchy

```
MaterialsTab (ctk.CTkFrame)
├── Title Label
├── CTkTabview
│   ├── Tab: "Materials Catalog"
│   │   └── MaterialsCatalogTab (inner frame)
│   │       ├── Filter Frame
│   │       │   ├── Search Entry
│   │       │   ├── L0 Category Dropdown
│   │       │   ├── L1 Subcategory Dropdown (cascading)
│   │       │   ├── Level Filter Dropdown
│   │       │   └── Clear Button
│   │       ├── Action Buttons Frame
│   │       │   ├── Add Material Button
│   │       │   └── Edit Button (selection-dependent)
│   │       ├── Grid Container
│   │       │   ├── ttk.Treeview (headings mode)
│   │       │   ├── Y Scrollbar
│   │       │   └── X Scrollbar
│   │       └── Status Label
│   │
│   ├── Tab: "Material Products"
│   │   └── MaterialProductsTab (inner frame)
│   │       ├── Filter Frame
│   │       │   ├── Search Entry
│   │       │   ├── Material Dropdown
│   │       │   └── Clear Button
│   │       ├── Action Buttons Frame
│   │       │   ├── Add Product Button
│   │       │   ├── Edit Button (selection-dependent)
│   │       │   ├── Record Purchase Button (selection-dependent)
│   │       │   └── Adjust Inventory Button (selection-dependent)
│   │       ├── Grid Container
│   │       │   └── ttk.Treeview (headings mode)
│   │       └── Status Label
│   │
│   └── Tab: "Material Units"
│       └── MaterialUnitsTab (inner frame)
│           ├── Filter Frame
│           │   ├── Search Entry
│           │   ├── Material Dropdown
│           │   └── Clear Button
│           ├── Action Buttons Frame
│           │   ├── Add Unit Button
│           │   └── Edit Button (selection-dependent)
│           ├── Grid Container
│           │   └── ttk.Treeview (headings mode)
│           └── Status Label
│
└── Dialogs (modal, created on demand)
    ├── MaterialFormDialog
    ├── MaterialProductFormDialog
    ├── MaterialUnitFormDialog
    ├── RecordPurchaseDialog
    └── AdjustInventoryDialog
```

## State Variables

### MaterialsTab (parent)

| Variable | Type | Purpose |
|----------|------|---------|
| `_data_loaded` | `bool` | Lazy loading flag |

### MaterialsCatalogTab

| Variable | Type | Purpose |
|----------|------|---------|
| `selected_material_id` | `Optional[int]` | Currently selected material |
| `materials` | `List[dict]` | Cached material list |
| `_l0_map` | `Dict[str, dict]` | L0 category name -> data |
| `_l1_map` | `Dict[str, dict]` | L1 subcategory name -> data |
| `_updating_filters` | `bool` | Re-entry guard for cascading updates |
| `_hierarchy_cache` | `Dict[int, Dict[str, str]]` | Material ID -> {l0, l1} display values |
| `sort_column` | `str` | Current sort column |
| `sort_ascending` | `bool` | Sort direction |

### MaterialProductsTab

| Variable | Type | Purpose |
|----------|------|---------|
| `selected_product_id` | `Optional[int]` | Currently selected product |
| `products` | `List[dict]` | Cached product list |
| `_material_map` | `Dict[str, int]` | Material name -> ID |
| `sort_column` | `str` | Current sort column |
| `sort_ascending` | `bool` | Sort direction |

### MaterialUnitsTab

| Variable | Type | Purpose |
|----------|------|---------|
| `selected_unit_id` | `Optional[int]` | Currently selected unit |
| `units` | `List[dict]` | Cached unit list |
| `_material_map` | `Dict[str, int]` | Material name -> ID |
| `sort_column` | `str` | Current sort column |
| `sort_ascending` | `bool` | Sort direction |

## Grid Definitions

### Materials Catalog Grid

| Column ID | Heading | Width | Data Source |
|-----------|---------|-------|-------------|
| `l0` | Category (L0) | 150 | Computed from hierarchy |
| `l1` | Subcategory (L1) | 150 | Computed from hierarchy |
| `name` | Material Name | 200 | `material.name` |
| `base_unit` | Default Unit | 100 | `material.base_unit` |

**Row ID**: `material.id` (int as string)

### Material Products Grid

| Column ID | Heading | Width | Data Source |
|-----------|---------|-------|-------------|
| `material` | Material | 150 | `product.material.name` |
| `name` | Product Name | 150 | `product.display_name` |
| `inventory` | Inventory | 120 | `f"{product.current_inventory:.1f} {product.material.base_unit}"` |
| `unit_cost` | Unit Cost | 100 | `f"${product.weighted_avg_cost:.4f}"` or "-" |
| `supplier` | Supplier | 120 | `product.supplier.name` or "-" |

**Row ID**: `product.id` (int as string)

### Material Units Grid

| Column ID | Heading | Width | Data Source |
|-----------|---------|-------|-------------|
| `material` | Material | 150 | `unit.material.name` |
| `name` | Unit Name | 150 | `unit.name` |
| `qty_per_unit` | Qty/Unit | 80 | `f"{unit.quantity_per_unit:.1f}"` |
| `available` | Available | 80 | `material_unit_service.get_available_inventory(unit.id)` |
| `cost` | Cost/Unit | 100 | `f"${material_unit_service.get_current_cost(unit.id):.4f}"` or "-" |

**Row ID**: `unit.id` (int as string)

## Dialog Data Structures

### MaterialFormDialog

**Input** (editing):
```python
{
    "id": int,
    "name": str,
    "base_unit": str,
    "category_id": int,      # For pre-selecting L0
    "subcategory_id": int,   # For pre-selecting L1
}
```

**Output** (result):
```python
{
    "name": str,
    "base_unit": str,
    "subcategory_id": int,   # Parent subcategory
}
```

### MaterialProductFormDialog

**Input** (editing):
```python
{
    "id": int,
    "name": str,
    "material_id": int,
    "package_quantity": float,
    "package_unit": str,
    "supplier_id": Optional[int],
    "sku": Optional[str],
    "notes": Optional[str],
}
```

**Output** (result):
```python
{
    "name": str,
    "material_id": int,
    "package_quantity": float,
    "package_unit": str,
    "supplier_id": Optional[int],
    "sku": Optional[str],
    "notes": Optional[str],
}
```

### MaterialUnitFormDialog

**Input** (editing):
```python
{
    "id": int,
    "name": str,
    "material_id": int,
    "quantity_per_unit": float,
    "description": Optional[str],
}
```

**Output** (result):
```python
{
    "name": str,
    "material_id": int,
    "quantity_per_unit": float,
    "description": Optional[str],
}
```

### RecordPurchaseDialog

**Output** (result):
```python
{
    "supplier_id": int,
    "purchase_date": date,
    "packages_purchased": int,
    "package_price": Decimal,
    "notes": Optional[str],
}
```

### AdjustInventoryDialog

**Output** (result):
```python
{
    "mode": str,  # "set" or "percentage"
    "value": float,
    "notes": Optional[str],
}
```

## Service Method Mapping

### Materials Catalog Tab

| UI Action | Service Method |
|-----------|----------------|
| Load categories | `material_catalog_service.list_categories()` |
| Load subcategories | `material_catalog_service.list_subcategories(category_id)` |
| Load materials | `material_catalog_service.list_materials(subcategory_id)` |
| Get all materials | Iterate categories -> subcategories -> materials |
| Create material | `material_catalog_service.create_material(subcategory_id, name, base_unit)` |
| Update material | `material_catalog_service.update_material(material_id, name=name)` |
| Delete material | `material_catalog_service.delete_material(material_id)` |

### Material Products Tab

| UI Action | Service Method |
|-----------|----------------|
| Load products | `material_catalog_service.list_products(material_id)` or iterate all |
| Create product | `material_catalog_service.create_product(material_id, name, package_quantity, package_unit, supplier_id)` |
| Update product | `material_catalog_service.update_product(product_id, ...)` |
| Delete product | `material_catalog_service.delete_product(product_id)` |
| Record purchase | `material_purchase_service.record_purchase(product_id, supplier_id, purchase_date, packages_purchased, package_price, notes)` |
| Adjust inventory | `material_purchase_service.adjust_inventory(product_id, new_quantity=, percentage=, notes=)` |

### Material Units Tab

| UI Action | Service Method |
|-----------|----------------|
| Load units | `material_unit_service.list_units(material_id)` |
| Get available | `material_unit_service.get_available_inventory(unit_id)` |
| Get cost | `material_unit_service.get_current_cost(unit_id)` |
| Create unit | `material_unit_service.create_unit(material_id, name, quantity_per_unit, description)` |
| Update unit | `material_unit_service.update_unit(unit_id, ...)` |
| Delete unit | `material_unit_service.delete_unit(unit_id)` |

## Event Flow

### Tab Selection
```
User selects tab -> CTkTabview callback -> refresh() on active tab
```

### Filter Change (Materials Catalog)
```
L0 dropdown change
  -> _on_l0_filter_change()
  -> Populate L1 dropdown from service
  -> Enable/disable L1 dropdown
  -> _update_display()
```

### Selection Change
```
Treeview selection
  -> <<TreeviewSelect>> event
  -> _on_select() handler
  -> Update selected_*_id
  -> Enable/disable buttons
  -> Update status
```

### CRUD Operation
```
Add/Edit button click
  -> Open dialog
  -> wait_window()
  -> Check dialog.result
  -> Call service method
  -> refresh()
  -> Show success/error message
```
