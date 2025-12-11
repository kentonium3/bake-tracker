# Implementation Plan: Event-Centric Production Model

**Branch**: `016-event-centric-production` | **Date**: 2025-12-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/016-event-centric-production/spec.md`

---

## Summary

Add event-production linkage to enable progress tracking and fulfillment workflows. This feature:
- Adds `event_id` FK to ProductionRun and AssemblyRun (nullable, RESTRICT on delete)
- Creates EventProductionTarget and EventAssemblyTarget tables for explicit targets
- Adds `fulfillment_status` to EventRecipientPackage (pending → ready → delivered workflow)
- Extends EventService with target CRUD, progress calculation, and fulfillment methods
- Adds event selector to production/assembly dialogs and Targets tab to Event Detail window

---

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% service coverage
**Target Platform**: Desktop (Windows, macOS, Linux)
**Project Type**: Single desktop application
**Performance Goals**: Sub-second UI response for all operations
**Constraints**: Single-user, local database, offline-capable
**Scale/Scope**: ~100 recipes, ~50 events, ~500 production runs

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Desktop Phase Checks

| Check | Status | Notes |
|-------|--------|-------|
| Does this design block web deployment? | **PASS** | Standard FK relationships, stateless services |
| Is the service layer UI-independent? | **PASS** | All business logic in EventService |
| Are business rules in services, not UI? | **PASS** | Progress calc, status workflow in service layer |
| What's the web migration cost? | **LOW** | Services become API endpoints with minimal changes |

### Principle Compliance

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | **PASS** | Solves real progress tracking need for holiday planning |
| II. Data Integrity | **PASS** | Explicit targets, FK constraints, FIFO unaffected |
| III. Future-Proof Schema | **PASS** | UUID support, standard patterns |
| IV. Test-Driven Development | **REQUIRED** | Service tests before UI implementation |
| V. Layered Architecture | **PASS** | Strict layer separation maintained |
| VI. Migration Safety | **PASS** | Export/import cycle with validation |
| VII. Pragmatic Aspiration | **PASS** | Enables multi-event planning, web-ready |

---

## Project Structure

### Documentation (this feature)

```
kitty-specs/016-event-centric-production/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 entity definitions
├── quickstart.md        # Phase 1 implementation guide
├── contracts/           # Phase 1 service contracts
│   └── event-service-contracts.md
├── checklists/          # Quality checklists
│   └── requirements.md
└── tasks.md             # Phase 2 output (from /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── __init__.py           # Export new classes
│   ├── event.py              # MODIFY: Add FulfillmentStatus, EventProductionTarget, EventAssemblyTarget
│   ├── production_run.py     # MODIFY: Add event_id FK
│   └── assembly_run.py       # MODIFY: Add event_id FK
├── services/
│   ├── batch_production_service.py  # MODIFY: Add event_id param
│   ├── assembly_service.py          # MODIFY: Add event_id param
│   ├── event_service.py             # MODIFY: Add 12 new methods
│   └── import_export_service.py     # MODIFY: Add new entities
└── ui/
    ├── forms/
    │   ├── record_production_dialog.py  # MODIFY: Add event selector
    │   └── record_assembly_dialog.py    # MODIFY: Add event selector
    └── event_detail_window.py           # MODIFY: Add Targets tab

tests/
├── unit/
│   └── services/
│       ├── test_event_service_targets.py      # NEW
│       ├── test_event_service_progress.py     # NEW
│       └── test_event_service_fulfillment.py  # NEW
└── integration/
    └── test_import_export_016.py              # NEW
