# Data Model: Planning Workspace (F039)

**Feature Branch**: `039-planning-workspace`
**Date**: 2026-01-05

## Overview

This document defines the data model for the Planning Workspace feature. It includes one new model (ProductionPlanSnapshot) and one model modification (Event.output_mode).

---

## New Entity: ProductionPlanSnapshot

Persists calculated production plan for an event, enabling staleness detection and plan persistence.

### Schema

```python
class ProductionPlanSnapshot(BaseModel):
    """Persisted production plan calculation for an event."""

    __tablename__ = "production_plan_snapshots"

    # Primary relationship
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"),
                      nullable=False, index=True)

    # Calculation metadata
    calculated_at = Column(DateTime, nullable=False, default=utc_now)

    # Input version tracking (for staleness detection)
    input_hash = Column(String(64), nullable=True)  # SHA256 of inputs (optional backup)
    requirements_updated_at = Column(DateTime, nullable=False)  # Latest target timestamp
    recipes_updated_at = Column(DateTime, nullable=False)  # Latest recipe.last_modified
    bundles_updated_at = Column(DateTime, nullable=False)  # Latest finished_good.updated_at

    # Calculation results (JSON blob for flexibility)
    calculation_results = Column(JSON, nullable=False)
    # Structure:
    # {
    #     "recipe_batches": [
    #         {
    #             "recipe_id": int,
    #             "recipe_name": str,
    #             "units_needed": int,
    #             "batches": int,
    #             "yield_per_batch": int,
    #             "total_yield": int,
    #             "waste_units": int,
    #             "waste_percent": float
    #         }
    #     ],
    #     "aggregated_ingredients": [
    #         {
    #             "ingredient_id": int,
    #             "ingredient_slug": str,
    #             "ingredient_name": str,
    #             "total_quantity": float,
    #             "unit": str
    #         }
    #     ],
    #     "shopping_list": [
    #         {
    #             "ingredient_slug": str,
    #             "needed": float,
    #             "in_stock": float,
    #             "to_buy": float,
    #             "unit": str
    #         }
    #     ]
    # }

    # Status tracking
    is_stale = Column(Boolean, default=False, nullable=False)
    stale_reason = Column(String(200), nullable=True)  # Why plan became stale

    # Shopping status
    shopping_complete = Column(Boolean, default=False, nullable=False)
    shopping_completed_at = Column(DateTime, nullable=True)

    # Relationships
    event = relationship("Event", back_populates="production_plan_snapshots")

    # Constraints
    __table_args__ = (
        # Only one active (non-stale) plan per event
        Index("ix_active_plan_per_event", "event_id", "is_stale",
              postgresql_where=text("is_stale = FALSE")),
    )
```

### Key Methods

```python
def check_staleness(self, session) -> tuple[bool, Optional[str]]:
    """Check if plan is stale based on input timestamps.

    Returns:
        (is_stale: bool, reason: Optional[str])
    """
    # Compare against current model timestamps
    # Return (True, "Recipe 'Chocolate Chip Cookies' modified") if stale

def mark_stale(self, reason: str) -> None:
    """Mark plan as stale with reason."""

def get_recipe_batches(self) -> List[Dict]:
    """Extract recipe batch data from calculation_results."""

def get_shopping_list(self) -> List[Dict]:
    """Extract shopping list from calculation_results."""
```

---

## Modified Entity: Event

Add `output_mode` field to support BUNDLED vs BULK_COUNT requirement entry.

### Schema Change

```python
class OutputMode(enum.Enum):
    """How event requirements are specified."""
    BULK_COUNT = "bulk_count"   # Direct FinishedUnit quantities
    BUNDLED = "bundled"         # FinishedGood/bundle quantities

# Add to Event model:
output_mode = Column(Enum(OutputMode), nullable=True, index=True)
```

### Migration Notes

- Existing events will have `output_mode = NULL`
- UI should prompt user to set output_mode before calculating plan
- Default to BUNDLED for new events (most common use case)

---

## Existing Entities (Reference)

### Event
Primary entity for planning. Links to targets and plan snapshots.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| name | String(200) | Event name |
| event_date | Date | When event occurs |
| date_added | DateTime | Created timestamp |
| last_modified | DateTime | Updated timestamp (auto-update) |
| **output_mode** | Enum | **NEW** - BUNDLED or BULK_COUNT |

**Relationships:**
- `production_targets` -> EventProductionTarget
- `assembly_targets` -> EventAssemblyTarget
- `production_plan_snapshots` -> ProductionPlanSnapshot (NEW)

### EventAssemblyTarget
Links event to bundle requirements.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| event_id | Integer | FK to Event |
| finished_good_id | Integer | FK to FinishedGood |
| target_quantity | Integer | How many bundles needed |
| notes | Text | Optional notes |
| created_at | DateTime | From BaseModel |
| updated_at | DateTime | From BaseModel |

### EventProductionTarget
Links event to recipe batch requirements.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| event_id | Integer | FK to Event |
| recipe_id | Integer | FK to Recipe |
| target_batches | Integer | How many batches needed |
| notes | Text | Optional notes |
| created_at | DateTime | From BaseModel |
| updated_at | DateTime | From BaseModel |

