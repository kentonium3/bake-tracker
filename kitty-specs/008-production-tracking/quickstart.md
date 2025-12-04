# Quickstart: Production Tracking (Feature 008)

**Branch**: `008-production-tracking`
**Date**: 2025-12-04

## What We're Building

A production lifecycle tracking system that:
1. Records when recipe batches are produced (with FIFO inventory consumption)
2. Tracks package status (pending -> assembled -> delivered)
3. Shows production progress across all events in a dashboard
4. Compares actual vs planned costs at event and recipe levels

## Key Files to Create

```
src/
├── models/
│   ├── production_record.py      # NEW: ProductionRecord model
│   └── package_status.py         # NEW: PackageStatus enum
├── services/
│   └── production_service.py     # NEW: Production business logic
├── ui/
│   └── production_tab.py         # NEW: Top-level production dashboard
└── tests/
    └── services/
        └── test_production_service.py  # NEW: Service tests
```

## Key Files to Modify

```
src/
├── models/
│   ├── __init__.py               # Export new models
│   └── event.py                  # Add status fields to EventRecipientPackage
├── services/
│   └── __init__.py               # Export production_service
└── ui/
    └── main_window.py            # Add Production tab
```

## Implementation Order

### 1. Models (Foundation)

1. Create `PackageStatus` enum in `src/models/package_status.py`
2. Create `ProductionRecord` model in `src/models/production_record.py`
3. Update `EventRecipientPackage` in `src/models/event.py` to add status fields
4. Update `Event` model to add production_records relationship
5. Run database migration

### 2. Service Layer (Business Logic)

1. Create `src/services/production_service.py` with:
   - `record_production()` - Core function, consumes pantry via FIFO
   - `get_production_progress()` - Aggregates progress data
   - `update_package_status()` - Status transitions with validation
   - `get_dashboard_summary()` - Multi-event overview
   - `get_recipe_cost_breakdown()` - Cost drill-down

2. Write tests for each service function (TDD)

### 3. UI Layer (User Interface)

1. Create `src/ui/production_tab.py` with:
   - Event list with progress bars
   - Recipe production form
   - Package status toggle buttons
   - Cost comparison display

2. Add tab to main window navigation

## Code Snippets

### Recording Production (Service)

```python
def record_production(event_id: int, recipe_id: int, batches: int, notes: str = None):
    # 1. Get recipe and its ingredients
    recipe = get_recipe(recipe_id)

    # 2. Calculate quantities for N batches
    for ri in recipe.recipe_ingredients:
        qty_needed = ri.quantity * batches

        # 3. Consume via FIFO (actual consumption, not dry run)
        result = pantry_service.consume_fifo(
            ingredient_slug=ri.ingredient.slug,
            quantity_needed=qty_needed,
            dry_run=False  # Actually consume!
        )

        if not result["satisfied"]:
            raise InsufficientInventoryError(...)

        total_cost += result["total_cost"]

    # 4. Create production record with actual cost
    record = ProductionRecord(
        event_id=event_id,
        recipe_id=recipe_id,
        batches=batches,
        actual_cost=total_cost,
        notes=notes
    )
    return record
```

### Calculating Progress

```python
def get_production_progress(event_id: int):
    # Get required batches from existing function
    recipe_needs = event_service.get_recipe_needs(event_id)

    # Get produced batches
    produced = session.query(
        ProductionRecord.recipe_id,
        func.sum(ProductionRecord.batches)
    ).filter(
        ProductionRecord.event_id == event_id
    ).group_by(ProductionRecord.recipe_id).all()

    # Merge and return
    ...
```

## Testing Strategy

1. **Unit tests**: Mock `consume_fifo()`, test business logic
2. **Integration tests**: Real database, verify FIFO consumption
3. **Edge cases**:
   - Insufficient inventory
   - Over-production warning
   - Invalid status transitions
   - Empty events

## Dependencies

- Feature 005: FIFO Recipe Costing (`consume_fifo()`)
- Feature 006: Event Planning (`get_recipe_needs()`)
- Existing: PantryService, RecipeService, EventService
