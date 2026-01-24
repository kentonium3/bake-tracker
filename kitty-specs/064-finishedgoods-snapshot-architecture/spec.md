# Feature Specification: FinishedGoods Snapshot Architecture

**Feature Branch**: `064-finishedgoods-snapshot-architecture`
**Created**: 2025-01-24
**Status**: Draft
**Input**: User description: "see docs/func-spec/F064_finished_goods_snapshot_implementation.md for inputs on this feature."

## Clarifications

### Session 2025-01-24

- Q: What is an acceptable response time for creating a complete snapshot tree? → A: Under 5 seconds for complex cases (up to 50 components)

## Overview

This feature implements immutable snapshot capture for FinishedGoods (gift boxes, assembled products) at planning and assembly time. Currently, changes to FinishedGood definitions affect planned and historical assemblies because the system references live catalog definitions. This violates the definition/instantiation separation principle already established for recipes.

**Business Problem**: When a user modifies a gift box's composition (e.g., changes from 6 cookies to 8 cookies), all previously planned events and completed assemblies incorrectly reflect the new definition instead of preserving what was actually planned or assembled.

**Solution**: Capture immutable snapshots of FinishedUnit, FinishedGood, and MaterialUnit definitions at the moment of planning or assembly, ensuring historical accuracy and supporting audit requirements.

## User Scenarios & Testing

### User Story 1 - Preserve Assembly History Accuracy (Priority: P1)

As a baker who assembled gift boxes last week, I need the system to remember exactly what was in each box at the time of assembly, even if I later change the gift box recipe.

**Why this priority**: This is the core value proposition. Without accurate historical records, users cannot trust the system for inventory tracking, cost calculation, or audit purposes.

**Independent Test**: Can be fully tested by recording an assembly, modifying the FinishedGood definition, then verifying the assembly record still shows the original composition.

**Acceptance Scenarios**:

1. **Given** I assembled 10 "Holiday Cookie Boxes" yesterday containing 6 chocolate chip cookies each, **When** I update the box definition to contain 8 cookies, **Then** viewing yesterday's assembly still shows 6 cookies per box.

2. **Given** I have an assembly record from last month, **When** I delete the FinishedGood definition entirely, **Then** the assembly record is preserved with all original component details intact.

3. **Given** I assembled a gift box containing a nested "Cookie Sampler" sub-assembly, **When** I modify the Cookie Sampler's composition, **Then** my assembly record preserves the original Cookie Sampler composition at the time of assembly.

---

### User Story 2 - Lock Event Plans at Planning Time (Priority: P1)

As an event planner, I need my production and assembly targets to be locked when I finalize a plan, so last-minute catalog changes don't disrupt my event preparation.

**Why this priority**: Events require advance planning. If catalog changes mid-planning affect the plan, inventory calculations become unreliable.

**Independent Test**: Can be fully tested by creating event targets, modifying catalog definitions, then verifying the event plan reflects original definitions.

**Acceptance Scenarios**:

1. **Given** I created assembly targets for "Thanksgiving Gift Boxes" for an event, **When** someone updates the gift box composition, **Then** my event plan still shows the original composition and quantities needed.

2. **Given** I have planned 50 cookie boxes for an event with specific material requirements (ribbons, boxes), **When** the material specifications change in the catalog, **Then** my event's material requirements reflect the original specifications.

3. **Given** I plan an event with complex nested gift boxes (box contains cookie sampler which contains individual cookie types), **When** any level of the hierarchy is modified, **Then** my entire nested plan is preserved as originally specified.

---

### User Story 3 - Prevent Infinite Loop in Complex Gift Structures (Priority: P2)

As a power user creating complex gift structures, I need the system to prevent me from creating circular references (Box A contains Box B which contains Box A) that could cause system failures.

**Why this priority**: While less common, circular references could cause system crashes during snapshot creation. Prevention ensures system stability.

**Independent Test**: Can be fully tested by attempting to create a circular reference and verifying the system blocks it with a clear error message.

**Acceptance Scenarios**:

1. **Given** I have a gift box that contains another gift box, **When** I try to add the parent box as a component of the child box, **Then** the system prevents this with a clear error message indicating the circular reference.

2. **Given** I have a 3-level hierarchy (Box A > Box B > Box C), **When** I try to add Box A as a component of Box C, **Then** the system detects and prevents this circular chain.

---

### User Story 4 - Preserve Material Component Details (Priority: P2)

As a gift assembler, I need material components (ribbons, packaging, decorations) captured in assembly snapshots so I can track exactly what materials were used.