### FinishedGood
Bundle/assembly definition.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| slug | String(100) | Unique identifier |
| display_name | String(200) | User-facing name |
| assembly_type | Enum | Type of assembly |
| created_at | DateTime | From BaseModel |
| updated_at | DateTime | From BaseModel |

**Relationships:**
- `components` -> Composition (bundle contents)

### Composition
Links bundle to its components.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| assembly_id | Integer | FK to parent FinishedGood |
| finished_unit_id | Integer | FK to FinishedUnit (XOR) |
| finished_good_id | Integer | FK to FinishedGood (XOR) - nested |
| packaging_product_id | Integer | FK to Product (XOR) |
| component_quantity | Float | How many per bundle |
| sort_order | Integer | Display order |
| created_at | DateTime | No updated_at! |

### FinishedUnit
Product variant linked to recipe.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| slug | String(100) | Unique identifier |
| display_name | String(200) | User-facing name |
| recipe_id | Integer | FK to Recipe |
| yield_mode | Enum | DISCRETE_COUNT or BATCH_PORTION |
| items_per_batch | Integer | For DISCRETE_COUNT |
| batch_percentage | Decimal | For BATCH_PORTION |
| inventory_count | Integer | Current stock |
| created_at | DateTime | From BaseModel |
| updated_at | DateTime | From BaseModel |

**Key Method:**
- `calculate_batches_needed(quantity)` - Returns recipe batches needed

### Recipe
Production template.

| Field | Type | Notes |
|-------|------|-------|
| id | Integer | PK |
| name | String(200) | Recipe name |
| yield_quantity | Float | Units per batch |
| yield_unit | String(50) | e.g., "cookies" |
| category | String(100) | Recipe category |
| date_added | DateTime | Created (not created_at) |
| last_modified | DateTime | Updated (not updated_at) |

---

## Entity Relationship Diagram

```
Event (1) ----< (N) EventAssemblyTarget >---- (1) FinishedGood
  |                                                    |
  |                                               (components)
  |                                                    |
  +----< (N) EventProductionTarget >---- (1) Recipe    v
  |                                          ^    Composition
  |                                          |         |
  +----< (N) ProductionPlanSnapshot (NEW)    |    (finished_unit_id)
                                             |         |
                                             |         v
                                        FinishedUnit --+
```

---

## Staleness Detection Logic

```python
def is_plan_stale(plan: ProductionPlanSnapshot, session) -> tuple[bool, str]:
    """Check if plan needs recalculation."""

    event = plan.event

    # Check event modification
    if event.last_modified > plan.calculated_at:
        return True, "Event modified since plan calculation"

    # Check assembly targets
    for target in event.assembly_targets:
        if target.updated_at > plan.calculated_at:
            return True, f"Assembly target '{target.finished_good.display_name}' modified"

    # Check production targets
    for target in event.production_targets:
        if target.updated_at > plan.calculated_at:
            return True, f"Production target '{target.recipe.name}' modified"

    # Check recipes in plan
    for recipe_batch in plan.get_recipe_batches():
        recipe = session.get(Recipe, recipe_batch["recipe_id"])
        if recipe.last_modified > plan.calculated_at:
            return True, f"Recipe '{recipe.name}' modified"

    # Check finished goods
    for target in event.assembly_targets:
        fg = target.finished_good
        if fg.updated_at > plan.calculated_at:
            return True, f"Bundle '{fg.display_name}' modified"

        # Check compositions (only has created_at)
        for comp in fg.components:
            if comp.created_at > plan.calculated_at:
                return True, f"Bundle '{fg.display_name}' contents changed"

    return False, None
```

---

## JSON Schema: calculation_results

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["recipe_batches", "aggregated_ingredients", "shopping_list"],
  "properties": {
    "recipe_batches": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["recipe_id", "recipe_name", "units_needed", "batches",
                     "yield_per_batch", "total_yield", "waste_units", "waste_percent"],
        "properties": {
          "recipe_id": {"type": "integer"},
          "recipe_name": {"type": "string"},
          "units_needed": {"type": "integer"},
          "batches": {"type": "integer"},
          "yield_per_batch": {"type": "integer"},
          "total_yield": {"type": "integer"},
          "waste_units": {"type": "integer"},
          "waste_percent": {"type": "number", "minimum": 0, "maximum": 100}
        }
      }
    },
    "aggregated_ingredients": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["ingredient_id", "ingredient_slug", "ingredient_name",
                     "total_quantity", "unit"],
        "properties": {
          "ingredient_id": {"type": "integer"},
          "ingredient_slug": {"type": "string"},
          "ingredient_name": {"type": "string"},
          "total_quantity": {"type": "number"},
          "unit": {"type": "string"}
        }
      }
    },
    "shopping_list": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["ingredient_slug", "needed", "in_stock", "to_buy", "unit"],
        "properties": {
          "ingredient_slug": {"type": "string"},
          "ingredient_name": {"type": "string"},
          "needed": {"type": "number"},
          "in_stock": {"type": "number"},
          "to_buy": {"type": "number"},
          "unit": {"type": "string"}
        }
      }
    }
  }
}
```
