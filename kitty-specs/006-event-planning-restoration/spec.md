# Feature Specification: Event Planning Restoration

**Feature Branch**: `006-event-planning-restoration`
**Created**: 2025-12-03
**Status**: Draft
**Input**: Reimplement the gift planning subsystem (Package, Event model chain) that was disabled during the Ingredient/Variant refactor, updated to work with the new architecture and FIFO-based costing from Feature 005.

## Problem Statement

During the Phase 4 Ingredient/Variant refactor (Features 002-004), the Package → Event model chain was disabled due to cascading foreign key dependencies. The app currently cannot perform gift planning, which is the core use case for the primary user.

## Background

Phase 3b (completed Nov 2024) delivered working event planning with:
- **Models**: Event, Recipient, Package, Bundle, PackageBundle, EventRecipientPackage
- **Services**: EventService, RecipientService, PackageService, FinishedGoodService
- **UI**: Events tab, Recipients tab, Packages tab, Bundles tab, EventDetailWindow (4 planning tabs)

**Architecture Change**: The Bundle model was eliminated during Features 002-004 refactoring. FinishedGood now serves as an assembly container (containing FinishedUnits and/or other FinishedGoods). This feature adapts Package to reference FinishedGood directly via a new PackageFinishedGood junction table.

The Phase 4 refactor changed the Ingredient model significantly (splitting into Ingredient/Variant with new FK patterns), breaking the dependency chain:
```
Recipe → FinishedUnit → Composition → FinishedGood → Package → Event
         ↑
    RecipeIngredient now uses new Ingredient model
```

## Approach

Fresh reimplementation using Phase 3b design as reference, adapted for:
- New FinishedGood/FinishedUnit architecture (Features 002-004) where FinishedGood is an assembly
- FIFO-based recipe costing from Feature 005
- Elimination of Bundle concept (replaced by FinishedGood assemblies)

## User Scenarios & Testing

### User Story 1 - Package Content Management (Priority: P1)

As a baker, I want to add FinishedGood assemblies (e.g., "Cookie Assortment Box") to packages so that I can define what each gift contains.

**Why this priority**: Packages are the foundation of event planning. They contain FinishedGood assemblies which are created via Features 002-004.

**Note**: FinishedGood assembly creation/editing is handled by existing FinishedGood management UI from Features 002-004. This user story covers **selecting** existing assemblies for packages.

**Independent Test**: Can be fully tested by creating a package, adding existing FinishedGoods, and verifying cost aggregation.

**Acceptance Scenarios**:

1. **Given** the Packages tab is open, **When** the user clicks "Add Package" and enters a name, **Then** the package is created (initially empty)
2. **Given** a package is selected, **When** the user opens the content editor and clicks "Add Item", **Then** a dialog shows available FinishedGood assemblies to select
3. **Given** a package with FinishedGoods, **When** the user changes quantity of an item, **Then** the package cost recalculates based on FIFO recipe costs
4. **Given** a package with FinishedGoods, **When** the user removes an item, **Then** the item is removed and cost recalculates

---

### User Story 2 - Package Management (Priority: P1)

As a baker, I want to manage gift packages containing FinishedGood assemblies so that I can define what each gift recipient will receive.

**Why this priority**: Packages are the deliverable unit assigned to recipients. Critical for gift planning.

**Independent Test**: Can be fully tested by creating a package with multiple FinishedGoods and verifying cost aggregation.

**Acceptance Scenarios**:

1. **Given** the Packages tab is open, **When** the user views the package list, **Then** all packages are displayed with name, item count, and total cost
2. **Given** an existing package, **When** the user edits package details (name, description), **Then** changes are saved
3. **Given** an existing package not assigned to any event, **When** the user deletes it, **Then** the package is removed
4. **Given** an existing package assigned to an event, **When** the user attempts to delete it, **Then** the system prevents deletion with a dependency warning

---

### User Story 3 - Recipient Management (Priority: P2)

As a baker, I want to maintain a list of gift recipients so that I can assign packages to them for events.

**Why this priority**: Recipients are required for event assignments but can be managed independently of event timing.

**Independent Test**: Can be fully tested by adding/editing/deleting recipients and verifying the list persists correctly.

**Acceptance Scenarios**:

1. **Given** the Recipients tab is open, **When** the user adds a recipient with name and optional notes, **Then** the recipient appears in the recipient list
2. **Given** an existing recipient, **When** the user edits their information, **Then** the changes are saved
3. **Given** a recipient with no event assignments, **When** the user deletes them, **Then** the recipient is removed
4. **Given** a recipient with event assignments, **When** the user attempts to delete them, **Then** the system warns about existing assignments and requires confirmation

---

### User Story 4 - Event Management (Priority: P2)

As a baker, I want to create events (e.g., "Christmas 2024") with year filtering so that I can plan gift-giving occasions.

**Why this priority**: Events are the container for gift planning but require packages and recipients to be meaningful.

**Independent Test**: Can be fully tested by creating events for different years and verifying year filter works correctly.

**Acceptance Scenarios**:

