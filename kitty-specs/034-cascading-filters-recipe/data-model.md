# Data Model: Cascading Filters & Recipe Integration

**Feature**: 034-cascading-filters-recipe
**Date**: 2026-01-02

## Overview

This feature does not introduce new entities or modify the database schema. It works with existing entities through the UI layer.

## Existing Entities (Reference Only)

### Ingredient

The three-tier ingredient hierarchy established in Phase 1 (F033):

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| display_name | String | User-visible name |
| parent_ingredient_id | Integer (FK) | Self-reference for hierarchy |
| hierarchy_level | Integer | Computed: 0=root, 1=subcategory, 2=leaf |

**Hierarchy Rules**:
- L0 (root): `parent_ingredient_id = NULL`
- L1 (subcategory): parent is L0
- L2 (leaf): parent is L1, can have Products

### Product

Links to L2 (leaf) ingredients:

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| ingredient_id | Integer (FK) | Must reference L2 ingredient |

### RecipeIngredient

Junction table for recipe ingredients:

| Field | Type | Description |
|-------|------|-------------|
| recipe_id | Integer (FK) | Recipe reference |
| ingredient_id | Integer (FK) | Must reference L2 ingredient |
| quantity | Decimal | Amount needed |
| unit | String | Measurement unit |

## Service Functions Used

### ingredient_hierarchy_service

| Function | Purpose | Used By |
|----------|---------|---------|
| `get_root_ingredients()` | Get all L0 ingredients | Filter initialization |
| `get_children(parent_id)` | Get direct children | Cascading dropdown population |
| `get_descendants(ingredient_id)` | Get all descendants | Filter application |

## No Schema Changes Required

This feature operates entirely at the UI layer, fixing/enhancing existing cascading filter behavior and adding Clear Filters buttons.