```

**Structure Decision**: Single project layout following existing bake-tracker conventions.

---

## Complexity Tracking

*No constitution violations requiring justification.*

This feature follows established patterns:
- FK additions to existing tables (standard)
- New junction tables with composite unique constraints (standard)
- Service method parameter additions (backward compatible)
- New UI tab in existing window (standard CustomTkinter pattern)

---

## Implementation Phases

### Phase 1: Model Layer

**Objective**: Add data model changes with FK constraints and relationships.

**Work Packages**:
1. Add `FulfillmentStatus` enum to `src/models/event.py`
2. Add `EventProductionTarget` model with unique constraint on (event_id, recipe_id)
3. Add `EventAssemblyTarget` model with unique constraint on (event_id, finished_good_id)
4. Add `event_id` FK to `ProductionRun` model (nullable, RESTRICT)
5. Add `event_id` FK to `AssemblyRun` model (nullable, RESTRICT)
6. Add `fulfillment_status` column to `EventRecipientPackage`
7. Add relationships to `Event` model
8. Update `src/models/__init__.py` exports

**Testing**: Model unit tests for CRUD, constraints, cascade/restrict behavior

**Dependencies**: None (base layer)

---

### Phase 2: Service Layer - Core Methods

**Objective**: Implement service methods for event_id parameter and target CRUD.

**Work Packages**:
1. Update `BatchProductionService.record_batch_production()` with `event_id` parameter
2. Update `AssemblyService.record_assembly()` with `event_id` parameter
3. Add `EventService.set_production_target()` - create/update
4. Add `EventService.set_assembly_target()` - create/update
5. Add `EventService.get_production_targets()`
6. Add `EventService.get_assembly_targets()`
7. Add `EventService.delete_production_target()`
8. Add `EventService.delete_assembly_target()`

**Testing**: Unit tests for each method, edge cases (duplicates, not found)

**Dependencies**: Phase 1 (models)

---

### Phase 3: Service Layer - Progress & Fulfillment

**Objective**: Implement progress calculation and fulfillment status methods.

**Work Packages**:
1. Add `EventService.get_production_progress()` - aggregate and calculate
2. Add `EventService.get_assembly_progress()` - aggregate and calculate
3. Add `EventService.get_event_overall_progress()` - summary
4. Add `EventService.update_fulfillment_status()` - with transition validation
5. Add `EventService.get_packages_by_status()`

**Testing**: Unit tests for progress calculation (0%, 50%, 100%, >100%), transition validation

**Dependencies**: Phase 2 (target methods)

---

### Phase 4: Import/Export

**Objective**: Extend import/export to handle new entities and fields.

**Work Packages**:
1. Add `EventProductionTarget` to export
2. Add `EventAssemblyTarget` to export
3. Add `event_name` field to ProductionRun export
4. Add `event_name` field to AssemblyRun export
5. Add `fulfillment_status` field to EventRecipientPackage export
6. Handle all new fields in import (resolve event_name to event_id)
7. Handle null event_name for standalone production/assembly

**Testing**: Export/import tests, round-trip validation

**Dependencies**: Phase 3 (services complete)

---

### Phase 5: UI - Event Selectors

**Objective**: Add event selector dropdowns to production/assembly dialogs.

**Work Packages**:
1. Add event selector to `RecordProductionDialog`
   - Dropdown with "(None - standalone)" + events ordered by event_date ascending
   - Pass selected event_id to service
2. Add event selector to `RecordAssemblyDialog`
   - Same pattern as production dialog

**Testing**: Manual UI testing

**Dependencies**: Phase 3 (service methods)

---

### Phase 6: UI - Targets Tab

**Objective**: Add Targets tab to Event Detail window with progress display.

**Work Packages**:
1. Add "Targets" tab to `EventDetailWindow` (after Assignments)
2. Create target list displays (Production Targets, Assembly Targets)
3. Add CTkProgressBar + text label for progress display
4. Add "Add Target" dialogs for production and assembly
5. Add edit/delete functionality for targets
6. Implement refresh to update progress after production

**Testing**: Manual UI testing

**Dependencies**: Phase 5 (event selectors)

---

### Phase 7: UI - Fulfillment Status

**Objective**: Add fulfillment status column to package assignments.

**Work Packages**:
1. Add status column to package assignments view
2. Add dropdown with sequential transition enforcement
3. Style completed status (delivered) differently

**Testing**: Manual UI testing

**Dependencies**: Phase 6 (Targets tab)

---

### Phase 8: Documentation & Final

**Objective**: Update documentation and verify feature complete.

**Work Packages**:
1. Update CLAUDE.md with event-centric model description
2. Update feature_roadmap.md
3. Verify all acceptance criteria from spec
4. Complete migration dry-run test

**Dependencies**: All previous phases

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Schema design source | Review/simplify schema_v0.6_design.md | User preference |
| Migration strategy | Export/recreate/import | Established pattern |
| Event deletion behavior | RESTRICT if production attributed | User preference (changed from SET NULL) |
| Target setting | Manual only (no auto-suggestion) | User preference |
| Progress display | CTkProgressBar + text | User preference |
| Over-production display | Show actual percentage (>100%) | User preference |
| Fulfillment workflow | Sequential (pending→ready→delivered) | User preference |
| Event selector ordering | event_date ascending (nearest first) | From spec clarification |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Event Detail window tab structure | Research confirmed CTkTabview exists; plan for new tab insertion |
| Data loss during migration | Export/import cycle with validation; test round-trip |
| Cascade behavior complexity | Clear documentation of RESTRICT vs CASCADE per relationship |
| Service test coverage | Write tests before UI implementation (TDD) |

---

## Artifacts Generated

| Artifact | Path | Purpose |
|----------|------|---------|
| Research | `kitty-specs/016-event-centric-production/research.md` | Phase 0 findings |
| Data Model | `kitty-specs/016-event-centric-production/data-model.md` | Entity definitions |
| Quickstart | `kitty-specs/016-event-centric-production/quickstart.md` | Implementation guide |
| Contracts | `kitty-specs/016-event-centric-production/contracts/event-service-contracts.md` | Service method specs |

---

## Next Steps

1. Run `/spec-kitty.tasks` to generate work packages
2. Begin implementation with Phase 1 (Model Layer)
3. Follow TDD: write service tests before UI integration
4. Run export/import validation after model changes
