# Implementation Plan: Event Management & Planning Data Model

**Branch**: `068-event-management-planning-data-model` | **Date**: 2026-01-26 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/068-event-management-planning-data-model/spec.md`

## Summary

F068 establishes the complete planning data model and basic event management UI as the foundation for all subsequent planning features (F069-F079). This includes:
- Extending the existing Event model with `expected_attendees` and `plan_state` fields
- Creating 4 new planning tables (`event_recipes`, `event_finished_goods`, `batch_decisions`, `plan_amendments`)
- Updating `plan_snapshots` table with `snapshot_type` field
- Adding planning-related methods to existing EventService
- Creating a new Planning workspace tab for event management UI

## Technical Context

**Language/Version**: Python 3.10+ (per Constitution)
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM)
**Storage**: SQLite with WAL mode
**Testing**: pytest with >70% coverage target for service layer
**Target Platform**: Desktop (macOS, Windows)
**Project Type**: Single desktop application
**Performance Goals**: CRUD operations <100ms
**Constraints**: Export/Reset/Import cycle for schema changes (Constitution Principle VI)
**Scale/Scope**: Single user, ~10-50 events per year

## Planning Decisions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Event Model Approach | **Extend existing** | Add `expected_attendees` and `plan_state` to existing Event model; avoids duplication |
| Service Layer | **Extend EventService** | Add planning methods to existing service rather than new PlanningService |
| UI Location | **New Planning tab** | Dedicated workspace becomes primary planning hub; legacy tabs removed after Phase 2 |
| New Tables | **Create 4 separate tables** | `event_recipes`, `event_finished_goods`, `batch_decisions`, `plan_amendments` |
| Existing Target Tables | **Keep separate** | `EventProductionTarget` and `EventAssemblyTarget` remain for production tracking |
| Schema Strategy | **Export/Reset/Import** | Follow Constitution Principle VI; validates import/export pipeline |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. User-Centric Design** | ✅ PASS | Planning workspace matches natural workflow; non-technical user tested |
| **II. Data Integrity & FIFO** | ✅ PASS | No FIFO impact; planning data is metadata |
| **III. Future-Proof Schema** | ✅ PASS | New tables designed for Phase 2+3 planning features |
| **IV. Test-Driven Development** | ✅ PASS | Service methods will have unit tests >70% coverage |
| **V. Layered Architecture** | ✅ PASS | UI → Services → Models; no cross-layer violations |
| **VI. Schema Change Strategy** | ✅ PASS | Export/Reset/Import cycle; no migration scripts |
| **VII. Pragmatic Aspiration** | ✅ PASS | Desktop first; service layer web-ready |

**Desktop Phase Checks:**
- Does this design block web deployment? → NO (service layer is UI-independent)
- Is the service layer UI-independent? → YES (extends existing EventService pattern)
- Does this support AI-assisted JSON import? → YES (new tables added to import/export)
- Web migration cost? → LOW (clean service layer, standard CRUD)

## Project Structure

### Documentation (this feature)

```
kitty-specs/068-event-management-planning-data-model/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
└── tasks.md             # Phase 2 output (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── event.py                    # MODIFY: Add expected_attendees, plan_state fields
│   ├── planning_snapshot.py        # MODIFY: Add snapshot_type field
│   ├── event_recipe.py             # NEW: Event-recipe junction table
│   ├── event_finished_good.py      # NEW: Event FG selections with quantities
│   ├── batch_decision.py           # NEW: User's batch choices per recipe
│   ├── plan_amendment.py           # NEW: Amendment tracking (Phase 3 prep)
│   └── __init__.py                 # MODIFY: Export new models
├── services/
│   └── event_service.py            # MODIFY: Add planning CRUD methods
└── ui/
    ├── planning_tab.py             # NEW: Planning workspace tab
    └── forms/
        └── event_planning_form.py  # NEW: Create/Edit event dialog for planning

src/tests/
├── test_event_planning.py          # NEW: Unit tests for planning service methods
└── test_planning_models.py         # NEW: Model relationship tests
```

**Structure Decision**: Single desktop application structure. New models in `src/models/`, service extensions in existing `event_service.py`, new UI components in `src/ui/`.

## Complexity Tracking

*No Constitution violations requiring justification.*

| Aspect | Complexity | Justification |
|--------|------------|---------------|
| 4 new tables | Medium | Required for Phase 2 planning features; defined upfront to prevent schema churn |
| New UI tab | Low | Standard pattern; follows existing tab structure |
| Service extension | Low | Follows existing EventService patterns exactly |

## Parallel Work Analysis

### Dependency Graph

```
Foundation (WP01-02)
├── WP01: Event model changes + new planning models
└── WP02: Service layer extensions
    │
    ↓
UI Layer (WP03-04, can run in parallel after WP01-02)
├── WP03: Planning tab skeleton
└── WP04: Event CRUD dialogs
    │
    ↓
Integration (WP05)
└── WP05: Integration tests + import/export validation
```

### Work Distribution

- **Sequential work**: WP01 (models) must complete before WP02 (service); WP01-02 must complete before WP03-04
- **Parallel streams**: WP03 (tab skeleton) and WP04 (dialogs) can run concurrently after foundation
- **File boundaries**:
  - WP01 owns: `src/models/event.py`, `src/models/event_recipe.py`, `src/models/event_finished_good.py`, `src/models/batch_decision.py`, `src/models/plan_amendment.py`, `src/models/planning_snapshot.py`
  - WP02 owns: `src/services/event_service.py`, `src/tests/test_event_planning.py`
  - WP03 owns: `src/ui/planning_tab.py`
  - WP04 owns: `src/ui/forms/event_planning_form.py`

### Coordination Points

- **Sync after WP01-02**: Verify models and service work together before UI work
- **Integration test**: WP05 validates full flow end-to-end
