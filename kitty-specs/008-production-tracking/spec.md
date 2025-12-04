# Feature Specification: Production Tracking

**Feature Branch**: `008-production-tracking`
**Created**: 2025-12-04
**Status**: Draft
**Dependencies**: Feature 006 (Event Planning), Feature 005 (FIFO Recipe Costing)

## Problem Statement

After Features 006-007, users can plan events (assign packages to recipients) and see what ingredients they need to buy. But there's no way to track the actual production process: when recipes are baked, when packages are assembled, and when they're delivered. The user has no "in progress" visibility into their holiday baking workflow.

### Current State
- Create recipes with ingredients
- Create bundles of finished goods
- Create packages containing bundles
- Assign packages to recipients for events
- See shopping list with variant recommendations

### Missing Capabilities
- No tracking of actual production
- No visibility into what's done vs pending
- No inventory depletion when baking occurs
- No actual cost capture vs estimates

## Production Lifecycle

```
Event Planning    -->    Production           -->    Assembly        -->    Delivery
(packages              (batches baked,             (packages             (packages
 assigned)              inventory consumed)         assembled)            delivered)
```

## User Scenarios & Testing

### User Story 1 - Record Recipe Production (Priority: P1)

As a baker, I want to mark batches of a recipe as "produced" so that pantry inventory is depleted and actual costs are recorded.

**Why this priority**: This is the core functionality - without production recording, no downstream tracking is possible. FIFO inventory consumption and actual cost capture are the foundation of the entire feature.

**Independent Test**: Can be fully tested by recording a batch of any recipe and verifying that pantry items are consumed via FIFO with actual costs captured.

**Acceptance Scenarios**:

1. **Given** an event with planned packages requiring 3 batches of "Chocolate Chip Cookies", **When** the user marks 2 batches as produced, **Then** the system depletes pantry ingredients for 2 batches via FIFO and records actual ingredient costs at time of production.

2. **Given** a recipe requiring 2 cups flour and 1 cup sugar per batch, **When** the user records 1 batch produced, **Then** the oldest (FIFO) flour and sugar pantry items are consumed in the correct quantities.

3. **Given** insufficient pantry stock for a recipe batch, **When** the user attempts to record production, **Then** the system warns about missing ingredients and prevents production recording.

---

### User Story 2 - Track Package Assembly (Priority: P2)

As a baker, I want to mark packages as "assembled" when all component finished goods have been produced, so I know which packages are ready for delivery.

**Why this priority**: Package assembly status bridges production to delivery - users need to know when a package transitions from "still baking" to "ready to give."

**Independent Test**: Can be fully tested by assembling a package after its required recipes are produced, verifying status change.

**Acceptance Scenarios**:

1. **Given** a package containing bundles that require recipes A and B, **When** all required batches of A and B are produced, **Then** the user can mark the package as "assembled."

2. **Given** a package where some required recipes are not yet fully produced, **When** the user attempts to mark it as assembled, **Then** the system shows which recipes/batches are still pending.

3. **Given** multiple packages for an event, **When** the user views the event, **Then** they see which packages are pending, assembled, or delivered.

---

### User Story 3 - Track Package Delivery (Priority: P2)

As a baker, I want to mark packages as "delivered" to recipients so I can track completion of my gift-giving.

**Why this priority**: Delivery tracking completes the lifecycle and provides closure on event progress.

**Independent Test**: Can be fully tested by marking an assembled package as delivered and verifying status update.

**Acceptance Scenarios**:

1. **Given** a package marked as "assembled", **When** the user marks it as "delivered", **Then** the package status updates to delivered with delivery timestamp.

2. **Given** a package still in "pending" status, **When** the user attempts to mark it as delivered, **Then** the system requires it to be assembled first (enforces status progression).

---

### User Story 4 - Production Dashboard (Priority: P3)

As a baker, I want a top-level Production Dashboard showing all active production across all events, so I can see my overall baking progress at a glance.

**Why this priority**: Provides the unified view across events - valuable for users managing multiple events, but core tracking (P1-P2) must work first.

**Independent Test**: Can be fully tested by creating multiple events with packages and viewing aggregate production status on the dashboard.

**Acceptance Scenarios**:

1. **Given** two active events with packages, **When** the user opens the Production Dashboard, **Then** they see a summary of all events with production progress (X of Y batches complete, X packages assembled, Y delivered).

2. **Given** an event with 6 recipes needed and 4 produced, **When** viewing the dashboard, **Then** the user sees "4 of 6 recipes complete" or similar progress indicator.

3. **Given** the Production Dashboard, **When** the user clicks on an event, **Then** they navigate to detailed event production view.

