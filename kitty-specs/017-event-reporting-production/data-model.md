# Data Model: Event Reporting & Production Dashboard

**Feature**: 017-event-reporting-production
**Date**: 2025-12-11

## Overview

Feature 017 requires **no new database tables**. All data model needs are satisfied by existing entities from Feature 016 (Event-Centric Production Model).

## Existing Entities Used

### Core Event Entities

| Entity | Purpose in Feature 017 |
|--------|------------------------|
| **Event** | Parent entity for all reporting |
| **EventProductionTarget** | Recipe production targets (batches) |
| **EventAssemblyTarget** | Finished good assembly targets (quantity) |
| **EventRecipientPackage** | Package assignments with fulfillment_status |
| **ProductionRun** | Actual production with event_id linkage |
| **AssemblyRun** | Actual assembly with event_id linkage |

### Cost Tracking Entities

| Entity | Purpose in Feature 017 |
|--------|------------------------|
| **ProductionConsumption** | Ingredient costs per production run |
| **AssemblyFinishedUnitConsumption** | Finished unit costs per assembly |
| **AssemblyPackagingConsumption** | Packaging costs per assembly |

### Reference Entities

| Entity | Purpose in Feature 017 |
|--------|------------------------|
| **Recipe** | Recipe names for progress display |
| **FinishedGood** | Finished good names for progress display |
| **Recipient** | Recipient names for history display |
| **Package** | Package names for history display |

## Key Relationships for Feature 017

```
Event (1) ──────────────── (*) EventProductionTarget
  │                              └── recipe_id → Recipe
  │
  ├───────────────────── (*) EventAssemblyTarget
  │                              └── finished_good_id → FinishedGood
  │
  ├───────────────────── (*) ProductionRun
  │                              └── (*) ProductionConsumption
  │
  ├───────────────────── (*) AssemblyRun
  │                              ├── (*) AssemblyFinishedUnitConsumption
  │                              └── (*) AssemblyPackagingConsumption
  │
  └───────────────────── (*) EventRecipientPackage
                               ├── recipient_id → Recipient
                               └── package_id → Package
```

## Data Flows

### 1. Production Progress

```
EventProductionTarget.target_batches
    compared with
SUM(ProductionRun.num_batches WHERE event_id = X AND recipe_id = Y)
    yields
progress_pct, is_complete
```

### 2. Assembly Progress

```
EventAssemblyTarget.target_quantity
    compared with
SUM(AssemblyRun.quantity_assembled WHERE event_id = X AND finished_good_id = Y)
    yields
progress_pct, is_complete
```

### 3. Cost Analysis

```
Estimated Cost:
  get_shopping_list(event_id).total_estimated_cost
    (from current ingredient prices)

Actual Cost:
  SUM(ProductionRun.total_cost WHERE event_id = X)
  + SUM(AssemblyRun.total_cost WHERE event_id = X)
    (from cost_at_time in consumption records)
```

### 4. Recipient History

```
EventRecipientPackage records
  WHERE recipient_id = X
  ORDER BY Event.event_date DESC
    yields
List of {event, package, quantity, fulfillment_status}
```

## CSV Export Schema

Shopping list CSV will include:

| Column | Source |
|--------|--------|
| Ingredient | shopping_list.items[].ingredient_name |
| Quantity Needed | shopping_list.items[].quantity_needed |
| On Hand | shopping_list.items[].quantity_on_hand |
| To Buy | shopping_list.items[].shortfall |
| Unit | shopping_list.items[].unit |
| Preferred Brand | shopping_list.items[].product_recommendation.display_name |
| Est. Cost | shopping_list.items[].product_recommendation.total_cost |

## New Service Method Signatures

### export_shopping_list_csv()

```python
def export_shopping_list_csv(event_id: int, file_path: str) -> bool:
    """
    Export shopping list to CSV file.

    Args:
        event_id: Event ID
        file_path: Destination file path

    Returns:
        True if successful

    Raises:
        EventNotFoundError: If event not found
        IOError: If file write fails
    """
```

### get_event_cost_analysis()

```python
def get_event_cost_analysis(event_id: int) -> Dict[str, Any]:
    """
    Get cost breakdown for an event.

    Returns:
        Dict with:
        - production_costs: List[{recipe_name, run_count, total_cost}]
        - assembly_costs: List[{finished_good_name, run_count, total_cost}]
        - total_production_cost: Decimal
        - total_assembly_cost: Decimal
        - grand_total: Decimal
        - estimated_cost: Decimal (from shopping list)
        - variance: Decimal (estimated - actual)
    """
```

## Validation Rules

No new validation rules required. Existing validations from Feature 016:
- EventProductionTarget: target_batches > 0
- EventAssemblyTarget: target_quantity > 0
- FulfillmentStatus: valid enum values (pending, ready, delivered)

## Migration Requirements

**None** - Feature 017 uses existing schema (v0.6) without modifications.
