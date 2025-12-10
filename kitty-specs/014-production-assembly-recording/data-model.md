# Data Model: Production & Assembly Recording UI

**Feature**: 014-production-assembly-recording
**Date**: 2025-12-10
**Status**: Complete

## Overview

This feature is primarily a UI feature. The underlying data models were implemented in Feature 013. This document describes the entities the UI will interact with and any UI-specific data structures.

## Existing Entities (from Feature 013)

### FinishedUnit

Individual consumable items produced from recipes.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| uuid | UUID | Unique identifier for sync |
| slug | String | URL-safe identifier |
| display_name | String | User-facing name |
| recipe_id | Integer | FK to Recipe |
| inventory_count | Integer | Current inventory |
| unit_cost | Decimal | Cost per unit |
| items_per_batch | Integer | Yield per batch |

**Relationships**:
- `recipe` - Many-to-One with Recipe
- `production_runs` - One-to-Many with ProductionRun

### FinishedGood

Assembled gift packages containing FinishedUnits and packaging.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| uuid | UUID | Unique identifier for sync |
| slug | String | URL-safe identifier |
| display_name | String | User-facing name |
| inventory_count | Integer | Current inventory |
| total_cost | Decimal | Total cost per unit |

**Relationships**:
- `compositions` - One-to-Many with Composition (BOM)
- `assembly_runs` - One-to-Many with AssemblyRun

### ProductionRun

Record of batch production event.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| uuid | UUID | Unique identifier |
| recipe_id | Integer | FK to Recipe |
| finished_unit_id | Integer | FK to FinishedUnit |
| num_batches | Integer | Batches produced |
| expected_yield | Integer | Calculated yield |
| actual_yield | Integer | Actual yield |
| produced_at | DateTime | Production timestamp |
| notes | String | Optional notes |
| total_ingredient_cost | Decimal | Total cost |
| per_unit_cost | Decimal | Cost per unit |

**Relationships**:
- `recipe` - Many-to-One with Recipe
- `finished_unit` - Many-to-One with FinishedUnit
- `consumptions` - One-to-Many with ProductionConsumption

### AssemblyRun

Record of assembly event.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| uuid | UUID | Unique identifier |
| finished_good_id | Integer | FK to FinishedGood |
| quantity_assembled | Integer | Units assembled |
| assembled_at | DateTime | Assembly timestamp |
| notes | String | Optional notes |
| total_component_cost | Decimal | Total cost |
| per_unit_cost | Decimal | Cost per unit |

**Relationships**:
- `finished_good` - Many-to-One with FinishedGood
- `finished_unit_consumptions` - One-to-Many with AssemblyFinishedUnitConsumption
- `packaging_consumptions` - One-to-Many with AssemblyPackagingConsumption

### Composition (BOM)

Bill of materials linking FinishedGood to components.

| Field | Type | Description |
|-------|------|-------------|
| id | Integer | Primary key |
| assembly_id | Integer | FK to FinishedGood |
| finished_unit_id | Integer | FK to FinishedUnit (optional) |
| finished_good_id | Integer | FK to FinishedGood (optional, nested) |
| packaging_product_id | Integer | FK to Product (optional) |
| component_quantity | Decimal | Quantity needed |

## UI-Specific Data Structures

### AvailabilityCheckResult (from service)

Returned by `check_can_produce()` and `check_can_assemble()`.

```python
{
    "can_produce": bool,  # or "can_assemble"
    "missing": [
        {
            "ingredient_slug": str,       # For production
            "ingredient_name": str,
            "needed": Decimal,
            "available": Decimal,
            "unit": str
        },
        # or for assembly:
        {
            "component_type": "finished_unit" | "finished_good" | "packaging",
            "component_id": int,
            "component_name": str,
            "needed": int | Decimal,
            "available": int | Decimal,
            "unit": str  # for packaging only
        }
    ]
}
```

### RecordProductionDialogResult

Data returned from RecordProductionDialog.

```python
{
    "recipe_id": int,
    "finished_unit_id": int,
    "num_batches": int,
    "actual_yield": int,
    "notes": str | None
}
```

### RecordAssemblyDialogResult

Data returned from RecordAssemblyDialog.

```python
{
    "finished_good_id": int,
    "quantity": int,
    "notes": str | None
}
```

### ProductionHistoryRow

Display format for production history table.

| Column | Source | Format |
|--------|--------|--------|
| Date | `produced_at` | "Dec 10, 2025" |
| Batches | `num_batches` | "2" |
| Yield | `actual_yield` / `expected_yield` | "24 / 24" or "22 / 24" |
| Cost | `total_ingredient_cost` | "$15.50" |

### AssemblyHistoryRow

Display format for assembly history table.

| Column | Source | Format |
|--------|--------|--------|
| Date | `assembled_at` | "Dec 10, 2025" |
| Quantity | `quantity_assembled` | "10" |
| Cost | `total_component_cost` | "$45.00" |

## Entity Relationship Diagram

```
Recipe ──────────────┬──────────── FinishedUnit
                     │                   │
                     │                   │ inventory_count
                     │                   │
                     ▼                   ▼
              ProductionRun ◄─────── [Record Production]
                     │
                     ▼
          ProductionConsumption
                     │
                     ▼
              InventoryItem (FIFO consumed)


FinishedUnit ────────┬──────────── FinishedGood
                     │                   │
                     │                   │ inventory_count
                     │                   │
                     ▼                   ▼
              Composition            AssemblyRun ◄─── [Record Assembly]
              (BOM entries)              │
                     │                   ▼
                     ▼         AssemblyFinishedUnitConsumption
              Product (packaging)        │
                     │                   ▼
                     ▼         AssemblyPackagingConsumption
              InventoryItem              │
              (FIFO consumed)            ▼
                                  InventoryItem (FIFO consumed)
```

## State Transitions

### FinishedUnit Inventory

```
[0] ──(Record Production)──> [+actual_yield]
```

No decrement path in this feature (consumption happens via Assembly).

### FinishedGood Inventory

```
[0] ──(Record Assembly)──> [+quantity_assembled]
```

No decrement path in this feature (consumption happens via Event Assignment - different feature).

## Validation Rules

### Record Production

1. `num_batches` MUST be >= 1
2. `actual_yield` MUST be >= 0 (0 allowed for failed batches)
3. `recipe_id` MUST exist and be associated with `finished_unit_id`
4. Availability check MUST pass (all ingredients sufficient)

### Record Assembly

1. `quantity` MUST be >= 1
2. `finished_good_id` MUST exist and have defined composition
3. Availability check MUST pass (all components sufficient)
