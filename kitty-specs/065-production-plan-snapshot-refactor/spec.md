# Feature Specification: Production Plan Snapshot Refactor

**Feature Branch**: `065-production-plan-snapshot-refactor`
**Created**: 2025-01-24
**Status**: Draft
**Input**: User description: "see docs/func-spec/F065_production_plan_snapshot_refactor.md for this feature's inputs."

## Clarifications

### Session 2025-01-24

- Q: What is the maximum acceptable time for displaying batch requirements after clicking to view an event plan? → A: Under 5 seconds

## Overview

This architectural refactoring transforms ProductionPlanSnapshot from a calculation cache into a true snapshot orchestration container. The refactor completes the definition/instantiation separation pattern by ensuring that event planning captures immutable snapshots of recipes and finished goods at planning time, not execution time.

**Problem Being Solved:**
- Current ProductionPlanSnapshot stores calculation results (cache pattern) instead of capturing definition state
- Planning references live definitions that can change after planning
- Staleness detection is a workaround for missing snapshot architecture
- Planning and production/assembly create separate snapshots instead of sharing

**Solution:**
- ProductionPlanSnapshot becomes a lightweight container referencing snapshots
- Snapshots are created at planning time and reused at production/assembly time
- Definitions are immutable once captured; changes require a new plan
- Calculation results are computed on-demand, not cached

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plan Event Production with Immutable Definitions (Priority: P1)

As an event planner, when I finalize production planning for an event, the system captures the current state of all recipes and finished goods so that subsequent changes to those definitions don't affect my planned event.

**Why this priority**: This is the core value proposition - ensuring planned events have stable, predictable production requirements regardless of future definition changes.

**Independent Test**: Can be fully tested by creating an event plan, modifying a recipe definition, then verifying the plan still reflects the original recipe state.

**Acceptance Scenarios**:

1. **Given** an event with production targets for recipes A, B, and C, **When** the user generates/saves the production plan, **Then** a snapshot of each recipe (A, B, C) is created and linked to the respective production targets.

2. **Given** an event with assembly targets for finished goods X and Y, **When** the user generates/saves the production plan, **Then** a snapshot of each finished good (X, Y) is created and linked to the respective assembly targets.

3. **Given** a saved production plan with recipe snapshots, **When** the user modifies the original recipe definition, **Then** the production plan continues to reference the original snapshot (unchanged).

---

### User Story 2 - Execute Production Using Planning Snapshots (Priority: P1)

As a production worker, when I record production for a planned event, the system uses the recipe snapshot that was captured during planning so that my production matches what was planned.

**Why this priority**: Critical for consistency between planning and execution - ensures production follows the plan exactly.

**Independent Test**: Can be fully tested by creating a plan, then recording production and verifying the production run references the same snapshot created during planning.

**Acceptance Scenarios**:

1. **Given** a production target with a linked recipe snapshot, **When** a production run is recorded for that target, **Then** the production run references the same recipe snapshot (not a new one).

2. **Given** an assembly target with a linked finished good snapshot, **When** an assembly run is recorded for that target, **Then** the assembly run references the same finished good snapshot (not a new one).

3. **Given** a production run for a recipe WITHOUT a planning snapshot (legacy/ad-hoc), **When** the production is recorded, **Then** a new recipe snapshot is created at production time (backward compatibility).

---

### User Story 3 - View Event Plan Requirements (Priority: P2)

As an event planner, when I view the production plan for an event, I see the calculated batch requirements and shopping list based on the captured snapshots.

**Why this priority**: Essential for usability but depends on snapshot infrastructure from P1 stories.

**Independent Test**: Can be tested by viewing a saved plan and verifying batch calculations and shopping list are displayed correctly.

**Acceptance Scenarios**:

1. **Given** an event with a saved production plan, **When** the user views the plan, **Then** batch requirements are calculated from the linked snapshots and displayed.

2. **Given** an event with a saved production plan, **When** the user views the shopping list, **Then** ingredient requirements are calculated from the linked snapshots and displayed.

---

### User Story 4 - Create New Plan After Definition Changes (Priority: P3)

