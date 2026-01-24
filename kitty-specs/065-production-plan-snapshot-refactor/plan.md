# Implementation Plan: Production Plan Snapshot Refactor

**Branch**: `065-production-plan-snapshot-refactor` | **Date**: 2025-01-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/kitty-specs/065-production-plan-snapshot-refactor/spec.md`

## Summary

Refactor ProductionPlanSnapshot from a calculation cache (Pattern C) into a true snapshot orchestration container (Pattern A). This completes the definition/instantiation separation by:
1. Removing calculation_results JSON blob and staleness tracking fields
2. Creating RecipeSnapshot and FinishedGoodSnapshot at planning time (not execution time)
3. Linking targets to their snapshots via new FK fields
4. Computing batch requirements on-demand from snapshots instead of caching

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: SQLAlchemy 2.x, CustomTkinter
**Storage**: SQLite with WAL mode
**Testing**: pytest (>70% service layer coverage required)
**Target Platform**: Desktop (Windows/macOS/Linux)
**Project Type**: Single desktop application
**Performance Goals**: On-demand calculation under 5 seconds
**Constraints**: Reset/re-import migration strategy (no Alembic scripts)
**Scale/Scope**: Single-user desktop application

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Refactoring improves data stability; no user workflow changes |
| II. Data Integrity & FIFO | PASS | Immutable snapshots improve data integrity |
| III. Future-Proof Schema | PASS | Adds snapshot FKs; nullable for backward compatibility |
| IV. Test-Driven Development | PASS | Unit tests required for all service changes |
| V. Layered Architecture | PASS | Changes span Models and Services only; UI receives calculated results |
| VI. Schema Change Strategy | PASS | Using reset/re-import pattern per constitution |
| VII. Pragmatic Aspiration | PASS | Service layer changes are web-migration ready |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```
kitty-specs/065-production-plan-snapshot-refactor/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output - architectural research
├── data-model.md        # Phase 1 output - schema changes
├── checklists/          # Quality checklists
│   └── requirements.md  # Spec quality validation
└── tasks/               # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   ├── production_plan_snapshot.py  # MODIFY: remove cache fields
│   ├── event.py                      # MODIFY: add snapshot FKs to targets
│   ├── recipe_snapshot.py            # MODIFY: make production_run_id nullable
│   └── finished_good_snapshot.py     # VERIFY: planning context support (F064)
├── services/
│   ├── planning/
│   │   ├── planning_service.py       # MODIFY: create snapshots at plan time
│   │   └── batch_calculation.py      # VERIFY: snapshot-aware calculation
│   ├── batch_production_service.py   # MODIFY: reuse planning snapshots
│   ├── assembly_service.py           # MODIFY: reuse planning snapshots
│   ├── recipe_snapshot_service.py    # MODIFY: support planning context
│   └── planning_snapshot_service.py  # ORCHESTRATION: existing service
└── ui/
    └── [planning views]              # MODIFY: remove staleness UI, use on-demand calc

src/tests/
├── unit/
│   ├── test_planning_service.py      # NEW/MODIFY: snapshot creation tests
│   ├── test_production_service.py    # MODIFY: snapshot reuse tests
│   └── test_assembly_service.py      # MODIFY: snapshot reuse tests
└── integration/
    └── test_planning_workflow.py     # NEW: end-to-end plan → production flow
```

**Structure Decision**: Single project structure with existing layered architecture. All changes within existing directory structure.

## Architectural Analysis

### Current State (Pattern C - Calculation Cache)

```
ProductionPlanSnapshot
├── calculation_results (JSON blob)     ← REMOVE
├── requirements_updated_at             ← REMOVE
├── recipes_updated_at                  ← REMOVE
├── bundles_updated_at                  ← REMOVE
├── is_stale / stale_reason             ← REMOVE
└── event_id, calculated_at             ← KEEP

Planning Workflow:
  Event + Targets → calculate_plan() → Store in JSON → Return cached

Production Workflow:
  ProductionRun → Create new RecipeSnapshot → No link to plan
```

### Target State (Pattern A - Snapshot Container)

```
ProductionPlanSnapshot (lightweight)
├── event_id                            ← KEEP
├── calculated_at                       ← KEEP (rename consideration)
├── shopping_complete/completed_at      ← KEEP
└── [references snapshots via targets]

EventProductionTarget
├── recipe_id                           ← EXISTING
└── recipe_snapshot_id (FK)             ← NEW

EventAssemblyTarget
├── finished_good_id                    ← EXISTING
└── finished_good_snapshot_id (FK)      ← NEW