**Why this priority**: Materials are part of the complete assembly record. Without material snapshots, cost tracking and inventory reconciliation are incomplete.

**Independent Test**: Can be fully tested by recording an assembly with material components, modifying material definitions, then verifying the assembly record preserves original material details.

**Acceptance Scenarios**:

1. **Given** I assembled gift boxes using "6-inch Red Ribbon" material units, **When** I update the ribbon's quantity_per_unit specification, **Then** my assembly record shows the original ribbon specification.

2. **Given** I assembled boxes with specific packaging materials, **When** I view the assembly history, **Then** I can see all material components that were part of each assembly including their quantities and specifications.

---

### Edge Cases

- What happens when creating a snapshot for a FinishedGood with 10+ levels of nesting? System enforces maximum depth and returns clear error.
- How does system handle snapshot creation when a component's catalog definition is deleted mid-transaction? Transaction atomicity ensures all-or-nothing - either complete snapshot tree or rollback.
- What happens when creating snapshots for a FinishedGood with 50+ components? System handles large component lists within transaction boundaries.
- How does system handle generic material placeholders (is_generic=true) in composition? Placeholder data captured without requiring MaterialUnit snapshot.

## Requirements

### Functional Requirements

- **FR-001**: System MUST capture FinishedUnit definitions as immutable snapshots at planning and assembly time.
- **FR-002**: System MUST capture FinishedGood definitions including all component relationships as immutable snapshots.
- **FR-003**: System MUST capture MaterialUnit definitions as immutable snapshots for material components in assemblies.
- **FR-004**: System MUST automatically create snapshots for all nested components when creating a FinishedGood snapshot (recursive capture).
- **FR-005**: System MUST detect and prevent circular references when creating snapshots for nested FinishedGoods.
- **FR-006**: System MUST enforce a maximum nesting depth of 10 levels for FinishedGood hierarchies.
- **FR-007**: System MUST create all snapshots for a complex hierarchy within a single transaction (all-or-nothing).
- **FR-008**: Assembly records MUST reference snapshots rather than live catalog definitions.
- **FR-009**: Event planning targets MUST reference snapshots created at plan finalization time.
- **FR-010**: Snapshots MUST be immutable - no modifications allowed after creation.
- **FR-011**: System MUST preserve assembly records even when source catalog definitions are modified or deleted.
- **FR-012**: Circular reference error messages MUST indicate which component caused the circular dependency.
- **FR-013**: System MUST handle generic material placeholders without requiring a MaterialUnit snapshot.

### Key Entities

- **FinishedUnitSnapshot**: Immutable capture of a FinishedUnit definition (individual baked item like "Chocolate Chip Cookie") at a point in time. Contains all definition fields including yield mode, items per batch, and linked recipe information.

- **FinishedGoodSnapshot**: Immutable capture of a FinishedGood definition (assembled product like "Holiday Gift Box") including its complete component structure. References nested snapshots for all FinishedUnit, FinishedGood, and MaterialUnit components.

- **MaterialUnitSnapshot**: Immutable capture of a MaterialUnit definition (packaging/material component like "6-inch Ribbon") at a point in time. Contains material reference, quantity specifications, and description.

- **PlanningSnapshot**: Container record linking an event to all snapshots created during plan finalization. Provides single reference point for all production and assembly target snapshots.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Assembly records display accurate historical component composition regardless of subsequent catalog changes.
- **SC-002**: Event production plans maintain accurate requirements after catalog modifications.
- **SC-003**: Circular reference attempts are blocked with user-understandable error messages indicating the specific conflict.
- **SC-004**: Nested FinishedGood structures up to 10 levels deep successfully create complete snapshot trees.
- **SC-005**: All component snapshots for a single assembly are created atomically - no partial snapshot trees exist.
- **SC-006**: Snapshot tree creation completes in under 5 seconds for complex FinishedGoods with up to 50 components.

## Assumptions

- No existing assembly production data exists that would require migration or backfilling.
- The existing RecipeSnapshot pattern provides a validated implementation template to follow.
- Maximum nesting depth of 10 levels is sufficient for all practical use cases.
- Cascade deletion behavior is appropriate for planning-linked snapshots (deleting a planning snapshot deletes associated component snapshots).

## Out of Scope

- Package-level snapshots (Tier 3 - deferred to future phase)
- Snapshot versioning or change tracking (snapshots are point-in-time captures)
- Snapshot comparison or diff functionality
- UI for viewing snapshot history
- Snapshot backfilling for historical records
