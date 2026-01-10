# Feature Specification: Finished Goods, Bundles & Assembly Tracking

**Feature Branch**: `046-finished-goods-bundles-assembly`
**Created**: 2026-01-09
**Status**: Draft
**Input**: Design document `docs/design/F046_finished_goods_bundles_assembly.md`

## Problem Statement

From user testing (2026-01-07): "Finished Goods button goes nowhere" - the baker cannot define gift boxes, bundles, or packages. This blocks the complete baking workflow:

1. **Missing Finished Goods Management**: No way to define assemblies like "Holiday Gift Box" that combine multiple finished units (cookies, brownies, etc.)
2. **Broken Event Planning**: Package cost calculation crashes because it references a field that was removed in F045
3. **No Assembly Tracking**: Cannot record when assemblies are created or what components were consumed
4. **No Cost Snapshots**: Assembly costs are not captured at assembly time, losing historical accuracy

This feature blocks F047 (Shopping Lists), F048 (Assembly Workflows), and complete Event Planning functionality.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a Finished Good (Priority: P1)

As a baker, I want to define what components make up a "Holiday Gift Box" so that I can plan assemblies and assign them to events.

**Why this priority**: Without finished good definitions, nothing else works. This is the foundational data model that enables all downstream features.

**Independent Test**: Can be tested by creating a finished good definition with components and verifying the structure is saved correctly.

**Acceptance Scenarios**:

1. **Given** I am in the Catalog view, **When** I navigate to Finished Goods tab, **Then** I see a list of defined finished goods (or empty state if none exist)
2. **Given** I am on the Finished Goods tab, **When** I click "Add Finished Good", **Then** I see a form to enter name, type, and components
3. **Given** I am adding a finished good, **When** I add components (e.g., 4x Large Cookie, 2x Brownie), **Then** the components are listed in the form
4. **Given** I have entered valid finished good details, **When** I save, **Then** the finished good appears in the list with its component count
5. **Given** I am viewing the Finished Goods list, **When** I look at the display, **Then** I do NOT see any cost columns (costs are not shown in catalog)

---

### User Story 2 - Record an Assembly (Priority: P1)

As a baker, I want to record when I assemble finished goods so that I know what was made, when, and at what cost.

**Why this priority**: Assembly recording is the core action that creates value - it tracks actual production and captures costs for reporting.

**Independent Test**: Can be tested by recording an assembly and verifying the cost snapshot and consumption records are created.

**Acceptance Scenarios**:

1. **Given** I am in Make mode, **When** I navigate to the Assembly tab, **Then** I see assembly history and a "Record Assembly" button
2. **Given** I click "Record Assembly", **When** the dialog opens, **Then** I can select a finished good, enter quantity, and optionally select an event
3. **Given** I am recording an assembly, **When** I enter a quantity, **Then** I see the current cost breakdown for the components (cost snapshot preview)
4. **Given** sufficient inventory exists, **When** I confirm the assembly, **Then** the system records the assembly with captured costs
5. **Given** insufficient inventory for a component, **When** I try to record the assembly, **Then** I receive an error indicating which component is short

---

### User Story 3 - Event Planning with Packages (Priority: P1)

As a baker, I want to assign packages containing finished goods to event recipients so that I can plan what to deliver.

**Why this priority**: This is currently broken (crashes). Fixing it unblocks event planning which is critical for the holiday baking workflow.

**Independent Test**: Can be tested by opening event planning, assigning a package, and verifying the cost is calculated without errors.

**Acceptance Scenarios**:

1. **Given** a package contains finished goods, **When** I view the package in event planning, **Then** I see the calculated cost based on current component prices
2. **Given** I am assigning packages to recipients, **When** I select a package, **Then** the system calculates the package cost dynamically (not from stored values)
3. **Given** ingredient prices change, **When** I view the same package later, **Then** the displayed cost reflects the updated prices

---

### User Story 4 - Edit and Delete Finished Goods (Priority: P2)

As a baker, I want to modify or remove finished good definitions so that I can keep my catalog current.

**Why this priority**: CRUD completeness is important but secondary to creating and using finished goods.

**Independent Test**: Can be tested by editing a finished good's components and verifying changes persist.

**Acceptance Scenarios**:

1. **Given** I select a finished good in the list, **When** I click Edit, **Then** I can modify the name, type, or components
2. **Given** I modify components and save, **When** I view the finished good again, **Then** I see the updated components
3. **Given** I select a finished good with no assembly history, **When** I delete it, **Then** it is removed from the list
4. **Given** I select a finished good with assembly history, **When** I try to delete it, **Then** I receive a warning about historical records

---

### User Story 5 - View Assembly History (Priority: P2)

As a baker, I want to see my assembly history with costs so that I can track production and analyze costs over time.

**Why this priority**: Historical visibility is valuable for reporting but not required for core workflow.

**Independent Test**: Can be tested by viewing assembly history and verifying cost snapshots are displayed accurately.

**Acceptance Scenarios**:

1. **Given** assemblies have been recorded, **When** I view the Assembly tab, **Then** I see a list with date, finished good, quantity, and cost per unit
2. **Given** I recorded assemblies at different times with different ingredient prices, **When** I view history, **Then** each assembly shows its captured cost (not current cost)
3. **Given** I select an assembly record, **When** I view details, **Then** I see the component breakdown with quantities and costs at assembly time

