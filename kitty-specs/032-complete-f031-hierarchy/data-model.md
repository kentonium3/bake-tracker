# Data Model: Complete F031 Hierarchy UI Implementation

**Feature**: 032-complete-f031-hierarchy
**Date**: 2025-12-31
**Status**: Complete (No schema changes - UI only)

## Overview

This feature is UI-only. The data model is already complete from F031. This document summarizes the existing schema elements relevant to the UI implementation.

---

## Existing Entities (No Changes)

### Ingredient

The core entity for hierarchy representation.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `display_name` | String | User-visible name |
| `slug` | String | URL-safe unique identifier |
| `hierarchy_level` | Integer | 0=Root, 1=Subcategory, 2=Leaf |
| `parent_ingredient_id` | Integer (FK) | Reference to parent ingredient |
| `category` | String | **DEPRECATED** - Legacy field, ignored by UI |
| `is_packaging` | Boolean | True if packaging material |
| `density_volume_value` | Float | Density conversion (volume side) |
| `density_volume_unit` | String | Density conversion unit |
| `density_weight_value` | Float | Density conversion (weight side) |
| `density_weight_unit` | String | Density conversion unit |

**Hierarchy Rules**:
- L0 (Root): `parent_ingredient_id = NULL`, `hierarchy_level = 0`
- L1 (Subcategory): `parent_ingredient_id` points to L0, `hierarchy_level = 1`
- L2 (Leaf): `parent_ingredient_id` points to L1, `hierarchy_level = 2`

### Product

Links to leaf ingredients only.

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Primary key |
| `ingredient_id` | Integer (FK) | **Must reference L2 ingredient** |
| ... | ... | Other fields unchanged |

### InventoryItem

Linked to products (inherits hierarchy through product → ingredient).

---

## UI Data Structures

### Hierarchy Display Cache

For efficient grid display, build a cache mapping ingredient ID to hierarchy info:

```python
# Cache structure (built once per display refresh)
hierarchy_cache: Dict[int, Tuple[str, str]] = {
    ingredient_id: (category_name, subcategory_name),
    # Example:
    42: ("Chocolate", "Dark Chocolate"),  # For a leaf ingredient
    15: ("Flour", "—"),  # For a subcategory (no parent subcategory)
    3: ("—", "—"),  # For a root category (no parents)
}
```

### Cascading Dropdown State

For ingredient edit form, maintain selection state:

```python
# Category (L0) selection
categories: List[Dict]  # From get_root_ingredients()
categories_map: Dict[str, Dict]  # display_name -> ingredient dict

# Subcategory (L1) selection - populated on category change
subcategories: List[Dict]  # From get_children(selected_l0_id)
subcategories_map: Dict[str, Dict]

# Selected parent for new ingredient
selected_parent: Optional[Dict]  # The L1 to become parent of new L2
```

---

## Validation Rules

| Rule | Enforcement | Error Message |
|------|-------------|---------------|
| Products must link to L2 ingredients | UI: Only show L2 in dropdown | "Please select a leaf ingredient" |
| Recipes must use L2 ingredients | UI: Only show L2 in dropdown | "Only leaf ingredients can be used in recipes" |
| L2 must have L1 parent | UI: Require subcategory selection | "Please select a subcategory" |
| L1 must have L0 parent | UI: Require category selection | "Please select a category" |

---

## Service Layer API (Existing)

No new service functions needed. Use existing:

```python
from src.services import ingredient_hierarchy_service

# For populating L0 dropdown
categories = ingredient_hierarchy_service.get_root_ingredients()

# For cascading L1 dropdown
subcategories = ingredient_hierarchy_service.get_children(selected_l0_id)

# For pre-populating edit form
ancestors = ingredient_hierarchy_service.get_ancestors(ingredient_id)
# Returns: [immediate_parent, grandparent, ...] (L1, L0 for a leaf)

# For level filter
filtered = ingredient_hierarchy_service.get_ingredients_by_level(level)

# For product/recipe ingredient dropdowns
leaves = ingredient_hierarchy_service.get_leaf_ingredients()
```

---

## Migration Notes

- **No database migration required** - Schema unchanged
- **Legacy `category` field** - Remains populated but UI ignores it
- **Backward compatibility** - Export/import already handles hierarchy
