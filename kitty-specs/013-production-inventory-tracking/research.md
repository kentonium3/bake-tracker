# Research: Production & Inventory Tracking

**Feature**: 013-production-inventory-tracking
**Date**: 2025-12-09

## Research Summary

This document captures decisions, rationale, and evidence gathered during the planning phase for Production & Inventory Tracking.

## Decision Log

### Decision 1: Service Architecture

**Decision**: Create two separate services (`BatchProductionService` and `AssemblyService`) rather than extending `production_service.py`

**Rationale**:
- Existing `production_service.py` handles event-based production (recording batches for specific events)
- New services handle general inventory tracking independent of events
- Separation of concerns keeps each service focused
- Avoids bloating existing service with unrelated functionality

**Alternatives Considered**:
- Single service extension: Rejected because it would make `production_service.py` too large and mix concerns

**Evidence**: Reviewed `src/services/production_service.py` - it's tightly coupled to Event model and handles package status management, which is orthogonal to general batch production tracking.

### Decision 2: Consumption Ledger Granularity

**Decision**: Store ingredient-level consumption summaries, not lot-level details

**Rationale**:
- Simpler storage model (one row per ingredient per production run)
- Lot-level detail is available at runtime via `consume_fifo()` breakdown
- Sufficient for cost tracking and audit purposes
- Reduces database complexity

**Alternatives Considered**:
- Lot-level storage: Would provide permanent record of exact inventory items consumed but adds storage overhead and complexity

**Evidence**: User confirmed ingredient-level is sufficient during planning interrogation.

### Decision 3: Assembly Consumption Tables

**Decision**: Use two separate tables for assembly consumption tracking

**Rationale**:
- `AssemblyFinishedUnitConsumption`: Foreign key to `finished_units.id`
- `AssemblyPackagingConsumption`: Foreign key to `products.id` (via FIFO consumption)
- Type-safe foreign key constraints
- Clear separation of component types

**Alternatives Considered**:
- Single polymorphic table with `component_type` discriminator: Would lose foreign key constraint benefits

**Evidence**: User confirmed separate tables during planning interrogation.

### Decision 4: FinishedUnit Selection During Production

**Decision**: User must specify `finished_unit_id` when recording batch production

**Rationale**:
- A recipe can have multiple FinishedUnits (e.g., "Sugar Cookie - 48 count" vs "Sugar Cookie - Party Size")
- System cannot automatically determine which FinishedUnit to increment
- Each FinishedUnit traces back to exactly one recipe (1:N relationship)

**Evidence**: Clarified in spec.md Session 2025-12-09 clarifications.

## Dependency Verification

### Feature 011 (Packaging Materials & BOM)
- **Status**: Complete
- **Evidence**: `Composition` model includes `packaging_product_id` column
- **Integration**: Assembly service will query `Composition` for packaging requirements

### Feature 012 (Nested Recipes)
- **Status**: Complete
- **Evidence**: `get_aggregated_ingredients()` exists at `recipe_service.py:1426`
- **Integration**: BatchProductionService will use this for nested recipe ingredient aggregation

### FIFO Consumption
- **Status**: Available
- **Evidence**: `consume_fifo(ingredient_slug, quantity, dry_run=False)` at `inventory_item_service.py:225`
- **Features**:
  - `dry_run=True` mode for availability checking
  - Returns breakdown with per-lot details and costs
  - Handles unit conversion automatically

### Inventory Count Fields
- **Status**: Available
- **Evidence**:
  - `FinishedUnit.inventory_count` at `finished_unit.py:98`
  - `FinishedGood.inventory_count` at `finished_good.py:76`
- **Constraints**: Both have `CHECK >= 0` constraints

## Transaction Pattern Research

### Current Pattern in Codebase
The codebase uses `session_scope()` context manager for transaction management:

```python
from src.services.database import session_scope

with session_scope() as session:
    # All operations within this block are atomic
    # Automatic commit on success, rollback on exception
```

### Production Service Pattern
New services will follow this pattern:
1. Start transaction
2. Perform all read operations (availability checks)
3. Perform all write operations (consumption, inventory updates, record creation)
4. Commit atomically or rollback on any failure

## Open Questions (Resolved)

All questions from spec clarification have been resolved:
- Q: How to determine FinishedUnit for production? A: User specifies explicitly
- Q: Where is packaging defined? A: In Composition BOM (assembly only, not batch production)
- Q: Retention policy? A: Retain indefinitely (single user prototype)

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| FIFO shortfall during production | Medium | Medium | Pre-flight availability check with clear error messaging |
| Transaction timeout on large batches | Low | Medium | Single recipe typically has <20 ingredients; timeout unlikely |
| Concurrent production attempts | N/A | N/A | Single-user app; transaction isolation sufficient |
| Unit conversion failures | Low | High | Use existing `convert_any_units()` with clear error on failure |

## References

- `src/services/inventory_item_service.py` - FIFO consumption implementation
- `src/services/recipe_service.py` - Nested recipe aggregation
- `src/models/finished_unit.py` - FinishedUnit model with inventory_count
- `src/models/finished_good.py` - FinishedGood model with inventory_count
- `src/models/composition.py` - BOM/composition relationships
- `src/services/production_service.py` - Existing event-based production (reference pattern)
