# Data Model: Production Loss Tracking

**Feature**: 025-production-loss-tracking
**Date**: 2025-12-21
**Schema Version**: 0.7 (extends 0.6)

## Overview

This document defines the data model changes for production loss tracking using a hybrid approach:
- **ProductionRun** (enhanced) - Add status and loss quantity for quick queries
- **ProductionLoss** (new) - Detailed loss records with category and cost snapshot

## Entities

### ProductionStatus Enum

Python enum for production outcome classification.

```python
class ProductionStatus(str, Enum):
    """Production run outcome status."""
    COMPLETE = "complete"        # All expected units produced (loss_quantity = 0)
    PARTIAL_LOSS = "partial_loss"  # Some units lost (0 < loss_quantity < expected_yield)
    TOTAL_LOSS = "total_loss"    # All units lost (loss_quantity = expected_yield)
```

### LossCategory Enum

Python enum for loss reason classification.

```python
class LossCategory(str, Enum):
    """Categories for production losses."""
    BURNT = "burnt"                    # Overcooked/burnt items
    BROKEN = "broken"                  # Physical damage during handling
    CONTAMINATED = "contaminated"      # Contamination (hair, debris, etc.)
    DROPPED = "dropped"                # Dropped on floor/ground
    WRONG_INGREDIENTS = "wrong_ingredients"  # Recipe error requiring discard
    OTHER = "other"                    # Catch-all with notes
```

### ProductionRun (Enhanced)

Add fields to existing `ProductionRun` model.

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `production_status` | String(20) | No | `"complete"` | Enum value: complete, partial_loss, total_loss |
| `loss_quantity` | Integer | No | `0` | Number of units lost (expected_yield - actual_yield) |

**Constraints:**
- `loss_quantity >= 0`
- `loss_quantity <= expected_yield`
- `actual_yield + loss_quantity = expected_yield` (enforced in service layer)

**Indexes:**
- `idx_production_run_status` on `production_status`

### ProductionLoss (New Entity)

Detailed loss record linked to ProductionRun.

| Field | Type | Nullable | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | Integer | No | auto | Primary key |
| `uuid` | UUID | No | auto | Unique identifier for import/export |
| `production_run_id` | Integer FK | No | - | Link to ProductionRun |
| `finished_unit_id` | Integer FK | No | - | Link to FinishedUnit (for querying) |
| `loss_category` | String(20) | No | `"other"` | Enum value from LossCategory |
| `loss_quantity` | Integer | No | - | Number of units lost |
| `per_unit_cost` | Numeric(10,4) | No | - | Cost per unit at production time |
| `total_loss_cost` | Numeric(10,4) | No | - | loss_quantity * per_unit_cost |
| `notes` | Text | Yes | - | Optional details about loss |
| `created_at` | DateTime | No | now | Record creation timestamp |
| `updated_at` | DateTime | No | now | Record update timestamp |

**Constraints:**
- `loss_quantity > 0`
- `per_unit_cost >= 0`
- `total_loss_cost >= 0`
- FK to ProductionRun with `ondelete="SET NULL"` (preserve loss records for audit)

**Indexes:**
- `idx_production_loss_run` on `production_run_id`
- `idx_production_loss_finished_unit` on `finished_unit_id`
- `idx_production_loss_category` on `loss_category`
- `idx_production_loss_created` on `created_at`

**Relationships:**
- `ProductionLoss.production_run` -> `ProductionRun` (many-to-one)
- `ProductionLoss.finished_unit` -> `FinishedUnit` (many-to-one)
- `ProductionRun.losses` -> `ProductionLoss` (one-to-many, backref)

## Entity Relationship Diagram

```
+------------------+       +-------------------+
|  ProductionRun   |       |  ProductionLoss   |
+------------------+       +-------------------+
| id (PK)          |<---+  | id (PK)           |
| recipe_id (FK)   |    |  | uuid              |
| finished_unit_id |    +--| production_run_id |
| event_id (FK)    |       | finished_unit_id  |
| num_batches      |       | loss_category     |
| expected_yield   |       | loss_quantity     |
| actual_yield     |       | per_unit_cost     |
| produced_at      |       | total_loss_cost   |
| notes            |       | notes             |
| total_cost       |       | created_at        |
| per_unit_cost    |       | updated_at        |
| production_status| (NEW) +-------------------+
| loss_quantity    | (NEW)
+------------------+
```

## Migration Strategy

Per Constitution Principle VI (Schema Change Strategy), use export/reset/import:

1. **Export**: Run full data export before schema change
2. **Transform**: Update exported production_runs JSON to add:
   - `production_status: "complete"` for all existing records
   - `loss_quantity: 0` for all existing records
   - Empty `losses: []` array
3. **Reset**: Delete database, update models, recreate empty database
4. **Import**: Load transformed data

## Validation Rules

### Service Layer Enforcement

```python
# In batch_production_service.record_batch_production():

# 1. Validate actual_yield <= expected_yield
if actual_yield > expected_yield:
    raise ValueError("Actual yield cannot exceed expected yield")

# 2. Calculate loss_quantity
loss_quantity = expected_yield - actual_yield

# 3. Determine production_status
if loss_quantity == 0:
    production_status = ProductionStatus.COMPLETE
elif loss_quantity == expected_yield:
    production_status = ProductionStatus.TOTAL_LOSS
else:
    production_status = ProductionStatus.PARTIAL_LOSS

# 4. Create ProductionLoss record if loss_quantity > 0
if loss_quantity > 0:
    loss = ProductionLoss(
        production_run_id=run.id,
        finished_unit_id=finished_unit_id,
        loss_category=loss_category or LossCategory.OTHER,
        loss_quantity=loss_quantity,
        per_unit_cost=per_unit_cost,
        total_loss_cost=loss_quantity * per_unit_cost,
        notes=loss_notes,
    )
    session.add(loss)
```

## Import/Export Schema

### Export Format (v1.1)

```json
{
  "version": "1.1",
  "exported_at": "2025-12-21T12:00:00Z",
  "production_runs": [
    {
      "uuid": "...",
      "recipe_name": "Chocolate Chip Cookies",
      "finished_unit_slug": "chocolate-chip-cookie",
      "num_batches": 2,
      "expected_yield": 48,
      "actual_yield": 42,
      "production_status": "partial_loss",
      "loss_quantity": 6,
      "produced_at": "2025-12-21T10:00:00Z",
      "notes": "...",
      "total_ingredient_cost": "12.50",
      "per_unit_cost": "0.2976",
      "event_name": "Christmas 2025",
      "consumptions": [...],
      "losses": [
        {
          "uuid": "...",
          "loss_category": "burnt",
          "loss_quantity": 6,
          "per_unit_cost": "0.2976",
          "total_loss_cost": "1.7856",
          "notes": "Oven ran hot"
        }
      ]
    }
  ]
}
```

## Backward Compatibility

- Existing production runs imported with `production_status=complete`, `loss_quantity=0`
- No breaking changes to existing API contracts
- UI displays loss columns with "-" for records without losses
