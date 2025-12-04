# Implementation Plan: Production Tracking

**Branch**: `008-production-tracking` | **Date**: 2025-12-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/008-production-tracking/spec.md`

## Summary

Add production lifecycle tracking to the bake-tracker application. Users can record when recipe batches are produced (consuming pantry inventory via FIFO with actual cost capture), track package assembly and delivery status, and view production progress across all events in a unified dashboard with actual vs planned cost comparisons.

## Technical Context

**Language/Version**: Python 3.10+ (minimum for type hints)
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM), pytest (testing)
**Storage**: SQLite with WAL mode (local database)
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (macOS, Windows, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Dashboard loads within 2 seconds for 10 concurrent events
**Constraints**: Single-user, offline-capable, FIFO accuracy required
**Scale/Scope**: Single user, ~10-20 events per year, ~50 recipes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Pre-Design | Post-Design | Notes |
|-----------|------------|-------------|-------|
| I. Layered Architecture | PASS | PASS | ProductionRecord in models, ProductionService in services, ProductionTab in ui |
| II. Build for Today | PASS | PASS | Single-user desktop focus, no multi-user complexity |
| III. FIFO Accuracy | PASS | PASS | Uses existing `consume_fifo()` with `dry_run=False` for actual consumption |
| IV. User-Centric Design | PASS | PASS | Dashboard provides at-a-glance visibility, status buttons are intuitive |
| V. Test-Driven Development | REQUIRED | REQUIRED | Service layer tests before implementation |
| VI. Migration Safety | PASS | PASS | New table + ALTER TABLE, both reversible |

## Project Structure

### Documentation (this feature)

```
kitty-specs/008-production-tracking/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output - technical research
├── data-model.md        # Phase 1 output - entity definitions
├── quickstart.md        # Phase 1 output - implementation guide
├── contracts/           # Phase 1 output - service interfaces
│   └── production_service.md
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── __init__.py              # MODIFY: Export new models
│   ├── event.py                 # MODIFY: Add status fields to EventRecipientPackage
│   ├── production_record.py     # NEW: ProductionRecord model
│   └── package_status.py        # NEW: PackageStatus enum
├── services/
│   ├── __init__.py              # MODIFY: Export production_service
│   └── production_service.py    # NEW: Production business logic
├── ui/
│   ├── main_window.py           # MODIFY: Add Production tab
│   └── production_tab.py        # NEW: Production dashboard UI
└── tests/
    └── services/
        └── test_production_service.py  # NEW: Service tests

```

**Structure Decision**: Existing single-project structure. New files follow established patterns in src/models/, src/services/, src/ui/.

## Dependencies

### Feature Dependencies

| Feature | Status | Required For |
|---------|--------|--------------|
| Feature 005 (FIFO Recipe Costing) | Complete | `consume_fifo()` for actual inventory consumption |
| Feature 006 (Event Planning) | Complete | `get_recipe_needs()` for calculating required batches |

### Key Existing Functions

| Function | Location | Usage |
|----------|----------|-------|
| `consume_fifo(slug, qty, dry_run)` | `src/services/pantry_service.py:226` | Consume pantry inventory, get actual FIFO cost |
| `get_recipe_needs(event_id)` | `src/services/event_service.py:777` | Calculate batches needed per recipe for an event |
| `get_shopping_list(event_id)` | `src/services/event_service.py:901` | Get ingredient needs with variant recommendations |

## Database Changes

### New Table: production_records

| Column | Type | Constraints |
|--------|------|-------------|
| id | INTEGER | PRIMARY KEY |
| uuid | TEXT | NOT NULL UNIQUE |
| event_id | INTEGER | NOT NULL, FK -> events.id ON DELETE CASCADE |
| recipe_id | INTEGER | NOT NULL, FK -> recipes.id ON DELETE RESTRICT |
| batches | INTEGER | NOT NULL, CHECK > 0 |
| actual_cost | NUMERIC(10,4) | NOT NULL, CHECK >= 0 |
| produced_at | TIMESTAMP | NOT NULL, DEFAULT NOW |
| notes | TEXT | NULLABLE |
| created_at | TIMESTAMP | NOT NULL, DEFAULT NOW |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT NOW |

Indexes: `(event_id, recipe_id)`, `event_id`, `recipe_id`, `produced_at`

### Alter Table: event_recipient_packages

| Column | Type | Constraints |
|--------|------|-------------|
| status | TEXT | NOT NULL, DEFAULT 'pending', CHECK IN ('pending', 'assembled', 'delivered') |
| delivered_to | TEXT | NULLABLE |

Index: `status`

## Implementation Phases

### Phase 1: Models & Migration

1. Create `PackageStatus` enum
2. Create `ProductionRecord` model
3. Add status fields to `EventRecipientPackage`
4. Add `production_records` relationship to `Event`
5. Write and run database migration
6. Update model exports in `__init__.py`

### Phase 2: Service Layer (TDD)

1. Write tests for `record_production()`
2. Implement `record_production()` - core FIFO consumption
3. Write tests for `get_production_progress()`
4. Implement `get_production_progress()`
5. Write tests for `update_package_status()`
6. Implement `update_package_status()` with transition validation
7. Write tests for `get_dashboard_summary()`
8. Implement `get_dashboard_summary()`
9. Write tests for `get_recipe_cost_breakdown()`
10. Implement `get_recipe_cost_breakdown()`

### Phase 3: UI Layer

1. Create `ProductionTab` frame with event list
2. Add recipe production recording form
3. Add package status toggle buttons
4. Add progress bars and cost comparison display
5. Integrate tab into `MainWindow`
6. Wire up callbacks to service layer

### Phase 4: Integration & Polish

1. End-to-end testing with real database
2. Edge case handling (insufficient inventory, over-production)
3. UI polish (loading states, error messages)
4. Documentation updates

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| FIFO consumption is destructive | Add confirmation dialog before recording production |
| Status transitions are irreversible | Clear UI feedback, no rollback as per spec |
| Cost mismatch with estimates | Display variance clearly, this is expected behavior |

## Complexity Tracking

*No constitution violations requiring justification.*

## Artifacts Generated

| Artifact | Path | Status |
|----------|------|--------|
| Research | `kitty-specs/008-production-tracking/research.md` | Complete |
| Data Model | `kitty-specs/008-production-tracking/data-model.md` | Complete |
| Service Contract | `kitty-specs/008-production-tracking/contracts/production_service.md` | Complete |
| Quickstart | `kitty-specs/008-production-tracking/quickstart.md` | Complete |

## Next Steps

Run `/spec-kitty.tasks` to generate atomic work packages for implementation.