As an event planner, when I want my plan to reflect updated recipe or finished good definitions, I can create a new production plan that captures the current state.

**Why this priority**: Supports the immutability model - users explicitly choose when to update plans.

**Independent Test**: Can be tested by modifying a recipe, creating a new plan, and verifying the new plan has new snapshots reflecting the changes.

**Acceptance Scenarios**:

1. **Given** a recipe has been modified since the last plan, **When** the user creates a new production plan, **Then** new recipe snapshots are created reflecting the current recipe state.

2. **Given** an event with an existing production plan, **When** the user creates a new plan, **Then** the new plan has its own set of snapshots independent of the previous plan.

---

### Edge Cases

- What happens when a production target references a recipe that has been deleted? The system should prevent deletion of recipes with active production targets, or the snapshot preserves the recipe state.
- How does the system handle events created before this refactor (no snapshots)? Production/assembly creates snapshots at execution time for backward compatibility.
- What happens if snapshot creation fails mid-transaction? All snapshot creation occurs in a single transaction; failure rolls back the entire plan creation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST remove calculation result storage from ProductionPlanSnapshot (calculation_results field removed)
- **FR-002**: System MUST remove staleness tracking from ProductionPlanSnapshot (requirements_updated_at, recipes_updated_at, bundles_updated_at, is_stale, stale_reason fields removed)
- **FR-003**: System MUST store recipe snapshot references on production targets (recipe_snapshot_id foreign key)
- **FR-004**: System MUST store finished good snapshot references on assembly targets (finished_good_snapshot_id foreign key)
- **FR-005**: System MUST create recipe snapshots for each production target during event plan creation
- **FR-006**: System MUST create finished good snapshots for each assembly target during event plan creation
- **FR-007**: System MUST create all planning snapshots within a single atomic transaction
- **FR-008**: System MUST reuse planning snapshots when recording production/assembly runs for planned events
- **FR-009**: System MUST create snapshots at execution time when no planning snapshot exists (backward compatibility)
- **FR-010**: System MUST support recipe snapshots created without a production run context (planning context)
- **FR-011**: System MUST support finished good snapshots created without an assembly run context (planning context)
- **FR-012**: System MUST calculate batch requirements on-demand from snapshots (not from cached results)
- **FR-013**: System MUST generate shopping lists on-demand from snapshots (not from cached results)

### Key Entities

- **ProductionPlanSnapshot**: Lightweight container linking an event to its planning timestamp; references snapshots via targets
- **ProductionTarget**: Event's production goal for a recipe; gains reference to recipe snapshot created at planning time
- **AssemblyTarget**: Event's assembly goal for a finished good; gains reference to finished good snapshot created at planning time
- **RecipeSnapshot**: Immutable capture of recipe state; can now be created for planning context (not just production)
- **FinishedGoodSnapshot**: Immutable capture of finished good state; can now be created for planning context (not just assembly)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Event plans remain stable after definition changes - modifying a recipe/finished good does not alter any existing event plan's requirements
- **SC-002**: Production runs for planned events reference the same snapshot as the plan (100% snapshot reuse for planned production)
- **SC-003**: Assembly runs for planned events reference the same snapshot as the plan (100% snapshot reuse for planned assembly)
- **SC-004**: Legacy events without planning snapshots continue to function (backward compatibility maintained)
- **SC-005**: Users can view event plan requirements within 5 seconds (on-demand calculation completes in under 5 seconds)
- **SC-006**: All planning snapshots for an event are created atomically (either all succeed or all fail)

## Assumptions

- F064 (FinishedGoodSnapshot) is complete and the finished_good_snapshot pattern is established
- The existing recipe_snapshot_service provides a reusable snapshot creation primitive
- On-demand calculation performance is acceptable for typical event sizes (no caching needed initially)
- Data migration can safely remove calculation_results as this data can be recalculated

## Out of Scope

- InventorySnapshot improvements (deferred to F066)
- Material snapshots (deferred to F066)
- Changes to event planning calculation logic (only where results are stored changes)
- UI redesign beyond removing cache dependencies
- Performance optimization of on-demand recalculation (acceptable for MVP)
