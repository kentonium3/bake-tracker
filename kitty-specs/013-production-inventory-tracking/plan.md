# Implementation Plan: Production & Inventory Tracking

**Branch**: `013-production-inventory-tracking` | **Date**: 2025-12-09 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/013-production-inventory-tracking/spec.md`

## Summary

Add production tracking entities and services to record batch production (Recipe -> FinishedUnit) and assembly runs (FinishedUnit -> FinishedGood) with FIFO consumption, yield-based costing, and full audit trail. This feature implements the core inventory flow: ingredients are consumed during batch production to create FinishedUnits, which are then consumed along with packaging during assembly to create FinishedGoods.

**Technical Approach:**
- Create two new services: `BatchProductionService` and `AssemblyService` (separate from existing event-based `production_service.py`)
- Add 5 new models: `ProductionRun`, `ProductionConsumption`, `AssemblyRun`, `AssemblyFinishedUnitConsumption`, `AssemblyPackagingConsumption`
- Leverage existing `consume_fifo()` with `dry_run=True` for availability checks
- Use `get_aggregated_ingredients()` from Feature 012 for nested recipe support
- Store consumption at ingredient-level (not lot-level) for simplicity

## Technical Context

**Language/Version**: Python 3.10+ (type hints required)
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter (UI out of scope)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service layer coverage required
**Target Platform**: Desktop (macOS/Windows/Linux)
**Project Type**: Single desktop application
**Performance Goals**: Production recording < 2 seconds including all FIFO calculations
**Constraints**: Single-user, single transaction per operation, atomic rollback on failure
**Scale/Scope**: Single user, ~100s of production runs per season

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Feature solves real production tracking need; UI deferred to Feature 014 |
| II. Data Integrity & FIFO Accuracy | PASS | Uses existing `consume_fifo()` for FIFO consumption; cost-at-consumption captured |
| III. Future-Proof Schema | PASS | New models follow BaseModel pattern with UUID support |
| IV. Test-Driven Development | PASS | >70% coverage required; tests will cover happy path, edge cases, errors |
| V. Layered Architecture | PASS | New services in services layer; no UI coupling |
| VI. Migration Safety | PASS | New tables only; no existing data migration required |
| VII. Pragmatic Aspiration | PASS | Clean service layer enables future web API exposure |

**Desktop Phase Checks:**
- Does this design block web deployment? **NO** - Services are UI-independent
- Is the service layer UI-independent? **YES** - Pure business logic
- Are business rules in services, not UI? **YES** - All logic in BatchProductionService/AssemblyService
- What's the web migration cost? **LOW** - Services can be wrapped with API endpoints directly

## Project Structure

### Documentation (this feature)

```
kitty-specs/013-production-inventory-tracking/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity definitions
├── quickstart.md        # Quick reference for implementation
├── contracts/           # Service contracts
└── tasks.md             # Task breakdown (from /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── production_run.py           # NEW: ProductionRun model
│   ├── production_consumption.py   # NEW: Ingredient-level consumption ledger
│   ├── assembly_run.py             # NEW: AssemblyRun model
│   ├── assembly_finished_unit_consumption.py  # NEW: FinishedUnit consumption
│   ├── assembly_packaging_consumption.py      # NEW: Packaging consumption
│   └── __init__.py                 # UPDATE: Export new models
├── services/
│   ├── batch_production_service.py # NEW: Batch production logic
│   ├── assembly_service.py         # NEW: Assembly logic
│   └── __init__.py                 # UPDATE: Export new services
└── tests/
    ├── test_batch_production_service.py  # NEW: BatchProductionService tests
    └── test_assembly_service.py          # NEW: AssemblyService tests
```

**Structure Decision**: Single desktop application structure. New models and services follow existing patterns. Separate services for batch production vs assembly per planning decision.

## Complexity Tracking

*No constitution violations - all choices align with existing patterns.*

| Decision | Rationale | Alternative Considered |
|----------|-----------|------------------------|
| Separate services (not extending production_service.py) | Clean separation of concerns; event-based vs general production | Single service would become too large |
| Ingredient-level consumption (not lot-level) | Simpler storage; lot-level audit trail available via FIFO breakdown at runtime | Lot-level would require more storage, complexity |
| Two assembly consumption tables | Type-safe foreign keys to FinishedUnit and InventoryItem | Single polymorphic table would lose FK constraints |

## Planning Decisions Summary

Captured during planning interrogation:

1. **Dependencies Verified**: Features 011 (Packaging/BOM) and 012 (Nested Recipes) are complete
   - `consume_fifo(dry_run=True)` available in `inventory_item_service.py:225`
   - `get_aggregated_ingredients()` available in `recipe_service.py:1426`
   - `inventory_count` fields on FinishedUnit and FinishedGood models

2. **Service Architecture**: Separate services
   - `BatchProductionService` for Recipe -> FinishedUnit production
   - `AssemblyService` for FinishedUnit -> FinishedGood assembly
   - Existing `production_service.py` unchanged (handles event-based production)

3. **Consumption Ledger Granularity**: Ingredient-level summary
   - One `ProductionConsumption` row per ingredient consumed (not per inventory lot)
   - Stores: production_run_id, ingredient_slug, quantity_consumed, unit, total_cost

4. **Assembly Consumption Tables**: Two separate tables
   - `AssemblyFinishedUnitConsumption`: tracks FinishedUnits consumed
   - `AssemblyPackagingConsumption`: tracks packaging/inventory items consumed
   - Provides type-safe foreign key constraints

## Key Integration Points

### Existing Services to Use

| Service | Method | Purpose |
|---------|--------|---------|
| `inventory_item_service` | `consume_fifo(slug, qty, dry_run=False)` | Deduct ingredients via FIFO |
| `inventory_item_service` | `consume_fifo(slug, qty, dry_run=True)` | Check availability without mutation |
| `recipe_service` | `get_aggregated_ingredients(recipe_id)` | Get flattened ingredients for nested recipes |
| `finished_unit_service` | `adjust_inventory(id, delta)` | Increment/decrement FinishedUnit count |
| `finished_good_service` | `adjust_inventory(id, delta)` | Increment/decrement FinishedGood count |

### Transaction Boundaries

All inventory mutations within a single production/assembly operation MUST occur in a single database transaction:
1. Check availability (dry_run)
2. Consume ingredients/components (actual)
3. Increment output inventory
4. Create run record with consumption ledger
5. Commit OR rollback entire transaction on any failure
