# Data Model: Finished Goods Catalog UI

**Feature**: 088-finished-goods-catalog-ui
**Date**: 2026-01-30

## Entity Overview

This feature uses existing models without schema changes.

## Entities

### FinishedGood (existing)

An assembled product containing foods (FinishedUnits), materials (MaterialUnits), and/or other finished goods.

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| slug | String(100) | Unique, not null | URL-safe identifier |
| display_name | String(200) | Not null | User-visible name |
| description | Text | Nullable | Extended description |
| assembly_type | Enum | Not null, default CUSTOM_ORDER | Type of assembly |
| packaging_instructions | Text | Nullable | How to package |
| inventory_count | Integer | Not null, default 0 | Current stock |
| notes | Text | Nullable | Additional notes |
| created_at | DateTime | Not null | Creation timestamp |
| updated_at | DateTime | Not null | Last update timestamp |

**Relationships**:
- `components` → List[Composition] (one-to-many, cascade delete)

**File**: `src/models/finished_good.py`

### Composition (existing)

Junction entity linking FinishedGood to its components with polymorphic FK.

**Attributes**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| id | Integer | PK, auto | Primary key |
| assembly_id | Integer | FK FinishedGood, not null | Parent assembly |
| finished_unit_id | Integer | FK FinishedUnit, nullable | Food component |
| finished_good_id | Integer | FK FinishedGood, nullable | Nested component |
| material_unit_id | Integer | FK MaterialUnit, nullable | Material component |
| packaging_product_id | Integer | FK Product, nullable | Packaging (deferred) |
| component_quantity | Integer | Not null, default 1 | Quantity needed |
| notes | Text | Nullable | Component-specific notes |
| sort_order | Integer | Not null, default 0 | Display order |

**Constraint**: Exactly one of (finished_unit_id, finished_good_id, material_unit_id, packaging_product_id) must be set (XOR).

**Relationships**:
- `assembly` → FinishedGood (many-to-one)
- `finished_unit_component` → FinishedUnit (many-to-one, nullable)
- `finished_good_component` → FinishedGood (many-to-one, nullable)
- `material_unit_component` → MaterialUnit (many-to-one, nullable)

**Factory Methods**:
- `create_unit_composition(assembly_id, finished_unit_id, quantity, notes=None, sort_order=0)`
- `create_assembly_composition(assembly_id, finished_good_id, quantity, notes=None, sort_order=0)`
- `create_material_unit_composition(assembly_id, material_unit_id, quantity, notes=None, sort_order=0)`

**File**: `src/models/composition.py`

### AssemblyType (existing enum)

Enumeration of assembly types.

**Values**:
| Value | Display Name | Description |
|-------|--------------|-------------|
| CUSTOM_ORDER | Custom Order | One-off assembly |
| GIFT_BOX | Gift Box | Boxed gift set |
| VARIETY_PACK | Variety Pack | Mixed selection bag |
| SEASONAL_BOX | Seasonal Box | Holiday-themed box |
| EVENT_PACKAGE | Event Package | Event-specific bundle |

**File**: `src/models/assembly_type.py`

### FinishedUnit (existing, referenced)

A yield type from a Recipe, used as food component.

**Key Attributes** (relevant to F088):
- `id` - Primary key
- `display_name` - User-visible name
- `category` - Recipe category
- `recipe` → Recipe relationship

**File**: `src/models/finished_unit.py`

### MaterialUnit (existing, referenced)

A product-specific material definition, used as material component.

**Key Attributes** (relevant to F088):
- `id` - Primary key
- `name` - Unit name
- `product` → MaterialProduct relationship

**File**: `src/models/material_unit.py`

## Entity Relationships

```
FinishedGood (assembly)
    │
    └── components (List[Composition])
            │
            ├── finished_unit_id → FinishedUnit (food)
            ├── material_unit_id → MaterialUnit (material)
            └── finished_good_id → FinishedGood (nested)
```

## Validation Rules

### FinishedGood Creation

1. `display_name` required, non-empty
2. `assembly_type` must be valid enum value
3. At least one component required (any type)
4. All component IDs must resolve to existing records

### Composition Creation

1. Exactly one component FK must be set (XOR constraint)
2. `component_quantity` must be > 0
3. For nested FinishedGoods: no circular references allowed

### Circular Reference Check

Before adding a FinishedGood as component:
1. Cannot add self (A → A)
2. Cannot add if target contains current (A → B where B contains A)
3. Cannot add if target's descendants contain current (transitive closure)

**Algorithm**: Graph traversal from target, check if current ID reachable.

## State Transitions

FinishedGood has no explicit state machine. Lifecycle:
1. Created with components
2. Updated (components can be added/removed)
3. Deleted (only if not referenced)

Delete blocked if:
- Referenced by other FinishedGood (as component)
- Referenced by Event (planning module)