Planning Workflow:
  Event + Targets → create_plan() → Create snapshots → Link to targets → Return

View Workflow:
  Event → get_plan_summary() → Calculate from snapshots → Return (no cache)

Production Workflow:
  ProductionRun → Check target.recipe_snapshot_id → Reuse if exists, else create
```

### Key Design Decisions

1. **Dual Context FKs on Snapshots**
   - RecipeSnapshot: `production_run_id` (nullable) OR planning context
   - FinishedGoodSnapshot: `assembly_run_id` (nullable) OR `planning_snapshot_id`
   - At least one context FK should be set

2. **Snapshot Timing**
   - Planning: snapshots created when plan is finalized (before any execution)
   - Production/Assembly: reuse planning snapshots if available; create new only for legacy/ad-hoc

3. **Calculation Strategy**
   - On-demand: compute batch requirements from snapshots when viewed
   - No caching: removes entire staleness detection subsystem
   - Performance acceptable: <5 seconds for typical event sizes

4. **Backward Compatibility**
   - Nullable FK on targets (legacy events have no snapshots)
   - Production/assembly services create snapshots at execution if target has no snapshot
   - Gradual migration: new plans get snapshots, old plans work via fallback

## Session Management Requirements

Per CLAUDE.md session management rules, all service functions must:

1. Accept optional `session=None` parameter
2. Pass session to nested service calls
3. Keep ORM objects within same session scope for modifications

**Critical Path**: `planning_service.create_plan()` must pass session to:
- `recipe_snapshot_service.create_recipe_snapshot()`
- `finished_good_service.create_finished_good_snapshot()` (if F064 pattern)
- Target modifications (setting snapshot_id FKs)

## Implementation Phases

### Phase 1: Model Changes (Foundation)

1. Remove fields from ProductionPlanSnapshot model
2. Make RecipeSnapshot.production_run_id nullable
3. Add RecipeSnapshot.planning_snapshot_id FK (optional - consider if needed)
4. Add EventProductionTarget.recipe_snapshot_id FK
5. Add EventAssemblyTarget.finished_good_snapshot_id FK
6. Verify FinishedGoodSnapshot already supports planning context (F064)

### Phase 2: Service Layer - Snapshot Creation

1. Update recipe_snapshot_service to accept planning context
2. Update planning_service to create snapshots at plan time
3. Create snapshots for each production target (RecipeSnapshot)
4. Create snapshots for each assembly target (FinishedGoodSnapshot)
5. Link targets to their snapshots (set FK values)
6. All operations in single transaction

### Phase 3: Service Layer - Snapshot Reuse

1. Update batch_production_service to check for existing snapshot
2. Update assembly_service to check for existing snapshot
3. Reuse planning snapshot if available
4. Create new snapshot only for legacy/ad-hoc production

### Phase 4: On-Demand Calculation

1. Add get_plan_summary() function for on-demand calculation
2. Calculate batch requirements from snapshots
3. Calculate shopping list from snapshots
4. Remove calculation_results access patterns
5. Remove staleness detection code

### Phase 5: UI Updates

1. Remove staleness warning UI components
2. Update plan display to use on-demand calculation
3. Update shopping list generation to use on-demand calculation
4. Verify performance target (<5 seconds)

### Phase 6: Cleanup & Testing

1. Remove unused staleness-related methods
2. Comprehensive unit tests for snapshot creation
3. Integration tests for plan → production flow
4. Backward compatibility tests for legacy events

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Performance of on-demand calculation | Acceptable for typical event size; profile before optimizing |
| Session management bugs | Follow CLAUDE.md patterns; pass session through all calls |
| Backward compatibility breaks | Nullable FKs; fallback to create-at-execution pattern |
| Data loss during reset/re-import | calculation_results can be regenerated; no true data loss |

## Dependencies

- **F064 (FinishedGoodSnapshot)**: Must be complete - provides finished_good_snapshot pattern
- **RecipeSnapshot service**: Must support planning context (nullable production_run_id)
- **PlanningSnapshot container**: Already exists from F064

## Acceptance Criteria Summary

1. ProductionPlanSnapshot has no calculation_results or staleness fields
2. EventProductionTarget has recipe_snapshot_id FK
3. EventAssemblyTarget has finished_good_snapshot_id FK
4. Planning creates snapshots and links to targets
5. Production/assembly reuses planning snapshots
6. UI displays calculated results in <5 seconds
7. Legacy events continue to function
8. Test coverage >70% for affected services