---

### Edge Cases

- What happens when a finished good has zero components defined? System requires at least one component.
- What happens when a component's finished unit is deleted? System prevents deletion of finished units that are components of finished goods.
- What happens when recording an assembly with quantity zero? System rejects invalid quantities.
- What happens when a finished good is edited while an assembly is in progress? Changes do not affect in-progress dialogs.
- What happens when all inventory of a component is consumed? Component shows zero available, assembly blocked until restocked.

## Requirements *(mandatory)*

### Functional Requirements

**Finished Goods Management (CATALOG Mode)**

- **FR-001**: System MUST allow users to create finished good definitions with a display name, assembly type, and one or more components
- **FR-002**: System MUST allow users to specify component quantities (how many of each finished unit per assembly)
- **FR-003**: System MUST display finished goods in a list view showing name, type, and component count
- **FR-004**: System MUST NOT display costs in the finished goods catalog view (costs are dynamic, not stored)
- **FR-005**: System MUST allow users to edit finished good definitions (name, type, components)
- **FR-006**: System MUST allow users to delete finished goods that have no assembly history
- **FR-007**: System MUST warn users before deleting finished goods that have assembly history

**Assembly Recording (MAKE Mode)**

- **FR-008**: System MUST allow users to record assembly runs specifying finished good, quantity, and optional event
- **FR-009**: System MUST capture a cost snapshot at assembly time (total cost and per-unit cost)
- **FR-010**: System MUST track which finished units were consumed and in what quantities
- **FR-011**: System MUST decrement finished unit inventory when assemblies are recorded
- **FR-012**: System MUST validate that sufficient inventory exists before allowing assembly recording
- **FR-013**: System MUST display assembly history with date, finished good, quantity, and captured costs

**Package Cost Calculation (PLAN Mode)**

- **FR-014**: System MUST calculate package costs dynamically from current finished good component costs
- **FR-015**: System MUST NOT reference stored cost fields on finished good definitions (use dynamic calculation)
- **FR-016**: Package cost calculation MUST work without errors in event planning workflows

**Data Integrity**

- **FR-017**: System MUST preserve historical cost accuracy (assembly cost snapshots are immutable)
- **FR-018**: System MUST maintain audit trail of component consumption per assembly
- **FR-019**: System MUST prevent deletion of finished units that are components of finished goods

### Key Entities

- **FinishedGood**: A definition of an assembled product (e.g., "Holiday Gift Box"). Contains a name, assembly type, and list of components. Does NOT store costs - costs are calculated dynamically when needed.

- **Composition**: A junction linking FinishedGood to its component FinishedUnits with quantities (e.g., "4x Large Cookie"). In F046, components are ONLY FinishedUnits - packaging materials deferred to F04X.

- **AssemblyRun**: A record of an assembly event capturing what was assembled, when, how many, and the cost snapshot at that moment. Immutable after creation.

- **AssemblyConsumption**: A junction tracking which FinishedUnits were consumed in an assembly run, with quantities and per-unit costs at assembly time.

- **Package**: (existing) A collection of FinishedGoods for event distribution. Costs calculated dynamically via FinishedGood calculations.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create a finished good definition with components in under 2 minutes
- **SC-002**: Users can record an assembly (select finished good, enter quantity, confirm) in under 1 minute
- **SC-003**: Package cost calculation in event planning completes without errors (zero crashes)
- **SC-004**: Historical assembly costs remain accurate regardless of current ingredient price changes
- **SC-005**: 100% of assembly operations validate inventory availability before proceeding
- **SC-006**: All finished goods are visible in catalog without any cost columns displayed
- **SC-007**: Assembly history displays cost snapshots that match the costs captured at assembly time

## Assumptions

- Finished units (the components of finished goods) already exist and have inventory tracking (completed in F044)
- The cost architecture refactor (F045) removed stored costs from definitions, establishing the pattern this feature follows
- Users understand that catalog costs are not shown because they vary based on current inventory
- The existing Package model and event planning UI exist and need the cost calculation fixed

## Dependencies

- **F044** (Finished Units): Must be complete - provides the components that make up finished goods
- **F045** (Cost Architecture Refactor): Must be complete - established the definition/instantiation pattern

## Scope Boundaries

**In Scope:**
- FinishedGood CRUD (create, read, update, delete)
- AssemblyRun recording with cost snapshots
- AssemblyConsumption tracking
- Package cost calculation fix
- Finished Goods tab UI (CATALOG mode)
- Assembly recording UI (MAKE mode)

**Out of Scope:**
- Shopping list generation from assemblies (F047)
- Assembly workflow reports and analytics (F048)
- Multi-stage assemblies (sub-assemblies containing other assemblies)
- Assembly yield loss tracking
- Finished unit lot tracking
- Packaging materials as components (deferred to F04X - proper PackagingMaterial model)

## Clarifications

### Session 2026-01-09

- Q: Can FinishedGood components include packaging/materials (Ingredients/Products) in addition to FinishedUnits, or are components ONLY FinishedUnits? → A: Defer packaging to future feature (F046 = FinishedUnits only). Packaging currently modeled incorrectly as Ingredients (temporary workaround). F04X will introduce proper PackagingMaterial model.
