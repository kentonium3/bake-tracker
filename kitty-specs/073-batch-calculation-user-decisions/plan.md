# Implementation Plan: Batch Calculation & User Decisions

**Branch**: `073-batch-calculation-user-decisions` | **Date**: 2026-01-27 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/kitty-specs/073-batch-calculation-user-decisions/spec.md`

## Summary

Implement automatic batch calculation with user decision UI for event planning. The system calculates floor/ceil batch options for each FinishedUnit in an event, presents options with clear trade-offs (shortfall warnings, exact match highlights), requires confirmation for shortfall selections, and persists decisions to the `batch_decisions` table. This is the core value proposition feature - replacing error-prone manual calculations that cause underproduction.

**Key architectural insight**: Batch calculation operates at the FinishedUnit level (not Recipe level) because yield varies by FU. However, batches are OF recipes - the FU provides yield context for how many FUs one recipe batch produces.

**Prerequisite fix (included in WP01)**: F072's `calculate_recipe_requirements()` currently returns `Dict[Recipe, int]` which aggregates at the recipe level. This loses FU-level yield context needed for batch calculation when a recipe has multiple FUs with different yields (e.g., Large/Medium/Small Cake). WP01 fixes F072 to return FU-level data before implementing batch calculation.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: CustomTkinter (UI), SQLAlchemy 2.x (ORM), math (floor/ceil)
**Storage**: SQLite with WAL mode (existing `batch_decisions` table - requires schema modification)
**Testing**: pytest with >70% service layer coverage
**Target Platform**: Desktop (Windows/macOS/Linux)
**Project Type**: Single project - desktop application
**Performance Goals**: Sub-second batch calculation for typical events (10-50 FGs)
**Constraints**: Single user, offline-capable
**Scale/Scope**: Single event planning at a time, ~50 FUs max per event

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. User-Centric Design | PASS | Core value proposition - solves actual underproduction problem |
| II. Data Integrity & FIFO | PASS | Batch decisions validated before save; positive integer constraint |
| III. Future-Proof Schema | PASS | BatchDecision model exists from F068; requires constraint modification |
| IV. Test-Driven Development | PASS | Service layer tests required before completion |
| V. Layered Architecture | PASS | Calculation in services; presentation in UI |
| VI. Schema Change Strategy | PASS | Constraint change via export/reset/import cycle |
| VII. Pragmatic Aspiration | PASS | Service layer API-ready for future web deployment |

**Schema Change Required**: See [data-model.md](data-model.md) for details on modifying `BatchDecision` constraint.

## Project Structure

### Documentation (this feature)

```
kitty-specs/073-batch-calculation-user-decisions/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 research findings
├── data-model.md        # Schema analysis and changes
├── quickstart.md        # Implementation guide
└── tasks.md             # Work packages (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── models/
│   └── batch_decision.py     # MODIFY: Update constraint (finished_unit_id NOT NULL)
├── services/
│   ├── planning_service.py   # MODIFY: Change return type to FU-level, add batch calc
│   └── batch_decision_service.py  # NEW: CRUD for batch decisions
├── ui/
│   ├── planning_tab.py       # MODIFY: Integrate batch decision UI
│   └── widgets/
│       └── batch_options_frame.py  # NEW: Batch option selection widget
└── tests/
    ├── test_planning_service.py    # MODIFY: Update 22 tests for new return type
    ├── test_batch_calculation.py   # NEW: Batch calculation tests
    └── test_batch_decision_ui.py   # NEW: UI integration tests (optional)
```

**Structure Decision**: Single project structure following existing patterns. New service file for batch decision CRUD, new UI widget for option selection.

## Complexity Tracking

| Item | Notes |
|------|-------|
| Schema constraint change | Required to support multiple FUs from same recipe per event |
| New service file | Clean separation of batch decision logic from planning_service |

No constitution violations. Complexity is appropriate for the feature scope.

## Key Design Decisions

### 1. Batch Calculation at FinishedUnit Level

**Decision**: Calculate batch options per-FinishedUnit, not per-Recipe.

**Rationale**:
- Same recipe can have multiple FUs with different yields (Large/Medium/Small Cake)
- User needs 10 Small Cakes (yield 4/batch) requires different calculation than 3 Large Cakes (yield 1/batch)
- BatchDecision stores `finished_unit_id` to track which yield was used

### 2. 1x Recipe Scaling Only

**Decision**: No half-batch or double-batch options in this feature.

**Rationale**:
- Keeps calculation simple and predictable
- Recipe scaling is a future feature
- One batch = standard recipe yield

### 3. Schema Constraint Modification

**Decision**: Change BatchDecision unique constraint from `(event_id, recipe_id)` to `(event_id, finished_unit_id)`.

**Rationale**:
- Original constraint prevents multiple FUs from same recipe in one event
- New constraint allows: Small Cake (3 batches) + Large Cake (3 batches) for same event
- `finished_unit_id` becomes NOT NULL (was nullable)

### 4. Input Source: EventFinishedGood

**Decision**: Batch calculation uses EventFinishedGood table (FU × quantity selections) directly, not F072 recipe-level aggregation.

**Rationale**:
- F072 aggregates to recipe level, losing FU-level yield information
- EventFinishedGood has exact FU and quantity user selected
- F072 remains useful for ingredient aggregation (F074)

## Data Flow

```
EventFinishedGood (user's FG selections)
         │
         ▼
┌─────────────────────────────────────┐
│ F072 (FIXED): decompose_event_to_  │
│              fu_requirements()      │
│ - Decomposes bundles recursively    │
│ - Returns List[FURequirement]       │
│   (FU, quantity, recipe per item)   │
└─────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────┐
│ F073: Batch Calculation Service     │
│ For each FURequirement:             │
│   - Get FU's yield (items_per_batch)│
│   - Calculate floor/ceil options    │
│   - Flag shortfalls, exact matches  │
└─────────────────────────────────────┘
         │
         ▼
BatchOptionsFrame (UI)
  - Display options per FU
  - Shortfall warnings
  - User selects option
         │
         ▼
┌─────────────────────────────────────┐
│ Shortfall Confirmation (if needed)  │
└─────────────────────────────────────┘
         │
         ▼
BatchDecision (persisted)
  - event_id
  - recipe_id (from FU.recipe)
  - finished_unit_id
  - batches (user's choice)
```

## Parallel Work Analysis

This feature has clear sequential dependencies - not suitable for parallel agent work.

**Sequential flow:**
1. **WP01**: F072 API fix (return FU-level data) + BatchDecision schema change
2. **WP02**: Batch calculation service (uses fixed F072 output)
3. **WP03**: Batch decision CRUD service
4. **WP04**: UI layer (BatchOptionsFrame widget)
5. **WP05**: Integration with planning_tab.py

**Recommended approach**: Single agent, sequential work packages.

## Work Package Outline

| WP | Focus | Key Deliverables |
|----|-------|------------------|
| WP01 | Foundation Fixes | F072 API change to FU-level return, BatchDecision constraint change, update 22 F072 tests |
| WP02 | Batch Calculation | `calculate_batch_options()` service using F072 output, floor/ceil logic, shortfall detection |
| WP03 | Batch Decision CRUD | `save_batch_decision()`, `get_batch_decisions()`, validation, shortfall confirmation logic |
| WP04 | UI Widget | BatchOptionsFrame with radio buttons, shortfall warnings, exact match highlights |
| WP05 | Integration | Wire up planning_tab.py, load/save flow, end-to-end testing |