1. **Given** the Events tab is open, **When** the user creates an event with name and year, **Then** the event appears in the event list
2. **Given** multiple events across different years, **When** the user selects a year filter, **Then** only events from that year are displayed
3. **Given** an existing event, **When** the user edits event details, **Then** changes are saved
4. **Given** an event with no assignments, **When** the user deletes it, **Then** the event is removed
5. **Given** an event with recipient-package assignments, **When** the user deletes it, **Then** all assignments are also removed (cascade delete with confirmation)

---

### User Story 5 - Event Assignment Planning (Priority: P1)

As a baker, I want to assign packages to recipients for a specific event so that I know who gets what.

**Why this priority**: This is the core gift planning workflow - the primary use case for the application.

**Independent Test**: Can be fully tested by opening an event, assigning packages to recipients, and verifying assignments persist.

**Acceptance Scenarios**:

1. **Given** an event is selected and EventDetailWindow opens to Assignments tab, **When** the user assigns a package to a recipient, **Then** the assignment is saved and displayed in the assignments list
2. **Given** existing assignments, **When** the user modifies an assignment (change package), **Then** the assignment updates and costs recalculate
3. **Given** an assignment, **When** the user removes it, **Then** the assignment is deleted and totals recalculate
4. **Given** multiple assignments, **When** viewing the Assignments tab, **Then** all recipient-package pairs are displayed with individual package costs

---

### User Story 6 - Recipe Needs Calculation (Priority: P2)

As a baker, I want to see how many batches of each recipe I need to make for an event so that I can plan my baking schedule.

**Why this priority**: Derived calculation from assignments - valuable but depends on assignments being complete.

**Independent Test**: Can be tested by creating assignments and verifying the Recipe Needs tab shows correct batch counts.

**Acceptance Scenarios**:

1. **Given** an event with assignments, **When** the user views the Recipe Needs tab, **Then** all recipes are listed with required batch counts
2. **Given** multiple packages containing the same recipe (via FinishedGoods), **When** viewing Recipe Needs, **Then** batch counts are aggregated across all assignments
3. **Given** an event with no assignments, **When** viewing Recipe Needs tab, **Then** an empty state message is displayed

---

### User Story 7 - Shopping List Generation (Priority: P2)

As a baker, I want to see what ingredients I need to buy for an event, accounting for what I already have in my pantry.

**Why this priority**: Critical for shopping but requires all upstream data (assignments, recipes, pantry) to be accurate.

**Independent Test**: Can be tested by creating assignments and verifying Shopping List shows ingredients with on-hand and shortfall quantities.

**Acceptance Scenarios**:

1. **Given** an event with assignments, **When** the user views the Shopping List tab, **Then** all required ingredients are listed with needed quantities
2. **Given** pantry has some inventory, **When** viewing Shopping List, **Then** on-hand quantities are displayed alongside needed quantities
3. **Given** ingredient needs exceed pantry quantities, **When** viewing Shopping List, **Then** shortfall is calculated and highlighted
4. **Given** pantry has sufficient inventory for an ingredient, **When** viewing Shopping List, **Then** that ingredient shows zero shortfall

---

### User Story 8 - Event Cost Summary (Priority: P2)

As a baker, I want to see the total cost of an event so that I can budget appropriately.

**Why this priority**: Summary view depends on all other calculations being correct.

**Independent Test**: Can be tested by creating assignments and verifying Summary tab shows correct totals using FIFO costs.

**Acceptance Scenarios**:

1. **Given** an event with assignments, **When** the user views the Summary tab, **Then** total event cost is displayed (sum of all assigned package costs)
2. **Given** an event with assignments, **When** viewing Summary, **Then** package count and recipient count are displayed
3. **Given** recipe costs change (pantry updates), **When** viewing Summary, **Then** costs reflect current FIFO-based calculations from RecipeService
4. **Given** an event with no assignments, **When** viewing Summary tab, **Then** zero totals are displayed with empty state messaging

---

### Edge Cases

- What happens when a FinishedGood is deleted that belongs to a Package? System should prevent deletion (RESTRICT foreign key) or warn about package dependencies.
- What happens when a recipe has no cost data (no purchases)? Display "Cost unavailable" rather than zero.
- How does the system handle an event with 100+ assignments? Pagination or virtualized list for performance.
- What happens when pantry is empty? Shopping List shows all ingredients as shortfall.
- What if a package contains zero FinishedGoods? Allow empty packages but display warning.

## Requirements

### Functional Requirements

#### Models
- **FR-001**: System MUST provide a Package entity that contains zero or more FinishedGoods via PackageFinishedGood junction
- **FR-002**: System MUST provide a Recipient entity with name and optional notes
- **FR-003**: System MUST provide an Event entity with name and year
- **FR-004**: System MUST provide EventRecipientPackage junction to assign packages to recipients for events

**Note**: FinishedGood entity already exists from Features 002-004 and serves as the assembly container.

