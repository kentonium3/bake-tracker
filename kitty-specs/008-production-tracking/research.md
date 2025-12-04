# Research: Production Tracking (Feature 008)

**Branch**: `008-production-tracking`
**Date**: 2025-12-04
**Status**: Complete

## Research Summary

This document captures technical research conducted during the planning phase to inform implementation decisions.

## Decisions

### D1: Cost Capture Strategy

**Decision**: Store actual costs as a snapshot directly on ProductionRecord

**Rationale**: Simpler model without audit trail to specific pantry consumption records. The user needs to know "this batch cost $X" but doesn't need to trace back to "which specific butter lot was used."

**Alternatives Considered**:
- Link ProductionRecord to PantryConsumption records (rejected: adds complexity for traceability the user doesn't need)

### D2: Package Status Location

**Decision**: Add `status` and `delivered_to` fields to `EventRecipientPackage` model

**Rationale**: The same Package template can be assigned to multiple recipients in an event. Each assignment has its own lifecycle (pending -> assembled -> delivered). Status belongs on the assignment, not the template.

**Alternatives Considered**:
- Add status to Package model (rejected: same Package used across recipients would have single shared status)

### D3: Production Scoping

**Decision**: Production records are event-scoped. Required batches calculated by aggregating from package chain.

**Rationale**: Enables "X of Y batches complete" visibility. The aggregation chain already exists in `event_service.get_recipe_needs()`.

**Alternatives Considered**:
- Standalone production unlinked to events (rejected: loses planning context)

### D4: Dashboard Location

**Decision**: Top-level Production tab showing all active events

**Rationale**: User wants unified view across all events, not navigating into each event separately.

### D5: Cost Comparison Granularity

**Decision**: Both event-level and recipe-level actual vs planned comparison

**Rationale**: Event summary provides quick overview; recipe drill-down helps identify cost variances.

## Existing Infrastructure

### Key Functions (Can Reuse)

| Function | Location | Purpose |
|----------|----------|---------|
| `consume_fifo()` | `src/services/pantry_service.py:226` | FIFO inventory consumption with actual cost calculation |
| `get_recipe_needs()` | `src/services/event_service.py:777` | Calculate batches needed per recipe for an event |
| `get_shopping_list()` | `src/services/event_service.py:901` | Calculate ingredient needs with variant recommendations |

### consume_fifo() API

```python
def consume_fifo(
    ingredient_slug: str,
    quantity_needed: Decimal,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Returns:
        - "consumed" (Decimal): Amount consumed in recipe_unit
        - "breakdown" (List[Dict]): Per-lot consumption details
        - "shortfall" (Decimal): Amount not available (0.0 if satisfied)
        - "satisfied" (bool): True if fully consumed
        - "total_cost" (Decimal): Total FIFO cost of consumed portion
    """
```

**Usage for Production**:
- Call with `dry_run=False` to actually consume pantry inventory
- `total_cost` returned is the actual FIFO cost to store on ProductionRecord

### get_recipe_needs() API

```python
def get_recipe_needs(event_id: int) -> List[Dict[str, Any]]:
    """
    Returns list of dicts:
        - recipe_id: int
        - recipe_name: str
        - total_units_needed: int
        - batches_needed: int (calculated from total_units / items_per_batch)
        - items_per_batch: int
    """
```

**Usage for Production**:
- Provides "Y" in "X of Y batches complete"
- Query ProductionRecord to get "X" (sum of batches produced per recipe)

### Existing Model Chain

```
Event
  -> EventRecipientPackage (assignment, needs status field)
     -> Package (template)
        -> PackageFinishedGood (junction)
           -> FinishedGood (assembly)
              -> Composition (junction)
                 -> FinishedUnit (items from recipe)
                    -> Recipe (what gets "produced")
                       -> RecipeIngredient
                          -> Ingredient (slug used for FIFO)
```

## Service Patterns

Existing services use module-level functions with `session_scope()` context manager:

```python
from src.services.database import session_scope

def my_function(...) -> ReturnType:
    try:
        with session_scope() as session:
            # Query and business logic
            return result
    except SQLAlchemyError as e:
        raise DatabaseError(f"Failed to do thing: {str(e)}")
```

This pattern should be followed for `production_service.py`.

## Constitution Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Layered Architecture | COMPLIANT | New ProductionService in services layer, ProductionRecord in models layer |
| II. Build for Today | COMPLIANT | Single-user, desktop focus. No multi-user or distributed complexity. |
| III. FIFO Accuracy | COMPLIANT | Uses existing `consume_fifo()` for actual consumption |
| IV. User-Centric Design | COMPLIANT | Dashboard provides at-a-glance progress visibility |
| V. Test-Driven Development | REQUIRED | Service layer needs >70% coverage |
| VI. Migration Safety | REQUIRED | New ProductionRecord table, EventRecipientPackage schema change needs migration |

## Open Questions (Resolved)

All planning questions have been resolved through stakeholder discovery:

1. ~~Cost capture strategy~~ -> Snapshot on ProductionRecord
2. ~~Package status location~~ -> EventRecipientPackage
3. ~~Production scoping~~ -> Event-scoped with aggregated requirements
4. ~~Dashboard location~~ -> Top-level tab
5. ~~Cost comparison granularity~~ -> Both levels
