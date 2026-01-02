# Data Model: Phase 1 Ingredient Hierarchy Fixes

**Feature**: `033-phase-1-ingredient`
**Date**: 2026-01-02

## Overview

This feature does NOT modify the database schema. It adds service-layer convenience functions and fixes UI implementation.

## Existing Entities (No Changes)

### Ingredient

The core entity already has hierarchy support from F031:

```
Ingredient
├── id (PK)
├── slug (unique)
├── display_name
├── category (legacy - still populated)
├── hierarchy_level (0/1/2) ← Computed from parent
├── parent_ingredient_id (FK → Ingredient.id, nullable)
├── is_packaging (bool)
├── ... (other fields)
```

**Hierarchy Rules**:
- `hierarchy_level = 0` when `parent_ingredient_id IS NULL` (L0 Root)
- `hierarchy_level = 1` when parent is L0 (L1 Subcategory)
- `hierarchy_level = 2` when parent is L1 (L2 Leaf)
- L2 ingredients cannot have children

### Product

Links to Ingredient for categorization:

```
Product
├── id (PK)
├── name
├── ingredient_id (FK → Ingredient.id)
├── ... (other fields)
```

**Relationship**: Many Products → One Ingredient

## New Service Functions

### can_change_parent()

**Signature**:
```python
def can_change_parent(
    ingredient_id: int,
    new_parent_id: Optional[int],
    session=None
) -> Dict[str, Any]:
    """
    Check if parent change is allowed and gather impact information.

    Returns:
        {
            "allowed": bool,
            "reason": str,  # Empty if allowed, error message if not
            "warnings": List[str],  # Informational warnings
            "child_count": int,
            "product_count": int,
            "new_level": int  # 0, 1, or 2
        }
    """
```

**Logic**:
1. Call existing `validate_hierarchy()` in try/except
2. If exception → `allowed=False`, `reason=exception.message`
3. If valid → gather counts and warnings
4. Return structured dict for UI consumption

### get_product_count()

**Signature**:
```python
def get_product_count(ingredient_id: int, session=None) -> int:
    """Count products linked to this ingredient."""
```

**Logic**:
- Simple query: `SELECT COUNT(*) FROM products WHERE ingredient_id = ?`

### get_child_count()

**Signature**:
```python
def get_child_count(ingredient_id: int, session=None) -> int:
    """Count direct child ingredients."""
```

**Logic**:
- Simple query: `SELECT COUNT(*) FROM ingredients WHERE parent_ingredient_id = ?`

## UI Data Flow

### Parent Selection → Level Display

```
User selects parent in dropdown
    ↓
_on_parent_change() callback
    ↓
Compute new_level:
  - No parent selected → level = 0
  - L0 parent → level = 1
  - L1 parent → level = 2
    ↓
Update level_display label: "Level: L{level} ({name})"
    ↓
If editing existing ingredient:
  - Call can_change_parent()
  - Display warnings inline if any
```

### Hierarchy Path Display

```
Load ingredients list
    ↓
For each ingredient:
  - Call get_ancestors(ingredient_id)
  - Build path: " > ".join([ancestor.display_name for ancestor in ancestors] + [ingredient.display_name])
  - Cache in _hierarchy_path_cache
    ↓
Display in treeview column
```

## Validation Rules

| Rule | Implementation | Location |
|------|---------------|----------|
| Max depth = 3 levels | `validate_hierarchy()` | ingredient_hierarchy_service.py |
| No circular references | `would_create_cycle()` | ingredient_hierarchy_service.py |
| L2 cannot have children | `validate_hierarchy()` depth check | ingredient_hierarchy_service.py |
| Parent must exist | `validate_hierarchy()` | ingredient_hierarchy_service.py |

## Test Data Requirements

Existing test fixtures should cover:
- L0, L1, L2 ingredients
- Ingredients with children
- Ingredients with products
- Parent change scenarios

See `src/tests/services/test_ingredient_hierarchy_service.py` for existing tests.