#### Package Operations
- **FR-005**: Users MUST be able to create packages with a name
- **FR-006**: Users MUST be able to add/remove FinishedGood assemblies to packages with quantities
- **FR-007**: Users MUST be able to edit package contents (add/remove FinishedGoods, change quantities)
- **FR-008**: Users MUST be able to delete packages that have no event assignment dependencies
- **FR-009**: System MUST calculate package cost as sum of (FinishedGood.total_cost * quantity) using FIFO recipe costs
- **FR-010**: System MUST prevent deletion of packages that are assigned to events

**Note**: FinishedGood assembly CRUD (create, edit, delete) is handled by existing UI from Features 002-004.

#### Recipient Operations
- **FR-011**: Users MUST be able to create recipients with name and optional notes
- **FR-012**: Users MUST be able to edit recipient information
- **FR-013**: Users MUST be able to delete recipients (with confirmation if assigned to events)

#### Event Operations
- **FR-014**: Users MUST be able to create events with name and year
- **FR-015**: Users MUST be able to filter events by year
- **FR-016**: Users MUST be able to edit event details
- **FR-017**: Users MUST be able to delete events (cascade deletes assignments with confirmation)

#### Event Detail Window
- **FR-018**: System MUST display EventDetailWindow with four tabs: Assignments, Recipe Needs, Shopping List, Summary
- **FR-019**: Assignments tab MUST allow CRUD operations on recipient-package assignments
- **FR-020**: Recipe Needs tab MUST display aggregated batch counts per recipe
- **FR-021**: Shopping List tab MUST display ingredients needed, on-hand quantities, and shortfall
- **FR-022**: Summary tab MUST display total event cost, package count, and recipient count

#### Cost Integration
- **FR-023**: All cost calculations MUST use RecipeService.calculate_actual_cost() with FIFO-based pricing
- **FR-024**: Shopping List MUST use PantryService to determine on-hand inventory quantities
- **FR-025**: Costs MUST update dynamically when underlying recipe costs or pantry inventory changes

### Key Entities

- **FinishedGood** (existing from Features 002-004): An assembly containing FinishedUnits and/or other FinishedGoods (e.g., "Cookie Assortment Box"). Has calculated cost from component costs via Composition relationships.
- **Package**: A gift package containing one or more FinishedGood assemblies (e.g., "Premium Gift Box"). Has calculated cost from component FinishedGoods.
- **PackageFinishedGood**: Junction table linking Packages to FinishedGoods with quantity.
- **Recipient**: A person who receives gift packages. Has name and optional notes/address.
- **Event**: A gift-giving occasion (e.g., "Christmas 2024"). Has name and year for filtering.
- **EventRecipientPackage**: Junction table assigning Packages to Recipients for a specific Event.

## Scope

### In Scope
- Create PackageFinishedGood junction model (replaces removed PackageBundle)
- Update Package model to reference FinishedGood directly
- Re-enable Event model and EventRecipientPackage junction
- Verify Recipient model (already enabled)
- Reimplement services (EventService, PackageService; verify RecipientService)
- Restore UI tabs: Packages, Recipients, Events
- Restore EventDetailWindow with Assignments, Recipe Needs, Shopping List, Summary tabs
- Integrate cost calculations with Feature 005's FIFO-based recipe costs

**Note**: Bundle model eliminated per research decision D1. FinishedGood assemblies (from Features 002-004) fulfill this role.

### Out of Scope
- Variant-aware shopping list recommendations (deferred to Feature 007)
- Production tracking and scheduling (deferred to Feature 008)
- New features beyond restoring Phase 3b functionality
- Export/print functionality for shopping lists or summaries
- FinishedGood assembly CRUD (already exists in Features 002-004)

## Dependencies

- **Requires**: Features 002-005 complete (FinishedGood/FinishedUnit architecture, FIFO recipe costing)
- **Builds on**: Phase 3b design documentation (reimplementation, not restoration of old code)
- **Integrates with**: RecipeService.calculate_actual_cost(), PantryService inventory queries, FinishedGoodService

## Assumptions

- FinishedGood → Composition → FinishedUnit → Recipe relationship from Features 002-004 will be leveraged for cost calculation
- Phase 3b UI layouts provide a valid reference but may be updated for consistency with current UI patterns
- RecipeService and PantryService APIs from Features 004-005 are stable and documented
- Year filtering on Events uses simple integer year (no date ranges needed)
- FinishedGood assemblies are already created via existing UI before being added to packages

## Success Criteria

### Measurable Outcomes

- **SC-001**: Users can complete the full gift planning workflow (select FinishedGoods for package → create event → assign to recipient) in under 5 minutes, assuming FinishedGood assemblies already exist
- **SC-002**: Event cost calculations match manual verification using FIFO costs within $0.01 accuracy
- **SC-003**: Shopping list shortfall calculations correctly reflect pantry inventory levels
- **SC-004**: All 4 EventDetailWindow tabs load and display data within 2 seconds for events with up to 50 assignments
- **SC-005**: Zero data loss when creating, editing, or deleting packages, recipients, events, and assignments
- **SC-006**: Primary user can successfully plan a holiday event (the core use case that was blocked)