---

### User Story 5 - Actual vs Planned Cost Comparison (Priority: P3)

As a baker, I want to compare actual production costs against planned estimates at both event and recipe level, so I can understand my true costs.

**Why this priority**: Cost visibility is valuable but depends on production recording (P1) being complete. Provides insights after the core workflow is established.

**Independent Test**: Can be fully tested by recording production for an event and comparing actual costs (from FIFO consumption) against planned estimates.

**Acceptance Scenarios**:

1. **Given** an event with estimated ingredient cost of $52, **When** production is partially complete with $45 actual cost recorded, **Then** the user sees "Actual: $45 / Planned: $52" comparison.

2. **Given** event-level cost summary, **When** the user drills down, **Then** they see recipe-by-recipe cost breakdown (actual vs planned per recipe).

3. **Given** no production recorded yet, **When** viewing costs, **Then** actual shows $0 and planned shows the full estimate.

---

### Edge Cases

- What happens when production would exceed planned quantities? System warns but allows recording (user may have made extra).
- What happens when pantry has insufficient stock? System prevents production and shows missing ingredients.
- What happens when a recipe is modified after production started? Existing production records retain their original cost data; new production uses updated recipe.
- What happens when viewing an event with no packages assigned? Production Dashboard shows "No packages planned" for that event.
- What happens when all packages for an event are delivered? Event shows as "Complete" in the Production Dashboard.

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow users to record batches of a recipe as "produced" for a specific event.
- **FR-002**: System MUST consume pantry inventory via FIFO when production is recorded (using existing `PantryService.consume_fifo()` with `dry_run=False`).
- **FR-003**: System MUST capture actual ingredient costs at the time of production based on FIFO consumption, not estimated costs.
- **FR-004**: System MUST track package status through the lifecycle: pending -> assembled -> delivered.
- **FR-005**: System MUST enforce status progression (packages cannot skip from pending to delivered).
- **FR-006**: System MUST provide a top-level Production Dashboard showing all active events and their production progress.
- **FR-007**: System MUST display event-level cost comparison (actual vs planned total).
- **FR-008**: System MUST display recipe-level cost comparison (actual vs planned per recipe) as drill-down from event level.
- **FR-009**: System MUST warn when production quantity exceeds planned quantity but allow the user to proceed.
- **FR-010**: System MUST prevent production recording when pantry has insufficient stock for the batch.
- **FR-011**: System MUST display production progress showing batches complete vs required for each recipe.
- **FR-012**: System MUST display package progress showing counts by status (pending, assembled, delivered).

### Key Entities

- **ProductionRecord**: Represents a batch of a recipe being produced for an event. Contains reference to recipe, event, batch count, production timestamp, and actual cost at time of production. Links to specific pantry consumption records.

- **Package Status**: Packages gain a status attribute tracking their lifecycle position (pending, assembled, delivered). Status transitions are enforced in order.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can record recipe production and see pantry inventory decrease within 3 clicks from the Production Dashboard.
- **SC-002**: Actual costs displayed after production match the sum of FIFO-consumed ingredient costs (100% accuracy).
- **SC-003**: Package status is always accurate - assembled packages have all required batches produced, delivered packages were previously assembled.
- **SC-004**: Production Dashboard loads and displays all active events within 2 seconds for up to 10 concurrent events.
- **SC-005**: Users can view actual vs planned cost comparison at event level and drill down to recipe level within 2 clicks.
- **SC-006**: 100% of production records include: recipe reference, event reference, batch count, timestamp, and captured actual cost.

## Scope Boundaries

### In Scope
- Production status tracking for finished goods (planned -> in progress -> complete)
- Batch recording: mark X batches of Recipe Y as complete
- Inventory depletion: consume pantry items via FIFO when production recorded
- Package assembly status (pending -> assembled)
- Package delivery status (assembled -> delivered)
- Top-level Production Dashboard showing all event progress
- Actual cost tracking (based on FIFO consumption at production time)
- Actual vs planned comparison at event and recipe levels

### Out of Scope
- Scheduling/calendar integration
- Multi-user assignment (who's baking what)
- Partial batch tracking (half-batches)
- Undo/rollback of production records
- Waste tracking

## Assumptions

- Events from Feature 006 are functional and packages can be assigned to events.
- `PantryService.consume_fifo()` is implemented and accepts a `dry_run` parameter.
- Recipe cost estimation from Feature 005 is available for planned cost calculations.
- Production is always event-scoped (no standalone production outside of events).
- A single user workflow - no concurrency concerns for production recording.
